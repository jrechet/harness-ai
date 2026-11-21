"""Tests of `harness target`: showing by path, clearing, and the warning in assistance mode."""
from __future__ import annotations

import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout

CLI_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, CLI_DIR)
from harness import main as harness_main  # noqa: E402

CONFIG = ".harness/config.json"
AGENTS_ASSISTANCE = "# demo\n\nMode: **assistance**. A human drives every task.\n"
AGENTS_DELEGATION = "# demo\n\nMode: **delegation**. An agent can receive a whole task.\n"


class TargetCommandTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.repo = os.path.realpath(self._tmp.name)
        self._cwd = os.getcwd()
        self.addCleanup(os.chdir, self._cwd)

    def write(self, rel: str, content: str) -> None:
        path = os.path.join(self.repo, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(content)

    def config(self) -> dict:
        with open(os.path.join(self.repo, CONFIG), encoding="utf-8") as fh:
            return json.load(fh)

    def run_target(self, *argv: str) -> tuple[int, str, str]:
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            try:
                code = harness_main(["target", *argv])
            except SystemExit as exc:  # argparse refuses with exit code 2
                code = exc.code
        return code, out.getvalue(), err.getvalue()


class ShowByPathTests(TargetCommandTests):
    def test_a_single_path_shows_the_target_of_that_repository(self):
        self.write(CONFIG, json.dumps({"target_level": 2}))
        code, out, err = self.run_target(self.repo)
        self.assertEqual((code, err), (0, ""))
        self.assertEqual(out.strip(), "target level: 2")

    def test_a_single_path_without_target_says_so_and_writes_nothing(self):
        code, out, _ = self.run_target(self.repo)
        self.assertEqual(code, 0)
        self.assertEqual(out.strip(), "no target level")
        self.assertFalse(os.path.exists(os.path.join(self.repo, ".harness")))

    def test_a_relative_path_is_accepted(self):
        self.write("sub/" + CONFIG, json.dumps({"target_level": 3}))
        os.chdir(self.repo)
        code, out, _ = self.run_target("sub")
        self.assertEqual(code, 0)
        self.assertEqual(out.strip(), "target level: 3")

    def test_no_argument_still_shows_the_target_of_the_current_directory(self):
        self.write(CONFIG, json.dumps({"target_level": 1}))
        os.chdir(self.repo)
        code, out, _ = self.run_target()
        self.assertEqual(code, 0)
        self.assertEqual(out.strip(), "target level: 1")

    def test_what_is_neither_a_level_nor_a_directory_is_refused_in_plain_words(self):
        for bad in ("5", "0", os.path.join(self.repo, "missing")):
            with self.subTest(bad=bad):
                code, out, err = self.run_target(bad)
                self.assertEqual((code, out), (2, ""))
                self.assertNotIn("invalid int value", err)
                self.assertIn("none", err)
                self.assertIn("path", err)

    def test_two_paths_are_refused(self):
        code, _, err = self.run_target(self.repo, self.repo)
        self.assertEqual(code, 2)
        self.assertIn("level", err)


class ClearTests(TargetCommandTests):
    def test_none_removes_the_target_and_keeps_the_other_keys(self):
        self.write(CONFIG, json.dumps({"schema": "harness-config/1", "note": "x", "target_level": 3}))
        code, out, _ = self.run_target("none", self.repo)
        self.assertEqual(code, 0)
        self.assertEqual(self.config(), {"schema": "harness-config/1", "note": "x"})
        self.assertIn("no target level", out)
        code, out, _ = self.run_target(self.repo)
        self.assertEqual(out.strip(), "no target level")

    def test_none_clears_the_current_directory_by_default(self):
        self.write(CONFIG, json.dumps({"target_level": 2}))
        os.chdir(self.repo)
        self.assertEqual(self.run_target("none")[0], 0)
        self.assertNotIn("target_level", self.config())

    def test_none_without_config_creates_no_file(self):
        code, out, _ = self.run_target("none", self.repo)
        self.assertEqual(code, 0)
        self.assertIn("no target level", out)
        self.assertFalse(os.path.exists(os.path.join(self.repo, ".harness")))

    def test_a_target_can_be_set_again_after_a_clear(self):
        self.assertEqual(self.run_target("2", self.repo)[0], 0)
        self.assertEqual(self.run_target("none", self.repo)[0], 0)
        self.assertEqual(self.run_target("3", self.repo)[0], 0)
        self.assertEqual(self.config()["target_level"], 3)


class AssistanceWarningTests(TargetCommandTests):
    def test_level_4_in_assistance_mode_warns_in_one_line_and_is_still_written(self):
        self.write("AGENTS.md", AGENTS_ASSISTANCE)
        code, out, err = self.run_target("4", self.repo)
        self.assertEqual(code, 0)
        self.assertEqual(self.config()["target_level"], 4)
        self.assertIn("target level: 4", out)
        self.assertEqual(len(err.strip().splitlines()), 1)
        self.assertTrue(err.startswith("warning:"))
        self.assertIn("assistance", err)

    def test_level_4_in_delegation_mode_does_not_warn(self):
        self.write("AGENTS.md", AGENTS_DELEGATION)
        code, _, err = self.run_target("4", self.repo)
        self.assertEqual((code, err), (0, ""))

    def test_level_4_without_a_declared_mode_does_not_warn(self):
        code, _, err = self.run_target("4", self.repo)
        self.assertEqual((code, err), (0, ""))

    def test_level_3_in_assistance_mode_does_not_warn(self):
        self.write("AGENTS.md", AGENTS_ASSISTANCE)
        code, _, err = self.run_target("3", self.repo)
        self.assertEqual((code, err), (0, ""))

    def test_showing_a_level_4_target_in_assistance_mode_warns_too(self):
        self.write("AGENTS.md", AGENTS_ASSISTANCE)
        self.write(CONFIG, json.dumps({"target_level": 4}))
        code, out, err = self.run_target(self.repo)
        self.assertEqual(code, 0)
        self.assertEqual(out.strip(), "target level: 4")
        self.assertTrue(err.startswith("warning:"))


if __name__ == "__main__":
    unittest.main()
