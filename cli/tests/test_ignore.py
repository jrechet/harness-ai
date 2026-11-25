"""Tests of `harness ignore`: the owner sets a check of the ladder aside, the choice is written in
`.harness/config.json`, and from then on the level is reached without it. A check set aside is never
shown as passed: the state, the map, the page and the medals say it was set aside, and why."""
from __future__ import annotations

import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from datetime import date

CLI_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, CLI_DIR)
from harness import main as harness_main  # noqa: E402
from harnesslib import facts, maturity, medals, page  # noqa: E402

CONFIG = ".harness/config.json"
TODAY = date(2026, 11, 25)
# Level 1 whole, except the Forbidden section.
AGENTS_NO_FORBIDDEN = "# demo\n\nMode: **assistance**. A human drives every task.\n\n## Rules\n- Tests pass.\n"
REASON = "we keep forbidden actions in the permissions"


class IgnoreTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.repo = os.path.realpath(self._tmp.name)
        self.write("AGENTS.md", AGENTS_NO_FORBIDDEN)

    def write(self, rel: str, content: str) -> None:
        path = os.path.join(self.repo, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(content)

    def config(self) -> dict:
        with open(os.path.join(self.repo, CONFIG), encoding="utf-8") as fh:
            return json.load(fh)

    def run_cli(self, *argv: str) -> tuple[int, str, str]:
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            try:
                code = harness_main(list(argv))
            except SystemExit as exc:  # argparse refuses with exit code 2
                code = exc.code
        return code, out.getvalue(), err.getvalue()

    def state(self) -> dict:
        return maturity.evaluate(facts.collect(self.repo, today=TODAY))

    def set_aside(self, check: str = "L1.forbidden", reason: str = REASON) -> None:
        self.write(CONFIG, json.dumps({"ignored_checks": {check: {"reason": reason, "date": "2026-11-25"}}}))


class EvaluateTests(IgnoreTests):
    def test_without_the_choice_the_level_is_not_reached(self):
        self.assertEqual(self.state()["level"]["reached"], 0)

    def test_a_check_set_aside_no_longer_holds_the_level_back(self):
        self.set_aside()
        state = self.state()
        self.assertEqual(state["level"]["reached"], 1)
        check = next(c for c in state["levels"][1]["checks"] if c["id"] == "L1.forbidden")
        self.assertFalse(check["passed"])                  # measured as it is: never shown as passed
        self.assertTrue(check["ignored"])
        self.assertEqual(check["reason"], REASON)
        self.assertIsNone(check["next_action"])
        self.assertEqual(state["levels"][1]["ignored_checks"], 1)
        self.assertEqual(state["levels"][1]["passed_checks"], 4)
        self.assertEqual([i["id"] for i in state["ignored"]], ["L1.forbidden"])

    def test_the_next_actions_skip_it_and_move_to_the_next_level(self):
        self.set_aside()
        state = self.state()
        self.assertTrue(state["next_actions"])
        self.assertNotIn("Forbidden", " ".join(state["next_actions"]))
        self.assertEqual(state["level"]["next"], 2)

    def test_a_check_set_aside_that_passes_is_simply_passed(self):
        self.set_aside("L1.mode")
        check = next(c for c in self.state()["levels"][1]["checks"] if c["id"] == "L1.mode")
        self.assertTrue(check["passed"])
        self.assertFalse(check.get("ignored"))

    def test_the_instruction_file_itself_cannot_be_set_aside(self):
        os.remove(os.path.join(self.repo, "AGENTS.md"))
        self.set_aside("L1.source")
        state = self.state()
        self.assertEqual(state["level"]["reached"], 0)
        self.assertEqual(state["ignored"], [])

    def test_an_unknown_id_or_a_malformed_entry_in_the_file_is_left_aside(self):
        self.write(CONFIG, json.dumps({"ignored_checks": {"L9.nope": {"reason": "x"}, "L1.forbidden": "yes"}}))
        state = self.state()
        self.assertEqual(state["level"]["reached"], 0)
        self.assertEqual(state["ignored"], [])

    def test_a_malformed_block_does_not_break_status(self):
        self.write(CONFIG, json.dumps({"ignored_checks": ["L1.forbidden"]}))
        self.assertEqual(self.state()["level"]["reached"], 0)


class RenderTests(IgnoreTests):
    def test_the_state_says_set_aside_and_why_and_never_ticks_the_box(self):
        self.set_aside()
        out = maturity.render_markdown(self.state())
        self.assertIn("✓ Level 1", out)
        self.assertIn("(4/5, 1 set aside)", out)
        self.assertIn(f"- [~] A \"Forbidden\" section says what an agent never does → set aside by the owner: {REASON}", out)
        self.assertNotIn("- [x] A \"Forbidden\"", out)

    def test_the_map_says_what_was_set_aside_and_does_not_ask_for_it(self):
        self.set_aside()
        out = maturity.render_map(self.state())
        self.assertIn("1 Framed", out)
        self.assertIn("(1 set aside)   ← you are here", out)
        self.assertIn("Set aside by you (not counted, not proposed again):", out)
        self.assertIn(f"- {maturity.CHECK_PLAIN['L1.forbidden'][0]} ({REASON})", out)
        needs = out.split("still needs:")[1].split("Set aside by you")[0]
        self.assertNotIn(maturity.CHECK_PLAIN["L1.forbidden"][0], needs)

    def test_a_level_blocked_only_by_a_set_aside_check_shows_no_step_for_it_on_the_page(self):
        self.set_aside()
        steps = page._steps(self.state())
        self.assertNotIn(maturity.CHECK_PLAIN["L1.forbidden"][0], [s["missing"] for s in steps])

    def test_the_medal_follows_the_level_and_its_line_says_set_aside(self):
        self.set_aside()
        evaluated = medals.evaluate_repo(self.repo, today=TODAY)
        success = next(s for s in evaluated["successes"] if s["id"] == "L1.forbidden")
        self.assertTrue(success["passed"])
        self.assertIn("set aside", success["evidence"])
        self.assertGreaterEqual(medals.build(evaluated)["medal"]["rank"], 1)


class CommandTests(IgnoreTests):
    def test_setting_a_check_aside_writes_it_with_its_reason_and_the_day(self):
        self.write(CONFIG, json.dumps({"schema": "harness-config/1", "target_level": 2}))
        code, out, err = self.run_cli("ignore", "L1.forbidden", "--reason", REASON, "--repo", self.repo)
        self.assertEqual((code, err), (0, ""))
        config = self.config()
        self.assertEqual(config["target_level"], 2)                 # the rest of the file is kept
        entry = config["ignored_checks"]["L1.forbidden"]
        self.assertEqual(entry["reason"], REASON)
        self.assertRegex(entry["date"], r"^\d{4}-\d{2}-\d{2}$")
        self.assertIn("set aside", out)
        self.assertEqual(self.state()["level"]["reached"], 1)

    def test_a_reason_is_required(self):
        code, _, err = self.run_cli("ignore", "L1.forbidden", "--repo", self.repo)
        self.assertEqual(code, 2)
        self.assertIn("--reason", err)
        code, _, _ = self.run_cli("ignore", "L1.forbidden", "--reason", "  ", "--repo", self.repo)
        self.assertEqual(code, 2)
        self.assertFalse(os.path.exists(os.path.join(self.repo, CONFIG)))

    def test_an_unknown_check_is_refused_with_the_known_ones(self):
        code, _, err = self.run_cli("ignore", "L1.nope", "--reason", REASON, "--repo", self.repo)
        self.assertEqual(code, 2)
        self.assertIn("L1.forbidden", err)

    def test_the_instruction_file_check_is_refused(self):
        code, _, err = self.run_cli("ignore", "L1.source", "--reason", REASON, "--repo", self.repo)
        self.assertEqual(code, 2)
        self.assertIn("cannot be set aside", err)

    def test_restoring_takes_it_back_and_keeps_the_rest(self):
        self.write(CONFIG, json.dumps({"target_level": 2, "ignored_checks": {
            "L1.forbidden": {"reason": REASON, "date": "2026-11-25"},
            "L2.signal": {"reason": "small team", "date": "2026-11-25"}}}))
        code, out, _ = self.run_cli("ignore", "L1.forbidden", "--restore", "--repo", self.repo)
        self.assertEqual(code, 0)
        self.assertEqual(sorted(self.config()["ignored_checks"]), ["L2.signal"])
        self.assertEqual(self.config()["target_level"], 2)
        code, _, _ = self.run_cli("ignore", "L2.signal", "--restore", "--repo", self.repo)
        self.assertNotIn("ignored_checks", self.config())
        code, out, _ = self.run_cli("ignore", "L2.signal", "--restore", "--repo", self.repo)
        self.assertEqual(code, 0)
        self.assertIn("was not set aside", out)

    def test_the_list_names_every_check_in_plain_words_with_its_state(self):
        self.set_aside()
        code, out, _ = self.run_cli("ignore", self.repo)
        self.assertEqual(code, 0)
        ids = [c["id"] for num in (1, 2, 3, 4) for c in maturity.LEVEL_CHECKS[num](facts.collect(self.repo, today=TODAY))]
        for cid in ids:
            with self.subTest(check=cid):
                self.assertIn(cid, out)
        self.assertIn(f"set aside: {REASON}", out)
        self.assertIn("missing", out)
        self.assertIn("held", out)

    def test_the_list_as_json(self):
        self.set_aside()
        code, out, _ = self.run_cli("ignore", self.repo, "--format", "json")
        self.assertEqual(code, 0)
        rows = {r["id"]: r for r in json.loads(out)}
        self.assertEqual(rows["L1.forbidden"]["state"], "set aside")
        self.assertEqual(rows["L1.mode"]["state"], "held")
        self.assertFalse(rows["L1.source"]["can_be_set_aside"])

    def test_a_folder_that_is_not_a_repository_path_is_refused(self):
        code, _, _ = self.run_cli("ignore", "L1.forbidden", "--reason", REASON, "--repo", os.path.join(self.repo, "nope"))
        self.assertEqual(code, 2)


if __name__ == "__main__":
    unittest.main()
