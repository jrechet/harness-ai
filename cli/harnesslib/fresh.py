"""What has aged in a repository's harness: the loop against obsolescence, without a model.

The rules of AGENTS.md already had their signals (date, harvest, references without a target). A skill
or an agent had none: it keeps citing a renamed file, a removed target, a replaced model, and nobody
sees it. This module reads the skills and agents of the repository and confronts them with the git
history:
- **broken**: it cites a path the repository had and no longer has, or a vanished `make` target /
  `npm` script; a rule cites a guardrail that no longer exists;
- **to review**: what it cites changed since its last reading, it has not moved for a long time, it
  names a model, the harvest or the audit is old, a rule is more than a year old without a guardrail.

A path git never saw is not judged: a skill often talks about the files of another repository.
Without git, only the rule signals are returned. Plugged into a session-start hook (`--hook`), it says
nothing as long as nothing is broken or late."""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import date
from typing import Any

from . import facts, maturity, rules

LAG_DAYS = 30          # what a skill cites changed longer ago than this without the skill being reread
IDLE_DAYS = 180        # a skill or an agent nobody touched since
AUDIT_DAYS = 180       # an older audit no longer describes the repository
MAX_PROBES = 20        # at most this many searches in the history of a Makefile or a manifest
RULE_DAYS = 365        # a rule without a guardrail older than a year goes back to the relevance review
STATES = ("broken", "to review")
_CODE = re.compile(r"```.*?```|`[^`\n]+`", re.DOTALL)
_SKIP_TOKEN = re.compile(r"[<>*${}|=…]|^-|^~|://|^@")
_MODEL = re.compile(r"\bclaude-(?:\d|opus|sonnet|haiku|fable|instant)[\w.-]*|\b(?:opus|sonnet|haiku)[ -]?\d(?:\.\d)?\b"
                    r"|\bgpt-\d[\w.-]*|\bgemini-\d[\w.-]*", re.IGNORECASE)
_MAKE = re.compile(r"\bmake\s+(?:-C\s+\S+\s+)?([A-Za-z0-9][\w.-]*)")
_NPM = re.compile(r"\b(?:npm|pnpm|yarn)\s+run\s+([\w:.-]+)")
_TARGET = re.compile(r"^([A-Za-z0-9][^:=#\t]*?)\s*:(?![:=])", re.MULTILINE)


def _git(repo: str, *args: str, stdin: bytes | None = None) -> str | None:
    try:
        out = subprocess.run(["git", "-C", repo, "-c", "core.quotepath=false", *args], capture_output=True, timeout=120,
                             input=stdin)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return out.stdout.decode("utf-8", "replace") if out.returncode in (0, 1) else None


def is_repo(repo: str) -> bool:
    """A git repository with at least one commit: without history, nothing can be confronted."""
    return bool((_git(repo, "rev-parse", "--verify", "--quiet", "HEAD") or "").strip())


def last_dates(repo: str, paths: list[str], deleted_only: bool = False) -> dict[str, str]:
    """The date of the last commit that touches each of these paths (or deletes them, with
    `deleted_only`). A single call, limited to the requested paths: the cost follows the number of
    citations, not the size of the whole history."""
    found: dict[str, str] = {}
    for start in range(0, len(paths), 400):
        args = ["--literal-pathspecs", "log", "--no-renames", "-z", "--name-only", "--relative", "--format=%x01%cs%x01"]
        out = _git(repo, *args, *(["--diff-filter=D"] if deleted_only else []), "--", *paths[start:start + 400]) or ""
        day = ""
        for part in out.split("\0"):
            match = re.match(r"^\n*\x01(\d{4}-\d{2}-\d{2})\x01\n*(.*)$", part, re.DOTALL)
            day, name = (match[1], match[2]) if match else (day, part)
            if name.strip("\n"):
                found.setdefault(name.strip("\n"), day)
    return found


def ignored(repo: str, paths: list[str]) -> set[str]:
    """Those of these paths that .gitignore excludes: a locally produced file is not a vanished file."""
    if not paths:
        return set()
    out = _git(repo, "check-ignore", "-z", "--stdin", stdin="\0".join(paths).encode("utf-8")) or ""
    return {p for p in out.split("\0") if p}


def tools(repo: str) -> list[dict[str, str]]:
    """The skills and agents of the repository, outside test data and copies of the repository (worktrees, sub-repositories)."""
    found = []
    for root, dirs, names in os.walk(repo):
        dirs[:] = sorted(d for d in dirs if d not in facts.SKIP_DIRS and d != "worktrees"
                         and not os.path.exists(os.path.join(root, d, ".git")))
        rel_root = os.path.relpath(root, repo).replace(os.sep, "/")
        for name in sorted(names):
            rel = name if rel_root == "." else f"{rel_root}/{name}"
            if name == "SKILL.md":
                found.append({"path": rel, "kind": "skill"})
            elif name.endswith(".md") and os.path.basename(root) == "agents" and (
                    ".claude" in rel_root.split("/") or os.path.isdir(os.path.join(os.path.dirname(root), "skills"))
                    or os.path.isdir(os.path.join(os.path.dirname(root), ".claude-plugin"))):
                found.append({"path": rel, "kind": "agent"})
    return found


def _read(repo: str, rel: str) -> str:
    try:
        with open(os.path.join(repo, rel), encoding="utf-8", errors="replace") as fh:
            return fh.read(1_000_000)
    except OSError:
        return ""


def cited_paths(text: str) -> list[str]:
    """What, in the code of a text or the target of a link, has the shape of a relative path: at least
    one `/`, no variable."""
    seen: list[str] = []
    spans = [span.strip("`") for span in _CODE.findall(text)] + re.findall(r"\]\(([^)\s#]+)", text)
    for span in spans:
        for token in span.split():
            token = re.sub(r":\d+(?:-\d+)?$", "", token.strip("'\"`(),;")).rstrip(".:").removeprefix("./")
            if ("/" in token.strip("/") or (token.endswith("/") and len(token) > 2)) and not _SKIP_TOKEN.search(token) and not token.startswith("/") and token not in seen:
                seen.append(token)
    return seen


def _bases(rel: str) -> list[str]:
    """Where a cited path can start from: the root, the tool's folder, the root of its plugin."""
    folder = os.path.dirname(rel)
    plugin = os.path.dirname(os.path.dirname(folder)) if os.path.basename(rel) == "SKILL.md" else os.path.dirname(folder)
    out = []
    for base in ("", folder, plugin):
        if base not in out:
            out.append(base)
    return out


def _join(base: str, token: str) -> str:
    return os.path.normpath(os.path.join(base, token)).replace(os.sep, "/")


def _days(day: str | None, today: date) -> int | None:
    try:
        return (today - date.fromisoformat(day)).days if day else None
    except ValueError:
        return None


def _gone_targets(repo: str, code: str, cache: dict[str, bool]) -> list[str]:
    """The cited `make` targets and `npm run` scripts that the repository had and no longer has. Judged
    only when they read unambiguously: root Makefile without `include`, command without `-C`."""
    gone = []
    makefile = _read(repo, "Makefile") if os.path.isfile(os.path.join(repo, "Makefile")) else None
    if makefile is not None and not re.search(r"^-?include\b", makefile, re.MULTILINE):
        present = {n for group in _TARGET.findall(makefile) for n in group.split()}
        for target in sorted(set(_MAKE.findall(code)) - present):
            key = f"make {target}"
            if key not in cache and len(cache) < MAX_PROBES:
                cache[key] = bool((_git(repo, "log", "-1", "--format=%H", f"-G^{re.escape(target)}\\s*:", "--", "Makefile") or "").strip())
            if cache.get(key):
                gone.append(key)
    try:
        scripts = json.loads(_read(repo, "package.json")).get("scripts")
    except (ValueError, AttributeError):
        scripts = None
    if isinstance(scripts, dict):
        for script in sorted(set(_NPM.findall(code)) - set(scripts)):
            key = f"npm run {script}"
            if key not in cache and len(cache) < MAX_PROBES:
                cache[key] = bool((_git(repo, "log", "-1", "--format=%H", f'-G"{re.escape(script)}"\\s*:', "--", "package.json") or "").strip())
            if cache.get(key):
                gone.append(key)
    return gone


def collect(repo: str, today: date | None = None, fast: bool = False) -> dict[str, Any]:
    """`fast` (the hook) skips what costs one git call per rule or per target."""
    today = today or date.today()
    repo = os.path.abspath(repo)
    has_git = is_repo(repo)
    found = tools(repo)
    items: list[dict[str, Any]] = []
    plans = []
    for tool in found:
        text = _read(repo, tool["path"])
        alive, missing = [], {}
        for token in cited_paths(text):
            candidates = [_join(base, token) for base in _bases(tool["path"])]
            hit = next((c for c in candidates if os.path.exists(os.path.join(repo, c))), None)
            if hit:
                alive.append(hit)
            else:
                missing[token] = [c for c in candidates if not c.startswith("..")]
        plans.append((tool, text, alive, missing))
    gone: dict[str, str] = {}
    dates: dict[str, str] = {}
    skipped: set[str] = set()
    if has_git:
        wanted = sorted({c for _, _, _, missing in plans for cs in missing.values() for c in cs})
        gone = last_dates(repo, wanted, deleted_only=True)
        # tracked by git but absent from disk: deleted, not committed yet
        tracked = _git(repo, "--literal-pathspecs", "ls-files", "-z", "--", *wanted[:400]) or ""
        gone.update({p: "" for p in tracked.split("\0") if p and not os.path.exists(os.path.join(repo, p))})
        skipped = ignored(repo, wanted)
        files = sorted({t["path"] for t, _, _, _ in plans} | {a for _, _, alive, _ in plans for a in alive
                                                              if os.path.isfile(os.path.join(repo, a))})
        dates = last_dates(repo, files)
    probes: dict[str, bool] = {}
    for tool, text, alive, missing in plans:
        def add(state: str, signal: str, what: str, evidence: str, action: str, tool: dict[str, str] = tool) -> None:
            items.append({"state": state, "signal": signal, "kind": tool["kind"], "path": tool["path"], "what": what,
                          "evidence": evidence, "action": action})

        models = sorted({m.group(0) for m in _MODEL.finditer(text)})
        if models:
            add("to review", "model", "It names a model", ", ".join(models[:4]),
                "Remove the model name, or reread it at every model change: the instruction may have become useless.")
        if not has_git:
            continue
        dead = [token for token, candidates in missing.items()
                if any(c not in skipped and (c in gone or any(g.startswith(c.rstrip("/") + "/") for g in gone)) for c in candidates)]
        if dead:
            add("broken", "reference", "It cites what the repository had and no longer has", ", ".join(dead[:5]),
                "Fix the reference (the file was renamed or deleted), or remove the step that depends on it.")
        targets = [] if fast else _gone_targets(repo, "\n".join(_CODE.findall(text)), probes)
        if targets:
            add("to review", "target", "It cites a target or a script the repository had and no longer has", ", ".join(targets[:5]),
                "Check whether it talks about this repository: if so, fix the command.")
        mine = dates.get(tool["path"])
        moved = [f"{a} ({dates[a]})" for a in dict.fromkeys(alive) if a in dates and mine and dates[a] > mine
                 and (_days(mine, today) or 0) - (_days(dates[a], today) or 0) > LAG_DAYS]
        if moved:
            add("to review", "change", f"What it cites changed since its last reading ({mine})", ", ".join(moved[:4]),
                "Reread the tool next to these files: a step may describe a behaviour that no longer exists.")
        idle = _days(mine, today)
        if idle is not None and idle > IDLE_DAYS:
            add("to review", "idle", f"Nobody touched it for {idle} days", mine or "",
                "Replay it on a real case or a fixture: if it still serves as is, note the date of the check.")

    def note(state: str, signal: str, path: str, what: str, evidence: str, action: str) -> None:
        items.append({"state": state, "signal": signal, "kind": "instructions", "path": path, "what": what,
                      "evidence": evidence, "action": action})

    collected = facts.collect(repo, today=today)
    state = maturity.evaluate(collected)
    source = collected["instructions"]["source"].get("path") or "AGENTS.md"
    for ref in state["dangling"]:
        note("broken", "guardrail", f"{source}:{ref.get('line')}", "A rule cites a guardrail or a contract that does not exist",
             str(ref.get("ref")), "Repair the reference, or mark the rule (unverified): it no longer is.")
    age = collected.get("harvest_marker_age_days")
    if isinstance(age, int) and age > maturity.MAX_MARKER_AGE_DAYS:
        note("to review", "harvest", source, f"The last harvest is {age} days old", f"threshold: {maturity.MAX_MARKER_AGE_DAYS} days",
             "Run harness-harvest: recent incidents have not become rules yet.")
    audit_age = _days((collected.get("audit") or {}).get("date"), today)
    if audit_age is not None and audit_age > AUDIT_DAYS:
        note("to review", "audit", ".harness/audit.json", f"The last audit is {audit_age} days old", f"threshold: {AUDIT_DAYS} days",
             "Run harness-audit again, at least its relevance review.")
    old = [r for r in rules.collect(repo, today, blame=not fast) if (r["age_days"] or 0) > RULE_DAYS and not r["guarded"]]
    if old:
        note("to review", "rules", old[0]["file"], f"{len(old)} rule(s) more than a year old without a guardrail",
             ", ".join(f"{r['file']}:{r['line']}" for r in old[:4]),
             "Put them through the relevance review of harness-audit: do they still change what the agent does?")
    order = {s: n for n, s in enumerate(STATES)}
    items.sort(key=lambda i: (order[i["state"]], i["path"], i["signal"]))
    return {"date": today.isoformat(), "git": has_git, "tools": len(found),
            "counts": {s: sum(i["state"] == s for i in items) for s in STATES}, "items": items}


def render_md(result: dict[str, Any]) -> str:
    counts = result["counts"]
    out = [f"Harness freshness on {result['date']}: {counts['broken']} broken, {counts['to review']} to review, "
           f"over {result['tools']} skill(s) and agent(s) and the instructions."]
    if not result["git"]:
        out.append("No git repository, or no commit yet: the skills and agents are not confronted with the history.")
    for item in result["items"]:
        out += [f"- **{item['state']}** — `{item['path']}` : {item['what']}" + (f" ({item['evidence']})" if item["evidence"] else "") + ".",
                f"  {item['action']}"]
    if not result["items"]:
        out.append("Nothing has aged according to what is measured. What is not measured: an instruction right yesterday, useless today.")
    return "\n".join(out) + "\n"


LABELS = {"reference": "skill(s) or agent(s) cite a file the repository no longer has",
          "guardrail": "rule(s) cite a guardrail that cannot be found",
          "harvest": "harvest late", "audit": "audit too old"}


def render_hook(result: dict[str, Any]) -> str:
    """Two lines at most, and nothing at all if nothing is broken or late: a reminder that speaks at
    every session is no longer read. Counts only: no text from the repository enters the session's
    context this way, a file name could carry an instruction."""
    counts = {signal: sum(i["signal"] == signal for i in result["items"]) for signal in LABELS}
    said = [f"{n} {LABELS[signal]}" if signal in ("reference", "guardrail") else LABELS[signal]
            for signal, n in counts.items() if n]
    if not said:
        return ""
    return f"harness fresh: {'; '.join(said)}.\nDetails and what to do: python3 cli/harness.py fresh\n"


def build_parser(parser: argparse.ArgumentParser | None = None) -> argparse.ArgumentParser:
    p = parser or argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("repo", nargs="?", default=".")
    p.add_argument("--format", choices=["md", "json"], default="md")
    p.add_argument("--hook", action="store_true", help="short output for a session-start hook, empty if nothing is urgent")
    p.add_argument("--strict", action="store_true", help="exits with 1 if something is broken (for a scheduled job)")
    p.add_argument("--today", help=argparse.SUPPRESS)
    return p


def main(argv: list[str] | None = None, args: argparse.Namespace | None = None) -> int:
    args = args or build_parser().parse_args(argv)
    try:
        today = date.fromisoformat(args.today) if args.today else None
    except ValueError:
        print(f"harness fresh: --today {args.today!r} is not a YYYY-MM-DD date", file=sys.stderr)
        return 2
    if not os.path.isdir(args.repo):
        print(f"harness fresh: {args.repo} is not a directory", file=sys.stderr)
        return 0 if args.hook else 2
    if args.hook:
        try:  # a session-start hook must never prevent work, nor exit with anything but 0
            text = render_hook(collect(args.repo, today, fast=True))
            raw = getattr(sys.stdout, "buffer", None)   # as bytes: an ASCII console does not make the hook fail
            if raw is None:
                sys.stdout.write(text)
            else:
                raw.write(text.encode("utf-8", "replace"))
                raw.flush()
        except Exception as exc:
            print(f"harness fresh: measurement impossible ({type(exc).__name__})", file=sys.stderr)
        return 0
    result = collect(args.repo, today)
    sys.stdout.write(json.dumps(result, ensure_ascii=False, indent=2) + "\n" if args.format == "json" else render_md(result))
    return 1 if args.strict and result["counts"]["broken"] else 0
