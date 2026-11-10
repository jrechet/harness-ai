"""Le modèle de maturité : cinq paliers, chacun gagné par des vérifications
mesurables sur les faits collectés par `facts.collect`. Un palier est atteint
quand toutes ses vérifications passent ; les paliers s'enchaînent (le palier n
suppose le palier n-1). Chaque vérification porte une action suivante, pour
que l'état dise toujours quoi faire ensuite.

Documentation lisible : docs/maturity.md. Les seuils sont ici, en constantes."""
from __future__ import annotations

from typing import Any, Callable

MAX_SOURCE_LINES = 60          # palier 1 : au-delà, c'est de la référence à déporter
MAX_MARKER_AGE_DAYS = 45       # palier 2 : un harvest doit avoir tourné récemment
MIN_GUARDED_RATIO = 0.5        # palier 3 : la moitié des règles vérifiées par un outil
MIN_JUSTIFIED_RATIO = 0.5      # palier 3 : la moitié des règles disent pourquoi

LEVELS = [
    (0, "Rien", "Aucun fichier d'instructions : l'agent part de zéro à chaque session."),
    (1, "Cadré", "Un AGENTS.md court, un mode explicite, des stubs : l'agent sait où il est."),
    (2, "Bouclé", "La boucle de retour tourne : les incidents deviennent des règles."),
    (3, "Vérifié", "Les règles obligatoires sont portées par des outils, pas par du texte."),
    (4, "Délégué", "Des tâches entières sont confiées à l'agent et reviennent propres."),
]

Check = dict[str, Any]


def _check(cid: str, label: str, passed: bool, value: Any, next_action: str) -> Check:
    return {"id": cid, "label": label, "passed": bool(passed), "value": value,
            "next_action": None if passed else next_action}


def _src(f: dict) -> dict:
    return f["instructions"]["source"]


def level1(f: dict) -> list[Check]:
    src = _src(f)
    files = f["instructions"]["files"]
    has_src = bool(src.get("path"))
    claude_ok = (not files["CLAUDE.md"]["exists"]) or files["CLAUDE.md"].get("is_stub") or src.get("path") == "CLAUDE.md"
    return [
        _check("L1.source", "Un fichier d'instructions existe (AGENTS.md)", has_src, src.get("path"),
               "Lancer harness-init pour créer AGENTS.md."),
        _check("L1.mode", "La ligne « Mode : délégation | assistance » est présente", bool(src.get("mode")), src.get("mode"),
               "Ajouter la ligne de mode en tête d'AGENTS.md ; harness-audit s'en sert pour son barème."),
        _check("L1.short", f"Le fichier chargé fait au plus {MAX_SOURCE_LINES} lignes",
               has_src and (src.get("lines") or 0) <= MAX_SOURCE_LINES, src.get("lines"),
               "Déporter la référence (commandes, architecture) dans des fichiers à la demande ou des skills."),
        _check("L1.single_source", "CLAUDE.md est un stub @AGENTS.md (ou absent)", has_src and claude_ok,
               files["CLAUDE.md"], "Réduire CLAUDE.md à `@AGENTS.md` et fusionner son contenu utile dans AGENTS.md."),
        _check("L1.forbidden", "Une section « Interdits » dit ce qu'un agent ne fait jamais",
               bool(src.get("has_forbidden_section")), src.get("has_forbidden_section"),
               "Ajouter la section Interdits : dossiers, secrets, actions prod, force push."),
    ]


def level2(f: dict) -> list[Check]:
    src = _src(f)
    h = f["harvest"]
    age = f["harvest_marker_age_days"]
    return [
        _check("L2.maintenance", "Une section Maintenance dit comment le fichier évolue",
               bool(src.get("has_maintenance_section")), src.get("has_maintenance_section"),
               "Ajouter la section Maintenance du template harness-init."),
        _check("L2.rule_convention", "La convention `rule:` en review est documentée",
               bool(src.get("mentions_rule_convention")), src.get("mentions_rule_convention"),
               "Documenter : un commentaire de review qui commence par `rule:` est une règle candidate."),
        _check("L2.marker_fresh", f"Un harvest a tourné depuis moins de {MAX_MARKER_AGE_DAYS} jours",
               age is not None and age <= MAX_MARKER_AGE_DAYS, age,
               "Lancer harness-harvest et fusionner sa PR, qui pose le marqueur."),
        _check("L2.signal", "Le dernier harvest a trouvé au moins un signal réel (S1–S4)",
               bool(h and h["real_signals"] > 0), h["real_signals"] if h else None,
               "Marquer les incidents en review avec `rule:` ; sans signal, la boucle ne tourne pas encore."),
    ]


def level3(f: dict) -> list[Check]:
    src = _src(f)
    a = f["audit"]
    total = src.get("rules_total") or 0
    guarded_ratio = (src.get("rules_guarded") or 0) / total if total else 0.0
    justified_ratio = (src.get("rules_justified") or 0) / total if total else 0.0
    return [
        _check("L3.ci", "Une CI existe (workflows ou .gitlab-ci.yml)", f["guardrails"]["has_ci"],
               f["guardrails"]["workflows"], "Sans CI, aucune règle ne peut être garantie : en poser une."),
        _check("L3.guarded", f"Au moins {int(MIN_GUARDED_RATIO*100)} % des règles sont « Vérifiée par » un outil",
               total > 0 and guarded_ratio >= MIN_GUARDED_RATIO, round(guarded_ratio, 2),
               "Pousser les règles racontées en L3 : lint custom, test d'architecture, check de PR."),
        _check("L3.justified", f"Au moins {int(MIN_JUSTIFIED_RATIO*100)} % des règles disent pourquoi",
               total > 0 and justified_ratio >= MIN_JUSTIFIED_RATIO, round(justified_ratio, 2),
               "Ajouter « Pourquoi : » ou le lien de l'incident à chaque règle."),
        _check("L3.audit", "Un harness-audit existe et n'a aucun P1 ouvert",
               bool(a) and a["priorities"].get("P1", 0) == 0, a["priorities"] if a else None,
               "Lancer harness-audit, écrire son JSON dans .harness/audit.json, traiter les P1."),
    ]


def level4(f: dict) -> list[Check]:
    src = _src(f)
    h = f["harvest"]
    a = f["audit"]
    return [
        _check("L4.mode", "Le mode est délégation", src.get("mode") == "delegation", src.get("mode"),
               "Passer en délégation avec harness-init quand les garde-fous sont là."),
        _check("L4.process", "Une section « Processus de travail » cadre l'agent",
               bool(src.get("has_process_section")), src.get("has_process_section"),
               "Ajouter : quand s'arrêter et demander, critère de fini, CI rouge, test flaky."),
        _check("L4.contracts", "Au moins un contrat de tâche existe et est référencé",
               any(c["referenced"] for c in f["contracts"]["items"]), f["contracts"]["count"],
               "Créer .claude/skills/<tâche>/SKILL.md pour la première tâche déléguée et le citer dans AGENTS.md."),
        _check("L4.clean_prs", "Le dernier harvest voit des PRs d'agent sans correction après coup",
               bool(h and (h["agent_prs"] or 0) > 0 and h["corrections_on_agent_prs"] == 0),
               {"agent_prs": h["agent_prs"], "S2": h["corrections_on_agent_prs"]} if h else None,
               "Chaque correction après coup (S2) est une règle ou un garde-fou manquant : les traiter."),
        _check("L4.cut_the_agent", "Le test « coupe l'agent » de l'audit passe",
               bool(a and a["cut_the_agent_passed"]), a["cut_the_agent_passed"] if a else None,
               "Pousser en L3/L4 les étapes qui n'existent que dans des prompts."),
    ]


LEVEL_CHECKS: dict[int, Callable[[dict], list[Check]]] = {1: level1, 2: level2, 3: level3, 4: level4}


def layer_view(f: dict) -> dict[str, Any]:
    """La vue par couche L1–L4, depuis le dernier audit ; sinon des pointeurs."""
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
        "hint": "Lancer harness-audit pour une vue par couche mesurée.",
    }


def evaluate(f: dict) -> dict[str, Any]:
    target = (f.get("config") or {}).get("target_level")      # None : le propriétaire n'a rien déclaré
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
    # Un palier est un endroit où l'on peut rester : au-delà du palier visé, on ne propose rien.
    pushing = next_level is not None and next_level["in_scope"]
    next_actions = [c["next_action"] for c in (next_level["checks"] if pushing else []) if not c["passed"]]
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
        "dangling": f.get("dangling") or [],
        "facts": f,
    }


def render_markdown(state: dict) -> str:
    lvl = state["level"]
    target = state.get("target") or {"level": None, "reached": False}
    if target["level"] is None:
        goal = "aucun palier visé : `harness target <n>` dit où tu veux t'arrêter"
    elif target["reached"]:
        goal = f"visé : {target['level']} · **objectif atteint**"
    else:
        goal = f"visé : {target['level']} · {target['name']}"
    out = [f"# État du harness — {state['repo']}", "",
           f"**Palier atteint** : {lvl['reached']} · {lvl['name']} · {goal}",
           f"**Date** : {state['date']}", ""]
    for l in state["levels"]:
        if not l["level"]:
            continue
        if not l.get("in_scope", True):
            out.append(f"## · Palier {l['level']} — {l['name']} (hors objectif)")
            out.append("")
            continue
        mark = "✓" if l["achieved"] else "·"
        out.append(f"## {mark} Palier {l['level']} — {l['name']} ({l['passed_checks']}/{l['total_checks']})")
        out.append(f"_{l['summary']}_")
        for c in l["checks"]:
            out.append(f"- [{'x' if c['passed'] else ' '}] {c['label']}" + ("" if c["passed"] else f" → {c['next_action']}"))
        out.append("")
    if state.get("dangling"):
        out.append("## Références sans cible")
        for d in state["dangling"]:
            what = {"contract": "contrat cité, SKILL.md introuvable", "job": "job de CI cité, absent des workflows"}.get(
                d["kind"], "garde-fou cité, chemin introuvable")
            out.append(f"- ligne {d['line']} : `{d['ref']}` ({what})")
        out.append("")
    lay = state["layers"]
    out.append(f"## Couches ({'audit du ' + str(lay.get('date')) if lay['source'] == 'audit' else 'estimation, pas d’audit'})")
    for name, v in lay["layers"].items():
        if name == "MIXED" and not (v.get("total") or 0):
            continue
        tot = "?" if v.get("total") is None else v["total"]
        mis = "" if v.get("misplaced") is None else f", {v['misplaced']} mal placé(s)"
        out.append(f"- {name} : {tot} élément(s){mis}")
    if lay.get("hint"):
        out.append(f"- {lay['hint']}")
    out.append("")
    if state["next_actions"]:
        out.append("## Prochaines actions")
        out.extend(f"{i}. {a}" for i, a in enumerate(state["next_actions"], 1))
        out.append("")
    elif target["reached"]:
        out.append("## Objectif atteint")
        out.append("Le palier visé est tenu. Rien à faire.")
        out.append("")
    return "\n".join(out)
