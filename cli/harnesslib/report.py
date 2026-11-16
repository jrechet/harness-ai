"""`report` subcommand: an assessment, always in the same form.

Whether it is about a repository, a harness, an agent, a skill, a plugin or a rule, an assessment
is a list of findings in four columns: what is evaluated (`scope`), what is expected (`expected`),
what is observed (`observed`), what is advised (`advice`). Each finding has a status, and a gap
cites its evidence: without evidence, the report is refused.

The skill or the agent fills in the data; this code validates it and writes the page. Same data, same
file, byte for byte: a single HTML file, with no external resource, readable without JavaScript,
locked by a CSP, and embedding its data (`report-data` block) so that a tool can read it back.

  harness report build report.json -o report.html
  harness report from-place pieces.json --kind skill --name release -o report.html

Format of `report.json`:
    {"subject": {"kind": "skill", "name": "release", "path": "…", "ref": "…"},
     "date": "YYYY-MM-DD", "source": "who produced the finding", "summary": "one sentence (optional)",
     "items": [{"scope": "…", "expected": "…", "observed": "…", "advice": "…",
                "status": "blocker|gap|todo|unknown|ok", "evidence": ["path:line"], "tag": "PUSH_DOWN"}]}

Statuses: `blocker` blocking gap, `gap` gap, `todo` to create, `unknown` not evaluated, `ok` compliant.
`advice` is required except for `ok`; `evidence` is required for `blocker` and `gap`.

Exit codes: 0 written, 2 invalid data (nothing is written)."""
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
KINDS = {"repo": "Repository", "harness": "Harness", "agent": "Agent", "skill": "Skill", "plugin": "Plugin",
         "rule": "Rule", "other": "Other"}
# In reading order: what blocks first, what is fine last.
STATUSES = {"blocker": "Blocking", "gap": "Gap", "todo": "To create", "unknown": "Not evaluated", "ok": "Compliant"}
NEEDS_EVIDENCE = {"blocker", "gap"}
VERDICT_STATUS = {"KEEP": "ok", "PUSH_DOWN": "blocker", "PROMOTE": "gap", "MOVE": "gap", "REMOVE": "gap"}
FIRST = 3


def _text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _validate_item(i: int, item: Any) -> list[str]:
    if not isinstance(item, dict):
        return [f"items[{i}]: expected an object"]
    errors = [f"items[{i}]: field {f} empty" for f in ("scope", "expected", "observed") if not _text(item.get(f))]
    status = item.get("status")
    if status not in STATUSES:
        return errors + [f"items[{i}]: unknown status {status} ({', '.join(STATUSES)})"]
    if status != "ok" and not _text(item.get("advice")):
        errors.append(f"items[{i}]: field advice empty for a {status} finding")
    evidence = item.get("evidence", [])
    if not isinstance(evidence, list) or not all(_text(e) for e in evidence):
        errors.append(f"items[{i}]: evidence is a list of non-empty texts")
    elif status in NEEDS_EVIDENCE and not evidence:
        errors.append(f"items[{i}]: a {status} finding cites its evidence in evidence (path:line)")
    return errors


def validate(report: Any) -> list[str]:
    """The data's defects; an empty list if the report can be written."""
    if not isinstance(report, dict):
        return ["expected an object {subject, date, source, items}"]
    errors = []
    subject = report.get("subject")
    if not isinstance(subject, dict):
        errors.append("subject: expected an object {kind, name}")
    else:
        if subject.get("kind") not in KINDS:
            errors.append(f"subject.kind {subject.get('kind')} unknown ({', '.join(KINDS)})")
        if not _text(subject.get("name")):
            errors.append("subject.name empty")
    try:
        date.fromisoformat(report.get("date", ""))
    except (TypeError, ValueError):
        errors.append("date: expected YYYY-MM-DD")
    if not _text(report.get("source")):
        errors.append("source empty: who produced these findings")
    items = report.get("items")
    if not isinstance(items, list) or not items:
        return errors + ["items: expected a non-empty list of findings"]
    for i, item in enumerate(items):
        errors += _validate_item(i, item)
    return errors


def ordered(report: dict[str, Any]) -> list[dict[str, Any]]:
    """The findings, blocking first; for equal status, the order of the data."""
    rank = {status: n for n, status in enumerate(STATUSES)}
    return sorted(report["items"], key=lambda item: rank[item["status"]])


def summarize(report: dict[str, Any]) -> dict[str, Any]:
    counts = {status: sum(1 for item in report["items"] if item["status"] == status) for status in STATUSES}
    first = [{"advice": item["advice"].strip(), "scope": item["scope"].strip(), "status": item["status"]}
             for item in ordered(report) if item["status"] != "ok"][:FIRST]
    return {"counts": counts, "first": first}


# --- From a placement plan -------------------------------------------------------------------------

def _item_from_piece(grid: dict[str, Any], piece: dict[str, Any], row: dict[str, Any]) -> dict[str, Any]:
    evidence = piece.get("evidence", [])
    base = {"scope": row["piece"], "evidence": evidence if isinstance(evidence, list) else [evidence]}
    current = grid["destinations"][row["current"]]["name"] if row["current"] else None
    if row["status"] == "incomplete":
        q = row["next"]
        return {**base, "status": "unknown", "expected": "A place returned by the placement grid.",
                "observed": f"Today: {current}." if current else "Not placed yet: an answer is missing.",
                "advice": f"Answer the question `{q['id']}`: {q['text']}"}
    dest = row["destination"]
    expected = f"{dest['name']} ({dest['layer']}). {dest['why']}"
    if not current:
        return {**base, "status": "todo", "expected": expected, "observed": "Does not exist yet.",
                "advice": f"Set up: {dest['where']}"}
    if row["verdict"] == "KEEP":
        return {**base, "status": "ok", "tag": "KEEP", "expected": expected,
                "observed": f"{current}: this is its place.", "advice": ""}
    advice = "Remove: nothing to write." if row["verdict"] == "REMOVE" else f"Move to: {dest['where']}"
    return {**base, "status": VERDICT_STATUS[row["verdict"]], "tag": row["verdict"], "expected": expected,
            "observed": f"Today: {current}.", "advice": advice}


def from_place(grid: dict[str, Any], pieces: list[dict[str, Any]], rows: list[dict[str, Any]],
               subject: dict[str, Any], day: str) -> dict[str, Any]:
    """The report of a placement plan: one finding per piece. `pieces` carries the evidence of each
    reviewed piece (`evidence`), `rows` what the grid said about it."""
    return {"subject": subject, "date": day, "source": "harness place",
            "items": [_item_from_piece(grid, piece, row) for piece, row in zip(pieces, rows)]}


# --- HTML rendering --------------------------------------------------------------------------------

def _e(value: Any) -> str:
    return html.escape(str(value).strip(), quote=True)


def _embed(report: dict[str, Any]) -> str:
    """The data in a script block: no sequence may close it or open a comment."""
    raw = json.dumps(report, ensure_ascii=False, sort_keys=True)
    return raw.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")


def _render_item(n: int, item: dict[str, Any]) -> str:
    status = item["status"]
    advice = _e(item.get("advice", "")) or "Nothing to change."
    tag = f'<span class="tag">{_e(item["tag"])}</span>' if _text(item.get("tag")) else ""
    evidence = ""
    if item.get("evidence"):
        codes = " ".join(f"<code>{_e(e)}</code>" for e in item["evidence"])
        evidence = f'\n<p class="evidence"><b>Evidence</b> {codes}</p>'
    return (f'<article class="finding" data-status="{status}">\n'
            f'<header><h3><small>What is evaluated · {n}</small>{_e(item["scope"])}</h3>'
            f'{tag}<span class="chip">{STATUSES[status]}</span></header>\n'
            f'<dl><div><dt>Expected</dt><dd>{_e(item["expected"])}</dd></div>'
            f'<div><dt>Observed</dt><dd>{_e(item["observed"])}</dd></div>'
            f'<div class="advice"><dt>Advice</dt><dd>{advice}</dd></div></dl>{evidence}\n'
            f'</article>')


def _render_first(first: list[dict[str, str]]) -> str:
    if not first:
        return '<p class="none">Nothing to do: everything is compliant.</p>'
    rows = "\n".join(f'<li data-status="{a["status"]}"><span>{_e(a["advice"])}<small>{_e(a["scope"])}</small></span></li>'
                     for a in first)
    return f"<ol>\n{rows}\n</ol>"


def _fields(report: dict[str, Any]) -> dict[str, str]:
    subject, summary = report["subject"], summarize(report)
    meta = [f'<time datetime="{_e(report["date"])}">{_e(report["date"])}</time>', f'by {_e(report["source"])}']
    meta += [f"<code>{_e(subject[k])}</code>" for k in ("path", "ref") if _text(subject.get(k))]
    counts = summary["counts"]
    tally = "\n".join(f'<li data-status="{s}"{"" if counts[s] else " data-zero"}><b>{counts[s]}</b><span>{label}</span></li>'
                      for s, label in STATUSES.items())
    filters = ['<button type="button" data-filter="all" aria-pressed="true">All</button>']
    filters += [f'<button type="button" data-filter="{s}" aria-pressed="false">{label} · {counts[s]}</button>'
                for s, label in STATUSES.items() if counts[s]]
    return {
        "title": f'Assessment · {_e(subject["name"])}',
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
    """Only the template's style and script run: their hash, not 'unsafe-inline'."""
    def digest(tag: str) -> str:
        body = re.search(rf"<{tag}>(.*?)</{tag}>", template, re.S).group(1)
        return base64.b64encode(hashlib.sha256(body.encode("utf-8")).digest()).decode("ascii")
    return (f"default-src 'none'; style-src 'sha256-{digest('style')}'; script-src 'sha256-{digest('script')}'; "
            "base-uri 'none'; form-action 'none'")


def render_html(report: dict[str, Any]) -> str:
    errors = validate(report)
    if errors:
        raise ValueError("invalid report:\n- " + "\n- ".join(errors))
    with open(TEMPLATE_FILE, encoding="utf-8") as fh:
        template = fh.read()
    fields = {**_fields(report), "csp": _csp(template)}
    # A single pass over the template: a "{{items}}" coming from the data is never replaced.
    return re.sub(r"\{\{(\w+)\}\}", lambda m: fields[m.group(1)], template)


# --- CLI -------------------------------------------------------------------------------------------

def _load(path: str) -> Any:
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"{path}: {exc}") from exc


def build_parser(parser: argparse.ArgumentParser | None = None) -> argparse.ArgumentParser:
    p = parser or argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="report_command", required=True)
    build = sub.add_parser("build", help="writes the page from a JSON report")
    build.add_argument("file", help="the report, in the common format")
    fp = sub.add_parser("from-place", help="writes the page of a placement plan")
    fp.add_argument("file", help="the pieces, as for `place plan`; `evidence` cites where a reviewed piece lives")
    fp.add_argument("--kind", choices=list(KINDS), required=True)
    fp.add_argument("--name", required=True, help="what is evaluated")
    fp.add_argument("--path", help="its path in the repository")
    fp.add_argument("--date", help="YYYY-MM-DD (default: today)")
    for sp in (build, fp):
        sp.add_argument("-o", "--output", help="file to write (default: standard output)")
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
        print(f"report: {exc}", file=sys.stderr)
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
