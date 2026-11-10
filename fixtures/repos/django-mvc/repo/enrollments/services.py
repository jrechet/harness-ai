"""The business rules of an enrollment: seats, waiting list, cancellation. Views and admin actions
call these functions; they hold no rule of their own (docs/adr/0001)."""
from functools import partial

from django.db import transaction
from django.utils import timezone

from catalog.models import Session

from . import notifications
from .models import Enrollment


class EnrollmentError(Exception):
    pass


class AlreadyEnrolled(EnrollmentError):
    pass


class SessionClosed(EnrollmentError):
    pass


def enroll(session: Session, *, email: str, full_name: str) -> Enrollment:
    """Enrolls one person: confirmed while a seat is left, on the waiting list after that.
    The e-mail leaves once the transaction has committed."""
    email = email.strip().lower()
    with transaction.atomic():
        # The row lock is what keeps two simultaneous requests from taking the same last seat.
        locked = Session.objects.select_for_update().get(pk=session.pk)
        if locked.has_started:
            raise SessionClosed(locked.pk)
        active = locked.enrollments.exclude(status=Enrollment.Status.CANCELLED)
        if active.filter(email=email).exists():
            raise AlreadyEnrolled(email)
        seats_taken = active.filter(status=Enrollment.Status.CONFIRMED).count()
        status = Enrollment.Status.CONFIRMED if seats_taken < locked.capacity else Enrollment.Status.WAITLISTED
        enrollment = Enrollment.objects.create(
            session=locked, email=email, full_name=full_name.strip(), status=status
        )
        transaction.on_commit(partial(notifications.send_enrollment_email, enrollment.pk))
    return enrollment


def cancel(enrollment: Enrollment) -> Enrollment | None:
    """Cancels an enrollment. A freed seat goes to the head of the waiting list: the promoted
    enrollment is returned, None when nobody was waiting."""
    with transaction.atomic():
        locked = Session.objects.select_for_update().get(pk=enrollment.session_id)
        enrollment.refresh_from_db()
        if not enrollment.is_active:
            return None
        freed_a_seat = enrollment.status == Enrollment.Status.CONFIRMED
        enrollment.status = Enrollment.Status.CANCELLED
        enrollment.cancelled_at = timezone.now()
        enrollment.save(update_fields=["status", "cancelled_at"])
        if not freed_a_seat or locked.has_started:
            return None
        promoted = locked.enrollments.filter(status=Enrollment.Status.WAITLISTED).first()
        if promoted is None:
            return None
        promoted.status = Enrollment.Status.CONFIRMED
        promoted.save(update_fields=["status"])
        transaction.on_commit(partial(notifications.send_promotion_email, promoted.pk))
    return promoted
