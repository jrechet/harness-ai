"""The prerequisites of a delivery: what a program can say before a human deploys.

`/ship` prepares and proposes, it does not deploy. This module says four things about what would ship:
- **state**: we deliver the head commit of the delivery branch, nothing else, and nothing uncommitted;
- **checks**: the CI is green on that exact commit, according to a CI report given as input;
- **zones**: what changed since the last version in a zone where a rollback is costly;
- **breaking**: the changes announced as breaking since the last version.

It also proposes a version number and notes, drawn from the commits. It sets no tag, pushes nothing,
calls no network. Commit titles come from third parties: they are rendered with nothing active."""
from __future__ import annotations

import os
import re
import time
from typing import Any

from . import qa, review, size
from .context import Refused, _git, resolve_base

OK, FAIL, UNKNOWN = qa.OK, qa.FAIL, qa.UNKNOWN
MAX_COMMITS = 500
MAX_SUBJECT = 140
MAX_SHOWN = 8
_TYPE = re.compile(r"^([a-zA-Z]{2,12})(?:\([^()\n]{0,40}\))?(!)?:\s?(.{0,400})")
_BREAKING = re.compile(r"^\s{0,8}BREAKING[ -]CHANGES?\b", re.MULTILINE | re.IGNORECASE)
MAX_FETCH_AGE = 24 * 3600   # beyond that, the remote branch known here no longer proves what is pushed
_VERSION = re.compile(r"^(v?)(\d{1,6})\.(\d{1,6})\.(\d{1,6})$")
TITLES = {"feat": "Features", "fix": "Fixes", "perf": "Performance", "refactor": "Refactoring",
          "docs": "Documentation", "test": "Tests", "chore": "Maintenance", "ci": "Maintenance", "build": "Maintenance"}
ORDER = ("Features", "Fixes", "Performance", "Refactoring", "Documentation", "Tests", "Maintenance", "Other")
_LEAD = re.compile(r"^(?:[#\-+*~=]|\d{1,9}[.)])")   # at the start, would open a heading or a list in the rendering
_GOOD = {"success", "skipped", "neutral", "pass", "skipping"}
_WAIT = {"queued", "in_progress", "pending", "waiting", "requested", "expected", "action_required"}


class NothingToDeliver(Refused):
    """No commit since the previous version. A refusal for `ship check`; a pipeline run on each push says it and passes."""


def _gate(ident: str, title: str, status: str, evidence: str, action: str | None = None) -> dict[str, Any]:
    return {"id": ident, "title": title, "status": status, "evidence": evidence, "action": None if status == OK else action}


def _plain(text: str, limit: int = MAX_SUBJECT) -> str:
    """A text from a commit or a CI report, ready to be rendered: no link, image, mention or tag, and no
    heading or list opened by its first character."""
    text = " ".join("".join(ch if ch.isprintable() else " " for ch in text).split())
    text = text[:limit] + ("…" if len(text) > limit else "")
    for old, new in (("<", "‹"), (">", "›"), ("`", "'"), ("](", "] ("), ("![", "["), ("@", "@​"), ("|", "/"),
                     ("://", ": //"), ("www.", "www​."), ("#", "#​")):
        text = text.replace(old, new)
    return _LEAD.sub(lambda m: "\\" + m[0], text) or "(untitled)"


def _more(items: list[str]) -> str:
    extra = len(items) - MAX_SHOWN
    return "; ".join(items[:MAX_SHOWN]) + (f"; and {extra} more" if extra > 0 else "")


def _text(repo: str, *args: str) -> str:
    code, out = _git(repo, *args)
    if code != 0:
        raise Refused(f"git {args[0]} failed in {repo}")
    return out.decode("utf-8", "replace").strip()


def last_version(repo: str) -> tuple[str | None, bool]:
    """The previous version: the highest X.Y.Z tag already in the history of HEAD (not the nearest: a merged
    hotfix branch carries an older one). Without a tag of that form, the nearest tag, and the fact that it is
    not a version. None if the repository has no reachable tag."""
    code, out = _git(repo, "tag", "--merged", "HEAD")
    versions = []
    for name in out.decode("utf-8", "replace").split("\n") if code == 0 else []:
        match = _VERSION.match(name.strip())
        if match:
            versions.append(((int(match[2]), int(match[3]), int(match[4])), name.strip()))
    if versions:
        return max(versions)[1], True
    code, out = _git(repo, "describe", "--tags", "--abbrev=0", "HEAD")
    return (out.decode("utf-8", "replace").strip(), False) if code == 0 and out.strip() else (None, False)


def commits(repo: str, since: str | None) -> list[dict[str, Any]]:
    span = f"{since}..HEAD" if since else "HEAD"
    code, out = _git(repo, "log", "--no-merges", f"--max-count={MAX_COMMITS + 1}", "--format=%h%x00%s%x00%b%x01", span)
    if code != 0:
        raise Refused(f"unreadable history since {since or 'the beginning'}")
    found = []
    for entry in out.decode("utf-8", "replace").split("\x01"):
        parts = entry.strip("\n").split("\0")
        if len(parts) != 3 or not parts[0]:
            continue
        sha, subject, body = parts
        match = _TYPE.match(subject)
        kind = match[1].lower() if match else None
        found.append({"sha": sha, "type": kind if kind in TITLES else None, "subject": _plain(match[3] if match and kind in TITLES else subject),
                      "breaking": bool(match and match[2]) or bool(_BREAKING.search(body)) or bool(_BREAKING.search(subject))})
    return found


def propose_version(previous: str | None, found: list[dict[str, Any]]) -> tuple[str | None, str]:
    """The next version according to the commits, and the reason. Without a readable tag, no proposal."""
    if previous is None:
        return None, "no tag in the repository: the first number is a decision"
    match = _VERSION.match(previous)
    if not match:
        return None, f"the last tag ({_plain(previous, 40)}) is not of the form X.Y.Z"
    prefix, major, minor, patch = match[1], int(match[2]), int(match[3]), int(match[4])
    if any(c["breaking"] for c in found):
        nxt, why = ((major + 1, 0, 0), "a change announced as breaking") if major else ((0, minor + 1, 0), "a breaking change, before 1.0")
    elif any(c["type"] == "feat" for c in found):
        nxt, why = (major, minor + 1, 0), "at least one feature"
    else:
        nxt, why = (major, minor, patch + 1), "fixes only"
    return f"{prefix}{nxt[0]}.{nxt[1]}.{nxt[2]}", why


def _fetch_age(repo: str) -> float | None:
    code, out = _git(repo, "rev-parse", "--git-path", "FETCH_HEAD")
    path = out.decode("utf-8", "replace").strip()
    try:
        return time.time() - os.path.getmtime(path if os.path.isabs(path) else os.path.join(repo, path)) if code == 0 else None
    except OSError:
        return None


def gate_state(repo: str, base: str, pipeline: bool = False) -> dict[str, Any]:
    title = "We deliver the head commit of the delivery branch, pushed and fully committed"
    target = _text(repo, "rev-parse", "--verify", f"{resolve_base(repo, base)}^{{commit}}")   # in full, like HEAD
    head = _text(repo, "rev-parse", "HEAD")
    # a pipeline examines a commit and leaves its tools beside it, untracked; a changed tracked file still counts
    dirty = _text(repo, "status", "--porcelain", *(["--untracked-files=no"] if pipeline else []))
    shown = _plain(base, 60)
    problems = []
    if head != target:
        behind = _git(repo, "merge-base", "--is-ancestor", head, target)[0] == 0
        problems.append(f"HEAD ({head[:7]}) is not the head of {shown} ({target[:7]})"
                        + (": it is behind" if behind else ": it carries commits that are not there"))
    if dirty:
        problems.append(f"{len(dirty.splitlines())} uncommitted file(s)")
    if problems:
        return _gate("state", title, FAIL, "; ".join(problems),
                     "Move to the head of the delivery branch, up to date, with nothing local. We do not deliver a workstation.")
    code, out = _git(repo, "rev-parse", "--symbolic-full-name", base)
    if code != 0 or not out.decode("utf-8", "replace").strip().startswith("refs/remotes/"):
        # a local branch, HEAD or a commit given as base: HEAD is compared with itself, and nothing says it is pushed
        return _gate("state", title, UNKNOWN, f"{head[:7]}; {shown} is not a remote branch: nothing says this commit is pushed",
                     "Run again with the remote delivery branch as --base (origin/main, for example), after a git fetch.")
    age = _fetch_age(repo)
    if age is None or age > MAX_FETCH_AGE:
        said = "no known fetch" if age is None else f"last fetch {int(age // 3600)} h ago"
        return _gate("state", title, UNKNOWN, f"{head[:7]}, head of {shown} as known here; {said}",
                     "Run git fetch, then run again: the remote branch may have moved since.")
    return _gate("state", title, OK, f"{head[:7]}, head of {shown} at the last fetch, {int(age // 60)} min ago")


def gate_checks(repo: str, checks: Any) -> dict[str, Any]:
    """The CI report, as `gh run list --commit <sha> --json name,status,conclusion,headSha` gives it.
    A report that does not say its commit, or speaks of another one, proves nothing for this one."""
    title = "The CI is green on this commit"
    if checks is None:
        return _gate("checks", title, UNKNOWN, "no CI report given",
                     "Fetch the CI report of the commit and run again with --checks <file>. Without CI, say so: a human decides.")
    if not isinstance(checks, list) or not all(isinstance(c, dict) for c in checks):
        raise Refused("--checks: a JSON list of objects (name, status, conclusion, headSha)")
    if not checks:
        return _gate("checks", title, UNKNOWN, "the report is empty: no check ran on this commit",
                     "Check that the repository has a CI and that it started.")
    head = _text(repo, "rev-parse", "HEAD")
    shas = {c["headSha"].strip().lower() if isinstance(c.get("headSha"), str) and c["headSha"].strip() else None for c in checks}
    if not all(s is not None and len(s) >= 7 and head.startswith(s) for s in shas):
        if None in shas:
            return _gate("checks", title, UNKNOWN, "the report does not say which commit it covers",
                         "Fetch it with headSha, for this exact commit.")
        other = sorted(s[:7] for s in shas if s and all(ch in "0123456789abcdef" for ch in s) and not head.startswith(s))
        return _gate("checks", title, FAIL, f"the report covers another commit than {head[:7]}" + (f": {', '.join(other[:3])}" if other else ""),
                     "Fetch the CI report of this exact commit: a green CI on a neighbouring commit says nothing about this one.")
    bad, waiting, ran = [], [], 0
    for item in checks:
        name = _plain(str(item.get("name") or "unnamed"), 50)
        words = {str(item.get(k) or "").lower() for k in ("conclusion", "bucket", "state")} - {""}
        status = str(item.get("status") or "").lower()
        if words - _GOOD - _WAIT:
            bad.append(name)
        elif not words or words & _WAIT or status in _WAIT:
            waiting.append(name)       # a green conclusion on a run still in progress is not an end
        else:
            ran += bool(words & {"success", "pass"})
    if bad:
        return _gate("checks", title, FAIL, "failed: " + _more(sorted(set(bad))),
                     "Fix the cause on the branch, through a PR. We do not deliver by re-running until green.")
    if waiting:
        return _gate("checks", title, UNKNOWN, "in progress: " + _more(sorted(set(waiting))), "Wait for the end.")
    if not ran:
        return _gate("checks", title, UNKNOWN, f"{len(checks)} check(s), all skipped: nothing ran on this commit",
                     "Check why the CI ran nothing (path filter, condition) before delivering.")
    return _gate("checks", title, OK, f"{len(checks)} green check(s) on {head[:7]}; the report is taken on trust")


def gate_zones(repo: str, since: str | None, zones: list[dict[str, str]]) -> dict[str, Any]:
    title = "Nothing ships in a zone where a rollback is costly"
    if since is None:
        return _gate("zones", title, UNKNOWN, "no previous version: the whole repository ships for the first time",
                     "Have a human review what the first delivery commits to.")
    code, out = _git(repo, "diff", "-z", "--name-only", "--no-renames", f"{since}..HEAD")
    if code != 0:
        raise Refused(f"cannot diff since {since}")
    paths = [p for p in out.decode("utf-8", "replace").split("\0") if p]
    hits = size.touched(paths, zones)
    if not hits:
        return _gate("zones", title, OK, f"{len(paths)} file(s) changed, none in a sensitive zone")
    return _gate("zones", title, UNKNOWN, _more([f"{_plain(h['path'], 80)} ({_plain(h['glob'], 40)})" for h in hits]),
                 "For each, write how we roll back and who decides it, before delivering.")


def gate_breaking(found: list[dict[str, Any]], truncated: bool) -> dict[str, Any]:
    title = "No breaking change is waiting to be announced"
    breaking = [f"{c['sha']} {c['subject']}" for c in found if c["breaking"]]
    untyped = sum(c["type"] is None for c in found)
    said = (["announced as breaking: " + _more(breaking)] if breaking else []) + \
           ([f"{untyped} commit(s) without a readable type: nothing says whether they break"] if untyped else []) + \
           ([f"more than {MAX_COMMITS} commits, the oldest not read"] if truncated else [])
    if said:
        return _gate("breaking", title, UNKNOWN, "; ".join(said),
                     "Tell those who depend on it what breaks and how to migrate, and review the untyped commits: "
                     "the gate reads only what a title announces.")
    return _gate("breaking", title, OK, f"{len(found)} commit(s), none announced as breaking; an unannounced breaking change is not seen here")


def check(table: dict[str, Any], repo: str, base: str, since: str | None = None, checks: Any = None,
          pipeline: bool = False) -> dict[str, Any]:
    if _text(repo, "rev-parse", "--is-shallow-repository") == "true":
        raise Refused("shallow clone: history and tags are missing, run git fetch --unshallow --tags")
    if since is not None:
        if since.startswith("-") or _git(repo, "rev-parse", "--verify", "--quiet", f"{since}^{{commit}}")[0] != 0:
            raise Refused(f"--since {_plain(since, 60)}: neither a tag nor a commit of this repository")
        if _git(repo, "merge-base", "--is-ancestor", since, "HEAD")[0] != 0:
            raise Refused(f"--since {_plain(since, 60)} is not in the history of HEAD: it is not the previous version of this branch")
        previous, is_version = since, bool(_VERSION.match(since))
    else:
        previous, is_version = last_version(repo)
    found = commits(repo, previous)
    truncated = len(found) > MAX_COMMITS
    found = found[:MAX_COMMITS]
    if not found:
        raise NothingToDeliver(f"no commit since {_plain(previous or '', 60)}: nothing to deliver")
    version, why = propose_version(previous if is_version else None, found)
    if previous and not is_version:
        version, why = None, f"{_plain(previous, 40)} is not a tag of the form X.Y.Z: it may not be the last delivered version"
    if version and _text(repo, "tag", "-l", version):
        version, why = None, f"{version} already exists in the repository, on another branch"
    if truncated:
        version, why = None, f"more than {MAX_COMMITS} commits since the previous version, the oldest not read"
    gates = [gate_state(repo, base, pipeline), gate_checks(repo, checks), gate_zones(repo, previous, size.zones(table, repo, base)),
             gate_breaking(found, truncated)]
    notes: dict[str, list[str]] = {}
    for commit in found:
        notes.setdefault(TITLES.get(commit["type"] or "", "Other"), []).append(
            f"{commit['subject']} ({commit['sha']})" + (" — BREAKING" if commit["breaking"] else ""))
    failed = [g["id"] for g in gates if g["status"] == FAIL]
    unknown = [g["id"] for g in gates if g["status"] == UNKNOWN]
    return {"pass": not failed and not unknown, "failed": failed, "unknown": unknown, "gates": gates,
            "previous": _plain(previous, 60) if previous else None, "since_given": since is not None, "truncated": truncated,
            "version": version, "version_why": why,
            "commits": len(found), "notes": {title: notes[title] for title in ORDER if title in notes}}


def render_md(result: dict[str, Any]) -> str:
    if result["failed"]:
        head = f"Delivery: {len(result['failed'])} prerequisite(s) failed. Do not deliver."
    elif result["unknown"]:
        head = f"Delivery: nothing failed, {len(result['unknown'])} prerequisite(s) for a human to clear."
    else:
        head = "Delivery: the four prerequisites pass. The decision to deliver stays with a human."
    out = [head]
    for gate in result["gates"]:
        out.append(f"- {gate['status']} — {gate['title']} ({gate['evidence']})" + (f". {gate['action']}" if gate["action"] else ""))
    span = (f"Since {result['previous']}" + (" (given by --since, not the last version tag)" if result["since_given"] else "")
            if result["previous"] else "Since the beginning of the repository")
    count = f"the {result['commits']} most recent commits, the oldest not read" if result["truncated"] else f"{result['commits']} commit(s)"
    out += ["", f"{span}: {count}.",
            (f"Proposed version: {result['version']} ({result['version_why']})." if result["version"]
             else f"No proposed version: {result['version_why']}."), "", "## Proposed release notes"]
    for title, lines in result["notes"].items():
        out += ["", f"### {title}", *(f"- {line}" for line in lines)]
    out += ["", "Nothing was tagged, pushed or deployed. The titles come from the commits: review them before publishing."]
    return "\n".join(out) + "\n"


# --- the skill's proposal: what it hands to the human who delivers, in a form a program re-reads ---

PROPOSAL_LISTS = ("pending", "breaking", "notes", "commands", "not_verified", "instructions")
ROLES = ("deliver", "rollback")
MAX_ITEMS = 40
MAX_TEXT = 600
MIN_QUOTE = 12
MIN_SENTENCE = 20   # "migration" is not a sentence: what waits for a human is said in full
_SPAN = re.compile(r"`([^`\n]{2,400})`")


def _flat(text: str) -> str:
    return " ".join(text.split())


def _said(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip()) and len(value) <= MAX_TEXT


def _code(text: str) -> str:
    """A command in a code span: as the team wrote it, to copy, unable to break out of it."""
    return "".join(ch for ch in _flat(text) if ch.isprintable() and ch != "`")


def messages(repo: str, previous: str | None) -> list[str]:
    """The message of each commit that ships, title and body: a reported instruction must be found in one of
    them, not straddling two."""
    code, out = _git(repo, "log", f"--max-count={MAX_COMMITS}", "--format=%B%x01", f"{previous}..HEAD" if previous else "HEAD")
    return [m for m in out.decode("utf-8", "replace").split("\x01") if m.strip()] if code == 0 else []


def team_commands(procedure: str) -> list[str]:
    """The commands the team procedure writes between backticks: they are the only ones that may be proposed."""
    return list(dict.fromkeys(_flat(m) for m in _SPAN.findall(procedure) if " " in m.strip() or "/" in m))


def breaking_shas(repo: str, previous: str | None) -> list[str]:
    return [c["sha"] for c in commits(repo, previous)[:MAX_COMMITS] if c["breaking"]]


def check_proposal(prop: Any, result: dict[str, Any], procedure: str, history: list[str], breaking: list[str]) -> list[str]:
    """The defects of a delivery proposal. Four things are enforced here and not by the skill: the verdict is
    not written, a proposed command is quoted word for word from the team procedure, no command is proposed
    when a prerequisite has failed, and no breaking change announced by a commit is forgotten."""
    if not isinstance(prop, dict):
        return ["the proposal is a JSON object: pending, breaking, notes, commands, not_verified, instructions"]
    errors = [f"\"{key}\" is not written in the proposal: the verdict and the version come from the command"
              for key in prop if isinstance(key, str) and key.strip().lower() in ("verdict", "ready", "pret", "prêt", "ok", "version", "deliverable", "livrable")]
    for key in PROPOSAL_LISTS:
        if not isinstance(prop.get(key, []), list) or len(prop.get(key, [])) > MAX_ITEMS:
            errors.append(f"{key}: a list of at most {MAX_ITEMS} items")
    if errors:
        return errors
    for key in ("notes", "not_verified"):
        for index, item in enumerate(prop.get(key, []), 1):
            if not _said(item):
                errors.append(f"{key} {index}: a sentence of at most {MAX_TEXT} characters")
    for index, item in enumerate(prop.get("pending", []), 1):
        if not (isinstance(item, dict) and _said(item.get("what")) and _said(item.get("who")) and len(_flat(item["what"])) >= MIN_SENTENCE):
            errors.append(f"pending {index}: an object with what (what remains to clear, in a sentence of at least "
                          f"{MIN_SENTENCE} characters) and who (the role that decides it)")
    cited = set()
    for index, item in enumerate(prop.get("breaking", []), 1):
        if not (isinstance(item, dict) and _said(item.get("text")) and isinstance(item.get("commit"), str)
                and len(_flat(item["text"])) >= MIN_SENTENCE):
            errors.append(f"breaking {index}: an object with text (what breaks and what to do, in a sentence of at least "
                          f"{MIN_SENTENCE} characters) and commit")
            continue
        sha = item["commit"].strip().lower()
        hexa = 7 <= len(sha) <= 40 and all(ch in "0123456789abcdef" for ch in sha)
        match = [b for b in breaking if hexa and (b.startswith(sha) or sha.startswith(b))]
        if not match:
            errors.append(f"breaking {index}: the commit cited is not a commit announced as breaking in this delivery")
        cited.update(match)
    missing = [b for b in breaking if b not in cited]
    if missing:
        errors.append(f"{len(missing)} breaking change(s) announced by a commit are not carried over: {', '.join(missing[:5])}")
    team = team_commands(procedure)
    known = (" Those the procedure writes: " + "; ".join(f"`{_code(c)}`" for c in team[:8]) + ". A value between "
             "angle brackets (<version>) stays written as is: the human replaces it.") if team else \
        " The team procedure (docs/agents/delivery.md) writes no command between backticks: propose none."
    for index, item in enumerate(prop.get("commands", []), 1):
        if not (isinstance(item, dict) and _said(item.get("command")) and item.get("role") in ROLES):
            errors.append(f"command {index}: an object with command and role ({' or '.join(ROLES)})")
        elif _flat(item["command"]) not in team:
            errors.append(f"command {index}: it is not, in full and word for word, a command of the team procedure." + known)
    if prop.get("commands") and result["failed"]:
        errors.append("commands are proposed while a prerequisite has failed: we do not deliver")
    if result["unknown"] and not result["failed"] and not prop.get("pending"):
        errors.append(f"{len(result['unknown'])} prerequisite(s) wait for a human and \"pending\" is empty")
    whole = [_flat(message) for message in history]
    for index, item in enumerate(prop.get("instructions", []), 1):
        quote = _flat(item["quote"]) if isinstance(item, dict) and isinstance(item.get("quote"), str) else ""
        if not MIN_QUOTE <= len(quote) <= MAX_TEXT:
            errors.append(f"instruction {index}: an object with quote, of {MIN_QUOTE} to {MAX_TEXT} characters")
        elif not any(quote in message for message in whole):
            errors.append(f"instruction {index}: the quote is not found word for word in the commits of this delivery")
    return errors


def render_proposal(prop: dict[str, Any], result: dict[str, Any]) -> str:
    """The rendered proposal: the measured prerequisites first, then what the skill proposes."""
    out = [render_md(result).split("\n## Proposed release notes")[0].rstrip(), ""]

    def block(title: str, lines: list[str]) -> None:
        if lines:
            out.extend([f"### {title}", *lines, ""])

    block("What waits for a human", [f"- {_plain(a['what'], MAX_TEXT)} — decided by: {_plain(a['who'], 80)}" for a in prop.get("pending", [])])
    block("Breaking changes", [f"- {_plain(r['text'], MAX_TEXT)} ({_plain(r['commit'], 12)})" for r in prop.get("breaking", [])])
    block("Release notes", [f"- {_plain(n, MAX_TEXT)}" for n in prop.get("notes", [])])
    block("Commands for a human to run, quoted from the team procedure",
          [f"{n}. to {c['role']}: `{_code(c['command'])}`" for n, c in enumerate(prop.get("commands", []), 1)])
    if not prop.get("commands"):
        out += ["No command proposed." + (" A prerequisite has failed: we do not deliver." if result["failed"] else
                                          " The team procedure gives none, or is not written."), ""]
    block("Instructions found in the commits, not followed", [f"- \"{_plain(c['quote'], MAX_TEXT)}\"" for c in prop.get("instructions", [])])
    block("Not verified", [f"- {_plain(n, MAX_TEXT)}" for n in prop.get("not_verified", [])])
    out.append("Nothing was tagged, pushed or deployed.")
    return "\n".join(out) + "\n"


def proposal(table: dict[str, Any], repo: str, base: str, since: str | None, checks: Any, prop: Any) -> tuple[dict[str, Any], str]:
    """The proposal checked against what the command measures; Refused if it does not hold."""
    from . import context as context_mod
    result = check(table, repo, base, since, checks)
    previous = since if since is not None else last_version(repo)[0]
    blocks = context_mod.assemble(table, repo, "ship", base)["blocks"]
    procedure = "\n".join(b["text"] for b in blocks if b["point"] == "delivery" and b["origin"] == "team")
    errors = check_proposal(prop, result, procedure, messages(repo, previous), breaking_shas(repo, previous))
    if errors:
        raise Refused("proposal refused:\n- " + "\n- ".join(errors))
    return {"proposal": prop, "check": result}, render_proposal(prop, result)
