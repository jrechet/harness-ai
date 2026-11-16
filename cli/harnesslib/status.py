"""`status` subcommand: collects the facts, evaluates maturity, writes
`.harness/state.json` and prints a Markdown summary or the JSON."""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date

from . import facts, maturity


def build_parser(parser: argparse.ArgumentParser | None = None) -> argparse.ArgumentParser:
    p = parser or argparse.ArgumentParser(description=__doc__)
    p.add_argument("repo", nargs="?", default=".", help="repository path (default: .)")
    p.add_argument("--harness-dir", default=".harness", help="folder of the skills' outputs (default: .harness)")
    p.add_argument("--audit", help="audit JSON to use (default: <harness-dir>/audit.json)")
    p.add_argument("--harvest", help="harvest JSON to use (default: <harness-dir>/harvest.json)")
    p.add_argument("--format", choices=["md", "json"], default="md")
    p.add_argument("--map", action="store_true",
                   help="prints only the short plain-words map of the levels (what the skills show first)")
    p.add_argument("--no-write", action="store_true", help="does not write <harness-dir>/state.json")
    p.add_argument("--today", help="YYYY-MM-DD, for reproducible outputs")
    return p


def build_target_parser(parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
    parser.add_argument("level", nargs="?", type=int, choices=[1, 2, 3, 4], help="target level; omitted: shows the target")
    parser.add_argument("repo", nargs="?", default=".", help="repository path (default: .)")
    parser.add_argument("--harness-dir", default=".harness")
    return parser


def target_main(args: argparse.Namespace) -> int:
    """Writes the target level to `<harness-dir>/config.json`: beyond it, `status` proposes nothing."""
    hdir = os.path.join(os.path.abspath(args.repo), args.harness_dir)
    path = os.path.join(hdir, "config.json")
    config = facts.load_json(path) or {"schema": "harness-config/1"}
    if args.level is None:
        current = facts.config_facts(hdir)["target_level"]
        print(f"target level: {current}" if current else "no target level")
        return 0
    config["target_level"] = args.level
    os.makedirs(hdir, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(config, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    print(f"target level: {args.level} · {maturity.LEVELS[args.level][1]} (written to {os.path.relpath(path)})")
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
    if args.map:
        sys.stdout.write(maturity.render_map(state))
    elif args.format == "json":
        json.dump(state, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
    else:
        sys.stdout.write(maturity.render_markdown(state))
    return 0
