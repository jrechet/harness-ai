"""The first slice of `harness flow` as a whole: the commands used one after the other, as a
person would, and the places where the core and the placement meet. Each part has its own
tests (test_flow, test_flow_place, test_flow_fixtures); these check they say the same thing."""
from __future__ import annotations

import contextlib
import copy
import io
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import harness  # noqa: E402
from harnesslib import flow, flow_notes, flow_place  # noqa: E402
from tests import flow_fixture_files as files  # noqa: E402


def run(*argv: str) -> tuple[int, str, str]:
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            code = harness.main(["flow", *argv])
        except SystemExit as exc:  # argparse refuses a wrong usage by exiting
            code = exc.code
    return code, out.getvalue(), err.getvalue()


class InAFolder(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.folder = folder.name
        before = os.getcwd()
        self.addCleanup(os.chdir, before)
        os.chdir(self.folder)

    def write(self, name: str, value) -> str:
        with open(name, "w", encoding="utf-8") as fh:
            json.dump(value, fh)
        return name


class WholePathTest(InAFolder):
    def test_a_new_flow_is_checked_placed_mapped_and_played_from_its_file(self):
        # Since section 12.1 a fresh template is at level 0 until each judge has answered.
        for kind in flow.TEMPLATES:
            with self.subTest(template=kind):
                path = os.path.join(".harness", "flow", f"{kind}.json")
                self.assertEqual(run("new", kind)[0], 0)
                self.assertEqual(flow.load_definition(path), flow.new(kind))
                code, out, _ = run("check", path)
                self.assertEqual(code, 0)
                self.assertTrue(out.startswith("This flow holds: "), out)
                code, out, _ = run("place", path)
                self.assertEqual(code, 1)
                self.assertIn("cannot be placed yet", out.splitlines()[-1])
                code, out, _ = run("status", path, "--map")
                self.assertEqual(code, 0)
                self.assertIn("· 0 None        the phases are chained by hand   ← you are here", out)
                answered = flow.load_definition(path)
                for gate in flow_place.waiting(answered):
                    answered["states"][gate]["can_judge"] = "yes"
                self.write(path, answered)
                code, out, _ = run("place", path)
                self.assertEqual(code, 0)
                self.assertEqual(out.splitlines()[-1], "Verdict: no step needs an engine.")
                code, out, _ = run("status", path, "--map")
                self.assertEqual(code, 0)
                self.assertIn("✓ 1 Mapped", out)
                self.assertIn("← you are here", out)

    def test_a_ticket_is_played_event_after_event_with_the_run_passed_back(self):
        run("new", "bug")
        path = os.path.join(".harness", "flow", "bug.json")
        events = [("ticket_ready", {"dollars": 0, "minutes": 1}), ("still_fails", {"dollars": 0.5, "minutes": 4}),
                  ("cause_written", {"dollars": 1, "minutes": 10}), ("confident", {"dollars": 0, "minutes": 1})]
        answer, how = None, ["--new"]
        for number, (kind, cost) in enumerate(events, 1):
            event = self.write(f"event-{number}.json", {"id": f"T-1:{number}:{kind}", "type": kind, "payload": cost})
            code, out, _ = run("next", path, "--event", event, *how, "--format", "json")
            answer = json.loads(out)
            self.assertEqual(code, 0, answer["message"])
            how = ["--run", self.write("run.json", answer["run"])]
        self.assertEqual((answer["outcome"], answer["reason"]), ("done", "stop_point"))
        self.assertEqual(answer["run"]["spent"], {"dollars": 1.5, "minutes": 16})

    def test_the_whole_answer_given_back_as_the_run_is_stopped_and_the_slip_is_named(self):
        run("new", "feature")
        path = os.path.join(".harness", "flow", "feature.json")
        event = self.write("event.json", {"id": "T-1:ready:1:claimed", "type": "claimed",
                                          "payload": {"dollars": 0, "minutes": 1}})
        _, out, _ = run("next", path, "--event", event, "--new", "--format", "json")
        whole = self.write("answer.json", json.loads(out))
        second = self.write("event-2.json", {"id": "T-1:planning:1:plan_written", "type": "plan_written",
                                             "payload": {"dollars": 1, "minutes": 5}})
        code, out, err = run("next", path, "--event", second, "--run", whole)
        self.assertEqual(code, 1)
        self.assertIn("Stopped", out)
        self.assertIn('"run"', err)
        self.assertIn("answer.json", err)
        code, _, err = run("next", path, "--event", second, "--run", self.write("run.json", json.loads(
            open(whole, encoding="utf-8").read())["run"]))
        # Since section 12.4 every command that exits 0 or 1 ends with the closing note, and here prints nothing else.
        self.assertEqual((code, err), (0, flow_notes.closing() + "\n"))


class OneVoiceTest(InAFolder):
    def test_a_missing_file_is_told_in_the_same_words_by_every_command(self):
        told = set()
        for command in (["check", "absent.json"], ["place", "absent.json"], ["status", "absent.json"]):
            code, out, err = run(*command)
            self.assertEqual((code, out), (2, ""))
            told.add(err)
        self.assertEqual(len(told), 1, told)
        self.assertNotIn("Errno", told.pop())

    def test_a_file_that_is_not_json_is_told_in_the_same_words_by_every_command(self):
        with open("broken.json", "w", encoding="utf-8") as fh:
            fh.write("{oops")
        told = {run(command, "broken.json")[2] for command in ("check", "place", "status")}
        self.assertEqual(len(told), 1, told)

    def test_the_placement_uses_the_words_of_the_core_for_a_step_type(self):
        self.assertIs(flow_place.TYPE_WORDS, flow.TYPE_WORDS)

    def test_the_map_names_the_judge_of_a_gate_nobody_can_judge_as_flow_place_does(self):
        # On the answered file since section 12.1, so that the gate refused is the one open reason.
        definition = files.answered_template("feature")
        definition["states"]["merge_auth"]["can_judge"] = "no"
        path = self.write("flow.json", definition)
        sentence = ("A gate nobody can judge: merge_auth. Remove it, or give "
                    f"{definition['states']['merge_auth']['judge']} something they can read and refuse.")
        self.assertIn(sentence, run("place", path)[1].splitlines())
        self.assertIn("  " + sentence, run("status", path, "--map")[1].splitlines())
        self.assertEqual(flow.status(definition)["checks"][1]["detail"], [sentence])


class OneSlipOneLineTest(unittest.TestCase):
    def test_a_mistyped_target_is_one_problem_not_one_per_step_behind_it(self):
        for kind in flow.TEMPLATES:
            with self.subTest(template=kind):
                definition = flow.new(kind)
                start = definition["start"]
                event = next(iter(definition["states"][start]["on"]))
                definition["states"][start]["on"][event]["to"] = "nowhere"
                self.assertEqual([(p["code"], p["where"]) for p in flow.check(definition)],
                                 [("malformed", f"states.{start}.on.{event}")])

    def test_a_step_no_path_leads_to_is_still_refused_when_every_target_is_a_step(self):
        definition = flow.new("feature")
        definition["states"]["island"] = copy.deepcopy(definition["states"]["checks"])
        self.assertEqual([(p["code"], p["where"]) for p in flow.check(definition)],
                         [("malformed", "states.island")])


if __name__ == "__main__":
    unittest.main()
