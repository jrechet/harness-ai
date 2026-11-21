"""The answer keys are not changed together with what they grade.

Whoever corrects both the paper and the answer key always raises the grade. This module lists, without a
model, what a branch changes compared with its base, and refuses the change when it touches both sides:

- the answer key: a fixture's `expected.json`, `traps.md` or `tasks/`, the fixture grader
  (`cli/harnesslib/fixtures.py`) or a `*grade.py`;
- what is graded: a skill (`skills/`, `plugins/ai-sdlc/skills/`), a `runs/` folder, `fixtures/results.jsonl`.

Each side may change alone. Both together pass only when a row of the progress plan added or edited by the
same change carries the marker `owner-agreed: answer key`: the agreement is then written where the review
reads it. The marker does not prove the agreement, it makes the claim visible."""
from __future__ import annotations

import argparse
import os
import sys

from . import progress

MARKER = "owner-agreed: answer key"
GRADER = "cli/harnesslib/fixtures.py"
RESULTS = "fixtures/results.jsonl"
KEY_NAMES = ("expected.json", "traps.md")
SKILL_ROOTS = ("skills/", "plugins/ai-sdlc/skills/")
SHOWN = 4


def _is_run(path: str) -> bool:
    return "runs" in path.split("/")[:-1]


def is_key(path: str) -> bool:
    """An answer key or a grader. A run keeps copies of what it was graded with: they are not the key."""
    if _is_run(path):
        return False
    parts = path.split("/")
    name = parts[-1]
    if path == GRADER or (name.endswith("grade.py") and not name.startswith("test_")):
        return True
    if parts[0] != "fixtures" or len(parts) < 3:
        return False
    return name in KEY_NAMES or "tasks" in parts[1:-1]


def is_graded(path: str) -> bool:
    """What an answer key grades: a skill, the record of a run, the results file."""
    return path == RESULTS or path.startswith(SKILL_ROOTS) or _is_run(path)


def _plan_rows(text: str) -> list[str]:
    """The lines of the plan table that are rows with an id, as written."""
    heading = next((h for h in (progress.HEADING, *progress.LEGACY_HEADINGS) if h in text), None)
    if heading is None:
        return []
    section = text.split(heading, 1)[1].split("\n## ", 1)[0]
    rows = []
    for line in section.splitlines():
        line = line.strip()
        if line.startswith("|") and progress._ID.match(line.strip("|").split("|")[0].strip()):
            rows.append(line)
    return rows


def agreed(repo: str, base: str, doc: str | None = None) -> bool:
    """True if a plan row added or edited since the base carries the marker."""
    doc = doc or progress.default_doc(repo)
    try:
        with open(os.path.join(repo, doc), encoding="utf-8") as fh:
            now = _plan_rows(fh.read())
    except OSError:
        return False
    code, fork = progress._git(repo, "merge-base", base, "HEAD")
    code, before = progress._git(repo, "show", f"{fork.strip() if code == 0 and fork.strip() else base}:{doc}")
    known = set(_plan_rows(before)) if code == 0 else set()
    return any(MARKER in row for row in now if row not in known)


def _sample(paths: list[str]) -> str:
    return ", ".join(paths[:SHOWN]) + (f" and {len(paths) - SHOWN} more" if len(paths) > SHOWN else "")


def check(repo: str, base: str = "origin/main", doc: str | None = None) -> list[str]:
    """What refuses the change: an empty list if it does not touch both the answer key and what it grades."""
    code, _ = progress._git(repo, "rev-parse", "--verify", "--quiet", f"{base}^{{commit}}")
    if code != 0:
        return [f"the base {base} is not a commit of this repository: the changed files cannot be listed"]
    changed = progress.changed_paths(repo, base)
    if changed is None:
        return ["not a git repository: the changed files cannot be listed"]
    key_side = sorted(p for p in changed if is_key(p))
    graded_side = sorted(p for p in changed if is_graded(p))
    if not key_side or not graded_side or agreed(repo, base, doc):
        return []
    return [f"the change touches the answer key ({_sample(key_side)}) together with what it grades "
            f"({_sample(graded_side)}): split it in two pull requests, or, if the owner agreed, write "
            f"\"{MARKER}\" in the row of this change in the progress plan"]


def build_parser(parser: argparse.ArgumentParser | None = None) -> argparse.ArgumentParser:
    p = parser or argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="keys_command", required=True)
    chk = sub.add_parser("check", help="the change does not touch both an answer key and what it grades")
    chk.add_argument("repo", nargs="?", default=".")
    chk.add_argument("--base", default="origin/main")
    chk.add_argument("--doc", default=None, help="the progress plan where the marker is read")
    return p


def main(argv: list[str] | None = None, args: argparse.Namespace | None = None) -> int:
    args = args or build_parser().parse_args(argv)
    errors = check(args.repo, args.base, args.doc)
    if not errors:
        print("Answer keys: not changed together with a skill, a run or the results.")
        return 0
    print("Answer key guard:\n- " + "\n- ".join(errors), file=sys.stderr)
    return 2
