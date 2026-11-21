"""The gates run in CI: verification leaves the session that wrote the code.

In a session, the agent runs `qa gate` and `secu gate`, so it may not do it. Here a pipeline runs them on
each pull request, and its exit code blocks the merge. What CI cannot run without a model (the review) is not
claimed. "One test per criterion" runs when the pipeline gives the two files /qa leaves, the accepted ticket and
the criteria-to-tests trace; without them it is not run, and the summary says so. The gate reads the ticket from
the file it is given: that this file is the ticket its owner agreed to, and not one the pull request rewrote, is
the pipeline's to guarantee (fetched from the tracker, or kept where the pull request cannot write).

On a push to the delivery branch, `ci main` says the prerequisites of a delivery (`ship check`) for that commit.
It delivers nothing, and what it cannot measure there (the CI report of the commit, while this very job runs) is
said unmeasured.

The settings come from `docs/agents/gates.json` (or, failing that, its former French name
`docs/agents/portes.json`, with its French keys), read **on the base branch**: a pull request can neither
loosen these settings nor put itself out of reading. This protects only the settings. The code that runs the
gates must also come from somewhere other than the pull request (the plugin at a pinned version, or the
target branch fetched separately), and the pipeline file stays modifiable by it: a ruleset of the forge is
what makes the check required. A PR to an unprotected branch takes that branch's settings."""
from __future__ import annotations

import json
import os
from typing import Any

from . import qa, secu, ship, size
from .context import Refused, _read_at, resolve_base

CONFIG = "docs/agents/gates.json"
FORMER_CONFIG = "docs/agents/portes.json"
# the keys of the former French file, in its own names: {"secu": {"exclure"}, "qa": {"commande", "passages", "exclure"}}
_FORMER_KEYS = {"security": "secu", "exclude": "exclure", "command": "commande", "runs": "passages"}
MAX_EXCLUDES = 20
_TOO_WIDE = ("*", "**", "**/*", "*/**", "**/**", "*.*", "**/*.*")


def _globs(value: Any, where: str, source: str) -> list[str]:
    """Path patterns kept out of a gate. Each starts with a named folder or file: a wildcard at the start would
    put the whole repository out of reading."""
    if not (isinstance(value, list) and len(value) <= MAX_EXCLUDES and all(isinstance(g, str) and g.strip() for g in value)):
        raise Refused(f"{source}: {where} is a list of at most {MAX_EXCLUDES} path patterns")
    for glob in value:
        first = glob.strip().split("/")[0]
        if glob.strip() in _TOO_WIDE or glob.startswith(("/", "..")) or not first or any(ch in first for ch in "*?["):
            raise Refused(f"{source}: the pattern {glob[:40]!r} puts too much out of reading; it starts with a named folder or "
                          "file (tests/secrets/**), not with a wildcard")
        size.glob_regex(glob)
    return [g.strip() for g in value]


def load_config(repo: str, base: str) -> dict[str, Any]:
    """The settings of the gates on the base branch; safe values if there are none."""
    commit = resolve_base(repo, base)
    source, text = CONFIG, _read_at(repo, commit, CONFIG)
    if text is None:
        source, text = FORMER_CONFIG, _read_at(repo, commit, FORMER_CONFIG)
    config: dict[str, Any] = {"security": {"exclude": []}, "qa": {"command": None, "runs": None, "exclude": []}}
    if text is None:
        return config
    try:
        data = json.loads(text)
    except (ValueError, RecursionError) as exc:
        raise Refused(f"{source} (base branch): unreadable JSON") from exc
    key = (lambda name: _FORMER_KEYS.get(name, name)) if source == FORMER_CONFIG else (lambda name: name)
    if not isinstance(data, dict) or set(data) - {key("security"), "qa"}:
        raise Refused(f"{source}: an object with {key('security')} and qa, nothing else")
    security_part, qa_part = data.get(key("security"), {}), data.get("qa", {})
    if not isinstance(security_part, dict) or set(security_part) - {key("exclude")} or not isinstance(qa_part, dict) \
            or set(qa_part) - {key("command"), key("runs"), key("exclude")}:
        raise Refused(f"{source}: {key('security')}.{key('exclude')}, qa.{key('command')}, qa.{key('runs')} and qa.{key('exclude')} "
                      "are the only settings")
    command, runs = qa_part.get(key("command")), qa_part.get(key("runs"))
    if command is not None and not (isinstance(command, str) and command.strip() and len(command) <= 300):
        raise Refused(f"{source}: qa.{key('command')} is the repository's test command")
    if runs is not None and not (type(runs) is int and 1 <= runs <= 20):
        raise Refused(f"{source}: qa.{key('runs')} is an integer from 1 to 20")
    return {"security": {"exclude": _globs(security_part.get(key("exclude"), []), f"{key('security')}.{key('exclude')}", source)},
            "qa": {"command": command, "runs": runs, "exclude": _globs(qa_part.get(key("exclude"), []), f"qa.{key('exclude')}", source)},
            "source": source}


def run(table: dict[str, Any], repo: str, base: str, coverage: str | None = None, reports: list[str] | None = None,
        strict: bool = False, ticket_text: str | None = None, mapping: Any = None) -> dict[str, Any]:
    """The gates of a pull request: security, then tests. `strict` fails what is not measured. With the text of a
    ticket, "one test per criterion" is run against `mapping`, the trace /qa leaves."""
    config = load_config(repo, base)
    security = secu.run_gates(table, repo, base, reports, config["security"]["exclude"], pipeline=True)
    spared = [size.glob_regex(g) for g in config["qa"]["exclude"]]
    changed = [s["path"] for s in size.diff_stats(repo, base)]
    paths = [p for p in changed if not any(r.match(p) for r in spared)]   # a test about the skip itself, for example
    tests = [qa.gate_disabled(repo, base, paths, spared)]
    if config["qa"]["command"]:
        tests.append(qa.gate_repeat(repo, config["qa"]["command"], config["qa"]["runs"] or table["qa"]["runs"]))
    if coverage:
        tests.append(qa.gate_coverage(repo, base, coverage, table["qa"]["diff_coverage"]))
    if ticket_text is not None:
        tests.append(qa.gate_criteria(repo, ticket_text, mapping))
    gates = security["gates"] + tests
    failed = [g["id"] for g in gates if g["status"] == qa.FAIL]
    unknown = [g["id"] for g in gates if g["status"] == qa.UNKNOWN]
    return {"pass": not failed and not (strict and unknown), "failed": failed, "unknown": unknown, "strict": strict, "gates": gates,
            "criteria": ticket_text is not None, "excluded": sorted({*security["excluded"], *(secu._where(p) for p in changed if p not in paths)}), "configured": config}


def render_md(result: dict[str, Any]) -> str:
    source = result["configured"].get("source", CONFIG)
    out_of_reading = f" {len(result['excluded'])} file(s) out of reading." if result["excluded"] else ""
    if result["failed"]:
        head = f"Gates: {len(result['failed'])} failed. The merge is blocked."
    elif result["unknown"] and result["strict"]:
        head = f"Gates: {len(result['unknown'])} unmeasured, and this repository requires them measured. The merge is blocked."
    elif result["unknown"]:
        head = f"Gates: nothing failed, {len(result['unknown'])} unmeasured, for a human to look at."
    else:
        head = "Gates: everything measured passes."
    out = [f"### {head}{out_of_reading}", ""]
    for gate in result["gates"]:
        out.append(f"- **{gate['status']}** — {gate['title']} ({gate['evidence']})" + (f". {gate['action']}" if gate["action"] else ""))
    if result["excluded"]:
        out.append(f"- Out of reading, according to `{source}` on the base branch: {', '.join(result['excluded'][:8])}"
                   + (f" and {len(result['excluded']) - 8} more" if len(result["excluded"]) > 8 else "") + ".")
    if not result["configured"]["qa"]["command"]:
        out.append(f"- The test suite is not replayed here: `{CONFIG}` gives no command on the base branch.")
    if result.get("criteria"):
        out += ["", "These gates do not run the review: that takes a reviewer. The criteria are read from the ticket file the "
                    "pipeline gives: where that file comes from is the pipeline's to guarantee."]
    else:
        out += ["", "These gates run neither the review nor \"one test per criterion\": the review takes a reviewer, and the "
                    "criteria gate takes the accepted ticket and the trace /qa leaves, given through `--ticket` and `--trace`."]
    out.append("They do not say a change is safe: they say what was looked at.")
    return "\n".join(out) + "\n"


def main(table: dict[str, Any], repo: str, base: str, since: str | None = None, checks: Any = None,
         strict: bool = False) -> dict[str, Any]:
    """The prerequisites of a delivery, on a push to the delivery branch: `ship check`, with the exit code of a
    pipeline. A push that carries nothing since the last version passes. `strict` fails what is not cleared."""
    try:
        delivery = ship.check(table, repo, base, since, checks, pipeline=True)
    except ship.NothingToDeliver as exc:
        return {"pass": True, "failed": [], "unknown": [], "strict": strict, "gates": [], "delivery": None, "nothing": str(exc)}
    failed, unknown = delivery["failed"], delivery["unknown"]
    return {"pass": not failed and not (strict and unknown), "failed": failed, "unknown": unknown, "strict": strict,
            "gates": delivery["gates"], "delivery": delivery, "nothing": None}


def render_main(result: dict[str, Any]) -> str:
    if result["delivery"] is None:
        return f"### Delivery: {result['nothing']}.\n\nNothing was tagged, pushed or deployed.\n"
    out = ["### " + ship.render_md(result["delivery"]).rstrip("\n")]
    if result["unknown"] and not result["failed"]:
        out += ["", "This repository requires them cleared before this job passes (`--strict`): the job fails." if result["strict"]
                else "This job passes with prerequisites left to a human: `--strict` makes it fail instead."]
    return "\n".join(out) + "\n"


def publish(text: str, environ: dict[str, str]) -> None:
    """The summary on the job page, when the forge offers one."""
    path = environ.get("GITHUB_STEP_SUMMARY")
    if not path:
        return
    try:
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(text + "\n")
    except OSError:
        pass
