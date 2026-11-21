"""`rules` subcommand: the rules of the instruction files, one per line, with what a relevance audit
must know without guessing it: since when the rule exists, whether it says why, whether a guardrail
enforces it. The date comes from the rule (`[YYYY-MM]`), failing that from `git blame`.

A file with a "Rules" or "Forbidden" heading gives rules. A file without one gives its bullets as
lines, not rules (`kind`): notes, logs and to-do boxes cannot be told from rules there. A bullet
that says "Enforced by:" is a rule in both cases."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import date, datetime, timezone
from typing import Any

from . import facts
from .github import ENFORCED_RE, has_rule_headings, iter_rules

RULE_FILES = {"AGENTS.md", "CLAUDE.md"}


def _blame_date(repo: str, rel: str, line: int) -> str | None:
    """The date of the last commit that touched the line, or None outside a git repository."""
    try:
        out = subprocess.run(["git", "-C", repo, "blame", "--porcelain", "-L", f"{line},{line}", "--", rel],
                             capture_output=True, text=True, timeout=120)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if out.returncode != 0:
        return None
    for row in out.stdout.splitlines():
        if row.startswith("author-time "):
            return datetime.fromtimestamp(int(row.split()[1]), tz=timezone.utc).date().isoformat()
    return None


def _age_days(day: str | None, today: date) -> int | None:
    if not day:
        return None
    parts = [int(p) for p in day.split("-")]
    return (today - date(parts[0], parts[1], parts[2] if len(parts) > 2 else 1)).days


def collect(repo: str, today: date | None = None, blame: bool = True) -> list[dict[str, Any]]:
    today = today or date.today()
    repo = os.path.abspath(repo)
    rows = []
    for rel, text in facts.instruction_corpus(repo, RULE_FILES, resolve=False).items():
        known = has_rule_headings(text)
        for line, rule in iter_rules(text):
            tagged = facts.rule_date(rule)
            since = tagged or (_blame_date(repo, rel, line) if blame else None)
            rows.append({
                "file": rel, "line": line, "text": rule,
                "kind": "rule" if known or ENFORCED_RE.search(rule) else "line",
                "since": since, "since_source": "rule" if tagged else ("git" if since else None),
                "age_days": _age_days(since, today),
                "guarded": bool(facts.GUARDED_RE.search(rule)) and not facts.UNGUARDED_RE.search(rule),
                "marked_unguarded": bool(facts.UNGUARDED_RE.search(rule)),
                "justified": bool(facts.WHY_RE.search(rule)),
            })
    return rows


def _summary(rows: list[dict[str, Any]], noun: str) -> str:
    return (f"{len(rows)} {noun}, {sum(1 for r in rows if r['since_source'] == 'rule')} dated in the text, "
            f"{sum(1 for r in rows if r['guarded'])} with a guardrail, {sum(1 for r in rows if r['justified'])} justified.")


def render_markdown(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "No rule found in AGENTS.md or CLAUDE.md.\n"
    lines = [r for r in rows if r.get("kind") == "line"]
    known = [r for r in rows if r.get("kind") != "line"]
    out = [f"| Where | {'Rule' if known else 'Line'} | Since | Age (d) | Guardrail | Why |", "|---|---|---|---|---|---|"]
    for r in rows:
        text = r["text"] if len(r["text"]) <= 70 else r["text"][:67] + "…"
        since = "?" if not r["since"] else r["since"] + ("" if r["since_source"] == "rule" else " (git)")
        guard = "yes" if r["guarded"] else ("no, marked" if r["marked_unguarded"] else "no")
        out.append(f"| {r['file']}:{r['line']} | {text.replace('|', '/')} | {since} | "
                   f"{'?' if r['age_days'] is None else r['age_days']} | {guard} | {'yes' if r['justified'] else 'no'} |")
    out += ["", _summary(known, "rule(s)")]
    if lines:
        files = ", ".join(sorted({r["file"] for r in lines}))
        out.append(f"{_summary(lines, 'line(s)')[:-1]}: lines, not rules — "
                   f"no Rules or Forbidden heading in {files}.")
    return "\n".join(out) + "\n"


def build_parser(parser: argparse.ArgumentParser | None = None) -> argparse.ArgumentParser:
    p = parser or argparse.ArgumentParser(description=__doc__)
    p.add_argument("repo", nargs="?", default=".", help="repository path (default: .)")
    p.add_argument("--format", choices=["md", "json"], default="md")
    p.add_argument("--no-blame", action="store_true", help="do not query git for undated rules")
    p.add_argument("--today", help="YYYY-MM-DD, for reproducible outputs")
    return p


def main(argv: list[str] | None = None, args: argparse.Namespace | None = None) -> int:
    if args is None:
        args = build_parser().parse_args(argv)
    today = date.fromisoformat(args.today) if args.today else None
    rows = collect(args.repo, today, blame=not args.no_blame)
    if args.format == "json":
        json.dump(rows, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
    else:
        sys.stdout.write(render_markdown(rows))
    return 0
