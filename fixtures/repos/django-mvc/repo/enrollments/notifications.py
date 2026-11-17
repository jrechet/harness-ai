"""Every e-mail the application sends. The services call these functions once their transaction has
committed; nothing here is wired to a model signal."""
from django.core.mail import send_mail
from django.utils import timezone

from .models import Enrollment


def _when_and_where(enrollment: Enrollment) -> str:
    session = enrollment.session
    return f"{timezone.localtime(session.starts_at):%d/%m/%Y at %H:%M}, {session.location}"


def send_enrollment_email(enrollment_id: int) -> None:
    enrollment = Enrollment.objects.select_related("session__course").get(pk=enrollment_id)
    title = enrollment.session.course.title
    match enrollment.status:
        case Enrollment.Status.CONFIRMED:
            subject = f"Enrollment confirmed: {title}"
            body = (
                f"Hello {enrollment.full_name},\n\n"
                f"Your enrollment in “{title}” is confirmed.\n"
                f"See you on {_when_and_where(enrollment)}.\n"
            )
        case Enrollment.Status.WAITLISTED:
            subject = f"Waiting list: {title}"
            body = (
                f"Hello {enrollment.full_name},\n\n"
                f"The session “{title}” of {_when_and_where(enrollment)} is full.\n"
                "You are on the waiting list: we will write to you if a seat is freed.\n"
            )
        case _:
            return
    send_mail(subject, body, None, [enrollment.email])


def send_promotion_email(enrollment_id: int) -> None:
    enrollment = Enrollment.objects.select_related("session__course").get(pk=enrollment_id)
    title = enrollment.session.course.title
    send_mail(
        f"A seat has been freed: {title}",
        f"Hello {enrollment.full_name},\n\n"
        f"A seat has been freed: your enrollment in “{title}” is confirmed.\n"
        f"See you on {_when_and_where(enrollment)}.\n",
        None,
        [enrollment.email],
    )
