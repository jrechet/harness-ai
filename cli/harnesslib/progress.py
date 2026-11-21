"""The progress plan kept up to date: a change in the repository does not leave without its row.

A progress document that nobody has to keep lies within a week. This module checks two things, without
a model: the document has the expected shape (a date no older than its latest row, a table whose rows
each have a unique id and a known state), and it is part of every change of the branch, with a date
that moved when the plan did. Plugged into an end-of-turn hook, it sends
the agent back to write its row before stopping.

The plan is written in English (`docs/capabilities.md`, `## Progress plan`, `Last updated:`, states
`done`, `in progress`, `to do`, `waiting`, `dropped`). The French form (`docs/capacites.md`,
`## Plan d'avancement`, `Dernière mise à jour :`, `fait`, `en cours`, `à faire`, `en attente`, `écarté`)
is still read, so a plan not yet translated keeps passing."""
from __future__ import annotations

import argparse
import datetime
import json
import os
import re
import subprocess
import sys
from typing import Any

DOC = "docs/capabilities.md"
LEGACY_DOCS = ("docs/capacites.md",)
HEADING = "## Progress plan"
LEGACY_HEADINGS = ("## Plan d'avancement",)
STATES = ("done", "in progress", "to do", "waiting", "dropped")
LEGACY_STATES = ("fait", "en cours", "à faire", "en attente", "écarté")
_DATE = re.compile(r"^(?:Last updated|Dernière mise à jour)\s*:\s*(\d{4}-\d{2}-\d{2})\b", re.MULTILINE)
_ID = re.compile(r"^[A-Z]{1,3}\d{1,3}$")
_DAY = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")
SINCE = ("Since", "Depuis")
SINCE_COLUMN = 3  # where the column sits when the table has no header that names it


def default_doc(repo: str) -> str:
    """The plan of the repository: the English file, or the French one while it is not renamed."""
    for doc in (DOC, *LEGACY_DOCS):
        if os.path.isfile(os.path.join(repo, doc)):
            return doc
    return DOC


def reminder(doc: str = DOC) -> str:
    return (f"Repository reminder: every new request or correction from whoever drives the session, and every piece of "
            f"work finished or started, is recorded in {doc} (section \"Progress plan\": one row per topic, state among "
            f"{', '.join(STATES)}), in the same change.")


def parse(text: str) -> tuple[list[dict[str, str]], list[str]]:
    """The rows of the plan and what is wrong with its shape."""
    errors = []
    updated = last_updated(text)
    if updated is None:
        errors.append("line \"Last updated: YYYY-MM-DD\" missing")
    heading = next((h for h in (HEADING, *LEGACY_HEADINGS) if h in text), None)
    if heading is None:
        return [], errors + [f"section \"{HEADING}\" missing"]
    section = text.split(heading, 1)[1].split("\n## ", 1)[0]
    known = STATES + LEGACY_STATES
    rows, seen = [], set()
    since, latest = SINCE_COLUMN, ("", "")
    for line in section.splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")] if line.strip().startswith("|") else []
        if not rows and any(c in SINCE for c in cells):
            since = next(i for i, c in enumerate(cells) if c in SINCE)
        if len(cells) < 3 or not _ID.match(cells[0]):
            continue
        row = {"id": cells[0], "what": cells[1], "state": cells[2]}
        latest = max([latest] + [(day, row["id"]) for day in _DAY.findall(cells[since] if since < len(cells) else "")])
        if row["id"] in seen:
            errors.append(f"{row['id']}: duplicate id")
        seen.add(row["id"])
        if row["state"] not in known:
            errors.append(f"{row['id']}: unknown state \"{row['state']}\" ({', '.join(STATES)})")
        if not row["what"]:
            errors.append(f"{row['id']}: empty topic")
        rows.append(row)
    if not rows:
        errors.append("no row in the plan (| A1 | topic | state | …)")
    if updated and updated < latest[0]:  # ISO dates sort as text
        errors.append(f"\"Last updated: {updated}\" is older than the latest row ({latest[1]}, since {latest[0]}): "
                      "update the date")
    return rows, errors


def last_updated(text: str) -> str | None:
    """The date the document says it was last updated on, None if the line is missing."""
    found = _DATE.search(text)
    return found.group(1) if found else None


def base_text(repo: str, doc: str, base: str) -> str | None:
    """The plan as the branch found it, under its present or former name; None if the base has none or is unknown."""
    code, fork = _git(repo, "merge-base", base, "HEAD")
    start = fork.strip() if code == 0 and fork.strip() else base
    for name in dict.fromkeys((doc, DOC, *LEGACY_DOCS)):
        code, text = _git(repo, "show", f"{start}:{name}")
        if code == 0:
            return text
    return None


def _git(repo: str, *args: str) -> tuple[int, str]:
    try:
        out = subprocess.run(["git", "-C", repo, "-c", "core.quotepath=false", *args], capture_output=True, timeout=120)
    except (OSError, subprocess.TimeoutExpired):
        return 1, ""
    return out.returncode, out.stdout.decode("utf-8", "replace")


def changed_paths(repo: str, base: str) -> set[str] | None:
    """What the branch and the working tree change compared with the base; None outside a git repository."""
    code, status = _git(repo, "status", "--porcelain", "-z", "--untracked-files=all")
    if code != 0:
        return None
    paths = set()
    entries = status.split("\0")
    index = 0
    while index < len(entries):
        entry = entries[index]
        index += 1
        if len(entry) < 4:
            continue
        paths.add(entry[3:])
        if entry[0] in "RC":  # a rename carries its old name in the next entry
            if index < len(entries):
                paths.add(entries[index])
            index += 1
    code, names = _git(repo, "diff", "--name-only", "-z", "--no-renames", f"{base}...HEAD")
    if code == 0:
        paths |= {p for p in names.split("\0") if p}
    return paths


def check(repo: str, doc: str | None = None, base: str = "origin/main", today: str | None = None) -> list[str]:
    """What prevents stopping here: an empty list if the plan is well formed and follows the change.

    `today` (YYYY-MM-DD, the local day by default) is the day of the change: a plan already dated that
    day may change again without a new date."""
    doc = doc or default_doc(repo)
    try:
        with open(os.path.join(repo, doc), encoding="utf-8") as fh:
            text = fh.read()
    except OSError:
        return [f"{doc} not found: it is the document that says what the repository can do and where it stands"]
    errors = [f"{doc}: {e}" for e in parse(text)[1]]
    changed = changed_paths(repo, base)
    if changed is not None:  # the measured state (.harness/) is a command output, not work to record
        changed = {p for p in changed if not p.startswith(".harness/")}
    if changed is not None and changed - {doc} and doc not in changed:
        sample = ", ".join(sorted(changed - {doc})[:4])
        errors.append(f"the repository changes ({sample}{'…' if len(changed) > 5 else ''}) and {doc} does not move: record "
                      "in the progress plan what is done, started or requested, and update the date")
    updated = last_updated(text)
    if changed is not None and doc in changed and updated and updated < (today or datetime.date.today().isoformat()):
        before = base_text(repo, doc, base)
        if before is not None and before != text and last_updated(before) == updated:
            errors.append(f"{doc}: the plan changes and its \"Last updated\" date did not move ({updated}): "
                          "set it to the day of the change")
    return errors


def build_parser(parser: argparse.ArgumentParser | None = None) -> argparse.ArgumentParser:
    p = parser or argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="progress_command", required=True)
    chk = sub.add_parser("check", help="the plan is well formed and follows the change of the branch")
    chk.add_argument("repo", nargs="?", default=".")
    chk.add_argument("--doc", default=None, help=f"the plan (default: {DOC}, or {LEGACY_DOCS[0]} if only it exists)")
    chk.add_argument("--base", default="origin/main")
    chk.add_argument("--hook", action="store_true",
                     help="called by a Stop hook: reads its JSON on stdin, and does not block twice in a row")
    sub.add_parser("remind", help="the reminder line injected at every request")
    return p


def main(argv: list[str] | None = None, args: argparse.Namespace | None = None) -> int:
    args = args or build_parser().parse_args(argv)
    if args.progress_command == "remind":
        print(reminder(default_doc(".")))  # the hook runs from the project directory
        return 0
    if args.hook:
        try:
            event: Any = json.load(sys.stdin)
        except (ValueError, OSError):
            event = {}
        if isinstance(event, dict) and event.get("stop_hook_active"):
            return 0  # already sent back once this turn: do not lock the agent in a loop
    doc = args.doc or default_doc(args.repo)
    errors = check(args.repo, doc, args.base)
    if not errors:
        if not args.hook:
            print(f"{doc}: well formed, and it follows the change.")
        return 0
    print("Progress plan to update before stopping:\n- " + "\n- ".join(errors), file=sys.stderr)
    return 2
