"""Sous-commande `fixture check` : compare ce que `status` mesure sur une fixture
à `expected.json`, et, si un JSON d'audit est fourni, compare les verdicts aux
pièges attendus ; si le résultat d'un harness-init est fourni (`--init`), note
ce qu'il a écrit contre le bloc `init`. Sortie : un rapport lisible et un code
de retour 0 si tout concorde, 1 sinon."""
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


def _elements_for(audit: dict, path: str, own_only: bool = False) -> list[dict]:
    """Les éléments dont c'est le chemin ; à défaut, ceux qui le citent en preuve
    (un rapport peut ranger un fichier sous un élément plus large). `own_only` pour un élément sain :
    un fichier cité en contraste dans la preuve d'un autre ne lui emprunte pas son verdict."""
    path = path.lower()
    elements = audit.get("elements") or []
    own = [e for e in elements if path in (e.get("path") or "").lower()]
    if own or own_only:
        return own
    return [e for e in elements if any(path in (ev or "").lower() for ev in e.get("evidence") or [])]


def _matches(rule: str, spec: dict) -> bool:
    """Une règle correspond à `rule_keywords` (l'un d'eux) et à `rule_all_of` (tous), s'ils sont donnés."""
    rule = rule.lower()
    any_of = [k.lower() for k in spec.get("rule_keywords") or []]
    all_of = [k.lower() for k in spec.get("rule_all_of") or []]
    return (not any_of or any(k in rule for k in any_of)) and all(k in rule for k in all_of) and bool(any_of or all_of)


def check_audit(audit: dict, expected: dict) -> dict[str, Any]:
    """Score d'un audit contre les pièges attendus : trouvés, manqués, faux, sains signalés."""
    found, missed, wrong = [], [], []
    leaks = [json.dumps(l, ensure_ascii=False).lower() for l in audit.get("process_leaks") or []]
    leaks_text = " ".join(leaks)

    def leaked(trap: dict) -> bool:
        """Une fuite est trouvée quand **une même** entrée de process_leaks porte tous les `leak_keywords`
        et, s'il y en a, l'un des `leak_any_of`. Chercher dans toutes les fuites à la fois créditait un
        piège avec les mots de deux fuites sans rapport."""
        all_of = [k.lower() for k in trap.get("leak_keywords") or []]
        any_of = [k.lower() for k in trap.get("leak_any_of") or []]
        return bool(all_of or any_of) and any(
            all(k in leak for k in all_of) and (not any_of or any(k in leak for k in any_of)) for leak in leaks)

    def wanted(trap: dict) -> str:
        return f"{trap.get('leak_keywords') or []}" + (f" et l'un de {trap['leak_any_of']}" if trap.get("leak_any_of") else "")

    for trap in expected.get("traps", []):
        # Un piège est trouvé soit par un élément au bon verdict sur le bon chemin, soit, pour une règle
        # racontée, par sa présence dans process_leaks (c'est là que le rapport range ces fuites).
        has_leak_spec = bool(trap.get("leak_keywords") or trap.get("leak_any_of"))
        in_leaks = leaked(trap)
        hits = _elements_for(audit, trap["path"])
        ok = [e for e in hits if e.get("verdict") in trap["verdicts"]
              and (not trap.get("priorities") or e.get("priority") in trap["priorities"])]
        if trap.get("require_leak"):
            # le piège est une fuite : seul process_leaks compte, quel que soit le verdict de l'élément
            if in_leaks:
                found.append(trap["id"])
            else:
                missed.append(f"{trap['id']} : aucune fuite de process_leaks ne contient {wanted(trap)}")
            continue
        if ok or in_leaks:
            found.append(trap["id"])
        elif not hits:
            missed.append(f"{trap['id']} : aucun élément pour {trap['path']}"
                          + (f" ni fuite contenant {wanted(trap)}" if has_leak_spec else ""))
        else:
            got = ", ".join(f"{e.get('verdict')}/{e.get('priority')}" for e in hits)
            wrong.append(f"{trap['id']} : {trap['path']} → {got}, attendu {'/'.join(trap['verdicts'])} "
                         f"{'/'.join(trap.get('priorities') or ['*'])}"
                         + (f" ou une fuite contenant {wanted(trap)}" if has_leak_spec else ""))
    sane_flagged = []
    for sane in expected.get("sane", []):
        for e in _elements_for(audit, sane["path"], own_only=True):
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
    # Une règle que rien ne vérifie : la dire gardée est faux quel que soit le garde-fou invoqué
    # (« vérifiée par : la revue » ne cite aucun chemin et passait).
    for g in audit.get("guarded_rules") or []:
        rule = g.get("rule") or ""
        if expected.get("no_guard_exists"):
            sane_flagged.append(f"guarded_rules déclare gardée « {rule[:60]} » : ce dépôt n'a aucun garde-fou qui bloque")
        for never in expected.get("never_guarded", []):
            if _matches(rule, never):
                sane_flagged.append(f"guarded_rules déclare gardée « {rule[:60]} » par {g.get('guarded_by')} : rien ne la vérifie ({never['what']})")
    # Biais « tout est une fuite » : des conventions de style dans process_leaks
    for k in expected.get("forbidden_leak_keywords", []):
        if k.lower() in leaks_text:
            sane_flagged.append(f"process_leaks contient « {k} » : une convention de style n'est pas une fuite de processus")
    # Retraits : les lignes d'instructions que l'audit propose d'enlever, avec leur motif.
    removals = audit.get("removals") or []
    removal_text = lambda r: " ".join(str(r.get(k) or "") for k in ("text", "path")).lower()  # noqa: E731
    for want in expected.get("removals", []):
        hits = [r for r in removals if any(k.lower() in removal_text(r) for k in want["any_of"])]
        good = [r for r in hits if r.get("reason") in want["reasons"]]
        if good and want.get("ask_owner") and not any(r.get("ask_owner") for r in good):
            wrong.append(f"{want['id']} : retrait proposé sans question au propriétaire, alors que lui seul sait si c'est périmé")
        elif good:
            found.append(want["id"])
        elif hits:
            got = ", ".join(str(r.get("reason")) for r in hits)
            wrong.append(f"{want['id']} : retrait motivé {got}, attendu {'/'.join(want['reasons'])}")
        else:
            missed.append(f"{want['id']} : aucun retrait proposé pour une ligne contenant {want['any_of']}")
    for keep in expected.get("must_keep", []):                  # la ligne qui vaut de l'or, noyée dans le bruit
        for r in removals:
            if any(k.lower() in (r.get("text") or "").lower() for k in keep["any_of"]):
                sane_flagged.append(f"{keep['id']} : retrait proposé pour une ligne à garder « {(r.get('text') or '')[:60]} »")
    total = len(expected.get("traps", [])) + len(expected.get("removals", []))
    return {"found": found, "missed": missed, "wrong": wrong, "sane_flagged": sane_flagged,
            "global": global_problems, "score": f"{len(found)}/{total}",
            "ok": not (missed or wrong or sane_flagged or global_problems)}


WORD_RE = re.compile(r"\w+")
REPRISE_RUN = 4     # mots consécutifs partagés avec une ligne d'origine : à partir de là, la ligne est recopiée
# Ce qui dit qu'une chose n'est plus là. Une liste de tournures dépend de la langue : elle ne sert qu'à
# excuser, jamais à accuser. Une tournure absente d'ici laisse la ligne comptée, comme avant.
GONE_MARKERS = ("n'existe", "n’existe", "inexistant", "retiré", "supprimé", "abandonn", "périmé", "obsolète",
                "n'est plus", "n’est plus", "plus installé", "does not exist", "doesn't exist", "no longer",
                "removed", "obsolete", "abandoned")
TEXT_SKIP_DIRS = {".git", "node_modules", ".venv", "__pycache__"}


def _repo_texts(repo: str) -> dict[str, str]:
    """Le texte de chaque fichier lisible d'un dépôt, en minuscules, par chemin relatif."""
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
    """Où un bruit est écrit (mot → fichiers), et les passages qui ne font que le citer.

    Par défaut tout mot trouvé compte. Une entrée `mention_ok` porte un identifiant du dépôt qu'une
    règle saine peut avoir à nommer pour le démentir (« le README annonce `make e2e`, qui n'existe
    plus ») : la ligne n'est alors qu'une citation si elle dit que la chose n'est plus là
    (`GONE_MARKERS`) **et** ne reprend pas une ligne d'origine qui porte le mot (`REPRISE_RUN` mots
    de suite en commun). Sans le dépôt d'origine, rien ne dit si la ligne est recopiée : tout compte."""
    written: dict[str, list[str]] = {}
    cited: list[str] = []
    lenient = bool(noise.get("mention_ok")) and origin is not None
    for word in noise["any_of"]:
        low = word.lower()
        sources = [WORD_RE.findall(line) for text in (origin or {}).values() for line in text.splitlines()
                   if low in line] if lenient else []
        need = max(REPRISE_RUN, len(WORD_RE.findall(low)) + 2)
        for path, text in corpus.items():
            for line in text.splitlines():
                if low not in line.lower():
                    continue
                words = WORD_RE.findall(line.lower())
                if (lenient and any(m in line.lower() for m in GONE_MARKERS)
                        and not any(_shares_run(words, src, need) for src in sources)):
                    quote = f"{word} : « {_excerpt(line.strip(), word)} »"
                    if quote not in cited:
                        cited.append(quote)
                elif path not in written.setdefault(word, []):
                    written[word].append(path)
    return written, cited


def check_init(result_dir: str, expected: dict, today: date | None = None, base: str | None = None,
               report: str | None = None) -> dict[str, Any]:
    """Note ce qu'un harness-init a écrit dans `result_dir` contre le bloc `init` d'expected.json :
    palier atteint, faits non découvrables remontés (`must_surface`), bruit recopié (`must_not_write`),
    garde-fous réels cités (`guards_cited`), garde-fous mensongers crus (`forbidden_guards`), références
    sans cible, matériel des paliers suivants posé trop tôt (`only_level_material`), et fichier sain
    réécrit sans raison (`min_similarity`). `base` est le dépôt de la fixture tel qu'il était avant le
    pas : il sert quand `result_dir` ne contient que les fichiers d'instructions, et à dire si une
    ligne recopie le bruit d'origine ou ne fait que le citer (`noise_hits`)."""
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
        problems.append(f"palier {level} < attendu {expected.get('min_level', 1)} ; échecs : {', '.join(failing)}")
    for fact in expected.get("must_surface", []):
        if any(k.lower() in text for k in fact["any_of"]):
            surfaced.append(fact["id"])
        else:
            problems.append(f"{fact['id']} non remonté : {fact['what']} (aucun de {fact['any_of']})")
    origin = _repo_texts(base) if base else None
    for noise in expected.get("must_not_write", []):
        written, cited = noise_hits(corpus, noise, origin)
        if written:
            where = sorted({p for paths in written.values() for p in paths})
            problems.append(f"{noise['id']} écrit à tort : {noise['what']} ({', '.join(written)} dans {', '.join(where)})")
        mentions += [f"{noise['id']} cité, non compté · {quote}" for quote in cited]
    for path in expected.get("guards_cited", []):
        if not any(path.lower() in r for r in guarded):
            problems.append(f"garde-fou {path} cité par aucune règle « Vérifiée par »")
    for lie in expected.get("forbidden_guards", []):
        for r in guarded:
            after = facts.GUARDED_RE.split(r, maxsplit=1)[-1]      # ce qui suit « Vérifiée par : »
            if lie["path"].lower() in after and any(w.lower() in r for w in lie["rule_keywords"]):
                problems.append(f"garde-fou mensonger cru : « {r[:90]} » s'appuie sur {lie['path']}")
    for r in guarded:                                             # vérifiée par quoi que ce soit : faux
        if expected.get("no_guard_exists"):
            problems.append(f"règle dite vérifiée dans un dépôt sans garde-fou qui bloque : « {r[:90]} »")
        for never in expected.get("never_guarded", []):
            if _matches(r, never):
                problems.append(f"règle dite vérifiée alors que rien ne la vérifie ({never['what']}) : « {r[:90]} »")
    for rest in expected.get("must_not_remain", []):              # les notes annexes : parties, ou réduites
        text_ = facts._read(os.path.join(result_dir, rest["path"]))
        if text_ is None:
            continue
        lines = len(text_.splitlines())
        hits = [k for k in rest.get("any_of", []) if k.lower() in text_.lower()]
        if hits or ("max_lines" in rest and lines > rest["max_lines"]):
            problems.append(f"{rest['path']} laissé en l'état : {rest['what']}"
                            + (f" ({', '.join(hits)})" if hits else f" ({lines} lignes, {rest['max_lines']} au plus)"))
    if report is not None:                                        # le compte rendu rendu au propriétaire
        low = report.lower()
        for want in expected.get("report_must_mention", []):
            if not any(k.lower() in low for k in want["any_of"]):
                problems.append(f"compte rendu : ne dit rien de {want['what']} (aucun de {want['any_of']})")
        for never in expected.get("report_must_not_mention", []):
            hits = [k for k in never["any_of"] if k.lower() in low]
            if hits:
                problems.append(f"compte rendu : contient {never['what']}")
    for ref in state["dangling"]:                                 # un pas ne promet pas le pas suivant
        if ref["kind"] == "guard" and base and facts.cited_path_exists(base, ref["ref"]):
            continue        # `result_dir` ne porte que les instructions : le garde-fou vit dans le dépôt de la fixture
        if ref["kind"] == "job":
            problems.append(f"référence sans cible : job `{ref['ref']}` ligne {ref['line']} (cité, absent des workflows)")
            continue
        problems.append(f"référence sans cible : `{ref['ref']}` ligne {ref['line']} "
                        + ("(contrat cité, pas de SKILL.md)" if ref["kind"] == "contract" else "(garde-fou cité, chemin introuvable)"))
    if expected.get("only_level_material"):
        src = state["facts"]["instructions"]["source"]
        extra = [name for name, present in (("section Maintenance", src.get("has_maintenance_section")),
                                            ("marqueur de harvest", src.get("harvest_marker")),
                                            ("section Processus de travail", src.get("has_process_section"))) if present]
        if extra and level <= expected.get("min_level", 1):
            problems.append("matériel des paliers suivants posé au pas 1 : " + ", ".join(extra))
    for keep in expected.get("min_similarity", []):               # le zèle : réécrire ce qui était sain
        original = facts._read(os.path.join(base or result_dir, keep["path"]))
        written = facts._read(os.path.join(result_dir, keep["path"]))
        if original is None or written is None:
            problems.append(f"{keep['path']} : fichier de départ ou fichier rendu introuvable")
            continue
        ratio = difflib.SequenceMatcher(None, original.splitlines(), written.splitlines()).ratio()
        if ratio < keep["ratio"]:
            problems.append(f"{keep['path']} réécrit : {ratio:.2f} de ressemblance avec le fichier de départ, "
                            f"au moins {keep['ratio']} attendu d'un harness déjà sain")
    total = len(expected.get("must_surface", []))
    return {"level": level, "surfaced": surfaced, "problems": problems, "mentions": mentions,
            "score": f"{len(surfaced)}/{total}", "files": sorted(corpus), "ok": not problems}


# Les vérifications qui ne se gagnent qu'avec le temps : aucun pas ne peut les faire basculer dans une
# séance ; les voir basculer, c'est un signal inventé.
WAITS = maturity.WAITING
# Les vérifications qui se gagnent par parts : une règle gardée par pas, et le palier ne bascule qu'à la
# moitié. Un pas qui fait monter la part avance, même si rien ne bascule (2026-11-14).
SHARES = {"L3.guarded", "L3.justified"}


def check_step(before: dict, after: dict, expected_init: dict, report: str, changed: list[str]) -> dict[str, Any]:
    """Note un pas de harness-step, d'après l'état mesuré avant et après (`maturity.evaluate`).

    Ce qui est attendu, quel que soit le dépôt :
    - objectif déjà atteint : rien ne change, et le compte rendu le dit ;
    - sinon un pas, et un seul : au moins une vérification d'un palier visé bascule, toutes dans le même
      palier ; un palier qu'on ne peut gagner qu'avec le temps n'arrête pas les suivants, s'ils sont visés ;
    - rien ne régresse, rien n'est posé au-delà du palier visé, aucun signal n'est inventé ;
    - les faits du pas 1 restent, et aucune référence sans cible n'apparaît."""
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
        problems.append(f"régression : {', '.join(down)} passai(en)t avant le pas")
    if target is not None and before["level"]["reached"] >= target:
        if files:
            problems.append(f"objectif déjà atteint, et le pas a quand même touché {', '.join(files[:5])}")
        if "objectif atteint" not in (report or "").lower():
            problems.append("objectif déjà atteint : le compte rendu ne le dit pas")
    else:
        in_scope = [cid for cid in up + gained if target is None or a[cid][0] <= target]
        levels = sorted({a[cid][0] for cid in in_scope})
        open_ = [cid for cid, (lvl, ok) in b.items() if not ok and cid not in WAITS and (target is None or lvl <= target)]
        if not in_scope and open_:
            problems.append(f"aucune vérification visée n'a basculé, alors que {', '.join(sorted(open_)[:4])} restai(en)t à gagner")
        if len(levels) > 1:
            problems.append(f"plus d'un pas : des vérifications de {len(levels)} paliers ont basculé ({', '.join(in_scope)})")
    beyond = [cid for cid in up if target is not None and a[cid][0] > target]
    if beyond:
        problems.append(f"matériel posé au-delà du palier visé : {', '.join(beyond)}")
    faked = [cid for cid in up if cid in WAITS]
    if faked:
        problems.append(f"signal inventé : {', '.join(faked)} ne se gagne(nt) qu'avec de vraies revues")
    corpus = "\n".join(facts.instruction_corpus(after["repo"]).values()).lower()
    for fact in expected_init.get("must_surface", []):
        if not any(k.lower() in corpus for k in fact["any_of"]):
            problems.append(f"fait perdu : {fact['id']}, {fact['what']}")
    known = {(d["kind"], d["ref"]) for d in before.get("dangling") or []}
    for d in after.get("dangling") or []:
        if (d["kind"], d["ref"]) not in known:
            problems.append(f"référence sans cible ajoutée : `{d['ref']}` ligne {d['line']}")
    return {"before": before["level"]["reached"], "after": after["level"]["reached"], "target": target,
            "flipped": up, "gained": [f"{cid} {vb[cid]} → {va[cid]}" for cid in gained],
            "problems": problems, "files": files, "ok": not problems}


HINT_RE = re.compile(r"[a-z0-9_][a-z0-9_./-]{3,}")
HINT_STOP = {"true", "false", "null", "none"}


def hint_tokens(word: str) -> list[str]:
    """Les morceaux d'un fait qui suffiraient à le deviner : ses identifiants pris un à un, sauf le fait
    entier, déjà cherché, et les valeurs que tout fichier JSON contient. `"deprecated": true` donne
    `deprecated` ; `idempotency-replayed` ne donne rien de plus que lui-même."""
    low = word.lower()
    return [t for t in dict.fromkeys(HINT_RE.findall(low)) if t not in HINT_STOP and t != low]


INSTRUMENTATION = ["AGENTS.md", "CLAUDE.md", ".claude", ".cursor", ".agents", ".github/copilot-instructions.md", ".harness"]


def check_oral_facts(fixture_dir: str, expected: dict) -> list[str]:
    """Un projet type porte au moins un fait écrit nulle part ailleurs que dans ses instructions, ou
    dit par son propriétaire. C'est le seul endroit où un harness peut montrer un gain : un fait rangé
    dans un ADR, un agent soigneux le trouve seul (campagne du 2026-11-11). Pour chaque fait marqué
    `only_in_instructions` : ses mots ne se lisent dans aucun autre fichier du dépôt, ni aucun de leurs
    morceaux (`hint_tokens` : un validateur qui liste `deprecated` mène à `"deprecated": true`), il s'apprend
    quelque part (instructions du dépôt ou `owner.md`), un contrôle de tâche l'exerce (`exercises`), et
    une solution tentée échoue à ce contrôle. Une fixture sans tâche n'est pas concernée."""
    tasks_dir = os.path.join(fixture_dir, "tasks")
    if not os.path.isdir(tasks_dir):
        return []
    oral = [f for f in expected.get("init", {}).get("must_surface", []) if f.get("only_in_instructions")]
    if not oral:
        return ["aucun fait marqué `only_in_instructions` : tout ce que ce projet apprend se lit dans sa documentation"]
    elsewhere: dict[str, str] = {}          # texte des fichiers qui ne sont pas des instructions
    instructions = ""
    for rel, text in _repo_texts(os.path.join(fixture_dir, "repo")).items():
        if os.path.basename(rel) in ("AGENTS.md", "CLAUDE.md"):
            instructions += text
        else:
            elsewhere[rel] = text
    owner = (facts._read(os.path.join(fixture_dir, "owner.md")) or "").lower()
    owner += (facts._read(os.path.join(fixture_dir, "owner.json")) or "").lower()     # le propriétaire simulé
    checks = []                             # (tâche, contrôle)
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
                problems.append(f"{fact['id']} : « {word} » se lit aussi dans {', '.join(where[:3])} : le fait est découvrable")
                continue
            for token in hint_tokens(word):     # un morceau du fait suffit à y mener (2026-11-13)
                where = sorted(p for p, text in elsewhere.items() if re.search(r"(?<![\w-])" + re.escape(token) + r"(?![\w-])", text))
                if where:
                    problems.append(f"{fact['id']} : « {token} », un morceau du fait, se lit dans {', '.join(where[:3])} : "
                                    "un indice qui y mène, le fait est découvrable")
        if not any(w in instructions or w in owner for w in words):
            problems.append(f"{fact['id']} : aucun de {words} dans les instructions du dépôt ni dans owner.md : nulle part où l'apprendre")
        exercising = [c["id"] for _, c in checks if c.get("exercises") == fact["id"]]
        if not exercising:
            problems.append(f"{fact['id']} : aucun contrôle de tâche ne l'exerce (`exercises`)")
        elif not any(cid in tempted_fails for cid in exercising):
            problems.append(f"{fact['id']} : aucune solution tentée n'échoue à {exercising} : rien ne prouve que le contrôle départage")
    return problems


COPY_IGNORE = shutil.ignore_patterns("node_modules", "__pycache__", ".venv", "*.pyc", ".pytest_cache")


def commit_all(dest: str, branch: str) -> None:
    """Fait de `dest` un dépôt git à un commit : le point de départ d'une exécution."""
    env = {**os.environ, "GIT_AUTHOR_NAME": "owner", "GIT_AUTHOR_EMAIL": "owner@example.test",
           "GIT_COMMITTER_NAME": "owner", "GIT_COMMITTER_EMAIL": "owner@example.test"}
    for args in (["init", "-q", "-b", branch], ["add", "-A"], ["commit", "-q", "-m", "import"]):
        subprocess.run(["git", "-C", dest, *args], check=True, env=env, capture_output=True)


def bare_copy(fixture_dir: str, dest: str, branch: str = "develop", keep_instrumentation: bool = False,
              commit: bool = True) -> list[str]:
    """Copie `repo/` d'une fixture dans `dest` sans son instrumentation IA, et en fait un dépôt git
    avec un commit : le dépôt « nu » sur lequel on évalue harness-init à l'aveugle. Ce qui n'est pas
    versionné (node_modules, caches) n'est pas copié. Retourne la liste de ce qui a été retiré."""
    src = os.path.join(fixture_dir, "repo")
    if os.path.exists(dest) and os.listdir(dest):
        raise SystemExit(f"{dest} existe et n'est pas vide")
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
    if not keep_instrumentation:                 # les notes de sous-dossier sont de l'instrumentation aussi
        for root, _dirs, files in os.walk(dest):
            for name in files:
                rel = os.path.relpath(os.path.join(root, name), dest).replace(os.sep, "/")
                if name in ("AGENTS.md", "CLAUDE.md") and "/" in rel:
                    os.remove(os.path.join(root, name))
                    removed.append(rel)
    readme = os.path.join(dest, "README.md")
    if os.path.exists(readme):
        with open(readme, encoding="utf-8") as fh:
            # La ligne qui avoue le banc. « fixture » seul est aussi un mot de Django et de pytest.
            lines = [l for l in fh.read().splitlines()
                     if not re.search(r"harness-ai|d[ée]p[ôo]t \*\*synth[ée]tique\*\*|pièges d'instrumentation", l, re.I)]
        with open(readme, "w", encoding="utf-8") as fh:
            fh.write("\n".join(lines).rstrip() + "\n")
    if commit:
        commit_all(dest, branch)
    return removed


def build_parser(parser: argparse.ArgumentParser | None = None) -> argparse.ArgumentParser:
    p = parser or argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="fixture_command", required=True)
    c = sub.add_parser("check", help="compare une fixture à expected.json")
    c.add_argument("name", help="nom de la fixture (dossier de fixtures/repos) ou chemin")
    c.add_argument("--audit", help="JSON d'audit à noter contre les pièges")
    c.add_argument("--init", help="dépôt produit par un harness-init, à noter contre le bloc init")
    c.add_argument("--report", help="avec --init : le compte rendu rendu par l'agent, noté lui aussi")
    c.add_argument("--today", help="AAAA-MM-JJ pour une mesure reproductible")
    b = sub.add_parser("bare", help="copie d'une fixture sans instrumentation IA, pour évaluer harness-init")
    b.add_argument("name", help="nom de la fixture ou chemin")
    b.add_argument("dest", help="dossier de destination (créé, doit être vide)")
    b.add_argument("--branch", default="develop")
    return p


def main(argv: list[str] | None = None, args: argparse.Namespace | None = None) -> int:
    if args is None:
        args = build_parser().parse_args(argv)
    fixture_dir = args.name if os.path.isdir(args.name) else os.path.join(FIXTURES_ROOT, args.name)
    if args.fixture_command == "bare":
        removed = bare_copy(fixture_dir, args.dest, args.branch)
        print(f"dépôt nu dans {args.dest} (branche {args.branch}) ; retiré : {', '.join(removed) or 'rien'}")
        return 0
    with open(os.path.join(fixture_dir, "expected.json"), encoding="utf-8") as fh:
        expected = json.load(fh)
    today = date.fromisoformat(args.today) if args.today else None
    problems = check_status(fixture_dir, expected["status"], today)
    print(f"# Fixture {expected.get('fixture', args.name)}")
    print("## status : " + ("conforme" if not problems else f"{len(problems)} écart(s)"))
    for p in problems:
        print(f"- {p}")
    ok = not problems
    if os.path.isdir(os.path.join(fixture_dir, "tasks")):
        oral = check_oral_facts(fixture_dir, expected)
        print("## faits écrits nulle part ailleurs : " + ("conforme" if not oral else f"{len(oral)} écart(s)"))
        for p in oral:
            print(f"- {p}")
        ok = ok and not oral
    if os.path.isfile(os.path.join(fixture_dir, "owner.json")):
        from . import owner
        posed = owner.check(fixture_dir, expected)
        print("## propriétaire simulé : " + ("conforme" if not posed else f"{len(posed)} écart(s)"))
        for p in posed:
            print(f"- {p}")
        ok = ok and not posed
    if args.audit:
        with open(args.audit, encoding="utf-8") as fh:
            audit = json.load(fh)
        result = check_audit(audit, expected.get("audit", {}))
        print(f"## audit : {result['score']} pièges et retraits trouvés" + (" · conforme" if result["ok"] else ""))
        for key, title in (("missed", "Manqués"), ("wrong", "Mauvais verdict"), ("sane_flagged", "Sains signalés"),
                           ("global", "Global")):
            if result[key]:
                print(f"### {title}")
                for line in result[key]:
                    print(f"- {line}")
        ok = ok and result["ok"]
    if args.init:
        report = facts._read(args.report) if args.report else None
        if args.report and report is None:
            raise SystemExit(f"compte rendu introuvable : {args.report}")
        result = check_init(args.init, expected.get("init", {}), today, base=os.path.join(fixture_dir, "repo"), report=report)
        if report is None and any(k.startswith("report_") for k in expected.get("init", {})):
            print("(compte rendu non noté : passer --report <fichier>)")
        print(f"## init : palier {result['level']} · {result['score']} faits remontés"
              + (" · conforme" if result["ok"] else f" · {len(result['problems'])} écart(s)"))
        for line in result["problems"]:
            print(f"- {line}")
        if result["mentions"]:
            print("### Cité sans être recopié : non compté, à relire")
            for line in result["mentions"]:
                print(f"- {line}")
        ok = ok and result["ok"]
    return 0 if ok else 1
