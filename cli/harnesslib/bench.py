"""`bench` subcommand: the bench that measures a before and an after.

A **task** is a typical piece of work given to an agent on a sample project (`fixtures/repos/<name>/tasks/<id>/`).
It is played on several **arms** of the same repository: `bare` (no instructions), `asis` (the repository as
found), `harness` (after the harness step, by default the fixture author's).
The gap between the arms is the proof that the harness helps, or that a line no longer does.

  bench plan                              the agent runs of a campaign, and their estimated cost
  bench prepare <fixture> <dest> --arm …  the working repository of an arm, with a starting commit
  bench check <fixture> <task> <dir>      grades the work handed in: tests, hidden tests, temptations
  bench play <fixture> <task> --arm …     plays the task with a neutral agent, grades, files, records
  bench init <fixture>                    plays step 1 with a neutral agent, with the owner's answers
  bench selftest <fixture>                is the task well posed? solution green, temptation red
  bench record … / bench report           the results registry, by skill, arm and model

Only `play` and `init` start an agent, and always the same one: a separate process, confined to its working
copy, that receives only the statement and loads only the repository's instructions. The rest prepares,
grades and keeps the registry."""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import date
from typing import Any

from . import facts, fixtures, maturity, owner

ARMS = ("bare", "asis", "harness")
# Estimated cost of one agent run, in tokens. Audit and init: the first seven blind evaluations,
# played by an agent of the session. Task: fresh tokens measured by `bench play` on 2026-11-11
# (70,000 and 75,000), excluding cache reads, which add about 650,000 per run.
COST = {"audit": 130_000, "init": 130_000, "task": 75_000, "step": 90_000}
RESULTS = os.path.join(os.path.dirname(fixtures.FIXTURES_ROOT), "results.jsonl")
OVERLAY_SKIP = {"RUN.md", "README.md", "REMOVE.txt"}   # what describes a run is not harness
OVERLAY_HARNESS_KEPT = {".harness/audit.json", ".harness/harvest.json"}   # what a next step must find again
OVERLAY_REMOVE = "REMOVE.txt"                    # one path per line: what the step deleted from the repository
GIT_ENV = {"GIT_AUTHOR_NAME": "owner", "GIT_AUTHOR_EMAIL": "owner@example.test",
           "GIT_COMMITTER_NAME": "owner", "GIT_COMMITTER_EMAIL": "owner@example.test"}


def _git(workdir: str, *args: str, env: dict | None = None, check: bool = True) -> str:
    out = subprocess.run(["git", "-C", workdir, *args], capture_output=True, text=True,
                         env={**os.environ, **GIT_ENV, **(env or {})})
    if check and out.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)}: {out.stderr.strip()}")
    return out.stdout


def resolve(name: str) -> str:
    return name if os.path.isdir(name) else os.path.join(fixtures.FIXTURES_ROOT, name)


def list_tasks(fixture_dir: str) -> list[str]:
    base = os.path.join(fixture_dir, "tasks")
    return sorted(d for d in os.listdir(base) if os.path.isfile(os.path.join(base, d, "task.json"))) \
        if os.path.isdir(base) else []


def load_task(fixture_dir: str, task_id: str) -> dict[str, Any]:
    task_dir = os.path.join(fixture_dir, "tasks", task_id)
    with open(os.path.join(task_dir, "task.json"), encoding="utf-8") as fh:
        task = json.load(fh)
    task["dir"] = task_dir
    return task


def author_overlay(fixture_dir: str) -> str | None:
    """The harness laid by the fixture author: the last `runs/*-author` that holds an AGENTS.md."""
    runs = os.path.join(fixture_dir, "runs")
    found = sorted(d for d in os.listdir(runs) if d.endswith("-author")
                   and os.path.isfile(os.path.join(runs, d, "AGENTS.md"))) if os.path.isdir(runs) else []
    return os.path.join(runs, found[-1]) if found else None


def available_arms(fixture_dir: str) -> list[str]:
    arms = ["bare"]
    if facts.instruction_corpus(os.path.join(fixture_dir, "repo")):
        arms.append("asis")
    if author_overlay(fixture_dir):
        arms.append("harness")
    return arms


def prepare(fixture_dir: str, dest: str, arm: str, overlay: str | None = None) -> dict[str, Any]:
    """The working repository of an arm: a copy of `repo/` turned into a git repository with one commit."""
    if arm not in ARMS:
        raise SystemExit(f"unknown arm: {arm} (expected: {', '.join(ARMS)})")
    removed = fixtures.bare_copy(fixture_dir, dest, branch="main", keep_instrumentation=(arm == "asis"), commit=False)
    copied: list[str] = []
    if arm == "harness":
        overlay = overlay or author_overlay(fixture_dir)
        if not overlay:
            raise SystemExit("harness arm: no runs/*-author, and no --overlay")
        for root, dirs, files in os.walk(overlay):
            dirs[:] = [d for d in dirs if d != ".git"]
            for name in files:
                rel = os.path.relpath(os.path.join(root, name), overlay)
                if rel in OVERLAY_SKIP:
                    continue
                os.makedirs(os.path.dirname(os.path.join(dest, rel)) or dest, exist_ok=True)
                shutil.copyfile(os.path.join(root, name), os.path.join(dest, rel))
                copied.append(rel.replace(os.sep, "/"))
        for rel in (facts._read(os.path.join(overlay, OVERLAY_REMOVE)) or "").splitlines():
            rel = rel.split("#", 1)[0].strip()
            target = os.path.normpath(os.path.join(dest, rel))
            if rel and target.startswith(os.path.abspath(dest) + os.sep) and os.path.isfile(target):
                os.remove(target)
                removed.append(rel)
    fixtures.commit_all(dest, "main")
    return {"arm": arm, "dest": dest, "removed": removed, "overlay": sorted(copied)}


def diff(workdir: str) -> dict[str, dict[str, Any]]:
    """What the agent changed since the starting commit, untracked files included:
    by path, the added lines and the number of lines touched."""
    base = _git(workdir, "rev-list", "--max-parents=0", "HEAD").split()[0]
    with tempfile.TemporaryDirectory() as tmp:
        env = {"GIT_INDEX_FILE": os.path.join(tmp, "index")}
        _git(workdir, "add", "-A", env=env)
        raw = _git(workdir, "diff", "--cached", "--unified=0", "--no-color", "--no-renames", base, env=env)
    changes: dict[str, dict[str, Any]] = {}
    current: dict[str, Any] | None = None
    for line in raw.splitlines():
        if line.startswith("diff --git "):
            path = line.split(" b/", 1)[1]
            current = changes.setdefault(path, {"added": [], "removed": [], "changed": 0})
        elif current is None or line.startswith(("+++", "---", "@@", "index ", "new file", "deleted file", "Binary")):
            continue
        elif line.startswith("+"):
            current["added"].append(line[1:])
            current["changed"] += 1
        elif line.startswith("-"):
            current["removed"].append(line[1:])
            current["changed"] += 1
    return changes


def patch_of(workdir: str) -> str:
    """The full diff of the work handed in, untracked files included, since the starting commit."""
    base = _git(workdir, "rev-list", "--max-parents=0", "HEAD").split()[0]
    with tempfile.TemporaryDirectory() as tmp:
        env = {"GIT_INDEX_FILE": os.path.join(tmp, "index")}
        _git(workdir, "add", "-A", env=env)
        return _git(workdir, "diff", "--cached", "--no-color", base, env=env)


DIFF_KINDS = ("forbid_changed", "max_changed_lines", "forbid_added", "forbid_removed", "require_added")


def _diff_check(spec: dict, changes: dict[str, dict[str, Any]]) -> tuple[bool, str]:
    """A diff check may combine several conditions: all must hold. `forbid_removed` exists because
    forbidding any change to a guardrail also punished whoever strengthened it: weakening means
    removing a line that runs a check, not adding one."""
    def lines(rule: dict, side: str) -> list[str]:
        return [f"{p}: {l.strip()[:80]}" for p, c in changes.items() if re.search(rule["paths"], p)
                for l in c[side] if re.search(rule.get("pattern", ""), l)]

    failures: list[str] = []
    notes: list[str] = []
    if "forbid_changed" in spec:
        hits = sorted(p for p in changes if re.search(spec["forbid_changed"], p))
        if hits:
            failures.append("touched: " + ", ".join(hits))
    if "max_changed_lines" in spec:
        rule = spec["max_changed_lines"]
        total = sum(c["changed"] for p, c in changes.items() if re.search(rule["paths"], p))
        notes.append(f"{total} line(s) touched, maximum {rule['max']}")
        if total > rule["max"]:
            failures.append(notes[-1])
    if "forbid_added" in spec:
        hits = lines(spec["forbid_added"], "added")
        if hits:
            failures.append("added: " + "; ".join(hits[:3]))
    if "forbid_removed" in spec:
        hits = lines(spec["forbid_removed"], "removed")
        if hits:
            failures.append("removed: " + "; ".join(hits[:3]))
    if "require_added" in spec:
        rule = spec["require_added"]
        if not lines(rule, "added"):
            failures.append(f"no added line contains {rule['pattern']} under {rule['paths']}")
    return not failures, " ; ".join(failures) if failures else "; ".join(notes)


def _run(command: str, workdir: str, timeout: int) -> tuple[bool, str]:
    try:
        out = subprocess.run(command, shell=True, cwd=workdir, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return False, f"timeout of {timeout} s exceeded"
    tail = "\n".join((out.stdout + out.stderr).strip().splitlines()[-12:])
    return out.returncode == 0, "" if out.returncode == 0 else tail


def check(fixture_dir: str, task_id: str, workdir: str) -> dict[str, Any]:
    """Grades the work handed in, in `workdir`. Order: the diff first (before any install), then
    the project's commands, then the hidden tests, copied at the last moment so that the agent has
    never seen them and they do not count in its diff."""
    task = load_task(fixture_dir, task_id)
    timeout = task.get("timeout", 600)
    changes = diff(workdir)
    results: dict[str, dict[str, Any]] = {}
    setup_error = ""
    for spec in task["checks"]:
        if "run" not in spec:
            passed, detail = _diff_check(spec, changes)
            results[spec["id"]] = {"passed": passed, "detail": detail}
    if task.get("setup"):
        ok, detail = _run(task["setup"], workdir, timeout)
        setup_error = "" if ok else f"setup failed: {detail}"
    for acceptance in (False, True):
        if acceptance:
            for item in task.get("acceptance", []):
                target = os.path.join(workdir, item["to"])
                os.makedirs(os.path.dirname(target), exist_ok=True)
                shutil.copyfile(os.path.join(task["dir"], item["from"]), target)
        for spec in task["checks"]:
            if "run" in spec and bool(spec.get("acceptance")) == acceptance:
                passed, detail = (False, setup_error) if setup_error else _run(spec["run"], workdir, timeout)
                results[spec["id"]] = {"passed": passed, "detail": detail}
    for item in task.get("acceptance", []):                       # leave the repository as the agent handed it in
        target = os.path.join(workdir, item["to"])
        if os.path.exists(target):
            os.remove(target)
    checks = [{"id": s["id"], "what": s["what"], **results[s["id"]]} for s in task["checks"]]
    passed = sum(c["passed"] for c in checks)
    return {"fixture": os.path.basename(os.path.normpath(fixture_dir)), "task": task_id, "checks": checks,
            "files_changed": sorted(changes), "score": f"{passed}/{len(checks)}", "ok": passed == len(checks)}


AGENT_TIMEOUT = 1800
# Variables of the calling session that would tell the evaluated agent about other repositories.
AGENT_ENV_SCRUB = ("CLAUDE_ADDITIONAL_DIRECTORIES", "CLAUDE_CODE_ADDITIONAL_DIRECTORIES_CLAUDE_MD")


def repo_root() -> str:
    return os.path.dirname(os.path.dirname(os.path.abspath(fixtures.FIXTURES_ROOT)))


def agent_command(task: dict[str, Any]) -> list[str]:
    """The command of the evaluated agent. Neutral: only the working repository's settings and
    instructions (`--setting-sources project`), no MCP server, no skill. Confined: edits accepted in its
    folder, commands limited to the task's `agent_bash` list, everything else denied without a
    question (`--permission-prompts none`), reading this repository forbidden. Never a permission
    bypass."""
    bash = [f"Bash({rule})" for rule in task.get("agent_bash", [])]
    return ["claude", "-p", "--output-format", "json", "--no-session-persistence",
            "--setting-sources", "project", "--strict-mcp-config", "--disable-slash-commands",
            "--permission-mode", "acceptEdits", "--permission-prompts", "none",
            "--allowedTools", "Read", "Edit", "Write", "Glob", "Grep", *bash,
            "--disallowedTools", f"Read(/{repo_root()}/**)"]


def run_agent(workdir: str, prompt: str, task: dict[str, Any]) -> dict[str, Any]:
    """Starts the agent in `workdir` with the statement as its only message, and returns its report and
    its usage. No model name is kept: the registry holds a generation label."""
    cmd = agent_command(task)
    env = {k: v for k, v in os.environ.items() if k not in AGENT_ENV_SCRUB}
    try:
        out = subprocess.run(cmd[:2] + [prompt] + cmd[2:], cwd=workdir, env=env, stdin=subprocess.DEVNULL,
                             capture_output=True, text=True, timeout=task.get("agent_timeout", AGENT_TIMEOUT))
    except subprocess.TimeoutExpired:
        return {"report": "", "error": "timeout exceeded", "usage": {}}
    try:
        data = json.loads(out.stdout)
    except json.JSONDecodeError:
        return {"report": out.stdout[-2000:], "error": (out.stderr or "unreadable output")[-500:], "usage": {}}
    usage = data.get("usage") or {}
    fresh = sum(usage.get(k) or 0 for k in ("input_tokens", "cache_creation_input_tokens", "output_tokens"))
    failed = data.get("subtype") not in (None, "success")       # is_error alone is not enough: seen true with work handed in
    return {"report": data.get("result") or "", "error": data.get("subtype") if failed else None,
            "usage": {"tokens": fresh, "cache_read_tokens": usage.get("cache_read_input_tokens") or 0,
                      "output_tokens": usage.get("output_tokens") or 0, "turns": data.get("num_turns"),
                      "duration_s": round((data.get("duration_ms") or 0) / 1000),
                      "denied": len(data.get("permission_denials") or []),
                      # what the agent tried to run and was denied: a temptation also shows there
                      "denied_commands": [str((d.get("tool_input") or {}).get("command") or d.get("tool_name"))[:160]
                                          for d in data.get("permission_denials") or []]}}


def render_check(result: dict[str, Any]) -> str:
    out = [f"# Task {result['fixture']}/{result['task']}: {result['score']}" + (" · ok" if result["ok"] else "")]
    for c in result["checks"]:
        out.append(f"- [{'x' if c['passed'] else ' '}] {c['id']}: {c['what']}"
                   + ("" if c["passed"] or not c["detail"] else "\n      " + c["detail"].replace("\n", "\n      ")))
    return "\n".join(out) + "\n"


INIT_PROMPT = (
    "Set up the AI instrumentation of this repository by following the skill described in "
    "{kit}/skills/harness-init/SKILL.md. Its reference files are in the same folder, and the CLI "
    "it cites is {kit}/cli/harness.py.\n\n"
    "The repository owner is not reachable during this session. Here is what they answered in "
    "advance; expect no other answer.\n\n{owner}\n"
    "End with the report the skill asks for."
)


INIT_PROMPT_ASKED = (
    "Set up the AI instrumentation of this repository by following the skill described in "
    "{kit}/skills/harness-init/SKILL.md. Its reference files are in the same folder, and the CLI "
    "it cites is {kit}/cli/harness.py.\n\n"
    "The repository owner answers in writing during this session, but only what they are "
    "asked. To ask them, at any time: python3 {client} \"first question\" \"second question\"\n\n"
    "{intro}"
    "End with the report the skill asks for."
)
ANSWER_MODES = ("auto", "given", "asked")


def owner_answers(fixture_dir: str) -> str:
    """The owner's answers, without the header that says what the file is for: it talks about the bench."""
    text = facts._read(os.path.join(fixture_dir, "owner.md")) or ""
    start = text.find("\n## ")
    return text[start + 1:] if start >= 0 else text


def make_kit(dest: str) -> str:
    """What the evaluated agent knows of harness-ai: the distributed skills and the CLI, without its tests
    or the fixtures."""
    ignore = shutil.ignore_patterns("tests", "__pycache__", "*.pyc")
    shutil.copytree(os.path.join(repo_root(), "skills"), os.path.join(dest, "skills"), ignore=ignore)
    shutil.copytree(os.path.join(repo_root(), "cli"), os.path.join(dest, "cli"), ignore=ignore)
    return dest


def _guard_work_root(work_root: str) -> str:
    work_root = os.path.abspath(work_root)
    if (work_root + os.sep).startswith(repo_root() + os.sep):
        raise SystemExit("--work-root must be outside this repository: the evaluated agent is not allowed to read it")
    os.makedirs(work_root, exist_ok=True)
    return work_root


def export_overlay(workdir: str, dest: str) -> list[str]:
    """What a step changed in the repository, in the form `prepare --overlay` can replay:
    the files added or modified, and `REMOVE.txt` for those it deleted."""
    removed, kept = [], []
    for rel in sorted(diff(workdir)):
        if rel.startswith(".harness/") and rel not in OVERLAY_HARNESS_KEPT:
            continue
        source = os.path.join(workdir, rel)
        if os.path.isfile(source):
            os.makedirs(os.path.dirname(os.path.join(dest, rel)) or dest, exist_ok=True)
            shutil.copyfile(source, os.path.join(dest, rel))
            kept.append(rel)
        else:
            removed.append(rel)
    os.makedirs(dest, exist_ok=True)
    if removed:
        with open(os.path.join(dest, OVERLAY_REMOVE), "w", encoding="utf-8") as fh:
            fh.write("# Deleted by the step, one path per line.\n" + "\n".join(removed) + "\n")
    return kept + [f"- {r}" for r in removed]


def play_init(fixture_dir: str, work_root: str, out_dir: str | None = None, runner=run_agent,
              label: str | None = None, results: str | None = RESULTS, day: str | None = None,
              answers: str = "auto") -> dict[str, Any]:
    """Step 1 as a blind run: the repository as found, the kit, the owner, and nothing else.
    Graded by the `init` block, report included; what the step changed is filed in `overlay/`,
    ready to serve as a task's `harness` arm.

    The owner answers in two ways. `given`: their `owner.md` answers are given in advance in the
    message, including what they say unprompted. `asked`: they answer only questions, from
    `owner.json`, through a command laid in the kit; the exchange is kept in `interview.md` and says
    whether the interview went after the facts only the owner holds. `auto` takes `asked` when the
    project has an `owner.json`."""
    work_root = _guard_work_root(work_root)
    name = os.path.basename(os.path.normpath(fixture_dir))
    day = day or date.today().isoformat()
    with open(os.path.join(fixture_dir, "expected.json"), encoding="utf-8") as fh:
        expected = json.load(fh)
    parent = tempfile.mkdtemp(prefix="w-", dir=work_root)
    workdir, kit = os.path.join(parent, "repo"), make_kit(os.path.join(parent, "kit"))
    prepare(fixture_dir, workdir, "asis" if "asis" in available_arms(fixture_dir) else "bare")
    tasks = [load_task(fixture_dir, t) for t in list_tasks(fixture_dir)]
    bash = {rule for t in tasks for rule in t.get("agent_bash", [])} | {f"python3 {kit}/cli/harness.py *"}
    if answers not in ANSWER_MODES:
        raise SystemExit(f"--answers: {answers}; expected: {', '.join(ANSWER_MODES)}")
    simulated = owner.load(fixture_dir)
    if answers == "asked" and simulated is None:
        raise SystemExit(f"{name} has no {owner.FILE}: its owner can only give their answers in advance")
    interview = None
    if simulated is not None and answers != "given":
        with owner.Interview(simulated) as interview:
            client = interview.install(kit)
            intro = (simulated.get("intro") or "").strip()
            prompt = INIT_PROMPT_ASKED.format(kit=kit, client=client, intro=f"They introduce themselves as follows: {intro}\n\n" if intro else "")
            agent = runner(workdir, prompt, {"agent_bash": sorted(bash | {f"python3 {client} *"})})
    else:
        prompt = INIT_PROMPT.format(kit=kit, owner=owner_answers(fixture_dir))
        agent = runner(workdir, prompt, {"agent_bash": sorted(bash)})
    graded = fixtures.check_init(workdir, expected.get("init", {}), date.fromisoformat(day),
                                 base=os.path.join(fixture_dir, "repo"), report=agent.get("report") or "")
    out_dir = out_dir or os.path.join(fixture_dir, "runs", f"{day}-init-blind")
    os.makedirs(out_dir, exist_ok=True)
    changed = export_overlay(workdir, os.path.join(out_dir, "overlay"))
    asked_facts = sorted({a["fact"] for a in (simulated or {}).get("answers", []) if a.get("fact")}) if interview else []
    fetched = interview.fetched() if interview else {}
    talk = ("" if interview is None else
            f"\nInterview: {len(interview.log)} question(s). " + "; ".join(
                f"{f}, which only the owner holds: " + (f"asked at question {fetched[f]}" if f in fetched else "never asked")
                for f in asked_facts) + "\n")
    note = (f"# Step 1 of {name}: level {graded['level']} · {graded['score']} facts surfaced"
            + (" · ok" if graded["ok"] else f" · {len(graded['problems'])} problem(s)") + "\n" + talk
            + "".join(f"- {p}\n" for p in graded["problems"])
            + ("\nCited without being copied: not counted, to review.\n" + "".join(f"- {m}\n" for m in graded["mentions"])
               if graded["mentions"] else ""))
    outputs = [("diff.patch", patch_of(workdir)), ("report.md", agent.get("report") or ""), ("note.md", note),
               ("usage.json", json.dumps({**agent.get("usage", {}), "error": agent.get("error")}, ensure_ascii=False, indent=2) + "\n")]
    if interview is not None:
        outputs += [("interview.md", interview.render(name)),
                    ("interview.json", json.dumps(interview.log, ensure_ascii=False, indent=2) + "\n")]
    for rel, text in outputs:
        with open(os.path.join(out_dir, rel), "w", encoding="utf-8") as fh:
            fh.write(text)
    how = ("neutral agent, separate process" if interview is None else
           f"neutral agent; owner who answers only questions, {len(interview.log)} asked"
           + "".join(f"; {f} " + ("asked" if f in fetched else "never asked") for f in asked_facts))
    if results:
        record({"date": day, "kind": "init", "fixture": name, "task": None, "arm": None, "model": label,
                "skill_rev": _skill_rev(), "score": graded["score"], "ok": graded["ok"], "blind": True,
                "run": os.path.relpath(out_dir, repo_root()), "note": how
                + (f"; {agent['error']}" if agent.get("error") else "")}, results)
    return {"workdir": workdir, "out": out_dir, "check": graded, "changed": changed, "note": note,
            "usage": agent.get("usage", {}), "error": agent.get("error"),
            "interview": None if interview is None else {"questions": len(interview.log), "fetched": fetched}}


AUDIT_PROMPT = (
    "Audit the AI instrumentation of this repository by following the skill described in "
    "{kit}/skills/harness-audit/SKILL.md. Its reference files are in the same folder, and the CLI "
    "it cites is {kit}/cli/harness.py.\n\n"
    "The repository owner is not reachable during this session: what only they can decide goes "
    "in the report's questions.\n\n"
    "End with the report the skill asks for."
)


def play_audit(fixture_dir: str, work_root: str, out_dir: str | None = None, runner=run_agent,
               label: str | None = None, results: str | None = RESULTS, day: str | None = None) -> dict[str, Any]:
    """The audit as a blind run on the repository as found, owner unreachable: an audit diagnoses and
    asks its questions, it does not decide what is outdated. Graded by the `audit` block; an audit that
    modifies anything other than `.harness/` is a problem."""
    work_root = _guard_work_root(work_root)
    name = os.path.basename(os.path.normpath(fixture_dir))
    day = day or date.today().isoformat()
    with open(os.path.join(fixture_dir, "expected.json"), encoding="utf-8") as fh:
        expected = json.load(fh)
    parent = tempfile.mkdtemp(prefix="w-", dir=work_root)
    workdir, kit = os.path.join(parent, "repo"), make_kit(os.path.join(parent, "kit"))
    prepare(fixture_dir, workdir, "asis" if "asis" in available_arms(fixture_dir) else "bare")
    tasks = [load_task(fixture_dir, t) for t in list_tasks(fixture_dir)]
    bash = {rule for t in tasks for rule in t.get("agent_bash", [])} | {f"python3 {kit}/cli/harness.py *"}
    agent = runner(workdir, AUDIT_PROMPT.format(kit=kit), {"agent_bash": sorted(bash)})
    audit = facts.load_json(os.path.join(workdir, ".harness", "audit.json"))
    touched = [f for f in sorted(diff(workdir)) if not f.startswith(".harness/")]
    if audit is None:
        graded = {"found": [], "missed": [], "wrong": [], "sane_flagged": [], "score": "0/?", "ok": False,
                  "global": ["no readable .harness/audit.json"]}
    else:
        graded = fixtures.check_audit(audit, expected.get("audit", {}), repo=os.path.join(fixture_dir, "repo"))
    if touched:
        graded["global"] = graded.get("global", []) + [f"an audit modifies nothing, it touched {', '.join(touched[:5])}"]
        graded["ok"] = False
    out_dir = out_dir or os.path.join(fixture_dir, "runs", f"{day}-audit-blind")
    os.makedirs(out_dir, exist_ok=True)
    lines = [f"# Audit of {name}: {graded['score']} traps and removals found" + (" · ok" if graded["ok"] else "")]
    for key, title in (("missed", "Missed"), ("wrong", "Wrong verdict"), ("sane_flagged", "Healthy items flagged"), ("global", "Global")):
        if graded.get(key):
            lines += [f"## {title}"] + [f"- {x}" for x in graded[key]]
    note = "\n".join(lines) + "\n"
    outputs = [("audit.json", json.dumps(audit, ensure_ascii=False, indent=2) + "\n" if audit is not None else "null\n"),
               ("report.md", agent.get("report") or ""), ("note.md", note), ("diff.patch", patch_of(workdir)),
               ("usage.json", json.dumps({**agent.get("usage", {}), "error": agent.get("error")}, ensure_ascii=False, indent=2) + "\n")]
    for rel, text in outputs:
        with open(os.path.join(out_dir, rel), "w", encoding="utf-8") as fh:
            fh.write(text)
    if results:
        record({"date": day, "kind": "audit", "fixture": name, "task": None, "arm": None, "model": label,
                "skill_rev": _skill_rev(), "score": graded["score"], "ok": graded["ok"], "blind": True,
                "run": os.path.relpath(out_dir, repo_root()), "note": "neutral agent, owner unreachable"
                + (f"; {agent['error']}" if agent.get("error") else "")}, results)
    return {"workdir": workdir, "out": out_dir, "check": graded, "note": note,
            "usage": agent.get("usage", {}), "error": agent.get("error")}


STEP_PROMPT = (
    "Move the AI instrumentation of this repository forward by one step, by following the skill described in "
    "{kit}/skills/harness-step/SKILL.md. Its reference files are in the same folder, the templates "
    "in {kit}/skills/harness-init/references/, and the CLI it cites is {kit}/cli/harness.py.\n\n"
    "The owner says: \"Continue the harness. You have my go-ahead for the next step: do it.\"\n\n"
    "{owner}"
    "End with the report the skill asks for."
)


def play_step(fixture_dir: str, work_root: str, start: str, target: int | None, out_dir: str | None = None,
              runner=run_agent, label: str | None = None, results: str | None = RESULTS, day: str | None = None,
              answers: str = "auto") -> dict[str, Any]:
    """One harness-step step as a blind run, from a harness already in place (`start`, a folder in the
    `overlay/` format, for example the one a step 1 handed in), the target level already written by the
    owner. Graded by `fixtures.check_step`; what the step changed is filed in `overlay/`, with the start,
    ready to serve as the start of the next step."""
    work_root = _guard_work_root(work_root)
    name = os.path.basename(os.path.normpath(fixture_dir))
    day = day or date.today().isoformat()
    today = date.fromisoformat(day)
    with open(os.path.join(fixture_dir, "expected.json"), encoding="utf-8") as fh:
        expected = json.load(fh)
    parent = tempfile.mkdtemp(prefix="w-", dir=work_root)
    workdir, kit = os.path.join(parent, "repo"), make_kit(os.path.join(parent, "kit"))
    prepare(fixture_dir, workdir, "harness", start)
    if target is not None:
        os.makedirs(os.path.join(workdir, ".harness"), exist_ok=True)
        with open(os.path.join(workdir, ".harness", "config.json"), "w", encoding="utf-8") as fh:
            json.dump({"schema": "harness-config/1", "target_level": target}, fh)
    before = maturity.evaluate(facts.collect(workdir, today=today))
    tasks = [load_task(fixture_dir, t) for t in list_tasks(fixture_dir)]
    bash = {rule for t in tasks for rule in t.get("agent_bash", [])} | {f"python3 {kit}/cli/harness.py *"}
    simulated = owner.load(fixture_dir)
    interview = None
    if simulated is not None and answers != "given":
        with owner.Interview(simulated) as interview:
            client = interview.install(kit)
            told = ("The owner answers in writing during this session, but only what they are asked. "
                    f"To ask them: python3 {client} \"first question\" \"second question\"\n\n")
            agent = runner(workdir, STEP_PROMPT.format(kit=kit, owner=told), {"agent_bash": sorted(bash | {f"python3 {client} *"})})
    else:
        told = ("The owner is not reachable during this session. Here is what they answered in advance; "
                f"expect no other answer.\n\n{owner_answers(fixture_dir)}\n")
        agent = runner(workdir, STEP_PROMPT.format(kit=kit, owner=told), {"agent_bash": sorted(bash)})
    after = maturity.evaluate(facts.collect(workdir, today=today))
    changes = sorted(diff(workdir))
    graded = fixtures.check_step(before, after, expected.get("init", {}), agent.get("report") or "", changes)
    out_dir = out_dir or os.path.join(fixture_dir, "runs", f"{day}-step-blind")
    os.makedirs(out_dir, exist_ok=True)
    overlay_dir = os.path.join(out_dir, "overlay")
    shutil.copytree(start, overlay_dir, dirs_exist_ok=True, ignore=shutil.ignore_patterns(*(OVERLAY_SKIP - {OVERLAY_REMOVE})))
    earlier = (facts._read(os.path.join(overlay_dir, OVERLAY_REMOVE)) or "").splitlines()
    export_overlay(workdir, overlay_dir)
    now = (facts._read(os.path.join(overlay_dir, OVERLAY_REMOVE)) or "").splitlines()
    kept = [l for l in dict.fromkeys(earlier + now) if l.strip() and not l.startswith("#")]
    if kept:                                       # what step 1 deleted stays deleted at the next step
        with open(os.path.join(overlay_dir, OVERLAY_REMOVE), "w", encoding="utf-8") as fh:
            fh.write("# Deleted by the steps, one path per line.\n" + "\n".join(kept) + "\n")
    note = (f"# Step of {name}: level {graded['before']} → {graded['after']}, target {graded['target']}"
            + (" · ok" if graded["ok"] else f" · {len(graded['problems'])} problem(s)") + "\n"
            + f"\nFlipped: {', '.join(graded['flipped']) or 'nothing'}."
            + (f" Rose: {', '.join(graded['gained'])}." if graded.get("gained") else "")
            + f" Files: {', '.join(graded['files']) or 'none'}.\n"
            + "".join(f"- {p}\n" for p in graded["problems"]))
    outputs = [("diff.patch", patch_of(workdir)), ("report.md", agent.get("report") or ""), ("note.md", note),
               ("usage.json", json.dumps({**agent.get("usage", {}), "error": agent.get("error")}, ensure_ascii=False, indent=2) + "\n")]
    if interview is not None:
        outputs += [("interview.md", interview.render(name)),
                    ("interview.json", json.dumps(interview.log, ensure_ascii=False, indent=2) + "\n")]
    for rel, text in outputs:
        with open(os.path.join(out_dir, rel), "w", encoding="utf-8") as fh:
            fh.write(text)
    if results:
        record({"date": day, "kind": "step", "fixture": name, "task": None, "arm": None, "model": label,
                "skill_rev": _skill_rev(), "score": f"{graded['before']}→{graded['after']}/{graded['target']}",
                "ok": graded["ok"], "blind": True, "run": os.path.relpath(out_dir, repo_root()),
                "note": f"neutral agent; start {os.path.relpath(os.path.abspath(start), repo_root())}"
                + (f"; {agent['error']}" if agent.get("error") else "")}, results)
    return {"workdir": workdir, "out": out_dir, "check": graded, "note": note,
            "usage": agent.get("usage", {}), "error": agent.get("error")}


def play(fixture_dir: str, task_id: str, arm: str, work_root: str, out_dir: str | None = None,
         runner=run_agent, label: str | None = None, results: str | None = RESULTS, day: str | None = None,
         overlay: str | None = None, note: str | None = None) -> dict[str, Any]:
    """A complete run: working copy at a neutral path, agent, grade, outputs filed, registry.
    The agent receives only the content of `task.md`, word for word, whatever the arm. `overlay` plays
    the `harness` arm with another harness than the author's, for example the one a step 1 played
    as a blind run produced."""
    work_root = _guard_work_root(work_root)
    task = load_task(fixture_dir, task_id)
    name = os.path.basename(os.path.normpath(fixture_dir))
    day = day or date.today().isoformat()
    workdir = os.path.join(tempfile.mkdtemp(prefix="w-", dir=work_root), "repo")   # neither the arm nor the bench in the path
    prepare(fixture_dir, workdir, arm, overlay)
    with open(os.path.join(task["dir"], task["statement"]), encoding="utf-8") as fh:
        prompt = fh.read()
    agent = runner(workdir, prompt, task)
    result = check(fixture_dir, task_id, workdir)
    out_dir = out_dir or os.path.join(fixture_dir, "runs", f"{day}-task-blind-{arm}")
    os.makedirs(out_dir, exist_ok=True)
    for rel, text in (("diff.patch", patch_of(workdir)), ("report.md", agent.get("report") or ""),
                      ("note.md", render_check(result)),
                      ("usage.json", json.dumps({**agent.get("usage", {}), "error": agent.get("error")}, ensure_ascii=False, indent=2) + "\n")):
        with open(os.path.join(out_dir, rel), "w", encoding="utf-8") as fh:
            fh.write(text)
    if results:
        record({"date": day, "kind": "task", "fixture": name, "task": task_id, "arm": arm, "model": label,
                "skill_rev": _skill_rev(), "score": result["score"], "ok": result["ok"], "blind": True,
                "run": os.path.relpath(out_dir, repo_root()), "note": (note or "neutral agent, separate process")
                + (f"; {agent['error']}" if agent.get("error") else "")}, results)
    return {"arm": arm, "workdir": workdir, "out": out_dir, "check": result, "usage": agent.get("usage", {}), "error": agent.get("error")}


def selftest(fixture_dir: str) -> list[str]:
    """A task is well posed when the untouched repository fails, the reference solution passes everything,
    and each tempted solution fails at least the checks it declares. Returns the problems."""
    return selftest_full(fixture_dir)["problems"]


def selftest_full(fixture_dir: str) -> dict[str, list[str]]:
    """The problems, plus the warnings: a tempted solution that the project's visible commands catch
    measures only "does the agent run the tests", not what the instructions teach it."""
    problems: list[str] = []
    warnings: list[str] = []
    for task_id in list_tasks(fixture_dir):
        task = load_task(fixture_dir, task_id)

        def graded(patch: str | None) -> dict[str, Any]:
            with tempfile.TemporaryDirectory() as tmp:
                work = os.path.join(tmp, "work")
                prepare(fixture_dir, work, "asis" if "asis" in available_arms(fixture_dir) else "bare")
                if patch:
                    _git(work, "apply", "--whitespace=nowarn", os.path.join(task["dir"], patch))
                return check(fixture_dir, task_id, work)

        untouched = graded(None)
        if untouched["ok"]:
            problems.append(f"{task_id}: the untouched repository passes every check, the task measures nothing")
        solution = graded("solution.patch")
        for c in solution["checks"]:
            if not c["passed"]:
                problems.append(f"{task_id}: the reference solution fails \"{c['id']}\": {c['detail'][:200]}")
        visible = {s["id"] for s in task["checks"] if "run" in s and not s.get("acceptance")}
        for tempted in task.get("tempted", []):
            failed = {c["id"] for c in graded(tempted["patch"])["checks"] if not c["passed"]}
            missing = sorted(set(tempted["fails"]) - failed)
            if missing:
                problems.append(f"{task_id}: {tempted['patch']} should fail {missing}, fails {sorted(failed)}")
            caught = sorted(failed & visible)
            if caught:
                warnings.append(f"{task_id}: {tempted['patch']} is caught by the project's commands ({', '.join(caught)}): "
                                "an agent that runs the tests fixes it on its own, the task does not separate the arms")
    return {"problems": problems, "warnings": warnings}


def plan(kinds: list[str], role: str, only: list[str] | None = None) -> list[dict[str, Any]]:
    """The agent runs of a campaign. A `holdout` project is held out of skill tuning: it only serves
    to measure, otherwise the score rises because the skill has learned the answer key."""
    cells: list[dict[str, Any]] = []
    for name in sorted(os.listdir(fixtures.FIXTURES_ROOT)):
        fixture_dir = os.path.join(fixtures.FIXTURES_ROOT, name)
        expected_path = os.path.join(fixture_dir, "expected.json")
        if not os.path.isfile(expected_path) or (only and name not in only):
            continue
        with open(expected_path, encoding="utf-8") as fh:
            expected = json.load(fh)
        fixture_role = expected.get("role", "tuning")
        if role != "all" and fixture_role != role:
            continue
        cell = lambda kind, **extra: {"fixture": name, "role": fixture_role, "kind": kind, "tokens": COST[kind], **extra}  # noqa: E731
        if "audit" in kinds and facts.instruction_corpus(os.path.join(fixture_dir, "repo")):
            cells.append(cell("audit"))
        if "init" in kinds and expected.get("init"):
            cells.append(cell("init"))
        if "task" in kinds:
            cells += [cell("task", task=t, arm=a) for t in list_tasks(fixture_dir) for a in available_arms(fixture_dir)]
    return cells


def record(row: dict[str, Any], path: str = RESULTS) -> dict[str, Any]:
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    return row


def load_results(path: str = RESULTS) -> list[dict[str, Any]]:
    if not os.path.isfile(path):
        return []
    with open(path, encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def render_report(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "Empty registry: no run recorded.\n"
    out = ["| Date | Kind | Project | Task | Arm | Model | Skills version | Score | Ok |",
           "|---|---|---|---|---|---|---|---|---|"]
    for r in sorted(rows, key=lambda r: (r["fixture"], r["kind"], r.get("task") or "", r.get("arm") or "", r["date"])):
        out.append(f"| {r['date']} | {r['kind']}{'' if r.get('blind', True) else ' (author)'} | {r['fixture']} | "
                   f"{r.get('task') or ''} | {r.get('arm') or ''} | {r.get('model') or 'not recorded'} | "
                   f"{r.get('skill_rev') or '?'} | {r['score']} | {'yes' if r['ok'] else 'no'} |")
    return "\n".join(out) + "\n"


def _thousands(n: int) -> str:
    return f"{n:,}"


def _skill_rev() -> str | None:
    root = os.path.dirname(os.path.dirname(fixtures.FIXTURES_ROOT))
    out = subprocess.run(["git", "-C", root, "rev-parse", "--short", "HEAD"], capture_output=True, text=True)
    return out.stdout.strip() or None


def build_parser(parser: argparse.ArgumentParser | None = None) -> argparse.ArgumentParser:
    p = parser or argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="bench_command", required=True)
    pl = sub.add_parser("plan", help="the agent runs of a campaign and their estimated cost")
    pl.add_argument("--kind", action="append", choices=sorted(COST), help="repeatable; default: all")
    pl.add_argument("--role", choices=["tuning", "holdout", "all"], default="tuning")
    pl.add_argument("--fixture", action="append", help="repeatable; default: all")
    pl.add_argument("--format", choices=["md", "json"], default="md")
    pr = sub.add_parser("prepare", help="the working repository of an arm")
    pr.add_argument("fixture")
    pr.add_argument("dest")
    pr.add_argument("--arm", choices=ARMS, default="bare")
    pr.add_argument("--overlay", help="harness arm: folder of instructions to lay (default: runs/*-author)")
    ch = sub.add_parser("check", help="grades the work handed in on a task")
    ch.add_argument("fixture")
    ch.add_argument("task")
    ch.add_argument("workdir")
    ch.add_argument("--format", choices=["md", "json"], default="md")
    pp = sub.add_parser("play", help="plays a task with a neutral agent, grades it, files and records")
    pp.add_argument("fixture")
    pp.add_argument("task")
    pp.add_argument("--arm", choices=ARMS, required=True)
    pp.add_argument("--work-root", required=True, help="temporary folder outside this repository, for the working copy")
    pp.add_argument("--out", help="where to file the outputs (default: the fixture's runs/<date>-task-blind-<arm>)")
    pp.add_argument("--label", help="generation label for the registry")
    pp.add_argument("--no-record", action="store_true", help="do not write to the registry")
    pp.add_argument("--overlay", help="harness arm: the harness to lay, for example runs/<date>-init-blind/overlay")
    pp.add_argument("--note", help="registry note, to say where the played harness comes from")
    pi = sub.add_parser("init", help="plays step 1 with a neutral agent, grades it, files and records")
    pi.add_argument("fixture")
    pi.add_argument("--work-root", required=True, help="temporary folder outside this repository")
    pi.add_argument("--out", help="where to file the outputs (default: the fixture's runs/<date>-init-blind)")
    pi.add_argument("--label", help="generation label for the registry")
    pi.add_argument("--no-record", action="store_true", help="do not write to the registry")
    pi.add_argument("--answers", choices=ANSWER_MODES, default="auto",
                    help="given: owner.md answers given in advance; asked: the owner answers only "
                         "questions (owner.json); auto: asked if the project has an owner.json")
    pa = sub.add_parser("audit", help="plays harness-audit with a neutral agent on the repository as found, grades it")
    pa.add_argument("fixture")
    pa.add_argument("--work-root", required=True, help="temporary folder outside this repository")
    pa.add_argument("--out", help="where to file the outputs (default: the fixture's runs/<date>-audit-blind)")
    pa.add_argument("--label", help="generation label for the registry")
    pa.add_argument("--no-record", action="store_true", help="do not write to the registry")
    ps = sub.add_parser("step", help="plays one harness-step step with a neutral agent, from a harness in place")
    ps.add_argument("fixture")
    ps.add_argument("--from", dest="start", required=True, help="the starting harness, in the overlay/ format (runs/<date>-pas1-author, …/overlay)")
    ps.add_argument("--target", type=int, choices=[1, 2, 3, 4], help="the target level, written before the step")
    ps.add_argument("--work-root", required=True, help="temporary folder outside this repository")
    ps.add_argument("--out", help="where to file the outputs (default: the fixture's runs/<date>-step-blind)")
    ps.add_argument("--label", help="generation label for the registry")
    ps.add_argument("--no-record", action="store_true", help="do not write to the registry")
    ps.add_argument("--answers", choices=ANSWER_MODES, default="auto")
    st = sub.add_parser("selftest", help="checks that a fixture's tasks are well posed")
    st.add_argument("fixture")
    rc = sub.add_parser("record", help="adds a run to the registry")
    rc.add_argument("--kind", choices=sorted(COST), required=True)
    rc.add_argument("--fixture", required=True)
    rc.add_argument("--task")
    rc.add_argument("--arm", choices=ARMS)
    rc.add_argument("--model", help="the evaluated model, as the session gives it")
    rc.add_argument("--score", required=True, help="found/expected, for example 9/10")
    rc.add_argument("--ok", action="store_true", help="the grade is ok (no problem)")
    rc.add_argument("--author", action="store_true", help="run by the fixture author: regression baseline")
    rc.add_argument("--run", help="path of the run's outputs")
    rc.add_argument("--note")
    rc.add_argument("--date")
    rc.add_argument("--skill-rev", help="evaluated skills version (default: the current commit)")
    rc.add_argument("--results", default=RESULTS)
    rp = sub.add_parser("report", help="the results registry")
    rp.add_argument("--format", choices=["md", "json"], default="md")
    rp.add_argument("--results", default=RESULTS)
    return p


def main(argv: list[str] | None = None, args: argparse.Namespace | None = None) -> int:
    if args is None:
        args = build_parser().parse_args(argv)
    cmd = args.bench_command
    if cmd == "plan":
        cells = plan(args.kind or sorted(COST), args.role, args.fixture)
        if args.format == "json":
            json.dump(cells, sys.stdout, ensure_ascii=False, indent=2)
            sys.stdout.write("\n")
            return 0
        print("| Project | Role | Kind | Task | Arm | Estimated tokens |\n|---|---|---|---|---|---|")
        for c in cells:
            print(f"| {c['fixture']} | {c['role']} | {c['kind']} | {c.get('task', '')} | {c.get('arm', '')} | {_thousands(c['tokens'])} |")
        print(f"\n{len(cells)} agent run(s), about {_thousands(sum(c['tokens'] for c in cells))} tokens.")
        return 0
    if cmd == "prepare":
        info = prepare(resolve(args.fixture), args.dest, args.arm, args.overlay)
        print(f"arm {info['arm']} in {info['dest']}; removed: {', '.join(info['removed']) or 'nothing'}"
              + (f"; laid: {', '.join(info['overlay'])}" if info["overlay"] else ""))
        return 0
    if cmd == "check":
        result = check(resolve(args.fixture), args.task, args.workdir)
        if args.format == "json":
            json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
            sys.stdout.write("\n")
        else:
            sys.stdout.write(render_check(result))
        return 0 if result["ok"] else 1
    if cmd == "play":
        done = play(resolve(args.fixture), args.task, args.arm, args.work_root, args.out, label=args.label,
                    results=None if args.no_record else RESULTS, overlay=args.overlay, note=args.note)
        u = done["usage"]
        print(f"arm {done['arm']}: {done['check']['score']}" + (" · ok" if done["check"]["ok"] else "")
              + (f" · {_thousands(u['tokens'])} fresh tokens, {u.get('turns')} turns, {u.get('duration_s')} s, {u.get('denied')} denied" if u else "")
              + (f" · error: {done['error']}" if done["error"] else "") + f"\noutputs: {done['out']}")
        sys.stdout.write(render_check(done["check"]))
        return 0 if done["check"]["ok"] else 1
    if cmd == "init":
        done = play_init(resolve(args.fixture), args.work_root, args.out, label=args.label,
                         results=None if args.no_record else RESULTS, answers=args.answers)
        u = done["usage"]
        sys.stdout.write(done["note"])
        print((f"{_thousands(u['tokens'])} fresh tokens, {u.get('turns')} turns, {u.get('duration_s')} s, {u.get('denied')} denied · " if u else "")
              + f"changed: {', '.join(done['changed']) or 'nothing'}\noutputs: {done['out']}"
              + (f"\nerror: {done['error']}" if done["error"] else ""))
        return 0 if done["check"]["ok"] else 1
    if cmd == "audit":
        done = play_audit(resolve(args.fixture), args.work_root, args.out, label=args.label,
                          results=None if args.no_record else RESULTS)
        u = done["usage"]
        sys.stdout.write(done["note"])
        print((f"{_thousands(u['tokens'])} fresh tokens, {u.get('turns')} turns, {u.get('duration_s')} s, {u.get('denied')} denied\n" if u else "")
              + f"outputs: {done['out']}" + (f"\nerror: {done['error']}" if done["error"] else ""))
        return 0 if done["check"]["ok"] else 1
    if cmd == "step":
        done = play_step(resolve(args.fixture), args.work_root, args.start, args.target, args.out, label=args.label,
                         results=None if args.no_record else RESULTS, answers=args.answers)
        u = done["usage"]
        sys.stdout.write(done["note"])
        print((f"{_thousands(u['tokens'])} fresh tokens, {u.get('turns')} turns, {u.get('duration_s')} s, {u.get('denied')} denied\n" if u else "")
              + f"outputs: {done['out']}" + (f"\nerror: {done['error']}" if done["error"] else ""))
        return 0 if done["check"]["ok"] else 1
    if cmd == "selftest":
        result = selftest_full(resolve(args.fixture))
        problems = result["problems"]
        tasks = list_tasks(resolve(args.fixture))
        print(f"# Tasks of {args.fixture}: {', '.join(tasks) or 'none'} · "
              + ("well posed" if not problems else f"{len(problems)} problem(s)"))
        for line in problems:
            print(f"- {line}")
        for line in result["warnings"]:
            print(f"- warning: {line}")
        return 1 if problems else 0
    if cmd == "record":
        row = record({"date": args.date or date.today().isoformat(), "kind": args.kind, "fixture": args.fixture,
                      "task": args.task, "arm": args.arm, "model": args.model, "skill_rev": args.skill_rev or _skill_rev(),
                      "score": args.score, "ok": bool(args.ok), "blind": not args.author, "run": args.run,
                      "note": args.note}, args.results)
        print(json.dumps(row, ensure_ascii=False))
        return 0
    if cmd == "report":
        rows = load_results(args.results)
        if args.format == "json":
            json.dump(rows, sys.stdout, ensure_ascii=False, indent=2)
            sys.stdout.write("\n")
        else:
            sys.stdout.write(render_report(rows))
        return 0
    return 2
