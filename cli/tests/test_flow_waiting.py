"""Section 12.1 of the flow contract: the templates no longer answer for the team. A gate with no
`can_judge` waits for its judge; `flow place` leaves it open, `flow status` stays at level 0 and
says whom to ask, and the commands say it in one note (docs/workflow-harness/flow-spec.md)."""
from __future__ import annotations

import contextlib
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

# Since the critics of section 12: "these steps", since another step of the file may be at fault.
REST = ("Nothing is wrong with these steps: a judge says whether they can really read what they are shown and refuse "
        'it, and the answer is written "can_judge": "yes" or "no" in the step. Until then flow place leaves such a '
        "step open and the flow stays under level 1 (Mapped).")
BEHIND = ("Behind the point where a run stops as written, so asked by no run yet: {}. Level 1 needs an answer there "
          "too: moving stop_at must not be what answers for the judge.")
FEATURE_NOTE = (f"3 approvals wait for their judge's answer: plan_review, human_review, merge_auth. {REST} "
                + BEHIND.format("human_review, merge_auth"))
BUG_NOTE = f"1 approval waits for its judge's answer: human_review. {REST} " + BEHIND.format("human_review")
ASK_PLAN = ('Ask a maintainer of the repository whether they can really read the plan and refuse it, then write '
            '"can_judge": "yes" or "no" in the step plan_review.')


def call(*argv: str) -> tuple[int, str, str]:
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            code = harness.main(["flow", *argv])
        except SystemExit as exc:
            code = exc.code
    return code, out.getvalue(), err.getvalue()


class WaitingTest(unittest.TestCase):
    def test_the_gates_of_a_fresh_template_wait_and_those_of_an_answered_file_do_not(self):
        self.assertEqual(flow_place.waiting(flow.new("feature")), ["plan_review", "human_review", "merge_auth"])
        self.assertEqual(flow_place.waiting(flow.new("bug")), ["human_review"])
        for kind in files.TEMPLATE_KINDS:
            self.assertEqual(flow_place.waiting(files.answered_template(kind)), [])

    def test_a_value_the_grid_cannot_read_is_a_fault_not_a_wait(self):
        definition = flow.new("bug")
        for value in (True, "Yes", None, "no"):
            definition["states"]["human_review"]["can_judge"] = value
            with self.subTest(value=value):
                self.assertEqual(flow_place.waiting(definition), [])

    def test_a_value_that_is_not_a_flow_waits_for_nothing_and_never_raises(self):
        for value in (None, [1], "text", {"states": 3}, {"states": {"a": 3, "b": {"type": "gate"}}}, {}):
            with self.subTest(value=repr(value)[:30]):
                self.assertIn(flow_place.waiting(value), ([], ["b"]))
        self.assertEqual(flow_place.waiting({"states": {"a": 3, "b": {"type": "gate"}}}), ["b"])


class StatusTest(unittest.TestCase):
    def test_a_fresh_template_holds_but_stays_at_level_0_and_says_whom_to_ask(self):
        state = flow.status(flow.new("feature"))
        self.assertEqual(state["level"]["reached"], 0)
        self.assertEqual([check["passed"] for check in state["checks"]], [True, False, True])
        self.assertEqual(state["waiting"], ["plan_review", "human_review", "merge_auth"])
        self.assertEqual(state["next_step"], ASK_PLAN)
        self.assertEqual(flow.status(files.answered_template("feature"))["waiting"], [])

    def test_the_words_used_when_the_file_names_no_judge_or_shows_nothing(self):
        definition = flow.new("bug")
        del definition["states"]["human_review"]["judge"]
        self.assertTrue(flow.status(definition)["next_step"].startswith("Fix this first: "),
                        "a gate with no judge is a problem of flow check, told first")
        definition = flow.new("bug")
        state = flow.status(definition)
        self.assertEqual(state["next_step"], 'Ask a maintainer of the repository whether they can really read the '
                                             'pull request and refuse it, then write "can_judge": "yes" or "no" in '
                                             "the step human_review.")

    def test_an_open_step_that_is_not_a_waiting_gate_keeps_fix_this_first(self):
        definition = flow.new("feature")
        del definition["states"]["planning"]["units"]  # planning comes before plan_review in the file
        self.assertTrue(flow.status(definition)["next_step"].startswith("Fix this first: The step planning"))

    def test_the_map_of_a_fresh_template(self):
        lines = flow.render_map(flow.status(flow.new("feature"))).splitlines()
        self.assertEqual(lines[1], "· 0 None        the phases are chained by hand   ← you are here")
        self.assertIn("- every step has a place", lines)
        self.assertIn('  The step plan_review has no answer to "Can the person who approves really judge what they '
                      'approve?" (key can_judge). Add "can_judge": "yes" or "no".', lines)
        self.assertEqual(lines[-1], f"Next step: {ASK_PLAN}")


class NotesTest(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.folder = folder.name

    def write(self, name: str, value) -> str:
        path = os.path.join(self.folder, name)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(value, fh)
        return path

    def test_every_command_that_reads_a_fresh_template_says_its_approvals_wait(self):
        path = os.path.join(self.folder, "f.json")
        code, _, err = call("new", "feature", "--out", path)
        self.assertEqual(code, 0)
        self.assertIn(FEATURE_NOTE, err.splitlines())
        for argv, exit_code in ((["check", path], 0), (["place", path], 1), (["status", path], 0),
                                (["status", path, "--map"], 0)):
            with self.subTest(argv=argv):
                code, _, err = call(*argv)
                self.assertEqual(code, exit_code)
                self.assertIn(FEATURE_NOTE, err.splitlines())
        bug = self.write("bug.json", flow.new("bug"))
        self.assertIn(BUG_NOTE, call("place", bug)[2].splitlines())

    def test_the_note_comes_after_the_stop_point_and_before_what_comes_next(self):
        path = self.write("f.json", flow.new("feature"))
        lines = call("check", path)[2].splitlines()
        stop = [n for n, line in enumerate(lines) if line.startswith("As written, a run stops")][0]
        self.assertEqual(lines[stop + 1], FEATURE_NOTE)
        self.assertGreater([n for n, line in enumerate(lines) if line.startswith("Next: ")][0], stop + 1)

    def test_no_note_beside_a_document_nor_once_every_gate_is_answered(self):
        path = self.write("f.json", flow.new("feature"))
        for argv in (["check", path], ["place", path], ["status", path], ["status", path, "--map"]):
            with self.subTest(argv=argv):
                self.assertEqual(call(*argv, "--format", "json")[2], "")
        answered = self.write("a.json", files.answered_template("feature"))
        for argv in (["check", answered], ["place", answered], ["status", answered]):
            with self.subTest(argv=argv):
                self.assertNotIn("wait for their judge", call(*argv)[2])

    def test_one_gate_answered_leaves_two_that_wait(self):
        definition = flow.new("feature")
        definition["states"]["plan_review"]["can_judge"] = "yes"
        err = call("place", self.write("f.json", definition))[2]
        self.assertIn("2 approvals wait for their judge's answer: human_review, merge_auth. ", err)

    def test_check_says_flow_place_names_the_approvals_that_wait(self):
        path = self.write("f.json", flow.new("feature"))
        lines = call("check", path)[2].splitlines()
        self.assertIn(f"Next: flow place {path} says where each step belongs and which approvals still wait. This "
                      "command does not look at that.", lines)
        self.assertFalse([line for line in lines if line.startswith("Careful:")])

    def test_check_still_warns_when_the_placement_fails_for_another_reason(self):
        definition = flow.new("feature")
        definition["states"]["coding"]["units"] = "several"
        lines = call("check", self.write("f.json", definition))[2].splitlines()
        self.assertTrue([line for line in lines if line.startswith("Careful: flow place ")], lines)
        self.assertFalse([line for line in lines if line.startswith("Next: ")], lines)

    def test_place_says_what_comes_next_only_when_waiting_gates_are_all_that_fails(self):
        path = self.write("f.json", flow.new("feature"))
        lines = call("place", path)[2].splitlines()
        # Since section 12.4 the closing note comes last, after the "Next:" note.
        self.assertEqual(lines[-2:], [f"Next: flow status {path} --map shows what level 1 still needs.",
                                      flow_notes.closing()])
        definition = flow.new("feature")
        del definition["states"]["coding"]["units"]
        lines = call("place", self.write("g.json", definition))[2].splitlines()
        self.assertFalse([line for line in lines if line.startswith("Next: ")], lines)
        self.assertIn(FEATURE_NOTE, lines)
        definition = flow.new("feature")
        del definition["states"]["coding"]["cap"]
        lines = call("place", self.write("h.json", definition))[2].splitlines()
        self.assertTrue(lines[-3].startswith("Careful: flow check "), lines)
        self.assertEqual(lines[-2:], [flow_notes.NOT_READ, flow_notes.closing()])
        # The steps behind the stop point are read on a flow that holds only (flow.beyond_stop).
        self.assertIn(FEATURE_NOTE[:FEATURE_NOTE.index(" Behind the point")], lines)

    def test_status_at_level_0_gives_the_note_then_the_next_step(self):
        path = self.write("f.json", flow.new("feature"))
        lines = call("status", path)[2].splitlines()
        # Since section 12.5 the note on the measured symptoms comes before the next step.
        self.assertEqual(lines[:3], [FEATURE_NOTE, flow_notes.NOT_READ, f"Next step: {ASK_PLAN}"])


if __name__ == "__main__":
    unittest.main()
