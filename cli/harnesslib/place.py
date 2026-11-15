"""Sous-commande `place` : où va chaque morceau d'un harness, et pourquoi.

La grille (`placement.json`) est un arbre de questions fermées. Ses feuilles sont des destinations :
une ligne dans AGENTS.md, un skill, un sous-agent, une sous-commande CLI, un hook, une permission,
un serveur MCP, un check CI, un paramètre géré… Elle étend L1–L4 de deux axes : la forme que prend
le morceau dans l'outil, et qui ne doit pas pouvoir le contourner (l'agent, le développeur, l'équipe).

L'agent découpe la demande et répond aux questions ; la grille rend la destination. Mêmes réponses,
même destination : c'est ce qui fait de la grille une garantie et pas un conseil.

  harness place grid                        les questions, leurs options, les destinations
  harness place one nature=limit …          un morceau ; s'il manque une réponse, la question suivante
  harness place plan morceaux.json          plusieurs morceaux, avec un verdict si `current` est donné
  harness place check plan.json --expected … note un plan de revue contre le corrigé d'une fixture

Format de `morceaux.json` : une liste de
    {"piece": "Ne jamais pousser sur main", "answers": {"nature": "limit", "bypass_limit": "dev"},
     "current": "agents_md"}
`current` (facultatif) est la destination où le morceau vit aujourd'hui ; le verdict compare.

Codes de sortie : 0 tout est placé, 3 une réponse manque, 2 saisie invalide ; pour `check`, 0 si tous les
pièges sont trouvés sans élément sain déplacé, 1 sinon."""
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
# Une fixture de revue part d'un artefact (chaque morceau a un `current`) ; une fixture de création part
# d'une demande, où rien n'existe encore.
MODES = ("review", "create")


def fold(text: str) -> str:
    """Sans casse ni accents : « Dév » et « dev » sont la même réponse."""
    decomposed = unicodedata.normalize("NFKD", str(text))
    return "".join(c for c in decomposed if not unicodedata.combining(c)).strip().lower()


def load_grid(path: str = GRID_FILE) -> dict[str, Any]:
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _target(option: dict[str, Any]) -> tuple[str, str] | None:
    """('ask', question) ou ('place', destination) ; None si l'option ne dit pas où elle mène."""
    kinds = [k for k in ("ask", "place") if k in option]
    return (kinds[0], option[kinds[0]]) if len(kinds) == 1 else None


def _validate_questions(grid: dict[str, Any]) -> list[str]:
    errors = []
    questions, destinations = grid.get("questions", {}), grid.get("destinations", {})
    for qid, q in questions.items():
        if not ID.fullmatch(qid):
            errors.append(f"question {qid} : identifiant hors minuscules ASCII")
        if not str(q.get("text", "")).strip():
            errors.append(f"question {qid} : texte manquant")
        if len(q.get("options", {})) < 2:
            errors.append(f"question {qid} : moins de deux options")
        for opt, option in q.get("options", {}).items():
            target = _target(option)
            if not ID.fullmatch(opt) or not str(option.get("label", "")).strip():
                errors.append(f"question {qid}, option {opt} : identifiant ou libellé invalide")
            if target is None:
                errors.append(f"question {qid}, option {opt} : ni ask ni place, ou les deux")
            elif target[1] not in (questions if target[0] == "ask" else destinations):
                errors.append(f"question {qid}, option {opt} : {target[0]} vers {target[1]}, introuvable")
    return errors


def _validate_destinations(grid: dict[str, Any]) -> list[str]:
    errors = []
    for did, dest in grid.get("destinations", {}).items():
        for field in ("name", "where", "why"):
            if not str(dest.get(field, "")).strip():
                errors.append(f"destination {did} : champ {field} vide")
        if dest.get("layer") not in LAYERS:
            errors.append(f"destination {did} : couche {dest.get('layer')} inconnue ({', '.join(LAYERS)})")
    return errors


def _reachable(grid: dict[str, Any]) -> tuple[set[str], set[str], list[str]]:
    """Questions et destinations atteintes depuis la racine, et les cycles rencontrés."""
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


def validate(grid: dict[str, Any]) -> list[str]:
    """Les défauts de la grille ; une liste vide si elle est saine."""
    if grid.get("root") not in grid.get("questions", {}):
        return [f"racine {grid.get('root')} introuvable parmi les questions"]
    errors = _validate_questions(grid) + _validate_destinations(grid)
    seen_q, seen_d, cycles = _reachable(grid)
    errors += [f"cycle : {c}" for c in cycles]
    errors += [f"question {q} : aucune réponse n'y mène" for q in sorted(set(grid["questions"]) - seen_q)]
    errors += [f"destination {d} : aucune réponse n'y mène" for d in sorted(set(grid["destinations"]) - seen_d)]
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
        raise ValueError(f"question répondue deux fois : {', '.join(twice)}")
    given = {fold(k): fold(v) for k, v in answers.items()}
    unknown = sorted(k for k in given if k not in grid["questions"])
    if unknown:
        raise ValueError(f"question inconnue : {', '.join(unknown)} (questions : {', '.join(grid['questions'])})")
    return given


def _alternatives(grid: dict[str, Any], qid: str, chosen: str) -> list[dict[str, str]]:
    """Où mènent les autres réponses à la dernière question : ce qui ferait changer la destination."""
    alts = []
    for opt, option in grid["questions"][qid]["options"].items():
        kind, target = _target(option)
        if opt != chosen:
            alts.append({"answer": opt, "leads_to": target, "kind": "destination" if kind == "place" else "question"})
    return alts


def walk(grid: dict[str, Any], answers: dict[str, Any]) -> dict[str, Any]:
    """Suit les réponses depuis la racine jusqu'à une destination, ou jusqu'à la première question
    sans réponse. Une réponse invalide est refusée avec les options valides."""
    given = _normalize(grid, answers)
    path: list[dict[str, str]] = []
    qid = grid["root"]
    while True:
        if qid not in given:
            return {"status": "incomplete", "path": path, "destination": None,
                    "next": question_view(grid, qid), "unused": [], "alternatives": []}
        options = grid["questions"][qid]["options"]
        if given[qid] not in options:
            raise ValueError(f"{qid}={given[qid]} : réponse invalide (options : {', '.join(options)})")
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
    """Le mouvement à faire, dans le vocabulaire de harness-audit, plus MOVE (même couche, ailleurs)."""
    if current == destination:
        return "KEEP"
    if destination == "nothing":
        return "REMOVE"
    here = LAYERS[grid["destinations"][current]["layer"]]
    there = LAYERS[grid["destinations"][destination]["layer"]]
    return "PUSH_DOWN" if there > here else "PROMOTE" if there < here else "MOVE"


def place_piece(grid: dict[str, Any], item: Any) -> dict[str, Any]:
    """Un morceau du plan : ses réponses suivies, et un verdict s'il dit où il vit aujourd'hui."""
    if not isinstance(item, dict) or not isinstance(item.get("piece"), str) or not item["piece"].strip():
        raise ValueError("chaque morceau a un champ piece : un texte non vide")
    if not isinstance(item.get("answers"), dict):
        raise ValueError(f"{item['piece']} : champ answers manquant (un objet question → réponse)")
    current = fold(item["current"]) if item.get("current") else None
    if current == "nothing":
        raise ValueError(f"{item['piece']} : current=nothing ; un morceau qui n'existe pas encore n'a pas de current")
    if current is not None and current not in grid["destinations"]:
        raise ValueError(f"{item['piece']} : current={current} n'est pas une destination "
                         f"({', '.join(grid['destinations'])})")
    result = walk(grid, item["answers"])
    placed = result["status"] == "placed"
    return {"piece": item["piece"], **result, "current": current,
            "verdict": verdict(grid, current, result["destination"]["id"]) if placed and current else None}


# --- Noter un plan contre le corrigé d'une fixture -------------------------------------------------

def _cites(piece: dict[str, Any], spec: dict[str, Any]) -> bool:
    """Le morceau cite-t-il une ligne de la plage attendue ? La preuve est `chemin:ligne`. Si le corrigé
    donne des `natures`, seul un morceau de l'une d'elles compte : deux morceaux tirés d'une même ligne
    ne sont pas le même morceau."""
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
    """Où le plan envoie les morceaux qu'il déplace ; un morceau gardé à sa place n'y figure pas. En
    création rien n'existe encore : toute destination rendue compte."""
    return [r["destination"]["id"] for r in rows
            if r["status"] == "placed" and (create or r["verdict"] not in (None, "KEEP"))]


def _validate_expected(grid: dict[str, Any], expected: Any) -> None:
    if not isinstance(expected, dict) or not isinstance(expected.get("traps"), list):
        raise ValueError("corrigé : attendu un objet {traps, healthy}")
    if expected.get("mode", "review") not in MODES:
        raise ValueError(f"corrigé : mode {expected.get('mode')} inconnu ({', '.join(MODES)})")
    for spec in expected["traps"] + expected.get("healthy", []):
        lines = spec.get("lines")
        if not spec.get("id") or not spec.get("file") or not isinstance(lines, list) or len(lines) != 2:
            raise ValueError(f"corrigé : {spec.get('id', '?')} a un id, un file et lines [début, fin]")
        natures = grid["questions"][grid["root"]]["options"]
        strangers = [n for n in spec.get("natures", []) if n not in natures]
        if strangers:
            raise ValueError(f"corrigé : {spec['id']} cite la nature {', '.join(strangers)}, inconnue")
        unknown = [d for d in spec.get("accept", []) if d not in grid["destinations"]]
        if unknown:
            raise ValueError(f"corrigé : {spec['id']} accepte {', '.join(unknown)}, destination inconnue")


def check(grid: dict[str, Any], expected: Any, pieces: list[Any]) -> dict[str, Any]:
    """Note un plan de revue. Généreux sur la destination (plusieurs sont acceptées), strict sur la
    preuve (le morceau cite la bonne ligne) et sur les éléments sains (aucun ne doit être déplacé)."""
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
    out = [f"Pièges trouvés : {result['found']}/{result['expected']} ; éléments sains déplacés : {result['flagged']}", ""]
    for t in result["traps"]:
        detail = "" if t["status"] == "found" else (
            f" — envoyé vers {', '.join(t['got']) or 'nulle part (gardé en place)'}, attendu {', '.join(t['accept'])}"
            if t["status"] == "wrong" else " — aucun morceau ne cite cette ligne")
        out.append(f"- {t['id']} {t['status']} : {t['what']}{detail}")
    for h in result["healthy"]:
        detail = f" — déplacé vers {', '.join(h['got'])}" if h["status"] == "flagged" else ""
        out.append(f"- {h['id']} {h['status']} : {h['what']}{detail}")
    return "\n".join(out) + "\n"


# --- Rendu -----------------------------------------------------------------------------------------

def _leads_to_label(grid: dict[str, Any], alt: dict[str, str]) -> str:
    if alt["kind"] == "destination":
        return grid["destinations"][alt["leads_to"]]["name"]
    return f"question {alt['leads_to']}"


def render_piece_md(grid: dict[str, Any], row: dict[str, Any]) -> str:
    if row["status"] == "incomplete":
        q = row["next"]
        lines = ["Il manque une réponse."]
        if row.get("current"):
            lines.append(f"Aujourd'hui : {grid['destinations'][row['current']]['name']} ; "
                         "le verdict viendra une fois le morceau placé.")
        lines += ["", f"Question `{q['id']}` : {q['text']}", ""]
        lines += [f"- `{opt}` : {label}" for opt, label in q["options"].items()]
        return "\n".join(lines + ["", f"Réponds avec `{q['id']}=<option>`."]) + "\n"
    dest = row["destination"]
    lines = [f"**{dest['name']}** ({dest['layer']})"]
    if row.get("verdict"):
        lines.append(f"Verdict : {row['verdict']}, depuis {grid['destinations'][row['current']]['name']}")
    lines += [f"Où : {dest['where']}", f"Pourquoi : {dest['why']}"]
    if dest.get("also"):
        lines.append(f"En complément : {dest['also']}")
    lines.append("Chemin : " + " → ".join(f"{s['question']}={s['answer']}" for s in row["path"]))
    last = row["path"][-1]["question"]
    alts = " ; ".join(f"{a['answer']} → {_leads_to_label(grid, a)}" for a in row["alternatives"])
    lines.append(f"Si `{last}` change : {alts}")
    if row["unused"]:
        lines.append("Réponses hors du chemin, ignorées : " + ", ".join(row["unused"]))
    return "\n".join(lines) + "\n"


def _cell(text: str) -> str:
    return str(text).replace("|", "\\|").replace("\n", " ")


def render_plan_md(grid: dict[str, Any], rows: list[dict[str, Any]]) -> str:
    out = ["# Plan de placement", "", "| # | Morceau | Destination | Couche | Verdict |", "|---|---|---|---|---|"]
    for i, row in enumerate(rows, 1):
        if row["status"] == "placed":
            dest = row["destination"]
            out.append(f"| {i} | {_cell(row['piece'])} | {dest['name']} | {dest['layer']} | {row['verdict'] or '—'} |")
        else:
            out.append(f"| {i} | {_cell(row['piece'])} | réponse manquante : `{row['next']['id']}` | — | — |")
    for i, row in enumerate(rows, 1):
        out += ["", f"## {i}. {row['piece']}", "", render_piece_md(grid, row).rstrip("\n")]
    return "\n".join(out) + "\n"


def render_grid_md(grid: dict[str, Any]) -> str:
    out = ["# Grille de placement", "", f"Racine : `{grid['root']}`", ""]
    for qid, q in grid["questions"].items():
        out += [f"## `{qid}` — {q['text']}", ""]
        for opt, option in q["options"].items():
            kind, target = _target(option)
            to = grid["destinations"][target]["name"] if kind == "place" else f"question `{target}`"
            out.append(f"- `{opt}` : {option['label']} → {to}")
        out.append("")
    out += ["## Destinations", ""]
    out += [f"- `{did}` — **{d['name']}** ({d['layer']}) : {d['where']}" for did, d in grid["destinations"].items()]
    return "\n".join(out) + "\n"


# --- CLI -------------------------------------------------------------------------------------------

def parse_answers(tokens: list[str]) -> dict[str, str]:
    answers = {}
    for token in tokens:
        key, sep, value = token.partition("=")
        if not sep or not key.strip() or not value.strip():
            raise ValueError(f"{token} : attendu question=réponse")
        answers[key.strip()] = value.strip()
    return answers


def load_pieces(path: str) -> list[Any]:
    try:
        with open(path, encoding="utf-8") as fh:
            pieces = json.load(fh)
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"{path} : {exc}") from exc
    if not isinstance(pieces, list) or not pieces:
        raise ValueError(f"{path} : attendu une liste non vide de morceaux")
    return pieces


def build_parser(parser: argparse.ArgumentParser | None = None) -> argparse.ArgumentParser:
    p = parser or argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="place_command", required=True)
    grid = sub.add_parser("grid", help="les questions, leurs options, les destinations")
    one = sub.add_parser("one", help="un morceau, à partir de ses réponses")
    one.add_argument("answers", nargs="*", metavar="question=réponse")
    one.add_argument("--current", help="destination où le morceau vit aujourd'hui, pour un verdict")
    plan = sub.add_parser("plan", help="plusieurs morceaux, depuis un fichier JSON")
    plan.add_argument("file", help="liste de {piece, answers, current?}")
    chk = sub.add_parser("check", help="note un plan de revue contre le corrigé d'une fixture")
    chk.add_argument("file", help="le plan : liste de {piece, answers, current, evidence}")
    chk.add_argument("--expected", required=True, help="expected.json de la fixture")
    for sp in (grid, one, plan, chk):
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
            row = place_piece(grid, {"piece": "morceau", "answers": parse_answers(args.answers),
                                     "current": args.current})
            _emit(args.format, row, render_piece_md(grid, row))
            return 0 if row["status"] == "placed" else INCOMPLETE
        if args.place_command == "check":
            try:
                with open(args.expected, encoding="utf-8") as fh:
                    expected = json.load(fh)
            except (OSError, json.JSONDecodeError) as exc:
                raise ValueError(f"{args.expected} : {exc}") from exc
            result = check(grid, expected, load_pieces(args.file))
            _emit(args.format, result, render_check_md(result))
            return 0 if result["passed"] else 1
        rows = [place_piece(grid, item) for item in load_pieces(args.file)]
    except ValueError as exc:
        print(f"place : {exc}", file=sys.stderr)
        return 2
    _emit(args.format, rows, render_plan_md(grid, rows))
    return 0 if all(r["status"] == "placed" for r in rows) else INCOMPLETE


if __name__ == "__main__":
    sys.exit(main())
