"""`ignore` subcommand: the owner sets a check of the level ladder aside.

The harness has its list of checks, level by level. A team may not want one of them. Saying so writes
the check and the reason in `<harness-dir>/config.json`; from then on `status` reaches the level
without it and never proposes it again. The measure does not move: the check is shown as set aside,
with its reason, never as passed.

  harness ignore [repo]                               every check, its state, what is set aside and why
  harness ignore <check> --reason "…" [--repo PATH]   sets it aside
  harness ignore <check> --restore [--repo PATH]      takes the choice back

The check that an instruction file exists cannot be set aside: without the file nothing is measured.
Exit codes: 0 done, 2 invalid input."""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import date
from typing import Any

from . import facts, maturity

CHECK_ID = re.compile(r"L[1-4]\.[a-z_]+")
CONFIG_SCHEMA = "harness-config/1"
BLOCK = "ignored_checks"


def build_parser(parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
    parser.add_argument("check", nargs="?", help="the id of a check (see the list); a repository path alone lists its checks")
    # An option and not a second positional: argparse refuses a positional given after an option.
    parser.add_argument("--repo", default=".", help="repository path (default: .)")
    parser.add_argument("--reason", help="why the team does not want this check; required to set it aside")
    parser.add_argument("--restore", action="store_true", help="takes the choice back: the check counts again")
    parser.add_argument("--harness-dir", default=".harness")
    parser.add_argument("--format", choices=["md", "json"], default="md")
    return parser


def rows(repo: str, harness_dir: str = ".harness") -> list[dict[str, Any]]:
    """Every check of the ladder as measured today: held, missing, or set aside with its reason."""
    state = maturity.evaluate(facts.collect(repo, harness_dir=harness_dir))
    out = []
    for level in state["levels"]:
        for check in level["checks"]:
            status = "set aside" if check.get("ignored") else "held" if check["passed"] else "missing"
            out.append({"id": check["id"], "level": level["level"], "label": check["label"], "state": status,
                        "reason": check.get("reason"), "can_be_set_aside": check["id"] not in maturity.NOT_IGNORABLE})
    return out


def render(listed: list[dict[str, Any]]) -> str:
    out = ["Checks of the level ladder (set one aside with `harness ignore <id> --reason \"…\"`):", ""]
    for row in listed:
        status = f"set aside: {row['reason']}" if row["state"] == "set aside" else row["state"]
        fixed = "" if row["can_be_set_aside"] else " (cannot be set aside)"
        out.append(f"- {row['id']}: {row['label']} — {status}{fixed}")
    return "\n".join(out) + "\n"


def _write(path: str, config: dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(config, fh, ensure_ascii=False, indent=2)
        fh.write("\n")


def _fail(message: str) -> int:
    print(f"harness ignore: {message}", file=sys.stderr)
    return 2


def main(args: argparse.Namespace) -> int:
    check, repo = args.check, args.repo
    if check is not None and not CHECK_ID.fullmatch(check):       # a path alone: lists that repository
        if repo != "." or args.reason or args.restore:
            return _fail(f"{check} is not the id of a check (for example L1.forbidden); the repository goes in --repo")
        check, repo = None, check
    if not os.path.isdir(repo):
        return _fail(f"{repo} is not a directory")
    repo = os.path.abspath(repo)
    listed = rows(repo, args.harness_dir)
    if check is None:
        if args.format == "json":
            json.dump(listed, sys.stdout, ensure_ascii=False, indent=2)
            sys.stdout.write("\n")
        else:
            sys.stdout.write(render(listed))
        return 0
    known = {row["id"]: row for row in listed}
    if check not in known:
        return _fail(f"{check} is not a check of the ladder ({', '.join(known)})")
    path = os.path.join(repo, args.harness_dir, "config.json")
    config = facts.load_json(path) or {"schema": CONFIG_SCHEMA}
    chosen = dict(config.get(BLOCK)) if isinstance(config.get(BLOCK), dict) else {}
    if args.restore:
        if check not in chosen:
            print(f"{check} was not set aside (nothing to restore)")
            return 0
        rest = {cid: entry for cid, entry in chosen.items() if cid != check}
        _write(path, {**{k: v for k, v in config.items() if k != BLOCK}, **({BLOCK: rest} if rest else {})})
        print(f"{check} counts again: {known[check]['label']} (written to {os.path.relpath(path)})")
        return 0
    if not known[check]["can_be_set_aside"]:
        return _fail(f"{check} cannot be set aside: without an instruction file, nothing is measured")
    reason = (args.reason or "").strip()
    if not reason:
        return _fail("--reason is required: one sentence saying why the team does not want this check")
    _write(path, {**config, BLOCK: {**chosen, check: {"reason": reason, "date": date.today().isoformat()}}})
    print(f"{check} set aside: {known[check]['label']}. Reason: {reason} (written to {os.path.relpath(path)}).\n"
          "The level is now reached without it; the state shows it as set aside, not as passed. "
          f"`harness ignore {check} --restore` takes it back.")
    return 0
