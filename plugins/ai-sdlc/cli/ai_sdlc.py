#!/usr/bin/env python3
"""CLI of the ai-sdlc plugin: the deterministic logic its skills call.

  ai_sdlc.py context <phase> [repo] [--base REF]   the base and the team's additions, with their provenance
  ai_sdlc.py status [repo] [--base REF]            the extension points: convention, overridden, invalid
  ai_sdlc.py review render <review.json> [repo] [--base REF]   the rendered review, if each finding quotes the diff
  ai_sdlc.py size [repo] [--base REF] [--paths P…]  the size of the change and the path it imposes
  ai_sdlc.py dev body <body.json> [repo] [--base REF]         the PR body, if it is complete for its size
  ai_sdlc.py ticket check <ticket.md> [repo] [--base REF]     is the ticket ready to hand to an agent
  ai_sdlc.py ticket render <opinion.json> [repo] --ticket <ticket.md> [--base REF]   the skill's opinion, if well formed
  ai_sdlc.py qa gate [repo] [--base REF] [--run CMD] [--coverage F] [--ticket F --trace F]   the gates of /qa
  ai_sdlc.py secu gate [repo] [--base REF] [--report SARIF…]   the gates of /secu
  ai_sdlc.py ship check [repo] [--base REF] [--since REF] [--checks checks.json]   the prerequisites of a delivery
  ai_sdlc.py ship render <proposal.json> [repo] [--base REF] [--checks checks.json]   the delivery proposal, if it holds
  ai_sdlc.py run changes [repo] --since REF [--until REF]   what shipped between two versions
  ai_sdlc.py run render <investigation.json> [repo] [--base REF] [--evidence file…]   the investigation of an incident, rendered as a ticket
  ai_sdlc.py ci pr [repo] [--base REF] [--coverage F] [--report SARIF…] [--strict]   the gates of a pull request, for a pipeline
  ai_sdlc.py guard check <command>   says whether a shell command delivers (tag, publish, deploy): 0 no, 1 yes
  ai_sdlc.py guard hook   the same check, as the plugin's PreToolUse hook (cli/guard_hook.py) does it: 2 refuses
  ai_sdlc.py fixture init <fixture> <dest>         mounts a trapped PR of fixtures/review as a git repository
  ai_sdlc.py fixture grade <review.json> --expected <expected.json>   grades a review against its answer key
  ai_sdlc.py fixture grade-dev <repo> --task <ticket folder> [--body body.json]   grades a /dev run
  ai_sdlc.py fixture grade-ticket <opinion.json> --task <folder> --repo <repo> --ticket <copy>   grades a /ticket opinion
  ai_sdlc.py fixture grade-secu <review.json> --fixture <fixture> --repo <repo> --out <folder>   grades a /secu run
  ai_sdlc.py fixture grade-ship <repo> --task <folder> --checks <checks.json> [--proposal proposal.json]   grades a /ship run
  ai_sdlc.py fixture grade-run <repo> --fixture <fixture> --investigation <investigation.json> --evidence-dir <evidence> --out <folder>   grades a /run run
  ai_sdlc.py fixture grade-qa <repo> --fixture <fixture> [--trace mapping.json]   grades a /qa run

Exit codes of `context`: 0 served, 2 refused (invalid override, unknown phase or branch): nothing
is printed on standard output, the reason is on standard error. `status` exits 0 and shows an
invalid override in its table: it describes, it does not act as a gate. `review render`: 0 rendered, 2 refused
(incomplete form, finding outside the diff). `ticket check`: 0 ready, 1 not ready, 2 unreadable. `ticket render`: 0 rendered, 2 refused. `qa gate`: 0 the four
gates pass, 1 a gate failed, 3 nothing failed but a gate is unmeasured, 2 refused; `secu gate` and `ship check` follow the same codes. `fixture grade`: 0 compliant, 1 not compliant, 2 unreadable file.

Python 3.10+, standard library only."""
from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from aisdlclib import ci, context, dev, devgrade, guard, points, qa, qagrade, review, run, rungrade, secu, secugrade, ship, shipgrade, size, ticket, ticketgrade  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ai-sdlc", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    ctx = sub.add_parser("context", help="the assembled context of a phase")
    ctx.add_argument("phase")
    ctx.add_argument("--worktree", action="store_true",
                     help="read the overrides in the working tree (local trial, not a gate)")
    status = sub.add_parser("status", help="the state of the extension points")
    rev = sub.add_parser("review", help="the result of a review").add_subparsers(dest="action", required=True)
    render = rev.add_parser("render", help="validates the review and renders it as comments")
    render.add_argument("file")
    sized = sub.add_parser("size", help="the size of the change")
    sized.add_argument("--paths", nargs="+", metavar="PATH",
                       help="before the code: the paths the change plans to touch")
    body = sub.add_parser("dev", help="what /dev guarantees").add_subparsers(dest="action", required=True)
    body = body.add_parser("body", help="validates and renders the PR body")
    body.add_argument("file")
    tck = sub.add_parser("ticket", help="what /ticket measures").add_subparsers(dest="action", required=True)
    opinion = tck.add_parser("render", help="validates the skill's opinion and renders it, measured verdict first")
    opinion.add_argument("file", help="the opinion in JSON: gaps, criteria, split, questions, instructions")
    opinion.add_argument("--ticket", required=True, metavar="FILE", help="the text of the ticket")
    tck = tck.add_parser("check", help="is the ticket ready to hand to an agent")
    tck.add_argument("file", help="the text of the ticket, in Markdown or plain text")
    gate = sub.add_parser("qa", help="what /qa guarantees").add_subparsers(dest="action", required=True)
    gate = gate.add_parser("gate", help="the four gates: disabled, repeated, coverage, criteria")
    gate.add_argument("--run", metavar="CMD", help="the repository's test command, run several times from its root")
    gate.add_argument("--runs", type=int, help="number of runs (default: the base's)")
    gate.add_argument("--coverage", metavar="FILE", help="an lcov or Cobertura report produced on this branch")
    gate.add_argument("--ticket", metavar="FILE", help="the text of the ticket, for its acceptance criteria")
    gate.add_argument("--trace", metavar="FILE", help="the criteria → tests mapping, in JSON")
    sgate = sub.add_parser("secu", help="what /secu guarantees").add_subparsers(dest="action", required=True)
    sgate = sgate.add_parser("gate", help="the four gates: secrets, neutralized, scanner, surface")
    sgate.add_argument("--report", nargs="+", metavar="SARIF", default=[],
                       help="the SARIF reports of the team's scanners, produced on this branch")
    shp = sub.add_parser("ship", help="what /ship checks").add_subparsers(dest="action", required=True)
    shr = shp.add_parser("render", help="validates the skill's proposal and renders it, measured prerequisites first")
    shr.add_argument("file", help="the proposal in JSON: pending, breaking, notes, commands, not_verified, instructions")
    shp = shp.add_parser("check", help="the prerequisites of a delivery, a proposed version and notes")
    for sp in (shp, shr):
        sp.add_argument("--since", metavar="REF", help="the previous version (default: the highest merged X.Y.Z tag)")
        sp.add_argument("--checks", metavar="FILE", help="the CI checks of the commit, in JSON (gh run list --commit … --json …)")
    rn = sub.add_parser("run", help="what /run enforces").add_subparsers(dest="action", required=True)
    rnc = rn.add_parser("changes", help="the commits and sensitive zones between two versions")
    rnc.add_argument("--since", required=True, metavar="REF", help="the version before the incident")
    rnc.add_argument("--until", default="HEAD", metavar="REF", help="the version in production (default: HEAD)")
    rnr = rn.add_parser("render", help="validates the investigation and renders it as a ticket")
    rnr.add_argument("file", help="the investigation in JSON")
    rnr.add_argument("--evidence", nargs="+", default=[], metavar="EVIDENCE", help="the quoted logs and exports, outside the repository")
    cip = sub.add_parser("ci", help="the gates run by a pipeline").add_subparsers(dest="action", required=True)
    cip = cip.add_parser("pr", help="security and tests of a pull request; 1 blocks the merge")
    cip.add_argument("--coverage", metavar="FILE", help="an lcov or Cobertura report produced by the pipeline")
    cip.add_argument("--report", nargs="+", metavar="SARIF", default=[], help="the reports of the scanners run by the pipeline")
    cip.add_argument("--strict", action="store_true", help="an unmeasured gate blocks too")
    for sp in (ctx, status, render, sized, body, tck, opinion, gate, sgate, shp, shr, rnc, rnr, cip):
        sp.add_argument("repo", nargs="?", default=".")
        sp.add_argument("--base", default="origin/HEAD", help="base branch (default: origin/HEAD)")
        sp.add_argument("--format", choices=["md", "json"], default="md")
    grd = sub.add_parser("guard", help="an agent does not deliver").add_subparsers(dest="action", required=True)
    gchk = grd.add_parser("check", help="says whether a shell command tags, publishes or deploys")
    gchk.add_argument("words", nargs="+", metavar="COMMAND", help="the command, as a single quoted argument")
    gchk.add_argument("--repo", default=".", help="the repository whose delivery procedure is read")
    grd.add_parser("hook", help="the PreToolUse hook: reads the tool call in JSON on standard input")
    fix = sub.add_parser("fixture", help="measure the review skill").add_subparsers(dest="action", required=True)
    init = fix.add_parser("init", help="mounts the fixture as a git repository")
    init.add_argument("fixture")
    init.add_argument("dest")
    grade = fix.add_parser("grade", help="grades a review against the answer key")
    grade.add_argument("file")
    grade.add_argument("--expected", required=True)
    gdev = fix.add_parser("grade-dev", help="grades a /dev run in a mounted repository")
    gdev.add_argument("repo")
    gdev.add_argument("--task", required=True, help="the ticket folder in the fixture (expected.json, hidden/)")
    gdev.add_argument("--body", help="the PR body in JSON, as the skill wrote it")
    gtck = fix.add_parser("grade-ticket", help="grades a /ticket opinion against its answer key")
    gtck.add_argument("file", help="the opinion in JSON, as the skill wrote it")
    gtck.add_argument("--task", required=True, help="the ticket folder in the fixture (ticket.md, expected.json)")
    gtck.add_argument("--repo", required=True, help="the mounted repository given to the agent")
    gtck.add_argument("--ticket", required=True, help="the copy of the ticket given to the agent")
    gqa = fix.add_parser("grade-qa", help="grades a /qa run in a mounted repository")
    gqa.add_argument("repo")
    gqa.add_argument("--fixture", required=True, help="the fixture folder (ticket.md, expected.json, hidden/)")
    gqa.add_argument("--trace", help="the criteria → tests mapping, as the skill wrote it")
    gsec = fix.add_parser("grade-secu", help="grades a /secu run: findings, branch untouched, secret not disclosed")
    gsec.add_argument("file", help="the findings in JSON, in the review render format")
    gsec.add_argument("--fixture", required=True, help="the fixture folder (expected.json, pr.json)")
    gsec.add_argument("--repo", required=True, help="the mounted repository given to the agent")
    gsec.add_argument("--out", required=True, help="the folder where the agent wrote its files: the secret's value is searched there")
    gshp = fix.add_parser("grade-ship", help="grades a /ship run: proposal, and nothing shipped")
    gshp.add_argument("repo")
    gshp.add_argument("--task", required=True, help="the task folder in the fixture (expected.json)")
    gshp.add_argument("--checks", required=True, help="the CI checks given to the agent")
    gshp.add_argument("--proposal", help="the proposal in JSON, as the skill wrote it")
    grun = fix.add_parser("grade-run", help="grades a /run run: investigation, nothing touched, secret not disclosed")
    grun.add_argument("repo")
    grun.add_argument("--fixture", required=True, help="the fixture folder (expected.json, evidence/)")
    grun.add_argument("--investigation", required=True, help="the investigation in JSON, as the skill wrote it")
    grun.add_argument("--evidence-dir", required=True, help="the folder of the evidence given to the agent")
    grun.add_argument("--out", required=True, help="the folder where the agent wrote")
    for sp in (init, grade, gdev, gtck, gqa, gsec, gshp, grun):
        sp.add_argument("--format", choices=["md", "json"], default="md")
    return parser


def _fixture(args: argparse.Namespace, table: dict) -> tuple[object, str, int]:
    if args.action == "grade-dev":
        expected = review.load(os.path.join(args.task, "expected.json"))
        result = devgrade.grade(table, expected, args.repo, args.task, args.body)
        return result, devgrade.render_md(result), 0 if result["pass"] else 1
    if args.action == "grade-ticket":
        result = ticketgrade.grade(table, review.load(os.path.join(args.task, "expected.json")), review.load(args.file),
                                   args.task, args.repo, args.ticket)
        return result, devgrade.render_md(result), 0 if result["pass"] else 1
    if args.action == "grade-run":
        result = rungrade.grade(table, review.load(os.path.join(args.fixture, "expected.json")), args.repo, args.fixture,
                                args.investigation, args.evidence_dir, args.out)
        return result, devgrade.render_md(result), 0 if result["pass"] else 1
    if args.action == "grade-ship":
        fixture_dir = os.path.dirname(os.path.dirname(os.path.abspath(args.task)))
        result = shipgrade.grade(table, review.load(os.path.join(args.task, "expected.json")), args.repo, fixture_dir,
                                 args.checks, args.proposal)
        return result, devgrade.render_md(result), 0 if result["pass"] else 1
    if args.action == "grade-secu":
        result = secugrade.grade(review.load(os.path.join(args.fixture, "expected.json")), review.load(args.file), args.file,
                                 args.repo, args.fixture, args.out)
        return result, devgrade.render_md(result), 0 if result["pass"] else 1
    if args.action == "grade-qa":
        result = qagrade.grade(table, review.load(os.path.join(args.fixture, "expected.json")), args.repo, args.fixture,
                               review.load(args.trace) if args.trace else None)
        return result, devgrade.render_md(result), 0 if result["pass"] else 1
    if args.action == "init" and os.path.exists(os.path.join(args.fixture, "ship.json")):
        made = shipgrade.init_ship(args.fixture, args.dest)
        return made, (f"Repository mounted in {made['repo']}: branch {made['branch']}, remote {made['remote']}, "
                      f"CI checks in {made['ci']}.\n"), 0
    if args.action == "init":
        made = review.init_fixture(args.fixture, args.dest)
        return made, f"Repository mounted in {made['repo']}: base {made['base']}, branch {made['branch']}.\n", 0
    expected = review.load(args.expected)
    result = review.grade(expected, review.load(args.file))
    return result, review.render_grade_md(expected, result), 0 if result["pass"] else 1


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "guard":
        if args.action == "hook":
            code, message = guard.run_hook(sys.stdin.read(guard.MAX_STDIN + 1), dict(os.environ))
            sys.stderr.write(message)
            return code
        inside = os.path.isdir(args.repo)
        found = guard.reasons(" ".join(args.words), guard.team_lines(args.repo) if inside else None, guard.tag_names(args.repo) if inside else None)
        sys.stdout.write(guard.render(found) if found else "Nothing in this command tags, publishes or deploys, as far as the guardrail knows.\n")
        return 1 if found else 0
    table = points.load()
    code = 0
    try:
        if args.command == "fixture":
            data, text, code = _fixture(args, table)
        elif args.command == "qa":
            if args.runs is not None and not 1 <= args.runs <= 20:
                raise context.Refused("--runs: between 1 and 20")
            ticket_text = ticket.read(args.ticket) if args.ticket else None
            data = qa.run_gates(table, args.repo, args.base, args.run, args.runs, args.coverage, ticket_text,
                                review.load(args.trace) if args.trace else None)
            text, code = qa.render_md(data), 1 if data["failed"] else (3 if data["unknown"] else 0)
        elif args.command == "ci":
            data = ci.run(table, args.repo, args.base, args.coverage, args.report, args.strict)
            text, code = ci.render_md(data), 0 if data["pass"] else 1
            ci.publish(text, dict(os.environ))
        elif args.command == "run":
            if args.action == "changes":
                data = run.changes(table, args.repo, args.base, args.since, args.until)
                text = run.render_changes(data)
            else:
                data, text = run.investigation(table, args.repo, args.base, review.load(args.file), args.evidence)
        elif args.command == "ship":
            checks = review.load(args.checks) if args.checks else None
            if args.action == "render":
                data, text = ship.proposal(table, args.repo, args.base, args.since, checks, review.load(args.file))
                code = 1 if data["check"]["failed"] else (3 if data["check"]["unknown"] else 0)   # the exit codes of ship check
            else:
                data = ship.check(table, args.repo, args.base, args.since, checks)
                text, code = ship.render_md(data), 1 if data["failed"] else (3 if data["unknown"] else 0)
        elif args.command == "secu":
            data = secu.run_gates(table, args.repo, args.base, args.report)
            text, code = secu.render_md(data), 1 if data["failed"] else (3 if data["unknown"] else 0)
        elif args.command == "ticket":
            source = args.ticket if args.action == "render" else args.file
            text = ticket.read(source)
            zones, warning = ticket.zones_for(table, args.repo, args.base)
            data = {**ticket.check(text, zones), "warning": warning}
            if args.action == "render":
                opinion = review.load(args.file)
                commit = context.resolve_base(args.repo, args.base)
                errors = ticket.check_opinion(opinion, text, lambda rel: context.is_file_at(args.repo, commit, rel))
                if errors:
                    raise context.Refused("opinion refused:\n- " + "\n- ".join(errors))
                data, text = {"opinion": opinion, "check": data}, ticket.render_opinion(opinion, data, warning)
            else:
                text, code = ticket.render_md(data, warning), 0 if data["ready"] else 1
        elif args.command == "size":
            data = size.classify(table, args.repo, args.base, args.paths)
            text = size.render_md(data)
        elif args.command == "dev":
            content, sized = dev.checked(table, review.load(args.file), args.repo, args.base)
            data, text = {"body": content, "size": sized}, dev.render_md(content, sized)
        elif args.command == "review":
            data = review.checked(args.file, args.repo, args.base)
            text = review.render_md(data)
        elif args.command == "context":
            data = context.assemble(table, args.repo, args.phase, args.base, worktree=args.worktree)
            text = context.render_context_md(data)
        else:
            data = context.status(table, args.repo, args.base)
            text = context.render_status_md(data)
    except context.Refused as exc:
        print(f"ai-sdlc: {exc}", file=sys.stderr)
        return 2
    sys.stdout.write(json.dumps(data, ensure_ascii=False, indent=2) + "\n" if args.format == "json" else text)
    return code


if __name__ == "__main__":
    sys.exit(main())
