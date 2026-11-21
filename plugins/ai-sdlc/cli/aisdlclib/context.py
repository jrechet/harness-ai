"""Assemble the context of a phase: the base convention, then what the team adds.

The assembly is done here, by written rules, not by the model: given two contradicting texts, the
model picks one at random. Each block carries its provenance. An override that acts as a gate (review,
security…) is read on the base branch: a PR cannot lighten its own review. An invalid override stops
everything: we do not review with half-understood rules.

Team overrides are written by people, so they are read in both languages: the file
`docs/agents/<point>.md` under its English name, or failing that under its former French name; in the
header, `mode: append|replace` or `ajoute|remplace`, and `why:` or `pourquoi:`."""
from __future__ import annotations

import json
import os
import re
import subprocess
from typing import Any

from .points import FORMER_NAMES

MODES = ("append", "replace")
FORMER_MODES = {"ajoute": "append", "remplace": "replace"}


class Refused(ValueError):
    """The request cannot be served as is; the message says what to fix."""


# A git command only hangs this long on a stalled disk; a CI runner on spinning disks under load needs
# far more than a laptop (a plain commit took over 30 s on the first CI run, 2026-11-16).
GIT_TIMEOUT = 120

def _git(repo: str, *args: str) -> tuple[int, bytes]:
    try:
        out = subprocess.run(["git", "-C", repo, "-c", "core.fsmonitor=false", "-c", "core.hooksPath=/dev/null", *args], capture_output=True, timeout=GIT_TIMEOUT)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise Refused(f"git {args[0]} did not answer in {repo}: {exc}") from exc
    return out.returncode, out.stdout


def _decode(raw: bytes, rel: str) -> str:
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise Refused(f"{rel}: the file is not UTF-8 text") from exc


def resolve_base(repo: str, base: str) -> str:
    if not base or base.startswith("-"):
        raise Refused(f"invalid base branch {base!r}: a branch name, a tag or a commit")
    code, out = _git(repo, "rev-parse", "--short", "--verify", "--quiet", f"{base}^{{commit}}")
    if code != 0 or not out.strip():
        shown = "".join(ch if ch.isprintable() else "?" for ch in base)[:80]   # the value comes from the command line
        raise Refused(f"base branch {shown} not found in {repo}: pass --base <ref>")
    return out.decode("ascii", "replace").strip()


def _is_head(repo: str, commit: str) -> bool:
    """Is the base the reviewed commit itself? Then nothing separates the PR from its own rules."""
    code, out = _git(repo, "rev-parse", "--short", "--verify", "--quiet", "HEAD^{commit}")
    return code == 0 and out.decode("ascii", "replace").strip() == commit


def _read_at(repo: str, commit: str, rel: str) -> str | None:
    """The file as it is in this commit; None if it is not there. Any other error refuses:
    a gate that cannot read its rules does not replace them with the default."""
    code, out = _git(repo, "ls-tree", commit, "--", rel)
    if code != 0:
        raise Refused(f"{rel}: cannot be read in {commit}")
    entry = out.decode("utf-8", "replace").strip()
    if not entry:
        return None
    if not entry.startswith("100"):
        raise Refused(f"{rel}: expected a regular file in {commit}, not a link or a folder")
    code, out = _git(repo, "show", f"{commit}:{rel}")
    if code != 0:
        raise Refused(f"{rel}: cannot be read in {commit}")
    return _decode(out, rel)


def is_file_at(repo: str, commit: str, rel: str) -> bool:
    """Is this path a regular file of this commit? Without reading its content, and without path patterns."""
    if not rel or rel.startswith(("/", "-")) or ".." in rel.split("/") or "\0" in rel or len(rel) > 300:
        return False
    if rel.endswith("/") or "." in (rel, *rel.split("/")) or "" in rel.split("/"):
        return False
    code, out = _git(repo, "--literal-pathspecs", "ls-tree", "-z", commit, "--", rel)
    entries = [e for e in out.decode("utf-8", "replace").split("\0") if e] if code == 0 else []
    return len(entries) == 1 and entries[0].startswith("100") and entries[0].partition("\t")[2] == rel


def _read_worktree(repo: str, rel: str) -> str | None:
    path = os.path.join(repo, rel)
    if os.path.islink(path):
        raise Refused(f"{rel}: expected a regular file, not a link")
    if not os.path.isfile(path):
        return None
    try:
        with open(path, "rb") as fh:
            return _decode(fh.read(), rel)
    except OSError as exc:
        raise Refused(f"{rel}: cannot be read ({exc})") from exc


def parse_override(name: str, point: dict[str, Any], text: str, budget: int) -> dict[str, Any]:
    """The header and body of an override; Refused if it does not respect the point's contract.
    The former French point name and header words are accepted; `mode` comes out in English."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---" or "---" not in [line.strip() for line in lines[1:]]:
        raise Refused(f"{name}: missing header (--- point: {name} / mode: append ---)")
    end = [line.strip() for line in lines[1:]].index("---") + 1
    header = {}
    for line in lines[1:end]:
        key, sep, value = line.split("#", 1)[0].partition(":")
        if sep and key.strip():
            header[key.strip()] = value.strip()
    if header.get("point") not in (name, FORMER_NAMES.get(name)):
        raise Refused(f"{name}: the header says point: {header.get('point')}, the file is the override of {name}")
    mode = FORMER_MODES.get(header.get("mode"), header.get("mode"))
    if mode not in MODES:
        raise Refused(f"{name}: unknown mode {header.get('mode')} ({', '.join(MODES)})")
    why = header.get("why") or header.get("pourquoi")
    if mode == "replace" and not point["replaceable"]:
        raise Refused(f"{name}: this point cannot be replaced, a team can only append to it (mode: append)")
    if mode == "replace" and not why:
        raise Refused(f"{name}: replace requires a why field in the header")
    body = [line for line in lines[end + 1:] if line.strip()]
    if any(line.lstrip().startswith("#") for line in body):
        raise Refused(f"{name}: no heading (line starting with #) in an override, only rules")
    if len(body) > budget:
        raise Refused(f"{name}: {len(body)} lines, at most {budget}; what overflows goes into a team skill")
    return {"mode": mode, "why": why, "text": "\n".join(body), "lines": len(body)}


def override_paths(table: dict[str, Any], name: str) -> list[str]:
    """Where a point's override is looked for, in order: its English name, then its former French name."""
    names = [name] + ([FORMER_NAMES[name]] if name in FORMER_NAMES else [])
    return [f"{table['override_dir']}/{n}.md" for n in names]


def _override(table: dict[str, Any], repo: str, name: str, base: str, commit: str,
              worktree: bool) -> tuple[dict[str, Any] | None, list[str]]:
    """A point's override where it must be read, and warnings if another version exists elsewhere."""
    point = table["points"][name]
    rels = override_paths(table, name)
    on_base = point["branch"] == "base" and not worktree
    warnings = []
    if on_base:
        found = {rel: text for rel in rels if (text := _read_at(repo, commit, rel)) is not None}
        for rel in rels:
            try:  # the working tree only serves to warn: unreadable, it does not block the review
                here = _read_worktree(repo, rel)
            except Refused:
                here = ""
            if here is not None and here != found.get(rel):
                warnings.append(f"{rel} differs from {base} in the working tree: the {base} version is read")
    else:
        found = {rel: text for rel in rels if (text := _read_worktree(repo, rel)) is not None}
    if not found:
        return None, warnings
    rel, text = next(iter(found.items()))
    if len(found) > 1:
        warnings.append(f"{' and '.join(found)} both exist: {rel} is read, the other is ignored")
    parsed = parse_override(name, point, text, table["budget_lines"])
    source = {"path": rel, "ref": base if on_base else "working tree",
              "commit": commit if on_base else None, "mode": parsed["mode"], "why": parsed["why"]}
    return {**parsed, "source": source}, warnings


def read_level(repo: str) -> int | None:
    """The harness-ai level of the repository, read from .harness/state.json without writing anything."""
    try:
        with open(os.path.join(repo, ".harness", "state.json"), encoding="utf-8") as fh:
            reached = json.load(fh).get("level", {}).get("reached")
    except (OSError, json.JSONDecodeError, AttributeError):
        return None
    return reached if isinstance(reached, int) else None


def assemble(table: dict[str, Any], repo: str, phase: str, base: str, worktree: bool = False) -> dict[str, Any]:
    from . import points as points_mod
    if phase not in table["phases"]:
        raise Refused(f"unknown phase {phase} ({', '.join(table['phases'])})")
    commit = resolve_base(repo, base)
    blocks, warnings = [], []
    for name, point in table["points"].items():
        if phase not in point["read_by"]:
            continue
        override, found = _override(table, repo, name, base, commit, worktree)
        warnings += found
        default = points_mod.default_text(point)
        if default and not (override and override["mode"] == "replace"):
            blocks.append({"point": name, "origin": "base", "text": default, "source": {"path": point["default"]}})
        if override:
            blocks.append({"point": name, "origin": "team", "text": override["text"], "source": override["source"]})
    same = _is_head(repo, commit)
    if same and not worktree:
        warnings.append(f"{base} is the reviewed commit itself: nothing separates this change from its own rules")
    reached = read_level(repo)
    needed = table["phases"][phase]["min_level"]
    return {"phase": phase, "base": base, "commit": commit, "gate": not worktree and not same, "blocks": blocks,
            "warnings": warnings,
            "level": {"reached": reached, "needed": needed, "open": reached is not None and reached >= needed}}


def status(table: dict[str, Any], repo: str, base: str) -> list[dict[str, Any]]:
    """Each extension point: base convention, overridden, or invalid override."""
    commit = resolve_base(repo, base)
    rows = []
    for name, point in table["points"].items():
        row = {"point": name, "read_by": point["read_by"], "replaceable": point["replaceable"],
               "has_default": bool(point.get("default")), "state": "convention"}
        try:
            override, _ = _override(table, repo, name, base, commit, worktree=False)
        except Refused as exc:
            rows.append({**row, "state": "invalid", "reason": str(exc)})
            continue
        if override:
            row = {**row, "state": "overridden", "mode": override["mode"], "lines": override["lines"],
                   "path": override["source"]["path"]}
        rows.append(row)
    return rows


# --- Forge locks -----------------------------------------------------------------------------------
# The skills say that merging and approving are locked by the forge. That is only true where the forge
# is set up that way, so `status` reads it instead of asserting it. Read-only: three GET requests through
# `gh`, nothing is ever written. What cannot be read is "unmeasured" (None), never "no".

GH = "gh"          # the GitHub CLI; a test points it at a fake
GH_TIMEOUT = 20    # seconds per request: a description must not hang on a slow network
REMOTE_URL = re.compile(r"^(?:[a-z+]+://)?(?:[^@/]+@)?(?P<host>[A-Za-z0-9.-]+)(?::\d+)?[:/]"
                        r"(?P<owner>[A-Za-z0-9_.-]+)/(?P<name>[A-Za-z0-9_.-]+?)(?:\.git)?/?$")
BRANCH_NAME = re.compile(r"[A-Za-z0-9_./-]+")   # what goes into the request path: no query, no escape


def _gh_get(host: str, path: str) -> tuple[int, Any]:
    """One GET on the forge's API: the exit code of `gh` and the JSON it printed (None if it is not JSON).
    OSError if `gh` is not installed."""
    env = {**os.environ, "GH_PROMPT_DISABLED": "1", "GH_NO_UPDATE_NOTIFIER": "1"}
    try:
        out = subprocess.run([GH, "api", "--method", "GET", "--hostname", host, path],
                             capture_output=True, timeout=GH_TIMEOUT, env=env, stdin=subprocess.DEVNULL)
    except subprocess.TimeoutExpired:
        return 1, None
    try:
        return out.returncode, json.loads(out.stdout.decode("utf-8", "replace"))
    except json.JSONDecodeError:
        return out.returncode or 1, None


def _forge_branch(repo: str, base: str) -> tuple[str, str]:
    """The remote and the branch name a base ref stands for; Refused if it is not a branch of a remote."""
    code, out = _git(repo, "remote")
    remotes = out.decode("utf-8", "replace").split() if code == 0 else []
    if not remotes:
        raise Refused("the repository has no remote, so no forge to ask")
    code, out = _git(repo, "rev-parse", "--symbolic-full-name", "--verify", "--quiet", base)
    full = out.decode("utf-8", "replace").strip() if code == 0 else ""
    if full.startswith("refs/heads/"):
        return ("origin" if "origin" in remotes else remotes[0]), full[len("refs/heads/"):]
    for remote in sorted(remotes, key=len, reverse=True):
        prefix = f"refs/remotes/{remote}/"
        if full.startswith(prefix) and full != prefix + "HEAD":
            return remote, full[len(prefix):]
    shown = "".join(ch if ch.isprintable() else "?" for ch in base)[:80]
    raise Refused(f"the base {shown} is not a branch, and protection is set on a branch")


def _either(*values: bool | None) -> bool | None:
    """Yes if one source says yes; no only if every source answered no."""
    if any(v is True for v in values):
        return True
    return None if any(v is None for v in values) else False


def _names_a_check(checks: Any) -> bool:
    return isinstance(checks, dict) and bool(checks.get("contexts") or checks.get("checks"))


def _classic_locks(host: str, slug: str, branch: str, summary: dict[str, Any]) -> tuple[bool | None, bool | None]:
    """(review required, check required) as classic branch protection sets them."""
    if not summary["protected"]:
        return False, False
    code, detail = _gh_get(host, f"repos/{slug}/branches/{branch}/protection")
    if code == 0 and isinstance(detail, dict):
        reviews = detail.get("required_pull_request_reviews")
        count = reviews.get("required_approving_review_count") if isinstance(reviews, dict) else 0
        return isinstance(count, int) and count >= 1, _names_a_check(detail.get("required_status_checks"))
    if isinstance(detail, dict) and detail.get("message") == "Branch not protected":
        return False, False   # protected by a ruleset only: the rules answer
    # The detail needs admin rights. The branch summary still names the required checks; it says nothing of reviews.
    protection = summary.get("protection")
    named = _names_a_check(protection.get("required_status_checks") if isinstance(protection, dict) else None)
    return None, (True if named else None)


def _ruleset_locks(host: str, slug: str, branch: str) -> tuple[bool | None, bool | None, bool | None]:
    """(a rule applies, review required, check required) as the active rulesets of the branch set them."""
    code, rules = _gh_get(host, f"repos/{slug}/rules/branches/{branch}")
    if code != 0 or not isinstance(rules, list):
        return None, None, None
    review = check = False
    for rule in (r for r in rules if isinstance(r, dict)):
        params = rule.get("parameters") if isinstance(rule.get("parameters"), dict) else {}
        count = params.get("required_approving_review_count")
        if rule.get("type") == "pull_request" and isinstance(count, int) and count >= 1:
            review = True
        if rule.get("type") == "required_status_checks" and params.get("required_status_checks"):
            check = True
    return bool(rules), review, check


def locks(repo: str, base: str) -> dict[str, Any]:
    """Whether the forge protects the base branch, requires a review and requires a check.
    Each answer is True, False, or None when it could not be read. Never refuses: `status` describes."""
    result = {"measured": False, "reason": None, "branch": None, "repository": None,
              "protected": None, "requires_review": None, "requires_check": None}
    try:
        remote, branch = _forge_branch(repo, base)
        code, out = _git(repo, "remote", "get-url", remote)
    except Refused as exc:
        return {**result, "reason": str(exc)}
    url = REMOTE_URL.match(out.decode("utf-8", "replace").strip()) if code == 0 else None
    if not url or not BRANCH_NAME.fullmatch(branch):
        return {**result, "reason": f"the remote {remote} or the branch name cannot be turned into a forge request"}
    host, slug = url["host"], f"{url['owner']}/{url['name']}"
    result = {**result, "branch": branch, "repository": f"{host}/{slug}"}
    try:
        code, summary = _gh_get(host, f"repos/{slug}/branches/{branch}")
        if code != 0 or not isinstance(summary, dict) or not isinstance(summary.get("protected"), bool):
            return {**result, "reason": f"gh could not read {branch} on {host}/{slug} (not GitHub, not signed in, or no such branch there)"}
        review, check = _classic_locks(host, slug, branch, summary)
        ruled, rule_review, rule_check = _ruleset_locks(host, slug, branch)
    except OSError:
        return {**result, "reason": "gh is not installed"}
    return {**result, "measured": True, "protected": _either(summary["protected"], ruled),
            "requires_review": _either(review, rule_review), "requires_check": _either(check, rule_check)}


# --- Rendering -------------------------------------------------------------------------------------

def render_context_md(result: dict[str, Any]) -> str:
    level = result["level"]
    seen = "unmeasured (run harness status)" if level["reached"] is None else str(level["reached"])
    out = [f"# Context of the {result['phase']} phase", "",
           f"Base branch: {result['base']} ({result['commit']}). harness-ai level: {seen}, "
           f"the phase opens at level {level['needed']}."]
    if not level["open"]:
        out.append("The required level is not reached: the phase remains usable, its results are to be taken as a trial.")
    if not result["gate"]:
        out.append("This context does not count for a gate: the rules do not come from a separate base branch.")
    out += [f"Warning: {w}" for w in result["warnings"]]
    for block in result["blocks"]:
        src = block["source"]
        if block["origin"] == "base":
            title = f"{block['point']} — base ({src['path']})"
        else:
            where = f"{src['ref']} {src['commit']}" if src["commit"] else src["ref"]
            title = f"{block['point']} — team ({src['path']} @ {where}, {src['mode']})"
        out += ["", f"## {title}", "", block["text"]]
    if not result["blocks"]:
        out += ["", "No convention and no override for this phase."]
    return "\n".join(out) + "\n"


def render_status_md(rows: list[dict[str, Any]]) -> str:
    out = ["| Point | Read by | State |", "|---|---|---|"]
    for row in rows:
        if row["state"] == "overridden":
            state = f"overridden: {row['mode']}, {row['lines']} lines ({row['path']})"
        elif row["state"] == "invalid":
            state = f"invalid: {row['reason']}"
        else:
            state = "framework convention" if row["has_default"] else "no convention yet"
        out.append(f"| `{row['point']}` | {', '.join(row['read_by'])} | {state} |")
    return "\n".join(out) + "\n"


LOCK_ROWS = (("protected", "Base branch protected"), ("requires_review", "A review is required before merging"),
             ("requires_check", "A check is required before merging"))
LOCK_WORDS = {True: "yes", False: "no", None: "unmeasured (gh could not read it; some settings need admin rights)"}


def render_locks_md(result: dict[str, Any]) -> str:
    out = ["## Locks", ""]
    if not result["measured"]:
        out += [f"Unmeasured: {result['reason']}.",
                "Whether the base branch is protected, requires a review and requires a check is unmeasured: "
                "look at the branch settings on the forge."]
        return "\n".join(out) + "\n"
    out += [f"What the forge enforces on `{result['branch']}` of {result['repository']}, read with gh. Nothing is changed.", "",
            "| Lock | State |", "|---|---|"]
    out += [f"| {label} | {LOCK_WORDS[result[key]]} |" for key, label in LOCK_ROWS]
    if result["protected"] is False:
        out += ["", "Nothing on the forge stops a merge or a push to this branch: here, an agent that does not merge is a habit, not a lock."]
    return "\n".join(out) + "\n"
