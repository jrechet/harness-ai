from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from catalog.models import Course, Session
from enrollments.models import Enrollment


def make_session(course=None, *, days=10, capacity=12, location="Salle Ampère"):
    course = course or Course.objects.get_or_create(slug="sst", defaults={"title": "Sauveteur secouriste du travail"})[0]
    return Session.objects.create(
        course=course, starts_at=timezone.now() + timedelta(days=days), location=location, capacity=capacity
    )


def fill(session, confirmed=0, waitlisted=0):
    for n in range(confirmed):
        Enrollment.objects.create(
            session=session, full_name=f"Inscrit {n}", email=f"c{n}@example.test", status=Enrollment.Status.CONFIRMED
        )
    for n in range(waitlisted):
        Enrollment.objects.create(
            session=session, full_name=f"Attente {n}", email=f"w{n}@example.test", status=Enrollment.Status.WAITLISTED
        )


class SessionListTests(TestCase):
    def test_lists_upcoming_sessions_only(self):
        make_session(location="Salle Ampère")
        make_session(days=-3, location="Salle Volta")
        response = self.client.get(reverse("catalog:session_list"))
        self.assertContains(response, "Salle Ampère")
        self.assertNotContains(response, "Salle Volta")

    def test_shows_the_seats_left(self):
        fill(make_session(capacity=12), confirmed=5)
        self.assertContains(self.client.get("/"), "7 sur 12")

    def test_a_full_session_shows_its_waiting_list(self):
        fill(make_session(capacity=2), confirmed=2, waitlisted=3)
        self.assertContains(self.client.get("/"), "Complet, 3 en attente")

    def test_a_cancelled_enrollment_frees_its_seat(self):
        session = make_session(capacity=2)
        fill(session, confirmed=2)
        session.enrollments.filter(email="c0@example.test").update(status=Enrollment.Status.CANCELLED)
        self.assertContains(self.client.get("/"), "1 sur 2")

    def test_filters_by_course(self):
        other = Course.objects.create(title="Habilitation électrique B1", slug="b1")
        make_session(location="Salle Ampère")
        make_session(other, location="Atelier 3")
        response = self.client.get("/", {"course": "b1"})
        self.assertContains(response, "Atelier 3")
        self.assertNotContains(response, "Salle Ampère")

    def test_paginates_and_keeps_the_filter(self):
        for n in range(25):
            make_session(days=n + 1)
        response = self.client.get("/", {"course": "sst"})
        self.assertEqual(len(response.context["sessions"]), 20)
        self.assertContains(response, "?course=sst&amp;page=2")


class SessionDetailTests(TestCase):
    def test_shows_the_enrollment_form(self):
        session = make_session(capacity=12)
        response = self.client.get(session.get_absolute_url())
        self.assertContains(response, "12 places sur 12")
        self.assertContains(response, 'name="email"')

    def test_a_started_session_takes_no_enrollment(self):
        response = self.client.get(make_session(days=-1).get_absolute_url())
        self.assertContains(response, "closes")
        self.assertNotContains(response, 'name="email"')

    def test_unknown_session(self):
        self.assertEqual(self.client.get("/sessions/999/").status_code, 404)
