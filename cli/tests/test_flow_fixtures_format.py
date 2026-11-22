"""The fixture family `fixtures/flow/` is well formed and follows the contract's format
(docs/workflow-harness/flow-spec.md, sections 1, 3 and 8). This test needs no code of
`harness flow`: it reads the family alone, so an answer key with a slip is caught before any
implementation is graded with it. What the answers are worth is `test_flow_fixtures.py`."""
from __future__ import annotations

import os
import random
import re
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tests import flow_fixture_files as files  # noqa: E402

NAME = re.compile(r"[a-z][a-z0-9_]*")
STEP_TYPES = ("code", "agent", "human", "gate", "wait")
RUNS = ("code", "agent")
WAITS = ("wait", "human")
OUTCOMES = ("moved", "done", "stopped", "duplicate", "refused")
UNCHANGED = ("duplicate", "refused")
EXPECT_REQUIRED = {"outcome", "reason", "state"}
EXPECT_OPTIONAL = {"visits", "spent", "remaining", "over_budget", "seen"}
STEP_KEYS = {"event", "expect", "note"}
SEQUENCE_KEYS = {"about", "definition", "override", "start", "events"}
OVERRIDABLE = {"stop_at", "budget"}
PLACE_KEYS = {"about", "definition", "steps", "engine", "refused_gates", "open", "verdict", "passed"}
DESTINATIONS = ("code", "skill", "dated_skill", "ticket_state", "human_gate", "no_gate",
                "reusable_workflow", "campaign", "durable_engine")
PLACE_ANSWERS = {"survives": ("restart", "midway"), "units": ("one", "many"), "repositories": ("one", "several")}
QUARTER = 0.25
FEATURE_STATES = ["ready", "planning", "plan_size", "plan_review", "coding", "checks", "draft_pr", "ci_wait",
                  "ci_check", "ci_fix", "review_checks", "mark_ready", "human_review", "rework", "merge_auth",
                  "merging", "delivery", "closing"]
BUG_STATES = ["triage", "premise", "root_cause", "notify", "repro", "fix", "verify", "draft_pr", "ci_wait",
              "ci_check", "ci_fix", "human_review", "closure_wait", "closure_check"]


def is_name(value) -> bool:
    return isinstance(value, str) and NAME.fullmatch(value) is not None


def is_number(value) -> bool:
    return not isinstance(value, bool) and isinstance(value, (int, float))


def is_count(value) -> bool:
    return not isinstance(value, bool) and isinstance(value, int)


def is_amount(value) -> bool:
    """Two numbers at or above 0, in dollars and minutes."""
    return isinstance(value, dict) and set(value) == {"dollars", "minutes"} \
        and all(is_number(v) and v >= 0 for v in value.values())


def _transition_slips(name: str, event: str, move, states: dict) -> list[str]:
    where = f"states.{name}.on.{event}"
    if not is_name(event) or not isinstance(move, dict) or "to" not in move:
        return [f"{where}: not a named event with a transition"]
    slips = []
    if move["to"] not in states and move["to"] not in files.ENDED:
        slips.append(f"{where}: goes to {move['to']}, which is not a state")
    if move["to"] == "stopped" and "reason" not in move:
        slips.append(f"{where}: stops without a reason")
    slips += [f"{where}: {key} is not a name" for key in ("reason", "reaches") if key in move and not is_name(move[key])]
    if event == "human_stop" or (event == "step_failed" and states[name].get("type") not in RUNS):
        slips.append(f"{where}: this built-in event may not be declared here")
    return slips


def _state_slips(name: str, state: dict, states: dict, writes: dict[str, str]) -> list[str]:
    where = f"states.{name}"
    kind = state.get("type")
    slips = [] if kind in STEP_TYPES else [f"{where}: unknown type {kind!r}"]
    if not (isinstance(state.get("does"), str) and state["does"].strip()):
        slips.append(f"{where}: no sentence saying what the step does")
    if "cap" in state and not (is_count(state["cap"]) and state["cap"] > 0):
        slips.append(f"{where}: cap is not an integer above 0")
    for index, entry in enumerate(state.get("writes", [])):
        what, key = entry.get("what"), entry.get("key")
        if not (isinstance(what, str) and what and isinstance(key, str) and "{ticket}" in key):
            slips.append(f"{where}.writes[{index}]: no key derived from the ticket")
        elif writes.setdefault(key, what) != what:
            slips.append(f"{where}.writes[{index}]: the key {key} already names {writes[key]}")
    if state.get("checks_premise", False) is not False:
        if state["checks_premise"] is not True or kind not in RUNS or len(state.get("on", {})) < 2:
            slips.append(f"{where}: checks its facts without being a program or an agent with two ways out")
    timed = kind in WAITS or kind == "gate"
    if (timed or "deadline_hours" in state) and not (is_number(state.get("deadline_hours")) and state["deadline_hours"] > 0):
        slips.append(f"{where}: no deadline above 0")
    if kind in RUNS:
        slips += [f"{where}: {key} is {state.get(key)!r}, which the grid cannot read"
                  for key, answers in PLACE_ANSWERS.items() if state.get(key) not in answers]
    if kind == "agent" and state.get("weak_model") not in ("yes", "no"):
        slips.append(f"{where}: weak_model is neither yes nor no")
    if kind == "gate":
        slips += _gate_slips(name, state, states)
    return slips


def _gate_slips(name: str, state: dict, states: dict) -> list[str]:
    where = f"states.{name}"
    slips = []
    if not (isinstance(state.get("judge"), str) and state["judge"].strip()):
        slips.append(f"{where}: the gate names nobody who decides")
    written_elsewhere = {entry.get("what") for other, s in states.items() if other != name for entry in s.get("writes", [])}
    if state.get("shows") not in written_elsewhere:
        slips.append(f"{where}: the gate shows {state.get('shows')!r}, which no other step writes")
    if state.get("can_judge") not in ("yes", "no"):
        slips.append(f"{where}: can_judge is neither yes nor no")
    targets = {move.get("to") for event, move in state.get("on", {}).items() if event != "deadline_passed"}
    if len(targets) < 2:
        slips.append(f"{where}: the gate can only say yes")
    return slips


def _premise_slips(states: dict) -> list[str]:
    """After a wait or a person's work the next program checks its facts; after a gate, when it writes."""
    slips = []
    for name, state in states.items():
        for event, move in state["on"].items():
            target = states.get(move["to"])
            if target is None or target.get("type") not in RUNS or target.get("checks_premise") is True:
                continue
            if state.get("type") in WAITS or (state.get("type") == "gate" and target.get("writes")):
                slips.append(f"states.{name}.on.{event}: {move['to']} does not check that the facts still hold")
    return slips


def _reached(states: dict, start: str) -> set[str]:
    seen, todo = {start}, [start]
    while todo:
        for move in states[todo.pop()]["on"].values():
            if move["to"] in states and move["to"] not in seen:
                seen.add(move["to"])
                todo.append(move["to"])
    return seen


def _uncapped_loops(states: dict) -> list[str]:
    """The states without a cap that can come back to themselves through states without a cap."""
    free = {name for name, state in states.items() if "cap" not in state}
    after = {name: {m["to"] for m in states[name]["on"].values() if m["to"] in free} for name in free}
    looping = []
    for name in sorted(free):
        seen, todo = set(), list(after[name])
        while todo:
            state = todo.pop()
            if state not in seen:
                seen.add(state)
                todo.extend(after[state])
        if name in seen:
            looping.append(f"states.{name}: can repeat without end, no cap on the loop")
    return looping


def slips_of(definition) -> list[str]:
    """Where a definition of the family leaves the contract's format; an empty list if nowhere."""
    if not isinstance(definition, dict) or not isinstance(definition.get("states"), dict) or not definition["states"]:
        return ["the file is not a flow with states"]
    states = definition["states"]
    slips = []
    if definition.get("format") != 1 or isinstance(definition.get("format"), bool):
        slips.append("format: not the integer 1")
    slips += [f"{key}: not a name" for key in ("name", "stop_at") if not is_name(definition.get(key))]
    if definition.get("start") not in states:
        slips.append("start: not a declared state")
    budget = definition.get("budget")
    if not (is_amount(budget) and all(value > 0 for value in budget.values())):
        slips.append("budget: not dollars and minutes above 0")
    shaped = True
    for name, state in states.items():
        if not is_name(name) or name in files.ENDED or not isinstance(state, dict) \
                or not isinstance(state.get("on"), dict) or not state["on"] \
                or not all(isinstance(w, dict) for w in state.get("writes", [])):
            slips.append(f"states.{name}: not a named state with transitions")
            shaped = False
            continue
        moves = [slip for event, move in state["on"].items() for slip in _transition_slips(name, event, move, states)]
        slips += moves
        shaped = shaped and not moves
    if not shaped or definition.get("start") not in states:
        return slips
    writes: dict[str, str] = {}
    for name, state in states.items():
        slips += _state_slips(name, state, states, writes)
    slips += [f"states.{name}: no path leads to it" for name in states if name not in _reached(states, definition["start"])]
    slips += _uncapped_loops(states) + _premise_slips(states)
    if not any(move.get("reaches") == definition.get("stop_at") and move["to"] != "stopped"
               for state in states.values() for move in state["on"].values()):
        slips.append("stop_at: no step reaches it")
    return slips


def all_definitions() -> dict[str, dict]:
    found = {f"definitions/{name}.json": files.read_json(path) for name, path in files.definition_files().items()}
    for name, folder in files.place_folders().items():
        own = os.path.join(folder, "definition.json")
        if os.path.isfile(own):
            found[f"place/{name}/definition.json"] = files.read_json(own)
    return found


class DefinitionFormatTests(unittest.TestCase):
    def test_every_definition_follows_the_format(self):
        definitions = all_definitions()
        self.assertGreaterEqual(len(definitions), 4)
        for label, definition in definitions.items():
            with self.subTest(definition=label):
                self.assertEqual(slips_of(definition), [])

    def test_the_reader_of_this_test_does_see_a_slip(self):
        # Otherwise the test above would pass on anything.
        for damage, word in ((lambda d: d["states"]["coding"].pop("cap"), "repeat"),
                             (lambda d: d["states"]["draft_pr"]["writes"][0].update(key="the-branch"), "ticket"),
                             (lambda d: d["states"]["plan_review"].update(shows="the code"), "shows"),
                             (lambda d: d["states"]["ci_check"].pop("checks_premise"), "facts"),
                             (lambda d: d["states"]["delivery"].pop("deadline_hours"), "deadline"),
                             (lambda d: d.update(stop_at="nowhere"), "stop_at"),
                             (lambda d: d["states"]["ready"]["on"]["claimed"].update(to="nowhere"), "not a state")):
            definition = files.reference_template("feature")
            damage(definition)
            with self.subTest(expected=word):
                self.assertTrue(any(word in slip for slip in slips_of(definition)), slips_of(definition))

    def test_the_two_reference_templates_have_the_states_of_the_contract_in_its_order(self):
        for kind, states, start, stop_at, budget in (
                ("feature", FEATURE_STATES, "ready", "ready_pr", {"dollars": 20, "minutes": 240}),
                ("bug", BUG_STATES, "triage", "root_cause", {"dollars": 10, "minutes": 120})):
            definition = files.reference_template(kind)
            with self.subTest(template=kind):
                self.assertEqual(list(definition["states"]), states)
                self.assertEqual((definition["name"], definition["start"], definition["stop_at"], definition["budget"]),
                                 (kind, start, stop_at, budget))
                for name, state in definition["states"].items():
                    if state["type"] == "gate":
                        self.assertEqual((state["deadline_hours"], state["can_judge"]), (72, "yes"), name)
                    if state["type"] == "wait":
                        self.assertEqual(state["deadline_hours"], 6 if name == "ci_wait" else 168, name)
                    if state["type"] in RUNS:
                        self.assertEqual((state["survives"], state["units"], state["repositories"]),
                                         ("restart", "one", "one"), name)
                    if state["type"] == "agent":
                        self.assertEqual(state["weak_model"], "no", name)

    def test_every_case_holds_what_the_templates_do_not(self):
        states = files.read_json(files.definition_files()["every-case"])["states"]
        self.assertTrue(any(s["type"] == "human" for s in states.values()), "no step done by a person")
        self.assertTrue(any(s["type"] == "agent" and "cap" in s and s["on"].get("step_failed", {}).get("to") == name
                            for name, s in states.items()), "no agent that retries itself under a cap")
        self.assertTrue(any(s["type"] == "gate" and "deadline_passed" in s["on"] for s in states.values()),
                        "no gate that declares its deadline")
        self.assertTrue(any(m["to"] == "done" and "reason" not in m for s in states.values() for m in s["on"].values()),
                        "no transition to done without a reason")


class SequenceFormatTests(unittest.TestCase):
    def test_the_sequences_of_the_contract_are_all_there(self):
        self.assertEqual(sorted(set(files.CONTRACT_SEQUENCES) - set(files.sequence_files())), [])

    def test_every_sequence_follows_the_format(self):
        for name, path in files.sequence_files().items():
            sequence = files.read_json(path)
            with self.subTest(sequence=name):
                self.assertLessEqual(set(sequence), SEQUENCE_KEYS)
                self.assertTrue(isinstance(sequence.get("about"), str) and sequence["about"].strip())
                self.assertLessEqual(set(sequence.get("override", {})), OVERRIDABLE)
                definition = files.sequence_definition(sequence, files.reference_template)
                self.assertEqual(slips_of(definition), [], "the definition, once overridden, no longer holds")
                self.assertTrue(sequence.get("start") == "new" or isinstance(sequence.get("start"), dict))
                self.assertTrue(isinstance(sequence.get("events"), list) and sequence["events"])
                for number, step in enumerate(sequence["events"], 1):
                    self.check_step(definition, number, step)

    def check_step(self, definition: dict, number: int, step: dict) -> None:
        label = f"event {number}"
        self.assertLessEqual(set(step), STEP_KEYS, label)
        self.assertIn("event", step, label)
        expect = step.get("expect")
        self.assertIsInstance(expect, dict, label)
        self.assertLessEqual(EXPECT_REQUIRED, set(expect), label)
        self.assertLessEqual(set(expect), EXPECT_REQUIRED | EXPECT_OPTIONAL, label)
        self.assertIn(expect["outcome"], OUTCOMES, label)
        self.assertEqual(expect["reason"] is None, expect["outcome"] == "moved", label)
        self.assertTrue(expect["reason"] is None or is_name(expect["reason"]), label)
        for state, count in expect.get("visits", {}).items():
            self.assertIn(state, definition["states"], label)
            self.assertTrue(is_count(count) and count >= 0, label)
            self.assertLessEqual(count, definition["states"][state].get("cap", count), f"{label}: {state} above its cap")
        for key in ("spent", "remaining"):
            self.assertTrue(key not in expect or is_amount(expect[key]), f"{label}: {key}")
        self.assertIsInstance(expect.get("over_budget", False), bool, label)
        seen = expect.get("seen", [])
        self.assertTrue(isinstance(seen, list) and all(isinstance(ident, str) and ident for ident in seen),
                        f"{label}: seen is not a list of event identifiers")

    def test_every_expected_answer_is_one_the_definition_allows(self):
        """Not the rules of `flow next`, only what follows from them whatever the code: a move
        follows a declared transition, a refusal changes nothing, what is spent never falls and
        grows by the event's own costs, an ended run stays ended."""
        for name, path in files.sequence_files().items():
            sequence = files.read_json(path)
            definition = files.sequence_definition(sequence, files.reference_template)
            start = sequence["start"]
            state = definition["start"] if start == "new" else start.get("state")
            spent = {"dollars": 0, "minutes": 0} if start == "new" else start.get("spent")
            for number, step in enumerate(sequence["events"], 1):
                event, expect = step["event"], step["expect"]
                with self.subTest(sequence=name, event=number):
                    self.one_answer(definition, state, spent, event, expect)
                state = expect["state"]
                spent = expect.get("spent", spent)

    def one_answer(self, definition: dict, state, spent, event, expect: dict) -> None:
        outcome, states = expect["outcome"], definition["states"]
        if outcome in UNCHANGED:
            self.assertEqual(expect["state"], state, "a duplicate or refused event moved the run")
            self.assertEqual(expect.get("spent", spent), spent, "a duplicate or refused event cost something")
            return
        self.assertNotIn(state, files.ENDED, "an ended run moved")
        self.assertTrue(files.is_well_formed_event(event), "an ill-formed event was accepted")
        if outcome == "moved":
            self.assertIn(state, states)
            self.assertIn(event["type"], states[state]["on"], "no such transition out of this state")
            self.assertEqual(states[state]["on"][event["type"]]["to"], expect["state"])
        else:
            self.assertEqual(expect["state"], outcome)
        self.assertIn("spent", expect, "an accepted event must say what the run has spent")
        cost = {} if expect["reason"] == "inconsistent" else event.get("payload", {})
        for unit in ("dollars", "minutes"):
            self.assertEqual(expect["spent"][unit], spent[unit] + cost.get(unit, 0), f"{unit} spent")
        budget = definition["budget"]
        over = any(expect["spent"][unit] > budget[unit] for unit in budget)
        self.assertIs(expect.get("over_budget", over), over)
        if "remaining" in expect:
            self.assertEqual(expect["remaining"], {unit: max(0, budget[unit] - expect["spent"][unit]) for unit in budget})

    def test_costs_are_in_quarters_so_sums_are_exact(self):
        for name, path in files.sequence_files().items():
            for number, step in enumerate(files.read_json(path)["events"], 1):
                payload = step["event"].get("payload") if isinstance(step["event"], dict) else None
                for unit in ("dollars", "minutes"):
                    value = payload.get(unit, 0) if isinstance(payload, dict) else 0
                    with self.subTest(sequence=name, event=number, unit=unit):
                        self.assertTrue(is_number(value) and value % QUARTER == 0, value)


class PlaceFormatTests(unittest.TestCase):
    def test_the_three_flows_to_place_are_there(self):
        self.assertEqual(sorted(files.place_folders()), sorted(files.PLACE_FOLDERS))

    def test_every_answer_key_names_each_state_once_and_agrees_with_itself(self):
        for name, folder in files.place_folders().items():
            expected = files.read_json(os.path.join(folder, "expected.json"))
            with self.subTest(flow=name):
                self.assertEqual(set(expected), PLACE_KEYS)
                self.assertTrue(isinstance(expected["about"], str) and expected["about"].strip())
                definition = files.resolve(expected["definition"], files.reference_template)
                steps = expected["steps"]
                self.assertEqual(list(steps), list(definition["states"]))
                for state, destination in steps.items():
                    self.assertTrue(destination is None or destination in DESTINATIONS, state)
                self.assertEqual(expected["engine"], [s for s, d in steps.items() if d == "durable_engine"])
                self.assertEqual(expected["refused_gates"], [s for s, d in steps.items() if d == "no_gate"])
                self.assertEqual(expected["open"], [s for s, d in steps.items() if d is None])
                verdict = "open" if expected["open"] else "engine" if expected["engine"] else "no_engine"
                self.assertEqual(expected["verdict"], verdict)
                self.assertIs(expected["passed"], not expected["open"] and not expected["refused_gates"])
                self.assertEqual(os.path.isfile(os.path.join(folder, "traps.md")), name == "trapped")
                self.assertEqual(os.path.isfile(os.path.join(folder, "definition.json")),
                                 not expected["definition"].startswith(files.TEMPLATE_PREFIX))

    def test_the_trapped_flow_holds_exactly_what_the_contract_plants(self):
        folder = files.place_folders()["trapped"]
        states = files.read_json(os.path.join(folder, "definition.json"))["states"]
        expected = files.read_json(os.path.join(folder, "expected.json"))
        midway = [name for name, s in states.items() if s.get("survives") == "midway"]
        unjudged = [name for name, s in states.items() if s.get("can_judge") == "no"]
        self.assertEqual(len(midway), 1)
        self.assertEqual(len(unjudged), 1)
        self.assertEqual((expected["engine"], expected["refused_gates"]), (midway, unjudged))
        self.assertTrue(any(s["type"] == "gate" and s.get("can_judge") == "yes" for s in states.values()))
        self.assertTrue(all(s.get("shows") for s in states.values() if s["type"] == "gate"))
        for destination in ("campaign", "reusable_workflow", "dated_skill"):
            self.assertIn(destination, expected["steps"].values())
        self.assertEqual((expected["verdict"], expected["passed"]), ("engine", False))
        with open(os.path.join(folder, "traps.md"), encoding="utf-8") as fh:
            traps = fh.read()
        for planted in midway + unjudged:
            self.assertIn(f"`{planted}`", traps)


class FamilyPageTests(unittest.TestCase):
    def test_the_page_of_the_family_names_every_fixture(self):
        with open(os.path.join(files.FAMILY, "README.md"), encoding="utf-8") as fh:
            page = fh.read()
        names = [*files.sequence_files(), *files.definition_files(), *files.place_folders()]
        self.assertEqual([name for name in names if f"`{name}`" not in page], [])


class GeneratorTests(unittest.TestCase):
    """The events the other test generates, checked here because that test cannot run without the code."""

    def test_the_table_covers_every_event_type_with_and_without_costs_and_at(self):
        definition = files.reference_template("bug")
        events = files.table_events(definition, "triage")
        kinds = [*files.declared_events(definition), *files.BUILT_IN_EVENTS, files.UNKNOWN_EVENT]
        self.assertEqual(len(events), 4 * len(kinds))
        self.assertEqual(len({event["id"] for event in events}), len(events))
        ill_formed = [event["type"] for event in events if not files.is_well_formed_event(event)]
        self.assertEqual(sorted(ill_formed), ["deadline_passed", "deadline_passed", "step_failed", "step_failed"])

    def test_no_listed_ill_formed_event_is_well_formed(self):
        self.assertEqual([event for event in files.MALFORMED_EVENTS if files.is_well_formed_event(event)], [])

    def test_a_generated_sequence_is_the_same_on_every_machine_and_mostly_fits_the_state(self):
        definition = files.reference_template("feature")
        run = files.run_in("coding")
        first = [files.random_event(random.Random(7), definition, run, n, []) for n in range(50)]
        again = [files.random_event(random.Random(7), definition, run, n, []) for n in range(50)]
        self.assertEqual(first, again)
        rng = random.Random(7)
        drawn = [files.random_event(rng, definition, run, n, []) for n in range(400)]
        fitting = [e for e in drawn if isinstance(e, dict) and e.get("type") == "code_written"]
        self.assertGreater(len(fitting), 200)
        self.assertLess(len(fitting), 400)
        ended = [files.random_event(rng, definition, files.run_in("stopped"), n, drawn[:3]) for n in range(50)]
        self.assertEqual(len(ended), 50)


if __name__ == "__main__":
    unittest.main()
