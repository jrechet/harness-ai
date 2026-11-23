"""`flow` subcommand: a team's workflow from a ticket to production, written down and checked
before anything runs.

A flow is a small table of states in one JSON file: each state is one step (a program, an agent,
a person who works, a person who decides, or a wait) and says where each event leads. Nothing here
calls an agent, a network, a clock or a key. The contract is docs/workflow-harness/flow-spec.md.

  harness flow new feature|bug [--out FILE] [--force]   writes a starting definition from a template
  harness flow check <file>                             refuses a flow that could loop, wait or spend without end
  harness flow place <file>                             where each step belongs, and whether one needs an engine
  harness flow status <file> [--map]                    the level this flow has reached, on paper
  harness flow next <file> --event FILE (--run FILE | --new) [--save-run FILE]
                                                        what one run does on one event, and what is left to spend

This module holds the rules; the command line is flow_cli.py, the placement flow_place.py.
Exit codes: 0 fine, 1 refused or failing, 2 wrong usage or an input file that is missing or is not JSON."""
from __future__ import annotations

import argparse
import copy
import difflib
import importlib
import json
import math
import os
import re
import sys
from decimal import ROUND_CEILING, Decimal, DecimalException
from typing import Any

from . import flow_read

TEMPLATE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "flow_templates")
STEP_TYPES = ("code", "agent", "human", "gate", "wait")
ENDED = ("done", "stopped")
TEMPLATES = ("feature", "bug")
BUILT_IN_EVENTS = ("human_stop", "deadline_passed", "step_failed")
TYPE_WORDS = {"code": "a program", "agent": "an agent", "human": "a person works",
              "gate": "a person decides", "wait": "waits"}
# The steps that run something and so cost something: they may fail, and they report what they spent.
WORKERS = ("code", "agent")
NAME = re.compile(r"[a-z][a-z0-9_]*")
UNITS = ("dollars", "minutes")
RUN_KEYS = ("state", "visits", "spent", "seen", "reason")
DECIMALS = 4
SMALLEST_COST = Decimal(1).scaleb(-DECIMALS)
# From there on a float holds no fourth decimal: there is nothing to round up.
NO_DECIMALS_FROM = 1e11
# What a sum no float can hold is stored as: still a number, and above any budget.
TOO_MUCH = sys.float_info.max


# ---------------------------------------------------------------- small readers

def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _is_number(value: Any) -> bool:
    """A finite JSON number: never a boolean, never NaN or Infinity."""
    if isinstance(value, bool):
        return False
    return isinstance(value, int) or (isinstance(value, float) and math.isfinite(value))


def _is_name(value: Any) -> bool:
    return isinstance(value, str) and NAME.fullmatch(value) is not None


def _is_text(value: Any) -> bool:
    return isinstance(value, str) and value.strip() != ""


def _above_zero(value: Any) -> bool:
    return _is_number(value) and value > 0


def _budget_holds(budget: Any) -> bool:
    return isinstance(budget, dict) and all(_above_zero(budget.get(unit)) for unit in UNITS)


def _step_type(state: dict) -> str | None:
    """The state's type when it is one of the five, otherwise None."""
    kind = state.get("type")
    return kind if isinstance(kind, str) and kind in STEP_TYPES else None


def _show(number: Any) -> str:
    """A number as a person reads it: 5, not 5.0."""
    if isinstance(number, float) and number.is_integer() and abs(number) < 1e15:
        return str(int(number))
    try:
        return str(number)
    except ValueError:  # Python refuses to print a whole number of several thousand digits
        return "a number too large to print"


def load_definition(path: str) -> Any:
    """The parsed JSON value, whatever it is. Raises ValueError only if the file is missing, is not JSON,
    or writes a key twice in one object."""
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh, object_pairs_hook=flow_read.once)
    except OSError as exc:
        raise ValueError(f"{path}: the file cannot be read ({exc.strerror or exc})") from exc
    except flow_read.KeyWrittenTwice as exc:
        raise ValueError(f"{path}: {exc}") from exc
    except (ValueError, RecursionError) as exc:
        raise ValueError(f"{path}: the file is not JSON ({exc})") from exc


def new(kind: str) -> dict[str, Any]:
    """A fresh copy of the template `feature` or `bug`."""
    if not isinstance(kind, str) or kind not in TEMPLATES:
        raise ValueError(f"no template for {kind!r}: choose one of {', '.join(TEMPLATES)}")
    return load_definition(os.path.join(TEMPLATE_DIR, f"{kind}.json"))


# ---------------------------------------------------------------- flow check

def _problem(code: str, where: str, message: str) -> dict[str, str]:
    return {"code": code, "message": message, "where": where}


def _malformed(where: str, what: str) -> dict[str, str]:
    return _problem("malformed", where, f"The file cannot be read as a flow: {what}.")


def _leads_nowhere(states: dict) -> bool:
    """True when a transition names a target that is not a step or an end: the path stops there."""
    for state in states.values():
        on = state.get("on") if isinstance(state, dict) else None
        for transition in (on.values() if isinstance(on, dict) else ()):
            to = transition.get("to") if isinstance(transition, dict) else None
            if not (isinstance(to, str) and (to in states or to in ENDED)):
                return True
    return False


def _reachable(start: Any, states: dict) -> set:
    """The states a path of transitions leads to from `start`."""
    if not isinstance(start, str) or start not in states or _leads_nowhere(states):
        # No start to walk from, or a broken path: that is the problem reported, not every state
        # behind it. One mistyped target is one line; the steps no path leads to are told once it is fixed.
        return set(states)
    seen, todo = {start}, [start]
    while todo:
        state = states[todo.pop()]
        on = state.get("on") if isinstance(state, dict) else None
        for transition in (on.values() if isinstance(on, dict) else ()):
            to = transition.get("to") if isinstance(transition, dict) else None
            if isinstance(to, str) and to in states and to not in seen:
                seen.add(to)
                todo.append(to)
    return seen


def _stops_here(definition: Any, transition: Any) -> bool:
    """True for a transition that reaches the stop point: the run ends there, its target is not entered."""
    stop_at = definition.get("stop_at") if isinstance(definition, dict) else None
    return (isinstance(stop_at, str) and isinstance(transition, dict) and transition.get("reaches") == stop_at
            and transition.get("to") not in ENDED)


def _live(definition: dict) -> set:
    """The states a run can enter as the file is written: those a path leads to from the start
    without crossing the stop point. Read on a definition that is not malformed."""
    states = definition["states"]
    seen, todo = {definition["start"]}, [definition["start"]]
    while todo:
        for transition in states[todo.pop()]["on"].values():
            to = transition["to"]
            if to in states and to not in seen and not _stops_here(definition, transition):
                seen.add(to)
                todo.append(to)
    return seen


def stop_steps(definition: Any) -> list[str]:
    """The steps after which a run stops on purpose: those with a transition that reaches the
    stop point. Empty when the definition does not hold."""
    if check(definition):
        return []
    return [name for name, state in definition["states"].items()
            if any(_stops_here(definition, transition) for transition in state["on"].values())]


def beyond_stop(definition: Any) -> list[str]:
    """The steps described but never run as the file is written: every path to them crosses the
    stop point. In file order; empty when the definition does not hold."""
    if check(definition):
        return []
    live = _live(definition)
    return [name for name in definition["states"] if name not in live]


def _malformed_top(definition: dict) -> list[dict[str, str]]:
    out = []
    if not (_is_int(definition.get("format")) and definition["format"] == 1):
        out.append(_malformed("format", "format must be the number 1, the only version of this format"))
    if not _is_name(definition.get("name")):
        out.append(_malformed("name", "the flow needs a name made of lowercase letters, digits and underscores"))
    states = definition.get("states")
    states_hold = isinstance(states, dict) and bool(states)
    start = definition.get("start")
    if not isinstance(start, str):
        out.append(_malformed("start", "start must name the step where a ticket begins"))
    elif states_hold and start not in states:
        out.append(_malformed("start", f"start names {start}, which is not one of the steps"))
    if not states_hold:
        out.append(_malformed("states", "states must hold at least one step, by name"))
    if "stop_at" in definition and not _is_name(definition["stop_at"]):
        out.append(_malformed("stop_at", "stop_at must be a name made of lowercase letters, digits and underscores"))
    return out


def _malformed_transition(where: str, event: Any, transition: Any, kind: str | None, states: dict) -> list[dict]:
    out = []
    if not _is_name(event):
        out.append(_malformed(where, f"the event {event} is not a name made of lowercase letters, digits and underscores"))
    if event == "human_stop":
        out.append(_malformed(where, "a person can stop a run in every step, so human_stop is never declared"))
    if event == "step_failed" and kind is not None and kind not in WORKERS:
        out.append(_malformed(where, "step_failed can only be declared on a step a program or an agent performs"))
    if not isinstance(transition, dict) or "to" not in transition:
        return out + [_malformed(where, f"the event {event} does not say where it leads")]
    to = transition["to"]
    if not (isinstance(to, str) and (to in states or to in ENDED)):
        out.append(_malformed(where, f"the event {event} leads to {to}, which is not a step, done or stopped"
                                     + _meant(to, states)))
    elif to == "stopped" and "reason" not in transition:
        out.append(_malformed(where, f"the event {event} stops the run without a reason"))
    for key in ("reason", "reaches"):
        if key in transition and not _is_name(transition[key]):
            out.append(_malformed(where, f"the {key} of the event {event} is not a name"))
    return out


def _meant(to: Any, states: dict) -> str:
    """The step a mistyped target most likely meant, as the end of a sentence."""
    close = difflib.get_close_matches(to, [*states, *ENDED], n=1) if isinstance(to, str) else []
    return f' (did you mean "{close[0]}"?)' if close else ""


def _malformed_state(name: Any, state: Any, states: dict, reachable: set) -> list[dict[str, str]]:
    where = f"states.{name}"
    out = []
    if not _is_name(name):
        out.append(_malformed(where, f"{name} is not a name made of lowercase letters, digits and underscores"))
    elif name in ENDED:
        out.append(_malformed(where, f"{name} is one of the two ends of every flow and is never declared"))
    if not isinstance(state, dict):
        return out + [_malformed(where, f"the step {name} is not an object")]
    if not _is_text(state.get("does")):
        out.append(_malformed(where, f'the step {name} does not say what it does: add "does": "<one plain sentence>"'))
    if "cap" in state and not (_is_int(state["cap"]) and state["cap"] > 0):
        out.append(_malformed(where, f"the cap of the step {name} must be a whole number above 0"))
    writes = state.get("writes")
    if "writes" in state and not (isinstance(writes, list) and all(isinstance(entry, dict) for entry in writes)):
        out.append(_malformed(where, f"the writes of the step {name} must be a list of objects"))
    kind = _step_type(state)
    if "checks_premise" in state:
        if not isinstance(state["checks_premise"], bool):
            out.append(_malformed(where, f"checks_premise of the step {name} must be true or false"))
        elif state["checks_premise"] and kind is not None and kind not in WORKERS:
            out.append(_malformed(where, f"the step {name} checks its facts, which only a program or an agent can do"))
    if name not in reachable:
        out.append(_malformed(where, f'no path leads from the start to the step {name}: point the "to" of an event '
                                     "of an earlier step at it"))
    on = state.get("on")
    if not isinstance(on, dict) or not on:
        return out + [_malformed(where, f'the step {name} has no way out: it needs at least one event, written '
                                      '"on": {"<event>": {"to": "<step>"}}')]
    for event, transition in on.items():
        out.extend(_malformed_transition(f"{where}.on.{event}", event, transition, kind, states))
    return out


def _malformed_problems(definition: Any) -> list[dict[str, str]]:
    if not isinstance(definition, dict):
        return [_malformed("", "it is not a JSON object")]
    out = _malformed_top(definition) + _module("flow_paths").malformed_irreversible(definition)
    states = definition.get("states")
    if isinstance(states, dict):
        reachable = _reachable(definition.get("start"), states)
        for name, state in states.items():
            out.extend(_malformed_state(name, state, states, reachable))
    return out


def _unknown_types(states: dict) -> list[dict[str, str]]:
    out = []
    listed = ", ".join(STEP_TYPES)
    for name, state in states.items():
        if _step_type(state) is None:
            said = f"has the type {state['type']}, which is not" if state.get("type") is not None else "has no type: it must be"
            out.append(_problem("unknown_step_type", f"states.{name}", f"Step {name} {said} one of {listed}."))
    return out


def _loops_without_cap(definition: dict, states: dict) -> list[dict[str, str]]:
    """One problem per group of states without a cap that can reach each other in a circle. A
    transition that reaches the stop point ends the run, so no circle goes through it."""
    free = [name for name, state in states.items() if "cap" not in state]
    edges = {name: [t["to"] for t in states[name]["on"].values()
                    if t["to"] in free and not _stops_here(definition, t)] for name in free}
    reach = {}
    for name in free:
        seen, todo = set(), list(edges[name])
        while todo:
            other = todo.pop()
            if other not in seen:
                seen.add(other)
                todo.extend(edges[other])
        reach[name] = seen
    out, grouped = [], set()
    for name in free:
        if name in grouped or name not in reach[name]:
            continue
        group = [other for other in free if other in reach[name] and name in reach[other]]
        grouped.update(group)
        out.append(_problem("loop_without_cap", f"states.{name}",
                            f"The steps {', '.join(group)} can repeat without end: none of them has a cap. "
                            'Add "cap": <n> to one of them, the one that costs: the most times one run '
                            "may enter that step."))
    return out


def _writes_without_key(states: dict) -> list[dict[str, str]]:
    out, named = [], {}
    for name, state in states.items():
        for index, entry in enumerate(state.get("writes", [])):
            what, key = entry.get("what"), entry.get("key")
            where = f"states.{name}.writes[{index}]"
            if not _is_text(what) or not (isinstance(key, str) and "{ticket}" in key):
                shown = what if _is_text(what) else "something it does not name"
                out.append(_problem("write_without_key", where,
                                    f"Step {name} writes {shown} without a key derived from the ticket: "
                                    "run twice, the step could not recognise its own write. "
                                    'Write it {"what": "<the thing>", "key": "<name>-{ticket}"}.'))
            elif named.setdefault(key, what) != what:
                out.append(_problem("write_without_key", where,
                                    f"Step {name} writes {what} under the key {key}, which already names "
                                    f"{named[key]}. Give it a key of its own."))
    return out


def _stop_and_budget(definition: dict, states: dict) -> list[dict[str, str]]:
    out = []
    stop_at = definition.get("stop_at")
    reached = []
    for state in states.values():
        for transition in state["on"].values():
            name = transition.get("reaches")
            if transition["to"] != "stopped" and name is not None and name not in reached:
                reached.append(name)
    choice = (f"Choose one of: {', '.join(reached)} (the names given by \"reaches\" on a transition)." if reached else
              'No transition names one yet: add "reaches": "<name>" to the transition after which a run stops on '
              'purpose, then "stop_at": "<name>".')
    if stop_at is None:
        out.append(_problem("no_stop_point", "stop_at",
                            f'The flow does not say where it stops on purpose: it has no "stop_at". {choice}'))
    elif stop_at not in reached:
        out.append(_problem("no_stop_point", "stop_at",
                            f'stop_at is "{stop_at}", which is not a stop point of this flow: a stop point is not '
                            f"a step, it is a name a transition reaches. {choice}"))
    if not _budget_holds(definition.get("budget")):
        out.append(_problem("no_budget", "budget", "The flow has no budget in dollars and minutes for one ticket. "
                            'Add "budget": {"dollars": <n>, "minutes": <n>}, both above 0.'))
    return out


def _premise_checks(states: dict) -> list[dict[str, str]]:
    out = []
    for name, state in states.items():
        kind = _step_type(state)
        if state.get("checks_premise") is True and len(state["on"]) < 2:
            out.append(_problem("wait_without_premise_check", f"states.{name}",
                                f"The step {name} checks its facts but has one way out only: "
                                'it cannot say they changed. Add a second event to its "on", for example '
                                '"premise_failed": {"to": "stopped", "reason": "premise_failed"}.'))
        if kind not in ("wait", "human", "gate"):
            continue
        for event, transition in state["on"].items():
            target = states.get(transition["to"])
            if target is None or _step_type(target) not in WORKERS or target.get("checks_premise") is True:
                continue
            if kind == "gate" and not target.get("writes"):
                continue  # nothing outside changes until a later step that writes
            out.append(_problem("wait_without_premise_check", f"states.{name}.on.{event}",
                                f"After {name}, the step {transition['to']} does not check that the facts "
                                f'still hold. Add "checks_premise": true to {transition["to"]}, and an event in '
                                'its "on" for the case where they changed.'))
    return out


def _written(states: dict, but: str, among: set) -> list[str]:
    """What the steps of `among`, `but` left aside, write outside: each thing once, in file order."""
    found = []
    for other, step in states.items():
        for entry in (step.get("writes", []) if other != but and other in among else []):
            if _is_text(entry.get("what")) and entry["what"] not in found:
                found.append(entry["what"])
    return found


def _shows_nothing(name: str, state: dict, states: dict, live: set) -> str | None:
    """A gate must show its judge something another step wrote; a gate a run can enter, something
    written by a step a run can enter too."""
    shows = state.get("shows")
    if not _is_text(shows):
        return (f'The gate {name} shows its judge nothing a step wrote: nobody could judge it. Add "shows": '
                'the "what" of a "writes" entry of an earlier step.')
    written = _written(states, name, live if name in live else set(states))
    if shows in written:
        return None
    late = (" Only a step after the point where a run stops writes it: such a step never runs."
            if shows in _written(states, name, set(states)) else "")
    known = "Use one of: " + ", ".join(f'"{what}"' for what in written) + ", or add" if written else "Add"
    return (f'The gate {name} shows its judge "{shows}", which is nothing a step wrote: nobody could judge it.'
            f'{late} {known} a "writes" entry with that "what" to the step that produces it.')


def _gate_problems(code: str, name: str, state: dict, states: dict, live: set) -> str | None:
    """The sentence of one gate rule when the gate breaks it."""
    if code == "gate_without_judge" and not _is_text(state.get("judge")):
        return f'The gate {name} names nobody who decides. Add "judge": "<who decides, by role or by name>".'
    if code == "gate_without_deadline" and not _above_zero(state.get("deadline_hours")):
        return (f"The gate {name} has no deadline: a silent approver would hold the ticket for ever. "
                'Add "deadline_hours": <n>.')
    if code == "gate_cannot_refuse":
        targets = {t["to"] for event, t in state["on"].items() if event != "deadline_passed"}
        if len(targets) < 2:
            return (f'The gate {name} can only say yes: nothing leads anywhere else. Add a second event to its "on" '
                    'that leads somewhere else, for example "refused": {"to": "stopped", "reason": "refused"}.')
    if code == "gate_shows_nothing":
        return _shows_nothing(name, state, states, live)
    return None


def _waits_and_gates(states: dict, live: set) -> list[dict[str, str]]:
    out = []
    for name, state in states.items():
        if _step_type(state) in ("wait", "human") and not _above_zero(state.get("deadline_hours")):
            out.append(_problem("wait_without_deadline", f"states.{name}",
                                f"The step {name} waits with no deadline: a lost event would hold the ticket "
                                'for ever. Add "deadline_hours": <n>.'))
    for code in ("gate_without_judge", "gate_without_deadline", "gate_cannot_refuse", "gate_shows_nothing"):
        for name, state in states.items():
            sentence = _gate_problems(code, name, state, states, live) if _step_type(state) == "gate" else None
            if sentence:
                out.append(_problem(code, f"states.{name}", sentence))
    return out


def check(definition: Any) -> list[dict[str, str]]:
    """The problems of a definition, `{"code", "message", "where"}` each; an empty list means it holds.
    `malformed` comes first and alone: the other rules need a readable structure. Never raises."""
    malformed = _malformed_problems(definition)
    if malformed:
        return malformed
    states = definition["states"]
    return (_unknown_types(states) + _loops_without_cap(definition, states) + _writes_without_key(states)
            + _stop_and_budget(definition, states) + _premise_checks(states)
            + _waits_and_gates(states, _live(definition)) + _module("flow_paths").unguarded(definition))


# ---------------------------------------------------------------- flow next

def new_run(definition: dict[str, Any]) -> dict[str, Any]:
    """The run before any event."""
    start = definition["start"]
    return {"state": start, "visits": {start: 1}, "spent": {unit: 0 for unit in UNITS}, "seen": [], "reason": None}


def _counted(cost: Any) -> Any:
    """A cost as it is counted: rounded up to four decimals, so that no cost above 0 counts for nothing."""
    if isinstance(cost, int) or cost >= NO_DECIMALS_FROM:
        return cost
    try:
        return float(Decimal(repr(cost)).quantize(SMALLEST_COST, rounding=ROUND_CEILING))
    except (DecimalException, ValueError, OverflowError):
        return cost


def _add(spent: Any, cost: Any) -> Any:
    """What was spent plus a cost rounded up, the sum rounded to four decimals; a sum no float can
    hold stays a number, above any budget."""
    try:
        total = round(spent + _counted(cost), DECIMALS)
    except OverflowError:
        return spent if spent > TOO_MUCH else TOO_MUCH  # what was spent never falls
    return total if _is_number(total) else TOO_MUCH


def _left(budget: Any, spent: Any) -> Any:
    try:
        return max(0, round(budget - spent, DECIMALS))
    except OverflowError:
        return 0


def _spent_holds(spent: Any) -> bool:
    return isinstance(spent, dict) and all(_is_number(spent.get(unit)) and spent[unit] >= 0 for unit in UNITS)


def _readable(definition: Any) -> tuple[dict, dict]:
    """The states and the budget `next_state` can use, whatever the definition is."""
    states = definition.get("states") if isinstance(definition, dict) else None
    budget = definition.get("budget") if isinstance(definition, dict) else None
    steps = {name: state for name, state in states.items() if isinstance(state, dict)} if isinstance(states, dict) else {}
    return steps, {unit: budget[unit] if isinstance(budget, dict) and _is_number(budget.get(unit)) else None
                   for unit in UNITS}


def _transitions(state: dict) -> dict:
    on = state.get("on")
    return {event: t for event, t in on.items() if isinstance(t, dict)} if isinstance(on, dict) else {}


def _over(budget: dict, spent: dict) -> bool:
    return any(budget[unit] is not None and spent[unit] > budget[unit] for unit in UNITS)


def _answer(budget: dict, outcome: str, reason: str | None, transition: dict | None, message: str, run: Any) -> dict:
    spent = run.get("spent") if isinstance(run, dict) else None
    if _spent_holds(spent):
        remaining = {unit: None if budget[unit] is None else _left(budget[unit], spent[unit]) for unit in UNITS}
        over = _over(budget, spent)
    else:
        remaining, over = None, False
    return {"outcome": outcome, "reason": reason, "transition": transition, "message": message, "run": run,
            "remaining": remaining, "over_budget": over}


def _as_given(value: Any) -> Any:
    """A copy of whatever was given, so the caller's object is never the one returned."""
    try:
        return copy.deepcopy(value)
    except Exception:  # an object that cannot be copied is not JSON; it is given back rather than failing
        return value


def _event_fault(event: Any) -> str | None:
    """What makes an event unreadable, in plain words; None when it is well formed (rule 1)."""
    if not isinstance(event, dict):
        return "it is not a JSON object"
    for key, what in (("id", '"<ticket>:<step>:<round>:<what happened>", the same each time the same fact '
                              "is delivered"), ("type", '"<what happened>", an event of the step the run is at')):
        if not (isinstance(event.get(key), str) and event[key]):
            return f'its "{key}" is missing or is not text: add "{key}": {what}'
    if "payload" in event:
        payload = event["payload"]
        if not isinstance(payload, dict):
            return "its payload is not an object"
        for unit in UNITS:
            if unit in payload and not (_is_number(payload[unit]) and payload[unit] >= 0):
                return f'the {unit} it reports are not a number at or above 0: write "{unit}": <n> in its "payload"'
    if "at" in event:
        at = event["at"]
        if not (isinstance(at, dict) and isinstance(at.get("state"), str) and at["state"]
                and _is_int(at.get("visit")) and at["visit"] > 0):
            return ('its "at" does not say which step and which round it answers: write '
                    '"at": {"state": "<step>", "visit": <n>}')
    elif event["type"] in ("deadline_passed", "step_failed"):
        return (f"a {event['type']} event must say which step and which round it answers: add "
                '"at": {"state": "<step>", "visit": <n>}')
    return None


def _visits_hold(states: dict, visits: Any) -> bool:
    return isinstance(visits, dict) and all(isinstance(name, str) and name in states and _is_int(count) and count >= 0
                                            for name, count in visits.items())


def _seen_holds(seen: Any) -> bool:
    return isinstance(seen, list) and all(isinstance(ident, str) for ident in seen)


def _run_fault(states: dict, run: Any) -> str | None:
    """What makes a run inconsistent with the flow, in plain words; None when it holds (rule 3)."""
    if not isinstance(run, dict):
        return "it is not a JSON object"
    missing = [key for key in RUN_KEYS if key not in run]
    if missing:
        return f"it lacks {', '.join(missing)}"
    state = run["state"]
    if not (isinstance(state, str) and state in states):
        return f"its state, {state}, is not a step of this flow" if isinstance(state, str) else "its state is not a name"
    if not _visits_hold(states, run["visits"]):
        return "its counts of visits are not whole numbers for steps of this flow"
    if run["visits"].get(state, 0) < 1:
        return f"it is at {state} without having entered it"
    for name, count in run["visits"].items():
        cap = states[name].get("cap")
        if _is_int(cap) and count > cap:
            return f"the step {name} ran {_show(count)} times, above its cap of {cap}"
    if not _spent_holds(run["spent"]):
        return "what it spent is not two numbers at or above 0"
    if not _seen_holds(run["seen"]):
        return "its list of events already seen is not a list of identifiers"
    if run["reason"] is not None:
        return "it carries a reason although it has not ended"
    return None


def _inconsistent(states: dict, budget: dict, run: Any, event: dict, what: str) -> dict:
    given = run if isinstance(run, dict) else {}
    seen = list(given["seen"]) if _seen_holds(given.get("seen")) else []
    if event["id"] not in seen:
        seen.append(event["id"])
    stopped = {"state": "stopped",
               "visits": dict(given["visits"]) if _visits_hold(states, given.get("visits")) else {},
               "spent": ({unit: given["spent"][unit] for unit in UNITS} if _spent_holds(given.get("spent"))
                         else {unit: 0 for unit in UNITS}),
               "seen": seen, "reason": "inconsistent"}
    state = given.get("state")
    transition = {"from": state if isinstance(state, str) else None, "event": event["type"], "to": "stopped"}
    return _answer(budget, "stopped", "inconsistent", transition,
                   f"Stopped: the run record does not match the flow ({what}). Nothing was continued from it.", stopped)


def _same(run: dict) -> dict:
    return {"state": run["state"], "visits": dict(run["visits"]), "spent": {unit: run["spent"][unit] for unit in UNITS},
            "seen": list(run["seen"]), "reason": run["reason"]}


def _accepted(run: dict, event: dict) -> dict:
    """The run with the event taken into account: its id recorded, its costs added. State and reason come after."""
    after = _same(run)
    if event["id"] not in after["seen"]:  # only a human stop gets here with an id already seen
        after["seen"].append(event["id"])
    payload = event.get("payload", {})
    for unit in UNITS:
        if unit in payload:
            after["spent"][unit] = _add(after["spent"][unit], payload[unit])
    return after


def _refusal(states: dict, run: dict, event: dict) -> tuple[str, str] | None:
    """Rules 6 to 8: the event does not belong here, answers another round, or hides what the step cost."""
    state, kind = run["state"], event["type"]
    step = states[state]
    worker = _step_type(step) in WORKERS
    if kind not in _transitions(step) and kind != "deadline_passed" and not (kind == "step_failed" and worker):
        if kind in BUILT_IN_EVENTS or any(kind in _transitions(other) for other in states.values()):
            expected = ", ".join(_transitions(step)) or "nothing"
            return "event_not_expected", (f"Refused: the event {kind} is not expected while the run is at {state}. "
                                          f"Expected here: {expected}.")
        return "unknown_event", f"Refused: no step of this flow knows the event {kind}."
    at, count = event.get("at"), run["visits"][state]
    if at is not None and (at["state"] != state or at["visit"] != count):
        return "stale_event", (f"Refused: the event {kind} answers {at['state']}, round {_show(at['visit'])}, "
                               f"but the run is at {state}, round {_show(count)}.")
    payload = event.get("payload", {})
    # A deadline nobody declared, or one that ends the run, comes from outside the step and knows no
    # cost; one declared towards a step starts work again, and what was spent must be counted.
    retry = _transitions(step).get(kind, {}).get("to") in states
    if worker and (kind != "deadline_passed" or retry) and not all(unit in payload for unit in UNITS):
        return "cost_missing", (f"Refused: the event {kind} ends the step {state} without saying what it cost. "
                                'Add "payload": {"dollars": <n>, "minutes": <n>} to the event; 0 is a cost.')
    return None


def _decide(definition: dict, states: dict, budget: dict, run: dict, after: dict, event: dict) -> tuple:
    """Rules 9 to 14, on a run that already counts the event: (outcome, reason, new state, message)."""
    state, kind = run["state"], event["type"]
    transition = _transitions(states[state]).get(kind)
    if transition is None:
        said = "its deadline went by with no answer" if kind == "deadline_passed" else "it failed"
        return "stopped", kind, "stopped", f"Stopped at {state}: {said}."
    to, reason = transition.get("to"), transition.get("reason")
    if to == "stopped":
        reason = reason if isinstance(reason, str) else "stopped"
        return "stopped", reason, "stopped", f"Stopped at {state}, on {kind}: {reason}."
    if to == "done":
        reason = reason if isinstance(reason, str) else "finished"
        return "done", reason, "done", f"Done at {state}, on {kind}: {reason}."
    stop_at = definition.get("stop_at")
    if isinstance(stop_at, str) and transition.get("reaches") == stop_at:
        return "done", "stop_point", "done", f"Done: the flow reached {stop_at}, where it stops on purpose."
    if _over(budget, after["spent"]):
        return "stopped", "budget_exceeded", "stopped", (
            f"Stopped: the run has spent {_show(after['spent']['dollars'])} dollars and "
            f"{_show(after['spent']['minutes'])} minutes, more than its budget of {_show(budget['dollars'])} "
            f"dollars and {_show(budget['minutes'])} minutes.")
    if not (isinstance(to, str) and to in states):
        return "stopped", "inconsistent", "stopped", f"Stopped: the event {kind} leads to no step of this flow."
    cap, count = states[to].get("cap"), after["visits"].get(to, 0)
    if _is_int(cap) and count >= cap:
        return "stopped", "cap_reached", "stopped", f"Stopped: the step {to} already ran {_show(count)} times, its cap."
    return "moved", None, to, f"{state} → {to}, on {kind}."


def next_state(definition: Any, run: Any, event: Any) -> dict[str, Any]:
    """What one run does on one event: the fourteen rules of the contract, the first that applies decides.
    Pure: no clock, no file, no randomness; it never changes its arguments and never raises."""
    states, budget = _readable(definition)
    fault = _event_fault(event)
    if fault:
        return _answer(budget, "refused", "malformed_event", None,
                       f"Refused: the event cannot be read: {fault}.", _as_given(run))
    if isinstance(run, dict) and isinstance(run.get("state"), str) and run["state"] in ENDED:
        why = f" ({run['reason']})" if isinstance(run.get("reason"), str) else ""
        return _answer(budget, "refused", "run_ended", None,
                       f"Refused: this run already ended{why}. Nothing moves any more.", _as_given(run))
    fault = _run_fault(states, run)
    if fault:
        return _inconsistent(states, budget, run, event, fault)
    if event["id"] in run["seen"] and event["type"] != "human_stop":
        return _answer(budget, "duplicate", "already_seen", None,
                       f"Event {event['id']} was already taken into account: nothing changes.", _same(run))
    state, kind = run["state"], event["type"]
    if kind == "human_stop":
        outcome, reason, to, message = "stopped", "human_stop", "stopped", f"Stopped by a person, at {state}."
    else:
        refusal = _refusal(states, run, event)
        if refusal:
            return _answer(budget, "refused", refusal[0], None, refusal[1], _same(run))
    after = _accepted(run, event)
    if kind != "human_stop":
        outcome, reason, to, message = _decide(definition, states, budget, run, after, event)
    after["state"], after["reason"] = to, reason
    if outcome == "moved":
        after["visits"][to] = after["visits"].get(to, 0) + 1
    return _answer(budget, outcome, reason, {"from": state, "event": kind, "to": to}, message, after)


# ---------------------------------------------------------------- the other modules of the contract

def _module(name: str) -> Any:
    """The placement, the status and the command line are modules of their own, which read this
    one: each is loaded when it is first asked for."""
    return importlib.import_module(f"{__package__}.{name}")


def _placement_module() -> Any:
    """The placement is another module of the same contract: it is read only when a flow is placed."""
    return _module("flow_place")


def status(definition: Any, placement: Any = None, measured: Any = None) -> dict[str, Any]:
    """Where a flow stands on the ladder. This version measures level 1, Mapped, from the file alone."""
    return _module("flow_status").status(definition, placement, measured)


def render_map(state: dict[str, Any]) -> str:
    """The short map, in plain words, from a `status` document."""
    return _module("flow_status").render_map(state)


def render_status(state: dict[str, Any]) -> str:
    """The level in one line, then one line per check."""
    return _module("flow_status").render_status(state)


def build_parser(parser: argparse.ArgumentParser | None = None) -> argparse.ArgumentParser:
    return _module("flow_cli").build_parser(parser)


def main(argv: list[str] | None = None, args: argparse.Namespace | None = None) -> int:
    return _module("flow_cli").main(argv, args)


if __name__ == "__main__":
    sys.exit(main())
