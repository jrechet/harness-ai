"""Tests of the progress plan guardrail: its shape, and the fact that it follows every change."""
from __future__ import annotations

import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from harnesslib import progress  # noqa: E402

DOC = """# Capabilities

Last updated: 2026-11-15

## Progress plan

| # | Topic | State | Since | Evidence |
|---|---|---|---|---|
| A1 | The grader | done | 2026-11-15 | PR 1 |
| A2 | The fixture | in progress | 2026-11-15 | |

## Other section
| Z9 | outside the plan | anything |
"""

# The same plan as written before 2026-11-16: still read until it is translated.
DOC_FR = """# Capacités

Dernière mise à jour : 2026-11-15

## Plan d'avancement

| # | Sujet | État | Depuis | Preuve |
|---|---|---|---|---|
| A1 | Le noteur | fait | 2026-11-15 | PR 1 |
| A2 | La fixture | en cours | 2026-11-15 | |
| A3 | Le banc | à faire | 2026-11-15 | |
| A4 | La page | en attente | 2026-11-15 | |
| A5 | L'ancien noteur | écarté | 2026-11-15 | |

## Autre section
| Z9 | hors plan | n'importe quoi |
"""


def git(repo: str, *args: str) -> None:
    subprocess.run(["git", "-C", repo, "-c", "user.name=t", "-c", "user.email=t@example.com", *args],
                   capture_output=True, check=True)


class ParseTests(unittest.TestCase):
    def test_a_well_formed_plan_has_its_rows_and_no_error(self):
        rows, errors = progress.parse(DOC)
        self.assertEqual([(r["id"], r["state"]) for r in rows], [("A1", "done"), ("A2", "in progress")])
        self.assertEqual(errors, [])

    def test_a_plan_still_in_french_is_read_with_its_heading_date_and_states(self):
        rows, errors = progress.parse(DOC_FR)
        self.assertEqual([r["state"] for r in rows], ["fait", "en cours", "à faire", "en attente", "écarté"])
        self.assertEqual(errors, [])

    def test_each_defect_of_form_is_named(self):
        cases = {"Last updated": DOC.replace("Last updated: 2026-11-15", ""),
                 "section": DOC.replace("## Progress plan", "## Plan"),
                 "unknown": DOC.replace("| in progress |", "| soon |"),
                 "duplicate": DOC.replace("| A2 |", "| A1 |"),
                 "no row": DOC.replace("| A1 |", "| a |").replace("| A2 |", "| b |")}
        for needle, text in cases.items():
            with self.subTest(needle=needle):
                self.assertTrue(any(needle in e for e in progress.parse(text)[1]), progress.parse(text)[1])


class CheckTests(unittest.TestCase):
    PLAN = "docs/capabilities.md"
    TEXT = DOC
    STATE_PAIR = ("| in progress |", "| done |")

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo = self.tmp.name
        git(self.repo, "init", "-q", "-b", "main")
        self.write(self.PLAN, self.TEXT)
        self.write("a.py", "x\n")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-q", "-m", "init")

    def write(self, rel: str, text: str) -> None:
        path = os.path.join(self.repo, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text)

    def check(self) -> list[str]:
        return progress.check(self.repo, base="main")

    def test_nothing_changed_is_fine(self):
        self.assertEqual(self.check(), [])

    def test_a_change_without_the_plan_is_refused_committed_or_not(self):
        self.write("b.py", "x\n")
        self.assertTrue(any("does not move" in e for e in self.check()))
        git(self.repo, "checkout", "-q", "-b", "pr")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-q", "-m", "b")
        self.assertTrue(any("does not move" in e for e in self.check()))

    def test_a_change_with_the_plan_passes(self):
        git(self.repo, "checkout", "-q", "-b", "pr")
        self.write("b.py", "x\n")
        self.write(self.PLAN, self.TEXT.replace(*self.STATE_PAIR))
        self.assertEqual(self.check(), [])
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-q", "-m", "b")
        self.assertEqual(self.check(), [])

    def test_a_broken_plan_is_refused_even_without_change(self):
        self.write(self.PLAN, self.TEXT.replace(self.STATE_PAIR[0], "| meh |"))
        self.assertTrue(any("unknown" in e for e in self.check()))

    def test_a_missing_plan_is_refused(self):
        os.remove(os.path.join(self.repo, self.PLAN))
        self.assertTrue(any("not found" in e for e in self.check()))

    def test_an_unknown_base_still_looks_at_the_working_tree(self):
        self.write("b.py", "x\n")
        self.assertTrue(progress.check(self.repo, base="origin/missing"))

    def run_cli(self, argv: list[str], stdin: str = "") -> tuple[int, str]:
        err = io.StringIO()
        old = sys.stdin
        sys.stdin = io.StringIO(stdin)
        try:
            with contextlib.redirect_stderr(err), contextlib.redirect_stdout(io.StringIO()):
                code = progress.main(argv)
        finally:
            sys.stdin = old
        return code, err.getvalue()

    def test_the_hook_blocks_once_then_lets_go(self):
        self.write("b.py", "x\n")
        argv = ["check", self.repo, "--base", "main", "--hook"]
        code, err = self.run_cli(argv, json.dumps({"stop_hook_active": False}))
        self.assertEqual(code, 2)
        self.assertIn(self.PLAN, err)
        self.assertEqual(self.run_cli(argv, json.dumps({"stop_hook_active": True}))[0], 0)
        self.assertEqual(self.run_cli(argv, "not json")[0], 2)

    def test_the_reminder_names_the_document(self):
        out = io.StringIO()
        old = os.getcwd()
        os.chdir(self.repo)
        try:
            with contextlib.redirect_stdout(out):
                self.assertEqual(progress.main(["remind"]), 0)
        finally:
            os.chdir(old)
        self.assertIn(self.PLAN, out.getvalue())


class FrenchPlanCheckTests(CheckTests):
    """The same checks on a repository whose plan is still the French `docs/capacites.md`."""
    PLAN = "docs/capacites.md"
    TEXT = DOC_FR
    STATE_PAIR = ("| en cours |", "| fait |")

    def test_renaming_the_plan_to_english_is_a_change_that_follows_itself(self):
        git(self.repo, "checkout", "-q", "-b", "pr")
        git(self.repo, "mv", self.PLAN, "docs/capabilities.md")
        self.write("docs/capabilities.md", DOC)
        self.write("b.py", "x\n")
        self.assertEqual(progress.default_doc(self.repo), "docs/capabilities.md")
        self.assertEqual(self.check(), [])


if __name__ == "__main__":
    unittest.main()
