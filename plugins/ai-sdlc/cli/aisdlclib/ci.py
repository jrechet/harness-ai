"""Les portes jouées en CI : la vérification sort de la session qui a écrit le code.

Dans une session, c'est l'agent qui lance `qa gate` et `secu gate`, donc il peut ne pas le faire. Ici un
pipeline les joue sur chaque pull request, et son code de sortie bloque la fusion. Ce que la CI ne peut pas
jouer sans modèle ni ticket (la revue, un test par critère) n'est pas prétendu.

Les réglages viennent de `docs/agents/portes.json`, lu **sur la branche de base** : une pull request ne peut
ni alléger ces réglages, ni se mettre elle-même hors lecture. Cela ne protège que les réglages. Le code qui
joue les portes doit lui aussi venir d'ailleurs que de la pull request (le plugin à une version fixée, ou la
branche cible récupérée à part), et le fichier du pipeline reste modifiable par elle : c'est un ruleset de
la forge qui rend le check obligatoire. Une PR vers une branche non protégée prend les réglages de celle-là."""
from __future__ import annotations

import json
import os
from typing import Any

from . import qa, secu, size
from .context import Refused, _read_at, resolve_base

CONFIG = "docs/agents/portes.json"
MAX_EXCLUDES = 20
_TOO_WIDE = ("*", "**", "**/*", "*/**", "**/**", "*.*", "**/*.*")


def _globs(value: Any, where: str) -> list[str]:
    """Des motifs de chemins tenus hors d'une porte. Chacun commence par un dossier ou un fichier nommé :
    un joker en tête mettrait tout le dépôt hors lecture."""
    if not (isinstance(value, list) and len(value) <= MAX_EXCLUDES and all(isinstance(g, str) and g.strip() for g in value)):
        raise Refused(f"{CONFIG} : {where} est une liste d'au plus {MAX_EXCLUDES} motifs de chemins")
    for glob in value:
        first = glob.strip().split("/")[0]
        if glob.strip() in _TOO_WIDE or glob.startswith(("/", "..")) or not first or any(ch in first for ch in "*?["):
            raise Refused(f"{CONFIG} : le motif {glob[:40]!r} met trop de choses hors lecture ; il commence par un dossier ou un "
                          "fichier nommé (tests/secrets/**), pas par un joker")
        size.glob_regex(glob)
    return [g.strip() for g in value]


def load_config(repo: str, base: str) -> dict[str, Any]:
    """Les réglages des portes sur la branche de base ; des valeurs sûres s'il n'y en a pas."""
    text = _read_at(repo, resolve_base(repo, base), CONFIG)
    config: dict[str, Any] = {"secu": {"exclure": []}, "qa": {"commande": None, "passages": None, "exclure": []}}
    if text is None:
        return config
    try:
        data = json.loads(text)
    except (ValueError, RecursionError) as exc:
        raise Refused(f"{CONFIG} (branche de base) : JSON illisible") from exc
    if not isinstance(data, dict) or set(data) - {"secu", "qa"}:
        raise Refused(f"{CONFIG} : un objet avec secu et qa, rien d'autre")
    secu_part, qa_part = data.get("secu", {}), data.get("qa", {})
    if not isinstance(secu_part, dict) or set(secu_part) - {"exclure"} or not isinstance(qa_part, dict) \
            or set(qa_part) - {"commande", "passages", "exclure"}:
        raise Refused(f"{CONFIG} : secu.exclure, qa.commande, qa.passages et qa.exclure sont les seuls réglages")
    command, runs = qa_part.get("commande"), qa_part.get("passages")
    if command is not None and not (isinstance(command, str) and command.strip() and len(command) <= 300):
        raise Refused(f"{CONFIG} : qa.commande est la commande de test du dépôt")
    if runs is not None and not (type(runs) is int and 1 <= runs <= 20):
        raise Refused(f"{CONFIG} : qa.passages est un entier de 1 à 20")
    return {"secu": {"exclure": _globs(secu_part.get("exclure", []), "secu.exclure")},
            "qa": {"commande": command, "passages": runs, "exclure": _globs(qa_part.get("exclure", []), "qa.exclure")}}


def run(table: dict[str, Any], repo: str, base: str, coverage: str | None = None, reports: list[str] | None = None,
        strict: bool = False) -> dict[str, Any]:
    """Les portes d'une pull request : sécurité, puis tests. `strict` fait échouer ce qui n'est pas mesuré."""
    config = load_config(repo, base)
    security = secu.run_gates(table, repo, base, reports, config["secu"]["exclure"], pipeline=True)
    spared = [size.glob_regex(g) for g in config["qa"]["exclure"]]
    changed = [s["path"] for s in size.diff_stats(repo, base)]
    paths = [p for p in changed if not any(r.match(p) for r in spared)]   # un test qui porte sur le skip lui-même, par exemple
    tests = [qa.gate_disabled(repo, base, paths, spared)]
    if config["qa"]["commande"]:
        tests.append(qa.gate_repeat(repo, config["qa"]["commande"], config["qa"]["passages"] or table["qa"]["runs"]))
    if coverage:
        tests.append(qa.gate_coverage(repo, base, coverage, table["qa"]["diff_coverage"]))
    gates = security["gates"] + tests
    failed = [g["id"] for g in gates if g["status"] == qa.FAIL]
    unknown = [g["id"] for g in gates if g["status"] == qa.UNKNOWN]
    return {"pass": not failed and not (strict and unknown), "failed": failed, "unknown": unknown, "strict": strict, "gates": gates,
            "excluded": sorted({*security["excluded"], *(secu._where(p) for p in changed if p not in paths)}), "configured": config}


def render_md(result: dict[str, Any]) -> str:
    out_of_reading = f" {len(result['excluded'])} fichier(s) hors lecture." if result["excluded"] else ""
    if result["failed"]:
        head = f"Portes : {len(result['failed'])} en échec. La fusion est bloquée."
    elif result["unknown"] and result["strict"]:
        head = f"Portes : {len(result['unknown'])} non mesurée(s), et ce dépôt les exige mesurées. La fusion est bloquée."
    elif result["unknown"]:
        head = f"Portes : rien en échec, {len(result['unknown'])} non mesurée(s) à regarder par un humain."
    else:
        head = "Portes : tout ce qui est mesuré passe."
    out = [f"### {head}{out_of_reading}", ""]
    for gate in result["gates"]:
        out.append(f"- **{gate['status']}** — {gate['title']} ({gate['evidence']})" + (f". {gate['action']}" if gate["action"] else ""))
    if result["excluded"]:
        out.append(f"- Hors lecture, d'après `{CONFIG}` sur la branche de base : {', '.join(result['excluded'][:8])}"
                   + (f" et {len(result['excluded']) - 8} autre(s)" if len(result["excluded"]) > 8 else "") + ".")
    if not result["configured"]["qa"]["commande"]:
        out.append(f"- La suite de tests n'est pas rejouée ici : `{CONFIG}` ne donne pas de commande sur la branche de base.")
    out += ["", "Ces portes ne jouent ni la revue ni « un test par critère » : il y faut un ticket et un relecteur.",
            "Elles ne disent pas qu'un changement est sûr : elles disent ce qui a été regardé."]
    return "\n".join(out) + "\n"


def publish(text: str, environ: dict[str, str]) -> None:
    """Le résumé dans la page du job, quand la forge en offre une."""
    path = environ.get("GITHUB_STEP_SUMMARY")
    if not path:
        return
    try:
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(text + "\n")
    except OSError:
        pass
