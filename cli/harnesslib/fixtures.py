"""Sous-commande `fixture check` : compare ce que `status` mesure sur une fixture
à `expected.json`, et, si un JSON d'audit est fourni, compare les verdicts aux
pièges attendus. Sortie : un rapport lisible et un code de retour 0 si tout
concorde, 1 sinon."""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date
from typing import Any

from . import facts, maturity

FIXTURES_ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                             "fixtures", "repos")


def check_status(fixture_dir: str, expected: dict, today: date | None = None) -> list[str]:
    """Écarts entre l'état mesuré et le bloc `status` d'expected.json."""
    state = maturity.evaluate(facts.collect(os.path.join(fixture_dir, "repo"), today=today))
    checks = {c["id"]: c["passed"] for l in state["levels"] for c in l["checks"]}
    problems = []
    if state["level"]["reached"] != expected["level_reached"]:
        problems.append(f"palier {state['level']['reached']} ≠ attendu {expected['level_reached']}")
    if state["facts"]["instructions"]["source"]["path"] != expected.get("source_path"):
        problems.append(f"source {state['facts']['instructions']['source']['path']} ≠ attendu {expected.get('source_path')}")
    for cid in expected.get("failing_checks", []):
        if checks.get(cid, None) is not False:
            problems.append(f"{cid} devrait échouer (état : {checks.get(cid)})")
    for cid in expected.get("passing_checks", []):
        if checks.get(cid, None) is not True:
            problems.append(f"{cid} devrait passer (état : {checks.get(cid)})")
    tools = sorted(state["facts"]["guardrails"]["tools"])
    if "guardrail_tools" in expected and tools != sorted(expected["guardrail_tools"]):
        problems.append(f"garde-fous {tools} ≠ attendus {sorted(expected['guardrail_tools'])}")
    if "contracts" in expected and state["facts"]["contracts"]["count"] != expected["contracts"]:
        problems.append(f"contrats {state['facts']['contracts']['count']} ≠ attendu {expected['contracts']}")
    return problems


def _elements_for(audit: dict, path: str) -> list[dict]:
    """Les éléments dont c'est le chemin ; à défaut, ceux qui le citent en preuve
    (un rapport peut ranger un fichier sous un élément plus large)."""
    path = path.lower()
    elements = audit.get("elements") or []
    own = [e for e in elements if path in (e.get("path") or "").lower()]
    if own:
        return own
    return [e for e in elements if any(path in (ev or "").lower() for ev in e.get("evidence") or [])]


def check_audit(audit: dict, expected: dict) -> dict[str, Any]:
    """Score d'un audit contre les pièges attendus : trouvés, manqués, faux, sains signalés."""
    found, missed, wrong = [], [], []
    leaks_text = " ".join(json.dumps(l, ensure_ascii=False).lower() for l in audit.get("process_leaks") or [])
    for trap in expected.get("traps", []):
        # Un piège est trouvé soit par un élément au bon verdict sur le bon chemin, soit, pour une règle
        # racontée, par sa présence dans process_leaks (c'est là que le rapport range ces fuites).
        in_leaks = bool(trap.get("leak_keywords")) and all(k.lower() in leaks_text for k in trap["leak_keywords"])
        hits = _elements_for(audit, trap["path"])
        ok = [e for e in hits if e.get("verdict") in trap["verdicts"]
              and (not trap.get("priorities") or e.get("priority") in trap["priorities"])]
        if trap.get("require_leak"):
            # le piège est une fuite : seul process_leaks compte, quel que soit le verdict de l'élément
            if in_leaks:
                found.append(trap["id"])
            else:
                missed.append(f"{trap['id']} : aucune fuite contenant {trap['leak_keywords']} dans process_leaks")
            continue
        if ok or in_leaks:
            found.append(trap["id"])
        elif not hits:
            missed.append(f"{trap['id']} : aucun élément pour {trap['path']}"
                          + (f" ni fuite contenant {trap['leak_keywords']}" if trap.get("leak_keywords") else ""))
        else:
            got = ", ".join(f"{e.get('verdict')}/{e.get('priority')}" for e in hits)
            wrong.append(f"{trap['id']} : {trap['path']} → {got}, attendu {'/'.join(trap['verdicts'])} "
                         f"{'/'.join(trap.get('priorities') or ['*'])}"
                         + (f" ou une fuite contenant {trap['leak_keywords']}" if trap.get("leak_keywords") else ""))
    sane_flagged = []
    for sane in expected.get("sane", []):
        for e in _elements_for(audit, sane["path"]):
            if e.get("verdict") not in sane["verdicts"]:
                sane_flagged.append(f"{sane['id']} : {sane['path']} signalé {e.get('verdict')}, attendu {'/'.join(sane['verdicts'])}")
    meta = audit.get("audit") or {}
    global_problems = []
    cut = (meta.get("cut_the_agent_test") or {}).get("passed")
    if "cut_the_agent_passed" in expected and cut != expected["cut_the_agent_passed"]:
        global_problems.append(f"test « coupe l'agent » : {cut}, attendu {expected['cut_the_agent_passed']}")
    if "max_health_score" in expected and (meta.get("health_score") or 0) > expected["max_health_score"]:
        global_problems.append(f"score {meta.get('health_score')} > maximum attendu {expected['max_health_score']}")
    p1 = sum(1 for e in audit.get("elements") or [] if e.get("priority") == "P1")
    if "min_p1" in expected and p1 < expected["min_p1"]:
        global_problems.append(f"{p1} P1 trouvés, au moins {expected['min_p1']} attendus")
    guarded = json.dumps(audit.get("guarded_rules") or [], ensure_ascii=False).lower()
    for k in expected.get("guarded_rule_keywords", []):          # mots, fragiles à la langue
        if k.lower() not in guarded:
            global_problems.append(f"guarded_rules ne mentionne pas « {k} »")
    for path in expected.get("guarded_rules_paths", []):          # chemins, robustes
        if path.lower() not in " ".join((g.get("guarded_by") or "").lower() for g in audit.get("guarded_rules") or []):
            global_problems.append(f"guarded_rules ne cite pas le garde-fou {path}")
    for lie in expected.get("forbidden_guarded_paths", []):         # garde-fou mensonger cru sur parole
        # {"path": "check-i18n.mjs", "rule_keywords": ["t()"]} : pénalisé seulement si ce chemin est
        # attribué à cette règle-là ; le même script peut garder légitimement une autre règle.
        path = (lie["path"] if isinstance(lie, dict) else lie).lower()
        words = [w.lower() for w in (lie.get("rule_keywords", []) if isinstance(lie, dict) else [])]
        for g in audit.get("guarded_rules") or []:
            if path in (g.get("guarded_by") or "").lower() and (not words or any(w in (g.get("rule") or "").lower() for w in words)):
                sane_flagged.append(f"guarded_rules attribue {path} à « {(g.get('rule') or '')[:60]} », qu'il ne vérifie pas")
    # Biais « tout est une fuite » : des conventions de style dans process_leaks
    for k in expected.get("forbidden_leak_keywords", []):
        if k.lower() in leaks_text:
            sane_flagged.append(f"process_leaks contient « {k} » : une convention de style n'est pas une fuite de processus")
    total = len(expected.get("traps", []))
    return {"found": found, "missed": missed, "wrong": wrong, "sane_flagged": sane_flagged,
            "global": global_problems, "score": f"{len(found)}/{total}",
            "ok": not (missed or wrong or sane_flagged or global_problems)}


def build_parser(parser: argparse.ArgumentParser | None = None) -> argparse.ArgumentParser:
    p = parser or argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="fixture_command", required=True)
    c = sub.add_parser("check", help="compare une fixture à expected.json")
    c.add_argument("name", help="nom de la fixture (dossier de fixtures/repos) ou chemin")
    c.add_argument("--audit", help="JSON d'audit à noter contre les pièges")
    c.add_argument("--today", help="AAAA-MM-JJ pour une mesure reproductible")
    return p


def main(argv: list[str] | None = None, args: argparse.Namespace | None = None) -> int:
    if args is None:
        args = build_parser().parse_args(argv)
    fixture_dir = args.name if os.path.isdir(args.name) else os.path.join(FIXTURES_ROOT, args.name)
    with open(os.path.join(fixture_dir, "expected.json"), encoding="utf-8") as fh:
        expected = json.load(fh)
    today = date.fromisoformat(args.today) if args.today else None
    problems = check_status(fixture_dir, expected["status"], today)
    print(f"# Fixture {expected.get('fixture', args.name)}")
    print("## status : " + ("conforme" if not problems else f"{len(problems)} écart(s)"))
    for p in problems:
        print(f"- {p}")
    ok = not problems
    if args.audit:
        with open(args.audit, encoding="utf-8") as fh:
            audit = json.load(fh)
        result = check_audit(audit, expected.get("audit", {}))
        print(f"## audit : {result['score']} pièges trouvés" + (" · conforme" if result["ok"] else ""))
        for key, title in (("missed", "Manqués"), ("wrong", "Mauvais verdict"), ("sane_flagged", "Sains signalés"),
                           ("global", "Global")):
            if result[key]:
                print(f"### {title}")
                for line in result[key]:
                    print(f"- {line}")
        ok = ok and result["ok"]
    return 0 if ok else 1
