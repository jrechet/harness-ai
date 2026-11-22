"""`flow place`: where each step of a team's flow goes, and which question decided.

The grid (`flow_placement.json`) has the format of `placement.json`, so `place.walk` reads it
unchanged. It adds two things: each question says which key of a step answers it (`from`), and
each destination carries the short sentence printed (`says`). The answers are computed from the
definition file, never asked: same file, same places.

  harness flow place flow.json                 one line per step, then the verdict
  harness flow place flow.json --format json   the `place` document

Needing a workflow engine is an answer, not a failure. Two things fail: a step with a missing
answer, and a gate whose judge could not judge what they approve. A step that cannot be placed
is told what to write: the key, its allowed values, and every other key it still lacks.

Exit codes: 0 every step has a place and every gate can be judged, 1 otherwise, 2 a file that is
missing, is not JSON or is not a flow."""
from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any

from . import place as grid_walk
from .flow import TYPE_WORDS, load_definition

GRID_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "flow_placement.json")
ENGINE = "durable_engine"
REFUSED_GATE = "no_gate"


def load_grid(path: str = GRID_FILE) -> dict[str, Any]:
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _text(value: Any) -> str | None:
    """A non-empty string, or nothing."""
    return value if isinstance(value, str) and value.strip() else None


def answers_of(grid: dict[str, Any], step: dict[str, Any]) -> dict[str, str]:
    """What the step answers to each question, read from its keys. A value the question's map
    does not hold is no answer."""
    answers = {}
    for qid, question in grid["questions"].items():
        value = step.get(question["from"]["key"])
        if isinstance(value, str) and value in question["from"]["map"]:
            answers[qid] = question["from"]["map"][value]
    return answers


def _values(question: dict[str, Any]) -> str:
    """The values a step may give to a question, as a person writes them: "yes" or "no"."""
    quoted = [json.dumps(value) for value in question["from"]["map"]]
    return quoted[0] if len(quoted) == 1 else f"{', '.join(quoted[:-1])} or {quoted[-1]}"


def fix_of(grid: dict[str, Any], step: dict[str, Any]) -> str | None:
    """What to write in a step that cannot be placed: the key the walk stopped on, with its
    allowed values, then every other key the walk would ask for if it went on. None once placed."""
    answers, lacking, qid = answers_of(grid, step), [], grid["root"]
    while qid is not None:
        question = grid["questions"][qid]
        option = answers.get(qid)
        if option is None:
            lacking.append(question)
            # Without an answer, go on as if the step had given the one that leads to the next
            # question. Nothing can be supposed of a step whose type is unknown.
            onward = [o for o, target in question["options"].items() if "ask" in target]
            option = onward[0] if onward and question["from"]["key"] != "type" else None
        qid = question["options"][option].get("ask") if option is not None else None
    if not lacking:
        return None
    first, key = lacking[0], lacking[0]["from"]["key"]
    said = (f'"{key}" is {json.dumps(step[key], ensure_ascii=False)}: write {_values(first)}.' if key in step
            else f'Add "{key}": {_values(first)}.')
    others = [f'"{q["from"]["key"]}" ({_values(q)})' for q in lacking[1:]]
    return said + (f" Also needed: {', '.join(others)}." if others else "")


def place_step(grid: dict[str, Any], state: str, step: dict[str, Any]) -> dict[str, Any]:
    """One step: its place and the question that decided, or the question left without an answer."""
    walked = grid_walk.walk(grid, answers_of(grid, step))
    entry = {"state": state, "type": step.get("type"), "does": _text(step.get("does")),
             "shows": _text(step.get("shows")), "status": "open", "destination": None, "name": None,
             "says": None, "path": walked["path"], "decided_by": None, "reason": None, "missing": None}
    if walked["status"] != "placed":
        qid = walked["next"]["id"]
        question = grid["questions"][qid]
        return {**entry, "missing": {"question": qid, "text": question["text"], "key": question["from"]["key"]},
                "fix": fix_of(grid, step)}
    destination, last = walked["destination"], walked["path"][-1]
    return {**entry, "status": "placed", "destination": destination["id"], "name": destination["name"],
            "says": destination["says"], "reason": destination["why"],
            "decided_by": {"question": last["question"], "text": grid["questions"][last["question"]]["text"],
                           "answer": last["answer"]}}


def _missing_words(entry: dict[str, Any]) -> str:
    return f'no answer to "{entry["missing"]["text"]}" (key {entry["missing"]["key"]})'


def _without_full_stop(does: str | None) -> str:
    """The step's sentence, ready to sit inside another one."""
    return (does or "no description").rstrip().rstrip(".")


def _verdict(steps: list[dict[str, Any]]) -> dict[str, str]:
    waiting = [s for s in steps if s["status"] == "open"]
    engine = [s for s in steps if s["destination"] == ENGINE]
    if waiting:
        count = "1 step" if len(waiting) == 1 else f"{len(waiting)} steps"
        detail = "; ".join(f"{s['state']} has {_missing_words(s)}" for s in waiting)
        return {"code": "open", "sentence": f"{count} cannot be placed yet: {detail}."}
    if engine:
        count = "One step" if len(engine) == 1 else f"{len(engine)} steps"
        detail = "; ".join(f"{s['state']}, {_without_full_stop(s['does'])}" for s in engine)
        return {"code": "engine", "sentence": f"{count} would need an engine: {detail}. {engine[0]['reason']}"}
    return {"code": "no_engine", "sentence": "No step needs an engine."}


def place(definition: Any) -> dict[str, Any]:
    """The `place` document of a flow definition. It places what it finds: whether the flow
    holds together is `flow check`'s question, not this one."""
    if not isinstance(definition, dict):
        raise ValueError("the file is not a flow: expected an object with its steps under states")
    states = definition.get("states")
    if not isinstance(states, dict) or not all(isinstance(step, dict) for step in states.values()):
        raise ValueError("the file is not a flow: states must be an object that gives each step as an object")
    grid = load_grid()
    steps = [place_step(grid, str(state), step) for state, step in states.items()]
    refused = [s["state"] for s in steps if s["destination"] == REFUSED_GATE]
    waiting = [s["state"] for s in steps if s["status"] == "open"]
    return {"flow": _text(definition.get("name")), "steps": steps,
            "engine": [s["state"] for s in steps if s["destination"] == ENGINE],
            "refused_gates": refused, "open": waiting, "verdict": _verdict(steps),
            "passed": not waiting and not refused}


# --- Rendering -------------------------------------------------------------------------------------

def _step_line(entry: dict[str, Any], judge: str | None) -> str:
    kind = entry["type"]
    who = TYPE_WORDS.get(kind, kind) if isinstance(kind, str) else json.dumps(kind)
    head = f"- {entry['state']} ({who}): "
    if entry["status"] == "open":
        fix = f"\n  {entry['fix']}" if entry.get("fix") else ""
        return f"{head}cannot be placed yet. N{_missing_words(entry)[1:]}.{fix}"
    decided = entry["decided_by"]
    line = f'{head}{entry["says"]}. Decided by "{decided["text"]}": {decided["answer"]}.'
    if kind == "gate" and entry["shows"]:
        line += f" Shown to {judge or 'its judge'}: {entry['shows']}."
    return line


def render_md(result: dict[str, Any], judges: dict[str, str | None]) -> str:
    """What a person reads: one line per step, the verdict, then the gates nobody can judge."""
    lines = [_step_line(entry, judges.get(entry["state"])) for entry in result["steps"]]
    sentence = result["verdict"]["sentence"]
    starts_with_a_word = sentence[:1].isalpha()
    lines += ["", "Verdict: " + (sentence[:1].lower() + sentence[1:] if starts_with_a_word else sentence)]
    lines += [f"A gate nobody can judge: {state}. Remove it, or give {judges.get(state) or 'its judge'} "
              "something they can read and refuse." for state in result["refused_gates"]]
    return "\n".join(lines) + "\n"


# --- CLI -------------------------------------------------------------------------------------------

def build_parser(parser: argparse.ArgumentParser | None = None) -> argparse.ArgumentParser:
    p = parser or argparse.ArgumentParser(prog="harness flow place", description=__doc__,
                                          formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("file", help="the flow definition, a JSON file")
    p.add_argument("--format", choices=["md", "json"], default="md")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        definition = load_definition(args.file)
        result = place(definition)
    except ValueError as exc:
        print(f"flow: {exc}", file=sys.stderr)
        return 2
    if args.format == "json":
        json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
    else:
        judges = {state: _text(step.get("judge")) for state, step in definition["states"].items()}
        sys.stdout.write(render_md(result, judges))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
