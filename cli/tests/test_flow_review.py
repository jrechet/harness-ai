"""What three reviews of the first slice of `harness flow` found, each pinned by a test that
would have caught it: four gaps in the rules (a retry nobody pays, costs that vanish, a human
stop dropped, steps cut off by the stop point), and what a person could not find out from the
commands alone (what an event file holds, how to pass a run back, which key to edit).
The contract is docs/workflow-harness/flow-spec.md."""
from __future__ import annotations

import contextlib
import copy
import io
import json
import os
import re
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import harness  # noqa: E402
from harnesslib import flow, flow_place  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FORMAT_PAGE = os.path.join(ROOT, "docs", "workflow-harness", "flow-format.md")
GUIDE = os.path.join(ROOT, "docs", "workflow-harness", "decide.md")
COST = {"dollars": 0.25, "minutes": 2}


def call(*argv: str) -> tuple[int, str, str]:
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            code = harness.main(["flow", *argv])
        except SystemExit as exc:  # argparse prints its help, or refuses a wrong usage, by exiting
            code = exc.code
    return code, out.getvalue(), err.getvalue()


def run_at(state: str, visits: dict, spent=(0, 0), seen=()) -> dict:
    return {"state": state, "visits": dict(visits), "spent": {"dollars": spent[0], "minutes": spent[1]},
            "seen": list(seen), "reason": None}


def problems(definition) -> list[tuple[str, str]]:
    return [(p["code"], p["where"]) for p in flow.check(definition)]


def message(definition, code: str) -> str:
    found = [p["message"] for p in flow.check(definition) if p["code"] == code]
    if not found:
        raise AssertionError(f"flow check did not report {code}: {flow.check(definition)}")
    return found[0]


def read(path: str) -> str:
    if not os.path.isfile(path):
        raise AssertionError(f"{os.path.relpath(path, ROOT)} does not exist")
    with open(path, encoding="utf-8") as fh:
        return fh.read()


class InAFolder(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        before = os.getcwd()
        self.addCleanup(os.chdir, before)
        os.chdir(folder.name)

    def write(self, name: str, value) -> str:
        with open(name, "w", encoding="utf-8") as fh:
            json.dump(value, fh)
        return name


# ---------------------------------------------------------------- the rules

class RetryOnADeadlineIsPaidTest(unittest.TestCase):
    """A deadline declared on a program or agent step, leading to a step, is a retry: it says what it cost."""

    def retrying(self) -> dict:
        definition = flow.new("feature")
        definition["states"]["coding"]["deadline_hours"] = 1
        definition["states"]["coding"]["on"]["deadline_passed"] = {"to": "coding"}
        return definition

    def test_a_declared_deadline_that_leads_to_a_step_is_refused_without_its_costs(self):
        definition = self.retrying()
        self.assertEqual(flow.check(definition), [])
        run = run_at("coding", {"coding": 1})
        out = flow.next_state(definition, run, {"id": "dl0", "type": "deadline_passed",
                                                "at": {"state": "coding", "visit": 1}})
        self.assertEqual((out["outcome"], out["reason"]), ("refused", "cost_missing"))
        self.assertEqual(out["run"], run)

    def test_with_its_costs_the_retry_moves_and_the_budget_sees_it(self):
        definition = self.retrying()
        run, spent = run_at("coding", {"coding": 1}), 0
        for visit in range(1, 6):
            out = flow.next_state(definition, run, {"id": f"dl{visit}", "type": "deadline_passed",
                                                    "at": {"state": "coding", "visit": visit},
                                                    "payload": {"dollars": 1, "minutes": 10}})
            spent += 1
            self.assertEqual((out["outcome"], out["run"]["spent"]["dollars"]), ("moved", spent))
            run = out["run"]

    def test_an_undeclared_deadline_and_one_that_ends_the_run_still_need_no_cost(self):
        definition = flow.new("feature")
        event = {"id": "dl", "type": "deadline_passed", "at": {"state": "coding", "visit": 1}}
        out = flow.next_state(definition, run_at("coding", {"coding": 1}), event)
        self.assertEqual((out["outcome"], out["reason"]), ("stopped", "deadline_passed"))
        definition["states"]["coding"]["on"]["deadline_passed"] = {"to": "stopped", "reason": "too_slow"}
        out = flow.next_state(definition, run_at("coding", {"coding": 1}), event)
        self.assertEqual((out["outcome"], out["reason"]), ("stopped", "too_slow"))

    def test_a_declared_deadline_on_a_gate_or_a_wait_costs_nothing(self):
        definition = flow.new("feature")
        definition["states"]["plan_review"]["on"]["deadline_passed"] = {"to": "planning"}
        out = flow.next_state(definition, run_at("plan_review", {"plan_review": 1}),
                              {"id": "dl", "type": "deadline_passed", "at": {"state": "plan_review", "visit": 1}})
        self.assertEqual((out["outcome"], out["run"]["state"]), ("moved", "planning"))


class NoCostVanishesTest(unittest.TestCase):
    def test_a_hundred_costs_too_small_to_round_still_add_up(self):
        definition = flow.new("feature")
        definition["states"]["coding"]["on"]["step_failed"] = {"to": "coding"}
        definition["states"]["coding"]["cap"] = 200
        run = run_at("coding", {"coding": 1})
        for visit in range(1, 101):
            out = flow.next_state(definition, run, {"id": f"e{visit}", "type": "step_failed",
                                                    "at": {"state": "coding", "visit": visit},
                                                    "payload": {"dollars": 0.00004, "minutes": 0.00004}})
            self.assertEqual(out["outcome"], "moved")
            run = out["run"]
        # Each cost is counted rounded up to four decimals: a hundred of them are a cent, never nothing.
        self.assertGreaterEqual(run["spent"]["dollars"], 0.004)
        self.assertEqual(run["spent"], {"dollars": 0.01, "minutes": 0.01})

    def test_a_cost_that_is_already_four_decimals_is_counted_as_it_is(self):
        definition = flow.new("feature")
        for cost in (0, 0.25, 0.29, 0.1, 1.0001, 7, 2.5):
            with self.subTest(cost=cost):
                out = flow.next_state(definition, run_at("coding", {"coding": 1}),
                                      {"id": "e1", "type": "code_written", "payload": {"dollars": cost, "minutes": cost}})
                self.assertEqual(out["run"]["spent"], {"dollars": cost, "minutes": cost})

    def test_a_small_cost_passes_a_budget_it_lands_on(self):
        definition = {**flow.new("feature"), "budget": {"dollars": 1, "minutes": 60}}
        out = flow.next_state(definition, run_at("coding", {"coding": 1}, (1, 0)),
                              {"id": "e1", "type": "code_written", "payload": {"dollars": 0.00001, "minutes": 0}})
        self.assertEqual((out["outcome"], out["reason"], out["over_budget"]), ("stopped", "budget_exceeded", True))

    def test_what_is_counted_never_raises_on_a_number_too_large(self):
        definition = flow.new("feature")
        for cost in (1e308, 10 ** 400, 1e-320):
            with self.subTest(cost=repr(cost)[:12]):
                out = flow.next_state(definition, run_at("coding", {"coding": 1}),
                                      {"id": "e1", "type": "code_written", "payload": {"dollars": cost, "minutes": 0}})
                self.assertIn(out["outcome"], ("moved", "stopped"))
                self.assertGreater(out["run"]["spent"]["dollars"], 0)


class AHumanStopIsNeverADuplicateTest(unittest.TestCase):
    def test_a_human_stop_whose_id_was_already_seen_still_stops(self):
        definition = flow.new("feature")
        run = run_at("planning", {"ready": 1, "planning": 1}, (0, 1), ["x"])
        out = flow.next_state(definition, run, {"id": "x", "type": "human_stop"})
        self.assertEqual((out["outcome"], out["reason"], out["run"]["state"]), ("stopped", "human_stop", "stopped"))
        self.assertEqual(out["run"]["seen"], ["x"], "a known id is not recorded twice")
        again = flow.next_state(definition, out["run"], {"id": "x", "type": "human_stop"})
        self.assertEqual((again["outcome"], again["reason"]), ("refused", "run_ended"))

    def test_any_other_type_with_a_known_id_is_still_a_duplicate(self):
        definition = flow.new("feature")
        run = run_at("planning", {"ready": 1, "planning": 1}, (0, 1), ["x"])
        for kind in ("plan_written", "deadline_passed", "step_failed", "nobody_knows"):
            with self.subTest(type=kind):
                out = flow.next_state(definition, run, {"id": "x", "type": kind, "payload": COST,
                                                        "at": {"state": "planning", "visit": 1}})
                self.assertEqual((out["outcome"], out["reason"]), ("duplicate", "already_seen"))


class CutOffByTheStopPointTest(unittest.TestCase):
    """A transition that reaches the stop point ends the run: what lies behind it never runs as written."""

    def test_the_steps_behind_the_stop_point_are_named(self):
        self.assertEqual(flow.beyond_stop(flow.new("feature")),
                         ["human_review", "rework", "merge_auth", "merging", "delivery", "closing"])
        self.assertEqual(flow.beyond_stop(flow.new("bug")),
                         ["repro", "fix", "verify", "draft_pr", "ci_wait", "ci_check", "ci_fix", "human_review",
                          "closure_wait", "closure_check"])
        self.assertEqual(flow.stop_steps(flow.new("bug")), ["notify"])
        self.assertEqual(flow.stop_steps(flow.new("feature")), ["mark_ready"])
        self.assertEqual(flow.beyond_stop({**flow.new("feature"), "stop_at": "deployed"}), ["closing"])

    def test_a_definition_that_does_not_hold_has_nothing_behind_its_stop_point(self):
        for value in (None, [], {}, {"states": {"a": 3}}, {**flow.new("bug"), "stop_at": "nowhere"}):
            with self.subTest(value=repr(value)[:30]):
                self.assertEqual(flow.beyond_stop(value), [])
                self.assertEqual(flow.stop_steps(value), [])

    def test_a_gate_that_runs_cannot_be_shown_what_only_a_cut_off_step_writes(self):
        definition = flow.new("feature")
        # The plan is now written by a step behind the stop point only.
        del definition["states"]["plan_size"]["writes"]
        definition["states"]["closing"]["writes"].append({"what": "the plan", "key": "plan-{ticket}"})
        self.assertEqual(problems(definition), [("gate_shows_nothing", "states.plan_review")])
        self.assertIn("after the point where a run stops", message(definition, "gate_shows_nothing"))

    def test_a_gate_behind_the_stop_point_may_be_shown_what_any_step_writes(self):
        self.assertEqual(flow.check(flow.new("feature")), [])
        self.assertEqual(flow.check({**flow.new("feature"), "stop_at": "merged"}), [])

    def test_a_circle_that_only_closes_through_the_stop_point_is_not_a_loop(self):
        definition = flow.new("bug")
        # verify → root_cause closes a circle; without the cap of root_cause, only the stop point cuts it.
        del definition["states"]["root_cause"]["cap"]
        self.assertEqual(flow.check(definition), [])
        definition["stop_at"] = "draft_pr"
        self.assertEqual(problems(definition), [("loop_without_cap", "states.root_cause")])

    def test_a_loop_behind_the_stop_point_is_still_refused(self):
        definition = flow.new("feature")
        # delivery and closing both lie behind the stop point, and now send a run round in a circle.
        definition["states"]["closing"]["on"]["premise_failed"] = {"to": "delivery"}
        self.assertEqual(problems(definition), [("loop_without_cap", "states.delivery")])


class CountsAboveACapTest(unittest.TestCase):
    def test_the_counts_of_an_inconsistent_run_are_kept_as_given(self):
        """The contract, "Settled while building": "A count above its cap makes the run inconsistent,
        and the counts are kept as given." No recorded sequence may state a count above its cap."""
        visits = {"ready": 1, "planning": 1, "plan_size": 1, "coding": 7, "checks": 6}
        run = run_at("coding", visits, (6.5, 96), ["e1", "e2"])
        out = flow.next_state(flow.new("feature"), run, {"id": "e3", "type": "human_stop"})
        self.assertEqual((out["outcome"], out["reason"]), ("stopped", "inconsistent"))
        self.assertEqual(out["run"], {"state": "stopped", "visits": visits, "spent": {"dollars": 6.5, "minutes": 96},
                                      "seen": ["e1", "e2", "e3"], "reason": "inconsistent"})


# ---------------------------------------------------------------- what flow check says

class CheckSaysWhatToEditTest(unittest.TestCase):
    def test_a_stop_point_that_is_a_step_name_lists_the_real_stop_points(self):
        definition = {**flow.new("bug"), "stop_at": "fix"}
        self.assertEqual(problems(definition), [("no_stop_point", "stop_at")])
        said = message(definition, "no_stop_point")
        for name in ("root_cause", "plan", "draft_pr", "ready_pr", "merged"):
            self.assertIn(name, said)
        self.assertIn('"fix"', said)
        self.assertIn('"reaches"', said)

    def test_a_missing_stop_point_lists_them_too(self):
        definition = flow.new("bug")
        del definition["stop_at"]
        said = message(definition, "no_stop_point")
        self.assertIn('"stop_at"', said)
        self.assertIn("draft_pr", said)

    def test_a_gate_with_no_shows_and_a_gate_that_shows_what_nobody_writes_are_two_sentences(self):
        definition = flow.new("bug")
        del definition["states"]["human_review"]["shows"]
        missing = message(definition, "gate_shows_nothing")
        self.assertIn('"shows"', missing)
        definition["states"]["human_review"]["shows"] = "the diff"
        wrong = message(definition, "gate_shows_nothing")
        self.assertNotEqual(missing, wrong)
        self.assertIn('"the diff"', wrong)
        for written in ("the run record", "the root cause note", "the branch", "the pull request"):
            self.assertIn(f'"{written}"', wrong)
        self.assertIn('"writes"', wrong)

    def test_every_refusal_names_the_key_to_write(self):
        cases = []
        definition = flow.new("feature")
        del definition["states"]["coding"]["cap"]
        cases.append((definition, "loop_without_cap", '"cap"'))
        definition = flow.new("feature")
        del definition["states"]["ci_check"]["checks_premise"]
        cases.append((definition, "wait_without_premise_check", '"checks_premise": true'))
        definition = flow.new("feature")
        del definition["states"]["closing"]["on"]["premise_failed"]
        cases.append((definition, "wait_without_premise_check", '"on"'))
        definition = flow.new("feature")
        del definition["states"]["ci_wait"]["deadline_hours"]
        cases.append((definition, "wait_without_deadline", '"deadline_hours"'))
        definition = flow.new("feature")
        del definition["states"]["plan_review"]["judge"]
        cases.append((definition, "gate_without_judge", '"judge"'))
        definition = flow.new("feature")
        del definition["states"]["plan_review"]["deadline_hours"]
        cases.append((definition, "gate_without_deadline", '"deadline_hours"'))
        definition = flow.new("feature")
        del definition["states"]["merge_auth"]["on"]["merge_refused"]
        cases.append((definition, "gate_cannot_refuse", '"on"'))
        definition = flow.new("feature")
        del definition["budget"]
        cases.append((definition, "no_budget", '"budget"'))
        definition = flow.new("feature")
        definition["states"]["draft_pr"]["writes"][0]["key"] = "the-branch"
        cases.append((definition, "write_without_key", "{ticket}"))
        for definition, code, key in cases:
            with self.subTest(code=code, key=key):
                self.assertIn(key, message(definition, code))

    def test_a_step_no_event_leads_to_says_how_to_wire_it(self):
        definition = flow.new("bug")
        definition["states"]["sec_review"] = copy.deepcopy(definition["states"]["verify"])
        self.assertEqual(problems(definition), [("malformed", "states.sec_review")])
        self.assertIn('"to"', flow.check(definition)[0]["message"])

    def test_a_step_with_no_way_out_shows_the_shape_of_one(self):
        definition = flow.new("bug")
        definition["states"]["verify"]["on"] = {}
        said = [p["message"] for p in flow.check(definition) if p["where"] == "states.verify"][0]
        self.assertIn('"on": {', said)

    def test_a_mistyped_target_suggests_the_step_meant(self):
        definition = flow.new("bug")
        definition["states"]["fix"]["on"]["fix_written"]["to"] = "verfy"
        self.assertEqual(problems(definition), [("malformed", "states.fix.on.fix_written")])
        self.assertIn('"verify"', flow.check(definition)[0]["message"])


# ---------------------------------------------------------------- what flow next says

class NextSaysWhatAnEventHoldsTest(InAFolder):
    def setUp(self):
        super().setUp()
        self.assertEqual(call("new", "bug")[0], 0)
        self.path = os.path.join(".harness", "flow", "bug.json")

    def test_the_help_of_next_shows_an_event_and_how_to_pass_the_run_back(self):
        code, out, _ = call("next", "--help")
        self.assertEqual(code, 0)
        shown = re.search(r"\{\"id\".*\}\}", out)
        self.assertIsNotNone(shown, "the help of flow next shows no event")
        event = json.loads(shown.group(0))
        self.assertEqual(set(event), {"id", "type", "payload"})
        self.assertEqual(set(event["payload"]), {"dollars", "minutes"})
        for word in ('"at"', "--save-run", "same id", "flow-format.md"):
            self.assertIn(word, out)

    def test_the_event_the_help_shows_is_one_the_bug_template_takes(self):
        _, out, _ = call("next", "--help")
        event = self.write("event.json", json.loads(re.search(r"\{\"id\".*\}\}", out).group(0)))
        code, out, _ = call("next", self.path, "--event", event, "--new")
        self.assertEqual(code, 0, out)

    def test_each_refusal_of_an_event_names_the_key_to_add(self):
        cases = (({"name": "ticket_ready"}, '"id"'),
                 ({"id": "T-1:triage:1:ticket_ready"}, '"type"'),
                 ({"id": "T-1:triage:1:ticket_ready", "type": "ticket_ready"}, '"payload": {"dollars"'),
                 ({"id": "T-1:triage:1:deadline", "type": "deadline_passed"}, '"at": {"state"'))
        for event, key in cases:
            with self.subTest(event=event):
                code, out, _ = call("next", self.path, "--event", self.write("event.json", event), "--new")
                self.assertEqual(code, 1)
                self.assertIn(key, out)

    def test_save_run_writes_the_run_so_that_the_next_call_takes_it(self):
        first = self.write("e1.json", {"id": "T-1:triage:1:ticket_ready", "type": "ticket_ready",
                                       "payload": {"dollars": 0, "minutes": 1}})
        code, out, err = call("next", self.path, "--event", first, "--new", "--save-run", "run.json")
        self.assertEqual(code, 0)
        self.assertEqual(out.splitlines()[0], "triage → premise, on ticket_ready.")
        self.assertIn("run.json", err)
        self.assertIn("--run run.json", err)
        self.assertEqual(flow.load_definition("run.json")["state"], "premise")
        second = self.write("e2.json", {"id": "T-1:premise:1:still_fails", "type": "still_fails",
                                        "payload": {"dollars": 0.5, "minutes": 4}})
        code, out, _ = call("next", self.path, "--event", second, "--run", "run.json", "--save-run", "run.json")
        self.assertEqual(code, 0)
        saved = flow.load_definition("run.json")
        self.assertEqual((saved["state"], saved["spent"]), ("root_cause", {"dollars": 0.5, "minutes": 5}))

    def test_save_run_with_json_writes_the_run_of_the_answer_and_prints_nothing_else(self):
        first = self.write("e1.json", {"id": "T-1:triage:1:ticket_ready", "type": "ticket_ready",
                                       "payload": {"dollars": 0, "minutes": 1}})
        code, out, err = call("next", self.path, "--event", first, "--new", "--save-run", "run.json",
                              "--format", "json")
        self.assertEqual((code, err), (0, ""))
        self.assertEqual(json.loads(out)["run"], flow.load_definition("run.json"))

    def test_a_first_event_whose_run_is_not_saved_says_how_to_go_on(self):
        first = self.write("e1.json", {"id": "T-1:triage:1:ticket_ready", "type": "ticket_ready",
                                       "payload": {"dollars": 0, "minutes": 1}})
        code, _, err = call("next", self.path, "--event", first, "--new")
        self.assertEqual(code, 0)
        self.assertIn("--save-run", err)
        self.assertIn("--run", err)

    def test_a_run_that_cannot_be_saved_is_a_usage_error_said_plainly(self):
        first = self.write("e1.json", {"id": "T-1:triage:1:ticket_ready", "type": "ticket_ready",
                                       "payload": {"dollars": 0, "minutes": 1}})
        code, _, err = call("next", self.path, "--event", first, "--new", "--save-run",
                            os.path.join("no", "such", "folder", "run.json"))
        self.assertEqual(code, 2)
        self.assertTrue(err.startswith("flow: "), err)
        self.assertNotIn("Errno", err)

    def test_the_help_of_run_says_where_a_run_comes_from(self):
        _, out, _ = call("next", "--help")
        self.assertIn("--save-run", out)
        self.assertRegex(out.replace("\n", " "), r'"run"\s+part')


# ---------------------------------------------------------------- what flow new, check, place and status say next

class OneCommandLeadsToTheNextTest(InAFolder):
    def test_the_help_of_flow_gives_the_order_of_work(self):
        code, out, _ = call("--help")
        self.assertEqual(code, 0)
        self.assertIn("In order", out)
        block = out[out.index("In order"):]
        found = [block.find(f"flow {name}") for name in ("new", "check", "place", "status", "next")]
        self.assertNotIn(-1, found, f"a command is missing from the order of work: {found}")
        self.assertEqual(found, sorted(found))
        self.assertIn("flow-format.md", out)

    def test_new_says_where_a_run_stops_what_is_not_run_and_what_to_do_next(self):
        code, out, err = call("new", "bug")
        path = os.path.join(".harness", "flow", "bug.json")
        self.assertEqual(code, 0)
        self.assertIn("after notify", err)
        self.assertIn("root_cause", err)
        self.assertIn("10 steps", err)
        for further in ("plan", "draft_pr", "ready_pr", "merged"):
            self.assertIn(further, err)
        for command in (f"flow check {path}", f"flow place {path}", f"flow status {path} --map"):
            self.assertIn(command, err)
        self.assertIn("flow-format.md", err)
        marked = [line for line in out.splitlines() if "stops here" in line]
        self.assertEqual(len(marked), 1)
        self.assertTrue(marked[0].startswith("- notify (a program): "))

    def test_new_with_json_prints_the_document_alone(self):
        code, out, err = call("new", "bug", "--format", "json")
        self.assertEqual((code, err), (0, ""))
        self.assertEqual(set(json.loads(out)), {"file", "definition"})

    def test_check_says_where_a_run_really_stops_and_what_comes_next(self):
        call("new", "bug")
        path = os.path.join(".harness", "flow", "bug.json")
        code, out, err = call("check", path)
        self.assertEqual(code, 0)
        self.assertEqual(len(out.splitlines()), 1)
        self.assertIn("after notify", err)
        self.assertIn("root_cause", err)
        self.assertIn("10 steps", err)
        self.assertIn(f"flow place {path}", err)

    def test_check_says_when_the_placement_refuses_a_flow_that_holds(self):
        definition = flow.new("feature")
        definition["states"]["plan_review"]["can_judge"] = "no"
        code, _, err = call("check", self.write("flow.json", definition))
        self.assertEqual(code, 0)
        self.assertIn("flow place flow.json", err)
        self.assertIn("does not pass", err)

    def test_check_with_json_prints_the_document_alone(self):
        code, out, err = call("check", self.write("flow.json", flow.new("bug")), "--format", "json")
        self.assertEqual((code, err), (0, ""))
        self.assertEqual(json.loads(out), {"file": "flow.json", "passed": True, "problems": []})

    def test_place_says_when_flow_check_refuses_the_file(self):
        definition = flow.new("feature")
        del definition["states"]["plan_review"]["shows"]
        code, out, err = call("place", self.write("flow.json", definition))
        self.assertEqual(code, 0)
        self.assertIn("this is a human gate", out)
        self.assertIn("flow check flow.json", err)
        self.assertIn("provisional", err)

    def test_place_on_a_flow_that_holds_says_what_comes_next(self):
        code, _, err = call("place", self.write("flow.json", flow.new("feature")))
        self.assertEqual(code, 0)
        self.assertIn("flow status flow.json --map", err)
        self.assertNotIn("provisional", err)

    def test_place_with_json_prints_the_document_alone(self):
        code, _, err = call("place", self.write("flow.json", flow.new("feature")), "--format", "json")
        self.assertEqual((code, err), (0, ""))

    def test_status_at_level_one_says_how_to_try_the_flow_by_hand(self):
        path = self.write("flow.json", flow.new("feature"))
        for extra in ([], ["--map"]):
            with self.subTest(extra=extra):
                code, out, err = call("status", path, *extra)
                self.assertEqual(code, 0)
                self.assertIn("flow next flow.json --event", err)
        self.assertIn("level 1 of 4 (Mapped)", call("status", path)[1].splitlines()[0])

    def test_status_without_the_map_gives_the_first_thing_to_fix_and_points_at_the_map(self):
        definition = flow.new("feature")
        del definition["states"]["coding"]["cap"]
        code, out, err = call("status", self.write("flow.json", definition))
        self.assertEqual(code, 0)
        self.assertIn("level 0 of 4 (None)", out.splitlines()[0])
        self.assertIn("Next step: Fix this first: ", err)
        self.assertIn("can repeat without end", err)
        self.assertIn("--map", err)

    def test_status_does_not_call_false_what_it_did_not_look_at(self):
        """A step nobody leads to makes the file unreadable as a flow: the stop point and the budget
        are set all the same, and saying "✗ a stop point and a budget are set" would be untrue."""
        definition = flow.new("feature")
        definition["states"]["extra"] = copy.deepcopy(definition["states"]["checks"])
        code, out, _ = call("status", self.write("flow.json", definition))
        lines = out.splitlines()
        self.assertEqual((code, len(lines)), (0, 4))
        self.assertTrue(lines[1].startswith("✗ the flow is written down and holds together"))
        for line in lines[2:]:
            self.assertFalse(line.startswith("✗"), line)
            self.assertIn("not looked at", line)
        _, out, _ = call("status", "flow.json", "--map")
        self.assertIn("not looked at", out)
        self.assertNotIn("  the file cannot be read as a flow", out)

    def test_the_status_document_and_the_map_of_a_mapped_flow_are_unchanged_by_the_notes(self):
        path = self.write("flow.json", flow.new("feature"))
        code, out, _ = call("status", path, "--format", "json")
        self.assertEqual(json.loads(out), flow.status(flow.new("feature")))
        code, out, err = call("status", path, "--map", "--format", "json")
        self.assertEqual(err, "")


# ---------------------------------------------------------------- what flow place says

def flow_of(**states) -> dict:
    return {"format": 1, "name": "tiny", "start": next(iter(states)), "stop_at": "end",
            "budget": {"dollars": 1, "minutes": 10}, "states": states}


def step(kind, **keys) -> dict:
    return {"type": kind, "does": "Does its work", "on": {"ok": {"to": "done"}}, **keys}


class PlaceSaysWhatToWriteTest(unittest.TestCase):
    def one(self, state_step: dict) -> dict:
        return flow_place.place(flow_of(only=state_step))["steps"][0]

    def test_a_placed_step_has_nothing_to_fix(self):
        self.assertNotIn("fix", self.one(step("wait", deadline_hours=1)))

    def test_a_missing_key_is_told_with_its_two_answers(self):
        fix = self.one(step("gate", judge="a maintainer", shows="the branch"))["fix"]
        self.assertEqual(fix, 'Add "can_judge": "yes" or "no".')

    def test_a_wrong_value_is_not_told_as_a_missing_answer(self):
        self.assertEqual(self.one(step("gate", can_judge=True))["fix"], '"can_judge" is true: write "yes" or "no".')
        fix = self.one(step("code", survives="hours", units="one", repositories="one"))["fix"]
        self.assertEqual(fix, '"survives" is "hours": write "restart" or "midway".')

    def test_every_key_the_step_still_lacks_comes_in_one_go(self):
        fix = self.one(step("agent"))["fix"]
        self.assertEqual(fix, 'Add "survives": "restart" or "midway". Also needed: "units" ("one" or "many"), '
                              '"repositories" ("one" or "several"), "weak_model" ("yes" or "no").')
        fix = self.one(step("code", survives="restart", repositories="two"))["fix"]
        self.assertEqual(fix, 'Add "units": "one" or "many". Also needed: "repositories" ("one" or "several").')

    def test_a_key_the_walk_would_not_read_is_not_asked_for(self):
        self.assertEqual(self.one(step("code", survives="restart", units="one"))["fix"],
                         'Add "repositories": "one" or "several".')

    def test_a_type_that_is_not_one_of_the_five_lists_them(self):
        fix = self.one(step("person"))["fix"]
        self.assertEqual(fix, '"type" is "person": write "code", "agent", "human", "wait" or "gate".')
        missing = step("code")
        del missing["type"]
        self.assertEqual(self.one(missing)["fix"], 'Add "type": "code", "agent", "human", "wait" or "gate".')

    def test_a_person_reads_the_fix_under_the_step_and_the_verdict_stays_last(self):
        out, err = io.StringIO(), io.StringIO()
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "flow.json")
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(flow_of(changelog=step("agent", survives="hours"), qa=step("person")), fh)
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                code = flow_place.main([path])
        lines = out.getvalue().splitlines()
        self.assertEqual(code, 1)
        self.assertEqual(lines[0], '- changelog (an agent): cannot be placed yet. No answer to "How long does it '
                                   'live, and what must survive?" (key survives).')
        self.assertEqual(lines[1], '  "survives" is "hours": write "restart" or "midway". Also needed: "units" '
                                   '("one" or "many"), "repositories" ("one" or "several"), "weak_model" '
                                   '("yes" or "no").')
        self.assertEqual(lines[3], '  "type" is "person": write "code", "agent", "human", "wait" or "gate".')
        self.assertTrue(lines[-1].startswith("Verdict: 2 steps cannot be placed yet"))

    def test_the_status_of_a_flow_gives_the_fix_with_the_step(self):
        definition = flow.new("feature")
        definition["states"]["plan_review"]["can_judge"] = True
        state = flow.status(definition)
        self.assertEqual(state["level"]["reached"], 0)
        self.assertIn('"can_judge" is true: write "yes" or "no".', state["checks"][1]["detail"][0])


# ---------------------------------------------------------------- the pages a person reads

class FormatPageTest(unittest.TestCase):
    """docs/workflow-harness/flow-format.md: every key of a definition, and a step of each type to paste."""

    def blocks(self) -> list:
        return [json.loads(block) for block in re.findall(r"```json\n(.*?)```", read(FORMAT_PAGE), re.S)]

    def test_every_key_the_templates_use_is_explained(self):
        page = read(FORMAT_PAGE)
        used = set()
        for kind in flow.TEMPLATES:
            definition = flow.new(kind)
            used |= set(definition)
            for state in definition["states"].values():
                used |= set(state)
                for transition in state["on"].values():
                    used |= set(transition)
                for entry in state.get("writes", []):
                    used |= set(entry)
        self.assertGreaterEqual(len(used), 25)
        self.assertEqual(sorted(key for key in used if f"`{key}`" not in page), [])
        for word in ("`done`", "`stopped`", "`{ticket}`", "`human_stop`", "`deadline_passed`", "`step_failed`"):
            self.assertIn(word, page)

    def test_the_page_holds_a_whole_flow_that_passes_with_a_step_of_each_type(self):
        whole = [block for block in self.blocks() if "states" in block]
        self.assertEqual(len(whole), 1, "flow-format.md must hold exactly one whole flow")
        definition = whole[0]
        self.assertEqual(flow.check(definition), [])
        self.assertTrue(flow_place.place(definition)["passed"])
        self.assertEqual({state["type"] for state in definition["states"].values()}, set(flow.STEP_TYPES))

    def test_each_step_to_paste_is_a_step_of_that_whole_flow(self):
        blocks = self.blocks()
        definition = [block for block in blocks if "states" in block][0]
        pasted = {}
        for block in blocks:
            if "states" not in block and "id" not in block:
                pasted.update(block)
        self.assertEqual({state["type"] for state in pasted.values()}, set(flow.STEP_TYPES))
        for name, state in pasted.items():
            with self.subTest(step=name):
                self.assertEqual(definition["states"].get(name), state)

    def test_the_events_the_page_shows_play_that_flow_to_its_stop_point(self):
        blocks = self.blocks()
        definition = [block for block in blocks if "states" in block][0]
        events = [block for block in blocks if "id" in block]
        self.assertGreaterEqual(len(events), 2)
        run, out = flow.new_run(definition), None
        for event in events:
            out = flow.next_state(definition, run, event)
            self.assertIn(out["outcome"], ("moved", "done"), out["message"])
            run = out["run"]

    def test_the_page_says_what_a_stop_point_a_cap_and_a_premise_check_are(self):
        page = read(FORMAT_PAGE).lower()
        for phrase in ("stop point", "the most times one run may enter", "still hold"):
            self.assertIn(phrase, page)


class GuideAfterReviewTest(unittest.TestCase):
    def test_the_guide_gives_the_order_of_work_with_the_five_commands(self):
        page = read(GUIDE)
        found = [page.find(f"flow {name}") for name in ("new", "check", "place", "status", "next")]
        self.assertNotIn(-1, found, f"a command is missing from decide.md: {found}")
        self.assertEqual(found, sorted(found), "the commands are not first named in the order of work")
        self.assertIn("flow-format.md", page)

    def test_the_guide_defines_the_words_flow_check_uses(self):
        words = read(GUIDE)
        for word in ("**Cap**", "**Premise check**", "**Stop point**"):
            self.assertIn(word, words)

    def test_the_guide_says_where_the_date_of_a_dated_skill_is_written_today(self):
        page = read(GUIDE)
        self.assertIn("does not check", page)
        self.assertIn("in the skill file", page)

    def test_the_guide_says_which_command_refuses_a_gate_nobody_can_judge(self):
        page = read(GUIDE)
        self.assertNotIn("the flow does not pass until", page)
        self.assertIn("`flow place` exits with 1", page)
        self.assertIn("level 0", page)

    def test_the_guide_does_not_call_a_step_the_stop_point(self):
        page = read(GUIDE)
        self.assertNotIn("| The default stop point |", page)
        self.assertNotIn("the default stop point |", page)
        self.assertIn("stop point `root_cause`", page)
        self.assertIn("stop point `ready_pr`", page)

    def test_the_guide_does_not_promise_a_pull_request_from_the_bug_template(self):
        page = read(GUIDE)
        self.assertIn("described but not run", page)


if __name__ == "__main__":
    unittest.main()
