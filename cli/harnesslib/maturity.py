"""The maturity model: five levels, each earned by measurable checks on the
facts collected by `facts.collect`. A level is reached when all its checks
pass; levels chain (level n assumes level n-1). Each check carries a next
action, so that the state always says what to do next.

Readable documentation: docs/maturity.md. The thresholds are here, as constants."""
from __future__ import annotations

from typing import Any, Callable

MAX_SOURCE_LINES = 60          # level 1: beyond this, it is reference material to move out
MAX_MARKER_AGE_DAYS = 45       # level 2: the harvest marker must be recent (a date, not proof that a harvest ran)
MIN_GUARDED_RATIO = 0.5        # level 3: half of the rules enforced by a tool
MIN_JUSTIFIED_RATIO = 0.5      # level 3: half of the rules say why

LEVELS = [
    (0, "None", "No instruction file: the agent starts from zero at every session."),
    (1, "Framed", "A short instruction file, an explicit mode, a single source: the agent knows where it is."),
    (2, "Looped", "The feedback loop runs: incidents become rules."),
    (3, "Verified", "Mandatory rules are enforced by tools, not by text."),
    (4, "Delegated", "Whole tasks are handed to the agent and come back clean."),
]

Check = dict[str, Any]

# What only time makes pass: a review signal, observed agent PRs. Such a check does not stop the climb:
# the next level, if targeted, is worked on without waiting for it (2026-11-14).
WAITING = {"L2.signal", "L4.clean_prs"}

# With no instruction file, one thing is missing: the file. What it would carry (mode, length, single
# source, forbidden section) is not measured, so it is not reported as failed for another reason: these
# checks stay unpassed, the level does not move, and they are marked as following the file (2026-11-21).
FOLLOWS_SOURCE = "L1.source"
WITH_FILE = "comes with the instruction file"

# The file the harness writes, and the one it also accepts as the source when it stands alone. Labels
# and next actions name the file actually found, never the one that would have been preferred (2026-11-21).
DEFAULT_SOURCE = "AGENTS.md"
CLAUDE_SOURCE = "CLAUDE.md"

# The signal check fails the same way in two different situations: a harvest ran and found nothing, and
# no harvest ever ran (no .harness/harvest.json; a `ref=init` marker is a date, not a harvest). Only the
# first one comes with time: in the second, nothing has looked yet, and one harvest tells. The measure
# does not move; the words do (2026-11-21).
SIGNAL = "L2.signal"
NEVER_HARVESTED = ("nobody has looked yet for a review remark or a fixed agent change to turn into a rule",
                   "collect once what recent reviews taught, to see whether a rule comes out of it")


def _check(cid: str, label: str, passed: bool, value: Any, next_action: str) -> Check:
    return {"id": cid, "label": label, "passed": bool(passed), "value": value,
            "next_action": None if passed else next_action, "waits": not passed and cid in WAITING}


def _src(f: dict) -> dict:
    return f["instructions"]["source"]


def source_name(f: dict) -> str:
    """The instruction file found, by its path; the one harness-init writes when there is none."""
    return _src(f).get("path") or DEFAULT_SOURCE


def _single_source(f: dict, has_src: bool, name: str) -> Check:
    claude = f["instructions"]["files"][CLAUDE_SOURCE]
    if name == CLAUDE_SOURCE:
        # Accepted on purpose: the check holds, and its line says what is true instead of naming a stub.
        return _check("L1.single_source",
                      f"{CLAUDE_SOURCE} is the source: fine, or move it to {DEFAULT_SOURCE} and leave a pointer",
                      True, claude, "")
    return _check("L1.single_source", f"{CLAUDE_SOURCE} is an @{DEFAULT_SOURCE} stub (or absent)",
                  has_src and ((not claude["exists"]) or claude.get("is_stub")), claude,
                  f"Reduce {CLAUDE_SOURCE} to `@{DEFAULT_SOURCE}` and merge its useful content into {DEFAULT_SOURCE}.")


def level1(f: dict) -> list[Check]:
    src = _src(f)
    has_src = bool(src.get("path"))
    name = source_name(f)
    checks = [
        _check("L1.source", f"An instruction file exists ({name})", has_src, src.get("path"),
               f"Run harness-init to create {DEFAULT_SOURCE}."),
        _check("L1.mode", "The line \"Mode: delegation | assistance\" is present", bool(src.get("mode")), src.get("mode"),
               f"Add the mode line at the top of {name}; harness-audit uses it for its scoring."),
        _check("L1.short", f"The loaded file is at most {MAX_SOURCE_LINES} lines",
               has_src and (src.get("lines") or 0) <= MAX_SOURCE_LINES, src.get("lines"),
               "Move the reference material (commands, architecture) to on-demand files or skills."),
        _single_source(f, has_src, name),
        _check("L1.forbidden", "A \"Forbidden\" section says what an agent never does",
               bool(src.get("has_forbidden_section")), src.get("has_forbidden_section"),
               "Add the Forbidden section: folders, secrets, production actions, force push."),
    ]
    if has_src:
        return checks
    return [c if c["id"] == FOLLOWS_SOURCE else {**c, "next_action": None, "follows": FOLLOWS_SOURCE} for c in checks]


def level2(f: dict) -> list[Check]:
    src = _src(f)
    h = f["harvest"]
    age = f["harvest_marker_age_days"]
    return [
        _check("L2.maintenance", "A maintenance section says how the file evolves",
               bool(src.get("has_maintenance_section")), src.get("has_maintenance_section"),
               "Add the \"Maintaining this file\" section of the harness-init template."),
        _check("L2.rule_convention", "The `rule:` review convention is documented",
               bool(src.get("mentions_rule_convention")), src.get("mentions_rule_convention"),
               "Document it: a review comment that starts with `rule:` is a candidate rule."),
        _check("L2.marker_fresh", f"The harvest marker is less than {MAX_MARKER_AGE_DAYS} days old",
               age is not None and age <= MAX_MARKER_AGE_DAYS, age,
               "Run harness-harvest and merge its PR, which sets the marker."),
        _check("L2.signal", "The last harvest found at least one real signal: a review remark or a fixed agent change",
               bool(h and h["real_signals"] > 0), h["real_signals"] if h else None,
               "Mark incidents in review with `rule:`; without a signal, the loop is not running yet." if h else
               "No harvest has run yet: run harness-harvest once, it says whether a signal is already there."),
    ]


def level3(f: dict) -> list[Check]:
    src = _src(f)
    a = f["audit"]
    total = src.get("rules_total") or 0
    guarded_ratio = (src.get("rules_guarded") or 0) / total if total else 0.0
    justified_ratio = (src.get("rules_justified") or 0) / total if total else 0.0
    return [
        _check("L3.ci", "A CI exists (workflows or .gitlab-ci.yml)", f["guardrails"]["has_ci"],
               f["guardrails"]["workflows"], "Without CI, no rule can be guaranteed: set one up."),
        _check("L3.guarded", f"At least {int(MIN_GUARDED_RATIO*100)}% of the rules are \"Enforced by\" a tool",
               total > 0 and guarded_ratio >= MIN_GUARDED_RATIO, round(guarded_ratio, 2),
               "Push the narrated rules down to a tool: custom lint, architecture test, PR check."),
        _check("L3.justified", f"At least {int(MIN_JUSTIFIED_RATIO*100)}% of the rules say why",
               total > 0 and justified_ratio >= MIN_JUSTIFIED_RATIO, round(justified_ratio, 2),
               "Add \"Why:\" or the link to the incident to each rule."),
        _check("L3.audit", "A harness-audit exists and has no urgent finding open",
               bool(a) and a["priorities"].get("P1", 0) == 0, a["priorities"] if a else None,
               "Run harness-audit, write its JSON to .harness/audit.json, handle its urgent findings."),
    ]


def level4(f: dict) -> list[Check]:
    src = _src(f)
    h = f["harvest"]
    a = f["audit"]
    return [
        _check("L4.mode", "The mode is delegation", src.get("mode") == "delegation", src.get("mode"),
               "Switch to delegation with harness-init once the guardrails are in place."),
        _check("L4.process", "A \"Working process\" section frames the agent",
               bool(src.get("has_process_section")), src.get("has_process_section"),
               "Add: when to stop and ask, definition of done, red CI, flaky test."),
        _check("L4.contracts", "At least one task contract exists and is referenced",
               any(c["referenced"] for c in f["contracts"]["items"]), f["contracts"]["count"],
               f"Create .claude/skills/<task>/SKILL.md for the first delegated task and cite it in {source_name(f)}."),
        _check("L4.clean_prs", "The last harvest sees agent PRs with no after-the-fact correction",
               bool(h and (h["agent_prs"] or 0) > 0 and h["corrections_on_agent_prs"] == 0),
               {"agent_prs": h["agent_prs"], "S2": h["corrections_on_agent_prs"]} if h else None,
               "Each after-the-fact correction on an agent PR is a missing rule or guardrail: handle them."),
        _check("L4.cut_the_agent", "The audit's \"cut the agent\" test passes",
               bool(a and a["cut_the_agent_passed"]), a["cut_the_agent_passed"] if a else None,
               "Move into scripts or CI the steps that exist only in prompts."),
    ]


LEVEL_CHECKS: dict[int, Callable[[dict], list[Check]]] = {1: level1, 2: level2, 3: level3, 4: level4}

# The map (`status --map`) speaks to the user, not to the agent: plain words, no check ids, no level
# name left undefined. One phrase per level; per check, what is missing and the step that fixes it.
LEVEL_PLAIN = {
    0: "no instructions: the agent starts from zero at every session",
    1: "the agent knows the project, its rules and what it must never do",
    2: "review remarks become rules, so the same mistake is not made twice",
    3: "mandatory rules are enforced by tools, not just written down",
    4: "whole tasks go to the agent and come back clean",
}

CHECK_PLAIN: dict[str, tuple[str, str]] = {
    "L1.source": ("there is no instruction file (AGENTS.md) for the agent",
                  "write a short AGENTS.md: four questions, about half an hour"),
    "L1.mode": ("the file does not say whether agents work alone or with a person reviewing each change",
                "add one line saying how agents work here"),
    "L1.short": (f"the instruction file is longer than {MAX_SOURCE_LINES} lines: the agent reads it with less attention",
                 f"move reference material out of the file until it is {MAX_SOURCE_LINES} lines or fewer"),
    "L1.single_source": ("CLAUDE.md carries its own instructions instead of pointing to AGENTS.md",
                         "merge CLAUDE.md into AGENTS.md and leave a one-line pointer"),
    "L1.forbidden": ("the file does not say what an agent must never do",
                     "write down what an agent must never do"),
    "L2.maintenance": ("the file does not say how it is kept up to date",
                       "add a short section saying how the file is kept up to date"),
    "L2.rule_convention": ("the team has no agreed way to turn a review remark into a rule",
                           "agree that a review comment starting with `rule:` proposes a rule, and write it in the file"),
    "L2.marker_fresh": (f"nobody has turned recent review feedback into rule changes in the last {MAX_MARKER_AGE_DAYS} days",
                        "collect what recent reviews taught and propose the rule changes"),
    "L2.signal": ("no review remark or fixed agent change has fed a rule yet",
                  "nothing to write: this comes with real reviews, over time"),
    "L3.ci": ("there is no CI to run checks on every change",
              "set up a minimal CI that runs the project's checks"),
    "L3.guarded": (f"fewer than {int(MIN_GUARDED_RATIO*100)}% of the rules are enforced by a tool "
                   "(a test, a lint rule, a CI check)",
                   "turn one written rule into a check that fails when the rule is broken"),
    "L3.justified": (f"fewer than {int(MIN_JUSTIFIED_RATIO*100)}% of the rules say why they exist",
                     "ask the team why, for the rules that do not say it"),
    "L3.audit": ("no full review of the setup exists yet, or the last one found an urgent problem",
                 "run a full review of the setup and fix its urgent findings"),
    "L4.mode": ("agents work with a person reviewing each change, not on their own",
                "decide whether agents may take whole tasks on their own"),
    "L4.process": ("the file does not say when the agent stops to ask, or when a task is done",
                   "write when the agent stops to ask, and when a task is done"),
    "L4.contracts": ("no task has a written procedure the agent can follow on its own",
                     "write the procedure of the first task to hand over"),
    "L4.clean_prs": ("no agent change has yet been seen merged without a fix afterwards",
                     "nothing to write: this comes with real agent changes, over time"),
    "L4.cut_the_agent": ("some mandatory steps exist only in prompts, not in scripts or CI",
                         "move one step that lives only in a prompt into a script or a CI job"),
}


def layer_view(f: dict) -> dict[str, Any]:
    """The L1–L4 layer view, from the last audit; otherwise pointers."""
    a = f["audit"]
    if a:
        return {"source": "audit", "date": a["date"], "layers": a["layers"],
                "process_leaks": a["process_leaks"], "health_score": a["health_score"]}
    src = _src(f)
    return {
        "source": "estimate",
        "layers": {
            "L1": {"total": None, "misplaced": None},
            "L2": {"total": (1 if src.get("path") else 0) + f["contracts"]["count"], "misplaced": None},
            "L3": {"total": len(f["guardrails"]["tools"]), "misplaced": None},
            "L4": {"total": len(f["guardrails"]["workflows"]), "misplaced": None},
        },
        "hint": "Run harness-audit for a measured layer view.",
    }


def evaluate(f: dict) -> dict[str, Any]:
    target = (f.get("config") or {}).get("target_level")      # None: the owner declared nothing
    levels = []
    reached = 0
    blocked = False
    for num, name, summary in LEVELS:
        checks = LEVEL_CHECKS[num](f) if num else []
        passed = all(c["passed"] for c in checks) if num else True
        achieved = passed and not blocked
        if not achieved and num:
            blocked = True
        if achieved:
            reached = num
        levels.append({"level": num, "name": name, "summary": summary, "achieved": achieved,
                       "in_scope": target is None or num <= target,
                       "checks": checks, "passed_checks": sum(c["passed"] for c in checks), "total_checks": len(checks)})
    next_level = next((l for l in levels if not l["achieved"]), None)
    # A level is a place where one can stay: beyond the target level, nothing is proposed.
    # A level that only lacks what time brings does not hold back the next ones.
    next_actions: list[str] = []
    waiting: list[str] = []
    for l in levels:
        if l["achieved"] or not l["level"]:
            continue
        if not l["in_scope"]:
            break
        failing = [c for c in l["checks"] if not c["passed"]]
        doable = [c for c in failing if not c["waits"] and not c.get("follows")]
        waiting += [c["id"] for c in failing if c["waits"]]
        if doable:
            next_actions = [c["next_action"] for c in doable]
            break
    return {
        "schema": "harness-state/1",
        "repo": f["repo"],
        "date": f["date"],
        "level": {"reached": reached, "name": LEVELS[reached][1], "next": next_level["level"] if next_level else None},
        "target": {"level": target, "name": LEVELS[target][1] if target else None,
                   "reached": target is not None and reached >= target},
        "levels": levels,
        "layers": layer_view(f),
        "next_actions": next_actions[:3],
        "waiting": waiting,
        "dangling": f.get("dangling") or [],
        "facts": f,
    }


def render_markdown(state: dict) -> str:
    lvl = state["level"]
    target = state.get("target") or {"level": None, "reached": False}
    if target["level"] is None:
        goal = "no target level: `harness target <n>` says where you want to stop"
    elif target["reached"]:
        goal = f"target: {target['level']} · **target reached**"
    else:
        goal = f"target: {target['level']} · {target['name']}"
    out = [f"# Harness state — {state['repo']}", "",
           f"**Level reached**: {lvl['reached']} · {lvl['name']} · {goal}",
           f"**Date**: {state['date']}", ""]
    for l in state["levels"]:
        if not l["level"]:
            continue
        if not l.get("in_scope", True):
            out.append(f"## · Level {l['level']} — {l['name']} (beyond target)")
            out.append("")
            continue
        mark = "✓" if l["achieved"] else "·"
        out.append(f"## {mark} Level {l['level']} — {l['name']} ({l['passed_checks']}/{l['total_checks']})")
        out.append(f"_{l['summary']}_")
        for c in l["checks"]:
            if c.get("follows"):
                out.append(f"- [ ] {c['label']} → {WITH_FILE}")
                continue
            out.append(f"- [{'x' if c['passed'] else ' '}] {c['label']}"
                       + ("" if c["passed"] else (" → **waiting**: " if c.get("waits") else " → ") + c["next_action"]))
        out.append("")
    if state.get("dangling"):
        out.append("## References without a target")
        for d in state["dangling"]:
            what = {"contract": "contract cited, SKILL.md not found", "job": "CI job cited, absent from the workflows"}.get(
                d["kind"], "guardrail cited, path not found")
            out.append(f"- line {d['line']}: `{d['ref']}` ({what})")
        out.append("")
    lay = state["layers"]
    out.append(f"## Layers ({'audit of ' + str(lay.get('date')) if lay['source'] == 'audit' else 'estimate, no audit'})")
    for name, v in lay["layers"].items():
        if name == "MIXED" and not (v.get("total") or 0):
            continue
        tot = "?" if v.get("total") is None else v["total"]
        mis = "" if v.get("misplaced") is None else f", {v['misplaced']} misplaced"
        out.append(f"- {name}: {tot} item(s){mis}")
    if lay.get("hint"):
        out.append(f"- {lay['hint']}")
    out.append("")
    if state.get("waiting"):
        out.append("## Waiting")
        # Plain words, as on the map: the check ids stay in the JSON (`waiting`).
        out.extend(f"- {CHECK_PLAIN[cid][0]}" for cid in state["waiting"])
        out.append("Only time makes them pass, with real reviews or real PRs. "
                   "The level that carries them will count then; the targeted levels above are worked on without waiting for it.")
        out.append("")
    if state["next_actions"]:
        out.append("## Next actions")
        out.extend(f"{i}. {a}" for i, a in enumerate(state["next_actions"], 1))
        out.append("")
    elif target["reached"]:
        out.append("## Target reached")
        out.append("The target level is held. Nothing to do.")
        out.append("")
    return "\n".join(out)


def _never_harvested(state: dict, check: Check) -> bool:
    """The signal check fails and no harvest ever ran: nothing has looked for a signal yet."""
    return check["id"] == SIGNAL and not check["passed"] and not (state.get("facts") or {}).get("harvest")


def _plain(state: dict, check: Check) -> tuple[str, str]:
    """What is missing and the step that fixes it, in the map's words, for a failing check."""
    return NEVER_HARVESTED if _never_harvested(state, check) else CHECK_PLAIN[check["id"]]


def _first_doable(state: dict) -> tuple[int, Check] | None:
    """The level and failing check the next step works on: the same walk as `evaluate`, except that a
    signal nobody has looked for yet is a step (one harvest), once the rest of its level is done."""
    for l in state["levels"]:
        if l["achieved"] or not l["level"]:
            continue
        if not l.get("in_scope", True):
            return None
        failing = [c for c in l["checks"] if not c["passed"] and not c.get("follows")]
        doable = [c for c in failing if not c["waits"]] or [c for c in failing if _never_harvested(state, c)]
        if doable:
            return l["level"], doable[0]
    return None


def beyond_target(state: dict, target: dict | None = None) -> str | None:
    """The one-line offer made once the target is held (or every level reached): the level above, as a
    choice. None while there is still something to reach. The map and the medals say this same line."""
    target = target or state.get("target") or {"level": None, "reached": False}
    reached = state["level"]["reached"]
    if not (target["reached"] or reached >= len(LEVELS) - 1):
        return None
    above = max(target["level"] or 0, reached) + 1
    if above >= len(LEVELS):
        return "every level is reached. What is in place still needs upkeep."
    return (f"your target is reached. If you want more, level {above} ({LEVELS[above][1]}) "
            f"would bring this: {LEVEL_PLAIN[above]}. It is your choice.")


def _next_step(state: dict, target: dict) -> str:
    if state.get("dangling"):
        return "fix or remove what the instruction file cites but cannot be found."
    found = _first_doable(state)
    if found:
        num, check = found
        return f"{_plain(state, check)[1]} (towards level {num})."
    offer = beyond_target(state, target)
    if offer:
        return f"none: {offer}"
    if state.get("waiting"):
        return "none for now: what is missing comes with real reviews and real agent changes, over time."
    return "none."


def render_map(state: dict) -> str:
    """The map the skills show first: in a few plain lines, what each level brings, where the
    repository is, the target, what the next level still needs and the next step. No check id."""
    reached = state["level"]["reached"]
    target = state.get("target") or {"level": None, "reached": False}
    out = ["Where this repository stands, level by level:"]
    for l in state["levels"]:
        num = l["level"]
        if num == 0 and reached:
            continue
        mark = "✓" if l["achieved"] and num else "·"
        line = f"{mark} {num} {l['name']:<10} {LEVEL_PLAIN[num]}"
        if num == reached:
            line += "   ← you are here"
        elif not l.get("in_scope", True) and not l["achieved"]:
            line += "   (beyond your target)"
        out.append(line)
    out.append("")
    if target["level"] is None:
        out.append("Target: none chosen yet. You decide how far to go; you can stay at any level.")
    else:
        out.append(f"Target: level {target['level']}, {target['name']} — "
                   + ("reached." if target["reached"] else "not reached yet."))
    nxt = state["level"]["next"]
    if nxt is not None and (target["level"] is None or nxt <= target["level"]):
        out.append(f"What level {nxt} still needs:")
        for c in state["levels"][nxt]["checks"]:
            if not c["passed"] and not c.get("follows"):
                waits = c["waits"] and not _never_harvested(state, c)
                out.append(f"- {_plain(state, c)[0]}" + (" (comes with time, not with work)" if waits else ""))
    if state.get("dangling"):
        out.append(f"Broken references: the instruction file cites {len(state['dangling'])} thing(s) "
                   "that cannot be found.")
    out.append("Next step: " + _next_step(state, target))
    return "\n".join(out) + "\n"
