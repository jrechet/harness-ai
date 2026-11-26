"""`session` subcommand: the numbers of one Claude Code session, and the user's own words about it.

Using the harness costs something and does not always suit: this is where that is written down. The
numbers are read by code from the session's transcript; the words are the user's. Everything stays in
`<harness-dir>/session/`, which git ignores. Nothing is sent anywhere, and no model judges anything.

  harness session measure [--session ID | --transcript PATH] [--repo P]   writes session/<id>.json
  harness session note "<your words>" [--repo P]                          adds a line to session/notes.jsonl
  harness session list [--repo P]                                         one line per measured session

What is read: the transcript Claude Code keeps under `~/.claude/projects/`, and the files of its
sub-agents. Its format is internal to Claude Code and changes between versions, so the measure says
`partial` or `unmeasured` when it does not find what it expects, never a number it is not sure of.
What is written: counts, token sums and names of skills and models, copied through an allowlist. No
prompt, no answer, no path, no branch, no account.

Dollar figures are the estimate Claude Code itself records, at list price: not a bill.
Exit codes: 0 measured or partial, 1 unmeasured, 2 invalid input."""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
import sys
from datetime import datetime, timezone
from typing import Any, Iterator

SCHEMA = "harness-session/1"
SESSION_ENV = "CLAUDE_CODE_SESSION_ID"
FOLDER = "session"
NOTES = "notes.jsonl"
SESSION_ID = re.compile(r"[0-9A-Za-z][0-9A-Za-z-]{7,63}")
NAME = re.compile(r"[\w:.@+/-]{1,100}")            # a skill, a plugin, a model, a version, a denial kind
TIMESTAMP = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:\d{2})")
OTHER = "(other)"
LATE_TOTALS = 1.1            # rows above the recorded totals by more than this: the totals started late
# What the report calls each count, then its name in a message's usage and in Claude Code's totals.
COUNTED = ("input_tokens", "output_tokens", "cache_read_tokens", "cache_creation_tokens")
USAGE_FIELDS = dict(zip(COUNTED, ("input_tokens", "output_tokens", "cache_read_input_tokens", "cache_creation_input_tokens")))
MODEL_FIELDS = dict(zip(COUNTED, ("inputTokens", "outputTokens", "cacheReadInputTokens", "cacheCreationInputTokens")))
REPORT_KEYS = {"schema", "status", "reason", "session", "measured_at", "claude_code_versions", "started_at",
               "ended_at", "counts", "totals", "rows", "by_skill"}
SKILL_KEYS = {"skill", "plugin", "messages", "tool_calls", *USAGE_FIELDS}


class Refused(ValueError):
    """Invalid input: one sentence for the user, exit code 2."""


def build_parser(parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
    actions = parser.add_subparsers(dest="action", required=True)
    measure = actions.add_parser("measure", help="the numbers of one session, written to session/<id>.json")
    measure.add_argument("--session", help=f"the session id (default: the running session, from ${SESSION_ENV})")
    measure.add_argument("--transcript", help="the transcript file itself, when the id is not enough")
    measure.add_argument("--projects-dir", default=os.path.join("~", ".claude", "projects"),
                         help="where Claude Code keeps its transcripts")
    measure.add_argument("--format", choices=["md", "json"], default="md")
    note = actions.add_parser("note", help="your own words about what suits you or not, kept on this machine")
    note.add_argument("text", help="what you want to remember, as you would say it")
    listing = actions.add_parser("list", help="one line per measured session")
    for sub in (measure, note, listing):
        sub.add_argument("--repo", default=".", help="repository path (default: .)")
        sub.add_argument("--harness-dir", default=".harness")
    for sub in (measure, note):
        sub.add_argument("--now", help="the time to record (default: now, UTC)")
    return parser


# --- reading -----------------------------------------------------------------------------------

def read_rows(path: str) -> Iterator[dict[str, Any]]:
    """The JSON objects of a transcript, one per line. A line that is not one is skipped."""
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            try:
                row = json.loads(line)
            except ValueError:
                continue
            if isinstance(row, dict):
                yield row


def _count(value: Any) -> int | None:
    """A token count or a duration: a non-negative whole number, or nothing."""
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0:
        return None
    return int(value)


def _name(value: Any) -> str | None:
    """A name copied out only when it looks like one: no spaces, no free text."""
    if value is None:
        return None
    return value if isinstance(value, str) and NAME.fullmatch(value) else OTHER


def _blocks(row: dict[str, Any], kind: str) -> list[dict[str, Any]]:
    message = row.get("message")
    content = message.get("content") if isinstance(message, dict) else None
    if not isinstance(content, list):
        return []
    return [block for block in content if isinstance(block, dict) and block.get("type") == kind]


def find_transcript(session_id: str, projects_dir: str) -> str:
    if not SESSION_ID.fullmatch(session_id):
        raise Refused(f"{session_id!r} is not a session id (letters, digits and dashes)")
    found = sorted(glob.glob(os.path.join(glob.escape(os.path.expanduser(projects_dir)), "*", session_id + ".jsonl")))
    if not found:
        raise Refused(f"no transcript of session {session_id} under {projects_dir}: give --transcript <file>")
    if len(found) > 1:
        raise Refused(f"session {session_id} has {len(found)} transcripts under {projects_dir}: give --transcript <file>")
    return found[0]


def subagent_files(transcript: str) -> list[str]:
    """The transcripts of the sub-agents and workflows of a session: `<id>/subagents/**/*.jsonl`."""
    base = os.path.join(glob.escape(transcript[:-len(".jsonl")]), "subagents")
    return sorted(glob.glob(os.path.join(base, "**", "*.jsonl"), recursive=True))


# --- measuring ---------------------------------------------------------------------------------

def _totals_from_claude_code(row: dict[str, Any]) -> dict[str, Any] | None:
    """The totals Claude Code recorded itself, or nothing when the row is not shaped as expected."""
    cost, usage = row.get("totalCostUSD"), row.get("modelUsage")
    if isinstance(cost, bool) or not isinstance(cost, (int, float)) or not isinstance(usage, dict) or not usage:
        return None
    totals: dict[str, Any] = {"source": "claude-code", "cost_usd_estimate": round(float(cost), 4)}
    by_model: dict[str, Any] = {}
    for field in MODEL_FIELDS:
        totals[field] = 0
    for model, numbers in usage.items():
        if not isinstance(numbers, dict):
            return None
        for field, key in MODEL_FIELDS.items():
            value = _count(numbers.get(key))
            if value is None:
                return None
            totals[field] += value
        model_cost = numbers.get("costUSD")
        by_model[_name(model) or OTHER] = {
            "output_tokens": _count(numbers.get("outputTokens")),
            "cost_usd_estimate": round(float(model_cost), 4) if isinstance(model_cost, (int, float)) and not isinstance(model_cost, bool) else None}
    for field, key in (("duration_s", "totalDuration"), ("api_duration_s", "totalAPIDuration"),
                       ("tool_duration_s", "totalToolDuration")):
        value = _count(row.get(key))
        totals[field] = None if value is None else round(value / 1000)
    totals["lines_added"] = _count(row.get("totalLinesAdded"))
    totals["lines_removed"] = _count(row.get("totalLinesRemoved"))
    totals["by_model"] = by_model
    return totals


def measure(transcript: str, session_id: str, now: str) -> dict[str, Any]:
    """Everything the report holds, from the transcript and the files of its sub-agents."""
    subs = subagent_files(transcript)
    seen_messages: set[str] = set()
    seen_tools: set[str] = set()
    failed_tools: set[str] = set()
    skills: dict[tuple[str | None, str | None], dict[str, int]] = {}
    versions: set[str] = set()
    denials: dict[str, int] = {}
    stamps: list[str] = []
    recorded: dict[str, Any] | None = None
    recorded_but_unreadable = False
    own_subagents = 0
    counts = {"human": 0, "origins": 0, "assistant": 0, "without_usage": 0, "compactions": 0, "api_errors": 0,
              "inherited": 0}
    for index, path in enumerate([transcript, *subs]):
        main = index == 0
        if not main and not os.path.isfile(path):
            continue
        own_rows = 0
        for row in read_rows(path):
            kind = row.get("type")
            # A forked session starts with a copy of its parent's rows and of its parent's sub-agent
            # files, which all keep the parent's id.
            if isinstance(row.get("sessionId"), str) and row["sessionId"] != session_id:
                counts["inherited"] += main
                continue
            own_rows += 1
            stamp = row.get("timestamp")
            if main and isinstance(stamp, str) and TIMESTAMP.fullmatch(stamp):
                stamps.append(stamp)
            if kind == "assistant":
                _assistant(row, seen_messages, seen_tools, skills, versions, counts)
            elif kind == "user":
                _user(row, main, failed_tools, denials, counts)
            elif kind == "system" and main:
                if row.get("subtype") == "compact_boundary":
                    counts["compactions"] += 1
                elif row.get("subtype") == "api_error":
                    counts["api_errors"] += 1
            elif kind == "cost-state" and main:
                totals = _totals_from_claude_code(row)
                recorded_but_unreadable = totals is None
                recorded = totals or recorded
        if not main and own_rows:
            own_subagents += 1
    by_skill = [{"skill": skill, "plugin": plugin, **numbers} for (skill, plugin), numbers in skills.items()]
    by_skill.sort(key=lambda row: (-row["output_tokens"], str(row["skill"])))
    summed = {field: sum(row[field] for row in by_skill) for field in USAGE_FIELDS}
    report: dict[str, Any] = {
        "schema": SCHEMA, "status": "measured", "reason": None, "session": session_id, "measured_at": now,
        "claude_code_versions": sorted(versions),
        "started_at": min(stamps) if stamps else None, "ended_at": max(stamps) if stamps else None,
        "counts": {"human_prompts": counts["human"] if counts["origins"] else None,
                   "assistant_messages": counts["assistant"], "tool_calls": len(seen_tools),
                   "tool_errors": len(failed_tools), "denials": dict(sorted(denials.items())),
                   "compactions": counts["compactions"], "api_errors": counts["api_errors"],
                   "subagent_files": own_subagents},
        "totals": None, "rows": summed, "by_skill": by_skill}
    if not counts["assistant"]:
        report.update(status="unmeasured", totals=None, by_skill=[], rows=None, reason=(
            "the assistant messages carry no usage: the transcript format is not the one this command reads"
            if counts["without_usage"] else "no assistant message in the transcript"))
        return report
    reasons = []
    if counts["inherited"]:
        recorded = None            # what Claude Code recorded counts the parent too
        reasons.append(f"this session was forked from another: its {counts['inherited']:,} inherited rows are left out")
    if recorded and not recorded_but_unreadable:
        report["totals"] = recorded
        if summed["output_tokens"] > recorded["output_tokens"] * LATE_TOTALS:
            reasons.append("the totals Claude Code recorded cover only a part of this session: the rows show more "
                           "output than they do, so the cost and the durations are a minimum")
    else:
        report["totals"] = {"source": "rows", "cost_usd_estimate": None, **summed}
        reasons.append("the totals Claude Code records are "
                       + ("left out with the fork" if counts["inherited"] else "not shaped as expected" if recorded_but_unreadable else "absent")
                       + ": tokens are summed from the rows, without a cost or a duration")
    if not counts["origins"]:
        reasons.append("no row says whether a prompt came from a human: your prompts are not counted")
    if counts["without_usage"]:
        reasons.append(f"{counts['without_usage']} assistant messages carry no usage and are left out")
    if reasons:
        report.update(status="partial", reason="; ".join(reasons))
    return report


def _assistant(row, seen_messages, seen_tools, skills, versions, counts) -> None:
    message = row.get("message")
    if not isinstance(message, dict):
        return
    version = _name(row.get("version"))
    if version and version != OTHER:
        versions.add(version)
    key = message.get("id") or row.get("uuid")
    if isinstance(key, str):
        if key in seen_messages:
            return
        seen_messages.add(key)
    usage = message.get("usage")
    if not isinstance(usage, dict) or _count(usage.get("output_tokens")) is None:
        if message.get("model") != "<synthetic>":
            counts["without_usage"] += 1
        return
    counts["assistant"] += 1
    numbers = skills.setdefault((_name(row.get("attributionSkill")), _name(row.get("attributionPlugin"))),
                                {"messages": 0, "tool_calls": 0, **{field: 0 for field in USAGE_FIELDS}})
    numbers["messages"] += 1
    for field, source in USAGE_FIELDS.items():
        numbers[field] += _count(usage.get(source)) or 0
    for block in _blocks(row, "tool_use"):
        tool_id = block.get("id")
        if isinstance(tool_id, str) and tool_id not in seen_tools:
            seen_tools.add(tool_id)
            numbers["tool_calls"] += 1


def _user(row, main, failed_tools, denials, counts) -> None:
    for block in _blocks(row, "tool_result"):
        if block.get("is_error") is True and isinstance(block.get("tool_use_id"), str):
            failed_tools.add(block["tool_use_id"])
    if not main:
        return
    denial = _name(row.get("toolDenialKind"))
    if denial:
        denials[denial] = denials.get(denial, 0) + 1
    origin = row.get("origin")
    if isinstance(origin, dict):
        counts["origins"] += 1
        if origin.get("kind") == "human" and not row.get("isCompactSummary") and not row.get("isMeta"):
            counts["human"] += 1


# --- writing -----------------------------------------------------------------------------------

def _folder(repo: str, harness_dir: str) -> str:
    """The session folder, created with the file that makes git ignore everything in it."""
    folder = os.path.join(repo, harness_dir, FOLDER)
    os.makedirs(folder, exist_ok=True)
    ignore = os.path.join(folder, ".gitignore")
    if not os.path.exists(ignore):
        with open(ignore, "w", encoding="utf-8") as fh:
            fh.write("*\n")
    return folder


def _now(given: str | None) -> str:
    return given or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _running_session() -> str | None:
    value = os.environ.get(SESSION_ENV)
    return value if value and SESSION_ID.fullmatch(value) else None


def read_notes(folder: str, session_id: str) -> list[str]:
    try:
        return [row["note"] for row in read_rows(os.path.join(folder, NOTES))
                if row.get("session") == session_id and isinstance(row.get("note"), str)]
    except OSError:
        return []


# --- telling -----------------------------------------------------------------------------------

def _n(value: int | None) -> str:
    return "?" if value is None else f"{value:,}"


def _plural(count: int, word: str) -> str:
    return f"{count:,} {word}" + ("" if count == 1 else "s")


def _minutes(seconds: int | None) -> str:
    if seconds is None:
        return "?"
    if seconds >= 2 * 3600:
        return f"{seconds / 3600:,.1f} h"
    return f"{seconds // 60} min" if seconds >= 60 else f"{seconds} s"


def render(report: dict[str, Any], notes: list[str], shown: str) -> str:
    versions = ", ".join(report["claude_code_versions"]) or "version unknown"
    out = [f"Session {report['session'][:8]} — {report['status']} (Claude Code {versions})"]
    if report["reason"]:
        out.append(f"  {report['status']}: {report['reason']}")
    counts = report["counts"]
    prompts = "prompts from you: not counted" if counts["human_prompts"] is None else \
        f"{counts['human_prompts']:,} prompt{'' if counts['human_prompts'] == 1 else 's'} from you"
    denied = sum(counts["denials"].values())
    line = [prompts, f"{_plural(counts['tool_calls'], 'tool call')}, {counts['tool_errors']:,} failed"]
    if denied:
        line.append(f"{denied:,} refused or interrupted (" + ", ".join(f"{k} {v}" for k, v in counts["denials"].items()) + ")")
    line += [_plural(counts["compactions"], "compaction"), _plural(counts["api_errors"], "API error"),
             _plural(counts["subagent_files"], "sub-agent file")]
    out.append(" · ".join(line))
    totals = report["totals"]
    if totals:
        if totals["source"] == "claude-code":
            out.append(f"Totals recorded by Claude Code: {_n(totals['output_tokens'])} output tokens, "
                       f"{_n(totals['cache_read_tokens'])} read from cache, open for {_minutes(totals['duration_s'])} "
                       f"of which {_minutes(totals['api_duration_s'])} waiting for the model; "
                       f"about ${totals['cost_usd_estimate']:,.2f} (an estimate at list price, not a bill)")
        else:
            out.append(f"Totals summed from the rows: {_n(totals['output_tokens'])} output tokens, "
                       f"{_n(totals['cache_read_tokens'])} read from cache; no cost estimate")
        out.append(f"By skill, output tokens (the rows of the transcript and its sub-agents: {_n(report['rows']['output_tokens'])}):")
        for row in report["by_skill"]:
            out.append(f"- {row['skill'] or '(no skill)'}: {_n(row['output_tokens'])} "
                       f"({_plural(row['messages'], 'message')}, {_plural(row['tool_calls'], 'tool call')})")
    if notes:
        out.append("Your notes on this session:")
        out += [f"- {note}" for note in notes]
    out.append(f"Written to {shown} (kept on this machine, ignored by git; nothing is sent).")
    return "\n".join(out) + "\n"


def render_list(folder: str) -> str:
    files = sorted(path for path in glob.glob(os.path.join(glob.escape(folder), "*.json")))
    lines, broken = [], []
    for path in files:
        try:
            with open(path, encoding="utf-8") as fh:
                report = json.load(fh)
            totals = report["totals"] or {}
            cost = totals.get("cost_usd_estimate")
            lines.append((str(report.get("started_at") or report["measured_at"]),
                          f"- {str(report.get('started_at') or '?')[:10]} {report['session'][:8]} {report['status']}: "
                          f"{_n(report['counts']['human_prompts'])} prompts from you, {_n(totals.get('output_tokens'))} output tokens"
                          + (f", about ${cost:,.2f}" if isinstance(cost, (int, float)) else "")
                          + "; top: " + (", ".join(f"{row['skill'] or '(no skill)'} {_n(row['output_tokens'])}"
                                                   for row in report["by_skill"][:3]) or "nothing")))
        except (OSError, ValueError, KeyError, TypeError, AttributeError):
            broken.append(os.path.basename(path))
    if not lines and not broken:
        return "No session measured yet. `harness session measure` at the end of a session writes one.\n"
    out = [f"{_plural(len(lines), 'session')} measured (dollars are estimates at list price):"]
    out += [text for _, text in sorted(lines)]
    out += [f"- {name}: not readable, left out" for name in broken]
    return "\n".join(out) + "\n"


# --- entry -------------------------------------------------------------------------------------

def _measure(args: argparse.Namespace, repo: str) -> int:
    if args.transcript:
        transcript = os.path.expanduser(args.transcript)
        session_id = os.path.basename(transcript)[:-len(".jsonl")] if transcript.endswith(".jsonl") else ""
        if not os.path.isfile(transcript) or not SESSION_ID.fullmatch(session_id):
            raise Refused(f"{args.transcript} is not a transcript file named <session id>.jsonl")
    else:
        session_id = args.session or _running_session()
        if not session_id:
            raise Refused(f"no session to measure: give --session <id> or --transcript <file> "
                          f"(${SESSION_ENV} is not set, so this is not run from a Claude Code session)")
        transcript = find_transcript(session_id, args.projects_dir)
    try:
        report = measure(transcript, session_id, _now(args.now))
    except OSError as exc:
        raise Refused(f"the transcript cannot be read: {exc.strerror}") from exc
    folder = _folder(repo, args.harness_dir)
    with open(os.path.join(folder, session_id + ".json"), "w", encoding="utf-8") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    if args.format == "json":
        json.dump(report, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
    else:
        shown = "/".join([args.harness_dir, FOLDER, session_id + ".json"])
        sys.stdout.write(render(report, read_notes(folder, session_id), shown))
    return 1 if report["status"] == "unmeasured" else 0


def _note(args: argparse.Namespace, repo: str) -> int:
    text = args.text.strip()
    if not text:
        raise Refused("the note is empty: say in your own words what suits you or not")
    folder = _folder(repo, args.harness_dir)
    with open(os.path.join(folder, NOTES), "a", encoding="utf-8") as fh:
        fh.write(json.dumps({"at": _now(args.now), "session": _running_session(), "note": text}, ensure_ascii=False) + "\n")
    print(f"Noted in {'/'.join([args.harness_dir, FOLDER, NOTES])} (kept on this machine, ignored by git; nothing is sent).")
    return 0


def main(args: argparse.Namespace) -> int:
    try:
        if not os.path.isdir(args.repo):
            raise Refused(f"{args.repo} is not a directory")
        repo = os.path.abspath(args.repo)
        if args.action == "measure":
            return _measure(args, repo)
        if args.action == "note":
            return _note(args, repo)
        sys.stdout.write(render_list(os.path.join(repo, args.harness_dir, FOLDER)))
        return 0
    except Refused as exc:
        print(f"harness session: {exc}", file=sys.stderr)
        return 2
    except OSError as exc:
        print(f"harness session: {exc.strerror or exc}", file=sys.stderr)
        return 2
