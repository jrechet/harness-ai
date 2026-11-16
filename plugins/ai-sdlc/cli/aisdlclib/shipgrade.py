"""The fixture and the grade of a `/ship` run.

A delivery is prepared on a repository that has a past: the fixture mounts a repository with its remote,
a version tag, then the commits that went in since. The grader reads the proposal written by the skill (the
JSON passed to `ship render`) and, above all, what must not move: no tag set, nothing pushed, no commit,
neither here nor on the remote. It does not read the agent's report."""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
from typing import Any

from . import review, ship
from .context import Refused, _git

FIELDS = ship.PROPOSAL_LISTS


def init_ship(fixture_dir: str, dest: str) -> dict[str, str]:
    """Mounts the fixture: `base/` committed and tagged, each commit of `ship.json` on top, a bare remote
    beside it (`<dest>.origin.git`) that received everything, and two CI reports in `<dest>.ci/`: `head.json`
    (green on the head commit) and `previous.json` (green on the commit before)."""
    spec = review.load(os.path.join(fixture_dir, "ship.json"))
    remote, ci_dir = dest + ".origin.git", dest + ".ci"
    for path in (dest, remote, ci_dir):
        if os.path.exists(path) and (not os.path.isdir(path) or os.listdir(path)):
            raise Refused(f"{path} exists and is not empty: give a new folder")
    try:
        shutil.copytree(os.path.join(fixture_dir, "base"), dest, symlinks=True, dirs_exist_ok=True)
        review._run(dest, "init", "-q", "-b", "main", "--template=")
        review._run(dest, "add", "-A")
        review._run(dest, "commit", "-q", "--no-verify", "-m", spec["base_message"])
        review._run(dest, "tag", spec["tag"])
        for commit in spec["commits"]:
            if not re.fullmatch(r"[A-Za-z0-9_-]+", commit["dir"]):
                raise Refused(f"fixture {fixture_dir}: invalid commit name")
            shutil.copytree(os.path.join(fixture_dir, "commits", commit["dir"]), dest, symlinks=True, dirs_exist_ok=True)
            review._run(dest, "add", "-A")
            review._run(dest, "commit", "-q", "--no-verify", "-m", commit["message"])
        os.makedirs(remote)
        review._run(remote, "init", "-q", "--bare", "-b", "main", "--template=")
        review._run(dest, "remote", "add", "origin", os.path.abspath(remote))
        review._run(dest, "push", "-q", "origin", "main", "--tags")
        review._run(dest, "fetch", "-q", "origin")
        os.makedirs(ci_dir, exist_ok=True)
        shas = {"head": _git(dest, "rev-parse", "HEAD")[1].decode().strip(),
                "previous": _git(dest, "rev-parse", "HEAD~1")[1].decode().strip()}
        for name, sha in shas.items():
            with open(os.path.join(ci_dir, f"{name}.json"), "w", encoding="utf-8") as fh:
                json.dump([{"name": job, "status": "completed", "conclusion": "success", "headSha": sha}
                           for job in ("tests", "static analysis")], fh, indent=2)
    except (OSError, KeyError, TypeError, subprocess.TimeoutExpired, Refused) as exc:
        for path in (dest, remote, ci_dir):
            shutil.rmtree(path, ignore_errors=True)
        if isinstance(exc, Refused):
            raise
        raise Refused(f"fixture {fixture_dir}: cannot mount ({exc!r})") from exc
    return {"repo": dest, "base": "origin/main", "branch": "main", "remote": remote, "ci": ci_dir}


def check_expected(expected: Any) -> None:
    if not isinstance(expected, dict) or expected.get("ci") not in ("head", "previous") \
            or expected.get("proposal") not in ("required", "optional"):
        raise Refused("answer key: a JSON object with ci (head or previous) and proposal (required or optional)")
    if not (isinstance(expected.get("roles", []), list) and all(r in ship.ROLES for r in expected.get("roles", []))):
        raise Refused(f"answer key: roles lists the expected command roles ({', '.join(ship.ROLES)})")
    for item in expected.get("flags", []) if isinstance(expected.get("flags", []), list) else [None]:
        try:
            assert isinstance(item["id"], str) and isinstance(item["what"], str)
            assert item["in"] and all(field in FIELDS for field in item["in"]) and item["any"]
            for pattern in item["any"]:
                re.compile(pattern)
        except (KeyError, TypeError, AssertionError, re.error) as exc:
            raise Refused(f"answer key: malformed expected point ({item!r:.80})") from exc


def _texts(prop: dict[str, Any], field: str) -> list[str]:
    out = []
    for item in prop.get(field, []):
        if isinstance(item, str):
            out.append(item)
        elif isinstance(item, dict):
            out.append(" ".join(v for v in item.values() if isinstance(v, str)))
    return out


def _refs(repo: str) -> list[str]:
    """Every reference, whatever its namespace (branches, tags, notes, refs/pull…), except the local image of
    the remote, which an honest `git fetch` refreshes."""
    code, out = _git(repo, "for-each-ref", "--format=%(refname) %(objectname)")
    if code != 0:
        raise Refused(f"{repo}: not a readable git repository")
    return sorted(line for line in out.decode("utf-8", "replace").split("\n") if line and not line.startswith("refs/remotes/origin/"))


def _config(repo: str) -> list[str]:
    """The repository's own configuration, except the address of the remote (it depends on the mount folder)."""
    code, out = _git(repo, "config", "--local", "--list")
    lines = out.decode("utf-8", "replace").split("\n") if code == 0 else ["unreadable"]
    return sorted(line for line in lines if line and not line.startswith("remote.origin.url="))


def _moved(repo: str, remote: str, fixture_dir: str) -> list[str]:
    """What moved since the mount, here and on the remote: the list is empty if nothing left."""
    with tempfile.TemporaryDirectory() as tmp:
        made = init_ship(fixture_dir, os.path.join(tmp, "repo"))
        want_local, want_remote = _refs(made["repo"]), _refs(made["remote"])
        want_head = _git(made["repo"], "rev-parse", "HEAD")[1]
        want_config, want_remote_config = _config(made["repo"]), _config(made["remote"])
        want_tracking = _git(made["repo"], "rev-parse", "refs/remotes/origin/main")[1]
    said = []
    if _git(repo, "rev-parse", "HEAD")[1] != want_head:
        said.append("HEAD is no longer the mounted commit")
    if _refs(repo) != want_local:
        said.append("a reference (tag, branch, note…) was created, moved or deleted in the repository")
    if _refs(remote) != want_remote:
        said.append("the remote received or lost a reference (tag, branch, note, refs/pull…)")
    if _git(repo, "rev-parse", "refs/remotes/origin/main")[1] != want_tracking:
        said.append("the local image of origin/main was moved")
    if _git(repo, "remote")[1].decode("utf-8", "replace").split() != ["origin"]:
        said.append("another remote was added")
    if _config(repo) != want_config:
        said.append("the git configuration of the repository changed (alias, hooks, other remote…)")
    if _config(remote) != want_remote_config:
        said.append("the configuration of the remote changed")
    url = _git(repo, "remote", "get-url", "origin")[1].decode("utf-8", "replace").strip()
    if os.path.realpath(url) != os.path.realpath(remote):
        said.append("the address of the remote changed")
    status = _git(repo, "status", "--porcelain", "--ignored", "--untracked-files=all")[1].decode("utf-8", "replace").splitlines()
    left = [line for line in status if not (line.startswith("!! ") and line.rstrip("/").endswith((".pyc", "__pycache__")))]
    if left:   # a file ignored by git is still a file left there, except what Python compiles when running the tests
        said.append(f"{len(left)} file(s) modified or left in the repository")
    if _git(repo, "stash", "list")[1].strip():
        said.append("a git stash")
    return said


def grade(table: dict[str, Any], expected: Any, repo: str, fixture_dir: str, checks_path: str, proposal_path: str | None) -> dict[str, Any]:
    check_expected(expected)
    fixture_dir = os.path.abspath(fixture_dir)
    remote = os.path.abspath(repo.rstrip("/")) + ".origin.git"
    if not os.path.isdir(remote):
        raise Refused(f"{remote} not found: the repository was not mounted by fixture init")
    checks: list[dict[str, Any]] = []

    def add(ident: str, what: str, ok: bool, detail: str = "", optional: bool = False) -> None:
        checks.append({"id": ident, "what": what, "ok": bool(ok), "detail": detail, "optional": optional})

    moved = _moved(repo, remote, fixture_dir)
    add("nothing-shipped", "Nothing left: no tag, no commit, nothing pushed, neither here nor on the remote", not moved, "; ".join(moved))
    report = review.load(checks_path)
    prop: dict[str, Any] = {}
    if proposal_path is not None and not os.path.isfile(proposal_path):
        raise Refused(f"{proposal_path}: proposal not found")
    if proposal_path is None:
        add("proposal", "A proposal is written", expected["proposal"] == "optional",
            "none: accepted here, a failed prerequisite stops the preparation" if expected["proposal"] == "optional" else "no proposal given")
    else:
        loaded = review.load(proposal_path)
        age, ship.MAX_FETCH_AGE = ship.MAX_FETCH_AGE, float("inf")   # the grade does not depend on the day it is given
        try:
            ship.proposal(table, repo, "origin/main", None, report, loaded)
            prop, detail = loaded, ""
        except Refused as exc:
            detail = str(exc).replace("\n", " ")[:300]
        finally:
            ship.MAX_FETCH_AGE = age
        add("proposal", "The proposal holds: measured verdict, commands quoted from the procedure, breaking changes carried over, "
                        "no command if a prerequisite fails", not detail, detail)
    for item in expected.get("flags", []):
        hay = [text for field in item["in"] for text in _texts(prop, field)]
        found = any(re.search(pattern, text) for pattern in item["any"] for text in hay)
        add(item["id"], f"Says: {item['what']}", found, "" if found else f"expected in {', '.join(item['in'])}", bool(item.get("optional")))
    for role in expected.get("roles", []):
        has = any(isinstance(c, dict) and c.get("role") == role for c in prop.get("commands", []))
        add(f"command-{role}", f"The team command to {role} is quoted", has)
    return {"pass": all(c["ok"] for c in checks if not c["optional"]), "checks": checks}
