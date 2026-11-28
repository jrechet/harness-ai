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
What is written: counts, token sums and names of skills, plugins and models. Nothing is copied out of
a field that holds a prompt, an answer, a path, a branch or an account (a message's content is read
for the ids of its tool calls and whether they failed, nothing else), and a name is copied only when
it is shaped like one (ASCII, no slash at its start, no "@", no space): anything else comes out as
"(other)". A name-shaped word put in a name field is copied as it is.
What the counts cover: tool calls, their failures, refusals and tokens include the sub-agents; your
prompts, compactions and API errors are those of the main conversation. A session measured while it
runs lacks the turn in progress. A message written twice with no id is counted twice.

Dollar figures are the estimate Claude Code itself records, at list price: not a bill.
Exit codes: 0 measured or partial, 1 unmeasured, 2 invalid input."""
from __future__ import annotations

import argparse
import glob
import json
import math
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from typing import Any, Iterator

SCHEMA = "harness-session/1"
SESSION_ENV = "CLAUDE_CODE_SESSION_ID"
FOLDER = "session"
NOTES = "notes.jsonl"
SESSION_ID = re.compile(r"[0-9A-Za-z][0-9A-Za-z-]{7,63}")
# A name is copied out only when it looks like one. One narrow pattern per field, ASCII only: no
# slash at the start, no "@", no space, so a path, an address or a sentence comes out as "(other)".
VERSION = re.compile(r"[0-9][0-9A-Za-z.+-]{0,30}", re.ASCII)
MODEL = re.compile(r"[A-Za-z0-9][A-Za-z0-9._\[\]-]{0,63}", re.ASCII)
DENIAL = re.compile(r"[a-z][a-z_-]{0,39}", re.ASCII)
PLUGIN = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,63}", re.ASCII)
SKILL = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,63}(:[A-Za-z0-9][A-Za-z0-9_.-]{0,63})?", re.ASCII)
TIMESTAMP = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d{1,6})?(Z|[+-]\d{2}:\d{2})", re.ASCII)
STATUSES = ("measured", "partial", "unmeasured")
UNPRINTABLE = re.compile(r"[\x00-\x1f\x7f-\x9f\u200b-\u200f\u2028-\u202e\u2066-\u2069\ufeff]+")
MAX_NOTE = 2000              # characters of one note
MAX_NUMBER = 10 ** 15        # above this a count is not a count
OTHER = "(other)"
LATE_TOTALS = 1.1            # rows above the recorded totals by more than this: the totals started late
# What the report calls each count, then its name in a message's usage and in Claude Code's totals.
COUNTED = ("input_tokens", "output_tokens", "cache_read_tokens", "cache_creation_tokens")
USAGE_FIELDS = dict(zip(COUNTED, ("input_tokens", "output_tokens", "cache_read_input_tokens", "cache_creation_input_tokens")))
MODEL_FIELDS = dict(zip(COUNTED, ("inputTokens", "outputTokens", "cacheReadInputTokens", "cacheCreationInputTokens")))
REPORT_KEYS = {"schema", "status", "reason", "session", "measured_at", "claude_code_versions", "started_at",
               "ended_at", "counts", "totals", "rows", "by_skill"}
SKILL_KEYS = {"skill", "plugin", "messages", "tool_calls", *USAGE_FIELDS}
COUNT_KEYS = {"human_prompts", "assistant_messages", "tool_calls", "tool_errors", "denials", "compactions",
              "api_errors", "subagent_files"}
TOTAL_KEYS = {"source", "cost_usd_estimate", *COUNTED, "duration_s", "api_duration_s", "tool_duration_s",
              "lines_added", "lines_removed", "by_model"}


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
            except (ValueError, RecursionError):
                continue
            if isinstance(row, dict):
                yield row


def _number(value: Any) -> int | float | None:
    """A finite number between zero and MAX_NUMBER, or nothing."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value if 0 <= value <= MAX_NUMBER else None


def _count(value: Any) -> int | None:
    """A token count or a duration: a finite, non-negative number, or nothing."""
    number = _number(value)
    return None if number is None else int(number)


def _cost(value: Any) -> float | None:
    """A cost estimate: a finite, non-negative number, or nothing."""
    number = _number(value)
    return None if number is None else round(float(number), 4)


def _plain(text: str) -> str:
    """A text safe to print on one line: control and invisible characters become one space."""
    return UNPRINTABLE.sub(" ", text).strip()


def _when(stamp: str) -> datetime:
    return datetime.fromisoformat(stamp.replace("Z", "+00:00"))


def _name(value: Any, pattern: re.Pattern[str]) -> str | None:
    """A name copied out only when it matches the pattern of its field."""
    if value is None:
        return None
    return value if isinstance(value, str) and pattern.fullmatch(value) else OTHER


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
    cost, usage = _cost(row.get("totalCostUSD")), row.get("modelUsage")
    if cost is None or not isinstance(usage, dict) or not usage:
        return None
    totals: dict[str, Any] = {"source": "claude-code", "cost_usd_estimate": cost}
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
        name, cost = _name(model, MODEL) or OTHER, _cost(numbers.get("costUSD"))
        before = by_model.get(name)
        if before is not None:               # two names that are not names share "(other)": they add up
            cost = None if cost is None or before["cost_usd_estimate"] is None else round(cost + before["cost_usd_estimate"], 4)
        by_model[name] = {"output_tokens": _count(numbers.get("outputTokens")) + (before["output_tokens"] if before else 0),
                          "cost_usd_estimate": cost}
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
    messages: dict[str, tuple[Any, dict[str, int]]] = {}
    no_usage: set[str] = set()
    seen_tools: set[str] = set()
    failed_tools: set[str] = set()
    seen_denials: set[str] = set()
    skills: dict[tuple[str | None, str | None], dict[str, int]] = {}
    versions: set[str] = set()
    denials: dict[str, int] = {}
    stamps: list[tuple[datetime, str]] = []
    recorded: dict[str, Any] | None = None
    recorded_but_unreadable = False
    own_subagents = 0
    unreadable = 0
    counts = {"human": 0, "origins": 0, "assistant": 0, "without_usage": 0, "compactions": 0, "api_errors": 0,
              "inherited": 0, "odd_usage": 0, "odd_tools": 0}
    keyless: list[tuple[Any, dict[str, int]]] = []
    for index, path in enumerate([transcript, *subs]):
        main = index == 0
        own_rows = 0
        try:
            rows = read_rows(path) if main else list(read_rows(path))
        except OSError:
            unreadable += 1                    # a sub-agent file that cannot be read: the rest still counts
            continue
        for row in rows:
            kind = row.get("type")
            # A forked session starts with a copy of its parent's rows and of its parent's sub-agent
            # files, which all keep the parent's id.
            if isinstance(row.get("sessionId"), str) and row["sessionId"] != session_id:
                counts["inherited"] += main
                continue
            own_rows += 1
            stamp = row.get("timestamp")
            if main and isinstance(stamp, str) and TIMESTAMP.fullmatch(stamp):
                try:
                    stamps.append((_when(stamp), stamp))
                except ValueError:
                    pass                       # shaped like a time, but not one (month 13)
            if kind == "assistant":
                _assistant(row, messages, keyless, no_usage, seen_tools, skills, versions, counts)
            elif kind == "user":
                _user(row, main, failed_tools, denials, seen_denials, counts)
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
    counts["without_usage"] += len(no_usage - set(messages))
    for bucket, usage in [*messages.values(), *keyless]:
        counts["assistant"] += 1
        skills[bucket]["messages"] += 1
        for field in USAGE_FIELDS:
            skills[bucket][field] += usage[field]
    failed_tools &= seen_tools                 # a failure counts only for a call that was seen
    by_skill = [{"skill": skill, "plugin": plugin, **numbers} for (skill, plugin), numbers in skills.items()
                if numbers["messages"] or numbers["tool_calls"]]
    by_skill.sort(key=lambda row: (-row["output_tokens"], str(row["skill"])))
    summed = {field: sum(row[field] for row in by_skill) for field in USAGE_FIELDS}
    report: dict[str, Any] = {
        "schema": SCHEMA, "status": "measured", "reason": None, "session": session_id, "measured_at": now,
        "claude_code_versions": sorted(versions),
        "started_at": min(stamps)[1] if stamps else None, "ended_at": max(stamps)[1] if stamps else None,
        "counts": {"human_prompts": counts["human"] if counts["origins"] else None,
                   "assistant_messages": counts["assistant"], "tool_calls": len(seen_tools),
                   "tool_errors": len(failed_tools), "denials": dict(sorted(denials.items())),
                   "compactions": counts["compactions"], "api_errors": counts["api_errors"],
                   "subagent_files": own_subagents},
        "totals": None, "rows": summed, "by_skill": by_skill}
    if not counts["assistant"]:
        report.update(status="unmeasured", totals=None, by_skill=[], rows=None, reason=(
            "the assistant messages carry no usage: the transcript format is not the one this command reads"
            if counts["without_usage"] else
            f"every row belongs to another session ({counts['inherited']:,} rows): a copy, or a fork with nothing of its own yet"
            if counts["inherited"] else "no assistant message in the transcript"))
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
    if unreadable:
        reasons.append(f"{unreadable} sub-agent file{'' if unreadable == 1 else 's'} could not be read and {'is' if unreadable == 1 else 'are'} left out")
    if not counts["origins"]:
        reasons.append("no row says whether a prompt came from a human: your prompts are not counted")
    if counts["without_usage"]:
        reasons.append(f"{counts['without_usage']} assistant messages carry no usage and are left out")
    if counts["odd_usage"]:
        reasons.append(f"{counts['odd_usage']} token counts are not numbers and count for nothing: the sums are a minimum")
    if counts["odd_tools"]:
        reasons.append(f"{counts['odd_tools']} tool calls carry no id and are not counted")
    if reasons:
        report.update(status="partial", reason="; ".join(reasons))
    return report


def _assistant(row, messages, keyless, no_usage, seen_tools, skills, versions, counts) -> None:
    """One row of an assistant message. Claude Code writes a message as several rows, one per block,
    that share the message id: the tool calls are read on every row, the usage once, from the row
    that shows the most output (an early row may carry a count that was not final yet)."""
    message = row.get("message")
    if not isinstance(message, dict):
        return
    version = _name(row.get("version"), VERSION)
    if version and version != OTHER:
        versions.add(version)
    bucket = (_name(row.get("attributionSkill"), SKILL), _name(row.get("attributionPlugin"), PLUGIN))
    numbers = skills.setdefault(bucket, {"messages": 0, "tool_calls": 0, **{field: 0 for field in USAGE_FIELDS}})
    for block in _blocks(row, "tool_use"):
        tool_id = block.get("id")
        if not isinstance(tool_id, str):
            counts["odd_tools"] += 1
        elif tool_id not in seen_tools:
            seen_tools.add(tool_id)
            numbers["tool_calls"] += 1
    key = message.get("id") or row.get("uuid")
    key = key if isinstance(key, str) else None
    usage = message.get("usage")
    if not isinstance(usage, dict) or _count(usage.get("output_tokens")) is None:
        if message.get("model") != "<synthetic>":
            if key is None:
                counts["without_usage"] += 1
            else:
                no_usage.add(key)
        return
    read = {field: _count(usage.get(source)) for field, source in USAGE_FIELDS.items()}
    odd = sum(1 for field, source in USAGE_FIELDS.items() if read[field] is None and usage.get(source) is not None)
    read = {field: value or 0 for field, value in read.items()}
    if key is None:
        keyless.append((bucket, read))
        counts["odd_usage"] += odd
    elif key not in messages:
        messages[key] = (bucket, read)
        counts["odd_usage"] += odd
    elif read["output_tokens"] > messages[key][1]["output_tokens"]:
        messages[key] = (messages[key][0], read)


def _user(row, main, failed_tools, denials, seen_denials, counts) -> None:
    for block in _blocks(row, "tool_result"):
        if block.get("is_error") is True and isinstance(block.get("tool_use_id"), str):
            failed_tools.add(block["tool_use_id"])
    denial = _name(row.get("toolDenialKind"), DENIAL)
    uuid = row.get("uuid")
    if denial and not (isinstance(uuid, str) and uuid in seen_denials):   # a row copied into two files counts once
        denials[denial] = denials.get(denial, 0) + 1
        if isinstance(uuid, str):
            seen_denials.add(uuid)
    if not main:
        return
    origin = row.get("origin")
    if isinstance(origin, dict):
        counts["origins"] += 1
        if origin.get("kind") == "human" and not row.get("isCompactSummary") and not row.get("isMeta"):
            counts["human"] += 1


# --- writing -----------------------------------------------------------------------------------

def _place(repo: str, harness_dir: str) -> str:
    """Where the session folder is, inside the repository. Refused when the path leaves the repository
    (`..`, an absolute path), goes through a link, or enters `.git`."""
    root = os.path.realpath(repo)
    folder = os.path.normpath(os.path.join(root, harness_dir, FOLDER))
    inside = not os.path.isabs(harness_dir) and os.path.commonpath([root, folder]) == root and folder != root
    if not inside or os.path.realpath(folder) != folder or ".git" in os.path.relpath(folder, root).split(os.sep):
        raise Refused(f"--harness-dir {harness_dir} leads outside the repository, through a link or into .git: "
                      "nothing was read or written")
    return folder


def _folder(repo: str, harness_dir: str) -> str:
    """The session folder, created, with the file that makes git ignore everything in it."""
    folder = _place(repo, harness_dir)
    os.makedirs(folder, exist_ok=True)
    ignore = os.path.join(folder, ".gitignore")
    lines = []
    if os.path.islink(ignore):
        raise Refused(".gitignore in the session folder is a link: nothing was written")
    if os.path.isfile(ignore):
        with open(ignore, encoding="utf-8", errors="replace") as fh:
            lines = fh.read().splitlines()
    if "*" not in [line.strip() for line in lines]:
        _write(folder, ".gitignore", "\n".join([*lines, "*"]) + "\n", "w")
    return folder


def _write(folder: str, name: str, text: str, mode: str) -> None:
    """Writes inside the session folder, never through a link someone left there."""
    path = os.path.join(folder, name)
    if os.path.islink(path):
        raise Refused(f"{name} in the session folder is a link: nothing was written")
    with open(path, mode, encoding="utf-8", errors="replace") as fh:
        fh.write(text)


def kept(repo: str, folder: str, name: str) -> str:
    """Where the file stands for git, checked and not assumed: ignored, tracked, or unknown."""
    path = os.path.join(folder, name)
    # Asked of this repository, not of the one a hook or a wrapper names in GIT_DIR.
    env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    try:
        tracked = subprocess.run(["git", "-C", repo, "ls-files", "--error-unmatch", "--", path],
                                 capture_output=True, timeout=10, env=env).returncode == 0
        ignored = subprocess.run(["git", "-C", repo, "check-ignore", "-q", "--", path],
                                 capture_output=True, timeout=10, env=env).returncode == 0
    except (OSError, subprocess.SubprocessError):
        return "kept on this machine; nothing is sent"
    if tracked:
        return "kept on this machine, but git ALREADY TRACKS this file: `git rm --cached` it if it must stay yours; nothing is sent"
    if ignored:
        return "kept on this machine, ignored by git; nothing is sent"
    return "kept on this machine; nothing is sent"


def _now(given: str | None) -> str:
    if given is not None and not TIMESTAMP.fullmatch(given):
        raise Refused(f"--now {given!r} is not a time such as 2026-11-26T10:00:00Z")
    return given or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _running_session() -> str | None:
    value = os.environ.get(SESSION_ENV)
    return value if value and SESSION_ID.fullmatch(value) else None


def _notes(folder: str) -> list[dict[str, Any]]:
    """The notes of the folder, each made safe to print. A notes file that is a link is not read."""
    path = os.path.join(folder, NOTES)
    if os.path.islink(path):
        return []
    try:
        return [{**row, "note": _plain(row["note"])[:MAX_NOTE]} for row in read_rows(path)
                if isinstance(row.get("note"), str)]
    except OSError:
        return []


def read_notes(folder: str, session_id: str) -> list[str]:
    return [row["note"] for row in _notes(folder) if row.get("session") == session_id]


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


def render(report: dict[str, Any], notes: list[str], shown: str, where: str, running: bool = False) -> str:
    versions = ", ".join(report["claude_code_versions"]) or "version unknown"
    out = [f"Session {report['session'][:8]} — {report['status']} (Claude Code {versions})"]
    if report["reason"]:
        out.append(f"  {report['status']}: {report['reason']}")
    counts = report["counts"]
    prompts = "prompts from you: not counted" if counts["human_prompts"] is None else \
        f"{counts['human_prompts']:,} prompt{'' if counts['human_prompts'] == 1 else 's'} from you"
    denied = sum(counts["denials"].values())
    line = [prompts, f"{_plural(counts['tool_calls'], 'tool call')}, {counts['tool_errors']:,} failed (sub-agents included)"]
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
            out.append(f"- {_skill(row)}: {_n(row['output_tokens'])} "
                       f"({_plural(row['messages'], 'message')}, {_plural(row['tool_calls'], 'tool call')})")
        if any(row["skill"] is None for row in report["by_skill"]):
            out.append("  (no skill): output Claude Code attributes to no skill. "
                       "A sub-agent counts under the skill its rows name: from 2.1.325 to 2.1.331 at least, "
                       "the skill that started it.")
    if notes:
        out.append("Your notes on this session:")
        out += [f"- {note}" for note in notes]
    if running:
        out.append("This session is still running: the turn in progress is not counted, and the totals are "
                   "the last ones Claude Code recorded.")
    out.append(f"Written to {shown} ({where}).")
    return "\n".join(out) + "\n"


def _skill(row: dict[str, Any]) -> str:
    """A skill's name, with its plugin when the name does not already carry it."""
    skill, plugin = row.get("skill"), row.get("plugin")
    if skill is None:
        return "(no skill)" + (f" [{plugin}]" if plugin else "")
    return skill if not plugin or skill.startswith(f"{plugin}:") else f"{skill} [{plugin}]"


def render_list(folder: str) -> str:
    files = sorted(glob.glob(os.path.join(glob.escape(folder), "*.json")))
    lines, broken, states = [], [], {}
    for path in files:
        try:
            with open(path, encoding="utf-8") as fh:
                report = json.load(fh)
            totals = report["totals"] or {}
            cost, prompts = _cost(totals.get("cost_usd_estimate")), _count(report["counts"]["human_prompts"])
            started = report.get("started_at")
            started = started if isinstance(started, str) and TIMESTAMP.fullmatch(started) else None
            if report["status"] not in STATUSES or not SESSION_ID.fullmatch(report["session"]):
                raise ValueError("not a session file")      # nothing of a file that is not ours is printed
            top = [{"skill": _name(row.get("skill"), SKILL), "plugin": _name(row.get("plugin"), PLUGIN),
                    "output_tokens": _count(row.get("output_tokens"))} for row in report["by_skill"][:3]]
            states[report["status"]] = states.get(report["status"], 0) + 1
            lines.append((started or "",
                          f"- {(started or '?')[:10]} {report['session'][:8]} {report['status']}: "
                          + ("prompts not counted" if prompts is None else _plural(prompts, "prompt") + " from you")
                          + f", {_n(_count(totals.get('output_tokens')))} output tokens"
                          + (f", about ${cost:,.2f}" if cost is not None else "")
                          + "; top: " + (", ".join(f"{_skill(row)} {_n(row['output_tokens'])}" for row in top)
                                         or "nothing")))
        except (OSError, ValueError, KeyError, TypeError, AttributeError, RecursionError):
            broken.append(os.path.basename(path))
    notes = _notes(folder)
    loose = [row["note"] for row in notes if not row.get("session")]
    if not lines and not broken and not notes:
        return "No session measured yet. `harness session measure` at the end of a session writes one.\n"
    split = ", ".join(f"{count} {state}" for state, count in sorted(states.items()))
    out = [f"{_plural(len(lines), 'session file')}" + (f": {split}" if split else "")
           + f"; {_plural(len(notes), 'note')} (dollars are estimates at list price)"]
    out += [text for _, text in sorted(lines)]
    out += [f"- {name}: not readable, left out" for name in broken]
    if loose:
        out.append("Notes attached to no session:")
        out += [f"- {note}" for note in loose]
    return "\n".join(out) + "\n"


# --- entry -------------------------------------------------------------------------------------

def _measure(args: argparse.Namespace, repo: str) -> int:
    if args.transcript and args.session:
        raise Refused("give --session or --transcript, not both")
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
    now = _now(args.now)
    try:
        report = measure(transcript, session_id, now)
    except OSError as exc:
        raise Refused(f"the transcript cannot be read: {exc.strerror}") from exc
    text = json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    folder = _folder(repo, args.harness_dir)
    _write(folder, session_id + ".json", text, "w")
    if args.format == "json":
        sys.stdout.write(text)
    else:
        shown = "/".join([args.harness_dir, FOLDER, session_id + ".json"])
        running = session_id == _running_session()
        sys.stdout.write(render(report, read_notes(folder, session_id), shown,
                                kept(repo, folder, session_id + ".json"), running))
    return 1 if report["status"] == "unmeasured" else 0


def _note(args: argparse.Namespace, repo: str) -> int:
    text = _plain(args.text)
    if not text:
        raise Refused("the note is empty: say in your own words what suits you or not")
    if len(text) > MAX_NOTE:
        raise Refused(f"the note is {len(text):,} characters long: {MAX_NOTE:,} at most")
    now, running = _now(args.now), _running_session()
    folder = _folder(repo, args.harness_dir)
    _write(folder, NOTES, json.dumps({"at": now, "session": running, "note": text}, ensure_ascii=False) + "\n", "a")
    where = f"attached to session {running[:8]}" if running else \
        "attached to no session (not run from Claude Code): `harness session list` shows it"
    print(f"Noted in {'/'.join([args.harness_dir, FOLDER, NOTES])}, {where} ({kept(repo, folder, NOTES)}).")
    return 0


def main(args: argparse.Namespace) -> int:
    try:
        if not os.path.isdir(args.repo):
            raise Refused(f"{args.repo} is not a directory")
        repo = os.path.realpath(args.repo)
        if args.action == "measure":
            return _measure(args, repo)
        if args.action == "note":
            return _note(args, repo)
        sys.stdout.write(render_list(_place(repo, args.harness_dir)))
        return 0
    except Refused as exc:
        print(f"harness session: {exc}", file=sys.stderr)
        return 2
    except OSError as exc:
        print(f"harness session: {exc.strerror or exc}", file=sys.stderr)
        return 2
