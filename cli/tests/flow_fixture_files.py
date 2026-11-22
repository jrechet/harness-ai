"""Reading the fixture family `fixtures/flow/`, shared by its two tests.

`test_flow_fixtures.py` grades the code with the family; `test_flow_fixtures_format.py` checks the
family itself and needs no code. Nothing here imports `harnesslib.flow`: what a template is comes
in as a function, so the same reader serves both tests."""
from __future__ import annotations

import copy
import json
import os
import random
from typing import Callable

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FAMILY = os.path.join(ROOT, "fixtures", "flow")
TEMPLATE_PREFIX = "template:"
TEMPLATE_KINDS = ("feature", "bug")
ENDED = ("done", "stopped")
BUILT_IN_EVENTS = ("human_stop", "deadline_passed", "step_failed")
NEEDS_AT = ("deadline_passed", "step_failed")
UNKNOWN_EVENT = "nobody_declares_this"
UNKNOWN_STATE = "nobody_defined_this"

# The sequences the contract lists (section 8): fifteen, and the two twins.
CONTRACT_SEQUENCES = (
    "feature-to-ready-pr", "event-twice", "events-out-of-order", "lost-event", "step-failed",
    "stale-answer", "cap-reached", "budget-exceeded", "human-stop", "unknown-label",
    "counts-over-cap", "rework-loop", "bug-already-fixed", "bug-low-confidence",
    "bug-to-root-cause", "gate-deadline", "ci-stale-and-fix",
)
PLACE_FOLDERS = ("feature", "bug", "trapped")


def read_json(path: str):
    """The JSON value of a fixture file; a file that cannot be read fails with its path."""
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError) as exc:
        raise ValueError(f"{os.path.relpath(path, ROOT)}: the fixture cannot be read: {exc}") from exc


def _json_files(folder: str) -> dict[str, str]:
    """name without `.json` → path, for every JSON file of a folder of the family."""
    full = os.path.join(FAMILY, folder)
    if not os.path.isdir(full):
        raise ValueError(f"fixtures/flow/{folder}: the folder is missing")
    return {name[:-len(".json")]: os.path.join(full, name)
            for name in sorted(os.listdir(full)) if name.endswith(".json")}


def sequence_files() -> dict[str, str]:
    return _json_files("sequences")


def definition_files() -> dict[str, str]:
    return _json_files("definitions")


def place_folders() -> dict[str, str]:
    """name → path of each folder of `place/`."""
    full = os.path.join(FAMILY, "place")
    if not os.path.isdir(full):
        raise ValueError("fixtures/flow/place: the folder is missing")
    return {name: os.path.join(full, name) for name in sorted(os.listdir(full))
            if os.path.isdir(os.path.join(full, name))}


def reference_template(kind: str) -> dict:
    """The fixture author's own writing of a template, from the contract's tables."""
    return read_json(os.path.join(FAMILY, "definitions", f"{kind}.json"))


def resolve(reference: str, template: Callable[[str], dict]) -> dict:
    """A definition reference: `template:<kind>`, or a path relative to `fixtures/flow/`."""
    if not isinstance(reference, str) or not reference:
        raise ValueError(f"a definition reference must be a non-empty string, not {reference!r}")
    if reference.startswith(TEMPLATE_PREFIX):
        return template(reference[len(TEMPLATE_PREFIX):])
    return read_json(os.path.join(FAMILY, reference))


def with_override(definition: dict, override: dict | None) -> dict:
    """A copy of the definition whose top-level keys are replaced by those of `override`."""
    changed = copy.deepcopy(definition)
    changed.update(copy.deepcopy(override or {}))
    return changed


def sequence_definition(sequence: dict, template: Callable[[str], dict]) -> dict:
    return with_override(resolve(sequence.get("definition"), template), sequence.get("override"))


def declared_events(definition: dict) -> list[str]:
    """Every event type some state declares, in file order, once each."""
    found: list[str] = []
    for state in definition["states"].values():
        for event in state["on"]:
            if event not in found:
                found.append(event)
    return found


def run_in(state: str) -> dict:
    """A run document that sits in `state` for the first time, nothing spent."""
    ended = state in ENDED
    return {"state": state, "visits": {} if ended else {state: 1}, "spent": {"dollars": 0, "minutes": 0},
            "seen": [], "reason": "finished" if state == "done" else "human_stop" if ended else None}


def table_events(definition: dict, state: str) -> list[dict]:
    """For one state, every event type (declared anywhere, built in, unknown), each with and
    without its costs and with and without `at`: the whole table of the contract's section 8."""
    events = []
    for kind in [*declared_events(definition), *BUILT_IN_EVENTS, UNKNOWN_EVENT]:
        for costs in (True, False):
            for at in (True, False):
                event: dict = {"id": f"table:{state}:{kind}:{int(costs)}{int(at)}", "type": kind}
                if costs:
                    event["payload"] = {"dollars": 0.25, "minutes": 1}
                if at:
                    event["at"] = {"state": state, "visit": 1}
                events.append(event)
    return events


def is_well_formed_event(event) -> bool:
    """Rule 1 of the contract, read the other way round."""
    if not isinstance(event, dict):
        return False
    if not all(isinstance(event.get(key), str) and event[key] for key in ("id", "type")):
        return False
    if "payload" in event:
        payload = event["payload"]
        if not isinstance(payload, dict):
            return False
        for key in ("dollars", "minutes"):
            if key in payload and not _is_cost(payload[key]):
                return False
    if "at" in event:
        at = event["at"]
        if not isinstance(at, dict) or not (isinstance(at.get("state"), str) and at["state"]):
            return False
        if isinstance(at.get("visit"), bool) or not isinstance(at.get("visit"), int) or at["visit"] < 1:
            return False
    return "at" in event or event["type"] not in NEEDS_AT


def _is_cost(value) -> bool:
    return not isinstance(value, bool) and isinstance(value, (int, float)) and value == value \
        and value not in (float("inf"), float("-inf")) and value >= 0


MALFORMED_EVENTS = (None, "claimed", [], {"type": "claimed"}, {"id": "", "type": "claimed"},
                    {"id": "m1", "type": "claimed", "payload": None},
                    {"id": "m2", "type": "claimed", "payload": {"dollars": -1, "minutes": 1}},
                    {"id": "m3", "type": "claimed", "payload": {"dollars": True, "minutes": 1}},
                    {"id": "m4", "type": "claimed", "at": None},
                    {"id": "m5", "type": "claimed", "at": {"state": "ready", "visit": 0}},
                    {"id": "m6", "type": "deadline_passed"}, {"id": "m7", "type": "step_failed"})


def random_event(rng: random.Random, definition: dict, run: dict, number: int, sent: list[dict]):
    """The next event of a generated sequence. Most of the time an event the current state
    declares, for its current visit, so that the run goes far enough to meet caps and budget; the
    rest of the time what a real queue also delivers: an event sent before, one from elsewhere,
    one for an earlier round, a deadline, a failure, a human stop, something ill formed."""
    states = definition["states"]
    state = run.get("state") if isinstance(run, dict) else None
    here = states.get(state) if isinstance(state, str) else None
    visit = run["visits"].get(state, 1) if here else 1
    at = {"state": state, "visit": visit} if here else {"state": next(iter(states)), "visit": 1}
    costs = {"dollars": 0, "minutes": 0} if rng.random() < 0.6 else \
        {"dollars": rng.randrange(0, 5) * 0.25, "minutes": rng.randrange(0, 6)}
    event_id = f"gen-{number}"
    draw = rng.random()
    if here and draw < 0.70:
        # An event that keeps the run alive is drawn six times more often than one that ends it.
        choices = [kind for kind, move in here["on"].items()
                   for _ in range(1 if move.get("to") in ENDED else 6)]
        return {"id": event_id, "type": rng.choice(choices), "at": dict(at), "payload": costs}
    if sent and draw < 0.80:
        return copy.deepcopy(rng.choice(sent))
    if draw < 0.88:
        event = {"id": event_id, "type": rng.choice(declared_events(definition)), "payload": costs}
        if rng.random() < 0.5:
            event["at"] = {"state": rng.choice(list(states)), "visit": rng.randrange(1, 4)}
        return event
    if draw < 0.92:
        return {"id": event_id, "type": "deadline_passed", "at": dict(at)}
    if draw < 0.95:
        return {"id": event_id, "type": "step_failed", "at": dict(at), "payload": costs}
    if draw < 0.96:
        return {"id": event_id, "type": "human_stop", "payload": costs}
    if draw < 0.98:
        return {"id": event_id, "type": UNKNOWN_EVENT, "payload": costs}
    return copy.deepcopy(rng.choice(MALFORMED_EVENTS))
