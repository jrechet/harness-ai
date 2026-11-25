"""Collects the measurable facts of a repository: instruction files, rules,
feedback loop, contracts, guardrails, and the latest audit and harvest JSON.
No judgement here: numbers, booleans, paths.

Convention: the skills' outputs live in `<repo>/.harness/`:
`audit.json` (machine block of harness-audit), `harvest.json` (evidence from
harness-harvest), `state.json` (written by `harness status`).

The instruction files are written by a team, in French or in English: every
heading and marker below is read in both languages."""
from __future__ import annotations

import json
import os
import re
from datetime import date, datetime
from typing import Any

from . import shape
from .github import iter_rules, parse_rules

INSTRUCTION_FILES = ["AGENTS.md", "CLAUDE.md", ".github/copilot-instructions.md"]
CURSOR_RULES_DIR = ".cursor/rules"
CONTRACT_DIRS = [".claude/skills", ".agents/skills"]
WORKFLOW_DIR = ".github/workflows"

# Files whose presence signals an L3 guardrail (lint, architecture, hooks, formats).
GUARDRAIL_MARKERS = {
    "eslint": [".eslintrc", ".eslintrc.js", ".eslintrc.cjs", ".eslintrc.json", "eslint.config.js", "eslint.config.mjs"],
    "stylelint": [".stylelintrc", ".stylelintrc.json", "stylelint.config.js"],
    "prettier": [".prettierrc", "prettier.config.js"],
    "ruff": ["ruff.toml", ".ruff.toml"],
    "golangci-lint": [".golangci.yml", ".golangci.yaml", ".golangci.toml"],
    "checkstyle": ["config/checkstyle/checkstyle.xml", "checkstyle.xml"],
    "spotless": [],
    "pre-commit": [".pre-commit-config.yaml"],
    "husky": [".husky"],
    "editorconfig": [".editorconfig"],
    "pr-template": [".github/pull_request_template.md", ".github/PULL_REQUEST_TEMPLATE.md"],
    "codeowners": [".github/CODEOWNERS", "CODEOWNERS"],
}
GUARDRAIL_CONTENT_HINTS = {          # patterns looked for in the build files
    "archunit": r"archunit",
    "spotless": r"spotless",
    "checkstyle": r"checkstyle",
    "errorprone": r"errorprone",
}
BUILD_FILES = ["build.gradle", "build.gradle.kts", "pom.xml", "package.json", "pyproject.toml"]

# "Mode : délégation | assistance" (French) or "Mode: delegation | assistance".
MODE_RE = re.compile(r"^\s*(?:[-*]\s*)?Mode\s*:\s*\**\s*(d[ée]l[ée]gation|assistance)\b", re.I | re.M)
MARKER_RE = re.compile(r"<!--\s*harvest:\s*last=(\d{4}-\d{2}-\d{2})(?:\s+ref=(\S+))?\s*-->")
GUARDED_RE = re.compile(r"v[ée]rifi[ée]e?\s+par\s*:|guarded\s+by\s*:|enforced\s+by\s*:", re.I)
UNGUARDED_RE = re.compile(r"\(non\s+v[ée]rifi[ée]e?\)|\(unverified\)", re.I)
WHY_RE = re.compile(r"pourquoi\s*:|why\s*:|incident|issue\s*#?\d+|#\d+|https?://", re.I)
# The "Git Workflow" of a generated file is not a working process: "workflow" alone, or qualified.
PROCESS_HEADING_RE = re.compile(r"processus de travail|working process|working agreements?|^(?:agent |working )?workflow$", re.I)
# Date of a rule: `[2026-11]` or `[2026-11-10]` at the end of the bullet. Without it, "no incident for
# six months" cannot be computed and nothing says for which generation of models the rule was written.
RULE_DATE_RE = re.compile(r"\[(\d{4}-\d{2}(?:-\d{2})?)\]")
DELEGATED_HEADING_RE = re.compile(r"t[âa]ches d[ée]l[ée]gu[ée]es|delegated tasks", re.I)
# A task contract says what it is (front matter with `name` and `description`) and when the task is done.
# Issue #91 asks for both. Only the front matter is required today: the contracts of the java-back,
# node-front and python-cli sample projects have no done criterion and their expected.json expects
# L4.contracts to pass, so the criterion is measured (`done_criterion`) and required only once the owner
# has settled those three. That day, set REQUIRE_DONE_CRITERION to True: the rule and its tests are ready.
REQUIRE_DONE_CRITERION = False
FRONT_MATTER_RE = re.compile(r"\A---[ \t]*\r?\n(.*?)\r?\n---[ \t]*(?:\r?\n|\Z)", re.S)
# "## Done when", "**Done when:** …", "Definition of done", "Fini quand", "Terminé quand".
DONE_CRITERION_RE = re.compile(r"\bdone when\b|\bdefinition of done\b|\bdone criteri(?:on|a)\b|\bfinished when\b"
                               r"|\bfinie? quand\b|\btermin[ée]e? quand\b", re.I)
# Test data sometimes carries fake instruction files: they are not the repository's own.
SKIP_DIRS = {".git", "node_modules", "vendor", "dist", "build", ".harness", "runs", "__pycache__", ".venv",
             "fixtures", "testdata"}
INSTRUCTION_NAMES = {"AGENTS.md", "CLAUDE.md", "SKILL.md", "copilot-instructions.md"}
RULE_CONVENTION_RE = re.compile(r"`rule:`|\brule:\s", re.I)
# "Maintenance de ce fichier", "Maintenance", "Maintaining this file".
MAINTENANCE_HEADING_RE = re.compile(r"maintenance|maintaining", re.I)
# "Interdits", "Forbidden", "Never do".
FORBIDDEN_HEADING_RE = re.compile(r"interdits?|never do|forbidden", re.I)


def _read(path: str) -> str | None:
    try:
        with open(path, encoding="utf-8") as fh:
            return fh.read()
    except OSError:
        return None


def _exists(repo: str, rel: str) -> bool:
    return os.path.exists(os.path.join(repo, rel))


def resolve_includes(repo: str, text: str, depth: int = 0) -> str:
    """Replaces the `@path` lines (Claude Code include) with the file they point to."""
    if depth > 3:
        return text
    out = []
    for line in text.splitlines():
        m = re.match(r"^@([\w./-]+)\s*$", line.strip())
        if m:
            inc = _read(os.path.join(repo, m.group(1)))
            out.append(resolve_includes(repo, inc, depth + 1) if inc is not None else line)
        else:
            out.append(line)
    return "\n".join(out)


def _headings(text: str) -> list[str]:
    return [re.sub(r"^#{1,6}\s+", "", l).strip() for l in text.splitlines() if re.match(r"^#{1,6}\s", l)]


def instruction_facts(repo: str) -> dict[str, Any]:
    files = {}
    for rel in INSTRUCTION_FILES:
        text = _read(os.path.join(repo, rel))
        if text is None:
            files[rel] = {"exists": False}
            continue
        loaded = resolve_includes(repo, text)
        stripped = text.strip()
        files[rel] = {
            "exists": True,
            "lines": len(text.splitlines()),
            "loaded_lines": len(loaded.splitlines()),
            "is_stub": bool(re.fullmatch(r"@AGENTS\.md", stripped))
            or (len(stripped.splitlines()) <= 3 and "AGENTS.md" in stripped),
        }
    cursor = os.path.join(repo, CURSOR_RULES_DIR)
    files[CURSOR_RULES_DIR] = {"exists": os.path.isdir(cursor),
                               "files": sorted(os.listdir(cursor)) if os.path.isdir(cursor) else []}

    # The "source" file: AGENTS.md, otherwise CLAUDE.md if it is not a stub.
    source_rel = None
    if files["AGENTS.md"]["exists"]:
        source_rel = "AGENTS.md"
    elif files["CLAUDE.md"]["exists"] and not files["CLAUDE.md"].get("is_stub"):
        source_rel = "CLAUDE.md"
    source: dict[str, Any] = {"path": source_rel}
    if source_rel:
        text = _read(os.path.join(repo, source_rel)) or ""
        rules = parse_rules(text)
        mode = MODE_RE.search(text)
        marker = MARKER_RE.search(text)
        headings = _headings(text)
        source.update({
            "mode": mode.group(1).lower().replace("é", "e").replace("è", "e") if mode else None,
            "lines": len(text.splitlines()),
            "rules_total": len(rules),
            "rules_guarded": sum(1 for r in rules if GUARDED_RE.search(r)),
            "rules_unguarded_marked": sum(1 for r in rules if UNGUARDED_RE.search(r)),
            "rules_justified": sum(1 for r in rules if WHY_RE.search(r)),
            "rules_dated": sum(1 for r in rules if rule_date(r)),
            "oldest_rule_date": min((d for d in map(rule_date, rules) if d), default=None),
            "has_maintenance_section": any(MAINTENANCE_HEADING_RE.search(h) for h in headings),
            "has_process_section": any(PROCESS_HEADING_RE.search(h) for h in headings),
            "has_forbidden_section": any(FORBIDDEN_HEADING_RE.search(h) for h in headings),
            "mentions_rule_convention": bool(RULE_CONVENTION_RE.search(text)),
            "harvest_marker": {"date": marker.group(1), "ref": marker.group(2)} if marker else None,
        })
    return {"files": files, "source": source}


def rule_date(rule: str) -> str | None:
    """The date carried by a rule (`[YYYY-MM]` or `[YYYY-MM-DD]`), the last one if several."""
    found = RULE_DATE_RE.findall(rule)
    return found[-1] if found else None


def instruction_corpus(repo: str, names: set[str] | None = None, resolve: bool = True) -> dict[str, str]:
    """The instruction text of a repository, by relative path: AGENTS.md and CLAUDE.md at any level,
    contracts (SKILL.md), Copilot stub, Cursor rules; `@includes` resolved unless `resolve=False`."""
    names = names or INSTRUCTION_NAMES
    corpus: dict[str, str] = {}
    for root, dirs, files in os.walk(repo):
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS)
        rel_root = os.path.relpath(root, repo).replace(os.sep, "/")
        for name in sorted(files):
            if name in names or (names is INSTRUCTION_NAMES and rel_root.startswith(".cursor/rules")):
                text = _read(os.path.join(root, name))
                if text is None:
                    continue
                rel = name if rel_root == "." else f"{rel_root}/{name}"
                corpus[rel] = resolve_includes(root, text) if resolve else text
    return corpus


def config_facts(hdir: str) -> dict[str, Any]:
    """`.harness/config.json`: what the owner decided, starting with the target level."""
    config = load_json(os.path.join(hdir, "config.json"))
    config = config if isinstance(config, dict) else {}       # a file of another shape decides nothing
    target = config.get("target_level")
    return {"target_level": target if isinstance(target, int) and 1 <= target <= 4 else None,
            "ignored_checks": ignored_checks(config)}


def ignored_checks(config: dict[str, Any]) -> dict[str, dict[str, str]]:
    """The checks the owner set aside, each with its reason: `{"L1.forbidden": {"reason", "date"}}`.
    An entry without a reason is not a decision: it is left aside, like a block of another shape."""
    block = config.get("ignored_checks")
    if not isinstance(block, dict):
        return {}
    return {str(cid): {"reason": entry["reason"].strip(), "date": str(entry.get("date") or "")}
            for cid, entry in block.items()
            if isinstance(entry, dict) and isinstance(entry.get("reason"), str) and entry["reason"].strip()}


def _repo_files(repo: str, limit: int = 20000) -> list[str]:
    found: list[str] = []
    for root, dirs, files in os.walk(repo):
        dirs[:] = [d for d in dirs if d not in {".git", "node_modules", "__pycache__", ".venv"}]
        rel_root = os.path.relpath(root, repo).replace(os.sep, "/")
        for name in files:
            found.append(name if rel_root == "." else f"{rel_root}/{name}")
            if len(found) >= limit:
                return found
    return found


def workflow_jobs(repo: str) -> set[str] | None:
    """The job ids of the repository's GitHub workflows; None if there is no workflow."""
    wf_dir = os.path.join(repo, WORKFLOW_DIR)
    files = sorted(f for f in os.listdir(wf_dir) if f.endswith((".yml", ".yaml"))) if os.path.isdir(wf_dir) else []
    if not files:
        return None
    jobs: set[str] = set()
    for name in files:
        indent = None
        in_jobs = False
        for line in (_read(os.path.join(wf_dir, name)) or "").splitlines():
            if re.match(r"^jobs:\s*(#.*)?$", line):
                in_jobs, indent = True, None
                continue
            if in_jobs and re.match(r"^\S", line):
                in_jobs = False
            key = re.match(r"^(\s+)([\w.-]+):\s*(#.*)?$", line)
            if in_jobs and key:
                indent = indent or len(key.group(1))
                if len(key.group(1)) == indent:
                    jobs.add(key.group(2))
    return jobs


def dangling_facts(repo: str, source_text: str | None) -> list[dict[str, Any]]:
    """References of the source file that lead nowhere: a contract cited under "Delegated tasks"
    ("Tâches déléguées") without a SKILL.md, a path cited after "Enforced by" ("Vérifiée par") that
    does not exist, a CI job cited that no workflow defines (the guardrail is gone, the sentence stayed).
    A linter rule name (`eslint/no-raw-fetch`) is not a path: only a token with an extension, or a path
    whose first segment exists at the root, is judged."""
    if not source_text:
        return []
    dangling: list[dict[str, Any]] = []
    in_delegated = False
    for number, line in enumerate(source_text.splitlines(), 1):
        if re.match(r"^#{1,6}\s", line):
            in_delegated = bool(DELEGATED_HEADING_RE.search(line))
            continue
        if in_delegated and re.match(r"^\s*[-*]\s+", line):
            name = re.search(r"`([\w.-]+)`", line)
            if name and not any(_exists(repo, f"{d}/{name.group(1)}/SKILL.md") for d in CONTRACT_DIRS):
                dangling.append({"kind": "contract", "ref": name.group(1), "line": number})
    files: list[str] | None = None
    jobs = workflow_jobs(repo)
    for number, rule in iter_rules(source_text):
        if not GUARDED_RE.search(rule):
            continue
        claim = GUARDED_RE.split(rule, maxsplit=1)[-1]
        for job in re.findall(r"\bjobs?\s+`([\w.-]+)`", claim, flags=re.I):
            if jobs is not None and job not in jobs:
                dangling.append({"kind": "job", "ref": job, "line": number})
        for token in cited_paths(repo, claim):
            if _exists(repo, token):
                continue
            if files is None:
                files = _repo_files(repo)
            if not cited_path_exists(repo, token, files):
                dangling.append({"kind": "guard", "ref": token, "line": number})
    return dangling


def _clean_token(token: str) -> str:
    """A cited token without the punctuation of its sentence and without a leading "./" (the dot of a
    dotfile such as `.golangci.yml` stays)."""
    token = token.strip("()[]<>\"'").rstrip(".,;:")
    return token[2:] if token.startswith("./") else token


def _is_path_like(repo: str, token: str) -> bool:
    """A token with an extension, or a path whose first segment exists at the root."""
    has_ext = bool(re.search(r"\.\w{1,5}$", token))
    rooted = "/" in token and _exists(repo, token.split("/", 1)[0])
    return has_ext or rooted


def _is_bare_path_like(repo: str, token: str) -> bool:
    """Outside backticks a token sits in prose: a URL, a version (`3.12`, `v9.x`), an abbreviation
    (`e.g.`) or a product name (`Node.js`, `ASP.NET`) is not a path. Only a token with a directory or
    the leading dot of a dotfile is judged, and its extension must hold a letter; a bare file name is
    judged when it is written in backticks."""
    if "://" in token or not _is_path_like(repo, token):
        return False
    _, dot, ext = token.rpartition("/")[-1].rpartition(".")
    if dot and not re.search(r"[A-Za-z]", ext):
        return False
    return "/" in token or token.startswith(".")


def cited_paths(repo: str, claim: str) -> list[str]:
    """The paths a claim ("Enforced by: …") cites: every back-ticked token that looks like a path, and
    the first path-like token written without backticks. Words that are not paths ("Stop hook",
    "branch protection", a linter rule name) are not returned."""
    ticked = [_clean_token(t) for t in re.findall(r"`([^`\s]+)`", claim)]
    paths = [t for t in ticked if _is_path_like(repo, t)]
    bare = (_clean_token(t) for t in re.sub(r"`[^`]*`", " ", claim).split())
    first = next((t for t in bare if _is_bare_path_like(repo, t)), None)
    return paths + [first] if first and first not in paths else paths


def cited_path_exists(repo: str, token: str, files: list[str] | None = None) -> bool:
    """A cited path exists if it is there as is, or if a file of the repository has this name or this suffix."""
    if _exists(repo, token):
        return True
    files = _repo_files(repo) if files is None else files
    return any(f == token or f.endswith("/" + token) or f.startswith(token.rstrip("/") + "/") for f in files)


def _front_matter_value(block: str, key: str) -> bool:
    """True if the front matter gives `key` a value, on its line or as an indented block (`>`, `|`)."""
    lines = block.splitlines()
    for number, line in enumerate(lines):
        found = re.match(rf"^{re.escape(key)}:[ \t]*(.*)$", line)
        if not found:
            continue
        value = found.group(1).strip()
        if not value or re.fullmatch(r"[>|][+-]?\d?", value):
            following = lines[number + 1:number + 2]
            return bool(following and re.match(r"^[ \t]+\S", following[0]))
        return bool(value.strip("'\""))
    return False


def contract_missing(text: str | None, require_done: bool | None = None) -> list[str]:
    """What a task contract lacks to be one: a 0-byte SKILL.md cited by the source file is not a contract.
    `require_done` also asks for a done criterion; left out, REQUIRE_DONE_CRITERION decides."""
    text = text or ""
    front = FRONT_MATTER_RE.match(text)
    block = front.group(1) if front else ""
    missing = [f"front matter {key}" for key in ("name", "description") if not _front_matter_value(block, key)]
    if (REQUIRE_DONE_CRITERION if require_done is None else require_done) and not contract_done_criterion(text):
        missing.append("done criterion")
    return missing


def contract_done_criterion(text: str | None) -> bool:
    """True if the body of the contract, front matter aside, says when the task is done."""
    text = text or ""
    front = FRONT_MATTER_RE.match(text)
    return bool(DONE_CRITERION_RE.search(text[front.end():] if front else text))


def contract_facts(repo: str, source_text: str | None) -> dict[str, Any]:
    contracts = []
    for d in CONTRACT_DIRS:
        base = os.path.join(repo, d)
        if not os.path.isdir(base):
            continue
        for name in sorted(os.listdir(base)):
            if os.path.isfile(os.path.join(base, name, "SKILL.md")):
                text = _read(os.path.join(base, name, "SKILL.md"))
                missing = contract_missing(text)
                contracts.append({"name": name, "path": f"{d}/{name}/SKILL.md",
                                  "referenced": bool(source_text and name in source_text),
                                  "complete": not missing, "missing": missing,
                                  "done_criterion": contract_done_criterion(text)})
    return {"count": len(contracts), "items": contracts}


def guardrail_facts(repo: str) -> dict[str, Any]:
    found: dict[str, list[str]] = {}
    for tool, rels in GUARDRAIL_MARKERS.items():
        hits = [r for r in rels if _exists(repo, r)]
        if hits:
            found[tool] = hits
    build_text = "\n".join((_read(os.path.join(repo, b)) or "") for b in BUILD_FILES).lower()
    for tool, pattern in GUARDRAIL_CONTENT_HINTS.items():
        if re.search(pattern, build_text):
            found.setdefault(tool, []).append("build file")
    wf_dir = os.path.join(repo, WORKFLOW_DIR)
    workflows = sorted(f for f in os.listdir(wf_dir) if f.endswith((".yml", ".yaml"))) if os.path.isdir(wf_dir) else []
    gitlab_ci = _exists(repo, ".gitlab-ci.yml")
    return {"tools": found, "workflows": workflows, "has_ci": bool(workflows) or gitlab_ci}


def load_json(path: str) -> dict | None:
    text = _read(path)
    if text is None:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def audit_facts(audit: dict | None) -> dict[str, Any] | None:
    if not isinstance(audit, dict) or not audit:
        return None
    raw = audit.get("elements")
    elements = [e for e in raw if isinstance(e, dict)] if isinstance(raw, list) else []   # a hand-edited file must not crash status
    layers: dict[str, dict[str, int]] = {l: {"total": 0, "misplaced": 0} for l in ("L1", "L2", "L3", "L4", "MIXED")}
    verdicts: dict[str, int] = {}
    priorities: dict[str, int] = {"P1": 0, "P2": 0, "P3": 0}
    for e in elements:
        layer = e.get("actual_layer") if isinstance(e.get("actual_layer"), str) and e.get("actual_layer") else "MIXED"
        layers.setdefault(layer, {"total": 0, "misplaced": 0})
        layers[layer]["total"] += 1
        if e.get("verdict") and e["verdict"] != "KEEP":
            layers[layer]["misplaced"] += 1
        verdict = e["verdict"] if isinstance(e.get("verdict"), str) and e["verdict"] else "?"
        verdicts[verdict] = verdicts.get(verdict, 0) + 1
        if isinstance(e.get("priority"), str) and e["priority"] in priorities:
            priorities[e["priority"]] += 1
    meta = audit.get("audit") if isinstance(audit.get("audit"), dict) else {}
    cut = meta.get("cut_the_agent_test") if isinstance(meta.get("cut_the_agent_test"), dict) else {}
    removals = [r for r in audit.get("removals") or [] if isinstance(r, dict)] if isinstance(audit.get("removals"), list) else []
    return {
        "date": meta.get("date"),
        "health_score": meta.get("health_score"),
        "cut_the_agent_passed": cut.get("passed"),
        "elements": len(elements),
        "layers": layers,
        "verdicts": verdicts,
        "priorities": priorities,
        "process_leaks": len(audit["process_leaks"]) if isinstance(audit.get("process_leaks"), list) else 0,
        "guarded_rules": len(audit["guarded_rules"]) if isinstance(audit.get("guarded_rules"), list) else 0,
        "removals": {reason: sum(1 for r in removals if r.get("reason") == reason)
                     for reason in ("useless", "harmful", "outdated")},
    }


def harvest_facts(harvest: dict | None) -> dict[str, Any] | None:
    if not harvest:
        return None
    ev = harvest.get("evidence") or []
    counts: dict[str, int] = {}
    for e in ev:
        counts[e.get("signal") or "?"] = counts.get(e.get("signal") or "?", 0) + 1
    return {
        "since": harvest.get("since"),
        "prs_scanned": harvest.get("prs_scanned"),
        "agent_prs": harvest.get("agent_prs"),
        "counts": counts,
        "real_signals": sum(counts.get(s, 0) for s in ("S1", "S2", "S3", "S4")),
        "corrections_on_agent_prs": counts.get("S2", 0),
        "errors": len(harvest.get("errors") or []),
    }


def days_since(day_s: str | None, today: date) -> int | None:
    if not day_s:
        return None
    try:
        return (today - datetime.strptime(day_s, "%Y-%m-%d").date()).days
    except ValueError:
        return None


def collect(repo: str, harness_dir: str = ".harness", audit_path: str | None = None,
            harvest_path: str | None = None, today: date | None = None) -> dict[str, Any]:
    today = today or date.today()
    repo = os.path.abspath(repo)
    hdir = os.path.join(repo, harness_dir)
    # A file that fails its shape check counts for nothing: it is left aside and said in one line.
    audit, audit_problem = shape.counted(audit_path or os.path.join(hdir, "audit.json"), shape.check_audit)
    harvest, harvest_problem = shape.counted(harvest_path or os.path.join(hdir, "harvest.json"), shape.check_harvest)
    instr = instruction_facts(repo)
    source_text = _read(os.path.join(repo, instr["source"]["path"])) if instr["source"]["path"] else None
    marker = (instr["source"].get("harvest_marker") or {}).get("date") if instr["source"]["path"] else None
    return {
        "repo": repo,
        "date": today.isoformat(),
        "instructions": instr,
        "contracts": contract_facts(repo, source_text),
        "guardrails": guardrail_facts(repo),
        "audit": audit_facts(audit),
        "harvest": harvest_facts(harvest),
        "unreadable": [said for said in (audit_problem, harvest_problem) if said],
        "harvest_marker_age_days": days_since(marker, today),
        "config": config_facts(hdir),
        "dangling": dangling_facts(repo, source_text),
    }
