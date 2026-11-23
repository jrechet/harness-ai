"""The paths of a flow: what `flow check` reads on the whole graph of transitions, beyond one step.

Two things, both from section 12.2 of docs/workflow-harness/flow-spec.md:
- `unguarded`: a write that cannot be taken back (a stop point listed under `irreversible`, by
  default `merged` and `deployed`) that a run can make without crossing a gate that guards it. A
  gate is crossed when a run leaves it by an answer, never by `deadline_passed`: silence is not a
  decision. A gate guards a stop point only if one of its answers can keep the run from every write
  of it; a person's own merge or deploy (a `human` step left by any event but `deadline_passed`, reaching
  an irreversible stop point or one of the default names) guards the writes after it.
- `bounds`: the figures that bound one run, printed for a person to read. No threshold is applied.

Nothing here prints; `flow_cli` does. The whole graph is read, the steps behind the stop point too:
moving `stop_at` must never be the edit that removes the last gate."""
from __future__ import annotations

from typing import Any

from .flow import ENDED, UNITS, _is_name, _live, _malformed, _problem, _show, _step_type, _stops_here, check

DEFAULT_IRREVERSIBLE = ("merged", "deployed")
SILENCE = "deadline_passed"
WAY_OUT = ('Add a step of type "gate" on that path, with an answer that stops the run; or, if a person does this '
           "outside the flow and the step {state} only waits for it, that step is a person's decision: give it the "
           'type "gate", with its judge and what they are shown; or, if your team can take "{stop}" back, write '
           '"irreversible": [<the stop points it cannot take back>] at the top of the file.')


# ---------------------------------------------------------------- the key `irreversible`

def stop_points(states: Any) -> list[str]:
    """Every name a transition reaches, in file order, once each, whatever its target: a step that
    stops the run after making its write still made it. Reads what it can of a broken file."""
    found: list[str] = []
    for state in (states.values() if isinstance(states, dict) else ()):
        on = state.get("on") if isinstance(state, dict) else None
        for transition in (on.values() if isinstance(on, dict) else ()):
            name = transition.get("reaches") if isinstance(transition, dict) else None
            if _is_name(name) and name not in found:
                found.append(name)
    return found


def malformed_irreversible(definition: dict) -> list[dict[str, str]]:
    """The `malformed` problem of the key `irreversible`: not a list of names, or a name no
    transition reaches, so that a slip of the pen never switches the rule off in silence."""
    if "irreversible" not in definition:
        return []
    value = definition["irreversible"]
    if not (isinstance(value, list) and all(_is_name(name) for name in value)):
        return [_malformed("irreversible", 'irreversible must be a list of stop point names, for example '
                                           '["merged", "deployed"], or [] when nothing is irreversible')]
    reached = stop_points(definition.get("states"))
    unknown = [name for index, name in enumerate(value) if name not in reached and name not in value[:index]]
    if not unknown:
        return []
    named = " and ".join(f'"{name}"' for name in unknown)
    choices = ", ".join(reached) or 'none yet, since no transition has a "reaches"'
    return [_malformed("irreversible", f"irreversible names {named}, which no transition reaches. Write one of the "
                                       f"stop points of this file, or remove the name: {choices}")]


def irreversible(definition: dict) -> list[str]:
    """The stop points whose write cannot be taken back, as the file says or by default, each once."""
    return list(dict.fromkeys(definition.get("irreversible", DEFAULT_IRREVERSIBLE)))


def _targets(definition: dict) -> list[tuple[str, str, str]]:
    """(state, event, stop point) of each transition that reaches an irreversible stop point, in file order."""
    names = irreversible(definition)
    return [(state, event, transition["reaches"]) for state, step in definition["states"].items()
            for event, transition in step["on"].items() if transition.get("reaches") in names]


# ---------------------------------------------------------------- the graph, read with the gates that guard
#
# `guards` holds the names of the gates that guard a stop point, and, as (state, event) pairs, the
# transitions by which a person's own step makes a write that cannot be taken back (rule 1): that
# person decided the write, so the transitions after it are guarded as by a gate.

def _crosses(guards: set, state: str, event: str) -> bool:
    """A run crosses a gate that guards when it leaves it by an answer: silence is not a decision.
    It crosses a person's write by the transition that makes it."""
    return (state in guards and event != SILENCE) or (state, event) in guards


def _free_from(states: dict, guards: set, origin: str, avoid: frozenset = frozenset()) -> set:
    """The states a run can reach from `origin` without crossing a gate of `guards`, nor entering a state of `avoid`."""
    seen, todo = {origin}, [origin]
    while todo:
        state = todo.pop()
        for event, transition in states[state]["on"].items():
            to = transition["to"]
            if to in states and to not in seen and to not in avoid and not _crosses(guards, state, event):
                seen.add(to)
                todo.append(to)
    return seen


def _can_take(states: dict, guards: set, origin: str, target: tuple, avoid: frozenset = frozenset()) -> bool:
    """Whether a run that is at `origin` can take the transition `target` crossing no gate of `guards`,
    nor entering a state of `avoid`."""
    state, event = target[0], target[1]
    return state in _free_from(states, guards, origin, avoid) and not _crosses(guards, state, event)


def _reaching(states: dict, stop: str) -> list[tuple[str, str]]:
    """(state, event) of every transition that reaches the stop point `stop`."""
    return [(name, event) for name, state in states.items() for event, transition in state["on"].items()
            if transition.get("reaches") == stop]


def _can_take_stop(states: dict, guards: set, origin: str, stop: str) -> bool:
    """Whether a run that is at `origin` can make a write of `stop`, by any transition, crossing no gate of `guards`."""
    free = _free_from(states, guards, origin)
    return any(name in free and not _crosses(guards, name, event) for name, event in _reaching(states, stop))


def _can_refuse(states: dict, guards: set, gate: str, stop: str) -> bool:
    """One answer of the gate, silence and every answer that itself makes a write of `stop` left aside,
    ends the run or leads where no write of `stop` can be made without crossing a gate that guards it."""
    for event, transition in states[gate]["on"].items():
        if event == SILENCE or transition.get("reaches") == stop:
            continue
        to = transition["to"]
        if to in ENDED or not _can_take_stop(states, guards, to, stop):
            return True
    return False


def _person_write(state: dict, event: str) -> bool:
    """Whether (a step, one of its events) is a person deciding a write (rule 1): a `human` step left
    by any event but `deadline_passed`, which passes when nobody acted and is nobody's decision."""
    return _step_type(state) == "human" and event != SILENCE


def _person_writes(states: dict, names: list[str]) -> set:
    """The transitions by which a `human` step decides the writes after it (rule 1): those that reach
    an irreversible stop point, or `merged` or `deployed` though the team can take it back, so that
    saying a merge is less dangerous never turns a flow that holds into one refused."""
    decided = set(names) | set(DEFAULT_IRREVERSIBLE)
    return {(name, event) for name, state in states.items()
            for event, transition in state["on"].items()
            if _person_write(state, event) and transition.get("reaches") in decided}


def guarding(states: dict, stop: str, names: list[str], struck: frozenset = frozenset()) -> set:
    """What guards the writes of `stop`, found by striking: every gate at first (but those of
    `struck`, read as guarding nothing), then each that cannot refuse is struck, again, until none
    is. Two gates that cannot refuse never vouch for each other. A person's own writes are kept."""
    guards = {name for name, state in states.items() if _step_type(state) == "gate" and name not in struck}
    guards |= _person_writes(states, names)
    struck_one = True
    while struck_one:
        struck_one = False
        for gate in [name for name in states if name in guards]:
            if not _can_refuse(states, guards, gate, stop):
                guards.discard(gate)
                struck_one = True
    return guards


def shortest_path(definition: dict, goal: str, guards: set | None = None) -> list[tuple[str, str | None]]:
    """The shortest path from the start to `goal`, breadth first, states and events in file order, as
    (state, the event it is left by); the last pair is (goal, None). With `guards`, the transitions that
    cross one of them are not followed. Empty when no path leads there."""
    states, start = definition["states"], definition["start"]
    before: dict[str, tuple[str, str] | None] = {start: None}
    queue, at = [start], 0
    while at < len(queue) and goal not in before:
        state, at = queue[at], at + 1
        for event, transition in states[state]["on"].items():
            to = transition["to"]
            if to in states and to not in before and not (guards is not None and _crosses(guards, state, event)):
                before[to] = (state, event)
                queue.append(to)
    if goal not in before:
        return []
    path, step = [(goal, None)], before[goal]
    while step is not None:
        path.insert(0, step)
        step = before[step[0]]
    return path


# ---------------------------------------------------------------- the refusal

def _why(states: dict, guards: set, path: list, target: tuple) -> str:
    """One parenthesis per gate on the path: it is left in silence, or its every answer leads to the write;
    and one for a person's step that makes the write when its deadline passes."""
    out = ""
    for state, event in path:
        if _step_type(states[state]) != "gate":
            continue
        left_by = target[1] if state == target[0] else event
        onward = states[state]["on"].get(SILENCE, {}).get("to")
        silent = left_by == SILENCE or (state != target[0] and onward in states
                                        and _can_take(states, guards, onward, target))
        out += (f" (it leaves the gate {state} by deadline_passed, when nobody answered)" if silent
                else f" (every answer of the gate {state} leads to this write)")
    if _step_type(states[target[0]]) == "human":  # rule 1 leaves aside only its silence
        out += f" (it leaves the person's step {target[0]} by deadline_passed, when nobody acted)"
    return out


def unguarded(definition: dict, struck: frozenset = frozenset()) -> list[dict[str, str]]:
    """`irreversible_without_gate`: one problem per transition that reaches an irreversible stop point
    and that a run can take crossing no gate that guards it, in file order. Read on a definition that
    is not malformed; nothing is said while a step type is unknown, which is fixed first. The gates
    of `struck` are read as guarding nothing, as if they were removed."""
    states, names = definition["states"], irreversible(definition)
    if any(_step_type(state) is None for state in states.values()):
        return []
    out, found = [], {}
    for target in _targets(definition):
        state, event, stop = target
        if _person_write(states[state], event):
            continue  # a person makes the write
        guards = found.setdefault(stop, guarding(states, stop, names, struck))
        path = shortest_path(definition, state, guards) if _can_take(states, guards, definition["start"], target) else []
        if not path:
            continue
        shown = " → ".join(name for name, _ in path)
        out.append(_problem("irreversible_without_gate", f"states.{state}.on.{event}",
                            f'The event {event} of the step {state} reaches "{stop}", which cannot be taken back, '
                            f"and the path {shown} crosses no gate that guards it"
                            f"{_why(states, guards, path, target)}. " + WAY_OUT.format(state=state, stop=stop)))
    return out


def removal_unread(definition: Any) -> bool:
    """Whether a fault hides the paths, so that no gate may be offered for removal: the file is
    `malformed`, or a step type is unknown and `unguarded` says nothing yet."""
    return any(problem["code"] in ("malformed", "unknown_step_type") for problem in check(definition))


def _run_order(definition: dict, gates: list[str]) -> list[str]:
    """`gates` in the order a run meets them: by the length of the shortest path from the start,
    file order between equals, the ones no run reaches last (a name that is no state of the file
    after them, in the order given). Never the order of the file alone."""
    states, start = definition["states"], definition["start"]
    far, queue = {start: 0}, [start]
    for state in queue:
        for transition in states[state]["on"].values():
            if transition["to"] in states and transition["to"] not in far:
                far[transition["to"]] = far[state] + 1
                queue.append(transition["to"])
    written = {name: index for index, name in enumerate(states)}
    return sorted(gates, key=lambda gate: (far.get(gate, len(written)), written.get(gate, len(written))))


def _opened(definition: dict, struck: frozenset) -> list[str]:
    """The `where` of each write that the gates of `struck`, read as guarding nothing, open a new way to:
    a run can reach, from the start, a state from which, crossing no gate that still guards, it takes
    that write without entering the path the file as written already leaves open to it. That path
    (the states a run reaches from the start and can take the write from, the write's own step left
    aside) is set apart, so that a bypass refused already never hides the gate nearest the write; with
    no such path, this is `unguarded` refusing a write it did not refuse. File order."""
    states, names, start = definition["states"], irreversible(definition), definition["start"]
    if any(_step_type(state) is None for state in states.values()):
        return []
    out, found = [], {}
    for target in _targets(definition):
        state, event, stop = target
        if _person_write(states[state], event):
            continue
        was, now = found.setdefault(stop, (guarding(states, stop, names), guarding(states, stop, names, struck)))
        open_before = {name for name in _free_from(states, was, start) if _can_take(states, was, name, target)}
        avoid = frozenset(open_before - {state})
        if any(_can_take(states, now, name, target, avoid) for name in _free_from(states, now, start) - open_before):
            out.append(f"states.{state}.on.{event}")
    return out


def _offers(definition: Any, gates: list[str]) -> tuple[dict[str, list[str]], list[str], dict[str, list[str]]]:
    """The gates kept, each with the `where` of the writes it keeps; the gates offered for removal in
    the order they were read (`kept_writes`); and, for each gate kept, the gates offered before it
    without which removing it alone would refuse nothing, empty when removing it alone would."""
    if any(problem["code"] == "malformed" for problem in check(definition)):
        return {}, [], {}
    out: dict[str, list[str]] = {}
    offered: list[str] = []
    together: dict[str, list[str]] = {}
    for gate in _run_order(definition, gates):
        refused = _opened(definition, frozenset(offered) | {gate})
        if not refused:
            offered.append(gate)
            continue
        out[gate] = refused
        together[gate] = [] if _opened(definition, frozenset({gate})) else list(offered)
    return out, offered, together


def kept_writes(definition: Any, gates: list[str]) -> dict[str, list[str]]:
    """Of `gates`, those a flow cannot lose, each with the `where` of the writes it keeps, in file order.
    The gates are read in the order a run meets them (`_run_order`), each struck together with the
    earlier ones offered for removal: it is kept when that opens a new way to a write (`_opened`). So
    following every offer together never removes the last gate before a write, and the gate kept is
    the one nearest the write, whatever the order of the file and whatever bypass the file already
    has. Read whenever the file is not malformed, its other problems left aside; empty for a malformed one."""
    return _offers(definition, gates)[0]


def struck_with(definition: Any, gates: list[str], gate: str) -> frozenset:
    """The gates removed when `gate` is, as `kept_writes` reads it: those offered before it, and itself."""
    offered = _offers(definition, gates)[1]
    return frozenset(offered[:offered.index(gate) + 1]) if gate in offered else frozenset({gate})


def gate_keeps(definition: Any, gates: list[str]) -> dict[str, dict[str, Any]]:
    """Of `gates`, those a flow cannot lose (`kept_writes`), each with what its line says: `stop`, a stop
    point it keeps, one it is the last gate before on the bounds' shortest path when there is one;
    `last`, whether it is; `where`, that write; `with`, the gates offered before it that must go with it
    for flow check to refuse the file, empty when removing it alone is refused."""
    kept, _, together = _offers(definition, gates)
    if not kept:
        return {}
    targets = {f"states.{state}.on.{event}": (state, event, stop) for state, event, stop in _targets(definition)}
    out = {}
    for gate, wheres in kept.items():
        last = [where for where in wheres if guard_of(definition, targets[where])["last_gate"] == gate]
        where = (last or wheres)[0]
        out[gate] = {"stop": targets[where][2], "last": bool(last), "where": where, "with": together[gate]}
    return out


def kept_gates(definition: Any, gates: list[str]) -> dict[str, str]:
    """Of `gates`, those a flow cannot lose (`kept_writes`), each with the stop point its line names (`gate_keeps`)."""
    return {gate: keep["stop"] for gate, keep in gate_keeps(definition, gates).items()}


UNREAD = ""  # in a `gate_marks` answer: whether the flow can lose that gate is not read yet


def gate_marks(definition: Any, gates: list[str]) -> dict[str, Any]:
    """What the line of each refused gate says (`refused_gate_line`): `gate_keeps`, or every gate
    marked `UNREAD` while a fault hides the paths (`removal_unread`)."""
    if not gates:
        return {}
    if removal_unread(definition):
        return {gate: UNREAD for gate in gates}
    return gate_keeps(definition, gates)


def together_with(gates: list[str]) -> str:
    """What follows "do not remove it" when a kept gate may go alone (section 12.2), empty otherwise."""
    return f" together with {', '.join(gates)}" if gates else ""


def refused_gate_line(gate: str, judge: str | None, kept: Any = None) -> str:
    """The line `flow place` prints for a gate nobody can judge, which `flow status` gives as its
    detail. When the flow cannot lose that gate (`kept`, a `gate_keeps` entry, or the stop point it is
    the last gate before), removing it is never offered, nor while a fault hides the paths (`kept` is
    `UNREAD`)."""
    judge = judge or "its judge"
    if kept == UNREAD:
        return (f"A gate nobody can judge: {gate}. Give {judge} something they can read and refuse. Whether the "
                "flow can do without it is said once flow check finds no fault that hides its paths.")
    if kept is None:
        return f"A gate nobody can judge: {gate}. Remove it, or give {judge} something they can read and refuse."
    keep = kept if isinstance(kept, dict) else {"stop": kept, "last": True, "with": []}
    said = (f'It is the last gate before "{keep["stop"]}", which cannot be taken back' if keep["last"]
            else f'Without it, a run could reach "{keep["stop"]}", which cannot be taken back, crossing no gate '
                 "that guards it")
    return (f"A gate nobody can judge: {gate}. {said}: do not remove it{together_with(keep['with'])}; give {judge} "
            "something they can read and refuse.")


# ---------------------------------------------------------------- the bounds of one run

def _circles(definition: dict) -> list[dict[str, Any]]:
    """The groups of states a run can enter that reach each other, the stop point cutting the graph,
    the capped states kept; a state alone only with a transition to itself."""
    states, live = definition["states"], _live(definition)
    order = [name for name in states if name in live]
    edges = {name: [t["to"] for t in states[name]["on"].values() if t["to"] in live and not _stops_here(definition, t)]
             for name in order}
    reach = {}
    for name in order:
        seen, todo = set(), list(edges[name])
        while todo:
            other = todo.pop()
            if other not in seen:
                seen.add(other)
                todo.extend(edges[other])
        reach[name] = seen
    out, grouped = [], set()
    for name in order:
        if name in grouped or name not in reach[name]:
            continue
        group = [other for other in order if other in reach[name] and name in reach[other]]
        grouped.update(group)
        caps = {other: states[other]["cap"] for other in group if "cap" in states[other]}
        out.append({"steps": group, "caps": caps, "most_entries": sum(caps.values())})
    return out


def _judge_answer(gate: dict) -> str | None:
    """The `can_judge` of a gate as the bounds give it: "yes" or "no", null when the key is absent
    (the gate waits for its judge), "unreadable" for any other value."""
    if "can_judge" not in gate:
        return None
    return gate["can_judge"] if gate["can_judge"] in ("yes", "no") else "unreadable"


def guard_of(definition: dict, target: tuple, struck: frozenset = frozenset()) -> dict[str, Any]:
    """How far the last gate that guards a write stands from it, on the shortest path to its step. The
    gates of `struck` are read as guarding nothing and are not counted among the steps between."""
    states = definition["states"]
    state, event, stop = target
    entry = {"stop_point": stop, "state": state, "event": event, "last_gate": None, "shows": None, "can_judge": None,
             "steps_between": None, "agents_between": None}
    if _person_write(states[state], event):
        return entry
    guards = guarding(states, stop, irreversible(definition), struck)
    path = shortest_path(definition, state)
    if _crosses(guards, state, event):
        gate, between = state, []
    else:
        crossed = [index for index, (name, left_by) in enumerate(path[:-1]) if _crosses(guards, name, left_by)]
        if not crossed:
            return entry
        gate = path[crossed[-1]][0]
        between = [name for name, _ in path[crossed[-1] + 1:-1] if name not in struck]
    agents = sum(_step_type(states[name]) == "agent" for name in between)
    if _step_type(states[gate]) == "human":  # a person's own write: no judge, nothing shown
        return {**entry, "last_gate": gate, "steps_between": len(between), "agents_between": agents}
    return {**entry, "last_gate": gate, "shows": states[gate].get("shows"), "can_judge": _judge_answer(states[gate]),
            "steps_between": len(between), "agents_between": agents}


def bounds(definition: Any) -> dict[str, Any] | None:
    """The figures that bound one run of a flow that passes `flow check`; None otherwise."""
    if check(definition):
        return None
    names = irreversible(definition)
    return {"budget": {unit: definition["budget"][unit] for unit in UNITS}, "irreversible": names,
            "irreversible_declared": "irreversible" in definition,
            "taken_back": [name for name in stop_points(definition["states"]) if name not in names],
            "circles": _circles(definition),
            "guards": [guard_of(definition, target) for target in _targets(definition)]}


# ---------------------------------------------------------------- what a person reads

def _circle_line(circle: dict[str, Any]) -> str:
    caps = circle["caps"]
    named = ", ".join(f"{state} {_show(cap)}" for state, cap in caps.items())
    times = "1 time" if circle["most_entries"] == 1 else f"{_show(circle['most_entries'])} times"
    return (f"- The circle {', '.join(circle['steps'])}: its capped steps can be entered {times} in all at most "
            f"({'cap' if len(caps) == 1 else 'caps'} of {named}).")


def _irreversible_line(found: dict[str, Any]) -> str:
    if not found["irreversible"]:
        return '- Cannot be taken back: nothing, the file says so ("irreversible": []): no write is checked for a gate.'
    said = ('the file says so under "irreversible"' if found["irreversible_declared"]
            else 'the default: the file has no "irreversible"')
    return f"- Cannot be taken back: {', '.join(found['irreversible'])} ({said})."


def _answer_sentence(guard: dict[str, Any]) -> str:
    """What a line that names a gate says of its judge's answer, when it is not "yes"."""
    if guard["can_judge"] is None:
        return " That gate still waits for its judge's answer."
    if guard["can_judge"] == "unreadable":
        return ' The file\'s answer for that gate cannot be read: write "can_judge": "yes" or "no".'
    return ""


def _between(guard: dict[str, Any], gate: str) -> str:
    return (f"Steps between {gate} and {guard['state']}: {guard['steps_between']}; agents among them: "
            f"{guard['agents_between']}.")


def _guard_line(guard: dict[str, Any]) -> str:
    gate, state = guard["last_gate"], guard["state"]
    head = f'- The event {guard["event"]} of {state} reaches "{guard["stop_point"]}".'
    if gate is None:
        return f"{head} {state} is a person's step (type \"human\"): no gate is asked."
    if guard["shows"] is None:  # a gate of a flow that holds always shows something: this is a person's write
        return (f"{head} Every path to it crosses a gate that guards it or a write a person makes. On the shortest "
                f"path the last one is {gate}, a person's step (type \"human\") whose write is that person's "
                "decision. "
                + _between(guard, gate))
    shows = f'"{guard["shows"]}"'
    nobody = ', and the file says nobody can judge it ("can_judge": "no"): flow place refuses it'
    if gate == state and guard["can_judge"] == "no":
        return f"{head} {state} is a gate, shown {shows}{nobody}."
    if gate == state:
        return f"{head} {state} is a gate: its judge, shown {shows}, decides it.{_answer_sentence(guard)}"
    if guard["can_judge"] == "no":
        return (f"{head} Every path to it crosses a gate flow check counts. On the shortest path the last one is "
                f"{gate}, whose judge is shown {shows}{nobody}. " + _between(guard, gate))
    return (f"{head} Every path to it crosses a gate that guards it. On the shortest path the last one is {gate}, "
            f"whose judge is shown {shows}. {_between(guard, gate)}{_answer_sentence(guard)}")


def render_bounds(found: dict[str, Any]) -> str:
    """The block `flow check` and `flow status --map` print, from a `bounds` document."""
    budget = found["budget"]
    lines = ["What bounds one run (figures for you to read: no threshold is applied to them):",
             f"- Spending: a run is stopped at the first event that takes it past {_show(budget['dollars'])} dollars "
             f"or {_show(budget['minutes'])} minutes. It can pass them by the cost of one step, which the file does "
             "not bound."]
    lines += [_circle_line(circle) for circle in found["circles"]] or ["- No circle: no step can be entered twice."]
    lines.append(_irreversible_line(found))
    if found["taken_back"]:
        lines.append(f"- The file treats as possible to take back: {', '.join(found['taken_back'])}.")
    reached = {guard["stop_point"] for guard in found["guards"]}
    lines += [f'- No transition of this file reaches "{name}": if a step of yours does that write under another '
              'name, flow check does not know it; write that name under "irreversible".'
              for name in found["irreversible"] if name not in reached]
    lines += [_guard_line(guard) for guard in found["guards"]]
    return "\n".join(lines) + "\n"
