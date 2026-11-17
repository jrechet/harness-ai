from django.db import models
from django.db.models import Q


class Enrollment(models.Model):
    class Status(models.TextChoices):
        CONFIRMED = "confirmed", "Confirmed"
        WAITLISTED = "waitlisted", "Waiting list"
        CANCELLED = "cancelled", "Cancelled"

    session = models.ForeignKey("catalog.Session", on_delete=models.CASCADE, related_name="enrollments")
    full_name = models.CharField("full name", max_length=200)
    email = models.EmailField("e-mail address")
    status = models.CharField("status", max_length=12, choices=Status.choices)
    created_at = models.DateTimeField("enrolled on", auto_now_add=True)
    cancelled_at = models.DateTimeField("cancelled on", null=True, blank=True)

    class Meta:
        ordering = ["created_at", "id"]
        verbose_name = "enrollment"
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
