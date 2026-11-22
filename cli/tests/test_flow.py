"""Tests of `harness flow`: a team's workflow written down as a small table of states, checked
before anything runs. `flow check` refuses a definition that could loop, wait or spend without
end; `flow next` is the one function that says what a run does on an event, and it never passes
a cap or the budget. The contract is docs/workflow-harness/flow-spec.md."""
from __future__ import annotations

import contextlib
import copy
import io
import json
import os
import random
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import harness  # noqa: E402
from harnesslib import flow  # noqa: E402

# The complete small example of the contract, section 1.
SMALL = json.loads("""
{"format": 1, "name": "small", "kind": "feature",
 "start": "ready", "stop_at": "draft_pr", "budget": {"dollars": 5, "minutes": 60},
 "states": {
  "ready": {"type": "code", "does": "Checks the ticket is eligible and claims it",
            "survives": "restart", "units": "one", "repositories": "one",
            "writes": [{"what": "the run record", "key": "run-{ticket}"}],
            "on": {"claimed": {"to": "coding"}, "not_eligible": {"to": "stopped", "reason": "not_eligible"}}},
  "coding": {"type": "agent", "does": "Implements the ticket and its tests", "cap": 3,
             "survives": "restart", "units": "one", "repositories": "one", "weak_model": "no",
             "on": {"code_written": {"to": "checks"}}},
  "checks": {"type": "code", "does": "Runs format, lint, build and the selected tests",
             "survives": "restart", "units": "one", "repositories": "one",
             "on": {"checks_passed": {"to": "push"}, "checks_failed": {"to": "coding"}}},
  "push": {"type": "code", "does": "Pushes the branch, so that a person can read it",
           "survives": "restart", "units": "one", "repositories": "one",
           "writes": [{"what": "the branch", "key": "flow/{ticket}"}],
           "on": {"pushed": {"to": "approval"}}},
  "approval": {"type": "gate", "does": "A maintainer reads the branch and says whether a PR may be opened",
               "judge": "a maintainer of the repository", "shows": "the branch", "deadline_hours": 48, "can_judge": "yes",
               "on": {"approved": {"to": "open_pr"}, "refused": {"to": "stopped", "reason": "refused"}}},
  "open_pr": {"type": "code", "does": "Checks the branch is still the one approved, then opens a draft PR linked to the ticket",
              "checks_premise": true, "survives": "restart", "units": "one", "repositories": "one",
              "writes": [{"what": "the draft PR", "key": "pr-{ticket}"}],
              "on": {"pr_opened": {"to": "ci_wait", "reaches": "draft_pr"},
                     "head_moved": {"to": "stopped", "reason": "head_moved"}}},
  "ci_wait": {"type": "wait", "does": "Waits for CI on the pushed commit", "cap": 3, "deadline_hours": 6,
              "on": {"ci_finished": {"to": "ci_check"}}},
  "ci_check": {"type": "code", "does": "Checks the CI result is for the current commit and reads it",
               "checks_premise": true, "survives": "restart", "units": "one", "repositories": "one",
               "on": {"ci_green": {"to": "done", "reason": "ci_green"}, "ci_red": {"to": "stopped", "reason": "ci_red"},
                      "ci_stale": {"to": "ci_wait"}}}}}
""")

# The two templates as the contract fixes them: state, type, cap, then `event>target[stop point](reason)`.
FEATURE_TABLE = """
ready code - claimed>planning not_eligible>stopped(not_eligible)
planning agent 3 plan_written>plan_size
plan_size code - plan_small>coding[plan] plan_large>plan_review[plan]
plan_review gate - plan_approved>coding plan_rejected>planning
coding agent 6 code_written>checks
checks code - checks_passed>draft_pr checks_failed>coding
draft_pr code - pr_opened>ci_wait[draft_pr]
ci_wait wait 8 ci_finished>ci_check
ci_check code - ci_green>review_checks ci_red>ci_fix ci_stale>ci_wait
ci_fix agent 2 fix_pushed>ci_wait
review_checks agent - review_done>mark_ready review_failed>coding
mark_ready code - marked_ready>human_review[ready_pr]
human_review gate - approved>merge_auth changes_requested>rework
rework code 2 comments_collected>coding
merge_auth gate - merge_authorised>merging merge_refused>stopped(merge_refused)
merging code - merged>delivery[merged] head_moved>stopped(head_moved) merge_failed>stopped(merge_failed)
delivery wait - deployed>closing[deployed] deploy_failed>stopped(deploy_failed)
closing code - closed>done(delivered) premise_failed>stopped(premise_failed)
"""
BUG_TABLE = """
triage code - ticket_ready>premise duplicate_found>done(duplicate) not_eligible>stopped(not_eligible)
premise agent - still_fails>root_cause already_fixed>done(already_fixed) cannot_reproduce>stopped(cannot_reproduce)
root_cause agent 5 cause_written>notify
notify code - confident>repro[root_cause] low_confidence>stopped(low_confidence)
repro agent - repro_written>fix[plan]
fix agent - fix_written>verify
verify code - verified>draft_pr verify_failed>root_cause
draft_pr code - pr_opened>ci_wait[draft_pr]
ci_wait wait 4 ci_finished>ci_check
ci_check code - ci_green>human_review[ready_pr] ci_red>ci_fix ci_stale>ci_wait
ci_fix agent 2 fix_pushed>ci_wait
human_review gate - merged_by_human>closure_wait[merged] closed_with_reason>done(rejected)
closure_wait wait - closure_due>closure_check
closure_check code - signal_stopped>done(fixed) signal_continues>stopped(not_fixed)
"""
TEMPLATE_FACTS = {
    "feature": {"table": FEATURE_TABLE, "start": "ready", "stop_at": "ready_pr",
                "budget": {"dollars": 20, "minutes": 240},
                "premise": {"ci_check", "merging", "closing"},
                "shows": {"plan_review": "the plan", "human_review": "the pull request",
                          "merge_auth": "the pull request"},
                "writes": {"ready": [("the run record", "run-{ticket}")],
                           "plan_size": [("the plan", "plan-{ticket}")],
                           "draft_pr": [("the branch", "flow/{ticket}"), ("the pull request", "pr-{ticket}")],
                           "ci_fix": [("the branch", "flow/{ticket}")],
                           "mark_ready": [("the pull request", "pr-{ticket}")],
                           "merging": [("the merge", "merge-{ticket}")],
                           "closing": [("the closing note", "close-{ticket}")]}},
    "bug": {"table": BUG_TABLE, "start": "triage", "stop_at": "root_cause",
            "budget": {"dollars": 10, "minutes": 120},
            "premise": {"premise", "ci_check", "closure_check"},
            "shows": {"human_review": "the pull request"},
            "writes": {"triage": [("the run record", "run-{ticket}")],
                       "notify": [("the root cause note", "cause-{ticket}")],
                       "draft_pr": [("the branch", "flow/{ticket}"), ("the pull request", "pr-{ticket}")],
                       "ci_fix": [("the branch", "flow/{ticket}")],
                       "closure_check": [("the closing note", "close-{ticket}")]}},
}
OUTPUT_KEYS = {"outcome", "reason", "transition", "message", "run", "remaining", "over_budget"}
OUTCOMES = {"moved", "done", "stopped", "duplicate", "refused"}
COST = {"dollars": 0.25, "minutes": 2}


def parse_table(text: str) -> list[tuple[str, str, int | None, dict]]:
    """Rows of a template table: (state, type, cap, {event: transition})."""
    rows = []
    for line in text.strip().splitlines():
        name, kind, cap, *cells = line.split()
        on = {}
        for cell in cells:
            event, rest = cell.split(">")
            transition: dict = {}
            if "(" in rest:
                rest, reason = rest[:-1].split("(")
                transition["reason"] = reason
            if "[" in rest:
                rest, reaches = rest[:-1].split("[")
                transition["reaches"] = reaches
            on[event] = {"to": rest, **transition}
        rows.append((name, kind, None if cap == "-" else int(cap), on))
    return rows


def small(**changes) -> dict:
    """A fresh copy of the small flow, with top-level keys replaced."""
    definition = copy.deepcopy(SMALL)
    definition.update(changes)
    return definition


def found(definition) -> list[tuple[str, str]]:
    return [(p["code"], p["where"]) for p in flow.check(definition)]


def run_at(state: str, visits: dict, spent=(0, 0), seen=()) -> dict:
    return {"state": state, "visits": dict(visits), "spent": {"dollars": spent[0], "minutes": spent[1]},
            "seen": list(seen), "reason": None}


def event(ident: str, kind: str, cost: dict | None = COST, at: tuple[str, int] | None = None) -> dict:
    document: dict = {"id": ident, "type": kind}
    if cost is not None:
        document["payload"] = dict(cost)
    if at is not None:
        document["at"] = {"state": at[0], "visit": at[1]}
    return document


def call(argv: list[str]) -> tuple[int, str, str]:
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            code = harness.main(argv)
        except SystemExit as exc:  # argparse refuses a wrong usage by exiting
            code = exc.code
    return code, out.getvalue(), err.getvalue()


class TemplatesTest(unittest.TestCase):
    def test_the_constants_are_the_ones_of_the_contract(self):
        self.assertEqual(flow.STEP_TYPES, ("code", "agent", "human", "gate", "wait"))
        self.assertEqual(flow.ENDED, ("done", "stopped"))
        self.assertEqual(flow.TEMPLATES, ("feature", "bug"))
        self.assertEqual(flow.BUILT_IN_EVENTS, ("human_stop", "deadline_passed", "step_failed"))
        self.assertEqual(flow.TYPE_WORDS, {"code": "a program", "agent": "an agent", "human": "a person works",
                                           "gate": "a person decides", "wait": "waits"})

    def test_both_templates_and_the_small_example_pass_check(self):
        for kind in flow.TEMPLATES:
            with self.subTest(kind=kind):
                self.assertEqual(flow.check(flow.new(kind)), [])
        self.assertEqual(flow.check(SMALL), [])

    def test_each_template_has_the_states_events_caps_and_stop_points_of_the_contract(self):
        for kind, facts in TEMPLATE_FACTS.items():
            definition = flow.new(kind)
            rows = parse_table(facts["table"])
            with self.subTest(kind=kind):
                self.assertEqual(definition["format"], 1)
                self.assertEqual(definition["name"], kind)
                self.assertEqual(definition["start"], facts["start"])
                self.assertEqual(definition["stop_at"], facts["stop_at"])
                self.assertEqual(definition["budget"], facts["budget"])
                self.assertEqual(list(definition["states"]), [row[0] for row in rows])
            for name, kind_of_step, cap, on in rows:
                state = definition["states"][name]
                with self.subTest(kind=kind, state=name):
                    self.assertEqual(state["type"], kind_of_step)
                    self.assertEqual(state.get("cap"), cap)
                    self.assertEqual(state["on"], on)
                    self.assertEqual(state.get("checks_premise", False), name in facts["premise"])
                    self.assertEqual([(w["what"], w["key"]) for w in state.get("writes", [])],
                                     facts["writes"].get(name, []))
                    self.assertEqual(state.get("shows"), facts["shows"].get(name))
                    self.assertTrue(state["does"].strip())

    def test_each_template_answers_the_placement_questions_as_the_contract_says(self):
        for kind in flow.TEMPLATES:
            for name, state in flow.new(kind)["states"].items():
                with self.subTest(kind=kind, state=name):
                    if state["type"] in ("code", "agent"):
                        self.assertEqual((state["survives"], state["units"], state["repositories"]),
                                         ("restart", "one", "one"))
                    if state["type"] == "agent":
                        self.assertEqual(state["weak_model"], "no")
                    if state["type"] == "gate":
                        self.assertEqual((state["can_judge"], state["deadline_hours"]), ("yes", 72))
                        self.assertTrue(state["judge"].strip())
                    if state["type"] == "wait":
                        self.assertEqual(state["deadline_hours"], 6 if name == "ci_wait" else 168)

    def test_new_gives_a_fresh_copy_each_time(self):
        first = flow.new("feature")
        first["states"]["coding"]["cap"] = 99
        self.assertEqual(flow.new("feature")["states"]["coding"]["cap"], 6)

    def test_new_refuses_a_kind_it_has_no_template_for(self):
        for kind in ("incident", "", "../feature", None):
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                flow.new(kind)

    def test_load_definition_returns_any_json_value_and_validates_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "list.json")
            with open(path, "w", encoding="utf-8") as fh:
                fh.write('["not", "a", "flow"]')
            self.assertEqual(flow.load_definition(path), ["not", "a", "flow"])

    def test_load_definition_raises_with_the_path_when_the_file_is_missing_or_not_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            missing = os.path.join(tmp, "absent.json")
            broken = os.path.join(tmp, "broken.json")
            with open(broken, "w", encoding="utf-8") as fh:
                fh.write("{not json")
            for path in (missing, broken):
                with self.subTest(path=os.path.basename(path)):
                    with self.assertRaises(ValueError) as caught:
                        flow.load_definition(path)
                    self.assertTrue(str(caught.exception).startswith(path))


class CheckMalformedTest(unittest.TestCase):
    """`malformed` comes first and alone: the other rules need a readable structure."""

    def assert_malformed(self, definition, where: str):
        problems = flow.check(definition)
        self.assertTrue(problems, "the definition was accepted")
        self.assertEqual({p["code"] for p in problems}, {"malformed"})
        self.assertIn(where, [p["where"] for p in problems])
        for problem in problems:
            self.assertEqual(set(problem), {"code", "message", "where"})
            self.assertTrue(problem["message"].startswith("The file cannot be read as a flow: "))

    def test_a_value_that_is_not_an_object(self):
        for value in ([], "flow", 3, None, True):
            with self.subTest(value=value):
                self.assert_malformed(value, "")

    def test_the_top_level_keys(self):
        cases = [
            ("format", {"format": 2}), ("format", {"format": "1"}), ("format", {"format": True}),
            ("format", {"format": 1.0}),
            ("name", {"name": "Small Flow"}), ("name", {"name": 3}),
            ("start", {"start": "nowhere"}), ("start", {"start": 1}),
            ("states", {"states": {}}), ("states", {"states": []}),
            ("stop_at", {"stop_at": "Draft PR"}), ("stop_at", {"stop_at": None}),
        ]
        for where, change in cases:
            with self.subTest(change=change):
                self.assert_malformed(small(**change), where)
        for key in ("format", "name", "start", "states"):
            with self.subTest(missing=key):
                definition = small()
                del definition[key]
                self.assert_malformed(definition, key)

    def test_a_state(self):
        def with_state(name, state):
            definition = small()
            definition["states"][name] = state
            definition["states"]["ready"]["on"]["extra"] = {"to": name}  # reachable, whatever its name
            return definition

        valid = {"type": "code", "does": "Does something", "on": {"ended": {"to": "done"}}}
        cases = [
            ("Bad-Name", valid), ("done", valid), ("stopped", valid),
            ("extra_step", "a sentence"),
            ("extra_step", {**valid, "does": ""}), ("extra_step", {**valid, "does": 3}),
            ("extra_step", {k: v for k, v in valid.items() if k != "does"}),
            ("extra_step", {**valid, "on": {}}), ("extra_step", {**valid, "on": []}),
            ("extra_step", {k: v for k, v in valid.items() if k != "on"}),
            ("extra_step", {**valid, "cap": 0}), ("extra_step", {**valid, "cap": 1.5}),
            ("extra_step", {**valid, "cap": True}), ("extra_step", {**valid, "cap": "3"}),
            ("extra_step", {**valid, "writes": {"what": "x", "key": "x-{ticket}"}}),
            ("extra_step", {**valid, "writes": ["the branch"]}),
            ("extra_step", {**valid, "checks_premise": "yes"}),
            ("extra_step", {**valid, "type": "wait", "deadline_hours": 1, "checks_premise": True}),
        ]
        for name, state in cases:
            with self.subTest(name=name, state=state):
                definition = with_state(name, state)
                if name in ("done", "stopped"):  # the name would otherwise read as an end state
                    del definition["states"]["ready"]["on"]["extra"]
                self.assert_malformed(definition, f"states.{name}")

    def test_a_state_no_path_leads_to(self):
        definition = small()
        definition["states"]["island"] = {"type": "code", "does": "Never reached",
                                          "on": {"ended": {"to": "done"}}}
        self.assert_malformed(definition, "states.island")

    def test_a_transition(self):
        cases = [
            ("checks", "Bad-Event", {"to": "push"}),
            ("checks", "extra", "push"),
            ("checks", "extra", {"reason": "no_target"}),
            ("checks", "extra", {"to": "nowhere"}),
            ("checks", "extra", {"to": ["push"]}),
            ("checks", "extra", {"to": "stopped"}),
            ("checks", "extra", {"to": "done", "reason": "Not A Name"}),
            ("checks", "extra", {"to": "push", "reaches": 3}),
            ("checks", "human_stop", {"to": "stopped", "reason": "human_stop"}),
            ("approval", "step_failed", {"to": "stopped", "reason": "step_failed"}),
            ("ci_wait", "step_failed", {"to": "ci_wait"}),
        ]
        for state, name, transition in cases:
            with self.subTest(state=state, event=name, transition=transition):
                definition = small()
                definition["states"][state]["on"][name] = transition
                self.assert_malformed(definition, f"states.{state}.on.{name}")

    def test_malformed_hides_the_other_refusals(self):
        definition = small(format=2)
        del definition["budget"]
        self.assertEqual(found(definition), [("malformed", "format")])

    def test_the_built_in_events_that_may_be_declared_are_accepted(self):
        definition = small()
        definition["states"]["coding"]["on"]["step_failed"] = {"to": "coding"}
        definition["states"]["approval"]["on"]["deadline_passed"] = {"to": "stopped", "reason": "nobody_answered"}
        self.assertEqual(flow.check(definition), [])

    def test_unknown_keys_are_ignored(self):
        definition = small(owner="the platform team")
        definition["states"]["coding"]["note"] = "anything"
        definition["states"]["coding"]["on"]["code_written"]["note"] = 3
        self.assertEqual(flow.check(definition), [])


class CheckRefusalsTest(unittest.TestCase):
    """One refusal per way a flow could loop, wait, spend or be approved without end."""

    def test_unknown_step_type(self):
        for change in ({"type": "robot"}, {"type": None}, {"type": ["code"]}):
            with self.subTest(change=change):
                definition = small()
                definition["states"]["checks"].update(change)
                self.assertEqual(found(definition), [("unknown_step_type", "states.checks")])
        definition = small()
        del definition["states"]["checks"]["type"]
        self.assertEqual(found(definition), [("unknown_step_type", "states.checks")])

    def test_a_state_of_unknown_type_is_left_out_of_the_rules_that_read_the_type(self):
        definition = small()
        definition["states"]["approval"]["type"] = "committee"
        del definition["states"]["approval"]["judge"]
        del definition["states"]["approval"]["deadline_hours"]
        self.assertEqual(found(definition), [("unknown_step_type", "states.approval")])

    def test_loop_without_cap(self):
        definition = small()
        del definition["states"]["coding"]["cap"]
        self.assertEqual(found(definition), [("loop_without_cap", "states.coding")])
        problem = flow.check(definition)[0]
        self.assertIn("coding, checks", problem["message"])

    def test_a_state_that_loops_on_itself_without_a_cap(self):
        definition = small()
        definition["states"]["push"]["on"]["push_failed"] = {"to": "push"}
        self.assertEqual(found(definition), [("loop_without_cap", "states.push")])

    def test_one_problem_per_group_of_states_that_repeat(self):
        definition = small()
        del definition["states"]["coding"]["cap"]
        del definition["states"]["ci_wait"]["cap"]
        self.assertEqual(found(definition), [("loop_without_cap", "states.coding"),
                                             ("loop_without_cap", "states.ci_wait")])

    def test_a_cap_anywhere_in_the_circle_bounds_it(self):
        definition = small()
        del definition["states"]["coding"]["cap"]
        definition["states"]["checks"]["cap"] = 4
        self.assertEqual(flow.check(definition), [])

    def test_write_without_key(self):
        cases = [{"what": "the branch"}, {"what": "the branch", "key": "flow/branch"},
                 {"what": "the branch", "key": 3}, {"key": "flow/{ticket}"},
                 {"what": "", "key": "flow/{ticket}"}, {"what": 3, "key": "flow/{ticket}"}]
        for entry in cases:
            with self.subTest(entry=entry):
                definition = small()
                definition["states"]["coding"]["writes"] = [entry]
                self.assertEqual(found(definition), [("write_without_key", "states.coding.writes[0]")])

    def test_one_key_names_one_thing(self):
        definition = small()
        definition["states"]["open_pr"]["writes"].append({"what": "the pull request body", "key": "flow/{ticket}"})
        self.assertEqual(found(definition), [("write_without_key", "states.open_pr.writes[1]")])
        self.assertIn("the branch", flow.check(definition)[0]["message"])

    def test_the_same_key_for_the_same_thing_is_fine(self):
        definition = small()
        definition["states"]["open_pr"]["writes"].append({"what": "the branch", "key": "flow/{ticket}"})
        self.assertEqual(flow.check(definition), [])

    def test_no_stop_point(self):
        missing = small()
        del missing["stop_at"]
        self.assertEqual(found(missing), [("no_stop_point", "stop_at")])
        self.assertEqual(found(small(stop_at="merged")), [("no_stop_point", "stop_at")])

    def test_a_stop_point_only_reached_by_a_transition_to_stopped_does_not_count(self):
        definition = small(stop_at="refusal")
        definition["states"]["approval"]["on"]["refused"]["reaches"] = "refusal"
        self.assertEqual(found(definition), [("no_stop_point", "stop_at")])

    def test_no_budget(self):
        budgets = [None, 5, [], {}, {"dollars": 5}, {"minutes": 60}, {"dollars": 0, "minutes": 60},
                   {"dollars": 5, "minutes": -1}, {"dollars": "5", "minutes": 60},
                   {"dollars": True, "minutes": 60}, {"dollars": float("inf"), "minutes": 60},
                   {"dollars": 5, "minutes": float("nan")}]
        for budget in budgets:
            with self.subTest(budget=budget):
                self.assertEqual(found(small(budget=budget)), [("no_budget", "budget")])
        missing = small()
        del missing["budget"]
        self.assertEqual(found(missing), [("no_budget", "budget")])

    def test_wait_without_premise_check_after_a_wait(self):
        definition = small()
        del definition["states"]["ci_check"]["checks_premise"]
        self.assertEqual(found(definition), [("wait_without_premise_check", "states.ci_wait.on.ci_finished")])

    def test_wait_without_premise_check_after_a_person_who_works(self):
        definition = small()
        definition["states"]["push"]["on"]["pushed"] = {"to": "handover"}
        definition["states"]["handover"] = {"type": "human", "does": "A person prepares the release note",
                                            "deadline_hours": 24, "on": {"note_ready": {"to": "approval"},
                                                                         "abandoned": {"to": "ready"}}}
        self.assertEqual(found(definition), [("wait_without_premise_check", "states.handover.on.abandoned")])

    def test_wait_without_premise_check_after_a_gate_only_when_the_next_step_writes(self):
        definition = small()
        del definition["states"]["open_pr"]["checks_premise"]
        self.assertEqual(found(definition), [("wait_without_premise_check", "states.approval.on.approved")])
        del definition["states"]["open_pr"]["writes"]
        self.assertEqual(flow.check(definition), [])

    def test_a_premise_check_with_one_way_out(self):
        definition = small()
        definition["states"]["coding"]["checks_premise"] = True
        self.assertEqual(found(definition), [("wait_without_premise_check", "states.coding")])

    def test_wait_without_deadline(self):
        for change in (None, {"deadline_hours": 0}, {"deadline_hours": "6"}, {"deadline_hours": True}):
            with self.subTest(change=change):
                definition = small()
                if change is None:
                    del definition["states"]["ci_wait"]["deadline_hours"]
                else:
                    definition["states"]["ci_wait"].update(change)
                self.assertEqual(found(definition), [("wait_without_deadline", "states.ci_wait")])

    def test_a_person_who_works_needs_a_deadline_too(self):
        definition = small()
        definition["states"]["push"]["on"]["pushed"] = {"to": "handover"}
        definition["states"]["handover"] = {"type": "human", "does": "A person prepares the release note",
                                            "on": {"note_ready": {"to": "approval"}}}
        self.assertEqual(found(definition), [("wait_without_deadline", "states.handover")])

    def test_gate_without_judge(self):
        for judge in (None, "", 3):
            with self.subTest(judge=judge):
                definition = small()
                definition["states"]["approval"]["judge"] = judge
                self.assertEqual(found(definition), [("gate_without_judge", "states.approval")])
        definition = small()
        del definition["states"]["approval"]["judge"]
        self.assertEqual(found(definition), [("gate_without_judge", "states.approval")])

    def test_gate_without_deadline(self):
        definition = small()
        del definition["states"]["approval"]["deadline_hours"]
        self.assertEqual(found(definition), [("gate_without_deadline", "states.approval")])
        definition["states"]["approval"]["deadline_hours"] = -2
        self.assertEqual(found(definition), [("gate_without_deadline", "states.approval")])

    def test_gate_cannot_refuse(self):
        definition = small()
        del definition["states"]["approval"]["on"]["refused"]
        self.assertEqual(found(definition), [("gate_cannot_refuse", "states.approval")])

    def test_two_events_to_the_same_target_or_a_deadline_are_not_a_refusal(self):
        definition = small()
        definition["states"]["approval"]["on"] = {
            "approved": {"to": "open_pr"}, "approved_with_remarks": {"to": "open_pr"},
            "deadline_passed": {"to": "stopped", "reason": "nobody_answered"}}
        self.assertEqual(found(definition), [("gate_cannot_refuse", "states.approval")])

    def test_gate_shows_nothing(self):
        for shows in (None, "", "the design document", ["the branch"]):
            with self.subTest(shows=shows):
                definition = small()
                definition["states"]["approval"]["shows"] = shows
                self.assertEqual(found(definition), [("gate_shows_nothing", "states.approval")])
        definition = small()
        del definition["states"]["approval"]["shows"]
        self.assertEqual(found(definition), [("gate_shows_nothing", "states.approval")])

    def test_a_gate_cannot_show_what_only_itself_writes(self):
        definition = small()
        definition["states"]["approval"]["shows"] = "the verdict"
        definition["states"]["approval"]["writes"] = [{"what": "the verdict", "key": "verdict-{ticket}"}]
        self.assertEqual(found(definition), [("gate_shows_nothing", "states.approval")])

    def test_the_problems_come_in_the_order_of_the_table_then_of_the_file(self):
        definition = small()
        del definition["budget"]
        del definition["stop_at"]
        del definition["states"]["approval"]["judge"]
        del definition["states"]["ci_wait"]["deadline_hours"]
        del definition["states"]["coding"]["cap"]
        definition["states"]["ready"]["writes"] = [{"what": "the run record"}]
        definition["states"]["push"]["type"] = "robot"
        self.assertEqual(found(definition), [
            ("unknown_step_type", "states.push"), ("loop_without_cap", "states.coding"),
            ("write_without_key", "states.ready.writes[0]"), ("no_stop_point", "stop_at"),
            ("no_budget", "budget"), ("wait_without_deadline", "states.ci_wait"),
            ("gate_without_judge", "states.approval")])

    def test_check_never_raises_whatever_it_is_given(self):
        junk = [None, 0, "x", [], {}, {"states": None}, {"states": {"a": None}}, {"states": {"a": {"on": 3}}},
                {"format": 1, "name": "x", "start": "a", "states": {"a": {"on": {"e": None}}}},
                {"format": 1, "name": "x", "start": ["a"], "states": {"a": {"on": {"e": {"to": {}}}}}},
                {"format": 1, "name": "x", "start": "a", "states": {3: {}, "a": {"type": {}, "does": "x",
                                                                         "on": {"e": {"to": "a"}}}}},
                small(budget={"dollars": 10 ** 400, "minutes": 1})]
        for value in junk:
            with self.subTest(value=repr(value)[:60]):
                problems = flow.check(value)
                self.assertIsInstance(problems, list)
                for problem in problems:
                    self.assertEqual(set(problem), {"code", "message", "where"})


class NextStateTest(unittest.TestCase):
    """The transition function, rule by rule, on the small flow."""

    def step(self, run, evt, definition=SMALL):
        before = copy.deepcopy((definition, run, evt))
        out = flow.next_state(definition, run, evt)
        self.assertEqual((definition, run, evt), before, "next_state changed one of its arguments")
        self.assertEqual(set(out), OUTPUT_KEYS)
        self.assertIn(out["outcome"], OUTCOMES)
        self.assertIsInstance(out["message"], str)
        self.assertTrue(out["message"])
        self.assertIsNot(out["run"], run)
        return out

    def assert_refused(self, out, reason, run):
        self.assertEqual((out["outcome"], out["reason"], out["transition"]), ("refused", reason, None))
        self.assertEqual(out["run"], run)

    def test_new_run_is_the_run_before_any_event(self):
        self.assertEqual(flow.new_run(SMALL), {"state": "ready", "visits": {"ready": 1},
                                               "spent": {"dollars": 0, "minutes": 0}, "seen": [], "reason": None})

    def test_worked_example_a_legal_transition_with_a_cost(self):
        run = run_at("checks", {"ready": 1, "coding": 1, "checks": 1}, (1.25, 14), ["evt-1", "evt-2"])
        out = self.step(run, event("evt-3", "checks_failed", {"dollars": 0.5, "minutes": 6}))
        self.assertEqual({k: v for k, v in out.items() if k != "message"}, {
            "outcome": "moved", "reason": None,
            "transition": {"from": "checks", "event": "checks_failed", "to": "coding"},
            "run": {"state": "coding", "visits": {"ready": 1, "coding": 2, "checks": 1},
                    "spent": {"dollars": 1.75, "minutes": 20}, "seen": ["evt-1", "evt-2", "evt-3"], "reason": None},
            "remaining": {"dollars": 3.25, "minutes": 40}, "over_budget": False})

    def test_worked_example_the_same_event_delivered_again(self):
        run = run_at("checks", {"ready": 1, "coding": 1, "checks": 1}, (1.25, 14), ["evt-1", "evt-2"])
        evt = event("evt-3", "checks_failed", {"dollars": 0.5, "minutes": 6})
        first = self.step(run, evt)
        again = self.step(first["run"], evt)
        self.assertEqual((again["outcome"], again["reason"], again["transition"]), ("duplicate", "already_seen", None))
        self.assertEqual(again["run"], first["run"])
        self.assertEqual((again["remaining"], again["over_budget"]), (first["remaining"], first["over_budget"]))

    def test_worked_example_a_cap_reached(self):
        run = run_at("checks", {"ready": 1, "coding": 3, "checks": 3}, (3, 40), [f"evt-{i}" for i in range(1, 7)])
        out = self.step(run, event("evt-7", "checks_failed", {"dollars": 0.25, "minutes": 2}))
        self.assertEqual({k: v for k, v in out.items() if k != "message"}, {
            "outcome": "stopped", "reason": "cap_reached",
            "transition": {"from": "checks", "event": "checks_failed", "to": "stopped"},
            "run": {"state": "stopped", "visits": {"ready": 1, "coding": 3, "checks": 3},
                    "spent": {"dollars": 3.25, "minutes": 42},
                    "seen": [f"evt-{i}" for i in range(1, 8)], "reason": "cap_reached"},
            "remaining": {"dollars": 1.75, "minutes": 18}, "over_budget": False})

    def test_rule_1_a_malformed_event_is_refused_and_the_run_given_back(self):
        run = flow.new_run(SMALL)
        events = [None, [], "claimed", 3,
                  {"type": "claimed"}, {"id": "", "type": "claimed"}, {"id": 3, "type": "claimed"},
                  {"id": "e1"}, {"id": "e1", "type": ""}, {"id": "e1", "type": ["claimed"]},
                  {"id": "e1", "type": "claimed", "payload": None},
                  {"id": "e1", "type": "claimed", "payload": [1, 2]},
                  {"id": "e1", "type": "claimed", "payload": {"dollars": -1, "minutes": 1}},
                  {"id": "e1", "type": "claimed", "payload": {"dollars": "1", "minutes": 1}},
                  {"id": "e1", "type": "claimed", "payload": {"dollars": 1, "minutes": True}},
                  {"id": "e1", "type": "claimed", "payload": {"dollars": 1, "minutes": float("nan")}},
                  {"id": "e1", "type": "claimed", "payload": {"dollars": float("inf"), "minutes": 1}},
                  {"id": "e1", "type": "claimed", "at": None},
                  {"id": "e1", "type": "claimed", "at": {"state": "ready"}},
                  {"id": "e1", "type": "claimed", "at": {"state": "", "visit": 1}},
                  {"id": "e1", "type": "claimed", "at": {"state": "ready", "visit": 0}},
                  {"id": "e1", "type": "claimed", "at": {"state": "ready", "visit": 1.0}},
                  {"id": "e1", "type": "claimed", "at": {"state": "ready", "visit": True}},
                  {"id": "e1", "type": "deadline_passed"},
                  {"id": "e1", "type": "step_failed", "payload": COST}]
        for evt in events:
            with self.subTest(event=repr(evt)):
                out = flow.next_state(SMALL, run, evt)
                self.assert_refused(out, "malformed_event", run)
                self.assertEqual((out["remaining"], out["over_budget"]), ({"dollars": 5, "minutes": 60}, False))

    def test_rule_1_comes_before_everything_and_gives_back_whatever_run_it_was_given(self):
        for run in (None, "a run", [1], {"state": "done"}, {"state": "nowhere", "spent": "a lot"}):
            with self.subTest(run=run):
                out = flow.next_state(SMALL, run, {"id": "e1"})
                self.assert_refused(out, "malformed_event", run)
                self.assertEqual((out["remaining"], out["over_budget"]), (None, False))

    def test_rule_2_an_ended_run_never_moves(self):
        ended = [{"state": "done", "visits": {"ready": 1}, "spent": {"dollars": 6, "minutes": 1},
                  "seen": ["e1"], "reason": "ci_green"},
                 {"state": "stopped", "visits": {"ready": 1}, "spent": {"dollars": 0, "minutes": 0},
                  "seen": [], "reason": "human_stop"},
                 {"state": "stopped"}, {"state": "done", "spent": "unreadable", "visits": 3}]
        for run in ended:
            for evt in (event("e1", "claimed"), event("e2", "human_stop"), event("e3", "nobody_knows")):
                with self.subTest(run=run, event=evt["type"]):
                    self.assert_refused(self.step(run, evt), "run_ended", run)
        out = self.step(ended[0], event("e9", "claimed"))
        self.assertEqual((out["remaining"], out["over_budget"]), ({"dollars": 0, "minutes": 59}, True))
        out = self.step(ended[2], event("e9", "claimed"))
        self.assertEqual((out["remaining"], out["over_budget"]), (None, False))

    def test_rule_3_an_inconsistent_run_is_stopped_at_once(self):
        good = run_at("coding", {"ready": 1, "coding": 2, "checks": 1}, (1, 10), ["e1", "e2"])
        cases = {
            "not an object": "coding",
            "a key missing": {k: v for k, v in good.items() if k != "seen"},
            "a label nobody defined": {**good, "state": "in_review"},
            "a state that is not text": {**good, "state": ["coding"]},
            "visits not an object": {**good, "visits": [1, 2]},
            "a count that is not an integer": {**good, "visits": {"ready": 1, "coding": 1.5}},
            "a count that is a boolean": {**good, "visits": {"ready": 1, "coding": True}},
            "a negative count": {**good, "visits": {"ready": -1, "coding": 1}},
            "a count for an unknown state": {**good, "visits": {"coding": 1, "in_review": 1}},
            "the current state never entered": {**good, "visits": {"ready": 1}},
            "the current state entered zero times": {**good, "visits": {"ready": 1, "coding": 0}},
            "a count above its cap": {**good, "visits": {"ready": 1, "coding": 4}},
            "spent not an object": {**good, "spent": 3},
            "spent without minutes": {**good, "spent": {"dollars": 1}},
            "spent negative": {**good, "spent": {"dollars": -1, "minutes": 0}},
            "spent not a number": {**good, "spent": {"dollars": "1", "minutes": 0}},
            "seen not a list": {**good, "seen": "e1"},
            "seen with something that is not text": {**good, "seen": ["e1", 2]},
            "a reason on a live run": {**good, "reason": "cap_reached"},
        }
        for label, run in cases.items():
            with self.subTest(case=label):
                out = self.step(run, event("e9", "code_written"))
                self.assertEqual((out["outcome"], out["reason"]), ("stopped", "inconsistent"))
                self.assertEqual((out["run"]["state"], out["run"]["reason"]), ("stopped", "inconsistent"))
                self.assertEqual(set(out["run"]), {"state", "visits", "spent", "seen", "reason"})
                self.assertEqual(out["run"]["seen"][-1], "e9")
                state = run.get("state") if isinstance(run, dict) else None
                self.assertEqual(out["transition"], {"from": state if isinstance(state, str) else None,
                                                     "event": "code_written", "to": "stopped"})
                self.assert_refused(self.step(out["run"], event("e10", "code_written")), "run_ended", out["run"])

    def test_rule_3_keeps_what_is_well_formed_and_adds_no_cost(self):
        run = run_at("in_review", {"ready": 1, "coding": 2}, (1.5, 10), ["e1", "e2"])
        out = self.step(run, event("e3", "code_written", {"dollars": 4, "minutes": 4}))
        self.assertEqual(out["run"], {"state": "stopped", "visits": {"ready": 1, "coding": 2},
                                      "spent": {"dollars": 1.5, "minutes": 10}, "seen": ["e1", "e2", "e3"],
                                      "reason": "inconsistent"})
        self.assertEqual((out["remaining"], out["over_budget"]), ({"dollars": 3.5, "minutes": 50}, False))
        broken = {"state": "coding", "visits": "many", "spent": None, "seen": 3, "reason": None}
        out = self.step(broken, event("e3", "code_written"))
        self.assertEqual(out["run"], {"state": "stopped", "visits": {}, "spent": {"dollars": 0, "minutes": 0},
                                      "seen": ["e3"], "reason": "inconsistent"})

    def test_rule_3_does_not_add_a_known_id_twice(self):
        run = run_at("in_review", {"ready": 1}, seen=["e1"])
        self.assertEqual(self.step(run, event("e1", "claimed"))["run"]["seen"], ["e1"])

    def test_rule_4_a_known_id_is_a_duplicate_whatever_else_the_event_says(self):
        run = run_at("coding", {"ready": 1, "coding": 1}, (1, 5), ["e1"])
        for evt in (event("e1", "claimed"), event("e1", "code_written", {"dollars": 3, "minutes": 3}),
                    event("e1", "nobody_knows", None), event("e1", "code_written", COST, at=("checks", 7))):
            with self.subTest(event=evt):
                out = self.step(run, evt)
                self.assertEqual((out["outcome"], out["reason"], out["transition"]),
                                 ("duplicate", "already_seen", None))
                self.assertEqual(out["run"], run)
                self.assertEqual(out["remaining"], {"dollars": 4, "minutes": 55})

    def test_rule_5_a_person_stops_the_run_whatever_the_state_the_caps_and_the_budget(self):
        for state in SMALL["states"]:
            with self.subTest(state=state):
                run = run_at(state, {state: 1}, (4.5, 59))
                out = self.step(run, event("stop-1", "human_stop", {"dollars": 3, "minutes": 5}, at=("push", 9)))
                self.assertEqual((out["outcome"], out["reason"]), ("stopped", "human_stop"))
                self.assertEqual(out["transition"], {"from": state, "event": "human_stop", "to": "stopped"})
                self.assertEqual(out["run"], {"state": "stopped", "visits": {state: 1},
                                              "spent": {"dollars": 7.5, "minutes": 64}, "seen": ["stop-1"],
                                              "reason": "human_stop"})
                self.assertEqual((out["remaining"], out["over_budget"]), ({"dollars": 0, "minutes": 0}, True))

    def test_rule_5_a_human_stop_needs_no_cost(self):
        out = self.step(run_at("coding", {"ready": 1, "coding": 1}), event("stop-1", "human_stop", None))
        self.assertEqual((out["outcome"], out["reason"], out["run"]["spent"]),
                         ("stopped", "human_stop", {"dollars": 0, "minutes": 0}))

    def test_rule_6_an_event_out_of_place_is_refused_never_guessed(self):
        run = run_at("coding", {"ready": 1, "coding": 1}, (1, 5), ["e1"])
        self.assert_refused(self.step(run, event("e2", "checks_passed")), "event_not_expected", run)
        self.assert_refused(self.step(run, event("e2", "ci_green")), "event_not_expected", run)
        self.assert_refused(self.step(run, event("e2", "nobody_knows")), "unknown_event", run)
        self.assert_refused(self.step(run, event("e2", "checks_passed", at=("checks", 1))), "event_not_expected", run)

    def test_rule_6_step_failed_does_not_belong_where_nobody_runs(self):
        for state in ("approval", "ci_wait"):
            with self.subTest(state=state):
                run = run_at(state, {state: 1})
                out = self.step(run, event("e1", "step_failed", at=(state, 1)))
                self.assert_refused(out, "event_not_expected", run)

    def test_rule_6_a_refused_event_is_refused_again_and_may_move_later(self):
        run = flow.new_run(SMALL)
        early = event("e2", "code_written")
        self.assert_refused(self.step(run, early), "event_not_expected", run)
        self.assert_refused(self.step(run, early), "event_not_expected", run)
        claimed = self.step(run, event("e1", "claimed"))
        self.assertEqual(self.step(claimed["run"], early)["outcome"], "moved")

    def test_rule_7_an_answer_meant_for_another_round_is_stale(self):
        run = run_at("coding", {"ready": 1, "coding": 2, "checks": 1})
        self.assert_refused(self.step(run, event("e5", "code_written", at=("coding", 1))), "stale_event", run)
        self.assert_refused(self.step(run, event("e5", "code_written", at=("checks", 2))), "stale_event", run)
        self.assert_refused(self.step(run, event("e5", "deadline_passed", None, at=("ci_wait", 1))), "stale_event", run)
        self.assert_refused(self.step(run, event("e5", "step_failed", at=("coding", 3))), "stale_event", run)
        self.assertEqual(self.step(run, event("e5", "code_written", at=("coding", 2)))["outcome"], "moved")

    def test_rule_8_the_end_of_a_program_or_agent_step_says_what_it_cost(self):
        run = run_at("coding", {"ready": 1, "coding": 1})
        for cost in (None, {}, {"dollars": 1}, {"minutes": 1}):
            with self.subTest(cost=cost):
                self.assert_refused(self.step(run, event("e2", "code_written", cost)), "cost_missing", run)
                self.assert_refused(self.step(run, event("e2", "step_failed", cost, at=("coding", 1))),
                                    "cost_missing", run)

    def test_rule_8_does_not_ask_a_cost_of_a_gate_a_wait_or_a_deadline(self):
        gate = run_at("approval", {"approval": 1})
        self.assertEqual(self.step(gate, event("e1", "approved", None))["outcome"], "moved")
        wait = run_at("ci_wait", {"ci_wait": 1})
        self.assertEqual(self.step(wait, event("e1", "ci_finished", None))["outcome"], "moved")
        coding = run_at("coding", {"coding": 1})
        out = self.step(coding, event("e1", "deadline_passed", None, at=("coding", 1)))
        self.assertEqual((out["outcome"], out["reason"]), ("stopped", "deadline_passed"))

    def test_rule_9_a_transition_to_stopped_carries_its_reason(self):
        out = self.step(flow.new_run(SMALL), event("e1", "not_eligible"))
        self.assertEqual((out["outcome"], out["reason"]), ("stopped", "not_eligible"))
        self.assertEqual(out["transition"], {"from": "ready", "event": "not_eligible", "to": "stopped"})
        self.assertEqual(out["run"], {"state": "stopped", "visits": {"ready": 1}, "spent": COST, "seen": ["e1"],
                                      "reason": "not_eligible"})

    def test_rule_9_a_passed_deadline_or_a_failed_step_stops_the_run_when_not_declared(self):
        for state, kind in (("approval", "deadline_passed"), ("ci_wait", "deadline_passed"),
                            ("coding", "deadline_passed"), ("coding", "step_failed"), ("checks", "step_failed")):
            with self.subTest(state=state, event=kind):
                out = self.step(run_at(state, {state: 1}), event("e1", kind, at=(state, 1)))
                self.assertEqual((out["outcome"], out["reason"], out["run"]["state"]), ("stopped", kind, "stopped"))
                self.assertEqual(out["run"]["spent"], COST)

    def test_a_declared_built_in_event_is_a_transition_like_any_other(self):
        definition = small()
        definition["states"]["coding"]["on"]["step_failed"] = {"to": "coding"}
        definition["states"]["approval"]["on"]["deadline_passed"] = {"to": "stopped", "reason": "nobody_answered"}
        run = run_at("coding", {"coding": 2})
        out = self.step(run, event("e1", "step_failed", at=("coding", 2)), definition)
        self.assertEqual((out["outcome"], out["run"]["state"], out["run"]["visits"]), ("moved", "coding", {"coding": 3}))
        out = self.step(out["run"], event("e2", "step_failed", at=("coding", 3)), definition)
        self.assertEqual((out["outcome"], out["reason"], out["run"]["visits"]), ("stopped", "cap_reached", {"coding": 3}))
        out = self.step(run_at("approval", {"approval": 1}), event("e1", "deadline_passed", None, at=("approval", 1)),
                        definition)
        self.assertEqual((out["outcome"], out["reason"]), ("stopped", "nobody_answered"))

    def test_rule_10_a_transition_to_done_ends_with_its_reason_or_finished(self):
        run = run_at("ci_check", {"ci_check": 1})
        out = self.step(run, event("e1", "ci_green"))
        self.assertEqual((out["outcome"], out["reason"], out["run"]["state"], out["run"]["reason"]),
                         ("done", "ci_green", "done", "ci_green"))
        self.assertEqual(out["transition"], {"from": "ci_check", "event": "ci_green", "to": "done"})
        definition = small()
        del definition["states"]["ci_check"]["on"]["ci_green"]["reason"]
        out = self.step(run, event("e1", "ci_green"), definition)
        self.assertEqual((out["outcome"], out["reason"], out["run"]["reason"]), ("done", "finished", "finished"))

    def test_rule_11_the_stop_point_ends_the_run_without_entering_the_target(self):
        run = run_at("open_pr", {"ready": 1, "open_pr": 1})
        out = self.step(run, event("e1", "pr_opened"))
        self.assertEqual((out["outcome"], out["reason"]), ("done", "stop_point"))
        self.assertEqual(out["transition"], {"from": "open_pr", "event": "pr_opened", "to": "done"})
        self.assertEqual(out["run"], {"state": "done", "visits": {"ready": 1, "open_pr": 1}, "spent": COST,
                                      "seen": ["e1"], "reason": "stop_point"})

    def test_rule_11_another_stop_point_on_the_way_is_passed_through(self):
        definition = flow.new("feature")
        out = self.step(run_at("plan_size", {"plan_size": 1}), event("e1", "plan_small"), definition)
        self.assertEqual((out["outcome"], out["run"]["state"]), ("moved", "coding"))

    def test_rule_12_landing_on_the_budget_is_within_it_and_passing_it_stops(self):
        on_it = self.step(run_at("coding", {"coding": 1}, (4.5, 50)),
                          event("e1", "code_written", {"dollars": 0.5, "minutes": 10}))
        self.assertEqual((on_it["outcome"], on_it["remaining"], on_it["over_budget"]),
                         ("moved", {"dollars": 0, "minutes": 0}, False))
        over = self.step(on_it["run"], event("e2", "checks_failed", {"dollars": 0, "minutes": 0.25}))
        self.assertEqual((over["outcome"], over["reason"], over["over_budget"]), ("stopped", "budget_exceeded", True))
        self.assertEqual(over["transition"], {"from": "checks", "event": "checks_failed", "to": "stopped"})
        self.assertEqual(over["run"], {"state": "stopped", "visits": {"coding": 1, "checks": 1},
                                       "spent": {"dollars": 5, "minutes": 60.25}, "seen": ["e1", "e2"],
                                       "reason": "budget_exceeded"})
        self.assertEqual(over["remaining"], {"dollars": 0, "minutes": 0})

    def test_rule_12_dollars_alone_are_enough(self):
        out = self.step(run_at("coding", {"coding": 1}, (4.5, 0)), event("e1", "code_written", {"dollars": 1, "minutes": 0}))
        self.assertEqual((out["outcome"], out["reason"]), ("stopped", "budget_exceeded"))

    def test_a_run_that_finishes_over_budget_is_still_done_and_says_so(self):
        out = self.step(run_at("ci_check", {"ci_check": 1}, (4.5, 0)), event("e1", "ci_green", {"dollars": 9, "minutes": 0}))
        self.assertEqual((out["outcome"], out["reason"], out["over_budget"]), ("done", "ci_green", True))
        out = self.step(run_at("open_pr", {"open_pr": 1}, (4.5, 0)), event("e1", "pr_opened", {"dollars": 9, "minutes": 0}))
        self.assertEqual((out["outcome"], out["reason"], out["over_budget"]), ("done", "stop_point", True))
        out = self.step(run_at("open_pr", {"open_pr": 1}, (4.5, 0)), event("e1", "head_moved", {"dollars": 9, "minutes": 0}))
        self.assertEqual((out["outcome"], out["reason"], out["over_budget"]), ("stopped", "head_moved", True))

    def test_rule_12_the_budget_is_tested_before_the_cap(self):
        run = run_at("checks", {"coding": 3, "checks": 3}, (4.5, 0))
        out = self.step(run, event("e1", "checks_failed", {"dollars": 1, "minutes": 0}))
        self.assertEqual((out["outcome"], out["reason"]), ("stopped", "budget_exceeded"))

    def test_the_sums_are_rounded_to_four_decimals(self):
        out = self.step(run_at("coding", {"coding": 1}, (0.1, 0.1)), event("e1", "code_written", {"dollars": 0.2, "minutes": 0.2}))
        self.assertEqual(out["run"]["spent"], {"dollars": 0.3, "minutes": 0.3})
        self.assertEqual(out["remaining"], {"dollars": 4.7, "minutes": 59.7})

    def test_other_payload_keys_are_carried_never_read(self):
        out = self.step(flow.new_run(SMALL), {"id": "e1", "type": "claimed",
                                              "payload": {"dollars": 0, "minutes": 1, "outcome": "not_eligible",
                                                          "to": "stopped"}})
        self.assertEqual((out["outcome"], out["run"]["state"]), ("moved", "coding"))

    def test_the_whole_small_flow_from_a_new_run(self):
        run = flow.new_run(SMALL)
        path = ["claimed", "code_written", "checks_passed", "pushed", "approved"]
        states = ["coding", "checks", "push", "approval", "open_pr"]
        for index, (kind, state) in enumerate(zip(path, states)):
            out = self.step(run, event(f"e{index}", kind))
            self.assertEqual((out["outcome"], out["run"]["state"]), ("moved", state))
            run = out["run"]
        self.assertEqual(run["visits"], {"ready": 1, "coding": 1, "checks": 1, "push": 1, "approval": 1, "open_pr": 1})
        self.assertEqual(run["spent"], {"dollars": 1.25, "minutes": 10})
        self.assertEqual(self.step(run, event("e9", "pr_opened"))["reason"], "stop_point")

    def test_next_state_returns_on_numbers_no_float_can_hold(self):
        huge = run_at("coding", {"coding": 1}, (10 ** 400, 0))
        out = self.step(huge, event("e1", "code_written"))
        self.assertEqual((out["outcome"], out["reason"]), ("stopped", "budget_exceeded"))
        out = self.step(run_at("coding", {"coding": 1}, (1e308, 0)), event("e1", "code_written", {"dollars": 1e308, "minutes": 0}))
        self.assertEqual((out["outcome"], out["reason"]), ("stopped", "budget_exceeded"))
        json.dumps(out, allow_nan=False)

    def test_next_state_returns_on_a_definition_that_does_not_hold(self):
        evt = event("e1", "claimed")
        for definition in (None, [], {}, {"states": 3}, {"states": {"ready": None}, "start": "ready"},
                           {"states": {"ready": {"on": {"claimed": 3}}}}, small(budget="none"),
                           {"states": {"ready": {"type": "code", "on": {"claimed": {"to": "nowhere"}}}}}):
            for run in (flow.new_run(SMALL), None):
                with self.subTest(definition=repr(definition)[:50], run=run is not None):
                    out = flow.next_state(definition, run, evt)
                    self.assertEqual(set(out), OUTPUT_KEYS)


class Sequences:
    """Generated event sequences: mostly the events the state expects, with every kind of noise."""

    def __init__(self, definition: dict, seed: int):
        self.definition = definition
        self.random = random.Random(seed)
        self.types = sorted({name for state in definition["states"].values() for name in state["on"]})
        self.counter = 0

    def cost(self) -> dict:
        budget = self.definition["budget"]
        heavy = self.random.random() < 0.05
        # A heavy step can pass the budget alone: the shortest flow has three steps before its stop point.
        return {"dollars": self.random.choice([0, 0.25, 0.5, 1]) * (budget["dollars"] * 1.25 if heavy else 1),
                "minutes": self.random.choice([0, 1, 2.5, 6]) * (budget["minutes"] / 5 if heavy else 1)}

    def one(self, run: dict, sent: list[dict]) -> dict:
        self.counter += 1
        ident = f"evt-{self.counter}"
        state = run.get("state")
        declared = sorted(self.definition["states"].get(state, {}).get("on", {}))
        visit = run.get("visits", {}).get(state, 1)
        draw = self.random.random()
        if draw < 0.70 and declared:
            evt = {"id": ident, "type": self.random.choice(declared), "payload": self.cost()}
            if self.random.random() < 0.5:
                evt["at"] = {"state": state, "visit": visit}
            return evt
        if draw < 0.76 and sent:
            return copy.deepcopy(self.random.choice(sent))
        if draw < 0.84:
            return {"id": ident, "type": self.random.choice(self.types + ["nobody_knows"]), "payload": self.cost()}
        if draw < 0.88 and declared:
            return {"id": ident, "type": self.random.choice(declared), "payload": self.cost(),
                    "at": {"state": self.random.choice(sorted(self.definition["states"])),
                           "visit": self.random.randint(1, 4)}}
        if draw < 0.91 and declared:
            return {"id": ident, "type": self.random.choice(declared),
                    "payload": self.random.choice([{}, {"dollars": 1}, {"minutes": 1}])}
        if draw < 0.95:
            evt = {"id": ident, "type": self.random.choice(["deadline_passed", "step_failed"]),
                   "payload": self.cost()}
            if self.random.random() < 0.9:
                evt["at"] = {"state": state or "ready", "visit": visit if self.random.random() < 0.8 else visit + 1}
            return evt
        if draw < 0.96:
            return {"id": ident, "type": "human_stop", "payload": self.cost()}
        return self.random.choice([None, {"id": ident}, {"id": ident, "type": "claimed", "payload": {"dollars": -1}},
                                   {"id": ident, "type": "claimed", "at": {"visit": 1}}, [ident]])

    def sequence(self, length: int) -> list:
        """One sequence, generated while replaying it so that most events fit the state of the run."""
        run, sent, events, after_end = flow.new_run(self.definition), [], [], 0
        while len(events) < length and after_end < 3:
            evt = self.one(run, sent)
            events.append(evt)
            if isinstance(evt, dict) and isinstance(evt.get("id"), str):
                sent.append(evt)
            run = flow.next_state(self.definition, run, evt)["run"]
            after_end += run["state"] in flow.ENDED
        return events


class PropertiesTest(unittest.TestCase):
    """What follows from the rules, checked on several thousand generated sequences."""

    SEQUENCES_PER_FLOW = 1500
    LENGTH = 120
    SEED = 143

    def replay(self, definition: dict, events: list) -> list[dict]:
        run, outputs = flow.new_run(definition), []
        for evt in events:
            frozen = json.dumps([run, evt], sort_keys=True)
            out = flow.next_state(definition, run, evt)
            if json.dumps([run, evt], sort_keys=True) != frozen:
                self.fail(f"next_state changed its arguments on {evt!r}")
            self.check_output(definition, run, evt, out)
            outputs.append(out)
            run = out["run"]
        return outputs

    def check_output(self, definition: dict, run: dict, evt, out: dict):
        states, budget = definition["states"], definition["budget"]
        after = out["run"]
        if set(out) != OUTPUT_KEYS or out["outcome"] not in OUTCOMES:
            self.fail(f"not an output document: {out!r}")
        for name, count in after["visits"].items():
            cap = states[name].get("cap")
            if cap is not None and count > cap:
                self.fail(f"{name} was entered {count} times, its cap is {cap}: {evt!r}")
        for unit in ("dollars", "minutes"):
            if after["spent"][unit] < run["spent"][unit]:
                self.fail(f"the {unit} spent fell on {evt!r}")
            if out["remaining"][unit] != max(0, round(budget[unit] - after["spent"][unit], 4)):
                self.fail(f"the {unit} left are wrong on {evt!r}: {out!r}")
        over = any(after["spent"][unit] > budget[unit] for unit in ("dollars", "minutes"))
        if out["over_budget"] != over:
            self.fail(f"over_budget is wrong on {evt!r}: {out!r}")
        if over and after["state"] not in flow.ENDED:
            self.fail(f"the run goes on past its budget: {out!r}")
        if out["outcome"] in ("refused", "duplicate"):
            if after != run or out["transition"] is not None or not out["reason"]:
                self.fail(f"a {out['outcome']} event changed the run: {evt!r} gave {out!r}")
            if run["state"] in flow.ENDED and out["reason"] not in ("run_ended", "malformed_event"):
                self.fail(f"an ended run answered {out['reason']} to {evt!r}")
            return
        if run["state"] in flow.ENDED:
            self.fail(f"an ended run moved on {evt!r}: {out!r}")
        self.check_accepted(definition, run, evt, out)

    def check_accepted(self, definition: dict, run: dict, evt: dict, out: dict):
        """An accepted event is one legal transition: the one the file declares, or an end the rules name."""
        states, after, kind = definition["states"], out["run"], evt["type"]
        declared = states[run["state"]]["on"].get(kind)
        if after["seen"] != run["seen"] + [evt["id"]]:
            self.fail(f"the event was not recorded once: {out!r}")
        if out["transition"] != {"from": run["state"], "event": kind, "to": after["state"]}:
            self.fail(f"the transition does not say what happened: {out!r}")
        if after["reason"] != out["reason"]:
            self.fail(f"the run and the answer disagree on the reason: {out!r}")
        if out["outcome"] == "moved":
            entered = dict(run["visits"])
            entered[after["state"]] = entered.get(after["state"], 0) + 1
            if declared is None or declared["to"] != after["state"] or after["visits"] != entered \
                    or out["reason"] is not None or declared.get("reaches") == definition["stop_at"]:
                self.fail(f"{run['state']} moved to {after['state']} on {kind}, which the flow does not declare")
            return
        if out["outcome"] != after["state"] or after["visits"] != run["visits"]:
            self.fail(f"an ended run entered a state: {out!r}")
        target = declared["to"] if declared else None
        legal = {
            "human_stop": kind == "human_stop",
            "deadline_passed": kind == "deadline_passed" and declared is None,
            "step_failed": kind == "step_failed" and declared is None,
            "stop_point": declared is not None and declared.get("reaches") == definition["stop_at"],
            "budget_exceeded": out["over_budget"] and target in states,
            "cap_reached": target in states and run["visits"].get(target, 0) == states[target].get("cap"),
        }
        if out["reason"] in legal:
            if not legal[out["reason"]] or out["outcome"] != ("done" if out["reason"] == "stop_point" else "stopped"):
                self.fail(f"{out['reason']} is not what happened: {evt!r} on {run!r}")
        elif declared is None or target != out["outcome"] or out["reason"] != declared.get("reason", "finished"):
            self.fail(f"the run ended in a way the flow does not declare: {evt!r} gave {out!r}")

    ALWAYS = (("moved", None), ("done", "stop_point"), ("stopped", "budget_exceeded"), ("stopped", "human_stop"),
              ("stopped", "deadline_passed"), ("stopped", "step_failed"), ("duplicate", "already_seen"),
              ("refused", "run_ended"), ("refused", "event_not_expected"), ("refused", "unknown_event"),
              ("refused", "stale_event"), ("refused", "cost_missing"), ("refused", "malformed_event"))

    def flows(self) -> list[tuple[str, dict, tuple]]:
        """Both templates as written, then both with a later stop point and a budget large enough for
        every loop to meet its cap. The bug template stops before its first loop, so only its longer
        variant can reach a cap."""
        longer = {"feature": {"stop_at": "deployed", "budget": {"dollars": 200, "minutes": 2400}},
                  "bug": {"stop_at": "merged", "budget": {"dollars": 200, "minutes": 2400}}}
        cap = (("stopped", "cap_reached"),)
        out = [("feature", flow.new("feature"), cap), ("bug", flow.new("bug"), ())]
        for kind, change in longer.items():
            out.append((f"{kind}, stopping later", {**flow.new(kind), **change}, cap))
        return out

    def test_no_generated_sequence_passes_a_cap_or_the_budget_and_every_answer_is_legal(self):
        for label, definition, more in self.flows():
            self.assertEqual(flow.check(definition), [], label)
            pristine = copy.deepcopy(definition)
            source = Sequences(definition, self.SEED)
            seen_outcomes: dict[tuple, int] = {}
            for _ in range(self.SEQUENCES_PER_FLOW):
                events = source.sequence(self.LENGTH)
                outputs = self.replay(definition, events)
                again = self.replay(definition, copy.deepcopy(events))
                if outputs != again:
                    self.fail(f"replaying a sequence of the flow {label} gave another result")
                for out in outputs:
                    key = (out["outcome"], out["reason"])
                    seen_outcomes[key] = seen_outcomes.get(key, 0) + 1
            self.assertEqual(definition, pristine, "next_state changed the definition")
            with self.subTest(flow=label):
                # The generator must really reach what the property is about, or it proves nothing.
                for key in self.ALWAYS + more:
                    self.assertGreater(seen_outcomes.get(key, 0), 0, f"no sequence gave {key}")

    def test_the_same_seed_generates_the_same_sequences(self):
        definition = flow.new("bug")
        first = [Sequences(definition, 7).sequence(40) for _ in range(3)]
        second = [Sequences(definition, 7).sequence(40) for _ in range(3)]
        self.assertEqual(first, second)

    def test_every_state_and_every_event_type_gives_one_well_formed_answer(self):
        for kind in flow.TEMPLATES:
            definition = flow.new(kind)
            types = sorted({name for state in definition["states"].values() for name in state["on"]})
            for state in list(definition["states"]) + ["done", "stopped", "nowhere"]:
                for name in types + list(flow.BUILT_IN_EVENTS) + ["nobody_knows"]:
                    for cost in (COST, None):
                        for at in (None, (state, 1), (state, 2)):
                            run = run_at(state, {state: 1})
                            out = flow.next_state(definition, run, event("e1", name, cost, at))
                            again = flow.next_state(definition, run, event("e1", name, cost, at))
                            if set(out) != OUTPUT_KEYS or out["outcome"] not in OUTCOMES or out != again:
                                self.fail(f"{kind}: {state} on {name} gave {out!r}")


PLACED = {"flow": "small", "steps": [], "engine": [], "refused_gates": [], "open": [],
          "verdict": {"code": "no_engine", "sentence": "No step needs an engine."}, "passed": True}
NOT_PLACED = {"flow": "small",
              "steps": [{"state": "approval", "status": "open", "destination": None,
                         "missing": {"question": "judge", "key": "can_judge",
                                     "text": "Can the person who approves really judge what they approve?"}},
                        {"state": "coding", "status": "placed", "destination": "skill", "missing": None}],
              "engine": [], "refused_gates": ["second_approval"], "open": ["approval"],
              "verdict": {"code": "open", "sentence": "1 step cannot be placed yet."}, "passed": False}


class StatusTest(unittest.TestCase):
    """Level Mapped, measured from the file alone."""

    def test_a_flow_that_holds_and_is_placed_is_mapped(self):
        state = flow.status(SMALL, PLACED)
        self.assertEqual(state, {
            "flow": "small", "steps": 8, "stop_at": "draft_pr", "budget": {"dollars": 5, "minutes": 60},
            "level": {"reached": 1, "name": "Mapped", "next": 2},
            "checks": [
                {"id": "definition_holds", "passed": True, "origin": "flow check",
                 "plain": "the flow is written down and holds together", "detail": []},
                {"id": "steps_placed", "passed": True, "origin": "flow place",
                 "plain": "every step has a place", "detail": []},
                {"id": "stop_and_budget", "passed": True, "origin": "the definition file",
                 "plain": "a stop point and a budget are set", "detail": []}],
            "next_step": "Nothing more on paper. The next level needs the flow to run on real tickets, "
                         "which this version does not do yet."})

    def test_a_problem_keeps_the_flow_at_level_none(self):
        definition = small()
        del definition["states"]["coding"]["cap"]
        state = flow.status(definition, PLACED)
        self.assertEqual(state["level"], {"reached": 0, "name": "None", "next": 1})
        passed = {check["id"]: check["passed"] for check in state["checks"]}
        self.assertEqual(passed, {"definition_holds": False, "steps_placed": True, "stop_and_budget": True})
        sentence = flow.check(definition)[0]["message"]
        self.assertEqual(state["checks"][0]["detail"], [sentence])
        self.assertEqual(state["next_step"], "Fix this first: " + sentence)

    def test_no_stop_point_or_no_budget_fails_two_checks(self):
        definition = small()
        del definition["budget"]
        state = flow.status(definition, PLACED)
        passed = {check["id"]: check["passed"] for check in state["checks"]}
        self.assertEqual(passed, {"definition_holds": False, "steps_placed": True, "stop_and_budget": False})
        self.assertEqual(state["checks"][2]["detail"], [flow.check(definition)[0]["message"]])
        self.assertIsNone(state["budget"])

    def test_a_step_without_a_place_or_a_gate_nobody_can_judge_keeps_level_none(self):
        state = flow.status(SMALL, NOT_PLACED)
        self.assertEqual(state["level"]["reached"], 0)
        placed = state["checks"][1]
        self.assertFalse(placed["passed"])
        self.assertEqual(len(placed["detail"]), 2)
        self.assertIn("approval", placed["detail"][0])
        self.assertIn("can_judge", placed["detail"][0])
        self.assertIn("second_approval", placed["detail"][1])
        self.assertEqual(state["next_step"], "Fix this first: " + placed["detail"][0])

    def test_a_file_that_is_not_a_flow_is_level_none_and_is_not_placed(self):
        for value in ([1, 2], "text", {"format": 1}, small(format=3)):
            with self.subTest(value=repr(value)[:40]):
                state = flow.status(value)  # no placement given: `place` must not be called
                self.assertEqual(state["level"], {"reached": 0, "name": "None", "next": 1})
                self.assertEqual([check["passed"] for check in state["checks"]], [False, False, False])
                for check in state["checks"][1:]:
                    self.assertEqual(check["detail"], ["the file cannot be read as a flow"])
                self.assertTrue(state["next_step"].startswith("Fix this first: The file cannot be read as a flow"))
        state = flow.status([1, 2])
        self.assertEqual((state["flow"], state["steps"], state["stop_at"], state["budget"]), (None, None, None, None))

    def test_the_map_of_a_mapped_flow(self):
        self.assertEqual(flow.render_map(flow.status(SMALL, PLACED)), "\n".join([
            "Where this flow stands, level by level:",
            "✓ 1 Mapped      the flow is written down and every step has a place   ← you are here",
            "· 2 Shadow      the flow runs on real tickets and only comments",
            "· 3 Drafting    runs end with a draft PR; CI and review results come back to the run",
            "· 4 Delivering  runs reach a reviewed PR and merge only on a human's word",
            "",
            "This flow: small, 8 steps, stops at draft_pr, up to 5 dollars and 60 minutes for one ticket.",
            "Levels 2 to 4 are read from real runs. Nothing measures them yet.",
            "Next step: Nothing more on paper. The next level needs the flow to run on real tickets, "
            "which this version does not do yet.", ""]))

    def test_the_map_of_a_flow_at_level_none_says_what_level_one_still_needs(self):
        definition = small()
        del definition["states"]["coding"]["cap"]
        text = flow.render_map(flow.status(definition, NOT_PLACED))
        lines = text.splitlines()
        self.assertEqual(lines[1], "· 0 None        the phases are chained by hand   ← you are here")
        self.assertEqual(lines[2], "· 1 Mapped      the flow is written down and every step has a place")
        self.assertIn("What level 1 still needs:", lines)
        block = lines[lines.index("What level 1 still needs:") + 1:]
        self.assertEqual(block[0], "- the flow is written down and holds together")
        self.assertTrue(block[1].startswith("  ") and "can repeat without end" in block[1])
        self.assertEqual(block[2], "- every step has a place")
        self.assertNotIn("a stop point and a budget are set", text)
        self.assertTrue(lines[-1].startswith("Next step: Fix this first: "))
        for ident in ("definition_holds", "steps_placed", "stop_and_budget", "loop_without_cap"):
            self.assertNotIn(ident, text)

    def test_the_map_of_a_file_that_is_not_a_flow_still_prints(self):
        text = flow.render_map(flow.status("not a flow"))
        self.assertIn("← you are here", text)
        self.assertIn("the file cannot be read as a flow", text)


class CommandLineTest(unittest.TestCase):
    """`python3 cli/harness.py flow …`: 0 fine, 1 refused or failing, 2 wrong usage or unreadable input."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def write(self, name: str, value) -> str:
        path = os.path.join(self.tmp.name, name)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(value if isinstance(value, str) else json.dumps(value))
        return path

    def test_new_writes_the_template_and_lists_its_steps(self):
        path = os.path.join(self.tmp.name, "deep", "folder", "feature.json")
        code, out, _ = call(["flow", "new", "feature", "--out", path])
        self.assertEqual(code, 0)
        lines = out.splitlines()
        self.assertEqual(lines[0], f"Written: {path}")
        self.assertEqual(len(lines), 1 + 18)
        self.assertEqual(lines[1], "- ready (a program): " + flow.new("feature")["states"]["ready"]["does"])
        self.assertTrue(lines[2].startswith("- planning (an agent): "))
        self.assertTrue(lines[4].startswith("- plan_review (a person decides): "))
        self.assertTrue(lines[8].startswith("- ci_wait (waits): "))
        self.assertEqual(flow.load_definition(path), flow.new("feature"))
        self.assertEqual(call(["flow", "check", path])[0], 0)

    def test_new_writes_under_dot_harness_by_default(self):
        before = os.getcwd()
        os.chdir(self.tmp.name)
        try:
            code, out, _ = call(["flow", "new", "bug", "--format", "json"])
        finally:
            os.chdir(before)
        self.assertEqual(code, 0)
        document = json.loads(out)
        self.assertEqual(set(document), {"file", "definition"})
        self.assertEqual(document["file"], os.path.join(".harness", "flow", "bug.json"))
        self.assertEqual(document["definition"], flow.new("bug"))
        self.assertEqual(flow.load_definition(os.path.join(self.tmp.name, ".harness", "flow", "bug.json")),
                         flow.new("bug"))

    def test_new_does_not_replace_a_file_without_force(self):
        path = self.write("mine.json", {"mine": True})
        code, out, err = call(["flow", "new", "bug", "--out", path])
        self.assertEqual((code, out), (1, ""))
        self.assertIn(path, err)
        self.assertEqual(flow.load_definition(path), {"mine": True})
        self.assertEqual(call(["flow", "new", "bug", "--out", path, "--force"])[0], 0)
        self.assertEqual(flow.load_definition(path), flow.new("bug"))

    def test_new_refuses_another_kind_as_a_wrong_usage(self):
        self.assertEqual(call(["flow", "new", "incident", "--out", os.path.join(self.tmp.name, "x.json")])[0], 2)

    def test_check_says_a_flow_holds(self):
        code, out, _ = call(["flow", "check", self.write("small.json", SMALL)])
        self.assertEqual((code, out), (0, "This flow holds: 8 steps, it stops at draft_pr, one ticket may cost "
                                          "up to 5 dollars and 60 minutes.\n"))

    def test_check_prints_one_line_per_problem_and_exits_1(self):
        definition = small()
        del definition["states"]["coding"]["cap"]
        del definition["budget"]
        path = self.write("broken.json", definition)
        code, out, _ = call(["flow", "check", path])
        problems = flow.check(definition)
        self.assertEqual(code, 1)
        self.assertEqual(out.splitlines(), [f"- {p['message']} ({p['where']})" for p in problems])
        code, out, _ = call(["flow", "check", self.write("text.json", '"a sentence"')])
        self.assertEqual((code, out), (1, f"- {flow.check('a sentence')[0]['message']}\n"))
        code, out, _ = call(["flow", "check", path, "--format", "json"])
        self.assertEqual(code, 1)
        self.assertEqual(json.loads(out), {"file": path, "passed": False, "problems": problems})

    def test_check_takes_a_json_value_that_is_not_a_flow_as_malformed(self):
        code, out, _ = call(["flow", "check", self.write("list.json", [1, 2]), "--format", "json"])
        self.assertEqual(code, 1)
        self.assertEqual([p["code"] for p in json.loads(out)["problems"]], ["malformed"])

    def test_a_missing_file_or_one_that_is_not_json_is_exit_2_for_every_command(self):
        missing = os.path.join(self.tmp.name, "absent.json")
        broken = self.write("broken.json", "{not json")
        evt = self.write("event.json", event("e1", "claimed"))
        for path in (missing, broken):
            for argv in (["flow", "check", path], ["flow", "status", path], ["flow", "status", path, "--map"],
                         ["flow", "next", path, "--event", evt, "--new"]):
                with self.subTest(argv=argv[1:3], file=os.path.basename(path)):
                    code, out, err = call(argv)
                    self.assertEqual((code, out), (2, ""))
                    self.assertTrue(err.startswith("flow: "), err)

    def test_next_on_a_new_run_then_on_the_run_it_returned(self):
        definition = self.write("small.json", SMALL)
        first = self.write("e1.json", event("T-1:ready:1:claimed", "claimed"))
        code, out, _ = call(["flow", "next", definition, "--event", first, "--new", "--format", "json"])
        self.assertEqual(code, 0)
        answer = json.loads(out)
        self.assertEqual(answer, flow.next_state(SMALL, flow.new_run(SMALL), event("T-1:ready:1:claimed", "claimed")))
        run = self.write("run.json", answer["run"])
        second = self.write("e2.json", event("T-1:coding:1:code_written", "code_written", {"dollars": 1.5, "minutes": 12}))
        code, out, _ = call(["flow", "next", definition, "--event", second, "--run", run])
        self.assertEqual(code, 0)
        self.assertEqual(out.splitlines(), ["coding → checks, on code_written.",
                                            "State: checks. Spent: 1.75 dollars, 14 minutes. "
                                            "Left: 3.25 dollars, 46 minutes."])
        code, out, _ = call(["flow", "next", definition, "--event", first, "--run", run])
        self.assertEqual(code, 0, "a duplicate is not a failure")
        self.assertIn("already taken into account", out)

    def test_next_exits_1_when_the_event_is_refused_or_the_run_stopped(self):
        definition = self.write("small.json", SMALL)
        for evt, outcome in ((event("e1", "code_written"), "refused"), (event("e1", "not_eligible"), "stopped"),
                             ({"id": "e1"}, "refused")):
            with self.subTest(event=evt):
                code, out, _ = call(["flow", "next", definition, "--event", self.write("e.json", evt), "--new",
                                     "--format", "json"])
                self.assertEqual((code, json.loads(out)["outcome"]), (1, outcome))

    def test_next_answers_an_ill_formed_run_by_the_rules_not_as_a_usage_error(self):
        definition = self.write("small.json", SMALL)
        evt = self.write("e.json", event("e1", "claimed"))
        code, out, _ = call(["flow", "next", definition, "--event", evt, "--run", self.write("run.json", [1, 2]),
                             "--format", "json"])
        self.assertEqual((code, json.loads(out)["reason"]), (1, "inconsistent"))
        code, out, _ = call(["flow", "next", definition, "--event", self.write("bad.json", ["text"]),
                             "--run", self.write("run.json", 3)])
        self.assertEqual(code, 1)
        self.assertTrue(out.strip())

    def test_next_needs_exactly_one_of_run_and_new(self):
        definition = self.write("small.json", SMALL)
        evt = self.write("e.json", event("e1", "claimed"))
        run = self.write("run.json", flow.new_run(SMALL))
        for extra in ([], ["--new", "--run", run]):
            with self.subTest(extra=extra):
                code, out, err = call(["flow", "next", definition, "--event", evt, *extra])
                self.assertEqual((code, out), (2, ""))
                self.assertTrue(err.startswith("flow: "), err)

    def test_next_exits_2_when_the_event_or_run_file_is_missing_or_not_json(self):
        definition = self.write("small.json", SMALL)
        evt = self.write("e.json", event("e1", "claimed"))
        missing = os.path.join(self.tmp.name, "absent.json")
        broken = self.write("broken.json", "{")
        for argv in (["--event", missing, "--new"], ["--event", broken, "--new"],
                     ["--event", evt, "--run", missing], ["--event", evt, "--run", broken]):
            with self.subTest(argv=argv):
                code, out, err = call(["flow", "next", definition, *argv])
                self.assertEqual((code, out), (2, ""))
                self.assertTrue(err.startswith("flow: "), err)

    def test_next_on_a_definition_that_does_not_hold_prints_what_check_prints_and_exits_2(self):
        definition = small()
        del definition["states"]["coding"]["cap"]
        path = self.write("broken.json", definition)
        evt = self.write("e.json", event("e1", "claimed"))
        for fmt in ("md", "json"):
            with self.subTest(format=fmt):
                checked = call(["flow", "check", path, "--format", fmt])
                code, out, _ = call(["flow", "next", path, "--event", evt, "--new", "--format", fmt])
                self.assertEqual((code, out), (2, checked[1]))
        code, _, _ = call(["flow", "next", self.write("list.json", [1]), "--event", evt, "--new"])
        self.assertEqual(code, 2)

    def test_status_never_fails_a_file_it_could_parse(self):
        path = self.write("list.json", [1, 2])
        code, out, _ = call(["flow", "status", path, "--format", "json"])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out), flow.status([1, 2]))
        code, out, _ = call(["flow", "status", path, "--map"])
        self.assertEqual((code, out), (0, flow.render_map(flow.status([1, 2]))))
        code, out, _ = call(["flow", "status", path])
        self.assertEqual(code, 0)
        lines = out.splitlines()
        self.assertEqual(len(lines), 4)
        self.assertIn("0", lines[0])
        self.assertEqual(lines[1], "✗ the flow is written down and holds together (read by flow check)")
        self.assertEqual(lines[2], "✗ every step has a place (read by flow place)")
        self.assertEqual(lines[3], "✗ a stop point and a budget are set (read by the definition file)")

    def test_place_is_handed_to_the_placement_module_with_the_file_and_the_format(self):
        """The placement is another module: `flow place` only passes the file and the format on,
        and its return value is the exit code."""
        import types
        calls = []
        stand_in = types.ModuleType("harnesslib.flow_place")
        stand_in.main = lambda argv=None: calls.append(argv) or 1
        key, had = "harnesslib.flow_place", sys.modules.get("harnesslib.flow_place")
        package = sys.modules["harnesslib"]
        attribute = getattr(package, "flow_place", None)
        sys.modules[key] = stand_in
        package.flow_place = stand_in
        try:
            code, _, _ = call(["flow", "place", "some/flow.json", "--format", "json"])
            default, _, _ = call(["flow", "place", "other.json"])
        finally:
            if had is None:
                del sys.modules[key]
            else:
                sys.modules[key] = had
            if attribute is None:
                delattr(package, "flow_place")
            else:
                package.flow_place = attribute
        self.assertEqual((code, default), (1, 1))
        self.assertEqual(calls, [["some/flow.json", "--format", "json"], ["other.json", "--format", "md"]])

    def test_without_the_placement_module_place_and_status_say_so_and_exit_2(self):
        path = self.write("small.json", SMALL)
        key = "harnesslib.flow_place"
        had = key in sys.modules, sys.modules.get(key)
        sys.modules[key] = None  # what Python reads as "this module cannot be imported"
        try:
            answers = [call(["flow", "place", path]), call(["flow", "status", path]),
                       call(["flow", "status", self.write("list.json", [1]), "--map"])]
        finally:
            if had[0]:
                sys.modules[key] = had[1]
            else:
                del sys.modules[key]
        for code, out, err in answers[:2]:
            self.assertEqual((code, out), (2, ""))
            self.assertTrue(err.startswith("flow: "), err)
        self.assertEqual(answers[2][0], 0, "a file that is not a flow is never placed")

    def test_the_core_does_not_import_the_placement_module_before_it_is_asked_to_place(self):
        with open(flow.__file__, encoding="utf-8") as fh:
            top_level = [line for line in fh if line.startswith(("import ", "from "))]
        self.assertFalse([line for line in top_level if "flow_place" in line])

    def test_the_flow_help_lists_the_five_commands(self):
        code, out, _ = call(["flow", "--help"])
        self.assertEqual(code, 0)
        for name in ("new", "check", "next", "place", "status"):
            self.assertIn(name, out)


if __name__ == "__main__":
    unittest.main()
