"""The command line of `harness flow`: what a person types and reads. The rules are in flow.py,
the placement in flow_place.py, the verdict of `flow fit` in flow_fit.py; nothing here decides anything.

What a command answers goes to the standard output, in the form the contract fixes
(docs/workflow-harness/flow-spec.md, section 4). What helps a person go on (where a run really
stops, which command comes next) goes to the standard error, one sentence per line, and only
with `--format md`: a program that reads the JSON document gets the document alone."""
from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any

from . import flow, flow_fit, flow_notes, flow_paths

FORMAT_PAGE = "the page flow-format.md"
EVENT_EXAMPLE = '{"id": "T-12:triage:1:ticket_ready", "type": "ticket_ready", "payload": {"dollars": 0, "minutes": 1}}'
STOPS_HERE = "   ← as written, a run stops here on purpose"
HELP_WIDTH = 78  # the width argparse takes when no terminal is there: the help is the same bytes everywhere
CLOSING_HELP = flow_notes.HELP_LAST


def RAW(prog: str) -> argparse.HelpFormatter:  # noqa: N802 - it stands where a formatter class is expected
    """The help as written, wrapped at a fixed width, whatever the terminal."""
    return argparse.RawDescriptionHelpFormatter(prog, width=HELP_WIDTH)


IN_ORDER = f"""In order:
  0. flow fit <answers.json>       before any definition: is a flow needed, and which tool? flow fit --questions
                                   lists the answers to record
  1. flow new feature|bug          writes a starting definition, .harness/flow/<kind>.json
  2. edit that file                every key, and a step of each type to paste: {FORMAT_PAGE}
  3. flow check <file>             refuses a flow that could loop, wait or spend without end, and says what to edit
  4. flow place <file>             where each step belongs; the page decide.md explains the answers
  5. flow status <file> --map      the level reached on paper, and the next step
  6. flow next <file> --event <event.json> --new
                                   tries the flow by hand, one event at a time; nothing is run

Every command takes --format json. Exit codes: 0 fine, 1 refused or failing, 2 wrong usage or unreadable file.
{CLOSING_HELP}"""

NEXT_HELP = f"""The event file is one JSON object:
  {EVENT_EXAMPLE}
  "id"       names the fact: ticket, step, round, what happened. A fact delivered twice carries the same id
             and is counted once.
  "type"     what happened: an event the step lists under "on", or human_stop, deadline_passed, step_failed.
  "payload"  what the step cost. Needed when a program or an agent step ends; 0 is a cost.
  "at"       {{"state": "<step>", "visit": <n>}}: the step and the round the event answers.
             Needed for deadline_passed and step_failed.

One ticket, event after event:
  flow next flow.json --event e1.json --new --save-run run.json
  flow next flow.json --event e2.json --run run.json --save-run run.json

Nothing is run and no clock is read: the command only says what the run does on that event.
The format of a definition and of an event: {FORMAT_PAGE}.
{CLOSING_HELP}"""


def build_parser(parser: argparse.ArgumentParser | None = None) -> argparse.ArgumentParser:
    p = parser or argparse.ArgumentParser(description=flow.__doc__)
    p.formatter_class, p.epilog = RAW, IN_ORDER
    sub = p.add_subparsers(dest="flow_command", required=True)
    fit = sub.add_parser("fit", help="before any definition: is a flow needed at all, and which tool",
                         formatter_class=RAW,
                         epilog="The answers are yours: nothing is measured here. A missing or unknown answer is "
                                "refused, never guessed.\nThe rules: the page flow-spec.md, section 11.\n"
                                + CLOSING_HELP)
    flow_fit.add_arguments(fit)
    new_ = sub.add_parser("new", help="writes a starting definition from a template", formatter_class=RAW,
                          epilog=f"Then edit the file: every key is explained in {FORMAT_PAGE}.\n{CLOSING_HELP}")
    new_.add_argument("kind", choices=flow.TEMPLATES, help="the kind of ticket the flow is for")
    new_.add_argument("--out", metavar="FILE", help="where to write it (default: .harness/flow/<kind>.json)")
    new_.add_argument("--force", action="store_true", help="replaces the file if it exists")
    chk = sub.add_parser("check", help="refuses a flow that could loop, wait or spend without end",
                         formatter_class=RAW,
                         epilog=f"Each problem ends with the key to write. Every key is explained in {FORMAT_PAGE}.\n"
                                f"The placement of the steps is another question: flow place <file>.\n{CLOSING_HELP}")
    plc = sub.add_parser("place", help="where each step belongs, and whether one needs an engine",
                         formatter_class=RAW,
                         epilog="It places what it finds and does not run flow check. The questions and the places "
                                f"are explained in\nthe page decide.md.\n{CLOSING_HELP}")
    sts = sub.add_parser("status", help="the level this flow has reached, on paper", formatter_class=RAW,
                         epilog=f"The levels, and what each one needs: the page flow-spec.md, section 7.\n{CLOSING_HELP}")
    nxt = sub.add_parser("next", help="what one run does on one event", formatter_class=RAW, epilog=NEXT_HELP)
    for sp in (chk, nxt, plc, sts):
        sp.add_argument("file", help="the flow definition, a JSON file")
    nxt.add_argument("--event", required=True, metavar="FILE", help="the event, a JSON file (shown below)")
    nxt.add_argument("--run", metavar="FILE",
                     help='the run this ticket is in: the "run" part of the answer to the event before, '
                          "as --save-run writes it")
    nxt.add_argument("--new", action="store_true", help="the first event of a ticket: the run starts here")
    nxt.add_argument("--save-run", metavar="FILE",
                     help='writes the "run" part of the answer to FILE, ready for --run with the next event')
    sts.add_argument("--map", action="store_true",
                     help="the levels in plain words, each reason this flow is not at the next one, and the next step")
    for sp in (plc, sts):
        sp.add_argument("--answers", metavar="FILE",
                        help="the answers file of flow fit: the symptoms measured on the runs of this flow are read "
                             "beside it")
    for sp in (fit, new_, chk, nxt, plc, sts):
        sp.add_argument("--format", choices=["md", "json"], default="md")
    return p


def _emit(fmt: str, data: Any, markdown: str) -> None:
    if fmt == "json":
        json.dump(data, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
    else:
        sys.stdout.write(markdown)


def _note(fmt: str, *sentences: str) -> None:
    """What helps a person go on: on the standard error, and never beside a JSON document."""
    if fmt == "md":
        sys.stdout.flush()  # so that a note never comes before the answer it follows
        for sentence in sentences:
            if sentence:
                print(sentence, file=sys.stderr)


def _listed(names: list[str], last: str = "or") -> str:
    return names[0] if len(names) == 1 else f"{', '.join(names[:-1])} {last} {names[-1]}"


def _stop_sentence(definition: Any, named: bool = True) -> str:
    """Where a run of this flow really stops, and what the file describes that is never run."""
    after, beyond = flow.stop_steps(definition), flow.beyond_stop(definition)
    if not after:
        return ""
    stop_at, states = definition["stop_at"], definition["states"]
    sentence = (f'As written, a run stops on purpose after {_listed(after)}: the stop point "{stop_at}" '
                f"(stop_at) is the name its transition reaches, not a step.")
    if not beyond:
        return sentence
    count = "The 1 step after it is" if len(beyond) == 1 else f"The {len(beyond)} steps after it are"
    sentence += f" {count} described but not run" + (f": {', '.join(beyond)}." if named else ".")
    further = []
    for name in beyond:
        for transition in states[name]["on"].values():
            reaches = transition.get("reaches")
            if reaches and reaches != stop_at and transition["to"] != "stopped" and reaches not in further:
                further.append(reaches)
    return sentence + (f" To go further, set stop_at to {_listed(further)}." if further else "")


def _waiting(definition: Any) -> list[str]:
    """The gates that wait for their judge; none said when the placement is not installed."""
    try:
        return flow._placement_module().waiting(definition)
    except ImportError:
        return []


def _steps_md(definition: dict[str, Any]) -> str:
    stops = flow.stop_steps(definition)
    return "".join(f"- {name} ({flow.TYPE_WORDS.get(state['type'], state['type'])}): {state['does']}"
                   f"{STOPS_HERE if name in stops else ''}\n" for name, state in definition["states"].items())


def _new_command(args: argparse.Namespace) -> int:
    path = args.out or os.path.join(".harness", "flow", f"{args.kind}.json")
    if os.path.exists(path) and not args.force:
        if args.format == "json":  # a program gets a document, and stderr stays empty (section 12.4)
            _emit(args.format, {"file": path, "written": False, "reason": "exists"}, "")
        else:
            print(f"flow: {path} already exists and was left as it is. Add --force to replace it.", file=sys.stderr)
        return 1
    definition = flow.new(args.kind)
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(definition, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    _emit(args.format, {"file": path, "definition": definition}, f"Written: {path}\n" + _steps_md(definition))
    _note(args.format, _stop_sentence(definition, named=False),
          flow_notes.waiting(definition, _waiting(definition)), flow_notes.new_next(path))
    return 0


def _emit_check(fmt: str, path: str, definition: Any, problems: list[dict[str, str]]) -> None:
    bounds = None if problems else flow_paths.bounds(definition)
    if problems:
        markdown = "".join(f"- {p['message']}" + (f" ({p['where']})\n" if p["where"] else "\n") for p in problems)
    else:
        budget = definition["budget"]
        markdown = (f"This flow holds: {len(definition['states'])} steps, it stops at {definition['stop_at']}, "
                    f"one ticket may cost up to {flow._show(budget['dollars'])} dollars and "
                    f"{flow._show(budget['minutes'])} minutes.\n" + flow_paths.render_bounds(bounds))
    _emit(fmt, {"file": path, "passed": not problems, "problems": problems, "bounds": bounds}, markdown)


def _placement(definition: Any) -> dict[str, Any] | None:
    """The `place` document of this definition; None when the placement cannot be asked."""
    try:
        return flow._placement_module().place(definition)
    except (ImportError, ValueError):
        return None


def _check_command(args: argparse.Namespace, definition: Any) -> int:
    problems = flow.check(definition)
    _emit_check(args.format, args.file, definition, problems)
    if problems or args.format != "md":
        return 1 if problems else 0
    placement, careful, then = _placement(definition), "", ""
    gates = _waiting(definition) if placement is not None else []
    if placement is not None and placement["passed"]:
        then = (f"Next: flow place {flow_notes.q(args.file)} says where each step belongs. This command does not look "
                "at that.")
    elif placement is not None and flow._placement_module().only_waiting(placement, gates):
        then = flow_notes.check_next_waiting(args.file)
    elif placement is not None:
        careful = (f"Careful: flow place {flow_notes.q(args.file)} does not pass on this file (a step without a place, "
                   "or a gate nobody can judge). This command does not look at the placement; flow status needs both.")
    _note(args.format, _stop_sentence(definition), flow_notes.waiting(definition, gates), careful,
          flow_notes.CANNOT_SEE, then)
    return 0


def _next_md(answer: dict[str, Any]) -> str:
    run, left = answer["run"], answer["remaining"]
    if left is None:
        return answer["message"] + "\n"
    show = flow._show
    return (f"{answer['message']}\nState: {run['state']}. Spent: {show(run['spent']['dollars'])} dollars, "
            f"{show(run['spent']['minutes'])} minutes. Left: {show(left['dollars'])} dollars, "
            f"{show(left['minutes'])} minutes.\n")


def _save_run(path: str, run: Any) -> None:
    try:
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(run, fh, ensure_ascii=False, indent=2)
            fh.write("\n")
    except OSError as exc:
        raise ValueError(f"{path}: the run cannot be written ({exc.strerror or exc})") from exc


def _next_command(args: argparse.Namespace, definition: Any) -> int:
    if bool(args.run) == bool(args.new):
        raise ValueError('give exactly one of --run FILE (the "run" part of the answer to the event before, as '
                         "--save-run writes it) and --new (the first event of a ticket)")
    event = flow.load_definition(args.event)
    given = flow.load_definition(args.run) if args.run else None
    problems = flow.check(definition)
    if problems:
        _emit_check(args.format, args.file, definition, problems)
        return 2
    answer = flow.next_state(definition, flow.new_run(definition) if args.new else given, event)
    run = answer["run"]
    if args.save_run:
        _save_run(args.save_run, run)
    if isinstance(given, dict) and "state" not in given and isinstance(given.get("run"), dict):
        print(f'flow: {args.run} holds a whole answer of flow next, not a run: give back only its "run" part, '
              "which --save-run FILE writes for you.", file=sys.stderr)
    _emit(args.format, answer, _next_md(answer))
    alive = isinstance(run, dict) and run.get("state") not in flow.ENDED
    if args.save_run:
        _note(args.format, f"Run saved: {args.save_run}. " + (
            f"Next event: flow next {flow_notes.q(args.file)} --event <event.json> --run {flow_notes.q(args.save_run)} "
            f"--save-run {flow_notes.q(args.save_run)}" if alive else "This run has ended: no later event moves it."))
    elif args.new and answer["outcome"] == "moved":
        _note(args.format, "This run was not saved. To send the next event, run this command again with "
                           "--save-run run.json, then pass --run run.json --save-run run.json with each event.")
    return 1 if answer["outcome"] in ("refused", "stopped") else 0


def _last_gate(definition: Any, found: dict[str, Any] | None) -> list[str]:
    """The "Careful:" notes of section 12.2: a gate to remove that is the last one before a write."""
    placement = _placement(definition) if found else None
    return flow_notes.last_gate(definition, placement["refused_gates"], found) if placement else []


def _measured(args: argparse.Namespace) -> dict[str, Any] | None:
    """What the answers given with --answers say of the runs, or None without the option.
    Raises ValueError (exit 2) for answers that cannot be read, that flow fit refuses, or that
    describe something else than a ticket workflow."""
    if not args.answers:
        return None
    return flow_fit.measured(flow_fit.read_answers(args.answers), args.answers, args.file)


def _place_command(args: argparse.Namespace) -> int:
    measured = _measured(args)  # answers that cannot be read stop here, before anything is printed
    argv = [args.file, "--format", args.format] + (["--answers", args.answers] if args.answers else [])
    module = flow._placement_module()
    code = module.main(argv)
    if code == 2 or args.format != "md":
        return code
    try:
        definition = flow.load_definition(args.file)
    except ValueError:
        return code
    problems, placement = flow.check(definition), module.place(definition)
    gates = module.waiting(definition)
    careful, then = "", ""
    if problems:
        count = "1 problem" if len(problems) == 1 else f"{len(problems)} problems"
        careful = (f"Careful: flow check {flow_notes.q(args.file)} finds {count} in this file, so this placement is "
                   "provisional: this command places the steps it finds and does not look at the rest.")
    elif code == 0:
        then = f"Next: flow status {flow_notes.q(args.file)} --map{flow_notes.with_answers(args.answers)}"
    elif module.only_waiting(placement, gates):
        then = flow_notes.place_next_waiting(args.file, args.answers)
    _note(args.format, flow_notes.waiting(definition, gates), careful,
          *_last_gate(definition, None if problems else flow_paths.bounds(definition)),
          flow_notes.symptoms_read(args.answers, measured), then)
    return code


def _status_command(args: argparse.Namespace, definition: Any) -> int:
    measured = _measured(args)
    state = flow.status(definition, measured=measured)
    _emit(args.format, state, flow.render_map(state) if args.map else flow.render_status(state))
    read = flow_notes.symptoms_read(args.answers, measured)
    if state["level"]["reached"] == 0:
        _note(args.format, flow_notes.waiting(definition, state["waiting"]),
              *_last_gate(definition, state["bounds"]), read)
        if not args.map:
            _note(args.format, f"Next step: {state['next_step']}",
                  f"Every reason, and the levels: flow status {flow_notes.q(args.file)} --map"
                  f"{flow_notes.with_answers(args.answers)}")
    else:
        _note(args.format, _stop_sentence(definition), read,
              "To try this flow by hand, one event at a time: "
              f"flow next {flow_notes.q(args.file)} --event <event.json> --new "
              "(flow next --help shows an event).")
    return 0


def _fit_command(args: argparse.Namespace) -> int:
    code, document = flow_fit.command(args)
    if args.questions:
        return code
    if not document["passed"]:
        _note(args.format, "The questions and the allowed values: flow fit --questions")
    elif document["verdict"]["code"] == "ticket_state_and_ci":
        _note(args.format, flow_notes.fit_next(os.path.abspath(os.getcwd())))
    elif document["verdict"]["code"] == "symptom" and args.file != "-":
        _note(args.format, flow_notes.fit_next_symptom(args.file))
    return code


def _command(args: argparse.Namespace) -> int:
    if args.flow_command == "fit":
        return _fit_command(args)
    if args.flow_command == "new":
        return _new_command(args)
    if args.flow_command == "place":
        return _place_command(args)
    definition = flow.load_definition(args.file)
    if args.flow_command == "next":
        return _next_command(args, definition)
    if args.flow_command == "check":
        return _check_command(args, definition)
    return _status_command(args, definition)


def main(argv: list[str] | None = None, args: argparse.Namespace | None = None) -> int:
    if args is None:
        args = build_parser().parse_args(argv)
    try:
        code = _command(args)
    except ModuleNotFoundError as exc:
        if not (exc.name or "").endswith("flow_place"):
            raise
        print("flow: the placement of steps (flow_place.py) is not installed with this version", file=sys.stderr)
        return 2
    except (ValueError, OSError) as exc:
        print(f"flow: {exc}", file=sys.stderr)
        return 2
    if code in (0, 1):
        _note(args.format, flow_notes.closing())  # after every other line of stderr, never on exit 2
    return code
