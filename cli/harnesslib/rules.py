"""Sous-commande `rules` : les règles des fichiers d'instructions, une par ligne, avec ce qu'un audit
de pertinence doit savoir sans le deviner — depuis quand la règle existe, si elle dit pourquoi, si un
garde-fou la porte. La date vient de la règle (`[AAAA-MM]`), à défaut de `git blame`."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import date, datetime, timezone
from typing import Any

from . import facts
from .github import iter_rules

RULE_FILES = {"AGENTS.md", "CLAUDE.md"}


def _blame_date(repo: str, rel: str, line: int) -> str | None:
    """La date du dernier commit qui a touché la ligne, ou None hors d'un dépôt git."""
    try:
        out = subprocess.run(["git", "-C", repo, "blame", "--porcelain", "-L", f"{line},{line}", "--", rel],
                             capture_output=True, text=True, timeout=20)
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
        for line, rule in iter_rules(text):
            tagged = facts.rule_date(rule)
            since = tagged or (_blame_date(repo, rel, line) if blame else None)
            rows.append({
                "file": rel, "line": line, "text": rule,
                "since": since, "since_source": "rule" if tagged else ("git" if since else None),
                "age_days": _age_days(since, today),
                "guarded": bool(facts.GUARDED_RE.search(rule)) and not facts.UNGUARDED_RE.search(rule),
                "marked_unguarded": bool(facts.UNGUARDED_RE.search(rule)),
                "justified": bool(facts.WHY_RE.search(rule)),
            })
    return rows


def render_markdown(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "Aucune règle trouvée dans AGENTS.md ni CLAUDE.md.\n"
    out = ["| Où | Règle | Depuis | Âge (j) | Garde-fou | Pourquoi |", "|---|---|---|---|---|---|"]
    for r in rows:
        text = r["text"] if len(r["text"]) <= 70 else r["text"][:67] + "…"
        since = "?" if not r["since"] else r["since"] + ("" if r["since_source"] == "rule" else " (git)")
        guard = "oui" if r["guarded"] else ("non, marquée" if r["marked_unguarded"] else "non")
        out.append(f"| {r['file']}:{r['line']} | {text.replace('|', '/')} | {since} | "
                   f"{'?' if r['age_days'] is None else r['age_days']} | {guard} | {'oui' if r['justified'] else 'non'} |")
    dated = sum(1 for r in rows if r["since_source"] == "rule")
    out += ["", f"{len(rows)} règle(s), {dated} datée(s) dans le texte, "
                f"{sum(1 for r in rows if r['guarded'])} avec garde-fou, {sum(1 for r in rows if r['justified'])} justifiée(s)."]
    return "\n".join(out) + "\n"


def build_parser(parser: argparse.ArgumentParser | None = None) -> argparse.ArgumentParser:
    p = parser or argparse.ArgumentParser(description=__doc__)
    p.add_argument("repo", nargs="?", default=".", help="chemin du dépôt (défaut : .)")
    p.add_argument("--format", choices=["md", "json"], default="md")
    p.add_argument("--no-blame", action="store_true", help="ne pas interroger git pour les règles sans date")
    p.add_argument("--today", help="AAAA-MM-JJ, pour des sorties reproductibles")
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
