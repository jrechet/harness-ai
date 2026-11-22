"""The fixture family `fixtures/flow/` grades `harness flow`: the answers written by hand from
the contract (docs/workflow-harness/flow-spec.md) are what the code must give. No agent is run.

Three things are graded through the Python interface of the contract's section 5:
- the two templates, against their reference writing in `definitions/`;
- `next_state`, on each recorded sequence of events, then over the whole table of states and
  events, then on generated sequences;
- `place`, on the three flows of `place/`."""
from __future__ import annotations

import copy
import os
import random
import re
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tests import flow_fixture_files as files  # noqa: E402

try:
    from harnesslib import flow, flow_place  # noqa: E402
except ImportError as exc:
    raise ImportError(
        "the fixtures of fixtures/flow/ grade cli/harnesslib/flow.py and cli/harnesslib/flow_place.py "
        f"(docs/workflow-harness/flow-spec.md, section 5), and one of them cannot be imported: {exc}") from exc

NAME = re.compile(r"[a-z][a-z0-9_]*")
OUTPUT_KEYS = {"outcome", "reason", "transition", "message", "run", "remaining", "over_budget"}
RUN_KEYS = {"state", "visits", "spent", "seen", "reason"}
OUTCOMES = ("moved", "done", "stopped", "duplicate", "refused")
UNCHANGED = ("duplicate", "refused")
# What the contract fixes of a template's state; `does` and `judge` are the core author's words.
FIXED_STATE_KEYS = ("type", "cap", "shows", "can_judge", "survives", "units", "repositories", "weak_model")
FIXED_TOP_KEYS = ("format", "name", "start", "stop_at", "budget")
TIMED_TYPES = ("gate", "wait")
SEQUENCES = 200
EVENTS = 300
SEED = 143


def fixed_part(definition: dict) -> dict:
    """What the contract fixes of a definition, in a form two writings can be compared in."""
    states = {}
    for name, state in definition["states"].items():
        fixed = {key: state.get(key) for key in FIXED_STATE_KEYS}
        fixed["checks_premise"] = state.get("checks_premise", False)
        fixed["writes"] = [(w.get("what"), w.get("key")) for w in state.get("writes", [])]
        fixed["on"] = {event: (move.get("to"), move.get("reason"), move.get("reaches"))
                       for event, move in state["on"].items()}
        if state.get("type") in TIMED_TYPES:
            fixed["deadline_hours"] = state.get("deadline_hours")
        states[name] = fixed
    return {"top": {key: definition.get(key) for key in FIXED_TOP_KEYS},
            "order": list(definition["states"]), "states": states}


def is_number(value) -> bool:
    return not isinstance(value, bool) and isinstance(value, (int, float))


class TemplateTests(unittest.TestCase):
    def test_each_template_is_the_flow_the_contract_fixes(self):
        for kind in files.TEMPLATE_KINDS:
            reference = fixed_part(files.reference_template(kind))
            written = fixed_part(flow.new(kind))
            with self.subTest(template=kind):
                self.assertEqual(written["top"], reference["top"])
                self.assertEqual(written["order"], reference["order"])
            for state in reference["order"]:
                with self.subTest(template=kind, state=state):
                    self.assertEqual(written["states"].get(state), reference["states"][state])

    def test_each_template_says_what_every_step_does_and_who_judges(self):
        for kind in files.TEMPLATE_KINDS:
            for name, state in flow.new(kind)["states"].items():
                with self.subTest(template=kind, state=name):
                    self.assertTrue(isinstance(state.get("does"), str) and state["does"].strip())
                    if state.get("type") == "gate":
                        self.assertTrue(isinstance(state.get("judge"), str) and state["judge"].strip())

    def test_a_template_is_a_fresh_copy(self):
        first = flow.new("feature")
        first["states"].clear()
        self.assertTrue(flow.new("feature")["states"])


class DefinitionTests(unittest.TestCase):
    def test_every_definition_of_the_family_holds(self):
        for name, path in files.definition_files().items():
            with self.subTest(definition=name):
                self.assertEqual(flow.check(files.read_json(path)), [])

    def test_every_sequence_replays_on_a_definition_that_holds(self):
        for name, path in files.sequence_files().items():
            with self.subTest(sequence=name):
                self.assertEqual(flow.check(files.sequence_definition(files.read_json(path), flow.new)), [])


class OutputShape(unittest.TestCase):
    """What every answer of `next_state` looks like, whatever it was given."""

    def assert_output(self, definition: dict, out) -> None:
        self.assertIsInstance(out, dict)
        self.assertEqual(set(out), OUTPUT_KEYS)
        self.assertIn(out["outcome"], OUTCOMES)
        if out["outcome"] == "moved":
            self.assertIsNone(out["reason"])
        else:
            self.assertIsInstance(out["reason"], str)
            self.assertTrue(NAME.fullmatch(out["reason"]), out["reason"])
        self.assertTrue(isinstance(out["message"], str) and out["message"].strip())
        self.assertIsInstance(out["over_budget"], bool)
        if out["remaining"] is not None:
            self.assertEqual(set(out["remaining"]), {"dollars", "minutes"})
            for value in out["remaining"].values():
                self.assertTrue(is_number(value) and value >= 0, value)
        if out["outcome"] in UNCHANGED:
            self.assertIsNone(out["transition"])
            return
        self.assertEqual(set(out["transition"]), {"from", "event", "to"})
        run = out["run"]
        self.assertIsInstance(run, dict)
        self.assertEqual(set(run), RUN_KEYS)
        self.assertEqual(run["state"], out["transition"]["to"])
        if out["outcome"] == "moved":
            self.assertIn(run["state"], definition["states"])
            self.assertIsNone(run["reason"])
        else:
            self.assertEqual(run["state"], out["outcome"])
            self.assertEqual(run["reason"], out["reason"])
        self.assertIsNotNone(out["remaining"])


class SequenceTests(OutputShape):
    def test_every_recorded_sequence_gives_the_expected_state_after_each_event(self):
        for name, path in files.sequence_files().items():
            sequence = files.read_json(path)
            definition = files.sequence_definition(sequence, flow.new)
            run = flow.new_run(definition) if sequence["start"] == "new" else copy.deepcopy(sequence["start"])
            for number, step in enumerate(sequence["events"], 1):
                given_run, given_event = copy.deepcopy(run), copy.deepcopy(step["event"])
                out = flow.next_state(definition, run, step["event"])
                with self.subTest(sequence=name, event=number, type=step["event"].get("type")):
                    self.assertEqual(run, given_run, "next_state changed the run it was given")
                    self.assertEqual(step["event"], given_event, "next_state changed the event it was given")
                    self.compare(definition, given_run, out, step["expect"])
                # The next event is fed to the run returned, right or wrong.
                run = out["run"] if isinstance(out, dict) and "run" in out else run

    def compare(self, definition: dict, given_run, out, expect: dict) -> None:
        """One answer of `next_state` against one entry of the answer key."""
        self.assert_output(definition, out)
        returned = out["run"]
        self.assertEqual((out["outcome"], out["reason"]), (expect["outcome"], expect["reason"]))
        self.assertEqual(returned.get("state"), expect["state"])
        if out["outcome"] in UNCHANGED:
            self.assertEqual(returned, given_run, "a duplicate or refused event changed the run")
        for state, count in expect.get("visits", {}).items():
            # A state never entered may be absent from `visits`, or be there with 0.
            self.assertEqual(returned["visits"].get(state, 0), count, f"visits of {state}")
        if "spent" in expect:
            self.assertEqual(returned["spent"], expect["spent"])
        if "remaining" in expect:
            self.assertEqual(out["remaining"], expect["remaining"])
        if "over_budget" in expect:
            self.assertIs(out["over_budget"], expect["over_budget"])


def graded_definitions() -> dict[str, dict]:
    """The two templates and every file of `definitions/`."""
    found = {f"template:{kind}": flow.new(kind) for kind in files.TEMPLATE_KINDS}
    found.update({f"definitions/{name}.json": files.read_json(path)
                  for name, path in files.definition_files().items()})
    return found


class WholeTableTests(OutputShape):
    def test_every_state_and_every_event_give_one_well_formed_answer(self):
        for label, definition in graded_definitions().items():
            for state in [*definition["states"], *files.ENDED, files.UNKNOWN_STATE]:
                for event in files.table_events(definition, state):
                    with self.subTest(definition=label, state=state, event=event["id"]):
                        self.one_cell(definition, state, event)

    def one_cell(self, definition: dict, state: str, event: dict) -> None:
        run = files.run_in(state)
        given = copy.deepcopy(run)
        out = flow.next_state(definition, run, event)
        self.assert_output(definition, out)
        self.assertEqual(run, given, "next_state changed the run it was given")
        answer = (out["outcome"], out["reason"])
        if not files.is_well_formed_event(event):
            self.assertEqual(answer, ("refused", "malformed_event"))   # rule 1 comes first
        elif state in files.ENDED:
            self.assertEqual(answer, ("refused", "run_ended"))         # rule 2
        elif state == files.UNKNOWN_STATE:
            self.assertEqual(answer, ("stopped", "inconsistent"))      # rule 3
        elif event["type"] == "human_stop":
            self.assertEqual(answer, ("stopped", "human_stop"))        # rule 5
        if out["outcome"] in UNCHANGED:
            self.assertEqual(out["run"], given)

    def test_an_ill_formed_event_or_run_never_raises(self):
        definition = flow.new("feature")
        for event in files.MALFORMED_EVENTS:
            with self.subTest(event=event):
                out = flow.next_state(definition, flow.new_run(definition), event)
                self.assertEqual((out["outcome"], out["reason"]), ("refused", "malformed_event"))
        good = {"id": "e1", "type": "claimed", "payload": {"dollars": 0, "minutes": 1}}
        for run in (None, "ready", [], {}, {"state": "ready"}, {"state": 3, "visits": [], "spent": 1, "seen": 0, "reason": 2}):
            with self.subTest(run=run):
                out = flow.next_state(definition, run, good)
                self.assertEqual((out["outcome"], out["reason"]), ("stopped", "inconsistent"))
                self.assertEqual(out["run"]["state"], "stopped")
                self.assertEqual(out["run"]["seen"], ["e1"])


class GeneratedSequenceTests(OutputShape):
    """On long generated sequences: no count passes its cap, what is spent never falls, an ended
    run never moves, an event delivered twice changes nothing the second time."""

    def test_no_generated_sequence_breaks_a_guarantee(self):
        definitions = list(graded_definitions().items())
        for number in range(SEQUENCES):
            label, definition = definitions[number % len(definitions)]
            definition = copy.deepcopy(definition)
            if number % 2:
                # Every other sequence has a budget nothing reaches, so that the caps are what stops it.
                definition["budget"] = {"dollars": 1_000_000, "minutes": 1_000_000}
            with self.subTest(definition=label, sequence=number):
                self.one_sequence(definition, random.Random(SEED + number))

    def one_sequence(self, definition: dict, rng: random.Random) -> None:
        caps = {name: state["cap"] for name, state in definition["states"].items() if "cap" in state}
        run = flow.new_run(definition)
        sent: list[dict] = []
        for number in range(EVENTS):
            event = files.random_event(rng, definition, run, number, sent)
            before, given_event = copy.deepcopy(run), copy.deepcopy(event)
            out = flow.next_state(definition, run, event)
            self.assert_output(definition, out)
            self.assertEqual(run, before, "next_state changed the run it was given")
            self.assertEqual(event, given_event, "next_state changed the event it was given")
            after = out["run"]
            well_formed = files.is_well_formed_event(event)
            if before["state"] in files.ENDED:
                self.assertEqual(out["outcome"], "refused", "an ended run answered an event")
                self.assertEqual(after, before, "an ended run moved")
            elif well_formed and event["id"] in before["seen"]:
                self.assertEqual((out["outcome"], out["reason"]), ("duplicate", "already_seen"))
            if out["outcome"] in UNCHANGED:
                self.assertEqual(after, before, "a duplicate or refused event changed the run")
            for state, cap in caps.items():
                self.assertLessEqual(after["visits"].get(state, 0), cap, f"{state} passed its cap")
            for unit in ("dollars", "minutes"):
                self.assertGreaterEqual(after["spent"][unit], before["spent"][unit], f"{unit} spent fell")
            if well_formed:
                sent.append(given_event)
            run = after


class PlaceTests(unittest.TestCase):
    def test_the_three_flows_to_place_are_there(self):
        self.assertEqual(sorted(files.place_folders()), sorted(files.PLACE_FOLDERS))

    def test_every_step_lands_where_the_answer_key_says(self):
        for name, folder in files.place_folders().items():
            expected = files.read_json(os.path.join(folder, "expected.json"))
            definition = files.resolve(expected["definition"], flow.new)
            with self.subTest(flow=name):
                self.assertEqual(flow.check(definition), [])
                self.assertEqual(set(expected["steps"]), set(definition["states"]),
                                 "the answer key does not name exactly the states of the definition")
            document = flow_place.place(definition)
            with self.subTest(flow=name):
                self.assertEqual([step["state"] for step in document["steps"]], list(definition["states"]))
                for key in ("engine", "refused_gates", "open"):
                    self.assertEqual(document[key], expected[key], key)
                self.assertEqual(document["verdict"]["code"], expected["verdict"])
                self.assertIs(document["passed"], expected["passed"])
            for step in document["steps"]:
                with self.subTest(flow=name, state=step["state"]):
                    self.assertEqual(step["destination"], expected["steps"][step["state"]])
                    if step["destination"] is None:
                        self.assertEqual(step["status"], "open")
                        continue
                    self.assertEqual(step["status"], "placed")
                    self.assertTrue(step["decided_by"] and step["decided_by"].get("question"))
                    self.assertTrue(isinstance(step["reason"], str) and step["reason"].strip())


if __name__ == "__main__":
    unittest.main()
