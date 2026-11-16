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
import subprocess
from typing import Any

from .points import FORMER_NAMES

MODES = ("append", "replace")
FORMER_MODES = {"ajoute": "append", "remplace": "replace"}


class Refused(ValueError):
    """The request cannot be served as is; the message says what to fix."""


def _git(repo: str, *args: str) -> tuple[int, bytes]:
    try:
        out = subprocess.run(["git", "-C", repo, "-c", "core.fsmonitor=false", "-c", "core.hooksPath=/dev/null", *args], capture_output=True, timeout=20)
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
