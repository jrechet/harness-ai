"""The minimum an audit or a harvest file must carry before `status` counts it.

A box is ticked on what a file says: a file with nothing in it must not tick one. This module checks,
without a model, that `.harness/audit.json` and `.harness/harvest.json` have the shape their skill
writes, and says what is wrong in one line per problem:

- an audit: a dated report, at least one element, each element with its path, its verdict and its
  priority, and a "cut the agent" test that does not pass while the same report lists a process leak;
- a harvest: where it comes from (`source`), since when (`since`), how many PRs it read (`prs_scanned`).

`harness audit check <file>` and `harness harvest check <file>` run it by hand or from a skill;
`harness status` runs it on what it loads and leaves aside a file that fails it."""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from typing import Any, Callable

VERDICTS = ("KEEP", "INLINE", "PUSH_DOWN", "PROMOTE", "MERGE", "SPLIT", "BLOCK", "REMOVE")
PRIORITIES = ("P1", "P2", "P3")
DAY = "%Y-%m-%d"
MAX_ELEMENT_PROBLEMS = 10     # a report with fifty broken elements is said in a few lines
MAX_SAID = 160                # one line: a JSON error or a long value does not flood the status


def _is_day(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    try:
        datetime.strptime(value, DAY)
    except ValueError:
        return False
    return True


def _shown(value: Any) -> str:
    text = json.dumps(value, ensure_ascii=False)
    return text if len(text) <= 40 else text[:37] + "..."


def _element_problem(index: int, element: Any) -> str | None:
    """What one element lacks, in one sentence; None when it has its path, verdict and priority."""
    if not isinstance(element, dict):
        return f"elements[{index}] is not an object"
    wrong = []
    if not (isinstance(element.get("path"), str) and element["path"].strip()):
        wrong.append("has no path")
    if element.get("verdict") not in VERDICTS:
        wrong.append(f"has no verdict among {'|'.join(VERDICTS)} (found {_shown(element.get('verdict'))})")
    if "priority" not in element or not (element["priority"] is None or element["priority"] in PRIORITIES):
        wrong.append(f"has no priority among {'|'.join(PRIORITIES)}|null"
                     + (f" (found {_shown(element['priority'])})" if "priority" in element else ""))
    return f"elements[{index}] " + ", ".join(wrong) if wrong else None


def check_audit(data: Any) -> list[str]:
    """The problems of an audit report, one sentence each; empty when `status` can count it."""
    if not isinstance(data, dict):
        return ["the file is not a JSON object"]
    problems = []
    meta = data.get("audit") if isinstance(data.get("audit"), dict) else {}
    if not _is_day(meta.get("date")):
        problems.append(f"audit.date is not a day written YYYY-MM-DD (found {_shown(meta.get('date'))})")
    cut = meta.get("cut_the_agent_test") if isinstance(meta.get("cut_the_agent_test"), dict) else {}
    if not isinstance(cut.get("passed"), bool):
        problems.append("audit.cut_the_agent_test.passed is not true or false")
    elements = data.get("elements")
    if not isinstance(elements, list) or not elements:
        problems.append("elements is not a list with at least one element")
    else:
        found = [p for p in (_element_problem(i, e) for i, e in enumerate(elements)) if p]
        problems += found[:MAX_ELEMENT_PROBLEMS]
        if len(found) > MAX_ELEMENT_PROBLEMS:
            problems.append(f"{len(found) - MAX_ELEMENT_PROBLEMS} more element(s) lack a path, a verdict or a priority")
    leaks = data.get("process_leaks")
    if not isinstance(leaks, list):
        problems.append("process_leaks is not a list (an empty one when nothing leaks)")
    elif leaks and cut.get("passed") is True:
        problems.append(f"audit.cut_the_agent_test.passed is true while process_leaks lists {len(leaks)} leak(s): "
                        "the test cannot pass while a mandatory step lives only in a prompt")
    return problems


def check_harvest(data: Any) -> list[str]:
    """The problems of a harvest file, one sentence each; empty when `status` can count it."""
    if not isinstance(data, dict):
        return ["the file is not a JSON object"]
    problems = []
    if not (isinstance(data.get("source"), str) and data["source"].strip()):
        problems.append("source does not say where the evidence comes from (\"github\")")
    if not _is_day(data.get("since")):
        problems.append(f"since is not a day written YYYY-MM-DD (found {_shown(data.get('since'))})")
    scanned = data.get("prs_scanned")
    if isinstance(scanned, bool) or not isinstance(scanned, int) or scanned < 0:
        problems.append(f"prs_scanned is not a number of PRs (found {_shown(scanned)})")
    evidence = data.get("evidence", [])
    if not isinstance(evidence, list) or not all(isinstance(e, dict) for e in evidence):
        problems.append("evidence is not a list of objects")
    return problems


def load(path: str) -> tuple[Any, str | None]:
    """The JSON of a file, or why it cannot be read. A file that is not there is (None, None):
    nothing was written yet, there is nothing to say."""
    if not os.path.exists(path):
        return None, None
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh), None
    except (OSError, UnicodeError) as exc:
        return None, _one_line(f"the file cannot be read ({exc.__class__.__name__})")
    except json.JSONDecodeError as exc:
        return None, _one_line(f"not JSON (line {exc.lineno}, column {exc.colno}: {exc.msg})")


def _one_line(text: str) -> str:
    text = " ".join(str(text).split())
    return text if len(text) <= MAX_SAID else text[:MAX_SAID - 3] + "..."


def counted(path: str, check: Callable[[Any], list[str]]) -> tuple[dict | None, str | None]:
    """What `status` does with a file: the data when it passes its check, otherwise nothing and one
    line saying why, named after the file (never after a path of the machine that measured)."""
    data, problem = load(path)
    if problem is None and not os.path.exists(path):
        return None, None
    problems = [problem] if problem else check(data)
    if not problems:
        return data, None
    more = f" (and {len(problems) - 1} more: `harness {_command(check)} check` lists them)" if len(problems) > 1 else ""
    return None, f"{os.path.basename(path)} unreadable: {_one_line(problems[0])}{more}"


def _command(check: Callable[[Any], list[str]]) -> str:
    return "audit" if check is check_audit else "harvest"


def _summary(kind: str, data: dict) -> str:
    if kind == "audit":
        return f"audit of {data['audit']['date']}, {len(data['elements'])} element(s), {len(data['process_leaks'])} process leak(s)"
    return f"harvest from {data['source']} since {data['since']}, {data['prs_scanned']} PR(s) scanned"


def build_parser(parser: argparse.ArgumentParser, kind: str) -> argparse.ArgumentParser:
    parser.add_argument("file", help=f"the {kind} JSON to check (.harness/{kind}.json)")
    parser.set_defaults(shape_kind=kind)
    return parser


def main(args: argparse.Namespace) -> int:
    """0: `status` will count the file. 1: it will not, and every problem is listed. 2: no such file."""
    kind = args.shape_kind
    if not os.path.isfile(args.file):
        print(f"harness {kind} check: {args.file} is not a file", file=sys.stderr)
        return 2
    data, problem = load(args.file)
    problems = [problem] if problem else (check_audit if kind == "audit" else check_harvest)(data)
    if problems:
        print(f"harness {kind} check: {args.file} is not counted by `harness status`:", file=sys.stderr)
        for line in problems:
            print(f"- {line}", file=sys.stderr)
        return 1
    print(f"ok: {_summary(kind, data)}")
    return 0
