"""Médailles et succès : le niveau de maturité, dit comme une progression qu'on a envie de suivre.

Rien n'est noté ici par un modèle. Pour un dépôt, la médaille est le palier que `harness status`
mesure (bronze = palier 1 … platine = palier 4) et chaque vérification passée est un succès débloqué.
Pour une marketplace de plugins, quatre rangs de vérifications lues dans ses fichiers. Le résultat
tient dans `.harness/medals.json`, qu'on peut commiter : il garde la date où chaque succès a été
débloqué, et dit quand l'un d'eux a été perdu. `--page` en fait une page HTML autonome."""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import re
import sys
from datetime import date
from typing import Any

from . import commands, facts, maturity, progress

SCHEMA = 1
FILE = "medals.json"
MEDALS = ({"id": "aucune", "name": "Aucune médaille"}, {"id": "bronze", "name": "Bronze"},
          {"id": "argent", "name": "Argent"}, {"id": "or", "name": "Or"}, {"id": "platine", "name": "Platine"})
KINDS = ("repo", "marketplace")
TEMPLATE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "medals_template.html")
MAX_SKILL_LINES = 500
_TRIGGER = re.compile(r"utiliser quand|à utiliser|use when|use this|when the user|trigger", re.IGNORECASE)
_NEGATIVE = re.compile(r"ne pas utiliser|do not use|don't use|not for\b|n'est pas pour", re.IGNORECASE)


def _success(ident: str, tier: str, title: str, passed: bool, evidence: str, action: str | None,
             waiting: bool = False) -> dict[str, Any]:
    return {"id": ident, "tier": tier, "title": title, "passed": bool(passed), "evidence": evidence,
            "next": None if passed else action, "waiting": bool(waiting and not passed)}


def _short(value: Any) -> str:
    """La valeur mesurée d'une vérification, en une ligne lisible."""
    if isinstance(value, dict):
        return ", ".join(f"{k} : {_short(v)}" for k, v in value.items() if not isinstance(v, (dict, list)))[:160]
    if isinstance(value, (list, tuple)):
        return ", ".join(_short(v) for v in value)[:160] or "aucun"
    if isinstance(value, bool):
        return "oui" if value else "non"
    return "" if value is None else str(value)[:160]


# --- Un dépôt : les paliers de harness status ------------------------------------------------------------

def evaluate_repo(repo: str, today: date | None = None) -> dict[str, Any]:
    state = maturity.evaluate(facts.collect(repo, today=today))
    tiers, successes = [], []
    for level in state["levels"][1:]:
        medal = MEDALS[level["level"]]
        tiers.append({"id": medal["id"], "name": medal["name"], "title": level["name"], "promise": level["summary"]})
        successes += [_success(c["id"], medal["id"], c["label"], c["passed"], _short(c.get("value")),
                               c.get("next_action"), c.get("waits", False)) for c in level["checks"]]
    source = state["facts"]["instructions"]["source"]
    total = source.get("rules_total") or 0
    found = commands.collect(repo)
    unwritten = [c["command"] for c in found["candidates"] if c["ci"] and c["kind"] != "livraison" and not c["documented"]]
    target = state["target"]
    bonus = [
        ("B.dates", "Chaque règle porte sa date", total > 0 and source.get("rules_dated") == total,
         f"{source.get('rules_dated', 0)} sur {total}", "Dater chaque règle [AAAA-MM] : l'âge d'une règle est l'entrée de la revue de pertinence."),
        ("B.pourquoi", "Chaque règle dit pourquoi", total > 0 and source.get("rules_justified") == total,
         f"{source.get('rules_justified', 0)} sur {total}", "Ajouter « Pourquoi : … » aux règles qui ne le disent pas, ou « pas d'incident connu »."),
        ("B.outils", "Chaque règle est tenue par un outil", total > 0 and source.get("rules_guarded") == total,
         f"{source.get('rules_guarded', 0)} sur {total}", "Pousser les règles racontées vers un lint, un test d'architecture ou un check de PR."),
        ("B.cibles", "Aucune référence sans cible", bool(source.get("path")) and not state["dangling"],
         f"{len(state['dangling'])} référence(s) sans cible", "Retirer ou réparer ce que `harness status` liste sous « références sans cible »."),
        ("B.commandes", "Les commandes que la CI lance sont écrites", bool(source.get("path")) and not unwritten,
         ", ".join(unwritten[:3]) or "aucun écart avec les commandes évidentes",
         "Lancer `harness commands`, confirmer chaque candidate et l'écrire dans le tableau d'AGENTS.md."),
        ("B.objectif", "Le palier visé est atteint", bool(target.get("reached")),
         f"visé : {target.get('name') or 'aucun'}", "Dire où l'on s'arrête avec `harness target <palier>`, puis l'atteindre."),
    ]
    successes += [_success(i, "bonus", t, p, e, a) for i, t, p, e, a in bonus]
    return {"kind": "repo", "name": os.path.basename(os.path.abspath(repo)), "date": state["date"],
            "rank": state["level"]["reached"], "tiers": tiers, "successes": successes}


# --- Une marketplace de plugins --------------------------------------------------------------------------

def _json(path: str) -> Any:
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None


def _front_matter(path: str) -> tuple[dict[str, str], int]:
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            lines = fh.read().splitlines()
    except OSError:
        return {}, 0
    header: dict[str, str] = {}
    if lines[:1] == ["---"]:
        for line in lines[1:]:
            if line.strip() == "---":
                break
            key, sep, value = line.partition(":")
            if sep and key.strip() and not key.startswith(" "):
                header[key.strip()] = value.strip()
    return header, len(lines)


def _plugins(repo: str) -> tuple[Any, list[dict[str, Any]]]:
    manifest = _json(os.path.join(repo, ".claude-plugin", "marketplace.json"))
    plugins = []
    entries = manifest.get("plugins") if isinstance(manifest, dict) else None
    for entry in entries if isinstance(entries, list) else []:
        source = entry.get("source") if isinstance(entry, dict) else None
        if not isinstance(source, str) or source.startswith(("/", "http")) or ".." in source.split("/"):
            plugins.append({"name": str((entry or {}).get("name") if isinstance(entry, dict) else entry), "root": None})
            continue
        root = os.path.normpath(os.path.join(repo, source))
        info = _json(os.path.join(root, ".claude-plugin", "plugin.json"))
        skills_dir = os.path.join(root, "skills")
        skills = sorted(os.path.join(skills_dir, d, "SKILL.md") for d in (os.listdir(skills_dir) if os.path.isdir(skills_dir) else [])
                        if os.path.isfile(os.path.join(skills_dir, d, "SKILL.md")))
        cli = os.path.join(root, "cli")
        has_code = os.path.isdir(cli) and any(n.endswith(".py") for _, _, ns in os.walk(cli) for n in ns)
        has_tests = os.path.isdir(cli) and any(n.startswith("test_") and n.endswith(".py") for _, _, ns in os.walk(cli) for n in ns)
        plugins.append({"name": entry.get("name") or source, "root": root, "info": info if isinstance(info, dict) else None,
                        "skills": [{"path": os.path.relpath(p, repo).replace(os.sep, "/"), "front": _front_matter(p)} for p in skills],
                        "has_code": has_code, "has_tests": has_tests})
    return manifest, plugins


def evaluate_marketplace(repo: str, today: date | None = None) -> dict[str, Any]:
    manifest, plugins = _plugins(repo)
    skills = [s for p in plugins if p["root"] for s in p["skills"]]

    def lacking(test: Any, items: list[dict[str, Any]], key: str) -> list[str]:
        return [str(i[key]) for i in items if not test(i)]

    def row(ident: str, tier: str, title: str, missing: list[str], total: int, action: str,
            vacuous: bool = False) -> dict[str, Any]:
        evidence = f"{total - len(missing)} sur {total}" + (f" ; manque : {', '.join(missing[:3])}" if missing else "")
        if vacuous and not total:
            evidence = "aucun plugin ne porte de code : rien à tester"
        return _success(ident, tier, title, (total > 0 or vacuous) and not missing, evidence, action)

    valid = isinstance(manifest, dict) and isinstance(manifest.get("name"), str) and bool(plugins)
    blind = [os.path.join(r, d) for r, ds, _ in os.walk(os.path.join(repo, "fixtures")) for d in ds
             if os.path.basename(r) == "runs" and "blind" in d]
    try:
        with open(os.path.join(repo, progress.DOC), encoding="utf-8") as fh:
            plan_errors = progress.parse(fh.read())[1]
    except OSError:
        plan_errors = [f"{progress.DOC} absent"]
    successes = [
        _success("M1.manifeste", "bronze", "Le manifeste de la marketplace se lit et liste des plugins", valid,
                 f"{len(plugins)} plugin(s)", "Écrire `.claude-plugin/marketplace.json` avec un nom et au moins un plugin."),
        row("M1.sources", "bronze", "Chaque plugin a sa source dans le dépôt, avec son `plugin.json`",
            lacking(lambda p: p["root"] and p.get("info"), plugins, "name"), len(plugins),
            "Donner à chaque plugin une source relative et un `.claude-plugin/plugin.json`."),
        row("M1.identite", "bronze", "Chaque plugin a un nom, une version et une description",
            lacking(lambda p: p.get("info") and all(isinstance(p["info"].get(k), str) and p["info"][k] for k in ("name", "version", "description")),
                    plugins, "name"), len(plugins), "Compléter `name`, `version` et `description` dans chaque `plugin.json`."),
        row("M2.skills", "argent", "Chaque skill a un nom et une description",
            lacking(lambda s: s["front"][0].get("name") and s["front"][0].get("description"), skills, "path"), len(skills),
            "Donner à chaque SKILL.md un en-tête `name` et `description`."),
        row("M2.quand", "argent", "Chaque description dit quand utiliser le skill",
            lacking(lambda s: _TRIGGER.search(s["front"][0].get("description", "")), skills, "path"), len(skills),
            "Écrire dans la description les demandes qui doivent déclencher le skill (« Utiliser quand… »)."),
        row("M2.quand-pas", "argent", "Chaque description dit quand ne pas l'utiliser",
            lacking(lambda s: _NEGATIVE.search(s["front"][0].get("description", "")), skills, "path"), len(skills),
            "Ajouter « Ne pas utiliser pour… » : c'est ce qui départage deux skills voisins."),
        row("M3.budget", "or", f"Aucun SKILL.md ne dépasse {MAX_SKILL_LINES} lignes",
            lacking(lambda s: 0 < s["front"][1] <= MAX_SKILL_LINES, skills, "path"), len(skills),
            "Déporter la référence dans des fichiers chargés à la demande."),
        row("M3.tests", "or", "Chaque plugin qui porte du code a ses tests",
            lacking(lambda p: p["has_tests"], [p for p in plugins if p.get("has_code")], "name"),
            len([p for p in plugins if p.get("has_code")]), "Tester le CLI du plugin : ce qui est garanti vit dans du code testé.",
            vacuous=valid),
        _success("M4.aveugle", "platine", "Au moins une exécution à l'aveugle est rangée dans le dépôt", bool(blind),
                 f"{len(blind)} exécution(s) sous fixtures/", "Jouer un skill sur une fixture par un agent neuf, et ranger son résultat dans `runs/`."),
        _success("M4.plan", "platine", "Le plan d'avancement existe et il est en forme", not plan_errors,
                 "; ".join(plan_errors[:2]) or progress.DOC, f"Tenir {progress.DOC} avec `harness progress check`."),
    ]
    order = [m["id"] for m in MEDALS[1:]]
    rank = 0
    for index, tier in enumerate(order, 1):
        if not all(s["passed"] for s in successes if s["tier"] == tier):
            break
        rank = index
    tiers = [{"id": "bronze", "name": "Bronze", "title": "Installable", "promise": "La marketplace se lit, chaque plugin s'installe."},
             {"id": "argent", "name": "Argent", "title": "Décrit", "promise": "Chaque skill dit quand il sert, et quand il ne sert pas."},
             {"id": "or", "name": "Or", "title": "Tenu", "promise": "Ce qui est garanti est dans du code testé, les skills restent courts."},
             {"id": "platine", "name": "Platine", "title": "Mesuré", "promise": "Les skills sont éprouvés à l'aveugle, l'avancement est tenu."}]
    name = manifest.get("name") if isinstance(manifest, dict) and isinstance(manifest.get("name"), str) else os.path.basename(os.path.abspath(repo))
    return {"kind": "marketplace", "name": name, "date": (today or date.today()).isoformat(), "rank": rank,
            "tiers": tiers, "successes": successes}


# --- Le fichier du dépôt : ce qu'on garde d'une fois sur l'autre -----------------------------------------

def build(evaluated: dict[str, Any], previous: Any = None) -> dict[str, Any]:
    """Le contenu de medals.json : l'évaluation du jour, plus la date où chaque succès a été débloqué
    (gardée de la fois précédente) et celle où il a été perdu."""
    today = evaluated["date"]
    same = isinstance(previous, dict) and previous.get("schema") == SCHEMA and previous.get("kind") == evaluated["kind"]
    before = {s["id"]: s for s in previous.get("successes", []) if isinstance(s, dict) and "id" in s} if same else {}
    successes = []
    for item in evaluated["successes"]:
        old = before.get(item["id"], {})
        unlocked = (old.get("unlocked") or today) if item["passed"] else None
        lost = None if item["passed"] else (old.get("lost") or (today if old.get("unlocked") else None))
        successes.append({"id": item["id"], "tier": item["tier"], "title": item["title"], "unlocked": unlocked, "lost": lost,
                          "evidence": item["evidence"], "next": item["next"], "waiting": item["waiting"]})
    rank = evaluated["rank"]
    medal = {**MEDALS[rank], "rank": rank, "of": len(MEDALS) - 1}
    tiers = []
    for index, tier in enumerate(evaluated["tiers"], 1):
        mine = [s for s in successes if s["tier"] == tier["id"]]
        tiers.append({**tier, "done": sum(bool(s["unlocked"]) for s in mine), "total": len(mine), "earned": index <= rank})
    upcoming = evaluated["tiers"][rank]["id"] if rank < len(evaluated["tiers"]) else None
    steps = [{"id": s["id"], "title": s["title"], "action": s["next"], "waiting": s["waiting"]}
             for s in successes if s["tier"] == upcoming and not s["unlocked"]]
    if rank and tiers:
        why = f"{medal['name']} : les {tiers[rank - 1]['total']} succès du rang « {tiers[rank - 1]['title']} » sont débloqués"
        why += f", et il en manque {len(steps)} pour {MEDALS[rank + 1]['name'].lower()}." if upcoming else ". C'est le dernier rang."
    else:
        why = f"Pas encore de médaille : il manque {len(steps)} succès pour le bronze."
    history = [h for h in (previous.get("history", []) if same else []) if isinstance(h, dict)]
    if not history or history[-1].get("medal") != medal["id"]:
        history.append({"date": today, "medal": medal["id"]})
    return {"schema": SCHEMA, "kind": evaluated["kind"], "name": evaluated["name"], "date": today, "medal": medal,
            "why": why, "tiers": tiers, "successes": successes, "next": steps, "history": history[-50:]}


def render_md(data: dict[str, Any]) -> str:
    done = [s for s in data["successes"] if s["unlocked"]]
    out = [f"# {data['medal']['name']} — {data['name']}", "", data["why"],
           f"Succès débloqués : {len(done)} sur {len(data['successes'])}. Mesuré le {data['date']}.", ""]
    for tier in data["tiers"]:
        out.append(f"## {'✓' if tier['earned'] else '·'} {tier['name']} — {tier['title']} ({tier['done']}/{tier['total']})")
        out.append(f"_{tier['promise']}_")
        for s in (s for s in data["successes"] if s["tier"] == tier["id"]):
            mark = f"[x] {s['title']} (depuis le {s['unlocked']})" if s["unlocked"] else f"[ ] {s['title']}"
            out.append(f"- {mark}" + (f" — perdu le {s['lost']}" if s["lost"] else ""))
        out.append("")
    extra = [s for s in data["successes"] if s["tier"] == "bonus"]
    if extra:
        out.append(f"## Hors rang ({sum(bool(s['unlocked']) for s in extra)}/{len(extra)})")
        out += [f"- [{'x' if s['unlocked'] else ' '}] {s['title']} ({s['evidence']})" for s in extra] + [""]
    if data["next"]:
        out.append("## Prochaines étapes")
        out += [f"{n}. {s['action'] or s['title']}" + (" (en attente : ça ne dépend pas que de toi)" if s["waiting"] else "")
                for n, s in enumerate(data["next"], 1)]
    return "\n".join(out).rstrip() + "\n"


# --- La page ---------------------------------------------------------------------------------------------

def _csp(template: str) -> str:
    def digest(tag: str) -> str:
        body = re.search(rf"<{tag}>(.*?)</{tag}>", template, re.DOTALL)[1]
        return base64.b64encode(hashlib.sha256(body.encode("utf-8")).digest()).decode("ascii")
    return (f"default-src 'none'; style-src 'sha256-{digest('style')}'; script-src 'sha256-{digest('script')}'; "
            "img-src data:; base-uri 'none'; form-action 'none'")


def render_html(data: dict[str, Any]) -> str:
    """Une page autonome : les données sont dans le fichier, le script ne fait que les montrer."""
    with open(TEMPLATE_FILE, encoding="utf-8") as fh:
        template = fh.read()
    raw = json.dumps(data, ensure_ascii=False, sort_keys=True).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    title = f"{data['medal']['name']} · {data['name']}".replace("&", "&amp;").replace("<", "&lt;")
    return template.replace("{{csp}}", _csp(template)).replace("{{title}}", title).replace("{{data}}", raw)


def build_parser(parser: argparse.ArgumentParser | None = None) -> argparse.ArgumentParser:
    p = parser or argparse.ArgumentParser(description=__doc__)
    p.add_argument("repo", nargs="?", default=".")
    p.add_argument("--kind", choices=KINDS, help="défaut : marketplace si le dépôt en déclare une et n'a pas d'AGENTS.md mesuré, sinon repo")
    p.add_argument("--write", action="store_true", help=f"met à jour .harness/{FILE}, en gardant les dates déjà acquises")
    p.add_argument("--page", metavar="FICHIER", help="écrit la page HTML interactive")
    p.add_argument("--format", choices=["md", "json"], default="md")
    p.add_argument("--name", help="le nom affiché (défaut : celui du dossier, ou de la marketplace)")
    p.add_argument("--today", help=argparse.SUPPRESS)
    return p


def main(argv: list[str] | None = None, args: argparse.Namespace | None = None) -> int:
    args = args or build_parser().parse_args(argv)
    if not os.path.isdir(args.repo):
        print(f"harness medals : {args.repo} n'est pas un dossier", file=sys.stderr)
        return 2
    today = date.fromisoformat(args.today) if args.today else None
    kind = args.kind or "repo"
    path = os.path.join(args.repo, ".harness", FILE if kind == "repo" else f"medals-{kind}.json")
    evaluated = evaluate_repo(args.repo, today) if kind == "repo" else evaluate_marketplace(args.repo, today)
    if args.name:
        evaluated["name"] = args.name
    data = build(evaluated, _json(path))
    if args.write:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False, indent=2)
            fh.write("\n")
    if args.page:
        with open(args.page, "w", encoding="utf-8") as fh:
            fh.write(render_html(data))
    sys.stdout.write(json.dumps(data, ensure_ascii=False, indent=2) + "\n" if args.format == "json" else render_md(data))
    return 0
