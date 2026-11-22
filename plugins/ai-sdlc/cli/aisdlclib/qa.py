"""The gates of `/qa`: what a program can say about the tests of a change.

Four gates, each `ok`, `failed`, or `unmeasured` when the repository gives nothing to decide on:
- **disabled**: the diff skips, disables or deletes no test;
- **repeat**: the test command passes several times in a row (a flaky test fails here);
- **coverage**: the added lines are executed, according to an lcov or Cobertura report of the repository;
- **criteria**: each acceptance criterion of the ticket has a named test that exists, or a written reason.

Writing the tests is the agent's job. Saying that they hold is not: that is this module."""
from __future__ import annotations

import contextlib
import os
import re
import shlex
import signal
import subprocess
import tempfile
import time
import xml.etree.ElementTree as ET
from typing import Any, Sequence

from . import size, ticket
from .context import Refused, _git, resolve_base
from .devgrade import _changed_lines

OK, FAIL, UNKNOWN = "ok", "failed", "unmeasured"
RUN_TIMEOUT = 600      # per run
RUN_BUDGET = 1800      # for all runs
MAX_REPORT = 50_000_000
MIN_REASON = 15
_SKIP = re.compile(r"unittest\.skip|(?:^|\s)@skip\w*\b|\bfrom\s+(?:unittest|pytest)\b[^\n#]{0,40}\bimport\b[^\n#]{0,120}\bskip\w*\b|\bskipTest\b|\bSkipTest\b|pytest\.mark\.(?:skip|xfail)|pytest\.(?:skip|xfail)\(|importorskip|"
                   r"expectedFailure|\b(?:it|test|describe|context)\.(?:skip|todo|only|fixme|fail)\b|(?<![.\w])(?<!def )[xf](?:it|describe|test)\(|"
                   r"@Disabled\w*\b|@Ignore\b|\[Ignore\b|Skip\s*=|enabled\s*=\s*false|assumeTrue\(false\)|"
                   r"\bt\.Skip(?:f|Now)?\(|#\[ignore\b|\bpending\(|__test__\s*=\s*False|collect_ignore|--deselect")
_TEST_PATH = re.compile(r"(?:^|/)(?:tests?|__tests__|__mocks__|specs?|e2e|cypress)/|(?:^|/)tests?\.py$|(?:^|/)test_[^/]+\.\w+$|"
                        r"(?:^|/)conftest\.py$|_test\.\w+$|\.(?:test|spec)\.[cm]?[jt]sx?$|(?:Tests?|IT|Spec)\.(?:java|kt|cs|scala|php)$|"
                        r"_spec\.rb$|\.feature$", re.IGNORECASE)
_TEST_CONFIG = re.compile(r"(?:^|/)(?:pytest\.ini|tox\.ini|setup\.cfg|pyproject\.toml|conftest\.py|package\.json|phpunit\.xml(?:\.dist)?|"
                          r"jest\.config\.\w+|vitest\.config\.\w+|playwright\.config\.\w+|karma\.conf\.\w+|\.mocharc[\w.]*|"
                          r"\.rspec|noxfile\.py|build\.gradle(?:\.kts)?|pom\.xml)$")
_CODE_EXT = (".py", ".js", ".jsx", ".mjs", ".ts", ".tsx", ".go", ".java", ".kt", ".rb", ".rs", ".cs", ".php", ".c", ".cpp",
             ".cc", ".h", ".hpp", ".swift", ".scala", ".vue", ".svelte", ".dart")
_ASSERT = re.compile(r"\bassert\w*\b|\bexpect\(|\bshould\b|\brequire\.\w+\(|\bverify\(")
# A test is defined at the start of a line. `def test_x` inside a string is test code written as data by another
# test, not a test of the suite: matching it anywhere made a renamed sample string look like a removed test.
_TEST_NAME = re.compile(r"^\s*(?:async\s+)?def\s+(test\w*)|^\s*func\s+(Test\w+)|^\s*(?:pub\s+)?(?:async\s+)?fn\s+(test\w*)|"
                        r"\b(?:it|test)\(\s*['\"`]([^'\"`]+)|^\s*(?:public\s+|private\s+|protected\s+)?void\s+(test\w+)\s*\(")
_SHELL = {"&&", "||", "|", ";", "&", ">", ">>", "<", "2>&1"}
_SECRET = re.compile(r"TOKEN|SECRET|PASSWORD|PASSWD|CREDENTIAL|API_?KEY|PRIVATE", re.IGNORECASE)
_HUNK = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@")


def _comment(line: str) -> bool:
    text = line.lstrip()
    return text.startswith(("//", "/*", "*", "--")) or (text.startswith("#") and not text.startswith(("#[", "#!")))


def skips(lines: list[str]) -> bool:
    """One of these lines skips or disables a test. A comment line that talks about it skips nothing."""
    return any(_SKIP.search(line) for line in lines if not _comment(line))


def is_test(path: str) -> bool:
    return bool(_TEST_PATH.search(path))


def _gate(ident: str, title: str, status: str, evidence: str, action: str | None = None) -> dict[str, Any]:
    return {"id": ident, "title": title, "status": status, "evidence": evidence, "action": None if status == OK else action}


def _names(lines: list[str]) -> set[str]:
    return {next(g for g in m.groups() if g) for line in lines for m in _TEST_NAME.finditer(line)}


def gate_disabled(repo: str, base: str, paths: list[str], spared: Sequence[re.Pattern[str]] = ()) -> dict[str, Any]:
    """No test skipped, disabled, removed or deleted by the diff. What a rule cannot decide
    (the test configuration changed, assertions disappeared) leaves the gate unmeasured."""
    title = "No test disabled, removed or deleted"
    code, out = _git(repo, "diff", "-z", "--name-only", "--diff-filter=D", "-M", f"{resolve_base(repo, base)}...HEAD")
    deleted = [p for p in out.decode("utf-8", "replace").split("\0")
               if p and is_test(p) and not any(r.match(p) for r in spared)] if code == 0 else []
    skipped, gone, weakened = [], [], []
    config = [p for p in paths if _TEST_CONFIG.search(p)]
    for path in paths:
        if not (is_test(path) or _TEST_CONFIG.search(path)):
            continue
        added, removed = _changed_lines(repo, base, path, "+"), _changed_lines(repo, base, path, "-")
        if skips(added):
            skipped.append(path)
        lost = sorted(_names(removed) - _names(added))
        if lost and os.path.exists(os.path.join(repo, path)):
            gone.append(f"{path} ({', '.join(lost[:3])})")
        if os.path.exists(os.path.join(repo, path)) and \
                sum(bool(_ASSERT.search(line)) for line in removed) > sum(bool(_ASSERT.search(line)) for line in added):
            weakened.append(path)
    if deleted or skipped or gone:
        said = ([f"deleted: {p}" for p in deleted[:3]] + [f"skipped or disabled: {p}" for p in skipped[:3]]
                + [f"test removed or renamed: {g}" for g in gone[:3]])
        return _gate("disabled", title, FAIL, "; ".join(said),
                     "Put the test back and fix what makes it fail. If the removal is intended (a test about "
                     "the skip itself, a rename), a human says so in the PR: the gate does not decide it.")
    if config or weakened:
        said = [f"test configuration changed: {p}" for p in config[:3]] + [f"fewer assertions than before: {p}" for p in weakened[:3]]
        return _gate("disabled", title, UNKNOWN, "; ".join(said),
                     "Say in the PR what this change does to the collected tests and to the assertions.")
    return _gate("disabled", title, OK, "nothing skipped, removed or deleted")


def _argv(command: str) -> list[str]:
    try:
        argv = shlex.split(command)
    except ValueError as exc:
        raise Refused(f"--run unreadable: {exc}") from exc
    if not argv:
        raise Refused("--run is empty")
    if any(t in _SHELL for t in argv) or re.match(r"^\w+=", argv[0]) or argv[0] in ("cd", "export", "source", "."):
        raise Refused("--run is started without a shell: no &&, pipe, redirection or leading VAR=value. "
                      "Give a command of the repository (make test, ./scripts/test.sh), or sh -c '…'")
    return argv


def gate_repeat(repo: str, command: str | None, runs: int) -> dict[str, Any]:
    """The test command, run several times: all runs pass, or it is a failure or a flaky test.
    It runs in the repository, without a sandbox; variables that look like secrets are not passed to it."""
    title = f"The suite passes {runs} times in a row"
    if not command:
        return _gate("repeat", title, UNKNOWN, "no test command given",
                     "Run again with --run \"<the repository's test command>\".")
    argv = _argv(command)
    env = {k: v for k, v in os.environ.items() if not _SECRET.search(k)}
    passed, last, started = 0, "", time.monotonic()
    for index in range(runs):
        if time.monotonic() - started > RUN_BUDGET:
            return _gate("repeat", title, FAIL, f"{index} run(s) in more than {RUN_BUDGET} s: budget exceeded",
                         "Give a narrower command: the whole suite is too slow to be repeated.")
        with tempfile.TemporaryFile() as log:
            try:
                proc = subprocess.Popen(argv, cwd=repo, stdout=log, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
                                        env=env, start_new_session=True)
            except OSError as exc:
                return _gate("repeat", title, FAIL, f"{argv[0]}: {type(exc).__name__}",
                             "The command does not start from the repository root: check its name and its path.")
            try:
                code = proc.wait(timeout=RUN_TIMEOUT)
            except subprocess.TimeoutExpired:
                with contextlib.suppress(OSError):
                    os.killpg(proc.pid, signal.SIGKILL)   # the whole group: a launcher leaves children behind
                proc.wait()
                return _gate("repeat", title, FAIL, f"run {index + 1}: more than {RUN_TIMEOUT} s",
                             "The suite does not return: look for a test waiting for input, a port or a lock.")
            if code != 0:
                log.seek(max(0, log.tell() - 4000))
                last = " ".join(log.read().decode("utf-8", "replace").strip().splitlines()[-1:])[:160]
            passed += code == 0
    if passed == runs:
        return _gate("repeat", title, OK, f"{runs} runs out of {runs}, in the same order: a test that fails rarely "
                                          "or depending on the order can still pass")
    if passed:
        return _gate("repeat", title, FAIL, f"flaky: {passed} runs out of {runs} ({last})",
                     "Find what makes the test flaky (order, clock, network, shared state): do not rerun it until it passes.")
    return _gate("repeat", title, FAIL, f"0 runs out of {runs} ({last})", "Fix the failing code or test.")


def read_coverage(path: str) -> dict[str, dict[int, int]]:
    """Per file, the measured lines and their hit counts, read from an lcov or Cobertura report."""
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            text = fh.read(MAX_REPORT + 1)
    except OSError as exc:
        raise Refused(f"{path}: unreadable coverage report ({exc})") from exc
    if len(text) > MAX_REPORT:
        raise Refused(f"{path}: report over {MAX_REPORT} characters, not read")
    found: dict[str, dict[int, int]] = {}
    if text.lstrip().startswith("<"):
        if "<!DOCTYPE" in text or "<!ENTITY" in text:
            raise Refused(f"{path}: an XML report with a DOCTYPE or entities is not read")
        try:
            root = ET.fromstring(text)
        except ET.ParseError as exc:
            raise Refused(f"{path}: unreadable XML ({exc})") from exc
        for cls in root.iter("class"):
            lines = found.setdefault((cls.get("filename") or "").replace("\\", "/"), {})
            for line in cls.iter("line"):
                try:
                    number, hits = int(line.get("number", "")), int(float(line.get("hits", "0")))
                except ValueError:
                    continue
                lines[number] = max(lines.get(number, 0), hits)
        return found
    current: dict[int, int] | None = None
    for line in text.splitlines():
        if line.startswith("SF:"):
            current = found.setdefault(line[3:].strip().replace("\\", "/"), {})
        elif line.startswith("DA:") and current is not None:
            parts = line[3:].split(",")
            if len(parts) >= 2 and parts[0].isdigit() and parts[1].lstrip("-").isdigit():
                current[int(parts[0])] = max(current.get(int(parts[0]), 0), int(parts[1]))
    return found


def added_lines(repo: str, base: str) -> dict[str, set[int]]:
    """Per file, only the lines the diff adds or rewrites: a deletion adds none."""
    commit = resolve_base(repo, base)
    code, out = _git(repo, "diff", "-z", "--name-only", "--no-renames", "--diff-filter=AM", f"{commit}...HEAD")
    if code != 0:
        raise Refused(f"no diff possible between {base} and HEAD")
    found: dict[str, set[int]] = {}
    for raw in filter(None, out.split(b"\0")):
        path = raw.decode("utf-8", "replace")
        code, patch = _git(repo, "--literal-pathspecs", "diff", "-U0", "--no-color", "--no-ext-diff", "--no-textconv",
                           "--no-renames", f"{commit}...HEAD", "--", path)
        lines = found.setdefault(path, set())
        for line in patch.decode("utf-8", "replace").splitlines() if code == 0 else []:
            match = _HUNK.match(line)
            if match and (match[2] is None or int(match[2]) > 0):
                start, count = int(match[1]), int(match[2] or 1)
                lines.update(range(start, start + count))
    return found


def _report_key(path: str, measured: dict[str, dict[int, int]]) -> str | None:
    """The report entry that names this file: the longest common suffix, on whole segments."""
    parts = path.split("/")
    best, score = None, 0
    for key in measured:
        other = key.split("/")
        common = 0
        while common < min(len(parts), len(other)) and parts[-1 - common] == other[-1 - common]:
            common += 1
        if common > score and (common == len(parts) or common == len(other)):
            best, score = key, common
    return best


def gate_coverage(repo: str, base: str, report: str | None, threshold: int) -> dict[str, Any]:
    """The share of added lines, in non-test code, that the tests execute. The report is
    taken at its word: nothing prevents writing it by hand, and the gate does not claim otherwise."""
    title = f"The added lines are executed by the tests (at least {threshold} %)"
    if not report:
        return _gate("coverage", title, UNKNOWN, "no coverage report given",
                     "Produce an lcov or Cobertura report with the repository's tool, then run again with --coverage <file>.")
    measured = read_coverage(report)
    stamp = (_git(repo, "log", "-1", "--format=%ct", "HEAD")[1] or b"").decode().strip()
    if stamp.isdigit() and os.path.getmtime(report) < int(stamp):
        return _gate("coverage", title, UNKNOWN, "the report is older than the last commit",
                     "Produce the report again on this branch, after the last commit.")
    changed = {p: lines for p, lines in added_lines(repo, base).items()
               if lines and p.endswith(_CODE_EXT) and not is_test(p) and not _TEST_CONFIG.search(p)}
    total = hit = 0
    missed: list[str] = []
    absent: list[str] = []
    used: dict[str, str] = {}
    for path, lines in sorted(changed.items()):
        key = _report_key(path, measured)
        if key is None:
            absent.append(path)
            continue
        if key in used:
            return _gate("coverage", title, UNKNOWN, f"ambiguous path in the report: {key} stands for {used[key]} and {path}",
                         "Produce the report with paths relative to the repository root.")
        used[key] = path
        seen = [n for n in sorted(lines) if n in measured[key]]
        total += len(seen)
        hit += sum(measured[key][n] > 0 for n in seen)
        missed += [f"{path}:{n}" for n in seen if measured[key][n] == 0]
    share = 100 * hit // total if total else 0
    evidence = f"{hit} lines out of {total} ({share} %), {len(changed) - len(absent)} file(s) out of {len(changed)} measured"
    if missed:
        evidence += f"; never executed: {', '.join(missed[:4])}"
    if total and share < threshold:
        return _gate("coverage", title, FAIL, evidence,
                     "Write the test that goes through these lines, or say in the PR why they have none.")
    if absent or not total:
        return _gate("coverage", title, UNKNOWN, evidence + (f"; missing from the report: {', '.join(absent[:4])}" if absent else ""),
                     "A changed file missing from the report is executed by no test, or the report does not track it: check it.")
    return _gate("coverage", title, OK, evidence)


def _defined(name: str, text: str) -> bool:
    """The name appears as a whole word on a line that is not a comment."""
    pattern = re.compile(r"(?<![\w])" + re.escape(name) + r"(?![\w])")
    return any(pattern.search(line) for line in text.splitlines() if not line.lstrip().startswith(("#", "//", "*", "/*")))


def gate_criteria(repo: str, ticket_text: str | None, mapping: Any) -> dict[str, Any]:
    """Each acceptance criterion has a named test that exists in a test file of the repository, or a
    written reason. A criterion left without a test waits for a human; no tested criterion is a failure."""
    title = "Each acceptance criterion has its test"
    if ticket_text is None or mapping is None:
        return _gate("criteria", title, UNKNOWN, "ticket or mapping missing",
                     "Run again with --ticket <ticket.md> and --trace <mapping.json>.")
    criteria = ticket.check(ticket_text, [])["criteria"]
    if not criteria:
        return _gate("criteria", title, UNKNOWN, "the ticket lists no criterion", "Run the ticket through the ticket skill first.")
    rows = mapping.get("criteria") if isinstance(mapping, dict) else None
    spared = mapping.get("not_covered", []) if isinstance(mapping, dict) else None
    if not isinstance(rows, list) or not isinstance(spared, list):
        raise Refused("mapping: an object {criteria: [{criterion, tests}], not_covered: [{criterion, reason}]}")
    covered: dict[int, list[str]] = {}
    for row in rows:
        if not (isinstance(row, dict) and type(row.get("criterion")) is int and isinstance(row.get("tests"), list)
                and all(isinstance(t, str) and t.strip() for t in row["tests"])):
            raise Refused(f"mapping: malformed row ({row!r:.80})")
        covered.setdefault(row["criterion"], []).extend(row["tests"])
    excused = {r["criterion"] for r in spared if isinstance(r, dict) and type(r.get("criterion")) is int
               and isinstance(r.get("reason"), str) and len(r["reason"].strip()) >= MIN_REASON}
    root = os.path.realpath(repo)
    problems = []
    for number in range(1, len(criteria) + 1):
        tests = covered.get(number, [])
        if not tests and number not in excused:
            problems.append(f"criterion {number} without a test or a reason of at least {MIN_REASON} characters")
        for ref in tests:
            path, _, name = ref.partition("::")
            path, name = path.strip(), name.split("::")[-1].strip()
            if "\0" in path or len(path) > 300:
                problems.append(f"criterion {number}: unreadable test path")
                continue
            full = os.path.realpath(os.path.join(repo, path))
            if not name:
                problems.append(f"criterion {number}: {ref} does not name a test (path::name)")
            elif path.startswith("/") or os.path.commonpath([root, full]) != root or not os.path.isfile(full):
                problems.append(f"criterion {number}: {path} does not exist in the repository")
            elif not is_test(path):
                problems.append(f"criterion {number}: {path} is not a test file")
            else:
                with open(full, encoding="utf-8", errors="replace") as fh:
                    if not _defined(name, fh.read(2_000_000)):
                        problems.append(f"criterion {number}: {name} not found in {path}")
    unknown = sorted((set(covered) | excused) - set(range(1, len(criteria) + 1)))
    if unknown:
        problems.append(f"criterion(s) {', '.join(map(str, unknown))}: the ticket has only {len(criteria)}")
    tested = [n for n in range(1, len(criteria) + 1) if covered.get(n)]
    if not problems and not tested:
        problems.append("no criterion has a test: all are excused")
    if problems:
        return _gate("criteria", title, FAIL, "; ".join(problems[:5]),
                     "Write the missing test, or put the criterion in not_covered with its reason.")
    shared = {ref for refs in covered.values() for ref in refs if sum(ref in r for r in covered.values()) > max(1, len(criteria) // 2)}
    if excused or shared:
        said = [f"{len(tested)} criteria out of {len(criteria)} tested"]
        said += [f"without a test, with a reason: {sorted(excused)}"] if excused else []
        said += [f"one same test for more than half of the criteria: {', '.join(sorted(shared)[:2])}"] if shared else []
        return _gate("criteria", title, UNKNOWN, "; ".join(said),
                     "Have a human approve the criteria without a test, and check that a single test really covers several criteria.")
    return _gate("criteria", title, OK, f"{len(criteria)} criteria out of {len(criteria)}")


def run_gates(table: dict[str, Any], repo: str, base: str, command: str | None = None, runs: int | None = None,
              coverage: str | None = None, ticket_text: str | None = None, mapping: Any = None) -> dict[str, Any]:
    stats = size.diff_stats(repo, base)
    if not stats:
        raise Refused(f"no change between {base} and HEAD: nothing to check")
    dirty = _git(repo, "status", "--porcelain")[1].decode("utf-8", "replace").strip()
    if dirty:   # two gates read HEAD, two read the disk: they must talk about the same change
        raise Refused("the working copy is not committed (" + dirty.splitlines()[0].strip() + "…): commit the tests, "
                      "and keep the coverage report and the mapping outside the repository")
    settings = table["qa"]
    gates = [gate_disabled(repo, base, [s["path"] for s in stats]),
             gate_repeat(repo, command, runs or settings["runs"]),
             gate_coverage(repo, base, coverage, settings["diff_coverage"]),
             gate_criteria(repo, ticket_text, mapping)]
    failed = [g["id"] for g in gates if g["status"] == FAIL]
    unknown = [g["id"] for g in gates if g["status"] == UNKNOWN]
    return {"pass": not failed and not unknown, "failed": failed, "unknown": unknown, "gates": gates}


def render_md(result: dict[str, Any]) -> str:
    if result["failed"]:
        head = f"QA: {len(result['failed'])} gate(s) failed."
    elif result["unknown"]:
        head = f"QA: nothing failed, {len(result['unknown'])} gate(s) unmeasured."
    else:
        head = "QA: all four gates pass."
    out = [head]
    for gate in result["gates"]:
        out.append(f"- {gate['status']} — {gate['title']} ({gate['evidence']})" + (f". {gate['action']}" if gate["action"] else ""))
    out.append("An unmeasured gate is not a passed gate: say so in the PR.")
    return "\n".join(out) + "\n"
