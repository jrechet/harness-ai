"""Tests of the file `harness status` writes: `.harness/state.json` is committed, so it carries no
path of the machine that wrote it and does not move when only the day changed."""
from __future__ import annotations

import io
import json
import os
import shutil
import sys
import tempfile
import unittest
from contextlib import redirect_stdout

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from harnesslib import status  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

AGENTS = """# demo — instructions for agents

Mode: **delegation**. An agent can receive a whole task.

## What this repo does
A billing API.

## Rules
- HTTP calls go through `src/http`. Why: centralised retries. Enforced by: `eslint/no-raw-fetch`

## Forbidden
- Never force push.
"""


class StateFileTests(unittest.TestCase):
    def setUp(self):
        self.repo = os.path.realpath(tempfile.mkdtemp(prefix="harness-state-"))
        self.addCleanup(shutil.rmtree, self.repo, ignore_errors=True)
        with open(os.path.join(self.repo, "AGENTS.md"), "w", encoding="utf-8") as fh:
            fh.write(AGENTS)
        self.path = os.path.join(self.repo, ".harness", "state.json")

    def run_status(self, *args: str) -> str:
        out = io.StringIO()
        with redirect_stdout(out):
            self.assertEqual(status.main([self.repo, *args]), 0)
        return out.getvalue()

    def read(self) -> str:
        with open(self.path, encoding="utf-8") as fh:
            return fh.read()

    def test_the_written_file_holds_no_absolute_path(self):
        self.run_status("--today", "2026-11-09")
        text = self.read()
        self.assertNotIn(self.repo, text)
        self.assertNotIn(os.path.dirname(self.repo), text)
        state = json.loads(text)
        self.assertEqual(state["repo"], ".")
        self.assertEqual(state["facts"]["repo"], ".")

    def test_the_file_is_the_same_wherever_the_repository_is_checked_out(self):
        self.run_status("--today", "2026-11-09")
        first = self.read()
        elsewhere = os.path.realpath(tempfile.mkdtemp(prefix="harness-state-other-"))
        self.addCleanup(shutil.rmtree, elsewhere, ignore_errors=True)
        shutil.copy(os.path.join(self.repo, "AGENTS.md"), os.path.join(elsewhere, "AGENTS.md"))
        with redirect_stdout(io.StringIO()):
            self.assertEqual(status.main([elsewhere, "--today", "2026-11-09"]), 0)
        with open(os.path.join(elsewhere, ".harness", "state.json"), encoding="utf-8") as fh:
            self.assertEqual(fh.read(), first)

    def test_what_is_printed_still_names_the_repository(self):
        printed = json.loads(self.run_status("--format", "json", "--today", "2026-11-09"))
        self.assertEqual(printed["repo"], self.repo)
        self.assertIn(self.repo, self.run_status("--today", "2026-11-09"))

    def test_a_date_only_change_does_not_rewrite_the_file(self):
        self.run_status("--today", "2026-11-09")
        first = self.read()
        os.utime(self.path, ns=(1, 1))
        self.run_status("--today", "2026-11-10")
        self.assertEqual(self.read(), first)
        self.assertEqual(os.stat(self.path).st_mtime_ns, 1)
        self.assertEqual(json.loads(first)["date"], "2026-11-09")

    def test_the_printed_state_carries_today_even_when_the_file_did_not_move(self):
        self.run_status("--today", "2026-11-09")
        printed = json.loads(self.run_status("--format", "json", "--today", "2026-11-10"))
        self.assertEqual(printed["date"], "2026-11-10")

    def test_a_real_change_rewrites_the_file_with_the_new_date(self):
        self.run_status("--today", "2026-11-09")
        with open(os.path.join(self.repo, "AGENTS.md"), "a", encoding="utf-8") as fh:
            fh.write("- Never commit a secret.\n")
        self.run_status("--today", "2026-11-10")
        state = json.loads(self.read())
        self.assertEqual(state["date"], "2026-11-10")
        self.assertEqual(state["facts"]["date"], "2026-11-10")

    def test_a_file_written_with_an_absolute_path_is_replaced(self):
        self.run_status("--today", "2026-11-09")
        old = json.loads(self.read())
        old["repo"] = old["facts"]["repo"] = self.repo
        with open(self.path, "w", encoding="utf-8") as fh:
            json.dump(old, fh, ensure_ascii=False, indent=2)
        self.run_status("--today", "2026-11-10")
        self.assertNotIn(self.repo, self.read())

    def test_an_unreadable_previous_file_is_replaced(self):
        os.makedirs(os.path.dirname(self.path))
        with open(self.path, "w", encoding="utf-8") as fh:
            fh.write("{not json")
        self.run_status("--today", "2026-11-09")
        self.assertEqual(json.loads(self.read())["repo"], ".")


class OwnStateFileTests(unittest.TestCase):
    def test_this_repository_s_committed_state_holds_no_local_path(self):
        with open(os.path.join(ROOT, ".harness", "state.json"), encoding="utf-8") as fh:
            text = fh.read()
        self.assertNotIn("/private/tmp", text)
        self.assertNotIn("/Users/", text)
        self.assertEqual(json.loads(text)["repo"], ".")


if __name__ == "__main__":
    unittest.main()
