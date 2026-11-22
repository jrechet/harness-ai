"""The cases of `fixtures/flow/cases/` grade the three commands that read a definition and replay
nothing: `flow check` (which problems, where, in which order), `flow place` (what is open, what
is refused, the verdict) and `flow status` (the level). One file is one definition, most often a
template with one thing changed, and the answers written by hand from the contract
(docs/workflow-harness/flow-spec.md, sections 2, 6, 7 and 8). No agent is run.

The first class needs no code of `harness flow`: it checks the cases themselves."""
from __future__ import annotations

import copy
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tests import flow_fixture_files as files  # noqa: E402

try:
    from harnesslib import flow, flow_place  # noqa: E402
except ImportError as exc:
    raise ImportError("the cases of fixtures/flow/cases/ grade cli/harnesslib/flow.py and flow_place.py, and one "
                      f"of them cannot be imported: {exc}") from exc

CASE_KEYS = {"about", "definition", "set", "remove", "check", "not_run", "place", "status"}
REQUIRED = {"about", "definition", "check"}
PLACE_KEYS = {"steps", "engine", "refused_gates", "open", "verdict", "passed", "missing"}
CHECK_IDS = ("definition_holds", "steps_placed", "stop_and_budget")
CODES = ("malformed", "unknown_step_type", "loop_without_cap", "write_without_key", "no_stop_point", "no_budget",
         "wait_without_premise_check", "wait_without_deadline", "gate_without_judge", "gate_without_deadline",
         "gate_cannot_refuse", "gate_shows_nothing")
DESTINATIONS = ("code", "skill", "dated_skill", "ticket_state", "human_gate", "no_gate", "reusable_workflow",
                "campaign", "durable_engine")
# What the family must hold at least: the refusals a reviewer asked an answer key for, and the
# two sides of "needing an engine is an answer, a gate nobody can judge is a failure".
MUST_HOLD = ("typo-in-a-target", "loop-without-cap", "gate-cannot-refuse", "gate-shows-nothing",
             "engine-alone", "gate-nobody-can-judge-alone", "answers-missing", "every-case-placed")


def case_files() -> dict[str, str]:
    folder = os.path.join(files.FAMILY, "cases")
    if not os.path.isdir(folder):
        raise ValueError("fixtures/flow/cases: the folder is missing")
    return {name[:-len(".json")]: os.path.join(folder, name)
            for name in sorted(os.listdir(folder)) if name.endswith(".json")}


def _parent(definition: dict, path: str):
    """The container a dotted path ends in, and its last segment (a list index when it is a number)."""
    *before, last = path.split(".")
    holder = definition
    for segment in before:
        holder = holder[int(segment)] if isinstance(holder, list) else holder[segment]
    return holder, (int(last) if isinstance(holder, list) else last)


def changed(case: dict, template) -> dict:
    """The definition of a case: its reference, then `remove`, then `set`, each a dotted path."""
    definition = copy.deepcopy(files.resolve(case.get("definition"), template))
    for path in case.get("remove", []):
        holder, last = _parent(definition, path)
        if isinstance(holder, dict) and last not in holder:
            raise ValueError(f"{path}: nothing to remove there")
        del holder[last]
    for path, value in case.get("set", {}).items():
        holder, last = _parent(definition, path)
        holder[last] = copy.deepcopy(value)
    return definition


class CaseFormatTests(unittest.TestCase):
    def test_the_cases_a_review_asked_for_are_there(self):
        self.assertEqual(sorted(set(MUST_HOLD) - set(case_files())), [])

    def test_every_case_follows_the_format(self):
        for name, path in case_files().items():
            case = files.read_json(path)
            with self.subTest(case=name):
                self.assertLessEqual(set(case), CASE_KEYS)
                self.assertLessEqual(REQUIRED, set(case))
                self.assertTrue(isinstance(case["about"], str) and case["about"].strip())
                definition = changed(case, files.reference_template)
                self.assertTrue(case.get("set") or case.get("remove") or name.endswith(("-written", "-placed")),
                                "a case that changes nothing says so in its name")
                self.assertIsInstance(case["check"], list)
                for problem in case["check"]:
                    self.assertEqual(set(problem), {"code", "where"})
                    self.assertIn(problem["code"], CODES)
                    self.assertIsInstance(problem["where"], str)
                if any(problem["code"] == "malformed" for problem in case["check"]):
                    self.assertEqual({problem["code"] for problem in case["check"]}, {"malformed"},
                                     "malformed comes alone (section 2)")
                states = definition["states"]
                self.assertLessEqual(set(case.get("not_run", [])), set(states))
                self.one_place(case.get("place"), states)
                self.one_status(case)

    def one_place(self, place, states: dict) -> None:
        if place is None:
            return
        self.assertLessEqual(PLACE_KEYS - {"missing"}, set(place))
        self.assertLessEqual(set(place), PLACE_KEYS)
        for state, destination in place["steps"].items():
            self.assertIn(state, states)
            self.assertTrue(destination is None or destination in DESTINATIONS, state)
        for key in ("engine", "refused_gates", "open"):
            self.assertLessEqual(set(place[key]), set(states))
            self.assertEqual(place[key], [state for state in states if state in place[key]], f"{key}: file order")
        verdict = "open" if place["open"] else "engine" if place["engine"] else "no_engine"
        self.assertEqual(place["verdict"], verdict)
        self.assertIs(place["passed"], not place["open"] and not place["refused_gates"])
        self.assertEqual(sorted(place.get("missing", {})), sorted(place["open"]) if "missing" in place else [])

    def one_status(self, case: dict) -> None:
        status = case.get("status")
        if status is None:
            return
        self.assertEqual(set(status), {"level", "passed"})
        self.assertEqual(set(status["passed"]), set(CHECK_IDS))
        self.assertEqual(status["level"], 1 if all(status["passed"].values()) else 0)
        self.assertIs(status["passed"]["definition_holds"], not case["check"])
        if "place" in case and not any(problem["code"] == "malformed" for problem in case["check"]):
            self.assertIs(status["passed"]["steps_placed"], case["place"]["passed"])

    def test_the_page_of_the_family_names_every_case(self):
        with open(os.path.join(files.FAMILY, "README.md"), encoding="utf-8") as fh:
            page = fh.read()
        self.assertEqual([name for name in case_files() if f"`{name}`" not in page], [])


class CaseTests(unittest.TestCase):
    def test_flow_check_reports_the_problems_of_the_answer_key_in_its_order(self):
        for name, path in case_files().items():
            case = files.read_json(path)
            with self.subTest(case=name):
                found = [{"code": p["code"], "where": p["where"]} for p in flow.check(changed(case, flow.new))]
                self.assertEqual(found, case["check"])

    def test_the_steps_behind_the_stop_point_are_the_ones_of_the_answer_key(self):
        for name, path in case_files().items():
            case = files.read_json(path)
            if "not_run" in case:
                with self.subTest(case=name):
                    self.assertEqual(flow.beyond_stop(changed(case, flow.new)), case["not_run"])

    def test_flow_place_answers_as_the_answer_key_says(self):
        for name, path in case_files().items():
            case = files.read_json(path)
            if "place" not in case:
                continue
            expected = case["place"]
            document = flow_place.place(changed(case, flow.new))
            steps = {step["state"]: step for step in document["steps"]}
            with self.subTest(case=name):
                for key in ("engine", "refused_gates", "open"):
                    self.assertEqual(document[key], expected[key], key)
                self.assertEqual(document["verdict"]["code"], expected["verdict"])
                self.assertIs(document["passed"], expected["passed"])
                for state, destination in expected["steps"].items():
                    self.assertEqual(steps[state]["destination"], destination, state)
                for state, key in expected.get("missing", {}).items():
                    self.assertEqual(steps[state]["missing"]["key"], key, state)
                    self.assertIn(f'"{key}"', steps[state]["fix"])

    def test_flow_status_gives_the_level_of_the_answer_key(self):
        for name, path in case_files().items():
            case = files.read_json(path)
            if "status" not in case:
                continue
            state = flow.status(changed(case, flow.new))
            with self.subTest(case=name):
                self.assertEqual(state["level"]["reached"], case["status"]["level"])
                self.assertEqual({check["id"]: check["passed"] for check in state["checks"]},
                                 case["status"]["passed"])


if __name__ == "__main__":
    unittest.main()
