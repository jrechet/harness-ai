"""`ignore` subcommand: a check of the level ladder is set aside.

The harness has its list of checks, level by level. A team may not want one of them. Saying so writes
the check and the reason in `<harness-dir>/config.json`; from then on `status` reaches the level
without it and never proposes it again. The measure does not move: the check is shown as set aside,
with its reason, never as passed, and the state keeps the level the checks alone give.

  harness ignore [repo]                               every check, its state, what is set aside and why
  harness ignore <check> --reason "…" [--repo PATH]   sets it aside
  harness ignore <check> --restore [--repo PATH]      takes the choice back

The check that an instruction file exists cannot be set aside: without the file nothing is measured.
The command cannot tell who calls it: the choice is whoever wrote the file. It is the owner's to make.
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
LOOKS_LIKE_AN_ID = re.compile(r"[Ll]\d+\.\w+")
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
    """Every check of the ladder as measured today: held, missing, or set aside with its reason. `chosen`
    is the reason written in the file, also when it has no effect today (the check passes, or it comes
    with an instruction file that does not exist yet)."""
    collected = facts.collect(repo, harness_dir=harness_dir)
    chosen = (collected.get("config") or {}).get("ignored_checks") or {}
    out = []
    for level in maturity.evaluate(collected)["levels"]:
        for check in level["checks"]:
            status = "set aside" if check.get("ignored") else "held" if check["passed"] else "missing"
            out.append({"id": check["id"], "level": level["level"], "label": check["label"],
                        "plain": maturity.CHECK_PLAIN[check["id"]][0], "state": status,
                        "reason": check.get("reason"), "chosen": (chosen.get(check["id"]) or {}).get("reason"),
                        "can_be_set_aside": check["id"] not in maturity.NOT_IGNORABLE})
    return out


def render(listed: list[dict[str, Any]]) -> str:
    """Plain words first, as the map says them; the id last, as the handle the command takes."""
    out = ["Checks of the level ladder. To set one aside: `harness ignore <id> --reason \"…\"`.", ""]
    for row in listed:
        if row["state"] == "set aside":
            status = f"set aside: {row['reason']}"
        elif row["chosen"]:
            status = f"{row['state']} (a choice to set it aside is written, without effect today: {row['chosen']})"
        else:
            status = row["state"]
        fixed = "" if row["can_be_set_aside"] else ", cannot be set aside"
        out.append(f"- {row['label']} — {status}{fixed}\n  When missing: {row['plain']}. Id: {row['id']}")
    return "\n".join(out) + "\n"


def _fail(message: str) -> int:
    print(f"harness ignore: {message}", file=sys.stderr)
    return 2


def _read_config(path: str) -> dict[str, Any]:
    """The file as an object; a missing file is a new one. A file that exists and is not a JSON object
    is refused: rewriting it would lose what it holds."""
    if not os.path.exists(path):
        return {"schema": CONFIG_SCHEMA}
    config = facts.load_json(path)
    if not isinstance(config, dict):
        raise ValueError(f"{path} exists and is not a JSON object: fix or remove it, nothing was written")
    return config


def _write(path: str, config: dict[str, Any]) -> None:
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(config, fh, ensure_ascii=False, indent=2)
            fh.write("\n")
    except OSError as exc:
        raise ValueError(f"{path}: {exc}") from exc


def _effect(row: dict[str, Any]) -> str:
    """What the choice changes today, read after writing: never announced, always measured."""
    if row["state"] == "set aside":
        return "Its level no longer waits for it; the state shows it as set aside, not as passed."
    if row["state"] == "held":
        return "The check passes today, so nothing changes; the choice will apply if it stops passing."
    return "No effect today: there is no instruction file yet, and this check comes with it."


def main(args: argparse.Namespace) -> int:
    check, repo = args.check, args.repo
    if check is not None and not CHECK_ID.fullmatch(check):       # a path alone: lists that repository
        if repo != "." or args.reason or args.restore or (LOOKS_LIKE_AN_ID.fullmatch(check) and not os.path.isdir(check)):
            return _fail(f"{check} is not a check of the ladder (ids look like L1.forbidden; "
                         "`harness ignore <repo>` lists them; the repository goes in --repo)")
        check, repo = None, check
    if not os.path.isdir(repo):
        return _fail(f"{repo} is not a directory")
    repo = os.path.abspath(repo)
    shown = os.path.join(args.harness_dir, "config.json")
    path = os.path.join(repo, shown)
    try:
        if check is None:
            listed = rows(repo, args.harness_dir)
            if args.format == "json":
                json.dump(listed, sys.stdout, ensure_ascii=False, indent=2)
                sys.stdout.write("\n")
            else:
                sys.stdout.write(render(listed))
            return 0
        config = _read_config(path)
        chosen = dict(config[BLOCK]) if isinstance(config.get(BLOCK), dict) else {}
        known = {row["id"]: row for row in rows(repo, args.harness_dir)}
        if args.restore:                       # also for an id the ladder no longer has: it is in the file
            if check not in chosen:
                print(f"{check} was not set aside (nothing to restore)")
                return 0
            rest = {cid: entry for cid, entry in chosen.items() if cid != check}
            _write(path, {**{k: v for k, v in config.items() if k != BLOCK}, **({BLOCK: rest} if rest else {})})
            label = known[check]["label"] if check in known else "no longer a check of the ladder"
            print(f"{check} counts again: {label} (written to {shown})")
            return 0
        if check not in known:
            return _fail(f"{check} is not a check of the ladder ({', '.join(known)})")
        if not known[check]["can_be_set_aside"]:
            return _fail(f"{check} cannot be set aside: without an instruction file, nothing is measured")
        reason = (args.reason or "").strip()
        if not reason:
            return _fail("--reason is required: one sentence saying why the team does not want this check")
        _write(path, {**config, BLOCK: {**chosen, check: {"reason": reason, "date": date.today().isoformat()}}})
        after = next(row for row in rows(repo, args.harness_dir) if row["id"] == check)
    except ValueError as exc:
        return _fail(str(exc))
    print(f"{check} recorded as set aside: {after['label']}. Reason: {reason} (written to {shown}).\n"
          f"{_effect(after)} `harness ignore {check} --restore` takes it back.")
    return 0
