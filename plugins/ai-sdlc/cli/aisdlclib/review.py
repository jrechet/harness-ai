"""The result of a review: its shape, its evidence, its rendering, and its grade on a fixture.

What the review skill promises (seven findings at most, each with a line of the diff and its four
parts) is enforced here, not in its text: a review that does not pass `render` is not rendered.
`grade` and `init_fixture` measure the skill on a trapped PR whose answer key is known.

The JSON is English (`findings`, `severity`, `location`…). The French keys of earlier runs and of
older copies of the skill (`constats`, `gravite`, `sur_quoi`…) are still read: `normalize` maps them."""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from typing import Any

from .context import Refused, _git, _is_head, resolve_base, GIT_TIMEOUT

MAX_FINDINGS = 7
MAX_CONSTATS = MAX_FINDINGS  # the former name, imported by other modules
MAX_SPAN = 20  # lines a finding can cite at once: beyond that, it no longer cites, it sweeps
SEVERITIES = {"blocking": "blocking", "should-fix": "should fix", "to-discuss": "to discuss"}
PARTS = {"expected": "Expected", "observed": "Observed", "suggestion": "Suggestion"}
# the French form of the JSON, still read: top-level keys, finding keys, severity values
_FRENCH_KEYS = {"constats": "findings", "non_verifie": "not_verified", "max_constats": "max_findings"}
_FRENCH_FINDING = {"gravite": "severity", "sur_quoi": "location", "attendu": "expected", "observe": "observed",
                   "conseille": "suggestion"}
_FRENCH_SEVERITIES = {"bloquant": "blocking", "a-corriger": "should-fix", "a-discuter": "to-discuss"}
_WHERE = re.compile(r"\A(?P<path>[^:\s][^:\n]*):(?P<first>[0-9]{1,9})(?:-(?P<last>[0-9]{1,9}))?\Z")
_HUNK = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@")
_FIXED = {"GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_SYSTEM": os.devnull, "GIT_AUTHOR_NAME": "fixture", "GIT_AUTHOR_EMAIL": "fixture@example.com",
          "GIT_COMMITTER_NAME": "fixture", "GIT_COMMITTER_EMAIL": "fixture@example.com",
          "GIT_AUTHOR_DATE": "2026-01-01T00:00:00Z", "GIT_COMMITTER_DATE": "2026-01-01T00:00:00Z"}


def parse_where(text: Any) -> tuple[str, int, int]:
    """`path:line` or `path:first-last`, path relative to the repository; ValueError otherwise."""
    match = _WHERE.match(text) if isinstance(text, str) else None
    if not match:
        raise ValueError(f"{text!r}: expected path:line or path:first-last")
    path, first = match["path"], int(match["first"])
    last = int(match["last"] or first)
    if path.startswith(("/", "./")) or ".." in path.split("/") or first < 1 or last < first:
        raise ValueError(f"{text!r}: path relative to the repository, lines from 1, first before last")
    if last - first >= MAX_SPAN:
        raise ValueError(f"{text!r}: at most {MAX_SPAN} lines cited, aim at the line that carries the defect")
    return path, first, last


def _renamed(item: dict[str, Any], names: dict[str, str]) -> dict[str, Any]:
    """The object with its French keys renamed; an English key already present wins."""
    return {names.get(k, k): v for k, v in item.items() if not (k in names and names[k] in item)}


def normalize(data: Any) -> Any:
    """A review (or an answer key) in its English form. French keys and severities of earlier runs are
    renamed; anything else is returned as it is, for `validate` to name. The input is not modified."""
    if not isinstance(data, dict):
        return data
    out = _renamed(data, _FRENCH_KEYS)
    if isinstance(out.get("findings"), list):
        out["findings"] = [_normalize_finding(item) for item in out["findings"]]
    return out


def _normalize_finding(item: Any) -> Any:
    if not isinstance(item, dict):
        return item
    out = _renamed(item, _FRENCH_FINDING)
    severity = out.get("severity")
    if isinstance(severity, str) and severity in _FRENCH_SEVERITIES:
        out["severity"] = _FRENCH_SEVERITIES[severity]
    return out


def validate(data: Any) -> list[str]:
    """What a review lacks to be rendered; an empty list if it is complete."""
    data = normalize(data)
    if not isinstance(data, dict):
        return ["the review is a JSON object with the keys findings and not_verified"]
    findings = data.get("findings")
    if not isinstance(findings, list):
        return ["findings: a list, empty if there is nothing to say"]
    errors = []
    unchecked = data.get("not_verified", [])
    if not isinstance(unchecked, list) or not all(isinstance(u, str) for u in unchecked):
        errors.append("not_verified: a list of sentences")
    if len(findings) > MAX_FINDINGS:
        errors.append(f"{len(findings)} findings, at most {MAX_FINDINGS}: keep the most serious")
    for index, item in enumerate(findings, 1):
        if not isinstance(item, dict):
            errors.append(f"finding {index}: an object")
            continue
        if not isinstance(item.get("severity"), str) or item["severity"] not in SEVERITIES:
            errors.append(f"finding {index}: severity {item.get('severity')!r} unknown ({', '.join(SEVERITIES)})")
        try:
            parse_where(item.get("location"))
        except ValueError as exc:
            errors.append(f"finding {index}: location {exc}")
        for key in ("point", *PARTS):
            if not isinstance(item.get(key), str) or not item[key].strip():
                errors.append(f"finding {index}: {key} is empty")
    return errors


def changed_lines(repo: str, base: str) -> dict[str, set[int]]:
    """Per file, the lines the change adds or modifies, numbered on the HEAD side. A deletion is
    cited at the line where it happened (the one before or the one after), a deleted file at its
    line 1. The paths come from git's list, never from the text of the diff: an added line that
    imitates a header does not make citable a file the PR does not touch."""
    commit = resolve_base(repo, base)
    span = f"{commit}...HEAD"
    code, out = _git(repo, "diff", "-z", "--name-only", "--no-renames", span)
    if code != 0:
        raise Refused(f"cannot diff {base} and HEAD in {repo}")
    changed: dict[str, set[int]] = {}
    for raw in filter(None, out.split(b"\0")):
        path = raw.decode("utf-8", "replace")
        code, patch = _git(repo, "--literal-pathspecs", "diff", "-U0", "--no-color", "--no-ext-diff", "--no-textconv",
                           "--no-renames", span, "--", path)
        if code != 0:
            raise Refused(f"cannot diff {path} between {base} and HEAD")
        lines = changed.setdefault(path, set())
        for line in patch.decode("utf-8", "replace").splitlines():
            match = _HUNK.match(line)  # with -U0, only a hunk header starts with @@
            if match:
                start, count = int(match[1]), int(match[2] if match[2] is not None else 1)
                lines.update(n for n in (range(start, start + count) if count else (start, start + 1)) if n >= 1)
    return changed


def outside_diff(data: dict[str, Any], changed: dict[str, set[int]]) -> list[str]:
    """The findings none of whose cited lines is in the diff."""
    errors = []
    for index, item in enumerate(normalize(data)["findings"], 1):
        path, first, last = parse_where(item["location"])
        if not any(first <= n <= last for n in changed.get(path, ())):
            errors.append(f"finding {index}: {item['location']} is not a line of the diff")
    return errors


def load(path: str) -> Any:
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError, RecursionError) as exc:
        raise Refused(f"{path}: unreadable ({exc})") from exc


def checked(path: str, repo: str, base: str) -> dict[str, Any]:
    """The review in the file, in its English form, if it is complete and each finding cites the
    diff; Refused otherwise."""
    data = normalize(load(path))
    errors = validate(data)
    if not errors:
        if _is_head(repo, resolve_base(repo, base)):
            raise Refused(f"{base} is the reviewed commit itself: there is no diff to cite, give the target branch")
        errors = outside_diff(data, changed_lines(repo, base))
    if errors:
        raise Refused("review refused:\n- " + "\n- ".join(errors))
    return data


def _cell(text: str) -> str:
    """A finding's text held in a cell: no line break, no bar, no forged heading."""
    flat = " ".join(text.split()).replace("&", "&amp;").replace("<", "&lt;")
    for char in "|[]":
        flat = flat.replace(char, "\\" + char)
    return flat.replace("@", "@​")  # no HTML, no link, no image, no mention that notifies


def _code(text: str) -> str:
    return "`" + " ".join(text.split()).replace("`", "'").replace("|", "/") + "`"


def _ordered(findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rank = list(SEVERITIES)
    return sorted(findings, key=lambda c: rank.index(c["severity"]))


def render_md(data: dict[str, Any]) -> str:
    data = normalize(data)
    findings = _ordered(data["findings"])
    counts = [f"{label}: {n}" for key, label in SEVERITIES.items()
              if (n := sum(c["severity"] == key for c in findings))]
    out = ["# Review", "", ("Findings — " + ", ".join(counts) + ".") if counts else "No findings."]
    unchecked = data.get("not_verified") or []
    out += ["", "Not verified:"] + [f"- {_cell(u)}" for u in unchecked] if unchecked else ["", "Not verified: nothing reported."]
    for index, item in enumerate(findings, 1):
        out += ["", f"## {index}. {SEVERITIES[item['severity']].capitalize()} — {_code(item['location'])}", "",
                "| Part | Content |", "|---|---|",
                f"| Location | {_code(item['location'])} — {_cell(item['point'])} |"]
        out += [f"| {label} | {_cell(item[key])} |" for key, label in PARTS.items()]
    return "\n".join(out) + "\n"


# --- Fixtures: a trapped PR, its answer key, the grade ------------------------------------------------

def _overlaps(item: dict[str, Any], place: dict[str, Any]) -> bool:
    path, first, last = parse_where(item["location"])
    return path == place["file"] and first <= place["lines"][1] and last >= place["lines"][0]


def _place_ok(place: Any) -> bool:
    lines = place.get("lines") if isinstance(place, dict) else None
    return (isinstance(place.get("file"), str) and isinstance(lines, list) and len(lines) == 2
            and all(type(n) is int for n in lines) and 1 <= lines[0] <= lines[1]) if lines is not None else False


def check_expected(expected: Any) -> None:
    """An empty or broken answer key grades nothing: Refused, rather than a "pass" that means nothing."""
    expected = normalize(expected)
    if not isinstance(expected, dict):
        raise Refused("answer key: a JSON object with traps and healthy")
    traps, healthy = expected.get("traps"), expected.get("healthy")
    if not isinstance(traps, list) or not isinstance(healthy, list):
        raise Refused("answer key: traps and healthy are lists")
    limit = expected.get("max_findings", MAX_FINDINGS)
    if type(limit) is not int or limit < 1:
        raise Refused("answer key: max_findings is a positive integer")
    for trap in traps:
        if not (isinstance(trap, dict) and isinstance(trap.get("id"), str) and isinstance(trap.get("what"), str)
                and type(trap.get("must")) is bool and isinstance(trap.get("where"), list) and trap["where"]
                and all(_place_ok(w) for w in trap["where"])):
            raise Refused(f"answer key: malformed trap ({trap!r:.80})")
    for item in healthy:
        if not (_place_ok(item) and isinstance(item.get("id"), str) and isinstance(item.get("what"), str)):
            raise Refused(f"answer key: malformed healthy item ({item!r:.80})")
    if not any(t["must"] for t in traps):
        raise Refused("answer key: no required trap, it cannot measure anything")


def _match(traps: list[dict[str, Any]], findings: list[dict[str, Any]]) -> dict[str, int]:
    """A finding finds one trap only: the largest matching, required traps served first."""
    owner: dict[int, str] = {}
    by_id = {t["id"]: t for t in traps}

    def claim(trap_id: str, seen: set[int]) -> bool:
        for index, item in enumerate(findings):
            if index in seen or not any(_overlaps(item, w) for w in by_id[trap_id]["where"]):
                continue
            seen.add(index)
            if index not in owner or claim(owner[index], seen):
                owner[index] = trap_id
                return True
        return False

    for trap in sorted(traps, key=lambda t: not t["must"]):
        claim(trap["id"], set())
    return {trap_id: index for index, trap_id in owner.items()}


def grade(expected: Any, data: Any) -> dict[str, Any]:
    """Generous on words, strict on evidence: a trap is found if a finding cites one of its lines, and
    a finding finds one trap only; a finding on a healthy line fails; the rest is noise, counted."""
    check_expected(expected)
    expected, data = normalize(expected), normalize(data)
    invalid = validate(data)
    limit = expected.get("max_findings", MAX_FINDINGS)
    traps = expected["traps"]
    if invalid:
        return {"pass": False, "invalid": invalid, "found": [], "missed": [t["id"] for t in traps if t["must"]],
                "optional_missed": [], "healthy_touched": [], "noise": [], "count": 0, "max": limit}
    findings = data["findings"]
    matched = _match(traps, findings)
    found = [t["id"] for t in traps if t["id"] in matched]
    touched = [h["id"] for h in expected["healthy"] if any(_overlaps(c, h) for c in findings)]
    places = [w for t in traps for w in t["where"]] + expected["healthy"]
    noise = [c["location"] for c in findings if not any(_overlaps(c, p) for p in places)]
    missed = [t["id"] for t in traps if t["must"] and t["id"] not in found]
    return {"pass": not missed and not touched and len(findings) <= limit, "invalid": [], "found": found,
            "missed": missed, "optional_missed": [t["id"] for t in traps if not t["must"] and t["id"] not in found],
            "healthy_touched": touched, "noise": noise, "count": len(findings), "max": limit}


def render_grade_md(expected: dict[str, Any], result: dict[str, Any]) -> str:
    what = {entry["id"]: entry["what"] for entry in expected["traps"] + expected["healthy"]}
    musts = [t["id"] for t in expected["traps"] if t["must"]]
    out = [f"{'PASS' if result['pass'] else 'FAIL'} — required traps found: "
           f"{len(musts) - len(result['missed'])}/{len(musts)}, findings: {result['count']}/{result['max']}"]
    out += [f"- invalid review: {e}" for e in result["invalid"]]
    out += [f"- missed: {i} — {what[i]}" for i in result["missed"]]
    out += [f"- missed (optional): {i} — {what[i]}" for i in result["optional_missed"]]
    out += [f"- healthy item commented: {i} — {what[i]}" for i in result["healthy_touched"]]
    out += [f"- outside the answer key: {w}" for w in result["noise"]]
    return "\n".join(out) + "\n"


_ISOLATED = ("-c", "core.hooksPath=" + os.devnull, "-c", "commit.gpgsign=false", "-c", "core.autocrlf=false")


def _run(dest: str, *args: str) -> None:
    """git without the user's configuration, hooks or templates: the fixture mounts the same everywhere."""
    out = subprocess.run(["git", "-C", dest, *_ISOLATED, *args], capture_output=True,
                         env={**os.environ, **_FIXED}, timeout=GIT_TIMEOUT)
    if out.returncode != 0:
        raise Refused(f"git {args[0]} failed in {dest}: {out.stderr.decode('utf-8', 'replace').strip()}")


def init_fixture(fixture_dir: str, dest: str) -> dict[str, str]:
    """Mounts the fixture as a git repository: `base/` committed on main, then, if it carries a PR
    (`pr.json`), `pr/` on top on its branch. Without a PR, the repository stops at main: a `/dev` fixture."""
    has_pr = os.path.exists(os.path.join(fixture_dir, "pr.json"))
    if not has_pr and os.path.exists(os.path.join(fixture_dir, "pr")):
        raise Refused(f"fixture {fixture_dir}: a pr/ folder without pr.json, the PR cannot be mounted")
    spec = load(os.path.join(fixture_dir, "pr.json")) if has_pr else {}
    if os.path.exists(dest) and (not os.path.isdir(dest) or os.listdir(dest)):
        raise Refused(f"{dest} exists and is not empty: give a new folder")
    try:
        branch = spec["branch"] if has_pr else None
        message = f"{spec['title']}\n\n{spec['body']}" if has_pr else ""
        removed = spec.get("removed", [])
        if any(not isinstance(r, str) or r.startswith("/") or ".." in r.split("/") for r in removed):
            raise Refused(f"fixture {fixture_dir}: removed cites only paths relative to the repository")
        shutil.copytree(os.path.join(fixture_dir, "base"), dest, symlinks=True, dirs_exist_ok=True)
        _run(dest, "init", "-q", "-b", "main", "--template=")
        _run(dest, "add", "-A")
        _run(dest, "commit", "-q", "--no-verify", "-m", "base")
        if not has_pr:
            return {"repo": dest, "base": "main", "branch": "main"}
        _run(dest, "checkout", "-q", "-b", branch)
        shutil.copytree(os.path.join(fixture_dir, "pr"), dest, symlinks=True, dirs_exist_ok=True)
        for rel in removed:
            os.remove(os.path.join(dest, rel))
        _run(dest, "add", "-A")
        _run(dest, "commit", "-q", "--no-verify", "-m", message)
    except (OSError, KeyError, TypeError, AttributeError, subprocess.TimeoutExpired, Refused) as exc:
        shutil.rmtree(dest, ignore_errors=True)  # a half-done mount is not reviewed
        if isinstance(exc, Refused):
            raise
        raise Refused(f"fixture {fixture_dir}: cannot mount ({exc!r})") from exc
    return {"repo": dest, "base": "main", "branch": branch}
