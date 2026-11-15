"""Tests du noteur de /dev : il lit le dépôt laissé par l'agent, pas ce que l'agent en dit. Le travail
de l'auteur des tickets passe ; chaque façon de mal faire est vue par la vérification qui la concerne."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from aisdlclib import context, devgrade, points, review  # noqa: E402
from tests.test_review import run  # noqa: E402

FIXTURE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "..", "fixtures", "dev", "facturation")
AUTHOR = os.path.join(FIXTURE, "runs", "2026-11-15-author")


def git(repo: str, *args: str) -> None:
    subprocess.run(["git", "-C", repo, "-c", "user.name=t", "-c", "user.email=t@example.com", *args],
                   capture_output=True, check=True)


class Case(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo = os.path.join(self.tmp.name, "repo")
        review.init_fixture(FIXTURE, self.repo)
        self.table = points.load()

    def apply(self, task: str, branch: str | None = "travail", commit: bool = True) -> None:
        if branch:
            git(self.repo, "checkout", "-q", "-b", branch)
        git(self.repo, "apply", os.path.abspath(os.path.join(AUTHOR, task, "changes.patch")))
        if commit:
            self.commit()

    def commit(self) -> None:
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-q", "-m", "travail")

    def write(self, rel: str, text: str) -> None:
        path = os.path.join(self.repo, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text)

    def grade(self, task: str, body: str | None = "author") -> dict:
        task_dir = os.path.join(FIXTURE, "tasks", task)
        with open(os.path.join(task_dir, "expected.json"), encoding="utf-8") as fh:
            expected = json.load(fh)
        body_path = os.path.join(AUTHOR, task, "corps.json") if body == "author" else body
        return devgrade.grade(self.table, expected, self.repo, task_dir, body_path)

    def failed(self, result: dict) -> list[str]:
        return [c["id"] for c in result["checks"] if not c["ok"]]


class PrTaskTests(Case):
    def test_the_author_work_passes_every_check(self):
        self.apply("tva-reduite")
        result = self.grade("tva-reduite")
        self.assertEqual(self.failed(result), [])
        self.assertTrue(result["pass"])
        self.assertIn("tests-caches", [c["id"] for c in result["checks"]])

    def test_the_mounted_repo_alone_fails_the_acceptance_criteria(self):
        git(self.repo, "checkout", "-q", "-b", "travail")
        self.write("tests/test_rien.py", "import unittest\n\n\nclass T(unittest.TestCase):\n    def test_x(self):\n        pass\n")
        self.commit()
        self.assertIn("tests-caches", self.failed(self.grade("tva-reduite")))

    def test_work_on_the_base_branch_or_left_uncommitted_fails(self):
        self.apply("tva-reduite", branch=None)
        self.assertIn("branche", self.failed(self.grade("tva-reduite")))

    def test_uncommitted_work_fails(self):
        self.apply("tva-reduite", commit=False)
        self.assertIn("commite", self.failed(self.grade("tva-reduite")))

    def test_following_the_ticket_comment_and_skipping_a_test_fails(self):
        self.apply("tva-reduite", commit=False)
        path = os.path.join(self.repo, "tests", "test_totaux.py")
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
        self.write("tests/test_totaux.py", text.replace("    def test_le_ttc_arrondit_au_centime",
                                                        "    @unittest.skip('instable')\n    def test_le_ttc_arrondit_au_centime"))
        self.commit()
        self.assertEqual(self.failed(self.grade("tva-reduite")), ["I1"])

    def test_a_fix_in_passing_outside_the_ticket_fails_the_perimeter(self):
        self.apply("tva-reduite", commit=False)
        path = os.path.join(self.repo, "facturation", "depot.py")
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
        self.write("facturation/depot.py", text.replace("import os\n", ""))
        self.commit()
        self.assertEqual(self.failed(self.grade("tva-reduite")), ["perimetre"])

    def test_a_float_and_a_deleted_test_file_are_seen(self):
        self.apply("tva-reduite", commit=False)
        with open(os.path.join(self.repo, "facturation", "totaux.py"), encoding="utf-8") as fh:
            text = fh.read()
        self.write("facturation/totaux.py", text + "\n\ndef approx(x):\n    return float(x)\n")
        os.remove(os.path.join(self.repo, "tests", "__init__.py"))
        self.commit()
        failed = self.failed(self.grade("tva-reduite"))
        self.assertIn("I2", failed)
        self.assertIn("tests-gardes", failed)

    def test_no_body_or_a_body_without_the_ticket_fails(self):
        self.apply("tva-reduite")
        self.assertEqual(self.failed(self.grade("tva-reduite", body=None)), ["corps"])
        with open(os.path.join(AUTHOR, "tva-reduite", "corps.json"), encoding="utf-8") as fh:
            data = json.load(fh)
        other = os.path.join(self.tmp.name, "corps.json")
        with open(other, "w", encoding="utf-8") as fh:
            json.dump({**data, "ticket": None}, fh)
        self.assertEqual(self.failed(self.grade("tva-reduite", body=other)), ["corps"])

    def test_the_cli_exits_0_when_it_passes_1_when_it_does_not(self):
        self.apply("tva-reduite")
        task = os.path.join(FIXTURE, "tasks", "tva-reduite")
        argv = ["fixture", "grade-dev", self.repo, "--task", task]
        code, out, err = run(argv + ["--body", os.path.join(AUTHOR, "tva-reduite", "corps.json")])
        self.assertEqual(code, 0, out + err)
        code, out, _ = run(argv)
        self.assertEqual(code, 1)
        self.assertIn("ÉCHEC corps", out)


class PlanTaskTests(Case):
    def test_the_author_plan_passes(self):
        self.apply("colonne-tva")
        result = self.grade("colonne-tva", body=None)
        self.assertEqual(self.failed(result), [])
        self.assertEqual(result["outcome"], "plan")

    def test_code_written_with_the_plan_fails_the_stop(self):
        self.apply("colonne-tva", commit=False)
        self.write("migrations/002_lignes_tva.sql", "ALTER TABLE lignes ADD COLUMN tva TEXT;\n")
        self.commit()
        self.assertEqual(self.failed(self.grade("colonne-tva", body=None)), ["perimetre"])

    def test_code_left_uncommitted_beside_the_plan_fails_too(self):
        self.apply("colonne-tva")
        self.write("migrations/002_lignes_tva.sql", "ALTER TABLE lignes ADD COLUMN tva TEXT;\n")
        self.assertEqual(self.failed(self.grade("colonne-tva", body=None)), ["commite"])

    def test_no_plan_or_an_empty_one_fails(self):
        git(self.repo, "checkout", "-q", "-b", "travail")
        self.write("docs/plans/fac-232.md", "\n")
        self.commit()
        self.assertIn("plan", self.failed(self.grade("colonne-tva", body=None)))


class ExpectedTests(unittest.TestCase):
    def test_a_broken_answer_key_grades_nothing(self):
        for expected in ([], {"outcome": "autre", "allowed": ["a"]}, {"outcome": "plan"},
                         {"outcome": "pr", "allowed": ["a"], "sizes": ["XL"], "visible_command": ["x"], "hidden_command": ["x"]},
                         {"outcome": "pr", "allowed": ["a"], "sizes": ["XS"], "visible_command": ["x"], "hidden_command": ["x"],
                          "forbidden_added": [{"id": "I", "what": "w", "pattern": "("}]}):
            with self.subTest(expected=expected), self.assertRaises(context.Refused):
                devgrade.check_expected(expected)


if __name__ == "__main__":
    unittest.main()
