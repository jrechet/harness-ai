"""Tests du garde-fou du plan d'avancement : sa forme, et le fait qu'il suive tout changement."""
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

DOC = """# Capacités

Dernière mise à jour : 2026-11-15

## Plan d'avancement

| # | Sujet | État | Depuis | Preuve |
|---|---|---|---|---|
| A1 | Le noteur | fait | 2026-11-15 | PR 1 |
| A2 | La fixture | en cours | 2026-11-15 | |

## Autre section
| Z9 | hors plan | n'importe quoi |
"""


def git(repo: str, *args: str) -> None:
    subprocess.run(["git", "-C", repo, "-c", "user.name=t", "-c", "user.email=t@example.com", *args],
                   capture_output=True, check=True)


class ParseTests(unittest.TestCase):
    def test_a_well_formed_plan_has_its_rows_and_no_error(self):
        rows, errors = progress.parse(DOC)
        self.assertEqual([(r["id"], r["state"]) for r in rows], [("A1", "fait"), ("A2", "en cours")])
        self.assertEqual(errors, [])

    def test_each_defect_of_form_is_named(self):
        cases = {"Dernière mise à jour": DOC.replace("Dernière mise à jour : 2026-11-15", ""),
                 "section": DOC.replace("## Plan d'avancement", "## Plan"),
                 "inconnu": DOC.replace("| en cours |", "| bientôt |"),
                 "en double": DOC.replace("| A2 |", "| A1 |"),
                 "aucune ligne": DOC.replace("| A1 |", "| a |").replace("| A2 |", "| b |")}
        for needle, text in cases.items():
            with self.subTest(needle=needle):
                self.assertTrue(any(needle in e for e in progress.parse(text)[1]), progress.parse(text)[1])


class CheckTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo = self.tmp.name
        git(self.repo, "init", "-q", "-b", "main")
        self.write("docs/capacites.md", DOC)
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
        self.assertTrue(any("ne bouge pas" in e for e in self.check()))
        git(self.repo, "checkout", "-q", "-b", "pr")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-q", "-m", "b")
        self.assertTrue(any("ne bouge pas" in e for e in self.check()))

    def test_a_change_with_the_plan_passes(self):
        git(self.repo, "checkout", "-q", "-b", "pr")
        self.write("b.py", "x\n")
        self.write("docs/capacites.md", DOC.replace("| en cours |", "| fait |"))
        self.assertEqual(self.check(), [])
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-q", "-m", "b")
        self.assertEqual(self.check(), [])

    def test_a_broken_plan_is_refused_even_without_change(self):
        self.write("docs/capacites.md", DOC.replace("| en cours |", "| bof |"))
        self.assertTrue(any("inconnu" in e for e in self.check()))

    def test_a_missing_plan_is_refused(self):
        os.remove(os.path.join(self.repo, "docs/capacites.md"))
        self.assertTrue(any("introuvable" in e for e in self.check()))

    def test_an_unknown_base_still_looks_at_the_working_tree(self):
        self.write("b.py", "x\n")
        self.assertTrue(progress.check(self.repo, base="origin/absente"))

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
        self.assertIn("docs/capacites.md", err)
        self.assertEqual(self.run_cli(argv, json.dumps({"stop_hook_active": True}))[0], 0)
        self.assertEqual(self.run_cli(argv, "pas du json")[0], 2)

    def test_the_reminder_names_the_document(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(progress.main(["remind"]), 0)
        self.assertIn("docs/capacites.md", out.getvalue())


if __name__ == "__main__":
    unittest.main()
