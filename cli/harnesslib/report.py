"""Sous-commande `report` : un état des lieux, toujours sous la même forme.

Qu'il porte sur un dépôt, un harness, un agent, un skill, un plugin ou une règle, un état des lieux
est une liste de constats à quatre colonnes : sur quoi porte l'évaluation (`scope`), ce qui est
attendu (`expected`), ce qui est observé (`observed`), ce qui est conseillé (`advice`). Chaque constat
a un statut, et un écart cite sa preuve : sans preuve, le rapport est refusé.

Le skill ou l'agent remplit les données ; ce code les valide et écrit la page. Mêmes données, même
fichier, à l'octet près : un seul fichier HTML, sans ressource externe, lisible sans JavaScript,
verrouillé par une CSP, et qui embarque ses données (bloc `report-data`) pour qu'un outil les relise.

  harness report build rapport.json -o rapport.html
  harness report from-place morceaux.json --kind skill --name release -o rapport.html

Format de `rapport.json` :
    {"subject": {"kind": "skill", "name": "release", "path": "…", "ref": "…"},
     "date": "AAAA-MM-JJ", "source": "qui a produit le constat", "summary": "une phrase (facultatif)",
     "items": [{"scope": "…", "expected": "…", "observed": "…", "advice": "…",
                "status": "blocker|gap|todo|unknown|ok", "evidence": ["chemin:ligne"], "tag": "PUSH_DOWN"}]}

Statuts : `blocker` écart bloquant, `gap` écart, `todo` à créer, `unknown` non évalué, `ok` conforme.
`advice` est exigé sauf pour `ok` ; `evidence` est exigé pour `blocker` et `gap`.

Codes de sortie : 0 écrit, 2 données invalides (rien n'est écrit)."""
from __future__ import annotations

import argparse
import base64
import hashlib
import html
import json
import os
import re
import sys
from datetime import date
from typing import Any

from . import place

TEMPLATE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "report_template.html")
KINDS = {"repo": "Dépôt", "harness": "Harness", "agent": "Agent", "skill": "Skill", "plugin": "Plugin",
         "rule": "Règle", "other": "Autre"}
# Dans l'ordre où on les lit : ce qui bloque d'abord, ce qui va bien en dernier.
STATUSES = {"blocker": "Bloquant", "gap": "Écart", "todo": "À créer", "unknown": "Non évalué", "ok": "Conforme"}
NEEDS_EVIDENCE = {"blocker", "gap"}
VERDICT_STATUS = {"KEEP": "ok", "PUSH_DOWN": "blocker", "PROMOTE": "gap", "MOVE": "gap", "REMOVE": "gap"}
FIRST = 3


def _text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _validate_item(i: int, item: Any) -> list[str]:
    if not isinstance(item, dict):
        return [f"items[{i}] : attendu un objet"]
    errors = [f"items[{i}] : champ {f} vide" for f in ("scope", "expected", "observed") if not _text(item.get(f))]
    status = item.get("status")
    if status not in STATUSES:
        return errors + [f"items[{i}] : status {status} inconnu ({', '.join(STATUSES)})"]
    if status != "ok" and not _text(item.get("advice")):
        errors.append(f"items[{i}] : champ advice vide pour un constat {status}")
    evidence = item.get("evidence", [])
    if not isinstance(evidence, list) or not all(_text(e) for e in evidence):
        errors.append(f"items[{i}] : evidence est une liste de textes non vides")
    elif status in NEEDS_EVIDENCE and not evidence:
        errors.append(f"items[{i}] : un constat {status} cite sa preuve dans evidence (chemin:ligne)")
    return errors


def validate(report: Any) -> list[str]:
    """Les défauts des données ; une liste vide si le rapport peut être écrit."""
    if not isinstance(report, dict):
        return ["attendu un objet {subject, date, source, items}"]
    errors = []
    subject = report.get("subject")
    if not isinstance(subject, dict):
        errors.append("subject : attendu un objet {kind, name}")
    else:
        if subject.get("kind") not in KINDS:
            errors.append(f"subject.kind {subject.get('kind')} inconnu ({', '.join(KINDS)})")
        if not _text(subject.get("name")):
            errors.append("subject.name vide")
    try:
        date.fromisoformat(report.get("date", ""))
    except (TypeError, ValueError):
        errors.append("date : attendu AAAA-MM-JJ")
    if not _text(report.get("source")):
        errors.append("source vide : qui a produit ces constats")
    items = report.get("items")
    if not isinstance(items, list) or not items:
        return errors + ["items : attendu une liste non vide de constats"]
    for i, item in enumerate(items):
        errors += _validate_item(i, item)
    return errors


def ordered(report: dict[str, Any]) -> list[dict[str, Any]]:
    """Les constats, bloquants d'abord ; à statut égal, l'ordre des données."""
    rank = {status: n for n, status in enumerate(STATUSES)}
    return sorted(report["items"], key=lambda item: rank[item["status"]])


def summarize(report: dict[str, Any]) -> dict[str, Any]:
    counts = {status: sum(1 for item in report["items"] if item["status"] == status) for status in STATUSES}
    first = [{"advice": item["advice"].strip(), "scope": item["scope"].strip(), "status": item["status"]}
             for item in ordered(report) if item["status"] != "ok"][:FIRST]
    return {"counts": counts, "first": first}


# --- Depuis un plan de placement -------------------------------------------------------------------

def _item_from_piece(grid: dict[str, Any], piece: dict[str, Any], row: dict[str, Any]) -> dict[str, Any]:
    evidence = piece.get("evidence", [])
    base = {"scope": row["piece"], "evidence": evidence if isinstance(evidence, list) else [evidence]}
    current = grid["destinations"][row["current"]]["name"] if row["current"] else None
    if row["status"] == "incomplete":
        q = row["next"]
        return {**base, "status": "unknown", "expected": "Une place rendue par la grille de placement.",
                "observed": f"Aujourd'hui : {current}." if current else "Pas encore placé : une réponse manque.",
                "advice": f"Répondre à la question `{q['id']}` : {q['text']}"}
    dest = row["destination"]
    expected = f"{dest['name']} ({dest['layer']}). {dest['why']}"
    if not current:
        return {**base, "status": "todo", "expected": expected, "observed": "N'existe pas encore.",
                "advice": f"Poser : {dest['where']}"}
    if row["verdict"] == "KEEP":
        return {**base, "status": "ok", "tag": "KEEP", "expected": expected,
                "observed": f"{current} : c'est sa place.", "advice": ""}
    advice = "Retirer : rien à écrire." if row["verdict"] == "REMOVE" else f"Déplacer vers : {dest['where']}"
    return {**base, "status": VERDICT_STATUS[row["verdict"]], "tag": row["verdict"], "expected": expected,
            "observed": f"Aujourd'hui : {current}.", "advice": advice}


def from_place(grid: dict[str, Any], pieces: list[dict[str, Any]], rows: list[dict[str, Any]],
               subject: dict[str, Any], day: str) -> dict[str, Any]:
    """Le rapport d'un plan de placement : un constat par morceau. `pieces` porte la preuve de chaque
    morceau revu (`evidence`), `rows` ce que la grille en a dit."""
    return {"subject": subject, "date": day, "source": "harness place",
            "items": [_item_from_piece(grid, piece, row) for piece, row in zip(pieces, rows)]}


# --- Rendu HTML ------------------------------------------------------------------------------------

def _e(value: Any) -> str:
    return html.escape(str(value).strip(), quote=True)


def _embed(report: dict[str, Any]) -> str:
    """Les données dans un bloc script : aucune séquence ne doit pouvoir le fermer ni ouvrir un commentaire."""
    raw = json.dumps(report, ensure_ascii=False, sort_keys=True)
    return raw.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")


def _render_item(n: int, item: dict[str, Any]) -> str:
    status = item["status"]
    advice = _e(item.get("advice", "")) or "Rien à changer."
    tag = f'<span class="tag">{_e(item["tag"])}</span>' if _text(item.get("tag")) else ""
    evidence = ""
    if item.get("evidence"):
        codes = " ".join(f"<code>{_e(e)}</code>" for e in item["evidence"])
        evidence = f'\n<p class="evidence"><b>Preuve</b> {codes}</p>'
    return (f'<article class="finding" data-status="{status}">\n'
            f'<header><h3><small>Sur quoi porte l\'évaluation · {n}</small>{_e(item["scope"])}</h3>'
            f'{tag}<span class="chip">{STATUSES[status]}</span></header>\n'
            f'<dl><div><dt>Attendu</dt><dd>{_e(item["expected"])}</dd></div>'
            f'<div><dt>Observé</dt><dd>{_e(item["observed"])}</dd></div>'
            f'<div class="advice"><dt>Conseillé</dt><dd>{advice}</dd></div></dl>{evidence}\n'
            f'</article>')


def _render_first(first: list[dict[str, str]]) -> str:
    if not first:
        return '<p class="none">Rien à faire : tout est conforme.</p>'
    rows = "\n".join(f'<li data-status="{a["status"]}"><span>{_e(a["advice"])}<small>{_e(a["scope"])}</small></span></li>'
                     for a in first)
    return f"<ol>\n{rows}\n</ol>"


def _fields(report: dict[str, Any]) -> dict[str, str]:
    subject, summary = report["subject"], summarize(report)
    meta = [f'<time datetime="{_e(report["date"])}">{_e(report["date"])}</time>', f'par {_e(report["source"])}']
    meta += [f"<code>{_e(subject[k])}</code>" for k in ("path", "ref") if _text(subject.get(k))]
    counts = summary["counts"]
    tally = "\n".join(f'<li data-status="{s}"{"" if counts[s] else " data-zero"}><b>{counts[s]}</b><span>{label}</span></li>'
                      for s, label in STATUSES.items())
    filters = ['<button type="button" data-filter="all" aria-pressed="true">Tout</button>']
    filters += [f'<button type="button" data-filter="{s}" aria-pressed="false">{label} · {counts[s]}</button>'
                for s, label in STATUSES.items() if counts[s]]
    return {
        "title": f'État des lieux · {_e(subject["name"])}',
        "kind": KINDS[subject["kind"]],
        "name": _e(subject["name"]),
        "meta": " ".join(f"<span>{m}</span>" for m in meta),
        "lede": f'<p class="lede">{_e(report["summary"])}</p>' if _text(report.get("summary")) else "",
        "tally": tally,
        "first": _render_first(summary["first"]),
        "count": str(len(report["items"])),
        "filters": "\n".join(filters),
        "items": "\n".join(_render_item(n, item) for n, item in enumerate(ordered(report), 1)),
        "data": _embed(report),
    }


def _csp(template: str) -> str:
    """Seuls le style et le script du gabarit s'exécutent : leur empreinte, pas 'unsafe-inline'."""
    def digest(tag: str) -> str:
        body = re.search(rf"<{tag}>(.*?)</{tag}>", template, re.S).group(1)
        return base64.b64encode(hashlib.sha256(body.encode("utf-8")).digest()).decode("ascii")
    return (f"default-src 'none'; style-src 'sha256-{digest('style')}'; script-src 'sha256-{digest('script')}'; "
            "base-uri 'none'; form-action 'none'")


def render_html(report: dict[str, Any]) -> str:
    errors = validate(report)
    if errors:
        raise ValueError("rapport invalide :\n- " + "\n- ".join(errors))
    with open(TEMPLATE_FILE, encoding="utf-8") as fh:
        template = fh.read()
    fields = {**_fields(report), "csp": _csp(template)}
    # Une seule passe sur le gabarit : un « {{items}} » venu des données n'est jamais remplacé.
    return re.sub(r"\{\{(\w+)\}\}", lambda m: fields[m.group(1)], template)


# --- CLI -------------------------------------------------------------------------------------------

def _load(path: str) -> Any:
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"{path} : {exc}") from exc


def build_parser(parser: argparse.ArgumentParser | None = None) -> argparse.ArgumentParser:
    p = parser or argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="report_command", required=True)
    build = sub.add_parser("build", help="écrit la page à partir d'un rapport JSON")
    build.add_argument("file", help="le rapport, au format commun")
    fp = sub.add_parser("from-place", help="écrit la page d'un plan de placement")
    fp.add_argument("file", help="les morceaux, comme pour `place plan` ; `evidence` cite où vit un morceau revu")
    fp.add_argument("--kind", choices=list(KINDS), required=True)
    fp.add_argument("--name", required=True, help="ce qui est évalué")
    fp.add_argument("--path", help="son chemin dans le dépôt")
    fp.add_argument("--date", help="AAAA-MM-JJ (défaut : aujourd'hui)")
    for sp in (build, fp):
        sp.add_argument("-o", "--output", help="fichier à écrire (défaut : sortie standard)")
        sp.add_argument("--format", choices=["html", "json"], default="html")
    return p


def _report_from_args(args: argparse.Namespace) -> dict[str, Any]:
    if args.report_command == "build":
        return _load(args.file)
    grid = place.load_grid()
    pieces = place.load_pieces(args.file)
    rows = [place.place_piece(grid, piece) for piece in pieces]
    subject = {"kind": args.kind, "name": args.name, **({"path": args.path} if args.path else {})}
    return from_place(grid, pieces, rows, subject, args.date or date.today().isoformat())


def main(argv: list[str] | None = None, args: argparse.Namespace | None = None) -> int:
    if args is None:
        args = build_parser().parse_args(argv)
    try:
        report = _report_from_args(args)
        page = render_html(report)
    except ValueError as exc:
        print(f"report : {exc}", file=sys.stderr)
        return 2
    content = page if args.format == "html" else json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        with open(args.output, "w", encoding="utf-8") as fh:
            fh.write(content)
    else:
        sys.stdout.write(content)
    return 0


if __name__ == "__main__":
    sys.exit(main())
