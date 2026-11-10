from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase
from django.urls import reverse

from catalog.tests.test_pages import fill, make_session
from enrollments.models import Enrollment


class EnrollViewTests(TestCase):
    def setUp(self):
        self.session = make_session(capacity=1)
        self.url = reverse("enrollments:enroll", args=[self.session.pk])

    def post(self, email="ana@example.test", full_name="Ana Morel"):
        with self.captureOnCommitCallbacks(execute=True):
            return self.client.post(self.url, {"email": email, "full_name": full_name}, follow=True)

    def test_enrolls_and_confirms_by_email(self):
        response = self.post()
        self.assertRedirects(response, self.session.get_absolute_url())
        self.assertContains(response, "Inscription confirmée")
        self.assertEqual(Enrollment.objects.get().status, "confirmed")
        self.assertEqual(len(mail.outbox), 1)

    def test_a_full_session_puts_on_the_waiting_list(self):
        fill(self.session, confirmed=1)
        self.assertContains(self.post(), "liste d'attente")
        self.assertEqual(Enrollment.objects.get(email="ana@example.test").status, "waitlisted")

    def test_an_invalid_address_shows_the_form_again(self):
        response = self.post(email="not-an-address")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name="email"')
        self.assertFalse(Enrollment.objects.exists())

    def test_the_same_address_twice(self):
        self.post()
        self.assertContains(self.post(), "déjà inscrite")
        self.assertEqual(Enrollment.objects.count(), 1)

    def test_a_started_session(self):
        url = reverse("enrollments:enroll", args=[make_session(days=-1).pk])
        self.assertContains(self.client.post(url, {"email": "ana@example.test", "full_name": "Ana"}), "closes")

    def test_get_is_refused(self):
        self.assertEqual(self.client.get(self.url).status_code, 405)


class StaffPagesTests(TestCase):
    def setUp(self):
        self.session = make_session(capacity=1)
        fill(self.session, confirmed=1, waitlisted=1)
        self.roster = reverse("enrollments:roster", args=[self.session.pk])
        self.staff = get_user_model().objects.create_user("lea", is_staff=True)

    def test_the_roster_is_for_staff_only(self):
        self.assertEqual(self.client.get(self.roster).status_code, 302)
        self.client.force_login(get_user_model().objects.create_user("visitor"))
        self.assertEqual(self.client.get(self.roster).status_code, 302)

    def test_the_roster_lists_everyone_with_their_status(self):
        self.client.force_login(self.staff)
        response = self.client.get(self.roster)
        self.assertContains(response, "c0@example.test")
        self.assertContains(response, "Liste d&#x27;attente")

    def test_staff_cancels_and_the_waiting_list_moves_up(self):
        self.client.force_login(self.staff)
        confirmed = self.session.enrollments.get(status="confirmed")
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(reverse("enrollments:cancel", args=[confirmed.pk]), follow=True)
        self.assertRedirects(response, self.roster)
        self.assertContains(response, "Attente 0 passe de la liste d&#x27;attente aux inscrits")
        self.assertEqual(self.session.enrollments.get(email="w0@example.test").status, "confirmed")
        self.assertEqual(mail.outbox[-1].to, ["w0@example.test"])

    def test_cancelling_is_for_staff_only(self):
        confirmed = self.session.enrollments.get(status="confirmed")
        self.client.post(reverse("enrollments:cancel", args=[confirmed.pk]))
        confirmed.refresh_from_db()
        self.assertEqual(confirmed.status, "confirmed")
