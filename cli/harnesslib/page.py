"""The state page: where a repository stands and where it is going, as one standalone HTML file.

Everything shown is computed here from what `status` measures: the files present or absent, layer
by layer, and the steps from today to the chosen level. The opinions of the last audit are carried
apart, marked as opinions. The medals are a tab of the same page. The script of the page only
shows this data: it decides nothing."""
from __future__ import annotations

import json
import os
import re
from typing import Any

from . import facts, maturity, medals

SCHEMA = "harness-page/1"
TEMPLATE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "state_template.html")
MAX_VERDICTS = 40
MAX_TEXT = 400
NOT_MEASURED = "nothing to measure yet: there is no instruction file"

# The four layers, from what the agent reads to what runs away from it.
LAYERS = (
    ("instructions", "Instructions", "what the agent reads at the start of every session"),
    ("procedures", "Procedures", "tasks written down so the agent can be given one whole"),
    ("checks", "Local checks", "tools that refuse a broken rule on the machine"),
    ("pipeline", "Pipeline", "what runs on every change, away from the agent"),
)
SOURCE = maturity.DEFAULT_SOURCE                # in TOUCHES, stands for the instruction file actually found
CLAUDE = maturity.CLAUDE_SOURCE
# CLAUDE.md alone is an accepted source: it is then shown as the source, and AGENTS.md as a choice.
CLAUDE_AS_SOURCE = {
    SOURCE: "Not needed here: CLAUDE.md is the source. Moving the instructions there, with a one-line pointer "
            "left in CLAUDE.md, lets other tools read them too.",
    CLAUDE: "The source of instructions here, loaded by Claude Code: the mode, the rules with their reason, what is forbidden.",
}
PURPOSE = {
    "AGENTS.md": "The single source of instructions: the mode, the rules with their reason, what is forbidden.",
    "CLAUDE.md": "What Claude Code loads. It should only point to AGENTS.md, so there is one source.",
    ".github/copilot-instructions.md": "What GitHub Copilot loads. Only needed if the team uses Copilot.",
    ".cursor/rules": "What Cursor loads. Only needed if the team uses Cursor.",
}
OPTIONAL = {".github/copilot-instructions.md", ".cursor/rules"}
NEW_CHECK, NEW_CONTRACT, NEW_PIPELINE = "a check for one rule", "a task contract", ".github/workflows/"
# What each check of the ladder touches when its step is done: (layer, file, "add" or "change").
# None: nothing to show on the map (the step is an action or comes with time).
TOUCHES: dict[str, tuple[str, str, str] | None] = {
    "L1.source": ("instructions", SOURCE, "add"),
    "L1.mode": ("instructions", SOURCE, "change"),
    "L1.short": ("instructions", SOURCE, "change"),
    "L1.single_source": ("instructions", "CLAUDE.md", "change"),
    "L1.forbidden": ("instructions", SOURCE, "change"),
    "L2.maintenance": ("instructions", SOURCE, "change"),
    "L2.rule_convention": ("instructions", SOURCE, "change"),
    "L2.marker_fresh": ("instructions", SOURCE, "change"),
    "L2.signal": None,
    "L3.ci": ("pipeline", NEW_PIPELINE, "add"),
    "L3.guarded": ("checks", NEW_CHECK, "add"),
    "L3.justified": ("instructions", SOURCE, "change"),
    "L3.audit": None,
    "L4.mode": ("instructions", SOURCE, "change"),
    "L4.process": ("instructions", SOURCE, "change"),
    "L4.contracts": ("procedures", NEW_CONTRACT, "add"),
    "L4.clean_prs": None,
    "L4.cut_the_agent": None,
}
VERDICT_PLAIN = {
    "KEEP": "in the right place",
    "PUSH_DOWN": "should be enforced by a tool, not only written",
    "PROMOTE": "should be written down for the agent",
    "MOVE": "belongs in another place",
    "REMOVE": "no longer serves",
    "SPLIT": "does too many things",
}


def _item(path: str, state: str, purpose: str, detail: str = "") -> dict[str, Any]:
    return {"path": path, "state": state, "purpose": purpose, "detail": detail}


def _instructions(instr: dict[str, Any]) -> list[dict[str, Any]]:
    claude_is_source = instr["source"].get("path") == CLAUDE
    purposes = {**PURPOSE, **CLAUDE_AS_SOURCE} if claude_is_source else PURPOSE
    optional = OPTIONAL | {SOURCE} if claude_is_source else OPTIONAL
    out = []
    for path, info in instr["files"].items():
        if not info.get("exists"):
            out.append(_item(path, "optional" if path in optional else "missing", purposes.get(path, "")))
        elif info.get("is_stub"):
            out.append(_item(path, "pointer", purposes.get(path, ""), "points to the single source"))
        else:
            lines = info.get("lines")
            detail = f"{lines} lines" if lines is not None else f"{len(info.get('files') or [])} file(s)"
            if claude_is_source and path == CLAUDE:
                detail += " · the source"
            out.append(_item(path, "present", purposes.get(path, ""), detail))
    return out


def _layers(f: dict[str, Any]) -> list[dict[str, Any]]:
    """The files of today, by layer. Only what `facts.collect` found: nothing is guessed."""
    items: dict[str, list[dict[str, Any]]] = {
        "instructions": _instructions(f["instructions"]),
        "procedures": [_item(c["path"], "present", "A task the agent can be given whole: its steps and what done looks like.",
                             "" if c.get("referenced") else "not cited by the instruction file")
                       for c in f["contracts"]["items"]],
        "checks": [_item(path, "present", f"A tool that enforces a rule on the machine ({kind}).")
                   for kind, paths in sorted(f["guardrails"]["tools"].items()) for path in paths],
        "pipeline": [_item(f".github/workflows/{name}", "present", "Runs on every change, away from the agent's machine.")
                     for name in f["guardrails"]["workflows"]],
    }
    return [{"id": ident, "title": title, "plain": plain, "items": items[ident]} for ident, title, plain in LAYERS]


def _steps(state: dict[str, Any]) -> list[dict[str, Any]]:
    """Every check that does not hold yet, in the order of the ladder: one step each. A step beyond
    the target level is kept, marked out of scope. With no instruction file, what the file would carry
    is marked `follows`: the page folds it into the step that creates the file, and does not show it.
    A step on the instruction file names the file found: CLAUDE.md when it is the source."""
    source = maturity.source_name(state["facts"])
    out = []
    for level in state["levels"]:
        for check in level["checks"]:
            if check["passed"]:
                continue
            follows = bool(check.get("follows"))
            missing, action = (NOT_MEASURED, maturity.WITH_FILE) if follows else maturity.CHECK_PLAIN[check["id"]]
            touch = None if follows else TOUCHES.get(check["id"])
            out.append({"level": level["level"], "missing": missing, "action": action, "waits": bool(check.get("waits")),
                        "follows": follows,
                        "in_scope": bool(level.get("in_scope", True)),
                        "touch": None if touch is None else {"layer": touch[0], "path": source if touch[1] == SOURCE else touch[1],
                                                         "effect": touch[2]}})
    return out


def _clip(value: Any) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    return text if len(text) <= MAX_TEXT else text[:MAX_TEXT - 1].rstrip() + "…"


def _verdicts(audit: Any) -> dict[str, Any] | None:
    """What the last audit said, element by element. An opinion with its evidence, not a measurement:
    the page shows it apart."""
    if not isinstance(audit, dict) or not isinstance(audit.get("elements"), list):
        return None
    rows = []
    for e in audit["elements"]:
        if not isinstance(e, dict) or not e.get("verdict") or e["verdict"] == "KEEP":
            continue
        where = _clip(e.get("path"))
        rows.append({"path": where, "file": where.split(":")[0], "verdict": _clip(e["verdict"]),
                     "plain": VERDICT_PLAIN.get(str(e["verdict"]), "to look at"),
                     "priority": _clip(e.get("priority")), "finding": _clip(e.get("finding")), "target": _clip(e.get("target"))})
    rows.sort(key=lambda r: (r["priority"] or "P9", r["path"]))
    meta = audit.get("audit") if isinstance(audit.get("audit"), dict) else {}
    return {"date": _clip(meta.get("date")), "total": len(rows), "rows": rows[:MAX_VERDICTS]}


def build(repo: str, harness_dir: str = ".harness", audit_path: str | None = None, harvest_path: str | None = None,
          today: Any = None) -> dict[str, Any]:
    f = facts.collect(repo, harness_dir, audit_path, harvest_path, today)
    state = maturity.evaluate(f)
    hdir = os.path.join(f["repo"], harness_dir)
    previous = facts.load_json(os.path.join(hdir, medals.FILE))                 # read only: the dates already earned
    target = state.get("target") or {}
    return {
        "schema": SCHEMA,
        "name": os.path.basename(f["repo"]) or f["repo"],
        "date": state["date"],
        "level": {"reached": state["level"]["reached"], "name": state["level"]["name"]},
        "target": {"level": target.get("level"), "name": target.get("name"), "reached": bool(target.get("reached"))},
        "ladder": [{"level": l["level"], "name": l["name"], "plain": maturity.LEVEL_PLAIN[l["level"]],
                    "achieved": bool(l["achieved"]), "in_scope": bool(l.get("in_scope", True))} for l in state["levels"]],
        "layers": _layers(f),
        "steps": _steps(state),
        "dangling": [_clip(f"{d.get('ref')} (line {d.get('line')} of the instruction file)") for d in state.get("dangling") or []
                     if isinstance(d, dict)],
        "audit": _verdicts(facts.load_json(audit_path or os.path.join(hdir, "audit.json"))),
        "medals": medals.build(medals.evaluate_repo(f["repo"], today), previous),
    }


def render_html(data: dict[str, Any]) -> str:
    """A standalone page: the data is in the file, the script only shows it."""
    with open(TEMPLATE_FILE, encoding="utf-8") as fh:
        template = fh.read()
    raw = json.dumps(data, ensure_ascii=False, sort_keys=True).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    title = f"{data['name']} · level {data['level']['reached']}".replace("&", "&amp;").replace("<", "&lt;")
    fields = {"csp": medals.csp(template), "title": title, "data": raw}       # a single pass: a value is never read again
    return re.sub(r"\{\{(csp|title|data)\}\}", lambda m: fields[m[1]], template)


def write(path: str, data: dict[str, Any]) -> None:
    folder = os.path.dirname(os.path.abspath(path))
    os.makedirs(folder, exist_ok=True)
    try:
        medals.write_file(path, render_html(data))
    finally:
        if os.path.isfile(f"{path}.tmp"):          # a write that failed half-way leaves nothing behind
            os.remove(f"{path}.tmp")
