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

    def test_a_date_older_than_the_latest_row_is_refused(self):
        stale = DOC.replace("| done | 2026-11-15 |", "| done | 2026-11-19 |")
        errors = progress.parse(stale)[1]
        self.assertTrue(any("2026-11-15" in e and "2026-11-19" in e and "A1" in e for e in errors), errors)
        stale_fr = DOC_FR.replace("| à faire | 2026-11-15 |", "| à faire | 2026-11-19 |")
        self.assertTrue(any("2026-11-19" in e and "A3" in e for e in progress.parse(stale_fr)[1]))

    def test_a_date_equal_to_or_later_than_the_latest_row_passes(self):
        current = DOC.replace("| done | 2026-11-15 |", "| done | 2026-11-19 |")
        for date in ("2026-11-19", "2026-12-01"):
            with self.subTest(date=date):
                self.assertEqual(progress.parse(current.replace("Last updated: 2026-11-15", f"Last updated: {date}"))[1], [])

    def test_the_since_column_is_found_by_its_header_and_a_date_elsewhere_is_not_one(self):
        elsewhere = DOC.replace("| PR 1 |", "| PR 1, replayed on 2026-11-19 |").replace(
            "| The grader |", "| The grader, due 2026-12-24 |")
        self.assertEqual(progress.parse(elsewhere)[1], [])
        moved = DOC.replace("| # | Topic | State | Since | Evidence |", "| # | Topic | State | Evidence | Since |").replace(
            "| done | 2026-11-15 | PR 1 |", "| done | PR 1 | 2026-11-19 |")
        self.assertTrue(any("2026-11-19" in e for e in progress.parse(moved)[1]), progress.parse(moved)[1])

    def test_a_month_or_a_word_in_the_since_column_is_not_compared(self):
        loose = DOC.replace("| done | 2026-11-15 |", "| done | 2026-12 |").replace("| in progress | 2026-11-15 |",
                                                                                 "| in progress | soon |")
        self.assertEqual(progress.parse(loose)[1], [])


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

    TODAY = "2026-11-15"  # the day the plan of these tests is dated: a change made that day needs no new date
    NEXT_DAY = "2026-11-16"

    def check(self, today: str | None = None) -> list[str]:
        return progress.check(self.repo, base="main", today=today or self.TODAY)

    def redate(self, text: str, date: str) -> str:
        return text.replace(f": {self.TODAY}", f": {date}", 1)

    def test_a_plan_changed_on_a_later_day_without_moving_its_date_is_refused(self):
        git(self.repo, "checkout", "-q", "-b", "pr")
        self.write(self.PLAN, self.TEXT.replace(*self.STATE_PAIR))
        errors = self.check(today=self.NEXT_DAY)
        self.assertTrue(any(self.PLAN in e and self.TODAY in e and "did not move" in e for e in errors), errors)
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-q", "-m", "plan")
        self.assertTrue(any("did not move" in e for e in self.check(today=self.NEXT_DAY)))

    def test_a_plan_changed_on_a_later_day_with_its_date_moved_passes(self):
        git(self.repo, "checkout", "-q", "-b", "pr")
        self.write(self.PLAN, self.redate(self.TEXT.replace(*self.STATE_PAIR), self.NEXT_DAY))
        self.assertEqual(self.check(today=self.NEXT_DAY), [])
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-q", "-m", "plan")
        self.assertEqual(self.check(today=self.NEXT_DAY), [])

    def test_an_untouched_plan_keeps_its_date_on_a_later_day(self):
        self.assertEqual(self.check(today=self.NEXT_DAY), [])

    def test_a_new_plan_has_no_former_date_to_move(self):
        git(self.repo, "checkout", "-q", "-b", "pr")
        git(self.repo, "rm", "-q", self.PLAN)
        git(self.repo, "commit", "-q", "-m", "no plan")
        git(self.repo, "checkout", "-q", "-b", "pr2")
        self.write(self.PLAN, self.TEXT)
        self.assertEqual(progress.check(self.repo, base="pr", today=self.NEXT_DAY), [])

    def test_the_date_is_not_compared_when_the_base_is_unknown(self):
        self.write(self.PLAN, self.TEXT.replace(*self.STATE_PAIR))
        self.assertEqual(progress.check(self.repo, base="origin/missing", today=self.NEXT_DAY), [])

    def test_the_command_refuses_a_plan_whose_date_did_not_move(self):
        self.write(self.PLAN, self.TEXT.replace(*self.STATE_PAIR))  # the real day is later than the plan's date
        code, err = self.run_cli(["check", self.repo, "--base", "main"])
        self.assertEqual(code, 2)
        self.assertIn("did not move", err)

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

    def test_renaming_the_plan_on_a_later_day_without_moving_its_date_is_refused(self):
        git(self.repo, "checkout", "-q", "-b", "pr")
        git(self.repo, "mv", self.PLAN, "docs/capabilities.md")
        self.write("docs/capabilities.md", DOC)
        self.assertTrue(any("did not move" in e for e in self.check(today=self.NEXT_DAY)))


if __name__ == "__main__":
    unittest.main()
