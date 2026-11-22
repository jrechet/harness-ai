"""`flow` subcommand: a team's workflow from a ticket to production, written down and checked
before anything runs.

A flow is a small table of states in one JSON file: each state is one step (a program, an agent,
a person who works, a person who decides, or a wait) and says where each event leads. Nothing here
calls an agent, a network, a clock or a key. The contract is docs/workflow-harness/flow-spec.md.

  harness flow new feature|bug [--out FILE] [--force]   writes a starting definition from a template
  harness flow check <file>                             refuses a flow that could loop, wait or spend without end
  harness flow next <file> --event FILE (--run FILE | --new)
                                                        what one run does on one event, and what is left to spend
  harness flow place <file>                             where each step belongs, and whether one needs an engine
  harness flow status <file> [--map]                    the level this flow has reached, on paper

Exit codes: 0 fine, 1 refused or failing, 2 wrong usage or an input file that is missing or is not JSON."""
from __future__ import annotations

import argparse
import copy
import importlib
import json
import math
import os
import re
import sys
from typing import Any

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
# What a sum no float can hold is stored as: still a number, and above any budget.
TOO_MUCH = sys.float_info.max
NOT_A_FLOW = "the file cannot be read as a flow"
LADDER = ((0, "None", "the phases are chained by hand"),
          (1, "Mapped", "the flow is written down and every step has a place"),
          (2, "Shadow", "the flow runs on real tickets and only comments"),
          (3, "Drafting", "runs end with a draft PR; CI and review results come back to the run"),
          (4, "Delivering", "runs reach a reviewed PR and merge only on a human's word"))
NOTHING_MORE = ("Nothing more on paper. The next level needs the flow to run on real tickets, "
                "which this version does not do yet.")


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
    """The parsed JSON value, whatever it is. Raises ValueError only if the file is missing or is not JSON."""
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except OSError as exc:
        raise ValueError(f"{path}: the file cannot be read ({exc.strerror or exc})") from exc
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


def _reachable(start: Any, states: dict) -> set:
    """The states a path of transitions leads to from `start`."""
    if not isinstance(start, str) or start not in states:
        return set(states)  # no start to walk from: that is the problem reported, not every state
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
        out.append(_malformed(where, f"the event {event} leads to {to}, which is not a step, done or stopped"))
    elif to == "stopped" and "reason" not in transition:
        out.append(_malformed(where, f"the event {event} stops the run without a reason"))
    for key in ("reason", "reaches"):
        if key in transition and not _is_name(transition[key]):
            out.append(_malformed(where, f"the {key} of the event {event} is not a name"))
    return out


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
        out.append(_malformed(where, f"the step {name} does not say what it does"))
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
        out.append(_malformed(where, f"no path leads from the start to the step {name}"))
    on = state.get("on")
    if not isinstance(on, dict) or not on:
        return out + [_malformed(where, f"the step {name} has no way out: it needs at least one event")]
    for event, transition in on.items():
        out.extend(_malformed_transition(f"{where}.on.{event}", event, transition, kind, states))
    return out


def _malformed_problems(definition: Any) -> list[dict[str, str]]:
    if not isinstance(definition, dict):
        return [_malformed("", "it is not a JSON object")]
    out = _malformed_top(definition)
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


def _loops_without_cap(states: dict) -> list[dict[str, str]]:
    """One problem per group of states without a cap that can reach each other in a circle."""
    free = [name for name, state in states.items() if "cap" not in state]
    edges = {name: [t["to"] for t in states[name]["on"].values() if t["to"] in free] for name in free}
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
                            f"The steps {', '.join(group)} can repeat without end: none of them has a cap."))
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
                                    "run twice, the step could not recognise its own write."))
            elif named.setdefault(key, what) != what:
                out.append(_problem("write_without_key", where,
                                    f"Step {name} writes {what} under the key {key}, which already names {named[key]}."))
    return out


def _stop_and_budget(definition: dict, states: dict) -> list[dict[str, str]]:
    out = []
    stop_at = definition.get("stop_at")
    reached = {t.get("reaches") for state in states.values() for t in state["on"].values() if t["to"] != "stopped"}
    if stop_at is None:
        out.append(_problem("no_stop_point", "stop_at", "The flow does not say where it stops on purpose."))
    elif stop_at not in reached:
        out.append(_problem("no_stop_point", "stop_at", f"The flow stops at {stop_at}, which no step reaches."))
    if not _budget_holds(definition.get("budget")):
        out.append(_problem("no_budget", "budget", "The flow has no budget in dollars and minutes for one ticket."))
    return out


def _premise_checks(states: dict) -> list[dict[str, str]]:
    out = []
    for name, state in states.items():
        kind = _step_type(state)
        if state.get("checks_premise") is True and len(state["on"]) < 2:
            out.append(_problem("wait_without_premise_check", f"states.{name}",
                                f"The step {name} checks its facts but has one way out only: "
                                "it cannot say they changed."))
        if kind not in ("wait", "human", "gate"):
            continue
        for event, transition in state["on"].items():
            target = states.get(transition["to"])
            if target is None or _step_type(target) not in WORKERS or target.get("checks_premise") is True:
                continue
            if kind == "gate" and not target.get("writes"):
                continue  # nothing outside changes until a later step that writes
            out.append(_problem("wait_without_premise_check", f"states.{name}.on.{event}",
                                f"After {name}, the step {transition['to']} does not check that the facts still hold."))
    return out


def _gate_problems(code: str, name: str, state: dict, states: dict) -> str | None:
    """The sentence of one gate rule when the gate breaks it."""
    if code == "gate_without_judge" and not _is_text(state.get("judge")):
        return f"The gate {name} names nobody who decides."
    if code == "gate_without_deadline" and not _above_zero(state.get("deadline_hours")):
        return f"The gate {name} has no deadline: a silent approver would hold the ticket for ever."
    if code == "gate_cannot_refuse":
        targets = {t["to"] for event, t in state["on"].items() if event != "deadline_passed"}
        if len(targets) < 2:
            return f"The gate {name} can only say yes: nothing leads anywhere else."
    if code == "gate_shows_nothing":
        written = {entry.get("what") for other, step in states.items() if other != name
                   for entry in step.get("writes", []) if isinstance(entry.get("what"), str)}
        shows = state.get("shows")
        if not _is_text(shows) or shows not in written:
            return f"The gate {name} shows its judge nothing a step wrote: nobody could judge it."
    return None


def _waits_and_gates(states: dict) -> list[dict[str, str]]:
    out = []
    for name, state in states.items():
        if _step_type(state) in ("wait", "human") and not _above_zero(state.get("deadline_hours")):
            out.append(_problem("wait_without_deadline", f"states.{name}",
                                f"The step {name} waits with no deadline: a lost event would hold the ticket for ever."))
    for code in ("gate_without_judge", "gate_without_deadline", "gate_cannot_refuse", "gate_shows_nothing"):
        for name, state in states.items():
            sentence = _gate_problems(code, name, state, states) if _step_type(state) == "gate" else None
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
    return (_unknown_types(states) + _loops_without_cap(states) + _writes_without_key(states)
            + _stop_and_budget(definition, states) + _premise_checks(states) + _waits_and_gates(states))


# ---------------------------------------------------------------- flow next

def new_run(definition: dict[str, Any]) -> dict[str, Any]:
    """The run before any event."""
    start = definition["start"]
    return {"state": start, "visits": {start: 1}, "spent": {unit: 0 for unit in UNITS}, "seen": [], "reason": None}


def _add(spent: Any, cost: Any) -> Any:
    """A sum rounded to four decimals; a sum no float can hold stays a number, above any budget."""
    try:
        total = round(spent + cost, DECIMALS)
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
    for key in ("id", "type"):
        if not (isinstance(event.get(key), str) and event[key]):
            return f"its {key} is missing or is not text"
    if "payload" in event:
        payload = event["payload"]
        if not isinstance(payload, dict):
            return "its payload is not an object"
        for unit in UNITS:
            if unit in payload and not (_is_number(payload[unit]) and payload[unit] >= 0):
                return f"the {unit} it reports are not a number at or above 0"
    if "at" in event:
        at = event["at"]
        if not (isinstance(at, dict) and isinstance(at.get("state"), str) and at["state"]
                and _is_int(at.get("visit")) and at["visit"] > 0):
            return "it does not say which step and which round it answers"
    elif event["type"] in ("deadline_passed", "step_failed"):
        return f"a {event['type']} event must say which step and which round it answers"
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
    if worker and kind != "deadline_passed" and not all(unit in payload for unit in UNITS):
        return "cost_missing", (f"Refused: the event {kind} ends the step {state} without saying "
                                "what it cost in dollars and minutes.")
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
    if event["id"] in run["seen"]:
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


# ---------------------------------------------------------------- flow status

def _placement_detail(placement: Any) -> list[str]:
    """One sentence per step that has no place yet and per gate nobody can judge."""
    if not isinstance(placement, dict):
        return ["the steps could not be placed"]
    out, told = [], set()
    steps = placement.get("steps")
    for step in (steps if isinstance(steps, list) else []):
        missing = step.get("missing") if isinstance(step, dict) else None
        if isinstance(missing, dict) and step.get("status") == "open":
            told.add(step.get("state"))
            out.append(f"The step {step.get('state')} has no answer to \"{missing.get('text')}\" "
                       f"(key {missing.get('key')}).")
    for name in placement.get("open") or []:
        if name not in told:
            out.append(f"The step {name} cannot be placed yet.")
    for name in placement.get("refused_gates") or []:
        out.append(f"A gate nobody can judge: {name}. Remove it, or give its judge something they can read and refuse.")
    return out or ["a step has no place"]


def _placement_module() -> Any:
    """The placement is another module of the same contract: it is read only when a flow is placed."""
    return importlib.import_module(f"{__package__}.flow_place")


def status(definition: Any, placement: Any = None) -> dict[str, Any]:
    """Where a flow stands on the ladder. This version measures level 1, Mapped, from the file alone."""
    problems = check(definition)
    malformed = any(p["code"] == "malformed" for p in problems)
    if placement is None and not malformed:
        placement = _placement_module().place(definition)
    unset = [p["message"] for p in problems if p["code"] in ("no_stop_point", "no_budget")]
    placed = isinstance(placement, dict) and placement.get("passed") is True
    results = [("definition_holds", not problems, "flow check", "the flow is written down and holds together",
                [p["message"] for p in problems]),
               ("steps_placed", placed and not malformed, "flow place", "every step has a place",
                [NOT_A_FLOW] if malformed else [] if placed else _placement_detail(placement)),
               ("stop_and_budget", not unset and not malformed, "the definition file",
                "a stop point and a budget are set", [NOT_A_FLOW] if malformed else unset)]
    checks = [{"id": ident, "passed": passed, "origin": origin, "plain": plain, "detail": detail}
              for ident, passed, origin, plain, detail in results]
    failing = [c for c in checks if not c["passed"]]
    whole = definition if isinstance(definition, dict) else {}
    states, budget = whole.get("states"), whole.get("budget")
    return {"flow": whole["name"] if isinstance(whole.get("name"), str) else None,
            "steps": len(states) if isinstance(states, dict) else None,
            "stop_at": whole["stop_at"] if isinstance(whole.get("stop_at"), str) else None,
            "budget": {unit: budget[unit] for unit in UNITS} if _budget_holds(budget) else None,
            "level": {"reached": 0, "name": "None", "next": 1} if failing else {"reached": 1, "name": "Mapped", "next": 2},
            "checks": checks,
            "next_step": "Fix this first: " + failing[0]["detail"][0] if failing else NOTHING_MORE}


def _flow_line(state: dict[str, Any]) -> str:
    parts = [state["flow"] or "it has no readable name"]
    if state["steps"] is not None:
        parts.append(f"{state['steps']} steps")
    parts.append(f"stops at {state['stop_at']}" if state["stop_at"] else "no stop point")
    budget = state["budget"]
    parts.append(f"up to {_show(budget['dollars'])} dollars and {_show(budget['minutes'])} minutes for one ticket"
                 if budget else "no budget for one ticket")
    return "This flow: " + ", ".join(parts) + "."


def render_map(state: dict[str, Any]) -> str:
    """The short map, in plain words: the ladder with "you are here", the flow in one line, what the
    next level needs, the next step."""
    reached = state["level"]["reached"]
    lines = ["Where this flow stands, level by level:"]
    for number, name, plain in LADDER:
        if number == 0 and reached > 0:
            continue
        mark = "✓" if 0 < number <= reached else "·"
        here = "   ← you are here" if number == reached else ""
        lines.append(f"{mark} {number} {name.ljust(12)}{plain}{here}")
    lines += ["", _flow_line(state)]
    if reached == 0:
        lines.append("What level 1 still needs:")
        for check_ in state["checks"]:
            if not check_["passed"]:
                lines.append(f"- {check_['plain']}")
                lines.extend(f"  {sentence}" for sentence in check_["detail"])
    else:
        lines.append("Levels 2 to 4 are read from real runs. Nothing measures them yet.")
    lines.append(f"Next step: {state['next_step']}")
    return "\n".join(lines) + "\n"


def render_status(state: dict[str, Any]) -> str:
    level = state["level"]
    lines = [f"This flow is at level {level['reached']} ({level['name']})."]
    lines += [f"{'✓' if c['passed'] else '✗'} {c['plain']} (read by {c['origin']})" for c in state["checks"]]
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------- the command line

def build_parser(parser: argparse.ArgumentParser | None = None) -> argparse.ArgumentParser:
    p = parser or argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="flow_command", required=True)
    new_ = sub.add_parser("new", help="writes a starting definition from a template")
    new_.add_argument("kind", choices=TEMPLATES, help="the kind of ticket the flow is for")
    new_.add_argument("--out", metavar="FILE", help="where to write it (default: .harness/flow/<kind>.json)")
    new_.add_argument("--force", action="store_true", help="replaces the file if it exists")
    chk = sub.add_parser("check", help="refuses a flow that could loop, wait or spend without end")
    nxt = sub.add_parser("next", help="what one run does on one event")
    plc = sub.add_parser("place", help="where each step belongs, and whether one needs an engine")
    sts = sub.add_parser("status", help="the level this flow has reached, on paper")
    for sp in (chk, nxt, plc, sts):
        sp.add_argument("file", help="the flow definition, a JSON file")
    nxt.add_argument("--event", required=True, metavar="FILE", help="the event, a JSON file")
    nxt.add_argument("--run", metavar="FILE", help="the run returned by the call before")
    nxt.add_argument("--new", action="store_true", help="the first event of a ticket: the run starts here")
    sts.add_argument("--map", action="store_true", help="prints the short plain-words map of the levels")
    for sp in (new_, chk, nxt, plc, sts):
        sp.add_argument("--format", choices=["md", "json"], default="md")
    return p


def _emit(fmt: str, data: Any, markdown: str) -> None:
    if fmt == "json":
        json.dump(data, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
    else:
        sys.stdout.write(markdown)


def _steps_md(definition: dict[str, Any]) -> str:
    return "".join(f"- {name} ({TYPE_WORDS.get(state['type'], state['type'])}): {state['does']}\n"
                   for name, state in definition["states"].items())


def _new_command(args: argparse.Namespace) -> int:
    path = args.out or os.path.join(".harness", "flow", f"{args.kind}.json")
    if os.path.exists(path) and not args.force:
        print(f"flow: {path} already exists and was left as it is. Add --force to replace it.", file=sys.stderr)
        return 1
    definition = new(args.kind)
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(definition, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    _emit(args.format, {"file": path, "definition": definition}, f"Written: {path}\n" + _steps_md(definition))
    return 0


def _emit_check(fmt: str, path: str, definition: Any, problems: list[dict[str, str]]) -> None:
    if problems:
        markdown = "".join(f"- {p['message']}" + (f" ({p['where']})\n" if p["where"] else "\n") for p in problems)
    else:
        budget = definition["budget"]
        markdown = (f"This flow holds: {len(definition['states'])} steps, it stops at {definition['stop_at']}, "
                    f"one ticket may cost up to {_show(budget['dollars'])} dollars and "
                    f"{_show(budget['minutes'])} minutes.\n")
    _emit(fmt, {"file": path, "passed": not problems, "problems": problems}, markdown)


def _next_md(answer: dict[str, Any]) -> str:
    run, left = answer["run"], answer["remaining"]
    if left is None:
        return answer["message"] + "\n"
    return (f"{answer['message']}\nState: {run['state']}. Spent: {_show(run['spent']['dollars'])} dollars, "
            f"{_show(run['spent']['minutes'])} minutes. Left: {_show(left['dollars'])} dollars, "
            f"{_show(left['minutes'])} minutes.\n")


def _next_command(args: argparse.Namespace, definition: Any) -> int:
    if bool(args.run) == bool(args.new):
        raise ValueError("give exactly one of --run FILE (the run returned by the call before) and --new "
                         "(the first event of a ticket)")
    event = load_definition(args.event)
    given = load_definition(args.run) if args.run else None
    problems = check(definition)
    if problems:
        _emit_check(args.format, args.file, definition, problems)
        return 2
    answer = next_state(definition, new_run(definition) if args.new else given, event)
    _emit(args.format, answer, _next_md(answer))
    return 1 if answer["outcome"] in ("refused", "stopped") else 0


def main(argv: list[str] | None = None, args: argparse.Namespace | None = None) -> int:
    if args is None:
        args = build_parser().parse_args(argv)
    try:
        if args.flow_command == "new":
            return _new_command(args)
        if args.flow_command == "place":
            return _placement_module().main([args.file, "--format", args.format])
        definition = load_definition(args.file)
        if args.flow_command == "next":
            return _next_command(args, definition)
        if args.flow_command == "check":
            problems = check(definition)
            _emit_check(args.format, args.file, definition, problems)
            return 1 if problems else 0
        state = status(definition)
        _emit(args.format, state, render_map(state) if args.map else render_status(state))
        return 0
    except ModuleNotFoundError as exc:
        if not (exc.name or "").endswith("flow_place"):
            raise
        print("flow: the placement of steps (flow_place.py) is not installed with this version", file=sys.stderr)
        return 2
    except (ValueError, OSError) as exc:
        print(f"flow: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
