"""The size of a change, computed by rules: it chooses the path of `/dev`.

XS goes straight to a PR, S–M carries its plan in the description, L or a sensitive zone requires a
plan written in the repository and approved by a human before the code. The sensitive zones are those
of the base plus those of the team (`docs/agents/sensitive-zones.md`, or the former
`docs/agents/zones-sensibles.md`), read on the base branch: a PR cannot take its own files off the list."""
from __future__ import annotations

import posixpath
import re
from typing import Any

from . import points as points_mod
from .context import Refused, _git, _is_head, _override, resolve_base

_LIST = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s*")

SIZES = ("XS", "S-M", "L")
PATHS = {"XS": "direct PR, no written plan",
         "S-M": "plan in the PR description",
         "L": "plan written in the repository and approved by a human before the code"}
_ZONE = re.compile(r"^\s*[-*]\s+((?:`[^`]+`\s*,?\s*)+)(.*)$")


def glob_regex(glob: str) -> re.Pattern[str]:
    """A path pattern: `*` stays within a folder, `**` crosses as many as needed. `folder/**`
    also takes `folder` itself (a link or a submodule put in its place), and case does not matter:
    on a disk that ignores it, `Migrations/` writes into `migrations/`."""
    glob = glob.lstrip("/")
    tail = ""
    for suffix in ("/**", "/"):
        if glob.endswith(suffix) and len(glob) > len(suffix):
            glob, tail = glob[:-len(suffix)], "(?:/.*)?"
            break
    out, index = [], 0
    while index < len(glob):
        if glob.startswith("**/", index):
            out.append("(?:.*/)?")
            index += 3
        elif glob.startswith("**", index):
            out.append(".*")
            index += 2
        elif glob[index] == "*":
            out.append("[^/]*")
            index += 1
        elif glob[index] == "?":
            out.append("[^/]")
            index += 1
        else:
            out.append(re.escape(glob[index]))
            index += 1
    return re.compile("".join(out) + tail + r"\Z", re.DOTALL | re.IGNORECASE)


def parse_zones(text: str, origin: str) -> list[dict[str, str]]:
    """The `- `pattern`, `pattern` — why` lines of a sensitive zones text. A list line that quotes a
    pattern without following this form is refused: silently ignored, the zone would not exist."""
    zones = []
    for line in text.splitlines():
        match = _ZONE.match(line)
        if not match or "`" in match[2]:
            if _LIST.match(line) and "`" in line:
                raise Refused(f"sensitive-zones ({origin}): unreadable line \"{line.strip()}\" — expected "
                              "- `pattern`, `pattern` — why, the patterns first and nowhere else")
            continue
        why = match[2].strip().lstrip("—–-: ").strip()
        for glob in (g.strip() for g in re.findall(r"`([^`]+)`", match[1])):
            if not glob.strip("/*") or any(char in glob for char in "[]{}\\"):
                raise Refused(f"sensitive-zones ({origin}): pattern `{glob}` not supported (*, ** and ? only)")
            zones.append({"glob": glob, "why": why, "origin": origin})
    return zones


def zones(table: dict[str, Any], repo: str, base: str) -> list[dict[str, str]]:
    point = table["points"]["sensitive-zones"]
    override, _ = _override(table, repo, "sensitive-zones", base, resolve_base(repo, base), worktree=False)
    found = parse_zones(points_mod.default_text(point) or "", "base")
    return found + (parse_zones(override["text"], "team") if override else [])


def diff_stats(repo: str, base: str) -> list[dict[str, Any]]:
    """Per file of the change: lines added and removed. A file git cannot count (binary, or declared
    `-diff` by a .gitattributes the PR may have added) counts for the lines of its content: it does
    not pass for empty."""
    commit = resolve_base(repo, base)
    if _is_head(repo, commit):
        raise Refused(f"{base} is the current commit: there is no change to measure, give the target branch")
    code, out = _git(repo, "diff", "-z", "--numstat", "--no-renames", "--no-ext-diff", "--no-textconv",
                     "--ignore-submodules=none", f"{commit}...HEAD")
    if code != 0:
        raise Refused(f"cannot diff {base} and HEAD in {repo}")
    stats = []
    for entry in filter(None, out.split(b"\0")):
        added, deleted, path = entry.decode("utf-8", "replace").split("\t", 2)
        if added.isdigit() and deleted.isdigit():
            stats.append({"path": path, "lines": int(added) + int(deleted)})
            continue
        blobs = [_git(repo, "cat-file", "blob", f"{ref}:{path}") for ref in ("HEAD", commit)]
        stats.append({"path": path, "unmeasured": True,
                      "lines": max(1, *(blob.count(b"\n") + 1 for code, blob in blobs if code == 0))})
    return stats


def planned_paths(paths: list[str]) -> list[str]:
    """The planned paths, brought to the form git gives them; Refused if they leave the repository."""
    clean = []
    for raw in paths:
        path = posixpath.normpath(raw.replace("\\", "/"))
        if path.startswith(("/", "..")) or path == ".":
            raise Refused(f"--paths {raw!r}: a path relative to the repository")
        clean.append(path)
    return clean


def touched(paths: list[str], found: list[dict[str, str]]) -> list[dict[str, str]]:
    """Each file that falls in a sensitive zone, with the first zone that takes it."""
    compiled = [(zone, glob_regex(zone["glob"])) for zone in found]
    hits = []
    for path in paths:
        zone = next((zone for zone, regex in compiled if regex.match(path)), None)
        if zone:
            hits.append({"path": path, **zone})
    return hits


def classify(table: dict[str, Any], repo: str, base: str, paths: list[str] | None = None) -> dict[str, Any]:
    """The size of the current change, or, with `paths`, what is known before the code is written:
    a sensitive zone is enough to say L, the rest waits for the diff."""
    found = zones(table, repo, base)
    planned = paths is not None
    stats = [{"path": p, "lines": 0} for p in planned_paths(paths)] if planned else diff_stats(repo, base)
    if not stats:
        raise Refused(f"no change between {base} and HEAD: nothing to measure")
    files, lines = len(stats), sum(s["lines"] for s in stats)
    sensitive = touched([s["path"] for s in stats], found)
    reasons = [f"{hit['path']} is in the sensitive zone `{hit['glob']}` ({hit['origin']})" for hit in sensitive]
    if sensitive:
        size = "L"
    elif planned:
        size = None
        reasons.append("no sensitive zone in the planned paths: XS or S-M, to measure on the diff before the PR")
    else:
        limits = table["sizes"]
        size = next((name for name in ("XS", "S-M")
                     if files <= limits[name]["files"] and lines <= limits[name]["lines"]), "L")
        reasons.append(f"{files} files, {lines} lines changed")
        reasons += [f"{s['path']} cannot be counted by git: counted for the {s['lines']} lines of its content"
                    for s in stats if s.get("unmeasured")]
    return {"size": size, "path": PATHS.get(size), "planned": planned, "files": files, "lines": lines,
            "sensitive": sensitive, "reasons": reasons, "paths": [s["path"] for s in stats]}


def render_md(result: dict[str, Any]) -> str:
    head = f"Size: {result['size']} — {result['path']}." if result["size"] else "Size: not decided yet."
    return "\n".join([head, *[f"- {reason}" for reason in result["reasons"]]]) + "\n"
