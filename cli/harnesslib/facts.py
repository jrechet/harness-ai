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

from .github import parse_rules

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
            "has_maintenance_section": any(re.search(r"maintenance", h, re.I) for h in headings),
            "has_process_section": any(re.search(r"processus de travail|working process|workflow", h, re.I) for h in headings),
            "has_forbidden_section": any(re.search(r"interdits?|never do|forbidden", h, re.I) for h in headings),
            "mentions_rule_convention": bool(RULE_CONVENTION_RE.search(text)),
            "harvest_marker": {"date": marker.group(1), "ref": marker.group(2)} if marker else None,
        })
    return {"files": files, "source": source}


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
    }
