"""`flow status`: where a flow stands on the ladder, measured from the definition file alone.

This version measures level 1, Mapped: the definition passes `flow check`, every step has a
place, a stop point and a budget are set. Levels 2 to 4 are read from real runs, which nothing
does yet. The contract is docs/workflow-harness/flow-spec.md, section 7."""
from __future__ import annotations

from typing import Any

from . import flow_fit, flow_paths
from .flow import UNITS, _budget_holds, _is_text, _placement_module, _show, check

NOT_A_FLOW = "the file cannot be read as a flow"
NOT_LOOKED_AT = "not looked at, the file must first pass flow check"
LEVELS = 4
LADDER = ((0, "None", "the phases are chained by hand"),
          (1, "Mapped", "the flow is written down and every step has a place"),
          (2, "Shadow", "the flow runs on real tickets and only comments"),
          (3, "Drafting", "runs end with a draft PR; CI and review results come back to the run"),
          (4, "Delivering", "runs reach a reviewed PR and merge only on a human's word"))
NOTHING_MORE = ("Nothing more on paper. The next level needs the flow to run on real tickets, "
                "which this version does not do yet.")


def _placement_detail(placement: Any, states: Any = None, kept: dict[str, Any] | None = None) -> list[str]:
    """One sentence per step that has no place yet and per gate nobody can judge, the line `flow
    place` prints for it (`kept`: the gates the flow cannot lose, each with its `flow_paths.gate_keeps` entry)."""
    if not isinstance(placement, dict):
        return ["the steps could not be placed"]
    out, told = [], set()
    steps = placement.get("steps")
    for step in (steps if isinstance(steps, list) else []):
        missing = step.get("missing") if isinstance(step, dict) else None
        if isinstance(missing, dict) and step.get("status") == "open":
            told.add(step.get("state"))
            fix = f" {step['fix']}" if _is_text(step.get("fix")) else ""
            out.append(f"The step {step.get('state')} has no answer to \"{missing.get('text')}\" "
                       f"(key {missing.get('key')}).{fix}")
    for name in placement.get("open") or []:
        if name not in told:
            out.append(f"The step {name} cannot be placed yet.")
    for name in placement.get("refused_gates") or []:
        gate = states.get(name) if isinstance(states, dict) and isinstance(name, str) else None
        judge = gate.get("judge") if isinstance(gate, dict) and _is_text(gate.get("judge")) else "its judge"
        out.append(flow_paths.refused_gate_line(name, judge, (kept or {}).get(name)))
    return out or ["a step has no place"]


def _kept(definition: Any, placement: Any) -> dict[str, Any]:
    """The refused gates a flow that holds cannot lose (section 12.2)."""
    refused = placement.get("refused_gates") if isinstance(placement, dict) else None
    return flow_paths.gate_marks(definition, refused) if isinstance(refused, list) and refused else {}


def _waiting(definition: Any, malformed: bool) -> list[str]:
    """The gates that wait for their judge. A file that is not a flow is never placed, so the
    placement module is not required to read it."""
    try:
        return _placement_module().waiting(definition)
    except ImportError:
        if malformed:
            return []
        raise


def _ask(definition: dict, state: str) -> str:
    """The next step when the first thing missing is a judge's answer (section 12.1)."""
    gate = definition["states"][state]
    judge = gate["judge"] if _is_text(gate.get("judge")) else "its judge"
    shows = gate["shows"] if _is_text(gate.get("shows")) else "what they are shown"
    return (f'Ask {judge} whether they can really read {shows} and refuse it, then write "can_judge": "yes" or '
            f'"no" in the step {state}.')


def _next_step(definition: Any, problems: list, placement: Any, waiting: list[str], failing: list) -> str:
    if not failing:
        return NOTHING_MORE
    opened = placement.get("open") if isinstance(placement, dict) else None
    if not problems and opened and opened[0] in waiting:
        return _ask(definition, opened[0])
    return "Fix this first: " + failing[0]["detail"][0]


def status(definition: Any, placement: Any = None, measured: Any = None) -> dict[str, Any]:
    """Where a flow stands on the ladder. This version measures level 1, Mapped, from the file alone.
    `measured`, what `flow_fit.measured` read of the team's answers, is carried and changes no level."""
    problems = check(definition)
    malformed = any(p["code"] == "malformed" for p in problems)
    if placement is None and not malformed:
        placement = _placement_module().place(definition, measured)
    waiting = _waiting(definition, malformed)
    unset = [p["message"] for p in problems if p["code"] in ("no_stop_point", "no_budget")]
    placed = isinstance(placement, dict) and placement.get("passed") is True
    results = [("definition_holds", not problems, "flow check", "the flow is written down and holds together",
                [p["message"] for p in problems]),
               ("steps_placed", placed and not malformed, "flow place", "every step has a place",
                [NOT_A_FLOW] if malformed else [] if placed
                else _placement_detail(placement, definition.get("states") if isinstance(definition, dict) else None,
                                       _kept(definition, placement))),
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
            "next_step": _next_step(definition, problems, placement, waiting, failing),
            "waiting": waiting, "bounds": flow_paths.bounds(definition), "measured": measured}


def _from_runs(state: dict[str, Any]) -> list[str]:
    """The line on what the team measured on its own runs, when answers were given (section 12.5)."""
    found = state.get("measured")
    return [f"From your own runs: {flow_fit.said_of_runs(found)}"] if found else []


def _flow_line(state: dict[str, Any]) -> str:
    parts = [state["flow"] or "it has no readable name"]
    if state["steps"] is not None:
        parts.append(f"{state['steps']} steps")
    parts.append(f"stops at {state['stop_at']}" if state["stop_at"] else "no stop point")
    budget = state["budget"]
    parts.append(f"up to {_show(budget['dollars'])} dollars and {_show(budget['minutes'])} minutes for one ticket"
                 if budget else "no budget for one ticket")
    return "This flow: " + ", ".join(parts) + "."


def _not_looked_at(state: dict[str, Any], check_: dict[str, Any]) -> bool:
    """True for a check that was not made because `flow check` refused a file whose steps can be
    read: saying it failed would call false something nobody looked at."""
    return check_["detail"] == [NOT_A_FLOW] and state["steps"] is not None


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
    if state.get("bounds"):
        lines += flow_paths.render_bounds(state["bounds"]).splitlines()
    lines += _from_runs(state)
    if reached == 0:
        lines.append("What level 1 still needs:")
        for check_ in state["checks"]:
            if not check_["passed"]:
                lines.append(f"- {check_['plain']}")
                detail = [NOT_LOOKED_AT] if _not_looked_at(state, check_) else check_["detail"]
                lines.extend(f"  {sentence}" for sentence in detail)
    else:
        lines.append("Levels 2 to 4 are read from real runs. Nothing measures them yet.")
    lines.append(f"Next step: {state['next_step']}")
    return "\n".join(lines) + "\n"


def render_status(state: dict[str, Any]) -> str:
    level = state["level"]
    lines = [f"This flow is at level {level['reached']} of {LEVELS} ({level['name']})."]
    for check_ in state["checks"]:
        if _not_looked_at(state, check_):
            lines.append(f"– {check_['plain']}: {NOT_LOOKED_AT}")
        else:
            lines.append(f"{'✓' if check_['passed'] else '✗'} {check_['plain']} (read by {check_['origin']})")
    return "\n".join(lines + _from_runs(state)) + "\n"
