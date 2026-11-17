"""A list page runs the same number of queries whatever the number of rows it shows.

Written after the home page took 14 seconds (docs/postmortems/2025-06-session-list.md).
A template that reaches for a relation or a count on each row breaks these tests: fix the view
(`annotate`, `select_related`), not the expected number."""
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .test_pages import fill, make_session


class ListPagesQueryCountTests(TestCase):
    def test_the_session_list_does_not_query_per_session(self):
        for n in range(15):
            fill(make_session(days=n + 1, capacity=3), confirmed=3, waitlisted=2)
        # one count for the pagination, one query for the page
        with self.assertNumQueries(2):
            response = self.client.get(reverse("catalog:session_list"))
        self.assertContains(response, "Full, 2 waiting", count=15)

    def test_the_roster_does_not_query_per_enrollment(self):
        session = make_session(capacity=20)
        fill(session, confirmed=20, waitlisted=5)
        self.client.force_login(get_user_model().objects.create_user("lea", is_staff=True))
        # the browser session, the user, the training session, its enrollments
        with self.assertNumQueries(4):
            response = self.client.get(reverse("enrollments:roster", args=[session.pk]))
        self.assertContains(response, "@example.test", count=25)
