"""`fixture check` subcommand: compares what `status` measures on a fixture
with `expected.json`, and, if an audit JSON is given, compares the verdicts with
the expected traps; if the result of a harness-init is given (`--init`), grades
what it wrote against the `init` block. Output: a readable report and an exit
code of 0 if everything matches, 1 otherwise."""
from __future__ import annotations

import argparse
import difflib
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import date
from typing import Any

from . import facts, maturity
from .github import parse_rules

FIXTURES_ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                             "fixtures", "repos")


def check_status(fixture_dir: str, expected: dict, today: date | None = None) -> list[str]:
    """Problems between the measured state and the `status` block of expected.json."""
    state = maturity.evaluate(facts.collect(os.path.join(fixture_dir, "repo"), today=today))
    checks = {c["id"]: c["passed"] for l in state["levels"] for c in l["checks"]}
    problems = []
    if state["level"]["reached"] != expected["level_reached"]:
        problems.append(f"level {state['level']['reached']} ≠ expected {expected['level_reached']}")
    if state["facts"]["instructions"]["source"]["path"] != expected.get("source_path"):
        problems.append(f"source {state['facts']['instructions']['source']['path']} ≠ expected {expected.get('source_path')}")
    for cid in expected.get("failing_checks", []):
        if checks.get(cid, None) is not False:
            problems.append(f"{cid} should fail (state: {checks.get(cid)})")
    for cid in expected.get("passing_checks", []):
        if checks.get(cid, None) is not True:
            problems.append(f"{cid} should pass (state: {checks.get(cid)})")
    tools = sorted(state["facts"]["guardrails"]["tools"])
    if "guardrail_tools" in expected and tools != sorted(expected["guardrail_tools"]):
        problems.append(f"guardrails {tools} ≠ expected {sorted(expected['guardrail_tools'])}")
    if "contracts" in expected and state["facts"]["contracts"]["count"] != expected["contracts"]:
        problems.append(f"contracts {state['facts']['contracts']['count']} ≠ expected {expected['contracts']}")
    return problems


def _elements_for(audit: dict, path: str, own_only: bool = False) -> list[dict]:
    """The elements whose path it is; failing that, those that cite it as evidence
    (a report may file a file under a broader element). `own_only` for a healthy item:
    a file cited as contrast in another one's evidence does not borrow its verdict."""
    path = path.lower()
    elements = audit.get("elements") or []
    own = [e for e in elements if path in (e.get("path") or "").lower()]
    if own or own_only:
        return own
    return [e for e in elements if any(path in (ev or "").lower() for ev in e.get("evidence") or [])]


def _matches(rule: str, spec: dict) -> bool:
    """A rule matches `rule_keywords` (one of them) and `rule_all_of` (all of them), when they are given."""
    rule = rule.lower()
    any_of = [k.lower() for k in spec.get("rule_keywords") or []]
    all_of = [k.lower() for k in spec.get("rule_all_of") or []]
    return (not any_of or any(k in rule for k in any_of)) and all(k in rule for k in all_of) and bool(any_of or all_of)


def _cited_line(repo: str | None, path: Any, line: Any) -> str:
    """The whole line a removal points to by `path` and `line`, read in the audited repository. The report
    template allows a shortened quote: the quoted text alone is not enough to recognise the line
    (2026-11-14, the 64 KB limit quoted by its "Why" alone)."""
    if not repo or not isinstance(path, str) or not isinstance(line, int) or line < 1:
        return ""
    target = os.path.normpath(os.path.join(repo, path.split(":", 1)[0]))
    if not target.startswith(os.path.abspath(repo) + os.sep):
        return ""
    lines = (facts._read(target) or "").splitlines()
    return lines[line - 1] if line <= len(lines) else ""


def check_audit(audit: dict, expected: dict, repo: str | None = None) -> dict[str, Any]:
    """Score of an audit against the expected traps: found, missed, wrong, healthy items flagged. `repo`,
    the audited repository, is used to read in full a removed line the audit quotes shortened."""
    found, missed, wrong = [], [], []
    leaks = [json.dumps(l, ensure_ascii=False).lower() for l in audit.get("process_leaks") or []]
    leaks_text = " ".join(leaks)

    def leaked(trap: dict) -> bool:
        """A leak is found when **one single** process_leaks entry holds all the `leak_keywords`
        and, if any, one of the `leak_any_of`. Searching all leaks at once credited a trap with
        the words of two unrelated leaks."""
        all_of = [k.lower() for k in trap.get("leak_keywords") or []]
        any_of = [k.lower() for k in trap.get("leak_any_of") or []]
        return bool(all_of or any_of) and any(
            all(k in leak for k in all_of) and (not any_of or any(k in leak for k in any_of)) for leak in leaks)

    def wanted(trap: dict) -> str:
        return f"{trap.get('leak_keywords') or []}" + (f" and one of {trap['leak_any_of']}" if trap.get("leak_any_of") else "")

    for trap in expected.get("traps", []):
        # A trap is found either by an element with the right verdict on the right path, or, for a told
        # rule, by its presence in process_leaks (that is where the report files these leaks).
        has_leak_spec = bool(trap.get("leak_keywords") or trap.get("leak_any_of"))
        in_leaks = leaked(trap)
        hits = _elements_for(audit, trap["path"])
        ok = [e for e in hits if e.get("verdict") in trap["verdicts"]
              and (not trap.get("priorities") or e.get("priority") in trap["priorities"])]
        if trap.get("require_leak"):
            # the trap is a leak: only process_leaks counts, whatever the element's verdict
            if in_leaks:
                found.append(trap["id"])
            else:
                missed.append(f"{trap['id']}: no process_leaks leak contains {wanted(trap)}")
            continue
        if ok or in_leaks:
            found.append(trap["id"])
        elif not hits:
            missed.append(f"{trap['id']}: no element for {trap['path']}"
                          + (f" nor leak containing {wanted(trap)}" if has_leak_spec else ""))
        else:
            got = ", ".join(f"{e.get('verdict')}/{e.get('priority')}" for e in hits)
            wrong.append(f"{trap['id']}: {trap['path']} → {got}, expected {'/'.join(trap['verdicts'])} "
                         f"{'/'.join(trap.get('priorities') or ['*'])}"
                         + (f" or a leak containing {wanted(trap)}" if has_leak_spec else ""))
    sane_flagged = []
    for sane in expected.get("sane", []):
        for e in _elements_for(audit, sane["path"], own_only=True):
            if e.get("verdict") not in sane["verdicts"]:
                sane_flagged.append(f"{sane['id']}: {sane['path']} flagged {e.get('verdict')}, expected {'/'.join(sane['verdicts'])}")
    meta = audit.get("audit") or {}
    global_problems = []
    cut = (meta.get("cut_the_agent_test") or {}).get("passed")
    if "cut_the_agent_passed" in expected and cut != expected["cut_the_agent_passed"]:
        global_problems.append(f"\"cut the agent\" test: {cut}, expected {expected['cut_the_agent_passed']}")
    if "max_health_score" in expected and (meta.get("health_score") or 0) > expected["max_health_score"]:
        global_problems.append(f"score {meta.get('health_score')} > expected maximum {expected['max_health_score']}")
    p1 = sum(1 for e in audit.get("elements") or [] if e.get("priority") == "P1")
    if "min_p1" in expected and p1 < expected["min_p1"]:
        global_problems.append(f"{p1} P1 found, at least {expected['min_p1']} expected")
    guarded = json.dumps(audit.get("guarded_rules") or [], ensure_ascii=False).lower()
    for k in expected.get("guarded_rule_keywords", []):          # words, fragile to the language
        if k.lower() not in guarded:
            global_problems.append(f"guarded_rules does not mention \"{k}\"")
    for path in expected.get("guarded_rules_paths", []):          # paths, robust
        if path.lower() not in " ".join((g.get("guarded_by") or "").lower() for g in audit.get("guarded_rules") or []):
            global_problems.append(f"guarded_rules does not cite the guardrail {path}")
    for lie in expected.get("forbidden_guarded_paths", []):         # lying guardrail taken at its word
        # {"path": "check-i18n.mjs", "rule_keywords": ["t()"]}: penalised only if this path is
        # attributed to that very rule; the same script may legitimately guard another rule.
        path = (lie["path"] if isinstance(lie, dict) else lie).lower()
        words = [w.lower() for w in (lie.get("rule_keywords", []) if isinstance(lie, dict) else [])]
        for g in audit.get("guarded_rules") or []:
            if path in (g.get("guarded_by") or "").lower() and (not words or any(w in (g.get("rule") or "").lower() for w in words)):
                sane_flagged.append(f"guarded_rules attributes {path} to \"{(g.get('rule') or '')[:60]}\", which it does not verify")
    # A rule nothing verifies: calling it guarded is false whatever guardrail is invoked
    # ("enforced by: the review" cites no path and used to pass).
    for g in audit.get("guarded_rules") or []:
        rule = g.get("rule") or ""
        if expected.get("no_guard_exists"):
            sane_flagged.append(f"guarded_rules declares \"{rule[:60]}\" guarded: this repository has no guardrail that blocks")
        for never in expected.get("never_guarded", []):
            if _matches(rule, never):
                sane_flagged.append(f"guarded_rules declares \"{rule[:60]}\" guarded by {g.get('guarded_by')}: nothing verifies it ({never['what']})")
    # "Everything is a leak" bias: style conventions in process_leaks
    for k in expected.get("forbidden_leak_keywords", []):
        if k.lower() in leaks_text:
            sane_flagged.append(f"process_leaks contains \"{k}\": a style convention is not a process leak")
    # Removals: the instruction lines the audit proposes to remove, with their reason.
    removals = audit.get("removals") or []
    removal_text = lambda r: " ".join([str(r.get(k) or "") for k in ("text", "path")]  # noqa: E731
                                      + [_cited_line(repo, r.get("path"), r.get("line"))]).lower()
    for want in expected.get("removals", []):
        hits = [r for r in removals if any(k.lower() in removal_text(r) for k in want["any_of"])]
        good = [r for r in hits if r.get("reason") in want["reasons"]]
        if good and want.get("ask_owner") and not any(r.get("ask_owner") for r in good):
            wrong.append(f"{want['id']}: removal proposed without a question to the owner, though only they know whether it is outdated")
        elif good:
            found.append(want["id"])
        elif hits:
            got = ", ".join(str(r.get("reason")) for r in hits)
            wrong.append(f"{want['id']}: removal with reason {got}, expected {'/'.join(want['reasons'])}")
        else:
            missed.append(f"{want['id']}: no removal proposed for a line containing {want['any_of']}")
    for keep in expected.get("must_keep", []):                  # the line worth gold, drowned in the noise
        for r in removals:
            if any(k.lower() in (r.get("text") or "").lower() for k in keep["any_of"]):
                sane_flagged.append(f"{keep['id']}: removal proposed for a line to keep \"{(r.get('text') or '')[:60]}\"")
    total = len(expected.get("traps", [])) + len(expected.get("removals", []))
    return {"found": found, "missed": missed, "wrong": wrong, "sane_flagged": sane_flagged,
            "global": global_problems, "score": f"{len(found)}/{total}",
            "ok": not (missed or wrong or sane_flagged or global_problems)}


WORD_RE = re.compile(r"\w+")
COPIED_RUN = 4     # consecutive words shared with an original line: from there on, the line is copied
# What says that a thing is no longer there. A list of phrasings depends on the language: it only serves to
# excuse, never to accuse. A phrasing missing from here leaves the line counted, as before.
# French and English: the fixtures and the agents' outputs are in either language.
GONE_MARKERS = ("n'existe", "n’existe", "inexistant", "retiré", "supprimé", "abandonn", "périmé", "obsolète",
                "n'est plus", "n’est plus", "plus installé", "does not exist", "doesn't exist", "doesn’t exist",
                "no longer", "removed", "deleted", "obsolete", "abandoned", "outdated", "stale")
TEXT_SKIP_DIRS = {".git", "node_modules", ".venv", "__pycache__"}


def _repo_texts(repo: str) -> dict[str, str]:
    """The text of each readable file of a repository, lowercased, by relative path."""
    texts: dict[str, str] = {}
    for root, dirs, files in os.walk(repo):
        dirs[:] = [d for d in dirs if d not in TEXT_SKIP_DIRS]
        for name in files:
            path = os.path.join(root, name)
            try:
                if os.path.getsize(path) > 1_000_000:
                    continue
                with open(path, encoding="utf-8", errors="ignore") as fh:
                    texts[os.path.relpath(path, repo).replace(os.sep, "/")] = fh.read().lower()
            except OSError:
                continue
    return texts


def _shares_run(a: list[str], b: list[str], need: int) -> bool:
    grams = {tuple(b[i:i + need]) for i in range(len(b) - need + 1)}
    return any(tuple(a[i:i + need]) in grams for i in range(len(a) - need + 1))


def _excerpt(line: str, word: str, around: int = 70) -> str:
    at = line.lower().find(word.lower())
    start, end = max(0, at - around), min(len(line), at + len(word) + around)
    return ("… " if start else "") + line[start:end].strip() + (" …" if end < len(line) else "")


def noise_hits(corpus: dict[str, str], noise: dict, origin: dict[str, str] | None) -> tuple[dict[str, list[str]], list[str]]:
    """Where a noise is written (word → files), and the passages that only cite it.

    By default every word found counts. A `mention_ok` entry holds a repository identifier that a
    healthy rule may have to name in order to refute it ("the README announces `make e2e`, which no
    longer exists"): the line is then only a citation if it says the thing is no longer there
    (`GONE_MARKERS`) **and** does not take up an original line that holds the word (`COPIED_RUN` words
    in a row in common). Without the original repository, nothing says whether the line is copied: everything counts."""
    written: dict[str, list[str]] = {}
    cited: list[str] = []
    lenient = bool(noise.get("mention_ok")) and origin is not None
    for word in noise["any_of"]:
        low = word.lower()
        sources = [WORD_RE.findall(line) for text in (origin or {}).values() for line in text.splitlines()
                   if low in line] if lenient else []
        need = max(COPIED_RUN, len(WORD_RE.findall(low)) + 2)
        for path, text in corpus.items():
            for line in text.splitlines():
                if low not in line.lower():
                    continue
                words = WORD_RE.findall(line.lower())
                if (lenient and any(m in line.lower() for m in GONE_MARKERS)
                        and not any(_shares_run(words, src, need) for src in sources)):
                    quote = f"{word}: \"{_excerpt(line.strip(), word)}\""
                    if quote not in cited:
                        cited.append(quote)
                elif path not in written.setdefault(word, []):
                    written[word].append(path)
    return written, cited


def check_init(result_dir: str, expected: dict, today: date | None = None, base: str | None = None,
               report: str | None = None) -> dict[str, Any]:
    """Grades what a harness-init wrote in `result_dir` against the `init` block of expected.json:
    level reached, non-discoverable facts surfaced (`must_surface`), noise copied (`must_not_write`),
    real guardrails cited (`guards_cited`), lying guardrails believed (`forbidden_guards`), references
    without a target, material of later levels laid too early (`only_level_material`), and a healthy
    file rewritten for no reason (`min_similarity`). `base` is the fixture's repository as it was before
    the step: it serves when `result_dir` holds only the instruction files, and to tell whether a
    line copies the original noise or only cites it (`noise_hits`)."""
    state = maturity.evaluate(facts.collect(result_dir, today=today))
    corpus = facts.instruction_corpus(result_dir)
    text = "\n".join(corpus.values()).lower()
    rules = [r for t in corpus.values() for r in parse_rules(t)]
    guarded = [r.lower() for r in rules if facts.GUARDED_RE.search(r) and not facts.UNGUARDED_RE.search(r)]
    problems, surfaced, mentions = [], [], []
    level = state["level"]["reached"]
    if level < expected.get("min_level", 1):
        failing = [c["id"] for l in state["levels"] if l["level"] <= expected.get("min_level", 1)
                   for c in l["checks"] if not c["passed"]]
        problems.append(f"level {level} < expected {expected.get('min_level', 1)}; failing: {', '.join(failing)}")
    for fact in expected.get("must_surface", []):
        if any(k.lower() in text for k in fact["any_of"]):
            surfaced.append(fact["id"])
        else:
            problems.append(f"{fact['id']} not surfaced: {fact['what']} (none of {fact['any_of']})")
    origin = _repo_texts(base) if base else None
    for noise in expected.get("must_not_write", []):
        written, cited = noise_hits(corpus, noise, origin)
        if written:
            where = sorted({p for paths in written.values() for p in paths})
            problems.append(f"{noise['id']} wrongly written: {noise['what']} ({', '.join(written)} in {', '.join(where)})")
        mentions += [f"{noise['id']} cited, not counted · {quote}" for quote in cited]
    for path in expected.get("guards_cited", []):
        if not any(path.lower() in r for r in guarded):
            problems.append(f"guardrail {path} cited by no \"Enforced by\" rule")
    for lie in expected.get("forbidden_guards", []):
        for r in guarded:
            after = facts.GUARDED_RE.split(r, maxsplit=1)[-1]      # what follows "Enforced by:" (or "Vérifiée par :")
            if lie["path"].lower() in after and any(w.lower() in r for w in lie["rule_keywords"]):
                problems.append(f"lying guardrail believed: \"{r[:90]}\" relies on {lie['path']}")
    for r in guarded:                                             # enforced by anything at all: false
        if expected.get("no_guard_exists"):
            problems.append(f"rule said to be enforced in a repository without a guardrail that blocks: \"{r[:90]}\"")
        for never in expected.get("never_guarded", []):
            if _matches(r, never):
                problems.append(f"rule said to be enforced though nothing verifies it ({never['what']}): \"{r[:90]}\"")
    for rest in expected.get("must_not_remain", []):              # the side notes: gone, or reduced
        text_ = facts._read(os.path.join(result_dir, rest["path"]))
        if text_ is None:
            continue
        lines = len(text_.splitlines())
        hits = [k for k in rest.get("any_of", []) if k.lower() in text_.lower()]
        if hits or ("max_lines" in rest and lines > rest["max_lines"]):
            problems.append(f"{rest['path']} left as it was: {rest['what']}"
                            + (f" ({', '.join(hits)})" if hits else f" ({lines} lines, {rest['max_lines']} at most)"))
    if report is not None:                                        # the report handed to the owner
        low = report.lower()
        for want in expected.get("report_must_mention", []):
            if not any(k.lower() in low for k in want["any_of"]):
                problems.append(f"report: says nothing about {want['what']} (none of {want['any_of']})")
        for never in expected.get("report_must_not_mention", []):
            hits = [k for k in never["any_of"] if k.lower() in low]
            if hits:
                problems.append(f"report: contains {never['what']}")
    for ref in state["dangling"]:                                 # a step does not promise the next step
        if ref["kind"] == "guard" and base and facts.cited_path_exists(base, ref["ref"]):
            continue        # `result_dir` holds only the instructions: the guardrail lives in the fixture's repository
        if ref["kind"] == "job":
            problems.append(f"reference without a target: job `{ref['ref']}` line {ref['line']} (cited, missing from the workflows)")
            continue
        problems.append(f"reference without a target: `{ref['ref']}` line {ref['line']} "
                        + ("(contract cited, no SKILL.md)" if ref["kind"] == "contract" else "(guardrail cited, path not found)"))
    if expected.get("only_level_material"):
        src = state["facts"]["instructions"]["source"]
        extra = [name for name, present in (("Maintenance section", src.get("has_maintenance_section")),
                                            ("harvest marker", src.get("harvest_marker")),
                                            ("Working process section", src.get("has_process_section"))) if present]
        if extra and level <= expected.get("min_level", 1):
            problems.append("material of later levels laid at step 1: " + ", ".join(extra))
    for keep in expected.get("min_similarity", []):               # zeal: rewriting what was healthy
        original = facts._read(os.path.join(base or result_dir, keep["path"]))
        written = facts._read(os.path.join(result_dir, keep["path"]))
        if original is None or written is None:
            problems.append(f"{keep['path']}: starting file or handed-in file not found")
            continue
        ratio = difflib.SequenceMatcher(None, original.splitlines(), written.splitlines()).ratio()
        if ratio < keep["ratio"]:
            problems.append(f"{keep['path']} rewritten: {ratio:.2f} similarity with the starting file, "
                            f"at least {keep['ratio']} expected from an already healthy harness")
    total = len(expected.get("must_surface", []))
    return {"level": level, "surfaced": surfaced, "problems": problems, "mentions": mentions,
            "score": f"{len(surfaced)}/{total}", "files": sorted(corpus), "ok": not problems}


# The checks that are only won with time: no step can flip them within a session; seeing them flip
# means an invented signal.
WAITS = maturity.WAITING
# The checks that are won by shares: one guarded rule per step, and the level flips only at half.
# A step that raises the share moves forward, even if nothing flips (2026-11-14).
SHARES = {"L3.guarded", "L3.justified"}
# What a report says when the target is already reached: the `harness status` phrase, French or English.
TARGET_REACHED = ("objectif atteint", "target reached")


def check_step(before: dict, after: dict, expected_init: dict, report: str, changed: list[str]) -> dict[str, Any]:
    """Grades a harness-step step, from the state measured before and after (`maturity.evaluate`).

    What is expected, whatever the repository:
    - target already reached: nothing changes, and the report says so (`TARGET_REACHED`);
    - otherwise one step, and only one: at least one check of a targeted level flips, all in the same
      level; a level that can only be won with time does not stop the next ones, if they are targeted;
    - nothing regresses, nothing is laid beyond the target level, no signal is invented;
    - the facts of step 1 remain, and no reference without a target appears."""
    def passed(state: dict) -> dict[str, tuple[int, bool]]:
        return {c["id"]: (l["level"], c["passed"]) for l in state["levels"] for c in l["checks"]}

    def values(state: dict) -> dict[str, Any]:
        return {c["id"]: c["value"] for l in state["levels"] for c in l["checks"]}
    b, a = passed(before), passed(after)
    target = after["target"]["level"]
    up = sorted(cid for cid in a if a[cid][1] and not b.get(cid, (0, False))[1])
    vb, va = values(before), values(after)
    gained = sorted(cid for cid in SHARES if cid in a and not a[cid][1]
                    and isinstance(va.get(cid), (int, float)) and isinstance(vb.get(cid), (int, float)) and va[cid] > vb[cid])
    down = sorted(cid for cid in a if b.get(cid, (0, False))[1] and not a[cid][1])
    problems: list[str] = []
    files = [f for f in changed if not f.startswith(".harness/")]
    if down:
        problems.append(f"regression: {', '.join(down)} passed before the step")
    if target is not None and before["level"]["reached"] >= target:
        if files:
            problems.append(f"target already reached, and the step still touched {', '.join(files[:5])}")
        if not any(phrase in (report or "").lower() for phrase in TARGET_REACHED):
            problems.append("target already reached: the report does not say so")
    else:
        in_scope = [cid for cid in up + gained if target is None or a[cid][0] <= target]
        levels = sorted({a[cid][0] for cid in in_scope})
        open_ = [cid for cid, (lvl, ok) in b.items() if not ok and cid not in WAITS and (target is None or lvl <= target)]
        if not in_scope and open_:
            problems.append(f"no targeted check flipped, though {', '.join(sorted(open_)[:4])} remained to be won")
        if len(levels) > 1:
            problems.append(f"more than one step: checks of {len(levels)} levels flipped ({', '.join(in_scope)})")
    beyond = [cid for cid in up if target is not None and a[cid][0] > target]
    if beyond:
        problems.append(f"material laid beyond the target level: {', '.join(beyond)}")
    faked = [cid for cid in up if cid in WAITS]
    if faked:
        problems.append(f"invented signal: {', '.join(faked)} can only be won with real reviews")
    corpus = "\n".join(facts.instruction_corpus(after["repo"]).values()).lower()
    for fact in expected_init.get("must_surface", []):
        if not any(k.lower() in corpus for k in fact["any_of"]):
            problems.append(f"fact lost: {fact['id']}, {fact['what']}")
    known = {(d["kind"], d["ref"]) for d in before.get("dangling") or []}
    for d in after.get("dangling") or []:
        if (d["kind"], d["ref"]) not in known:
            problems.append(f"reference without a target added: `{d['ref']}` line {d['line']}")
    return {"before": before["level"]["reached"], "after": after["level"]["reached"], "target": target,
            "flipped": up, "gained": [f"{cid} {vb[cid]} → {va[cid]}" for cid in gained],
            "problems": problems, "files": files, "ok": not problems}


HINT_RE = re.compile(r"[a-z0-9_][a-z0-9_./-]{3,}")
HINT_STOP = {"true", "false", "null", "none"}


def hint_tokens(word: str) -> list[str]:
    """The pieces of a fact that would be enough to guess it: its identifiers taken one by one, except the
    whole fact, already searched for, and the values every JSON file contains. `"deprecated": true` gives
    `deprecated`; `idempotency-replayed` gives nothing more than itself."""
    low = word.lower()
    return [t for t in dict.fromkeys(HINT_RE.findall(low)) if t not in HINT_STOP and t != low]


INSTRUMENTATION = ["AGENTS.md", "CLAUDE.md", ".claude", ".cursor", ".agents", ".github/copilot-instructions.md", ".harness"]


def check_oral_facts(fixture_dir: str, expected: dict) -> list[str]:
    """A sample project holds at least one fact written nowhere else than in its instructions, or
    told by its owner. It is the only place where a harness can show a gain: a fact filed in an ADR,
    a careful agent finds it on its own (campaign of 2026-11-11). For each fact marked
    `only_in_instructions`: its words are read in no other file of the repository, nor any of their
    pieces (`hint_tokens`: a validator that lists `deprecated` leads to `"deprecated": true`), it can be
    learned somewhere (the repository's instructions or `owner.md`), a task check exercises it
    (`exercises`), and a tempted solution fails that check. A fixture without tasks is not concerned."""
    tasks_dir = os.path.join(fixture_dir, "tasks")
    if not os.path.isdir(tasks_dir):
        return []
    oral = [f for f in expected.get("init", {}).get("must_surface", []) if f.get("only_in_instructions")]
    if not oral:
        return ["no fact marked `only_in_instructions`: everything this project teaches is read in its documentation"]
    elsewhere: dict[str, str] = {}          # text of the files that are not instructions
    instructions = ""
    for rel, text in _repo_texts(os.path.join(fixture_dir, "repo")).items():
        if os.path.basename(rel) in ("AGENTS.md", "CLAUDE.md"):
            instructions += text
        else:
            elsewhere[rel] = text
    owner = (facts._read(os.path.join(fixture_dir, "owner.md")) or "").lower()
    owner += (facts._read(os.path.join(fixture_dir, "owner.json")) or "").lower()     # the simulated owner
    checks = []                             # (task, check)
    tempted_fails: set[str] = set()
    for task_id in sorted(os.listdir(tasks_dir)):
        path = os.path.join(tasks_dir, task_id, "task.json")
        if os.path.isfile(path):
            with open(path, encoding="utf-8") as fh:
                task = json.load(fh)
            checks += [(task_id, c) for c in task.get("checks", [])]
            tempted_fails |= {cid for t in task.get("tempted", []) for cid in t.get("fails", [])}
    problems = []
    for fact in oral:
        words = [w.lower() for w in fact["only_in_instructions"]]
        for word in words:
            where = sorted(p for p, text in elsewhere.items() if word in text)
            if where:
                problems.append(f"{fact['id']}: \"{word}\" is also read in {', '.join(where[:3])}: the fact is discoverable")
                continue
            for token in hint_tokens(word):     # a piece of the fact is enough to lead to it (2026-11-13)
                where = sorted(p for p, text in elsewhere.items() if re.search(r"(?<![\w-])" + re.escape(token) + r"(?![\w-])", text))
                if where:
                    problems.append(f"{fact['id']}: \"{token}\", a piece of the fact, is read in {', '.join(where[:3])}: "
                                    "a hint that leads to it, the fact is discoverable")
        if not any(w in instructions or w in owner for w in words):
            problems.append(f"{fact['id']}: none of {words} in the repository's instructions nor in owner.md: nowhere to learn it")
        exercising = [c["id"] for _, c in checks if c.get("exercises") == fact["id"]]
        if not exercising:
            problems.append(f"{fact['id']}: no task check exercises it (`exercises`)")
        elif not any(cid in tempted_fails for cid in exercising):
            problems.append(f"{fact['id']}: no tempted solution fails {exercising}: nothing proves that the check separates")
    return problems


COPY_IGNORE = shutil.ignore_patterns("node_modules", "__pycache__", ".venv", "*.pyc", ".pytest_cache")
# The README line of a fixture that gives the bench away, French or English:
# "Dépôt **synthétique** : une fixture du projet harness-ai" / "**Synthetic** repository: a fixture of harness-ai".
BENCH_LINE_RE = re.compile(r"harness-ai|d[ée]p[ôo]t \*\*synth[ée]tique\*\*|pièges d'instrumentation"
                           r"|\*\*synthetic\*\* repo|instrumentation traps", re.I)


def commit_all(dest: str, branch: str) -> None:
    """Turns `dest` into a git repository with one commit: the starting point of a run."""
    env = {**os.environ, "GIT_AUTHOR_NAME": "owner", "GIT_AUTHOR_EMAIL": "owner@example.test",
           "GIT_COMMITTER_NAME": "owner", "GIT_COMMITTER_EMAIL": "owner@example.test"}
    for args in (["init", "-q", "-b", branch], ["add", "-A"], ["commit", "-q", "-m", "import"]):
        subprocess.run(["git", "-C", dest, *args], check=True, env=env, capture_output=True)


def bare_copy(fixture_dir: str, dest: str, branch: str = "develop", keep_instrumentation: bool = False,
              commit: bool = True) -> list[str]:
    """Copies a fixture's `repo/` into `dest` without its AI instrumentation, and turns it into a git
    repository with one commit: the "bare" repository on which harness-init is evaluated as a blind run.
    What is not versioned (node_modules, caches) is not copied. Returns the list of what was removed."""
    src = os.path.join(fixture_dir, "repo")
    if os.path.exists(dest) and os.listdir(dest):
        raise SystemExit(f"{dest} exists and is not empty")
    shutil.copytree(src, dest, dirs_exist_ok=True, ignore=COPY_IGNORE)
    removed = []
    for rel in [] if keep_instrumentation else INSTRUMENTATION:
        path = os.path.join(dest, rel)
        if os.path.isdir(path):
            shutil.rmtree(path)
            removed.append(rel + "/")
        elif os.path.exists(path):
            os.remove(path)
            removed.append(rel)
    if not keep_instrumentation:                 # subfolder notes are instrumentation too
        for root, _dirs, files in os.walk(dest):
            for name in files:
                rel = os.path.relpath(os.path.join(root, name), dest).replace(os.sep, "/")
                if name in ("AGENTS.md", "CLAUDE.md") and "/" in rel:
                    os.remove(os.path.join(root, name))
                    removed.append(rel)
    readme = os.path.join(dest, "README.md")
    if os.path.exists(readme):
        with open(readme, encoding="utf-8") as fh:
            # The line that gives the bench away, in French or English. "fixture" alone is also a word of
            # Django and pytest.
            lines = [l for l in fh.read().splitlines() if not BENCH_LINE_RE.search(l)]
        with open(readme, "w", encoding="utf-8") as fh:
            fh.write("\n".join(lines).rstrip() + "\n")
    if commit:
        commit_all(dest, branch)
    return removed


def build_parser(parser: argparse.ArgumentParser | None = None) -> argparse.ArgumentParser:
    p = parser or argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="fixture_command", required=True)
    c = sub.add_parser("check", help="compares a fixture with expected.json")
    c.add_argument("name", help="name of the fixture (folder of fixtures/repos) or path")
    c.add_argument("--audit", help="audit JSON to grade against the traps")
    c.add_argument("--init", help="repository produced by a harness-init, to grade against the init block")
    c.add_argument("--report", help="with --init: the report handed in by the agent, graded too")
    c.add_argument("--today", help="YYYY-MM-DD for a reproducible measurement")
    b = sub.add_parser("bare", help="copy of a fixture without AI instrumentation, to evaluate harness-init")
    b.add_argument("name", help="name of the fixture or path")
    b.add_argument("dest", help="destination folder (created, must be empty)")
    b.add_argument("--branch", default="develop")
    return p


def known_fixtures() -> list[str]:
    """The names accepted by `fixture check` and `fixture bare`."""
    try:
        names = os.listdir(FIXTURES_ROOT)
    except OSError:
        return []
    return sorted(n for n in names if os.path.isfile(os.path.join(FIXTURES_ROOT, n, "expected.json")))


def _usage_problem(args: argparse.Namespace, fixture_dir: str) -> str | None:
    """One sentence when the command line names something that does not exist, else None."""
    if not os.path.isdir(fixture_dir):
        return f"unknown fixture {args.name}; known fixtures: {', '.join(known_fixtures()) or 'none'}"
    if args.fixture_command == "bare":
        return None
    if not os.path.isfile(os.path.join(fixture_dir, "expected.json")):
        return f"{args.name} is not a fixture: it has no expected.json"
    if args.audit and not os.path.isfile(args.audit):
        return f"audit file not found: {args.audit}; this file is produced by a harness-audit run"
    return None


def main(argv: list[str] | None = None, args: argparse.Namespace | None = None) -> int:
    if args is None:
        args = build_parser().parse_args(argv)
    fixture_dir = args.name if os.path.isdir(args.name) else os.path.join(FIXTURES_ROOT, args.name)
    problem = _usage_problem(args, fixture_dir)
    if problem:
        print(f"harness fixture {args.fixture_command}: {problem}", file=sys.stderr)
        return 2
    if args.fixture_command == "bare":
        removed = bare_copy(fixture_dir, args.dest, args.branch)
        print(f"bare repository in {args.dest} (branch {args.branch}); removed: {', '.join(removed) or 'nothing'}")
        return 0
    with open(os.path.join(fixture_dir, "expected.json"), encoding="utf-8") as fh:
        expected = json.load(fh)
    today = date.fromisoformat(args.today) if args.today else None
    problems = check_status(fixture_dir, expected["status"], today)
    print(f"# Fixture {expected.get('fixture', args.name)}")
    print("## status: " + ("ok" if not problems else f"{len(problems)} problem(s)"))
    for p in problems:
        print(f"- {p}")
    ok = not problems
    if os.path.isdir(os.path.join(fixture_dir, "tasks")):
        oral = check_oral_facts(fixture_dir, expected)
        print("## facts written nowhere else: " + ("ok" if not oral else f"{len(oral)} problem(s)"))
        for p in oral:
            print(f"- {p}")
        ok = ok and not oral
    if os.path.isfile(os.path.join(fixture_dir, "owner.json")):
        from . import owner
        posed = owner.check(fixture_dir, expected)
        print("## simulated owner: " + ("ok" if not posed else f"{len(posed)} problem(s)"))
        for p in posed:
            print(f"- {p}")
        ok = ok and not posed
    if args.audit:
        with open(args.audit, encoding="utf-8") as fh:
            audit = json.load(fh)
        result = check_audit(audit, expected.get("audit", {}), repo=os.path.join(fixture_dir, "repo"))
        print(f"## audit: {result['score']} traps and removals found" + (" · ok" if result["ok"] else ""))
        for key, title in (("missed", "Missed"), ("wrong", "Wrong verdict"), ("sane_flagged", "Healthy items flagged"),
                           ("global", "Global")):
            if result[key]:
                print(f"### {title}")
                for line in result[key]:
                    print(f"- {line}")
        ok = ok and result["ok"]
    if args.init:
        report = facts._read(args.report) if args.report else None
        if args.report and report is None:
            raise SystemExit(f"report not found: {args.report}")
        result = check_init(args.init, expected.get("init", {}), today, base=os.path.join(fixture_dir, "repo"), report=report)
        if report is None and any(k.startswith("report_") for k in expected.get("init", {})):
            print("(report not graded: pass --report <file>)")
        print(f"## init: level {result['level']} · {result['score']} facts surfaced"
              + (" · ok" if result["ok"] else f" · {len(result['problems'])} problem(s)"))
        for line in result["problems"]:
            print(f"- {line}")
        if result["mentions"]:
            print("### Cited without being copied: not counted, to review")
            for line in result["mentions"]:
                print(f"- {line}")
        ok = ok and result["ok"]
    return 0 if ok else 1
