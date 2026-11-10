"""Collecte des faits mesurables d'un dépôt : fichiers d'instructions, règles,
boucle de retour, contrats, garde-fous, et les derniers JSON d'audit et de
harvest. Aucun jugement ici : des nombres, des booléens, des chemins.

Convention : les sorties des skills vivent dans `<repo>/.harness/` —
`audit.json` (bloc machine de harness-audit), `harvest.json` (évidences de
harness-harvest), `state.json` (écrit par `harness status`)."""
from __future__ import annotations

import json
import os
import re
from datetime import date, datetime
from typing import Any

from .github import iter_rules, parse_rules

INSTRUCTION_FILES = ["AGENTS.md", "CLAUDE.md", ".github/copilot-instructions.md"]
CURSOR_RULES_DIR = ".cursor/rules"
CONTRACT_DIRS = [".claude/skills", ".agents/skills"]
WORKFLOW_DIR = ".github/workflows"

# Fichiers dont la présence signale un garde-fou L3 (lint, archi, hooks, formats).
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
GUARDRAIL_CONTENT_HINTS = {          # motifs cherchés dans les fichiers de build
    "archunit": r"archunit",
    "spotless": r"spotless",
    "checkstyle": r"checkstyle",
    "errorprone": r"errorprone",
}
BUILD_FILES = ["build.gradle", "build.gradle.kts", "pom.xml", "package.json", "pyproject.toml"]

MODE_RE = re.compile(r"^\s*(?:[-*]\s*)?Mode\s*:\s*\**\s*(d[ée]l[ée]gation|assistance)\b", re.I | re.M)
MARKER_RE = re.compile(r"<!--\s*harvest:\s*last=(\d{4}-\d{2}-\d{2})(?:\s+ref=(\S+))?\s*-->")
GUARDED_RE = re.compile(r"v[ée]rifi[ée]e?\s+par\s*:|guarded\s+by\s*:|enforced\s+by\s*:", re.I)
UNGUARDED_RE = re.compile(r"\(non\s+v[ée]rifi[ée]e?\)|\(unverified\)", re.I)
WHY_RE = re.compile(r"pourquoi\s*:|why\s*:|incident|issue\s*#?\d+|#\d+|https?://", re.I)
# « Git Workflow » d'un fichier généré n'est pas un processus de travail : « workflow » seul, ou qualifié.
PROCESS_HEADING_RE = re.compile(r"processus de travail|working process|working agreements?|^(?:agent |working )?workflow$", re.I)
# Date d'une règle : `[2026-11]` ou `[2026-11-10]` en fin de puce. Sans elle, « sans incident depuis
# six mois » ne se calcule pas et rien ne dit pour quelle génération de modèles la règle fut écrite.
RULE_DATE_RE = re.compile(r"\[(\d{4}-\d{2}(?:-\d{2})?)\]")
DELEGATED_HEADING_RE = re.compile(r"t[âa]ches d[ée]l[ée]gu[ée]es|delegated tasks", re.I)
# Les données de test portent parfois des fichiers d'instructions factices : ce ne sont pas ceux du dépôt.
SKIP_DIRS = {".git", "node_modules", "vendor", "dist", "build", ".harness", "runs", "__pycache__", ".venv",
             "fixtures", "testdata"}
INSTRUCTION_NAMES = {"AGENTS.md", "CLAUDE.md", "SKILL.md", "copilot-instructions.md"}
RULE_CONVENTION_RE = re.compile(r"`rule:`|\brule:\s", re.I)


def _read(path: str) -> str | None:
    try:
        with open(path, encoding="utf-8") as fh:
            return fh.read()
    except OSError:
        return None


def _exists(repo: str, rel: str) -> bool:
    return os.path.exists(os.path.join(repo, rel))


def resolve_includes(repo: str, text: str, depth: int = 0) -> str:
    """Remplace les lignes `@chemin` (inclusion Claude Code) par le fichier visé."""
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

    # Le fichier « source » : AGENTS.md, sinon CLAUDE.md s'il n'est pas un stub.
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
            "has_maintenance_section": any(re.search(r"maintenance", h, re.I) for h in headings),
            "has_process_section": any(PROCESS_HEADING_RE.search(h) for h in headings),
            "has_forbidden_section": any(re.search(r"interdits?|never do|forbidden", h, re.I) for h in headings),
            "mentions_rule_convention": bool(RULE_CONVENTION_RE.search(text)),
            "harvest_marker": {"date": marker.group(1), "ref": marker.group(2)} if marker else None,
        })
    return {"files": files, "source": source}


def rule_date(rule: str) -> str | None:
    """La date portée par une règle (`[AAAA-MM]` ou `[AAAA-MM-JJ]`), la dernière si plusieurs."""
    found = RULE_DATE_RE.findall(rule)
    return found[-1] if found else None


def instruction_corpus(repo: str, names: set[str] | None = None, resolve: bool = True) -> dict[str, str]:
    """Le texte d'instructions d'un dépôt, par chemin relatif : AGENTS.md et CLAUDE.md à tout niveau,
    contrats (SKILL.md), stub Copilot, règles Cursor ; `@inclusions` résolues sauf `resolve=False`."""
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
    """`.harness/config.json` : ce que le propriétaire a décidé, à commencer par le palier visé."""
    config = load_json(os.path.join(hdir, "config.json")) or {}
    target = config.get("target_level")
    return {"target_level": target if isinstance(target, int) and 1 <= target <= 4 else None}


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
    """Les identifiants de jobs des workflows GitHub du dépôt ; None s'il n'y a pas de workflow."""
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
    """Références du fichier source qui ne mènent nulle part : un contrat cité sous « Tâches
    déléguées » sans SKILL.md, un chemin cité après « Vérifiée par » qui n'existe pas, un job de CI
    cité qu'aucun workflow ne définit (le garde-fou a disparu, la phrase est restée). Un nom de règle
    de linter (`eslint/no-raw-fetch`) n'est pas un chemin : on ne juge qu'un jeton avec une extension,
    ou un chemin dont le premier segment existe à la racine."""
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
        for token in re.findall(r"`([^`\s]+)`", claim):
            token = token.rstrip(".,;:").lstrip("./")
            has_ext = bool(re.search(r"\.\w{1,5}$", token))
            rooted = "/" in token and _exists(repo, token.split("/", 1)[0])
            if not (has_ext or rooted) or _exists(repo, token):
                continue
            if files is None:
                files = _repo_files(repo)
            if not cited_path_exists(repo, token, files):
                dangling.append({"kind": "guard", "ref": token, "line": number})
    return dangling


def cited_path_exists(repo: str, token: str, files: list[str] | None = None) -> bool:
    """Un chemin cité existe s'il est là tel quel, ou si un fichier du dépôt porte ce nom ou ce suffixe."""
    if _exists(repo, token):
        return True
    files = _repo_files(repo) if files is None else files
    return any(f == token or f.endswith("/" + token) or f.startswith(token.rstrip("/") + "/") for f in files)


def contract_facts(repo: str, source_text: str | None) -> dict[str, Any]:
    contracts = []
    for d in CONTRACT_DIRS:
        base = os.path.join(repo, d)
        if not os.path.isdir(base):
            continue
        for name in sorted(os.listdir(base)):
            if os.path.isfile(os.path.join(base, name, "SKILL.md")):
                contracts.append({"name": name, "path": f"{d}/{name}/SKILL.md",
                                  "referenced": bool(source_text and name in source_text)})
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
    if not audit:
        return None
    elements = audit.get("elements") or []
    layers: dict[str, dict[str, int]] = {l: {"total": 0, "misplaced": 0} for l in ("L1", "L2", "L3", "L4", "MIXED")}
    verdicts: dict[str, int] = {}
    priorities: dict[str, int] = {"P1": 0, "P2": 0, "P3": 0}
    for e in elements:
        layer = e.get("actual_layer") or "MIXED"
        layers.setdefault(layer, {"total": 0, "misplaced": 0})
        layers[layer]["total"] += 1
        if e.get("verdict") and e["verdict"] != "KEEP":
            layers[layer]["misplaced"] += 1
        verdicts[e.get("verdict") or "?"] = verdicts.get(e.get("verdict") or "?", 0) + 1
        if e.get("priority") in priorities:
            priorities[e["priority"]] += 1
    meta = audit.get("audit") or {}
    return {
        "date": meta.get("date"),
        "health_score": meta.get("health_score"),
        "cut_the_agent_passed": (meta.get("cut_the_agent_test") or {}).get("passed"),
        "elements": len(elements),
        "layers": layers,
        "verdicts": verdicts,
        "priorities": priorities,
        "process_leaks": len(audit.get("process_leaks") or []),
        "guarded_rules": len(audit.get("guarded_rules") or []),
        "removals": {reason: sum(1 for r in audit.get("removals") or [] if r.get("reason") == reason)
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
    audit = load_json(audit_path or os.path.join(hdir, "audit.json"))
    harvest = load_json(harvest_path or os.path.join(hdir, "harvest.json"))
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
        "harvest_marker_age_days": days_since(marker, today),
        "config": config_facts(hdir),
        "dangling": dangling_facts(repo, source_text),
    }
