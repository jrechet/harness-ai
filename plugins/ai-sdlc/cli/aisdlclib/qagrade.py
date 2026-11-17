"""The grade of a `/qa` run on a fixture, read in the repository it leaves.

The fixture mounts a change already written, on its branch, with its ticket. The change has defects
that only tests drawn from the acceptance criteria reveal. The grader does not read the report: it
plays the tests left by the agent against a reference implementation (they must pass: a test comes
from a criterion, not from an implementation), then against faulty variants, one per criterion (they
must fail: that is the test that would have failed). Fixing the code or leaving it red are two accepted
outcomes; a test disabled, weakened or aligned on the defect is not."""
from __future__ import annotations

import os
import re
import shutil
import tempfile
from typing import Any

from . import qa, review, size, ticket
from .context import Refused, _git, _read_at
from .devgrade import BASE, _changed_lines, _checkout, _run, _state

_NAME = re.compile(r"[A-Za-z0-9_-]+")


def check_expected(expected: Any) -> None:
    def command(value: Any) -> bool:
        return isinstance(value, list) and bool(value) and all(isinstance(a, str) for a in value)

    def globs(value: Any) -> bool:
        return isinstance(value, list) and bool(value) and all(isinstance(g, str) and g for g in value)

    if not isinstance(expected, dict) or not globs(expected.get("allowed")) or not globs(expected.get("code")):
        raise Refused("answer key: a JSON object with allowed and code (path patterns)")
    if not (command(expected.get("visible_command")) and command(expected.get("hidden_command"))
            and _NAME.fullmatch(expected["hidden_command"][-1])):
        raise Refused("answer key: visible_command and hidden_command, the second ends with the hidden tests folder")
    if not (isinstance(expected.get("may_skip", []), list) and all(type(n) is int for n in expected.get("may_skip", []))):
        raise Refused("answer key: may_skip lists the numbers of the criteria no test can cover")
    for item in expected.get("forbidden_added", []) if isinstance(expected.get("forbidden_added", []), list) else [None]:
        try:
            re.compile(item["pattern"])
            assert isinstance(item["id"], str) and isinstance(item["what"], str)
            assert all(isinstance(g, str) and g for g in item.get("paths", []))
        except (KeyError, TypeError, AssertionError, re.error) as exc:
            raise Refused(f"answer key: malformed forbidden item ({item!r:.80})") from exc


def _original_branch(fixture_dir: str) -> tuple[str, str]:
    """The name and the commit of the change's branch, as mounting produces them."""
    with tempfile.TemporaryDirectory() as tmp:
        made = review.init_fixture(fixture_dir, os.path.join(tmp, "base"))
        if made["branch"] == "main":
            raise Refused(f"fixture {fixture_dir}: a /qa fixture mounts a change (pr.json, pr/)")
        return made["branch"], _git(made["repo"], "rev-parse", f"refs/heads/{made['branch']}")[1].decode().strip()


def _overlay(source: str, dest: str) -> None:
    try:
        shutil.copytree(source, dest, dirs_exist_ok=True)
    except OSError as exc:
        raise Refused(f"{source}: cannot be laid down ({exc})") from exc


def _mutants(hidden: str) -> list[str]:
    root = os.path.join(hidden, "mutants")
    names = sorted(n for n in os.listdir(root) if os.path.isdir(os.path.join(root, n))) if os.path.isdir(root) else []
    if not names or not os.path.isdir(os.path.join(hidden, "reference")) or not os.path.isdir(os.path.join(hidden, "tests")):
        raise Refused(f"{hidden}: needs tests/, reference/ and at least one variant in mutants/")
    return names


def grade(table: dict[str, Any], expected: Any, repo: str, fixture_dir: str, mapping: Any) -> dict[str, Any]:
    check_expected(expected)
    fixture_dir = os.path.abspath(fixture_dir)
    hidden = os.path.join(fixture_dir, "hidden")
    mutants = _mutants(hidden)
    ticket_text = ticket.read(os.path.join(fixture_dir, "ticket.md"))
    branch, start = _original_branch(fixture_dir)
    state = _state(repo, BASE, fixture_dir)
    checks: list[dict[str, Any]] = []

    def add(ident: str, what: str, ok: bool, detail: str = "") -> None:
        checks.append({"id": ident, "what": what, "ok": bool(ok), "detail": detail})

    onto = _git(repo, "merge-base", "--is-ancestor", start, "HEAD")[0] == 0
    add("branch", "The work continues the change's branch; main and the original change are intact",
        state["branch"] == branch and state["base_intact"] and onto,
        f"branch {state['branch']}" + ("" if onto else ", the change's commit is no longer in the history"))
    if not onto:   # without the original commit, no diff says what the agent did
        return {"pass": False, "checks": checks}
    ahead = int(_git(repo, "rev-list", "--count", f"{start}..HEAD")[1].decode().strip() or 0)
    add("committed", "The tests are committed: nothing in the working copy, a stash or another branch",
        ahead > 0 and not state["leftovers"], ", ".join(state["leftovers"]) or f"{ahead} commit(s)")
    paths = [s["path"] for s in size.diff_stats(repo, start)] if ahead else []
    allowed = [size.glob_regex(g) for g in expected["allowed"]]
    outside = [p for p in paths if not any(r.match(p) for r in allowed)]
    add("scope", "The work stays within the tests and the code of the ticket", bool(paths) and not outside, ", ".join(outside))
    for item in expected.get("forbidden_added", []):
        pattern = re.compile(item["pattern"])
        scope = [size.glob_regex(g) for g in item.get("paths", [])]
        hits = [p for p in paths if (not scope or any(r.match(p) for r in scope))
                and any(pattern.search(line) for line in _changed_lines(repo, start, p))]
        add(item["id"], f"Absent from the work: {item['what']}", not hits, ", ".join(hits))

    tracked = _git(repo, "ls-tree", "-r", "--name-only", "HEAD")[1].decode("utf-8", "replace").splitlines()
    skipped = [p for p in tracked if qa.is_test(p) and qa.skips((_read_at(repo, "HEAD", p) or "").splitlines())]
    gate = qa.gate_disabled(repo, start, paths) if paths else {"status": qa.OK, "evidence": ""}
    add("tests-active", "No test is disabled: the one the change skipped is back in play, none is removed",
        not skipped and gate["status"] != qa.FAIL, ", ".join(skipped) or (gate["evidence"] if gate["status"] == qa.FAIL else ""))

    code_globs = [size.glob_regex(g) for g in expected["code"]]
    fixed = any(r.match(p) for p in paths for r in code_globs)
    with tempfile.TemporaryDirectory() as tmp:
        head = os.path.join(tmp, "snapshot")    # the content of HEAD, never executed: each run starts from it
        os.makedirs(head)
        _checkout(repo, head)
        stage = os.path.join(tmp, "repo")        # the same folder for each run: its name says nothing about the run

        def play(command: list[str], *overlays: tuple[str, str]) -> tuple[bool, str]:
            shutil.rmtree(stage, ignore_errors=True)
            shutil.copytree(head, stage)
            for source, rel in overlays:
                target = os.path.join(stage, rel)
                if rel:
                    shutil.rmtree(target, ignore_errors=True)
                _overlay(source, target)
            return _run(command, stage)

        reference = (os.path.join(hidden, "reference"), "")
        if fixed:
            ok, detail = play(expected["visible_command"])
            ok_hidden, detail_hidden = play(expected["hidden_command"], (os.path.join(hidden, "tests"), expected["hidden_command"][-1]))
            add("outcome", "The code was fixed: the suite passes and the ticket's criteria hold (hidden tests)",
                ok and ok_hidden, f"suite: {detail}; criteria: {detail_hidden}")
        else:
            add("outcome", "The code was not touched: the defects are left visible through red tests", True,
                "accepted outcome, provided the faulty variants below are caught")
        portable, detail = play(expected["visible_command"], reference)
        add("tests-portable", "The tests pass on a correct reference implementation: they come from the criteria",
            portable, detail)
        alive = [name for name in (mutants if portable else [])
                 if play(expected["visible_command"], reference, (os.path.join(hidden, "mutants", name), ""))[0]]
        add("variants", f"Each faulty variant of the code ({len(mutants)}) makes the suite fail",
            portable and not alive,
            ("not caught: " + ", ".join(alive)) if alive else ("" if portable else "not measurable: the tests do not pass on the reference"))

    if mapping is None:
        add("mapping", "Each testable criterion has its named test in the mapping", False, "no mapping given")
    else:
        try:
            if not (isinstance(mapping, dict) and isinstance(mapping.get("criteria"), list)):
                raise Refused("mapping: an object {criteria: [...], not_covered: [...]}")
            result = qa.gate_criteria(repo, ticket_text, mapping)
            total = len(ticket.check(ticket_text, [])["criteria"])
            covered = {row["criterion"] for row in mapping["criteria"] if row["tests"]}
            missing = sorted(set(range(1, total + 1)) - covered - set(expected.get("may_skip", [])))
            ok = result["status"] != qa.FAIL and not missing
            detail = result["evidence"] if result["status"] == qa.FAIL else (
                f"without a test: criterion(s) {', '.join(map(str, missing))}" if missing else result["evidence"])
        except (Refused, OSError, ValueError, TypeError, KeyError) as exc:
            ok, detail = False, str(exc)[:200]
        add("mapping", "Each testable criterion has its named test in the mapping", ok, detail)
    return {"pass": all(c["ok"] for c in checks), "checks": checks}
