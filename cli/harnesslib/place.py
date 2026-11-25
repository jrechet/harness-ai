"""`place` subcommand: where each piece of a harness goes, and why.

The grid (`placement.json`) is a tree of closed questions. Its leaves are destinations:
a line in AGENTS.md, a skill, a subagent, a CLI subcommand, a hook, a permission,
an MCP server, a CI check, a managed setting… It extends L1–L4 with two axes: the form the piece
takes in the tool, and who must not be able to bypass it (the agent, the developer, the team).

The agent splits the request and answers the questions; the grid returns the destination. Same answers,
same destination: that is what makes the grid a guarantee and not advice.

  harness place grid                        the questions, their options, the destinations
  harness place one nature=limit …          one piece; if an answer is missing, the next question
  harness place plan pieces.json            several pieces, with a verdict if `current` is given
  harness place review pieces.json          the same placement told as named concepts: what is well
                                            placed, what is weak and why; no layer, no verdict code
  harness place check plan.json --expected … grades a review plan against a fixture's answer key

Format of `pieces.json`: a list of
    {"piece": "Never push to main", "answers": {"nature": "limit", "bypass_limit": "dev"},
     "current": "agents_md"}
`current` (optional) is the destination where the piece lives today; the verdict compares.

Exit codes: 0 everything is placed, 3 an answer is missing, 2 invalid input; for `check`, 0 if every
trap is found with no healthy item moved, 1 otherwise."""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import unicodedata
from typing import Any

GRID_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "placement.json")
ID = re.compile(r"[a-z][a-z0-9_]*")
LAYERS = {"L1": 1, "L2": 2, "L3": 3, "L4": 4, "L3 + L4": 4, "-": 0}
INCOMPLETE = 3
# A review fixture starts from an artifact (each piece has a `current`); a create fixture starts
# from a request, where nothing exists yet.
MODES = ("review", "create")
# What `place review` can name. `two_in_one` is a note on the whole artifact, the others file one piece.
CONCEPTS = ("skippable_condition", "determinism", "limit_only_asked", "unguarded_action", "weak_guard",
            "frozen_judgment", "tidy_helper", "dead_weight", "wrong_place", "two_in_one")
CHECKS = ("hook_check", "ci_check", "release_gate", "org_check")
TEXT_LAYER = 2          # up to here a piece is held by a sentence; beyond, by code or by a setting


def fold(text: str) -> str:
    """Without case or accents: "Dév" and "dev" are the same answer."""
    decomposed = unicodedata.normalize("NFKD", str(text))
    return "".join(c for c in decomposed if not unicodedata.combining(c)).strip().lower()


def load_grid(path: str = GRID_FILE) -> dict[str, Any]:
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _target(option: dict[str, Any]) -> tuple[str, str] | None:
    """('ask', question) or ('place', destination); None if the option does not say where it leads."""
    kinds = [k for k in ("ask", "place") if k in option]
    return (kinds[0], option[kinds[0]]) if len(kinds) == 1 else None


def _validate_questions(grid: dict[str, Any]) -> list[str]:
    errors = []
    questions, destinations = grid.get("questions", {}), grid.get("destinations", {})
    for qid, q in questions.items():
        if not ID.fullmatch(qid):
            errors.append(f"question {qid}: id is not lowercase ASCII")
        if not str(q.get("text", "")).strip():
            errors.append(f"question {qid}: text missing")
        if len(q.get("options", {})) < 2:
            errors.append(f"question {qid}: fewer than two options")
        for opt, option in q.get("options", {}).items():
            target = _target(option)
            if not ID.fullmatch(opt) or not str(option.get("label", "")).strip():
                errors.append(f"question {qid}, option {opt}: invalid id or label")
            if target is None:
                errors.append(f"question {qid}, option {opt}: neither ask nor place, or both")
            elif target[1] not in (questions if target[0] == "ask" else destinations):
                errors.append(f"question {qid}, option {opt}: {target[0]} to {target[1]}, not found")
    return errors


def _validate_destinations(grid: dict[str, Any]) -> list[str]:
    errors = []
    for did, dest in grid.get("destinations", {}).items():
        for field in ("name", "where", "why"):
            if not str(dest.get(field, "")).strip():
                errors.append(f"destination {did}: field {field} empty")
        if dest.get("layer") not in LAYERS:
            errors.append(f"destination {did}: unknown layer {dest.get('layer')} ({', '.join(LAYERS)})")
    return errors


def _reachable(grid: dict[str, Any]) -> tuple[set[str], set[str], list[str]]:
    """Questions and destinations reached from the root, and the cycles met."""
    seen_q: set[str] = set()
    seen_d: set[str] = set()
    cycles: list[str] = []

    def visit(qid: str, stack: tuple[str, ...]) -> None:
        if qid in stack:
            cycles.append(" → ".join(stack + (qid,)))
            return
        if qid not in grid["questions"]:
            return
        seen_q.add(qid)
        for option in grid["questions"][qid].get("options", {}).values():
            target = _target(option)
            if target and target[0] == "ask":
                visit(target[1], stack + (qid,))
            elif target:
                seen_d.add(target[1])

    visit(grid.get("root", ""), ())
    return seen_q, seen_d, cycles


def _validate_concepts(grid: dict[str, Any]) -> list[str]:
    """A grid that names concepts names all those the review can file a piece under, and no other.
    A grid without the block (the flow's own grid) is not reviewed, so it is not held to it."""
    if "concepts" not in grid:
        return []
    concepts = grid["concepts"]
    errors = [f"concept {cid}: missing" for cid in CONCEPTS if cid not in concepts]
    errors += [f"concept {cid}: unknown, the review never names it" for cid in concepts if cid not in CONCEPTS]
    for cid, concept in concepts.items():
        for field in ("name", "definition"):
            if not str(concept.get(field, "")).strip():
                errors.append(f"concept {cid}: field {field} empty")
    return errors


def validate(grid: dict[str, Any]) -> list[str]:
    """The grid's defects; an empty list if it is sound."""
    if grid.get("root") not in grid.get("questions", {}):
        return [f"root {grid.get('root')} not found among the questions"]
    errors = _validate_questions(grid) + _validate_destinations(grid) + _validate_concepts(grid)
    seen_q, seen_d, cycles = _reachable(grid)
    errors += [f"cycle: {c}" for c in cycles]
    errors += [f"question {q}: no answer leads to it" for q in sorted(set(grid["questions"]) - seen_q)]
    errors += [f"destination {d}: no answer leads to it" for d in sorted(set(grid["destinations"]) - seen_d)]
    return errors


def question_view(grid: dict[str, Any], qid: str) -> dict[str, Any]:
    q = grid["questions"][qid]
    return {"id": qid, "text": q["text"], "options": {o: v["label"] for o, v in q["options"].items()}}


def destination_view(grid: dict[str, Any], did: str) -> dict[str, Any]:
    return {"id": did, **grid["destinations"][did]}


def _normalize(grid: dict[str, Any], answers: dict[str, Any]) -> dict[str, str]:
    keys = [fold(k) for k in answers]
    twice = sorted({k for k in keys if keys.count(k) > 1})
    if twice:
        raise ValueError(f"question answered twice: {', '.join(twice)}")
    given = {fold(k): fold(v) for k, v in answers.items()}
    unknown = sorted(k for k in given if k not in grid["questions"])
    if unknown:
        raise ValueError(f"unknown question: {', '.join(unknown)} (questions: {', '.join(grid['questions'])})")
    return given


def _alternatives(grid: dict[str, Any], qid: str, chosen: str) -> list[dict[str, str]]:
    """Where the other answers to the last question lead: what would change the destination."""
    alts = []
    for opt, option in grid["questions"][qid]["options"].items():
        kind, target = _target(option)
        if opt != chosen:
            alts.append({"answer": opt, "leads_to": target, "kind": "destination" if kind == "place" else "question"})
    return alts


def walk(grid: dict[str, Any], answers: dict[str, Any]) -> dict[str, Any]:
    """Follows the answers from the root to a destination, or to the first unanswered question.
    An invalid answer is refused with the valid options."""
    given = _normalize(grid, answers)
    path: list[dict[str, str]] = []
    qid = grid["root"]
    while True:
        if qid not in given:
            return {"status": "incomplete", "path": path, "destination": None,
                    "next": question_view(grid, qid), "unused": [], "alternatives": []}
        options = grid["questions"][qid]["options"]
        if given[qid] not in options:
            raise ValueError(f"{qid}={given[qid]}: invalid answer (options: {', '.join(options)})")
        path.append({"question": qid, "answer": given[qid]})
        kind, target = _target(options[given[qid]])
        if kind == "place":
            break
        qid = target
    on_path = {step["question"] for step in path}
    return {"status": "placed", "path": path, "destination": destination_view(grid, target), "next": None,
            "unused": sorted(k for k in given if k not in on_path),
            "alternatives": _alternatives(grid, path[-1]["question"], path[-1]["answer"])}


def verdict(grid: dict[str, Any], current: str, destination: str) -> str:
    """The move to make, in harness-audit's vocabulary, plus MOVE (same layer, elsewhere)."""
    if current == destination:
        return "KEEP"
    if destination == "nothing":
        return "REMOVE"
    here = LAYERS[grid["destinations"][current]["layer"]]
    there = LAYERS[grid["destinations"][destination]["layer"]]
    return "PUSH_DOWN" if there > here else "PROMOTE" if there < here else "MOVE"


def place_piece(grid: dict[str, Any], item: Any) -> dict[str, Any]:
    """One piece of the plan: its answers followed, and a verdict if it says where it lives today."""
    if not isinstance(item, dict) or not isinstance(item.get("piece"), str) or not item["piece"].strip():
        raise ValueError("each piece has a piece field: a non-empty text")
    if not isinstance(item.get("answers"), dict):
        raise ValueError(f"{item['piece']}: answers field missing (an object question → answer)")
    current = fold(item["current"]) if item.get("current") else None
    if current == "nothing":
        raise ValueError(f"{item['piece']}: current=nothing; a piece that does not exist yet has no current")
    if current is not None and current not in grid["destinations"]:
        raise ValueError(f"{item['piece']}: current={current} is not a destination "
                         f"({', '.join(grid['destinations'])})")
    result = walk(grid, item["answers"])
    placed = result["status"] == "placed"
    return {"piece": item["piece"], **result, "current": current,
            "verdict": verdict(grid, current, result["destination"]["id"]) if placed and current else None}


# --- Grading a plan against a fixture's answer key -------------------------------------------------

def _cites(piece: dict[str, Any], spec: dict[str, Any]) -> bool:
    """Does the piece cite a line in the expected range? The evidence is `path:line`. If the answer key
    gives `natures`, only a piece of one of them counts: two pieces cut from the same line
    are not the same piece."""
    natures = spec.get("natures")
    answers = piece.get("answers") if isinstance(piece.get("answers"), dict) else {}
    if natures and fold(answers.get("nature", "")) not in natures:
        return False
    evidence = piece.get("evidence", [])
    for entry in evidence if isinstance(evidence, list) else [evidence]:
        path, _, line = str(entry).rpartition(":")
        digits = line.split("-")[0].strip()
        if path.strip().removeprefix("./").removeprefix("artifact/") == spec["file"] and digits.isdigit() \
                and spec["lines"][0] <= int(digits) <= spec["lines"][1]:
            return True
    return False


def _moves(rows: list[dict[str, Any]], create: bool = False) -> list[str]:
    """Where the plan sends the pieces it moves; a piece kept in place is not listed. In
    create mode nothing exists yet: every destination returned counts."""
    return [r["destination"]["id"] for r in rows
            if r["status"] == "placed" and (create or r["verdict"] not in (None, "KEEP"))]


def _validate_expected(grid: dict[str, Any], expected: Any) -> None:
    if not isinstance(expected, dict) or not isinstance(expected.get("traps"), list):
        raise ValueError("answer key: expected an object {traps, healthy}")
    if expected.get("mode", "review") not in MODES:
        raise ValueError(f"answer key: unknown mode {expected.get('mode')} ({', '.join(MODES)})")
    for spec in expected["traps"] + expected.get("healthy", []):
        lines = spec.get("lines")
        if not spec.get("id") or not spec.get("file") or not isinstance(lines, list) or len(lines) != 2:
            raise ValueError(f"answer key: {spec.get('id', '?')} needs an id, a file and lines [start, end]")
        natures = grid["questions"][grid["root"]]["options"]
        strangers = [n for n in spec.get("natures", []) if n not in natures]
        if strangers:
            raise ValueError(f"answer key: {spec['id']} cites the nature {', '.join(strangers)}, unknown")
        unknown = [d for d in spec.get("accept", []) if d not in grid["destinations"]]
        if unknown:
            raise ValueError(f"answer key: {spec['id']} accepts {', '.join(unknown)}, unknown destination")


def check(grid: dict[str, Any], expected: Any, pieces: list[Any]) -> dict[str, Any]:
    """Grades a review plan. Generous on the destination (several are accepted), strict on the
    evidence (the piece cites the right line) and on healthy items (none may be moved)."""
    _validate_expected(grid, expected)
    rows = [(piece, place_piece(grid, piece)) for piece in pieces]
    create = expected.get("mode", "review") == "create"
    traps, healthy = [], []
    for spec in expected["traps"]:
        got = _moves([row for piece, row in rows if _cites(piece, spec)], create)
        status = "found" if any(d in spec["accept"] for d in got) else "wrong" if any(
            _cites(piece, spec) for piece, _ in rows) else "missed"
        traps.append({"id": spec["id"], "what": spec.get("what", ""), "status": status, "got": got,
                      "accept": spec["accept"]})
    for spec in expected.get("healthy", []):
        cited = [row for piece, row in rows if _cites(piece, spec)]
        got = _moves(cited)
        healthy.append({"id": spec["id"], "what": spec.get("what", ""), "got": got,
                        "status": "flagged" if got else "kept" if cited else "absent"})
    found = sum(1 for t in traps if t["status"] == "found")
    flagged = sum(1 for h in healthy if h["status"] == "flagged")
    return {"found": found, "expected": len(traps), "flagged": flagged, "traps": traps, "healthy": healthy,
            "passed": found == len(traps) and flagged == 0}


def render_check_md(result: dict[str, Any]) -> str:
    out = [f"Traps found: {result['found']}/{result['expected']}; healthy items moved: {result['flagged']}", ""]
    for t in result["traps"]:
        detail = "" if t["status"] == "found" else (
            f" — sent to {', '.join(t['got']) or 'nowhere (kept in place)'}, expected {', '.join(t['accept'])}"
            if t["status"] == "wrong" else " — no piece cites this line")
        out.append(f"- {t['id']} {t['status']}: {t['what']}{detail}")
    for h in result["healthy"]:
        detail = f" — moved to {', '.join(h['got'])}" if h["status"] == "flagged" else ""
        out.append(f"- {h['id']} {h['status']}: {h['what']}{detail}")
    return "\n".join(out) + "\n"


# --- Review: the same placement, told as named concepts --------------------------------------------

def concept(grid: dict[str, Any], row: dict[str, Any]) -> str | None:
    """The concept a misplaced piece falls under; None if it is in its place or not placed yet.
    Decided from the piece's nature, where it is held today and where the grid sends it: same
    answers, same concept."""
    if row["status"] != "placed" or row["verdict"] in (None, "KEEP"):
        return None
    nature = row["path"][0]["answer"]
    destination = row["destination"]["id"]
    held_by_text = LAYERS[grid["destinations"][row["current"]]["layer"]] <= TEXT_LAYER
    if row["verdict"] == "REMOVE":
        return "dead_weight"
    if row["verdict"] == "PROMOTE":
        return "wrong_place" if held_by_text else "frozen_judgment"
    if row["current"] == "subagent" and destination == "session":
        return "tidy_helper"
    if held_by_text:
        if nature == "compute":
            return "determinism"
        if nature == "rule" and destination in CHECKS:
            return "skippable_condition"
        if nature == "limit":
            return "limit_only_asked"
        if nature == "action":
            return "unguarded_action"
    elif nature in ("rule", "limit", "action"):
        return "weak_guard"
    return "wrong_place"


def review(grid: dict[str, Any], pieces: list[Any]) -> dict[str, Any]:
    """Every piece of an existing artifact, sorted: well placed, weak (with its concept), or still
    waiting for an answer. A review reads what exists: a piece without `current` is refused."""
    good, findings, waiting = [], [], []
    for item in pieces:
        row = place_piece(grid, item)
        if row["current"] is None:
            raise ValueError(f"{row['piece']}: current field missing; a review says where each piece is held today")
        evidence = item.get("evidence", [])
        row["evidence"] = [str(e) for e in (evidence if isinstance(evidence, list) else [evidence])]
        row["concept"] = concept(grid, row)
        (waiting if row["status"] != "placed" else findings if row["concept"] else good).append(row)
    skill_keeps_its_procedure = any(r["current"] == "skill" for r in good)
    mixed = skill_keeps_its_procedure and any(r["current"] == "skill" for r in findings)
    return {"good": good, "findings": findings, "waiting": waiting, "notes": ["two_in_one"] if mixed else []}


def _cited(row: dict[str, Any]) -> str:
    return f" ({', '.join(row['evidence'])})" if row.get("evidence") else ""


def render_review_md(grid: dict[str, Any], result: dict[str, Any]) -> str:
    names = grid["destinations"]
    total = len(result["good"]) + len(result["findings"]) + len(result["waiting"])
    summary = f"{total} pieces read: {len(result['good'])} well placed, {len(result['findings'])} to change"
    if result["waiting"]:
        summary += f", {len(result['waiting'])} waiting for an answer"
    out = ["# Review", "", summary + "."]
    if result["good"]:
        out += ["", "## Well placed", ""]
        out += [f"- **{_cell(r['piece'])}**{_cited(r)}: {names[r['current']]['name']}, where it belongs."
                for r in result["good"]]
    for cid in CONCEPTS:
        rows = [r for r in result["findings"] if r["concept"] == cid]
        if not rows and cid not in result["notes"]:
            continue
        out += ["", f"## {grid['concepts'][cid]['name']}", "", grid["concepts"][cid]["definition"]]
        for r in rows:
            dest = r["destination"]
            out += ["", f"- **{_cell(r['piece'])}**{_cited(r)}"]
            if dest["id"] == "nothing":
                out.append(f"  Today: {names[r['current']]['name']}. Better: take it out.")
                continue
            out += [f"  Today: {names[r['current']]['name']}. Better: {dest['name']}.",
                    f"  Where: {dest['where']}", f"  Why: {dest['why']}"]
    if result["waiting"]:
        out += ["", "## Not decided yet", ""]
        for r in result["waiting"]:
            q = r["next"]
            out += [f"- **{_cell(r['piece'])}**{_cited(r)}: {q['text']}"]
            out += [f"  - {label}" for label in q["options"].values()]
    return "\n".join(out) + "\n"


# --- Rendering -------------------------------------------------------------------------------------

def _leads_to_label(grid: dict[str, Any], alt: dict[str, str]) -> str:
    if alt["kind"] == "destination":
        return grid["destinations"][alt["leads_to"]]["name"]
    return f"question {alt['leads_to']}"


def render_piece_md(grid: dict[str, Any], row: dict[str, Any]) -> str:
    if row["status"] == "incomplete":
        q = row["next"]
        lines = ["An answer is missing."]
        if row.get("current"):
            lines.append(f"Today: {grid['destinations'][row['current']]['name']}; "
                         "the verdict will come once the piece is placed.")
        lines += ["", f"Question `{q['id']}`: {q['text']}", ""]
        lines += [f"- `{opt}`: {label}" for opt, label in q["options"].items()]
        return "\n".join(lines + ["", f"Answer with `{q['id']}=<option>`."]) + "\n"
    dest = row["destination"]
    lines = [f"**{dest['name']}** ({dest['layer']})"]
    if row.get("verdict"):
        lines.append(f"Verdict: {row['verdict']}, from {grid['destinations'][row['current']]['name']}")
    lines += [f"Where: {dest['where']}", f"Why: {dest['why']}"]
    if dest.get("also"):
        lines.append(f"In addition: {dest['also']}")
    lines.append("Path: " + " → ".join(f"{s['question']}={s['answer']}" for s in row["path"]))
    last = row["path"][-1]["question"]
    alts = " ; ".join(f"{a['answer']} → {_leads_to_label(grid, a)}" for a in row["alternatives"])
    lines.append(f"If `{last}` changes: {alts}")
    if row["unused"]:
        lines.append("Answers off the path, ignored: " + ", ".join(row["unused"]))
    return "\n".join(lines) + "\n"


def _cell(text: str) -> str:
    return str(text).replace("|", "\\|").replace("\n", " ")


def render_plan_md(grid: dict[str, Any], rows: list[dict[str, Any]]) -> str:
    out = ["# Placement plan", "", "| # | Piece | Destination | Layer | Verdict |", "|---|---|---|---|---|"]
    for i, row in enumerate(rows, 1):
        if row["status"] == "placed":
            dest = row["destination"]
            out.append(f"| {i} | {_cell(row['piece'])} | {dest['name']} | {dest['layer']} | {row['verdict'] or '—'} |")
        else:
            out.append(f"| {i} | {_cell(row['piece'])} | missing answer: `{row['next']['id']}` | — | — |")
    for i, row in enumerate(rows, 1):
        out += ["", f"## {i}. {row['piece']}", "", render_piece_md(grid, row).rstrip("\n")]
    return "\n".join(out) + "\n"


def render_grid_md(grid: dict[str, Any]) -> str:
    out = ["# Placement grid", "", f"Root: `{grid['root']}`", ""]
    for qid, q in grid["questions"].items():
        out += [f"## `{qid}` — {q['text']}", ""]
        for opt, option in q["options"].items():
            kind, target = _target(option)
            to = grid["destinations"][target]["name"] if kind == "place" else f"question `{target}`"
            out.append(f"- `{opt}`: {option['label']} → {to}")
        out.append("")
    out += ["## Destinations", ""]
    out += [f"- `{did}` — **{d['name']}** ({d['layer']}): {d['where']}" for did, d in grid["destinations"].items()]
    return "\n".join(out) + "\n"


# --- CLI -------------------------------------------------------------------------------------------

def parse_answers(tokens: list[str]) -> dict[str, str]:
    answers = {}
    for token in tokens:
        key, sep, value = token.partition("=")
        if not sep or not key.strip() or not value.strip():
            raise ValueError(f"{token}: expected question=answer")
        answers[key.strip()] = value.strip()
    return answers


def load_pieces(path: str) -> list[Any]:
    try:
        with open(path, encoding="utf-8") as fh:
            pieces = json.load(fh)
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"{path}: {exc}") from exc
    if not isinstance(pieces, list) or not pieces:
        raise ValueError(f"{path}: expected a non-empty list of pieces")
    return pieces


def build_parser(parser: argparse.ArgumentParser | None = None) -> argparse.ArgumentParser:
    p = parser or argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="place_command", required=True)
    grid = sub.add_parser("grid", help="the questions, their options, the destinations")
    one = sub.add_parser("one", help="one piece, from its answers")
    one.add_argument("answers", nargs="*", metavar="question=answer")
    one.add_argument("--current", help="destination where the piece lives today, for a verdict")
    plan = sub.add_parser("plan", help="several pieces, from a JSON file")
    plan.add_argument("file", help="list of {piece, answers, current?}")
    chk = sub.add_parser("check", help="grades a review plan against a fixture's answer key")
    chk.add_argument("file", help="the plan: list of {piece, answers, current, evidence}")
    chk.add_argument("--expected", required=True, help="the fixture's expected.json")
    rev = sub.add_parser("review", help="an existing artifact's pieces, told as named concepts")
    rev.add_argument("file", help="list of {piece, answers, current, evidence?}")
    for sp in (grid, one, plan, chk, rev):
        sp.add_argument("--format", choices=["md", "json"], default="md")
    return p


def _emit(fmt: str, data: Any, markdown: str) -> None:
    if fmt == "json":
        json.dump(data, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
    else:
        sys.stdout.write(markdown)


def main(argv: list[str] | None = None, args: argparse.Namespace | None = None) -> int:
    if args is None:
        args = build_parser().parse_args(argv)
    grid = load_grid()
    try:
        if args.place_command == "grid":
            _emit(args.format, grid, render_grid_md(grid))
            return 0
        if args.place_command == "one":
            row = place_piece(grid, {"piece": "piece", "answers": parse_answers(args.answers),
                                     "current": args.current})
            _emit(args.format, row, render_piece_md(grid, row))
            return 0 if row["status"] == "placed" else INCOMPLETE
        if args.place_command == "check":
            try:
                with open(args.expected, encoding="utf-8") as fh:
                    expected = json.load(fh)
            except (OSError, json.JSONDecodeError) as exc:
                raise ValueError(f"{args.expected}: {exc}") from exc
            result = check(grid, expected, load_pieces(args.file))
            _emit(args.format, result, render_check_md(result))
            return 0 if result["passed"] else 1
        if args.place_command == "review":
            result = review(grid, load_pieces(args.file))
            _emit(args.format, result, render_review_md(grid, result))
            return INCOMPLETE if result["waiting"] else 0
        rows = [place_piece(grid, item) for item in load_pieces(args.file)]
    except ValueError as exc:
        print(f"place: {exc}", file=sys.stderr)
        return 2
    _emit(args.format, rows, render_plan_md(grid, rows))
    return 0 if all(r["status"] == "placed" for r in rows) else INCOMPLETE


if __name__ == "__main__":
    sys.exit(main())
