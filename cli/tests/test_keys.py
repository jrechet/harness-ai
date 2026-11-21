"""Tests of the answer-key guard: a change does not touch both the paper and its answer key."""
from __future__ import annotations

import contextlib
import io
import os
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import harness  # noqa: E402
from harnesslib import keys  # noqa: E402

PLAN = """# Capabilities

Last updated: 2026-11-15

## Progress plan

| # | Topic | State | Since | Evidence |
|---|---|---|---|---|
| A1 | The grader | done | 2026-11-15 | PR 1 |
{rows}
## Other section
"""


def git(repo: str, *args: str) -> None:
    subprocess.run(["git", "-C", repo, "-c", "user.name=t", "-c", "user.email=t@example.com", *args],
                   capture_output=True, check=True)


def write(repo: str, path: str, text: str) -> None:
    full = os.path.join(repo, path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w", encoding="utf-8") as fh:
        fh.write(text)


class ClassifyTests(unittest.TestCase):
    def test_answer_keys_and_graders_are_recognised(self):
        for path in ("fixtures/repos/go-hexa/expected.json", "fixtures/design/release-skill/traps.md",
                     "fixtures/dev/billing/tasks/t1/task.md", "fixtures/dev/billing/tasks/t1/check/test_x.py",
                     "cli/harnesslib/fixtures.py", "plugins/ai-sdlc/cli/aisdlclib/devgrade.py", "tools/grade.py"):
            self.assertTrue(keys.is_key(path), path)

    def test_other_files_are_not_answer_keys(self):
        for path in ("expected.json", "docs/traps.md", "fixtures/repos/go-hexa/owner.md", "cli/harnesslib/bench.py",
                     "plugins/ai-sdlc/cli/tests/test_devgrade.py", "fixtures/repos/go-hexa/runs/r1/expected.json",
                     "cli/harnesslib/upgrade.py.txt"):
            self.assertFalse(keys.is_key(path), path)

    def test_skills_runs_and_results_are_the_graded_side(self):
        for path in ("skills/harness-init/SKILL.md", "plugins/ai-sdlc/skills/dev/SKILL.md",
                     "fixtures/repos/go-hexa/runs/2026-11-15-blind/RUN.md", "fixtures/results.jsonl"):
            self.assertTrue(keys.is_graded(path), path)

    def test_other_files_are_not_the_graded_side(self):
        for path in ("cli/harnesslib/bench.py", "docs/skills/notes.md", "fixtures/repos/go-hexa/expected.json",
                     "plugins/ai-sdlc/cli/ai_sdlc.py", "fixtures/runs.md"):
            self.assertFalse(keys.is_graded(path), path)


class GuardTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.repo = tmp.name
        git(self.repo, "init", "-q", "-b", "main")
        write(self.repo, "docs/capabilities.md", PLAN.format(rows=""))
        write(self.repo, "fixtures/repos/demo/expected.json", "{}\n")
        write(self.repo, "skills/harness-init/SKILL.md", "v1\n")
        write(self.repo, "cli/harnesslib/fixtures.py", "X = 1\n")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-q", "-m", "base")
        git(self.repo, "checkout", "-q", "-b", "work")

    def commit(self, message: str = "change") -> None:
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-q", "-m", message)

    def test_an_answer_key_changed_alone_is_allowed(self):
        write(self.repo, "fixtures/repos/demo/expected.json", '{"a": 1}\n')
        write(self.repo, "cli/harnesslib/fixtures.py", "X = 2\n")
        self.commit()
        self.assertEqual(keys.check(self.repo, "main"), [])

    def test_a_skill_changed_alone_is_allowed(self):
        write(self.repo, "skills/harness-init/SKILL.md", "v2\n")
        write(self.repo, "fixtures/repos/demo/runs/r1/RUN.md", "run\n")
        self.commit()
        self.assertEqual(keys.check(self.repo, "main"), [])

    def test_an_answer_key_changed_with_a_skill_is_refused(self):
        write(self.repo, "fixtures/repos/demo/expected.json", '{"a": 1}\n')
        write(self.repo, "skills/harness-init/SKILL.md", "v2\n")
        self.commit()
        errors = keys.check(self.repo, "main")
        self.assertEqual(len(errors), 1)
        self.assertIn("fixtures/repos/demo/expected.json", errors[0])
        self.assertIn("skills/harness-init/SKILL.md", errors[0])
        self.assertIn(keys.MARKER, errors[0])

    def test_the_grader_changed_with_a_run_is_refused_across_commits(self):
        write(self.repo, "cli/harnesslib/fixtures.py", "X = 2\n")
        self.commit("grader")
        write(self.repo, "fixtures/repos/demo/runs/r1/RUN.md", "run\n")
        self.commit("run")
        self.assertEqual(len(keys.check(self.repo, "main")), 1)

    def test_a_new_task_with_the_results_file_is_refused(self):
        write(self.repo, "fixtures/repos/demo/tasks/t1/task.md", "task\n")
        write(self.repo, "fixtures/results.jsonl", "{}\n")
        self.commit()
        self.assertEqual(len(keys.check(self.repo, "main")), 1)

    def test_a_deleted_answer_key_with_a_skill_is_refused(self):
        os.remove(os.path.join(self.repo, "fixtures/repos/demo/expected.json"))
        write(self.repo, "plugins/ai-sdlc/skills/dev/SKILL.md", "v1\n")
        self.commit()
        self.assertEqual(len(keys.check(self.repo, "main")), 1)

    def test_uncommitted_changes_count(self):
        write(self.repo, "fixtures/repos/demo/expected.json", '{"a": 1}\n')
        write(self.repo, "skills/harness-init/SKILL.md", "v2\n")
        self.assertEqual(len(keys.check(self.repo, "main")), 1)

    def test_the_marker_on_a_row_of_the_change_allows_it(self):
        write(self.repo, "fixtures/repos/demo/expected.json", '{"a": 1}\n')
        write(self.repo, "skills/harness-init/SKILL.md", "v2\n")
        row = f"| A2 | Fix the answer key of demo | done | 2026-11-21 | {keys.MARKER}, 2026-11-21 |\n"
        write(self.repo, "docs/capabilities.md", PLAN.format(rows=row))
        self.commit()
        self.assertEqual(keys.check(self.repo, "main"), [])

    def test_a_marker_already_on_the_base_does_not_allow_a_later_change(self):
        git(self.repo, "checkout", "-q", "main")
        row = f"| A2 | Fix the answer key of demo | done | 2026-11-21 | {keys.MARKER} |\n"
        write(self.repo, "docs/capabilities.md", PLAN.format(rows=row))
        self.commit("an earlier agreed change")
        git(self.repo, "checkout", "-q", "-b", "later")
        write(self.repo, "fixtures/repos/demo/expected.json", '{"a": 1}\n')
        write(self.repo, "skills/harness-init/SKILL.md", "v2\n")
        self.commit()
        self.assertEqual(len(keys.check(self.repo, "main")), 1)

    def test_a_marker_outside_the_plan_rows_does_not_allow_it(self):
        write(self.repo, "fixtures/repos/demo/expected.json", '{"a": 1}\n')
        write(self.repo, "skills/harness-init/SKILL.md", "v2\n")
        write(self.repo, "docs/capabilities.md", PLAN.format(rows="") + f"\n{keys.MARKER}\n")
        self.commit()
        self.assertEqual(len(keys.check(self.repo, "main")), 1)

    def test_an_unknown_base_is_an_error_not_a_pass(self):
        write(self.repo, "fixtures/repos/demo/expected.json", '{"a": 1}\n')
        write(self.repo, "skills/harness-init/SKILL.md", "v2\n")
        self.commit()
        errors = keys.check(self.repo, "origin/absent")
        self.assertEqual(len(errors), 1)
        self.assertIn("origin/absent", errors[0])

    def test_the_command_exits_with_2_when_refused_and_0_when_allowed(self):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            self.assertEqual(harness.main(["keys", "check", self.repo, "--base", "main"]), 0)
        write(self.repo, "fixtures/repos/demo/expected.json", '{"a": 1}\n')
        write(self.repo, "skills/harness-init/SKILL.md", "v2\n")
        self.commit()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            self.assertEqual(harness.main(["keys", "check", self.repo, "--base", "main"]), 2)
        self.assertIn("fixtures/repos/demo/expected.json", err.getvalue())


if __name__ == "__main__":
    unittest.main()
