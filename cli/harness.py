#!/usr/bin/env python3
"""harness-ai CLI: the deterministic logic (L3) that the skills call.

  harness status [repo]              maturity state, writes .harness/state.json
  harness target <level> [repo]      declares the target level: beyond it, status proposes nothing
  harness rules [repo]               the rules, their date, their guardrail, their justification
  harness harvest github --repo …    GitHub evidence for harness-harvest
  harness harvest check <file>       a harvest file has what `status` needs to count it
  harness audit check <file>         an audit file has what `status` needs to count it
  harness fixture check <name>       compares a fixture with its expected.json
  harness bench …                    the before-and-after bench: plan, prepare, check, selftest, record, report
  harness serve [repo]               local tracking app (http://127.0.0.1:8787)
  harness place grid|one|plan …      where each piece of a harness goes, and why
  harness commands [repo]            the commands an agent does not guess: what the CI really runs
  harness fresh [repo] [--hook|--strict]   what has aged: a skill citing a vanished file, a late harvest
  harness medals [repo] [--write] [--page F]   medal, unlocked achievements, next steps; HTML page
  harness progress check|remind      the progress plan in docs/capabilities.md follows every change
  harness keys check [--base REF]    an answer key or a grader does not change with a skill or a run
  harness report build|from-place …  a one-page HTML assessment, always in the same format

Python 3.10+, standard library only."""
from __future__ import annotations

import argparse
import os
import sys

if sys.version_info < (3, 10):  # before any import: the rest of the CLI does not parse on 3.9
    sys.exit("harness: Python 3.10 or later is required (here %d.%d). Try python3.11 or python3.12." % sys.version_info[:2])

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from harnesslib import bench, commands, fixtures, fresh, github, keys, medals, place, progress, report, rules, serve, shape, status  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="harness", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    status.build_parser(sub.add_parser("status", help="maturity state of the repository"))
    status.build_target_parser(sub.add_parser("target", help="declares or shows the target level"))
    rules.build_parser(sub.add_parser("rules", help="the rules and what is known about them"))
    harvest = sub.add_parser("harvest", help="evidence collection for harness-harvest")
    hsub = harvest.add_subparsers(dest="source", required=True)
    github.build_parser(hsub.add_parser("github", help="GitHub adapter"))
    shape.build_parser(hsub.add_parser("check", help="a harvest file has what status needs to count it"), "harvest")
    audit = sub.add_parser("audit", help="checks on what harness-audit writes")
    asub = audit.add_subparsers(dest="action", required=True)
    shape.build_parser(asub.add_parser("check", help="an audit file has what status needs to count it"), "audit")
    fixtures.build_parser(sub.add_parser("fixture", help="fixture checks"))
    bench.build_parser(sub.add_parser("bench", help="the before-and-after task bench"))
    serve.build_parser(sub.add_parser("serve", help="local tracking app"))
    place.build_parser(sub.add_parser("place", help="where each piece of a harness goes"))
    report.build_parser(sub.add_parser("report", help="a one-page HTML assessment"))
    commands.build_parser(sub.add_parser("commands", help="the commands an agent does not guess"))
    progress.build_parser(sub.add_parser("progress", help="the progress plan follows every change"))
    keys.build_parser(sub.add_parser("keys", help="the answer keys do not change with what they grade"))
    medals.build_parser(sub.add_parser("medals", help="medals and achievements: the maturity level and why"))
    fresh.build_parser(sub.add_parser("fresh", help="what has aged: skills, agents, rules"))
    args = parser.parse_args(argv)
    target = getattr(args, "repo", None)
    if args.command in ("status", "target", "rules", "serve") and isinstance(target, str) and not os.path.isdir(target):
        print(f"harness {args.command}: {target} is not a directory", file=sys.stderr)
        return 2
    if args.command == "status":
        return status.main(args=args)
    if args.command == "target":
        return status.target_main(args)
    if args.command == "rules":
        return rules.main(args=args)
    if args.command == "harvest" and args.source == "github":
        return github.main(args=args)
    if args.command in ("audit", "harvest"):
        return shape.main(args)
    if args.command == "fixture":
        return fixtures.main(args=args)
    if args.command == "bench":
        return bench.main(args=args)
    if args.command == "serve":
        return serve.main(args=args)
    if args.command == "place":
        return place.main(args=args)
    if args.command == "report":
        return report.main(args=args)
    if args.command == "commands":
        return commands.main(args=args)
    if args.command == "progress":
        return progress.main(args=args)
    if args.command == "keys":
        return keys.main(args=args)
    if args.command == "medals":
        return medals.main(args=args)
    if args.command == "fresh":
        return fresh.main(args=args)
    parser.error("unknown command")
    return 2


if __name__ == "__main__":
    sys.exit(main())
