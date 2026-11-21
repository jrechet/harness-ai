"""`status` subcommand: collects the facts, evaluates maturity, writes
`.harness/state.json` and prints a Markdown summary or the JSON."""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date

from . import facts, maturity, page


def build_parser(parser: argparse.ArgumentParser | None = None) -> argparse.ArgumentParser:
    p = parser or argparse.ArgumentParser(description=__doc__)
    p.add_argument("repo", nargs="?", default=".", help="repository path (default: .)")
    p.add_argument("--harness-dir", default=".harness", help="folder of the skills' outputs (default: .harness)")
    p.add_argument("--audit", help="audit JSON to use (default: <harness-dir>/audit.json)")
    p.add_argument("--harvest", help="harvest JSON to use (default: <harness-dir>/harvest.json)")
    p.add_argument("--format", choices=["md", "json"], default="md")
    p.add_argument("--map", action="store_true",
                   help="prints only the short plain-words map of the levels (what the skills show first)")
    p.add_argument("--page", metavar="FILE",
                   help="also writes the interactive HTML page: the files of today, the steps to the target, the medals")
    p.add_argument("--no-write", action="store_true", help="does not write <harness-dir>/state.json")
    p.add_argument("--today", help="YYYY-MM-DD, for reproducible outputs")
    return p


TARGET_LEVELS = (1, 2, 3, 4)
DELEGATED_LEVEL = 4
CLEAR_WORD = "none"


def _level_or_path(value: str) -> int | str:
    """The first argument of `target`: a level, the word that clears it, or a repository path."""
    if value.isdigit() and int(value) in TARGET_LEVELS:
        return int(value)
    if value.lower() == CLEAR_WORD:
        return CLEAR_WORD
    if os.path.isdir(value):
        return value
    raise argparse.ArgumentTypeError(
        f"{value!r} is not a level (1 to 4), '{CLEAR_WORD}' (clears the target) or the path of a repository")


def build_target_parser(parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
    parser.add_argument("level", nargs="?", type=_level_or_path, metavar=f"{{1,2,3,4,{CLEAR_WORD}}}",
                        help=f"target level, or '{CLEAR_WORD}' to clear it; omitted: shows the target")
    parser.add_argument("repo", nargs="?", default=".", help="repository path (default: .)")
    parser.add_argument("--harness-dir", default=".harness")
    return parser


def _write_config(path: str, config: dict) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(config, fh, ensure_ascii=False, indent=2)
        fh.write("\n")


def _warn_if_delegated_in_assistance(repo: str, level: int | None) -> None:
    """Level 4 is delegation: in assistance mode it is not a target. Said, not refused."""
    if level != DELEGATED_LEVEL or facts.instruction_facts(repo)["source"].get("mode") != "assistance":
        return
    print(f"warning: level {DELEGATED_LEVEL} ({maturity.LEVELS[DELEGATED_LEVEL][1]}) is not a target in assistance mode: "
          "it only counts once the team switches to delegation", file=sys.stderr)


def target_main(args: argparse.Namespace) -> int:
    """Shows, writes or clears the target level of `<harness-dir>/config.json`: beyond it, `status` proposes nothing."""
    level, repo = args.level, args.repo
    if isinstance(level, str) and level != CLEAR_WORD:  # a single path: shows the target of that repository
        if repo != ".":
            print(f"harness target: {level} is a path, not a level: give a level (1 to 4) or '{CLEAR_WORD}' "
                  "before the repository, or the repository alone", file=sys.stderr)
            return 2
        level, repo = None, level
    repo = os.path.abspath(repo)
    hdir = os.path.join(repo, args.harness_dir)
    path = os.path.join(hdir, "config.json")
    if level is None:
        current = facts.config_facts(hdir)["target_level"]
        print(f"target level: {current}" if current else "no target level")
        _warn_if_delegated_in_assistance(repo, current)
        return 0
    config = facts.load_json(path) or {"schema": "harness-config/1"}
    if level == CLEAR_WORD:
        if "target_level" not in config:
            print("no target level (nothing to clear)")
            return 0
        _write_config(path, {key: value for key, value in config.items() if key != "target_level"})
        print(f"no target level (cleared in {os.path.relpath(path)})")
        return 0
    _write_config(path, {**config, "target_level": level})
    print(f"target level: {level} · {maturity.LEVELS[level][1]} (written to {os.path.relpath(path)})")
    _warn_if_delegated_in_assistance(repo, level)
    return 0


def main(argv: list[str] | None = None, args: argparse.Namespace | None = None) -> int:
    if args is None:
        args = build_parser().parse_args(argv)
    today = date.fromisoformat(args.today) if args.today else None
    f = facts.collect(args.repo, args.harness_dir, args.audit, args.harvest, today)
    state = maturity.evaluate(f)
    if not args.no_write:
        out_dir = os.path.join(os.path.abspath(args.repo), args.harness_dir)
        os.makedirs(out_dir, exist_ok=True)
        with open(os.path.join(out_dir, "state.json"), "w", encoding="utf-8") as fh:
            json.dump(state, fh, ensure_ascii=False, indent=2)
            fh.write("\n")
    if args.page:
        try:
            page.write(args.page, page.build(args.repo, args.harness_dir, args.audit, args.harvest, today))
        except (OSError, UnicodeError) as exc:
            print(f"harness status: the page could not be written to {args.page}: {exc}", file=sys.stderr)
            return 2
        print(f"page written: {args.page}", file=sys.stderr)
    if args.map:
        sys.stdout.write(maturity.render_map(state))
    elif args.format == "json":
        json.dump(state, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
    else:
        sys.stdout.write(maturity.render_markdown(state))
    return 0
