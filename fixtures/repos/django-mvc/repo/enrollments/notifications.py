"""Every e-mail the application sends. The services call these functions once their transaction has
committed; nothing here is wired to a model signal."""
from django.core.mail import send_mail
from django.utils import timezone

from .models import Enrollment


def _when_and_where(enrollment: Enrollment) -> str:
    session = enrollment.session
    return f"{timezone.localtime(session.starts_at):%d/%m/%Y à %H:%M}, {session.location}"


def send_enrollment_email(enrollment_id: int) -> None:
    enrollment = Enrollment.objects.select_related("session__course").get(pk=enrollment_id)
    title = enrollment.session.course.title
    match enrollment.status:
        case Enrollment.Status.CONFIRMED:
            subject = f"Inscription confirmée : {title}"
            body = (
                f"Bonjour {enrollment.full_name},\n\n"
                f"Votre inscription à « {title} » est confirmée.\n"
                f"Rendez-vous le {_when_and_where(enrollment)}.\n"
            )
        case Enrollment.Status.WAITLISTED:
            subject = f"Liste d'attente : {title}"
            body = (
                f"Bonjour {enrollment.full_name},\n\n"
                f"La session « {title} » du {_when_and_where(enrollment)} est complète.\n"
                "Vous êtes sur liste d'attente : nous vous écrirons si une place se libère.\n"
            )
        case _:
            return
    send_mail(subject, body, None, [enrollment.email])


def send_promotion_email(enrollment_id: int) -> None:
    enrollment = Enrollment.objects.select_related("session__course").get(pk=enrollment_id)
    title = enrollment.session.course.title
    send_mail(
        f"Une place s'est libérée : {title}",
        f"Bonjour {enrollment.full_name},\n\n"
        f"Une place s'est libérée : votre inscription à « {title} » est confirmée.\n"
        f"Rendez-vous le {_when_and_where(enrollment)}.\n",
        None,
        [enrollment.email],
    )
