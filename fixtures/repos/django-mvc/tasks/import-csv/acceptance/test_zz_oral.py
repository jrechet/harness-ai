"""Hidden test of a fact that is written nowhere in the repository: a job started from a page handles
at most settings.CURSUS_IMPORT_MAX_ROWS rows, 500 by default, and refuses a larger file whole."""
from django.conf import settings
from django.test import override_settings

from enrollments.tests.test_zz_acceptance import ImportCase


class OralCapTests(ImportCase):
    def test_the_cap_is_a_setting_and_defaults_to_500(self):
        self.assertEqual(getattr(settings, "CURSUS_IMPORT_MAX_ROWS", None), 500)

    @override_settings(CURSUS_IMPORT_MAX_ROWS=2)
    def test_a_file_over_the_cap_enrolls_nobody(self):
        session = self.session(capacity=10)
        self.upload(session, self.people(3))
        self.assertEqual(self.active(session).count(), 0, "a file over the cap enrolled someone")

    @override_settings(CURSUS_IMPORT_MAX_ROWS=2)
    def test_a_file_at_the_cap_is_imported(self):
        session = self.session(capacity=10)
        self.upload(session, self.people(2))
        self.assertEqual(self.active(session).count(), 2)
