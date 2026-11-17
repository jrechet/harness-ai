from django.db import models
from django.db.models import Count, F, Q
from django.urls import reverse
from django.utils import timezone


class Course(models.Model):
    title = models.CharField("title", max_length=200)
    slug = models.SlugField(unique=True)
    summary = models.TextField("summary", blank=True)

    class Meta:
        ordering = ["title"]
        verbose_name = "course"

    def __str__(self) -> str:
        return self.title


class SessionQuerySet(models.QuerySet):
    def upcoming(self):
        return self.filter(starts_at__gt=timezone.now())

    def with_seats(self):
        """The course and the seat counts come with the row: a list page needs nothing else."""
        return (
            self.select_related("course")
            .annotate(
                confirmed_count=Count("enrollments", filter=Q(enrollments__status="confirmed")),
                waitlisted_count=Count("enrollments", filter=Q(enrollments__status="waitlisted")),
            )
            .annotate(seats_left=F("capacity") - F("confirmed_count"))
            .order_by("starts_at", "id")  # an aggregate drops Meta.ordering
        )


class Session(models.Model):
    course = models.ForeignKey(Course, on_delete=models.PROTECT, related_name="sessions", verbose_name="course")
    starts_at = models.DateTimeField("start")
    location = models.CharField("location", max_length=120)
    capacity = models.PositiveIntegerField("seats")

    objects = SessionQuerySet.as_manager()

    class Meta:
        ordering = ["starts_at", "id"]
        constraints = [
            models.CheckConstraint(condition=Q(capacity__gte=1), name="session_capacity_at_least_one"),
        ]

    def __str__(self) -> str:
        return f"{self.course} ({timezone.localtime(self.starts_at):%d/%m/%Y})"

    def get_absolute_url(self) -> str:
        return reverse("catalog:session_detail", args=[self.pk])

    @property
    def has_started(self) -> bool:
        return self.starts_at <= timezone.now()
