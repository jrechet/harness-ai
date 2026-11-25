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
from harnesslib import facts, maturity, medals, page, serve  # noqa: E402

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
        self.assertIn(f"- [~] A \"Forbidden\" section says what an agent never does → set aside: {REASON}", out)
        self.assertIn("**Level reached**: 1 · Framed (1 check set aside; level 0 without that)", out)
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

    def test_the_medal_follows_the_level_but_the_achievement_is_set_aside_not_unlocked(self):
        self.set_aside()
        built = medals.build(medals.evaluate_repo(self.repo, today=TODAY))
        success = next(s for s in built["successes"] if s["id"] == "L1.forbidden")
        self.assertEqual((success["unlocked"], success["lost"], success["set_aside"]), (None, None, REASON))
        self.assertEqual(built["medal"]["rank"], 1)
        self.assertIn("4 are unlocked and 1 set aside", built["why"])
        out = medals.render_md(built)
        self.assertIn("## ✓ Bronze — Framed (4/5, 1 set aside)", out)
        self.assertIn(f"- [~] A \"Forbidden\" section says what an agent never does — set aside: {REASON}", out)
        self.assertNotIn("[x] A \"Forbidden\"", out)
        self.assertNotIn("Forbidden", " ".join(str(s.get("action")) for s in built["next"]))

    def test_restoring_does_not_report_as_lost_what_was_never_held(self):
        self.set_aside()
        first = medals.build(medals.evaluate_repo(self.repo, today=TODAY))
        os.remove(os.path.join(self.repo, CONFIG))
        second = medals.build(medals.evaluate_repo(self.repo, today=TODAY), first)
        success = next(s for s in second["successes"] if s["id"] == "L1.forbidden")
        self.assertEqual((success["unlocked"], success["lost"]), (None, None))

    def test_the_page_says_what_was_set_aside_and_what_the_measure_alone_gives(self):
        self.set_aside()
        data = page.build(self.repo, today=TODAY)
        self.assertEqual((data["level"]["reached"], data["level"]["measured"], data["level"]["set_aside"]), (1, 0, 1))
        self.assertEqual(data["ladder"][1]["set_aside"], 1)
        self.assertEqual(data["set_aside"], [{"level": 1, "missing": maturity.CHECK_PLAIN["L1.forbidden"][0],
                                              "reason": REASON}])
        html = page.render_html(data)
        self.assertIn("data.set_aside", html)
        self.assertIn("the measure alone gives level", html)

    def test_the_local_app_gets_the_count_and_draws_a_third_state(self):
        self.set_aside()
        summary = serve.summarize(self.state())
        self.assertEqual((summary["set_aside"], summary["levels"][0]["set_aside"]), (1, 1))
        with open(os.path.join(os.path.dirname(CLI_DIR), "app", "app.js"), encoding="utf-8") as fh:
            app = fh.read()
        self.assertIn('v-if="c.ignored"', app)
        self.assertIn("set aside, not passed: {{ c.reason }}", app)

    def test_the_state_keeps_the_level_the_checks_alone_give(self):
        self.set_aside()
        level = self.state()["level"]
        self.assertEqual((level["reached"], level["measured"], level["set_aside"]), (1, 0, 1))
        self.assertIn("the measure alone gives level 0", maturity.render_map(self.state()))

    def test_the_measure_alone_can_be_asked_for_whatever_the_repository_chose(self):
        self.set_aside()
        measured = maturity.evaluate(facts.collect(self.repo, today=TODAY), honour_ignored=False)
        self.assertEqual((measured["level"]["reached"], measured["ignored"]), (0, []))


class PartlySetAsideTests(IgnoreTests):
    """A level that still lacks something after one of its checks was set aside: the walk goes on with
    the others, and only with them."""

    def setUp(self):
        super().setUp()
        self.write("AGENTS.md", "# demo\n\n## Rules\n- Tests pass.\n")      # no mode, no Forbidden section
        self.set_aside()

    def test_the_level_is_not_reached_and_the_other_check_is_the_step(self):
        state = self.state()
        self.assertEqual((state["level"]["reached"], state["level"]["set_aside"]), (0, 0))
        self.assertEqual(len(state["next_actions"]), 1)
        self.assertIn("mode", state["next_actions"][0])
        out = maturity.render_map(state)
        needs = out.split("still needs:")[1].split("Set aside by you")[0]
        self.assertIn(maturity.CHECK_PLAIN["L1.mode"][0], needs)
        self.assertNotIn(maturity.CHECK_PLAIN["L1.forbidden"][0], needs)
        self.assertIn(f"Next step: {maturity.CHECK_PLAIN['L1.mode'][1]}", out)
        self.assertEqual([s["missing"] for s in page._steps(state) if s["level"] == 1],
                         [maturity.CHECK_PLAIN["L1.mode"][0]])

    def test_a_check_that_only_time_passes_no_longer_waits_once_set_aside(self):
        self.write("AGENTS.md", AGENTS_NO_FORBIDDEN)
        self.write(CONFIG, json.dumps({"ignored_checks": {
            "L1.forbidden": {"reason": REASON}, "L2.signal": {"reason": "two people, no reviews"}}}))
        state = self.state()
        self.assertEqual(state["waiting"], [])
        signal = next(c for c in state["levels"][2]["checks"] if c["id"] == "L2.signal")
        self.assertEqual((signal["ignored"], signal["waits"]), (True, False))

    def test_with_no_instruction_file_nothing_is_set_aside(self):
        os.remove(os.path.join(self.repo, "AGENTS.md"))
        state = self.state()
        self.assertEqual(state["ignored"], [])
        check = next(c for c in state["levels"][1]["checks"] if c["id"] == "L1.forbidden")
        self.assertFalse(check.get("ignored"))
        code, out, _ = self.run_cli("ignore", "L1.mode", "--reason", "x", "--repo", self.repo)
        self.assertEqual(code, 0)
        self.assertIn("No effect today", out)
        self.assertNotIn("no longer waits", out)


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
        self.assertIn("no longer waits for it", out)
        self.assertIn("(written to .harness/config.json)", out)        # relative to the repository, wherever it is run
        self.assertEqual(self.state()["level"]["reached"], 1)

    def test_another_harness_folder_is_written_and_read(self):
        code, _, _ = self.run_cli("ignore", "L1.forbidden", "--reason", REASON, "--repo", self.repo, "--harness-dir", ".h")
        self.assertEqual(code, 0)
        self.assertTrue(os.path.isfile(os.path.join(self.repo, ".h", "config.json")))
        self.assertFalse(os.path.exists(os.path.join(self.repo, ".harness")))
        code, out, _ = self.run_cli("ignore", self.repo, "--harness-dir", ".h")
        self.assertIn(f"set aside: {REASON}", out)

    def test_a_check_that_passes_is_recorded_and_said_to_change_nothing(self):
        code, out, _ = self.run_cli("ignore", "L1.mode", "--reason", "x", "--repo", self.repo)
        self.assertEqual(code, 0)
        self.assertIn("passes today, so nothing changes", out)
        code, out, _ = self.run_cli("ignore", self.repo)
        self.assertIn("held (a choice to set it aside is written, without effect today: x)", out)

    def test_a_settings_file_that_is_not_an_object_is_refused_and_kept(self):
        for broken in ("{", "[1, 2]", "42"):
            with self.subTest(content=broken):
                self.write(CONFIG, broken)
                code, _, err = self.run_cli("ignore", "L1.forbidden", "--reason", REASON, "--repo", self.repo)
                self.assertEqual(code, 2)
                self.assertIn("not a JSON object", err)
                with open(os.path.join(self.repo, CONFIG), encoding="utf-8") as fh:
                    self.assertEqual(fh.read(), broken)
                self.assertEqual(self.run_cli("status", self.repo, "--no-write")[0], 0)    # and status still answers
                self.assertEqual(self.run_cli("ignore", self.repo)[0], 0)

    def test_an_id_the_ladder_no_longer_has_can_still_be_taken_out_of_the_file(self):
        self.write(CONFIG, json.dumps({"ignored_checks": {"L1.gone": {"reason": "old"}}}))
        code, out, _ = self.run_cli("ignore", "L1.gone", "--restore", "--repo", self.repo)
        self.assertEqual(code, 0)
        self.assertNotIn("ignored_checks", self.config())

    def test_a_mistyped_id_is_not_taken_for_a_folder(self):
        code, _, err = self.run_cli("ignore", "l1.forbidden")
        self.assertEqual(code, 2)
        self.assertIn("not a check of the ladder", err)

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
        self.assertIn(f"When missing: {maturity.CHECK_PLAIN['L1.forbidden'][0]}. Id: L1.forbidden", out)

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
