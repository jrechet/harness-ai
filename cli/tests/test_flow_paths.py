"""Section 12.2 of the flow contract: `flow check` refuses a write that cannot be taken back when
a run can make it crossing no gate that guards it, and prints the figures that bound one run
(docs/workflow-harness/flow-spec.md). The rules are in `cli/harnesslib/flow_paths.py`."""
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
from harnesslib import flow, flow_paths  # noqa: E402
from tests import flow_fixture_files as files  # noqa: E402
from tests import test_flow_cases as cases  # noqa: E402

THE_WAY_OUT = ('Add a step of type "gate" on that path, with an answer that stops the run; or, if a person does '
               "this outside the flow and the step {state} only waits for it, that step is a person's decision: "
               'give it the type "gate", with its judge and what they are shown; or, if your team can take '
               '"{stop}" back, write "irreversible": [<the stop points it cannot take back>] at the top of the file.')
TO_MERGING = "ready → planning → plan_size → coding → checks → draft_pr → ci_wait → ci_check → review_checks → mark_ready"
FEATURE_BOUNDS = {
    "budget": {"dollars": 20, "minutes": 240}, "irreversible": ["merged", "deployed"], "irreversible_declared": False,
    "taken_back": ["plan", "draft_pr", "ready_pr"],
    "circles": [{"steps": ["planning", "plan_size", "plan_review"], "caps": {"planning": 3}, "most_entries": 3},
                {"steps": ["coding", "checks", "draft_pr", "ci_wait", "ci_check", "ci_fix", "review_checks"],
                 "caps": {"coding": 6, "ci_wait": 8, "ci_fix": 2}, "most_entries": 16}],
    "guards": [{"stop_point": "merged", "state": "merging", "event": "merged", "last_gate": "merge_auth",
                "shows": "the pull request", "can_judge": "yes", "steps_between": 0, "agents_between": 0},
               {"stop_point": "deployed", "state": "delivery", "event": "deployed", "last_gate": "merge_auth",
                "shows": "the pull request", "can_judge": "yes", "steps_between": 1, "agents_between": 0}]}
FEATURE_LINES = [
    "What bounds one run (figures for you to read: no threshold is applied to them):",
    "- Spending: a run is stopped at the first event that takes it past 20 dollars or 240 minutes. It can pass "
    "them by the cost of one step, which the file does not bound.",
    "- The circle planning, plan_size, plan_review: its capped steps can be entered 3 times in all at most "
    "(cap of planning 3).",
    "- The circle coding, checks, draft_pr, ci_wait, ci_check, ci_fix, review_checks: its capped steps can be "
    "entered 16 times in all at most (caps of coding 6, ci_wait 8, ci_fix 2).",
    '- Cannot be taken back: merged, deployed (the default: the file has no "irreversible").',
    "- The file treats as possible to take back: plan, draft_pr, ready_pr.",
    '- The event merged of merging reaches "merged". Every path to it crosses a gate that guards it. On the '
    'shortest path the last one is merge_auth, whose judge is shown "the pull request". Steps between merge_auth '
    "and merging: 0; agents among them: 0.",
    '- The event deployed of delivery reaches "deployed". Every path to it crosses a gate that guards it. On the '
    'shortest path the last one is merge_auth, whose judge is shown "the pull request". Steps between merge_auth '
    "and delivery: 1; agents among them: 0."]
CANNOT_SEE = ("flow check reads the file, not the programs: it cannot see a write a step does not declare, nor a "
              "step given the wrong type. The full list is in the page flow-spec.md, section 12.")


def unreached(name: str) -> str:
    return (f'- No transition of this file reaches "{name}": if a step of yours does that write under another name, '
            'flow check does not know it; write that name under "irreversible".')


def answered(kind: str) -> dict:
    return files.answered_template(kind)


def case(name: str) -> dict:
    return cases.changed(files.read_json(os.path.join(files.FAMILY, "cases", f"{name}.json")), flow.new)


def call(*argv: str) -> tuple[int, str, str]:
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            code = harness.main(["flow", *argv])
        except SystemExit as exc:
            code = exc.code
    return code, out.getvalue(), err.getvalue()


class RefusalTest(unittest.TestCase):
    def test_a_merge_with_no_gate_before_it_is_refused_in_the_words_of_the_contract(self):
        problems = flow.check(case("merge-without-a-person"))
        self.assertEqual([(p["code"], p["where"]) for p in problems],
                         [("irreversible_without_gate", "states.merging.on.merged"),
                          ("irreversible_without_gate", "states.delivery.on.deployed")])
        self.assertEqual(problems[0]["message"],
                         f'The event merged of the step merging reaches "merged", which cannot be taken back, and the '
                         f"path {TO_MERGING} → merging crosses no gate that guards it. "
                         + THE_WAY_OUT.format(state="merging", stop="merged"))
        self.assertTrue(problems[1]["message"].startswith(
            'The event deployed of the step delivery reaches "deployed", which cannot be taken back, and the path '
            f"{TO_MERGING} → merging → delivery crosses no gate"), problems[1]["message"])

    def test_silence_is_not_a_decision(self):
        message = flow.check(case("silence-is-consent"))[0]["message"]
        self.assertIn(f"{TO_MERGING} → human_review → merge_auth → merging crosses no gate that guards it "
                      "(it leaves the gate human_review by deadline_passed, when nobody answered) "
                      "(it leaves the gate merge_auth by deadline_passed, when nobody answered). Add", message)

    def test_a_gate_whose_every_answer_leads_to_the_write_guards_nothing(self):
        message = flow.check(case("refusal-leads-to-the-write"))[0]["message"]
        self.assertIn(f"{TO_MERGING} → merge_auth → merging crosses no gate that guards it "
                      "(every answer of the gate merge_auth leads to this write). Add", message)

    def test_the_refusal_comes_last_in_the_order_of_the_table(self):
        definition = case("merge-without-a-person")
        del definition["budget"]
        self.assertEqual([p["code"] for p in flow.check(definition)],
                         ["no_budget", "irreversible_without_gate", "irreversible_without_gate"])

    def test_an_unknown_type_is_told_first_and_alone(self):
        definition = case("merge-without-a-person")
        definition["states"]["checks"]["type"] = "program"
        self.assertEqual([p["code"] for p in flow.check(definition)], ["unknown_step_type"])

    def test_a_gate_that_guards_the_write_itself_lets_its_judge_decide(self):
        self.assertEqual(flow.check(answered("bug")), [])
        definition = answered("bug")
        definition["states"]["human_review"]["on"]["deadline_passed"] = {"to": "closure_wait", "reaches": "merged"}
        self.assertEqual([(p["code"], p["where"]) for p in flow.check(definition)],
                         [("irreversible_without_gate", "states.human_review.on.deadline_passed")])
        self.assertIn("(it leaves the gate human_review by deadline_passed, when nobody answered)",
                      flow.check(definition)[0]["message"])

    def test_a_persons_step_left_by_its_deadline_decides_nothing(self):
        # Rule 1 reads a person's write as their decision; the deadline of a `human` step passes when
        # nobody acted, so that transition is checked like any other, and guards nothing after it.
        problems = flow.check(case("person-merges-on-silence"))
        self.assertEqual([(p["code"], p["where"]) for p in problems],
                         [("irreversible_without_gate", "states.human_review.on.deadline_passed")])
        self.assertIn("crosses no gate that guards it (it leaves the person's step human_review by deadline_passed, "
                      "when nobody acted). Add", problems[0]["message"])
        self.assertEqual(flow_paths.bounds(case("person-merges-on-silence")), None)
        later = flow.check(case("person-merges-on-silence-then-pipeline-deploys"))
        self.assertEqual([p["where"] for p in later], ["states.merging.on.deadline_passed", "states.delivery.on.deployed"])

    def test_unguarded_is_read_on_a_definition_that_is_not_malformed(self):
        self.assertEqual(flow_paths.unguarded(answered("feature")), [])
        self.assertEqual(len(flow_paths.unguarded(case("merge-without-a-person"))), 2)


class IrreversibleKeyTest(unittest.TestCase):
    def test_a_value_that_is_not_a_list_of_names_is_malformed(self):
        for value in ("merged", None, [1], ["Merged"], {"merged": True}, [["merged"]]):
            definition = answered("feature")
            definition["irreversible"] = value
            with self.subTest(value=value):
                self.assertEqual([(p["code"], p["where"]) for p in flow.check(definition)],
                                 [("malformed", "irreversible")])

    def test_a_name_no_transition_reaches_is_malformed_and_the_choices_are_given(self):
        definition = answered("feature")
        definition["irreversible"] = ["mergd"]
        self.assertEqual(flow.check(definition), [{
            "code": "malformed", "where": "irreversible",
            "message": 'The file cannot be read as a flow: irreversible names "mergd", which no transition reaches. '
                       "Write one of the stop points of this file, or remove the name: plan, draft_pr, ready_pr, "
                       "merged, deployed."}])

    def test_a_name_reached_only_by_a_stop_is_a_stop_point_of_the_file(self):
        definition = case("reaches-on-a-stop")
        definition["irreversible"] = ["merged"]
        self.assertEqual([p["where"] for p in flow.check(definition)], ["states.merging.on.merged"])

    def test_check_never_raises_on_an_odd_irreversible(self):
        for value in (float("nan"), [None], [{}], 3, True):
            definition = answered("bug")
            definition["irreversible"] = value
            with self.subTest(value=value):
                self.assertEqual([p["code"] for p in flow.check(definition)], ["malformed"])
        broken = {"format": 1, "name": "x", "start": "a", "states": {"a": 3}, "irreversible": ["merged"]}
        self.assertTrue(all(p["code"] == "malformed" for p in flow.check(broken)))


class BoundsTest(unittest.TestCase):
    def test_the_bounds_of_the_answered_feature_flow_are_those_of_the_contract(self):
        self.assertEqual(flow_paths.bounds(answered("feature")), FEATURE_BOUNDS)

    def test_no_bounds_for_a_flow_that_does_not_hold(self):
        for value in (case("merge-without-a-person"), [1], "text", None, {"format": 1}):
            with self.subTest(value=repr(value)[:30]):
                self.assertIsNone(flow_paths.bounds(value))

    def test_the_figures_a_person_reads_for_the_feature_flow(self):
        self.assertEqual(flow_paths.render_bounds(FEATURE_BOUNDS), "\n".join(FEATURE_LINES) + "\n")

    def test_a_huge_cap_and_budget_are_printed_not_judged(self):
        text = flow_paths.render_bounds(flow_paths.bounds(case("huge-cap-and-budget")))
        self.assertIn("past 1000000000 dollars or 240 minutes", text)
        self.assertIn("can be entered 1000010 times in all at most (caps of coding 1000000, ci_wait 8, ci_fix 2)", text)

    def test_a_gate_that_is_the_step_itself_and_no_circle(self):
        lines = flow_paths.render_bounds(flow_paths.bounds(answered("bug"))).splitlines()
        self.assertIn("- No circle: no step can be entered twice.", lines)
        self.assertIn('- The event merged_by_human of human_review reaches "merged". human_review is a gate: its '
                      'judge, shown "the pull request", decides it.', lines)
        self.assertIn("- The file treats as possible to take back: root_cause, plan, draft_pr, ready_pr.", lines)

    def test_a_person_who_merges_by_hand_is_said_to_be_no_gate(self):
        lines = flow_paths.render_bounds(flow_paths.bounds(case("person-merges-by-hand"))).splitlines()
        self.assertIn('- The event merged_by_human of human_review reaches "merged". human_review is a person\'s '
                      'step (type "human"): no gate is asked.', lines)

    def test_the_key_written_or_empty(self):
        declared = answered("feature")
        declared["irreversible"] = ["merged"]
        lines = flow_paths.render_bounds(flow_paths.bounds(declared)).splitlines()
        self.assertIn('- Cannot be taken back: merged (the file says so under "irreversible").', lines)
        self.assertIn("- The file treats as possible to take back: plan, draft_pr, ready_pr, deployed.", lines)
        self.assertEqual(sum(line.startswith("- The event ") for line in lines), 1)
        empty = flow_paths.render_bounds(flow_paths.bounds(case("irreversible-empty"))).splitlines()
        self.assertIn('- Cannot be taken back: nothing, the file says so ("irreversible": []): no write is checked '
                      "for a gate.", empty)
        self.assertFalse([line for line in empty if line.startswith(("- The event ", "- No transition"))])

    def test_names_the_file_does_not_reach_are_said_to_be_unknown_to_flow_check(self):
        # Since the critics of section 12: one line per irreversible name that no transition reaches.
        lines = flow_paths.render_bounds(flow_paths.bounds(case("stop-point-renamed"))).splitlines()
        for name in ("merged", "deployed"):
            self.assertIn(unreached(name), lines)

    def test_a_name_left_unreached_is_said_even_when_the_other_one_is_reached(self):
        definition = answered("feature")
        for path in ("human_review", "rework"):
            del definition["states"][path]
        definition["stop_at"] = "deployed"
        definition["states"]["mark_ready"]["on"]["marked_ready"] = {"to": "merging", "reaches": "ready_pr"}
        definition["states"]["merging"]["on"]["merged"] = {"to": "merge_auth", "reaches": "landed"}
        definition["states"]["merge_auth"]["on"]["merge_authorised"] = {"to": "delivery"}
        lines = flow_paths.render_bounds(flow_paths.bounds(definition)).splitlines()
        self.assertIn(unreached("merged"), lines)
        self.assertNotIn(unreached("deployed"), lines)
        bug = flow_paths.render_bounds(flow_paths.bounds(answered("bug"))).splitlines()
        self.assertIn(unreached("deployed"), bug)
        self.assertNotIn(unreached("merged"), bug)

    def test_a_name_written_twice_under_irreversible_is_read_once(self):
        definition = answered("feature")
        definition["irreversible"] = ["merged", "merged"]
        self.assertEqual(flow_paths.bounds(definition)["irreversible"], ["merged"])
        self.assertIn('- Cannot be taken back: merged (the file says so under "irreversible").',
                      flow_paths.render_bounds(flow_paths.bounds(definition)).splitlines())

    def test_a_gate_whose_answer_cannot_be_read_is_not_said_to_wait(self):
        definition = answered("feature")
        definition["states"]["merge_auth"]["can_judge"] = True
        found = flow_paths.bounds(definition)
        self.assertEqual([g["can_judge"] for g in found["guards"]], ["unreadable", "unreadable"])
        last = flow_paths.render_bounds(found).splitlines()[-1]
        self.assertTrue(last.endswith('agents among them: 0. The file\'s answer for that gate cannot be read: write '
                                      '"can_judge": "yes" or "no".'), last)
        self.assertNotIn("still waits", last)

    def test_a_deploy_after_a_person_merge_names_that_person_step(self):
        # Since the attacks on issue 165 the line no longer says the person's write cannot be taken back:
        # with "irreversible": ["deployed"] the merge can be, and it still stands before the deploy.
        for name in ("person-merges-then-pipeline-deploys", "person-merges-what-can-be-taken-back"):
            with self.subTest(case=name):
                lines = flow_paths.render_bounds(flow_paths.bounds(case(name))).splitlines()
                self.assertIn('- The event deployed of delivery reaches "deployed". Every path to it crosses a gate '
                              "that guards it or a write a person makes. On the shortest path the last one is "
                              "merging, a person's step (type \"human\") whose write is that person's decision. "
                              "Steps between merging and delivery: 0; agents among them: 0.", lines)

    def test_a_silent_write_of_a_person_step_names_the_gate_before_it(self):
        definition = answered("feature")
        merging = definition["states"]["merging"]
        for key in ("checks_premise", "survives", "units", "repositories"):
            del merging[key]
        merging.update({"type": "human", "deadline_hours": 1})
        merging["on"]["deadline_passed"] = {"to": "delivery", "reaches": "merged"}
        self.assertEqual(flow.check(definition), [])
        guards = flow_paths.bounds(definition)["guards"]
        self.assertEqual([(g["state"], g["event"], g["last_gate"], g["steps_between"]) for g in guards],
                         [("merging", "merged", None, None), ("merging", "deadline_passed", "merge_auth", 0),
                          ("delivery", "deployed", "merging", 0)])
        self.assertIn('- The event deadline_passed of merging reaches "merged". Every path to it crosses a gate that '
                      'guards it. On the shortest path the last one is merge_auth, whose judge is shown "the pull '
                      'request". Steps between merge_auth and merging: 0; agents among them: 0.',
                      flow_paths.render_bounds(flow_paths.bounds(definition)).splitlines())

    def test_one_cap_entered_once_and_a_gate_that_waits_or_cannot_be_judged(self):
        definition = answered("feature")
        definition["states"]["planning"]["cap"] = 1
        del definition["states"]["merge_auth"]["can_judge"]
        lines = flow_paths.render_bounds(flow_paths.bounds(definition)).splitlines()
        self.assertIn("- The circle planning, plan_size, plan_review: its capped steps can be entered 1 time in all "
                      "at most (cap of planning 1).", lines)
        self.assertTrue(lines[-1].endswith("agents among them: 0. That gate still waits for its judge's answer."))
        definition["states"]["merge_auth"]["can_judge"] = "no"
        lines = flow_paths.render_bounds(flow_paths.bounds(definition)).splitlines()
        # Since the critics of section 12, the line no longer says such a gate guards the write.
        self.assertEqual(lines[-1], '- The event deployed of delivery reaches "deployed". Every path to it crosses a '
                                    "gate flow check counts. On the shortest path the last one is merge_auth, whose "
                                    'judge is shown "the pull request", and the file says nobody can judge it '
                                    '("can_judge": "no"): flow place refuses it. Steps between merge_auth and '
                                    "delivery: 1; agents among them: 0.")
        self.assertNotIn("a gate that guards it", lines[-1])
        self.assertEqual([g["can_judge"] for g in flow_paths.bounds(definition)["guards"]], ["no", "no"])
        bug = answered("bug")
        bug["states"]["human_review"]["can_judge"] = "no"
        self.assertIn('- The event merged_by_human of human_review reaches "merged". human_review is a gate, shown '
                      '"the pull request", and the file says nobody can judge it ("can_judge": "no"): flow place '
                      "refuses it.", flow_paths.render_bounds(flow_paths.bounds(bug)).splitlines())

    def test_the_words_a_person_decides_are_never_printed(self):
        for definition in (answered("feature"), answered("bug"), case("person-merges-by-hand")):
            self.assertNotIn("a person decides", flow_paths.render_bounds(flow_paths.bounds(definition)))


class CommandTest(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.folder = folder.name

    def write(self, name: str, value) -> str:
        path = os.path.join(self.folder, name)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(value, fh)
        return path

    def test_check_prints_the_bounds_after_its_first_line(self):
        code, out, err = call("check", self.write("flow.json", answered("feature")))
        self.assertEqual(code, 0)
        self.assertEqual(out.splitlines(), ["This flow holds: 18 steps, it stops at ready_pr, one ticket may cost "
                                            "up to 20 dollars and 240 minutes.", *FEATURE_LINES])
        self.assertIn(CANNOT_SEE, err.splitlines())

    def test_check_carries_the_bounds_in_its_document(self):
        path = self.write("flow.json", answered("feature"))
        code, out, err = call("check", path, "--format", "json")
        self.assertEqual((code, err), (0, ""))
        self.assertEqual(json.loads(out), {"file": path, "passed": True, "problems": [], "bounds": FEATURE_BOUNDS})
        broken = self.write("broken.json", case("merge-without-a-person"))
        code, out, _ = call("check", broken, "--format", "json")
        document = json.loads(out)
        self.assertEqual((code, list(document), document["bounds"]), (1, ["file", "passed", "problems", "bounds"], None))

    def test_a_refused_flow_prints_its_problems_and_no_bounds_nor_note(self):
        code, out, err = call("check", self.write("flow.json", case("merge-without-a-person")))
        self.assertEqual(code, 1)
        self.assertEqual(len(out.splitlines()), 2)
        self.assertTrue(out.splitlines()[0].endswith("(states.merging.on.merged)"))
        self.assertNotIn("What bounds one run", out)
        self.assertNotIn(CANNOT_SEE, err)

    def test_the_status_document_and_the_map_carry_the_bounds(self):
        # Since section 12.5 the document ends with "measured", after the bounds.
        state = flow.status(answered("feature"))
        self.assertEqual(list(state)[-3:], ["waiting", "bounds", "measured"])
        self.assertEqual(state["bounds"], FEATURE_BOUNDS)
        lines = flow.render_map(state).splitlines()
        at = lines.index("This flow: feature, 18 steps, stops at ready_pr, up to 20 dollars and 240 minutes for one "
                         "ticket.")
        self.assertEqual(lines[at + 1:at + 1 + len(FEATURE_LINES)], FEATURE_LINES)
        self.assertEqual(lines[at + 1 + len(FEATURE_LINES)], "Levels 2 to 4 are read from real runs. Nothing measures "
                                                             "them yet.")
        fresh = flow.render_map(flow.status(flow.new("feature"))).splitlines()
        at = [n for n, line in enumerate(fresh) if line.startswith("This flow: ")][0]
        self.assertEqual(fresh[at + 1], FEATURE_LINES[0])
        self.assertIsNone(flow.status(case("merge-without-a-person"))["bounds"])
        self.assertNotIn(FEATURE_LINES[0], flow.render_map(flow.status(case("merge-without-a-person"))))

    def test_a_gate_nobody_can_judge_last_before_the_merge_is_not_to_be_removed(self):
        definition = answered("feature")
        definition["states"]["merge_auth"]["can_judge"] = "no"
        path = self.write("flow.json", definition)
        # Since the critics of section 12: human_review still guards the merge once merge_auth is removed,
        # so the note says what removing it changes, and does not say flow check would refuse the file.
        careful = ['Careful: merge_auth is the last gate before "merged". Removed, the last one would be human_review, '
                   "0 steps and 0 agents before the write.",
                   'Careful: merge_auth is the last gate before "deployed". Removed, the last one would be '
                   "human_review, 1 step and 0 agents before the write."]
        for argv in (["place", path], ["status", path], ["status", path, "--map"]):
            with self.subTest(argv=argv[0:1] + argv[2:]):
                code, out, err = call(*argv)
                self.assertEqual([line for line in err.splitlines() if line.startswith("Careful: merge_auth")],
                                 careful)
                self.assertNotIn("flow check would refuse", err)
                self.assertNotIn("Careful: merge_auth", out)
        self.assertEqual(call("place", path, "--format", "json")[2], "")
        other = copy.deepcopy(answered("feature"))
        other["states"]["plan_review"]["can_judge"] = "no"
        self.assertNotIn("is the last gate", call("place", self.write("other.json", other))[2])

    def test_the_only_gate_before_the_merge_nobody_can_judge_is_never_said_to_be_removed(self):
        definition = answered("bug")
        definition["states"]["human_review"]["can_judge"] = "no"
        path = self.write("bug.json", definition)
        keep = ('A gate nobody can judge: human_review. It is the last gate before "merged", which cannot be taken '
                "back: do not remove it; give a maintainer of the repository something they can read and refuse.")
        careful = ('Careful: human_review is the last gate before "merged", which cannot be taken back. Do not remove '
                   "it: flow check would refuse the file. Give a maintainer of the repository something they can read "
                   "and refuse.")
        code, out, err = call("place", path)
        self.assertEqual(code, 1)
        self.assertIn(keep, out.splitlines())
        self.assertNotIn("Remove it", out)
        self.assertIn(careful, err.splitlines())
        state = json.loads(call("status", path, "--format", "json")[1])
        self.assertEqual(state["next_step"], "Fix this first: " + keep)
        self.assertIn("  " + keep, call("status", path, "--map")[1].splitlines())

    def test_a_gate_still_guarded_by_another_one_may_be_removed(self):
        definition = answered("feature")
        definition["states"]["merge_auth"]["can_judge"] = "no"
        out = call("place", self.write("flow.json", definition))[1]
        self.assertIn("A gate nobody can judge: merge_auth. Remove it, or give a maintainer who is not the requester "
                      "something they can read and refuse.", out.splitlines())
        self.assertEqual(flow_paths.kept_gates(definition, ["merge_auth"]), {})
        bug = answered("bug")
        bug["states"]["human_review"]["can_judge"] = "no"
        self.assertEqual(flow_paths.kept_gates(bug, ["human_review"]), {"human_review": "merged"})
        self.assertEqual(flow_paths.kept_gates(case("merge-without-a-person"), ["human_review"]), {})


    def only_gate_nobody_can_judge(self) -> dict:
        """The feature flow with merge_auth the only gate before the merge, and nobody can judge it."""
        definition = answered("feature")
        for name in ("human_review", "rework"):
            del definition["states"][name]
        definition["states"]["mark_ready"]["on"]["marked_ready"]["to"] = "merge_auth"
        definition["states"]["merge_auth"]["can_judge"] = "no"
        return definition

    def test_an_unrelated_fault_never_turns_the_only_gate_into_one_to_remove(self):
        # Since the review of the change: kept gates are read whenever the file is not malformed, the
        # refusals it already has left aside, so a missing budget does not change what stdout offers.
        definition = self.only_gate_nobody_can_judge()
        del definition["budget"]
        self.assertEqual([p["code"] for p in flow.check(definition)], ["no_budget"])
        self.assertEqual(flow_paths.kept_gates(definition, ["merge_auth"]), {"merge_auth": "merged"})
        keep = ('A gate nobody can judge: merge_auth. It is the last gate before "merged", which cannot be taken '
                "back: do not remove it; give a maintainer who is not the requester something they can read and "
                "refuse.")
        path = self.write("nobudget.json", definition)
        out = call("place", path)[1]
        self.assertIn(keep, out.splitlines())
        self.assertNotIn("Remove it", out)
        self.assertIn("  " + keep, call("status", path, "--map")[1].splitlines())
        self.assertEqual(flow_paths.kept_gates({"states": "not a flow"}, ["merge_auth"]), {})

    def test_two_gates_nobody_can_judge_on_one_path_are_never_both_offered_for_removal(self):
        # Struck one at a time, each looked expendable; struck with the ones offered before it, the
        # last one before the merge is kept, and removing every gate offered leaves a flow that holds.
        definition = answered("feature")
        for name in ("human_review", "merge_auth"):
            definition["states"][name]["can_judge"] = "no"
        self.assertEqual(flow_paths.kept_gates(definition, ["human_review", "merge_auth"]), {"merge_auth": "merged"})
        path = self.write("two.json", definition)
        code, out, err = call("place", path)
        self.assertIn("A gate nobody can judge: human_review. Remove it, or give a reviewer who is not the requester "
                      "something they can read and refuse.", out.splitlines())
        # Since the fuzzing of the fix: merge_auth alone can go, human_review still guarding the merge, so
        # both sentences say it is the two together that flow check would refuse.
        self.assertIn('A gate nobody can judge: merge_auth. It is the last gate before "merged", which cannot be '
                      "taken back: do not remove it together with human_review; give a maintainer who is not the "
                      "requester something they can read and refuse.", out.splitlines())
        self.assertNotIn("Removed, the last one would be", err)
        self.assertIn('Careful: merge_auth is the last gate before "merged", which cannot be taken back. Do not '
                      "remove it together with human_review: flow check would then refuse the file. Give a maintainer "
                      "who is not the requester something they can read and refuse.", err.splitlines())
        removed = copy.deepcopy(definition)
        for name in ("human_review", "rework"):
            del removed["states"][name]
        removed["states"]["mark_ready"]["on"]["marked_ready"]["to"] = "merge_auth"
        self.assertEqual(flow.check(removed), [])

    # Issue 165, after the attacks on the fix: which gate is kept never depends on the order of the
    # states in the file, and the "Careful:" note strikes the gates offered before the one it reads.

    def reordered(self, definition: dict, names: list[str]) -> dict:
        """The same flow, the states of `names` written in that order where the first of them stood."""
        states = definition["states"]
        order = [name for name in states if name not in names]
        at = min(list(states).index(name) for name in names)
        out = copy.deepcopy(definition)
        out["states"] = {name: states[name] for name in order[:at] + names + order[at:]}
        return out

    def test_the_gate_kept_is_the_last_on_the_path_whatever_the_file_order(self):
        definition = answered("feature")
        for name in ("human_review", "merge_auth"):
            definition["states"][name]["can_judge"] = "no"
        remove = ("A gate nobody can judge: human_review. Remove it, or give a reviewer who is not the requester "
                  "something they can read and refuse.")
        keep = ('A gate nobody can judge: merge_auth. It is the last gate before "merged", which cannot be taken '
                "back: do not remove it together with human_review; give a maintainer who is not the requester "
                "something they can read and refuse.")
        swapped = self.reordered(definition, ["merge_auth", "human_review"])
        self.assertEqual(list(swapped["states"]).index("merge_auth") + 1, list(swapped["states"]).index("human_review"))
        for name, flow_file in (("as-written", definition), ("swapped", swapped)):
            with self.subTest(file=name):
                self.assertEqual(flow_paths.kept_gates(flow_file, ["human_review", "merge_auth"]),
                                 {"merge_auth": "merged"})
                path = self.write(f"{name}.json", flow_file)
                out, err = call("place", path)[1:]
                self.assertIn(remove, out.splitlines())
                self.assertIn(keep, out.splitlines())
                self.assertNotIn("Careful: merge_auth is the last gate before \"merged\". Removed", err)
                self.assertIn("  " + keep, call("status", path, "--map")[1].splitlines())

    def test_three_gates_nobody_can_judge_keep_the_one_nearest_the_merge(self):
        definition = answered("feature")
        definition["states"]["plan_size"]["on"]["plan_small"]["to"] = "plan_review"
        for name in ("plan_review", "human_review", "merge_auth"):
            definition["states"][name]["can_judge"] = "no"
        definition = self.reordered(definition, ["human_review", "merge_auth", "plan_review"])
        out, err = call("place", self.write("three.json", definition))[1:]
        lines = out.splitlines()
        self.assertIn("A gate nobody can judge: plan_review. Remove it, or give a maintainer of the repository "
                      "something they can read and refuse.", lines)
        self.assertIn("A gate nobody can judge: human_review. Remove it, or give a reviewer who is not the "
                      "requester something they can read and refuse.", lines)
        self.assertTrue([line for line in lines if line.startswith(
            'A gate nobody can judge: merge_auth. It is the last gate before "merged"')], lines)
        self.assertNotIn('plan_review. It is the last gate', out)

    def test_the_careful_note_strikes_the_gates_offered_before_the_one_it_reads(self):
        # plan_review, which every plan crosses, is the gate left once both refused gates are removed.
        definition = answered("feature")
        definition["states"]["plan_size"]["on"]["plan_small"]["to"] = "plan_review"
        for name in ("human_review", "merge_auth"):
            definition["states"][name]["can_judge"] = "no"
        out, err = call("place", self.write("plan.json", definition))[1:]
        self.assertIn("A gate nobody can judge: human_review. Remove it, or give a reviewer who is not the requester "
                      "something they can read and refuse.", out.splitlines())
        self.assertIn("A gate nobody can judge: merge_auth. Remove it, or give a maintainer who is not the requester "
                      "something they can read and refuse.", out.splitlines())
        careful = [line for line in err.splitlines() if line.startswith("Careful: merge_auth")]
        self.assertEqual(careful, [
            'Careful: merge_auth is the last gate before "merged". Removed, the last one would be plan_review, '
            "7 steps and 2 agents before the write.",
            'Careful: merge_auth is the last gate before "deployed". Removed, the last one would be plan_review, '
            "8 steps and 2 agents before the write."])
        removed = copy.deepcopy(definition)
        for name in ("human_review", "rework", "merge_auth"):
            del removed["states"][name]
        removed["states"]["mark_ready"]["on"]["marked_ready"]["to"] = "merging"
        guards = flow_paths.bounds(removed)["guards"]
        self.assertEqual([(g["last_gate"], g["steps_between"], g["agents_between"]) for g in guards],
                         [("plan_review", 7, 2), ("plan_review", 8, 2)])

    # Issue 165, after the fuzzing of the fix: a gate kept for one write is never offered for removal
    # by the note of another, the line names the write it keeps, and a bypass hides no gate.

    def test_a_gate_kept_for_another_write_is_never_offered_for_removal_in_a_careful_note(self):
        definition = case("triage-before-the-merge-authorisation")
        self.assertEqual(flow.check(definition), [])
        self.assertEqual(flow_paths.kept_writes(definition, ["human_review", "merge_auth"]),
                         {"human_review": ["states.delivery.on.deployed"],
                          "merge_auth": ["states.delivery.on.deployed"]})
        err = call("place", self.write("triage.json", definition))[2]
        self.assertNotIn("Removed, the last one would be", err)
        self.assertIn('Careful: merge_auth is the last gate before "merged". Do not remove it: flow check would '
                      'refuse the file, for "deployed", which cannot be taken back. Give a maintainer who is not the '
                      "requester something they can read and refuse.", err.splitlines())
        self.assertIn('Careful: human_review is the last gate before "deployed", which cannot be taken back. Do not '
                      "remove it: flow check would refuse the file. Give a reviewer who is not the requester "
                      "something they can read and refuse.", err.splitlines())
        removed = copy.deepcopy(definition)
        del removed["states"]["merge_auth"]
        removed["states"]["human_review"]["on"]["approved"]["to"] = "merging"
        self.assertEqual([(p["code"], p["where"]) for p in flow.check(removed)],
                         [("irreversible_without_gate", "states.delivery.on.deployed")])

    def test_the_line_of_a_kept_gate_names_a_write_it_is_the_last_gate_of_or_says_it_is_not(self):
        definition = case("triage-before-the-merge-authorisation")
        path = self.write("triage.json", definition)
        review = ('A gate nobody can judge: human_review. It is the last gate before "deployed", which cannot be '
                  "taken back: do not remove it; give a reviewer who is not the requester something they can read "
                  "and refuse.")
        merge = ('A gate nobody can judge: merge_auth. Without it, a run could reach "deployed", which cannot be '
                 "taken back, crossing no gate that guards it: do not remove it; give a maintainer who is not the "
                 "requester something they can read and refuse.")
        out = call("place", path)[1].splitlines()
        self.assertIn(review, out)
        self.assertIn(merge, out)
        lines = call("status", path, "--map")[1].splitlines()
        self.assertIn("  " + merge, lines)
        self.assertNotIn('merge_auth. It is the last gate before "deployed"', "\n".join(lines))

    def test_a_kept_gate_that_can_go_alone_is_said_to_be_kept_only_with_the_others(self):
        definition = answered("feature")
        for name in ("human_review", "merge_auth"):
            definition["states"][name]["can_judge"] = "no"
        alone = copy.deepcopy(definition)
        del alone["states"]["merge_auth"]
        alone["states"]["human_review"]["on"]["approved"]["to"] = "merging"
        self.assertEqual(flow.check(alone), [])
        out = call("place", self.write("two.json", definition))[1]
        self.assertNotIn("merge_auth. It is the last gate before \"merged\", which cannot be taken back: do not "
                         "remove it;", out)
        self.assertIn("do not remove it together with human_review;", out)

    def test_a_bypass_never_turns_the_gate_nearest_the_write_into_one_to_remove(self):
        definition = case("bypass-and-two-gates-nobody-can-judge")
        self.assertEqual(flow_paths.kept_gates(definition, ["human_review", "merge_auth"]), {"merge_auth": "merged"})
        out = call("place", self.write("bypass.json", definition))[1].splitlines()
        self.assertIn("A gate nobody can judge: human_review. Remove it, or give a reviewer who is not the requester "
                      "something they can read and refuse.", out)
        self.assertIn('A gate nobody can judge: merge_auth. Without it, a run could reach "merged", which cannot be '
                      "taken back, crossing no gate that guards it: do not remove it; give a maintainer who is not "
                      "the requester something they can read and refuse.", out)
        # While the bypass is there, the refusal of human_review leads to it: human_review guards nothing,
        # so removing merge_auth alone already opens a way from the human review to the merge.
        closed = copy.deepcopy(definition)
        del closed["states"]["review_checks"]["on"]["trivial"]
        for name in ("human_review", "rework"):
            del closed["states"][name]
        closed["states"]["mark_ready"]["on"]["marked_ready"]["to"] = "merge_auth"
        self.assertEqual(flow.check(closed), [])

    def test_no_gate_is_offered_for_removal_while_a_fault_hides_the_paths(self):
        # A malformed file (a step nobody leads to, or the default list written in a flow that never
        # deploys) or an unknown step type: whether the flow can lose the gate is not read yet.
        bug = answered("bug")
        bug["states"]["human_review"]["can_judge"] = "no"
        orphan = copy.deepcopy(bug)
        orphan["states"]["sec_review"] = {"type": "code", "does": "Nothing", "survives": "restart", "units": "one",
                                          "repositories": "one", "on": {"done_it": {"to": "done"}}}
        listed = copy.deepcopy(bug)
        listed["irreversible"] = ["merged", "deployed"]
        feature = answered("feature")
        for name in ("human_review", "merge_auth"):
            feature["states"][name]["can_judge"] = "no"
        feature["states"]["closing"]["type"] = "program"
        for name, flow_file in (("orphan", orphan), ("listed", listed), ("typo", feature)):
            with self.subTest(file=name):
                self.assertTrue(flow.check(flow_file))
                path = self.write(f"{name}.json", flow_file)
                out = call("place", path)[1]
                self.assertNotIn("Remove it", out)
                self.assertNotIn("Remove it", call("status", path, "--map")[1])
                self.assertNotIn("Remove it", json.loads(call("status", path, "--format", "json")[1])["next_step"])
                self.assertIn("A gate nobody can judge: human_review. Give ", out)

    def test_a_person_who_only_writes_a_draft_by_hand_decides_no_merge(self):
        # Rule 1 counts a person's write of a merge or a deploy, not any write: a person who works decides nothing.
        definition = case("merge-without-a-person")
        draft = definition["states"]["draft_pr"]
        for key in ("checks_premise", "survives", "units", "repositories", "writes"):
            draft.pop(key, None)
        draft.update({"type": "human", "deadline_hours": 1})
        self.assertEqual([p["where"] for p in flow.check(definition)],
                         ["states.merging.on.merged", "states.delivery.on.deployed"])


if __name__ == "__main__":
    unittest.main()
