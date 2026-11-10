"""Hidden acceptance tests of the import-csv task. They only use what the task statement gives (the
two URLs, the `file` field, the CSV header) and what the project had before the task: the test
client, the models, the staff flag."""
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from catalog.models import Course, Session
from enrollments.models import Enrollment

IMPORTER = "zz-importer"


class ImportCase(TestCase):
    def setUp(self):
        self.course = Course.objects.create(title="Zz acceptance", slug="zz-acceptance")
        self.staff = get_user_model().objects.create_user(IMPORTER, password="zz", is_staff=True)
        self.client.force_login(self.staff)

    def session(self, capacity):
        return Session.objects.create(
            course=self.course, starts_at=timezone.now() + timedelta(days=30), location="Zz room", capacity=capacity
        )

    def seat(self, session, count):
        for n in range(count):
            Enrollment.objects.create(
                session=session, full_name=f"Seated {n}", email=f"seated{n}@example.test", status="confirmed"
            )

    def upload(self, session, rows, client=None):
        """Posts a CSV and lets the callbacks registered for the commit run, as they do in production."""
        content = "email,full_name\n" + "".join(f"{email},{name}\n" for email, name in rows)
        file = SimpleUploadedFile("list.csv", content.encode("utf-8"), content_type="text/csv")
        with self.captureOnCommitCallbacks(execute=True):
            return (client or self.client).post(f"/sessions/{session.pk}/import/", {"file": file}, follow=True)

    def people(self, count, prefix="row"):
        return [(f"zz-{prefix}{n}@example.test", f"Zz {prefix.title()} {n}") for n in range(count)]

    def active(self, session, prefix="zz-"):
        return Enrollment.objects.filter(session=session, email__startswith=prefix).exclude(status="cancelled")


class ImportTests(ImportCase):
    def test_every_row_enrolls_its_person(self):
        session = self.session(capacity=10)
        response = self.upload(session, self.people(3))
        self.assertLess(response.status_code, 400, "the import answered an error")
        self.assertEqual(
            sorted(self.active(session).values_list("email", flat=True)),
            ["zz-row0@example.test", "zz-row1@example.test", "zz-row2@example.test"],
        )
        self.assertEqual(self.active(session).get(email="zz-row1@example.test").full_name, "Zz Row 1")

    def test_the_form_is_shown_on_get(self):
        response = self.client.get(f"/sessions/{self.session(capacity=10).pk}/import/")
        self.assertEqual(response.status_code, 200)
        self.assertRegex(response.content.decode(), r"""name=["']file["']""")

    def test_the_page_is_for_staff_only(self):
        session = self.session(capacity=10)
        for client in (self.client_class(), self.logged_in("zz-visitor", is_staff=False)):
            self.upload(session, self.people(2), client=client)
            self.assertEqual(self.active(session).count(), 0, "someone who is not staff imported enrollments")

    def logged_in(self, username, **flags):
        client = self.client_class()
        client.force_login(get_user_model().objects.create_user(username, password="zz", **flags))
        return client

    def test_an_address_already_enrolled_is_skipped(self):
        session = self.session(capacity=10)
        Enrollment.objects.create(
            session=session, full_name="Zz Row 0", email="zz-row0@example.test", status="confirmed"
        )
        response = self.upload(session, self.people(2) + self.people(2))
        self.assertLess(response.status_code, 400, "a repeated address broke the import")
        self.assertEqual(self.active(session).filter(email="zz-row0@example.test").count(), 1)
        self.assertEqual(self.active(session).filter(email="zz-row1@example.test").count(), 1)

    def test_the_roster_tells_who_imported(self):
        session = self.session(capacity=10)
        self.upload(session, self.people(2))
        self.assertContains(self.client.get(f"/sessions/{session.pk}/roster/"), IMPORTER)


class CapacityTests(ImportCase):
    def test_an_import_never_confirms_more_people_than_the_session_has_seats(self):
        session = self.session(capacity=5)
        self.seat(session, 3)
        self.upload(session, self.people(6))
        self.assertEqual(self.active(session).count(), 6, "the six rows of the file are not all enrolled")
        confirmed = Enrollment.objects.filter(session=session, status="confirmed").count()
        self.assertLessEqual(confirmed, 5, f"{confirmed} confirmed enrollments for 5 seats")


class MailTests(ImportCase):
    def test_an_import_does_not_send_one_email_per_row(self):
        session = self.session(capacity=30)
        self.upload(session, self.people(20))
        self.assertEqual(self.active(session).count(), 20, "the twenty rows of the file are not all enrolled")
        self.assertLessEqual(len(mail.outbox), 1, f"{len(mail.outbox)} e-mails left for a 20-row import")


class QueryTests(ImportCase):
    def test_the_roster_runs_as_many_queries_for_3_imported_rows_as_for_30(self):
        small, large = self.session(capacity=50), self.session(capacity=50)
        self.upload(small, self.people(3, "few"))
        self.upload(large, self.people(30, "many"))
        self.assertEqual((self.active(small).count(), self.active(large).count()), (3, 30))
        with CaptureQueriesContext(connection) as few:
            self.assertContains(self.client.get(f"/sessions/{small.pk}/roster/"), IMPORTER)
        with CaptureQueriesContext(connection) as many:
            self.assertContains(self.client.get(f"/sessions/{large.pk}/roster/"), IMPORTER)
        self.assertEqual(len(few), len(many), f"{len(few)} queries for 3 rows, {len(many)} for 30")
