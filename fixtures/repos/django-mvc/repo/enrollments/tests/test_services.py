from django.core import mail
from django.db import transaction
from django.test import TestCase

from catalog.tests.test_pages import make_session
from enrollments import services
from enrollments.models import Enrollment


def enroll(session, name):
    return services.enroll(session, email=f"{name}@example.test", full_name=name.title())


class EnrollTests(TestCase):
    def test_confirmed_while_a_seat_is_left_then_waitlisted(self):
        session = make_session(capacity=2)
        statuses = [enroll(session, name).status for name in ("ana", "bob", "cleo")]
        self.assertEqual(statuses, ["confirmed", "confirmed", "waitlisted"])

    def test_the_same_address_cannot_enroll_twice(self):
        session = make_session()
        enroll(session, "ana")
        with self.assertRaises(services.AlreadyEnrolled):
            services.enroll(session, email=" ANA@example.test ", full_name="Ana")
        self.assertEqual(session.enrollments.count(), 1)

    def test_a_cancelled_address_can_enroll_again(self):
        session = make_session()
        services.cancel(enroll(session, "ana"))
        self.assertEqual(enroll(session, "ana").status, "confirmed")

    def test_a_started_session_is_closed(self):
        with self.assertRaises(services.SessionClosed):
            enroll(make_session(days=-1), "ana")

    def test_the_same_address_can_follow_two_sessions(self):
        enroll(make_session(), "ana")
        self.assertEqual(enroll(make_session(days=20), "ana").status, "confirmed")


class CancelTests(TestCase):
    def setUp(self):
        self.session = make_session(capacity=1)
        self.ana, self.bob, self.cleo = (enroll(self.session, name) for name in ("ana", "bob", "cleo"))

    def test_a_freed_seat_goes_to_the_head_of_the_waiting_list(self):
        promoted = services.cancel(self.ana)
        self.assertEqual(promoted, self.bob)
        self.bob.refresh_from_db()
        self.cleo.refresh_from_db()
        self.assertEqual((self.bob.status, self.cleo.status), ("confirmed", "waitlisted"))

    def test_leaving_the_waiting_list_promotes_nobody(self):
        self.assertIsNone(services.cancel(self.bob))
        self.cleo.refresh_from_db()
        self.assertEqual(self.cleo.status, "waitlisted")

    def test_cancelling_twice_changes_nothing(self):
        services.cancel(self.ana)
        self.assertIsNone(services.cancel(self.ana))
        self.assertEqual(self.session.enrollments.filter(status="confirmed").count(), 1)

    def test_the_cancellation_is_dated(self):
        services.cancel(self.ana)
        self.ana.refresh_from_db()
        self.assertIsNotNone(self.ana.cancelled_at)


class EmailTests(TestCase):
    def test_a_confirmation_leaves_once_the_enrollment_is_committed(self):
        session = make_session(capacity=1)
        with self.captureOnCommitCallbacks(execute=True):
            enroll(session, "ana")
        self.assertEqual([m.to for m in mail.outbox], [["ana@example.test"]])
        self.assertIn("Inscription confirmée", mail.outbox[0].subject)
        self.assertIn("Salle Ampère", mail.outbox[0].body)

    def test_the_waiting_list_gets_its_own_message(self):
        session = make_session(capacity=1)
        enroll(session, "ana")
        with self.captureOnCommitCallbacks(execute=True):
            enroll(session, "bob")
        self.assertIn("Liste d'attente", mail.outbox[-1].subject)

    def test_a_promotion_is_announced(self):
        session = make_session(capacity=1)
        ana = enroll(session, "ana")
        enroll(session, "bob")
        with self.captureOnCommitCallbacks(execute=True):
            services.cancel(ana)
        self.assertEqual(mail.outbox[-1].to, ["bob@example.test"])
        self.assertIn("Une place s'est libérée", mail.outbox[-1].subject)

    def test_nothing_leaves_when_the_transaction_rolls_back(self):
        session = make_session()
        with self.captureOnCommitCallbacks(execute=True) as callbacks:
            try:
                with transaction.atomic():
                    enroll(session, "ana")
                    raise RuntimeError("the surrounding work failed")
            except RuntimeError:
                pass
        self.assertEqual(callbacks, [])
        self.assertEqual(mail.outbox, [])

    def test_saving_an_enrollment_sends_nothing(self):
        session = make_session()
        with self.captureOnCommitCallbacks(execute=True):
            Enrollment.objects.create(
                session=session, full_name="Ana", email="ana@example.test", status=Enrollment.Status.CONFIRMED
            )
        self.assertEqual(mail.outbox, [])
