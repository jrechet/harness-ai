from django.db import models
from django.db.models import Q


class Enrollment(models.Model):
    class Status(models.TextChoices):
        CONFIRMED = "confirmed", "Confirmée"
        WAITLISTED = "waitlisted", "Liste d'attente"
        CANCELLED = "cancelled", "Annulée"

    session = models.ForeignKey("catalog.Session", on_delete=models.CASCADE, related_name="enrollments")
    full_name = models.CharField("nom et prénom", max_length=200)
    email = models.EmailField("adresse e-mail")
    status = models.CharField("statut", max_length=12, choices=Status.choices)
    created_at = models.DateTimeField("inscrit le", auto_now_add=True)
    cancelled_at = models.DateTimeField("annulé le", null=True, blank=True)

    class Meta:
        ordering = ["created_at", "id"]
        verbose_name = "inscription"
        constraints = [
            models.UniqueConstraint(
                fields=["session", "email"],
                condition=~Q(status="cancelled"),
                name="one_active_enrollment_per_email",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.full_name} ({self.get_status_display()})"

    @property
    def is_active(self) -> bool:
        return self.status != self.Status.CANCELLED
