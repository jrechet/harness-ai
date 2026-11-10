import contextlib
import io
import json
import os
import tempfile
import unittest

from tools.check_imports import SERVICE_RULE, SHARED_RULE, check, main

REPOSITORY = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class CheckImportsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = self.tmp.name

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, rel, source):
        path = os.path.join(self.root, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(source)

    def found(self):
        return [(v["file"], v["line"], v["import"], v["rule"]) for v in check(self.root)]

    def test_a_service_may_import_itself_shared_code_and_the_standard_library(self):
        self.write("services/billing/app.py",
                   "import json\nfrom shared.bus import envelope\nfrom services.billing.ledger import Ledger\nfrom .ledger import Invoice\n")
        self.assertEqual(self.found(), [])

    def test_a_service_importing_another_service_is_a_violation(self):
        self.write("services/billing/app.py", "import json\nfrom services.orders.catalog import unit_price_cents\n")
        self.assertEqual(self.found(), [("services/billing/app.py", 2, "services.orders.catalog.unit_price_cents", SERVICE_RULE)])

    def test_every_spelling_of_the_import_is_seen(self):
        self.write("services/billing/a.py", "import services.orders.app\n")
        self.write("services/billing/b.py", "from services import orders\n")
        self.write("services/billing/c.py", "from ..orders import catalog\n")
        self.write("services/billing/d.py", "def late():\n    from services.orders import catalog\n")
        self.assertEqual([(file, line) for file, line, _import, _rule in self.found()],
                         [("services/billing/a.py", 1), ("services/billing/b.py", 1),
                          ("services/billing/c.py", 1), ("services/billing/d.py", 2)])

    def test_a_test_file_is_not_exempt(self):
        self.write("services/billing/test_app.py", "from services.orders.app import create_app\n")
        self.assertEqual(len(self.found()), 1)

    def test_shared_code_and_tools_know_no_service(self):
        self.write("shared/bus.py", "from services.billing import ledger\n")
        self.write("tools/schema.py", "import services.orders.catalog\n")
        self.assertEqual([(file, rule) for file, _line, _import, rule in self.found()],
                         [("shared/bus.py", SHARED_RULE), ("tools/schema.py", SHARED_RULE)])

    def test_the_command_exits_1_and_prints_one_line_per_violation(self):
        self.write("services/billing/app.py", "from services.orders import catalog\n")
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = main([self.root])
        self.assertEqual(code, 1)
        self.assertEqual(out.getvalue(), f"services/billing/app.py:1 imports services.orders.catalog: {SERVICE_RULE}\n")

    def test_the_command_can_answer_in_json(self):
        self.write("services/billing/app.py", "from services.orders import catalog\n")
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            main([self.root, "--json"])
        self.assertEqual(json.loads(out.getvalue()), [{"file": "services/billing/app.py", "line": 1,
                                                       "import": "services.orders.catalog", "rule": SERVICE_RULE}])

    def test_a_clean_tree_exits_0(self):
        self.write("services/billing/app.py", "import json\n")
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(main([self.root]), 0)


class RepositoryTest(unittest.TestCase):
    def test_this_repository_crosses_no_boundary(self):
        self.assertEqual(check(REPOSITORY), [])


if __name__ == "__main__":
    unittest.main()
