"""Le corps d'une PR ouverte par `/dev` : ce qui change, pourquoi, le plan, ce qui est vérifié ou non.

La définition de fini demande que la description dise ces choses. Elles sont exigées ici, pas dans
le texte du skill : un corps incomplet n'est pas rendu, et un changement de taille L sans son plan
dans le diff non plus. La taille affichée est celle que le CLI calcule, pas celle que l'agent estime."""
from __future__ import annotations

from typing import Any

from . import size as size_mod
from .context import Refused


def _text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _texts(value: Any, empty_ok: bool = False) -> bool:
    return isinstance(value, list) and all(_text(v) for v in value) and (empty_ok or bool(value))


def validate(data: Any, sized: dict[str, Any], plans_dir: str) -> list[str]:
    """Ce qui manque au corps pour être rendu, compte tenu de la taille du changement."""
    if not isinstance(data, dict):
        return ["le corps est un objet JSON : titre, ticket, quoi, pourquoi, plan, verifie, non_verifie"]
    errors = []
    if not _text(data.get("titre")):
        errors.append("titre : une ligne")
    if data.get("ticket") is not None and not _text(data.get("ticket")):
        errors.append("ticket : sa clé ou son lien, ou null s'il n'y en a pas")
    if not _texts(data.get("quoi")):
        errors.append("quoi : la liste de ce qui change, au moins une ligne")
    if not _text(data.get("pourquoi")):
        errors.append("pourquoi : la raison du changement")
    checks = data.get("verifie")
    if not isinstance(checks, list) or not all(
            isinstance(c, dict) and _text(c.get("commande")) and _text(c.get("resultat")) for c in checks):
        errors.append("verifie : une liste de {commande, resultat}, vide si rien n'a été lancé")
        checks = None
    unchecked = data.get("non_verifie")
    if not _texts(unchecked, empty_ok=True):
        errors.append("non_verifie : une liste de phrases, vide si tout est vérifié")
    elif checks == [] and not unchecked:
        errors.append("verifie et non_verifie sont vides : dis ce qui a été lancé, ou ce qui ne l'a pas été")
    plan = data.get("plan", [])
    if not _texts(plan, empty_ok=True):
        errors.append("plan : une liste d'étapes")
    elif sized["size"] == "S-M" and not plan:
        errors.append("plan : un changement de taille S-M porte son plan dans la description")
    if sized["size"] == "L":
        plan_file = data.get("plan_fichier")
        if not _text(plan_file) or not plan_file.startswith(plans_dir + "/") or plan_file not in sized["paths"]:
            errors.append(f"plan_fichier : un changement de taille L a son plan dans {plans_dir}/, commité dans "
                          "cette branche et validé par un humain avant le code")
    return errors


def checked(table: dict[str, Any], data: Any, repo: str, base: str) -> tuple[dict[str, Any], dict[str, Any]]:
    sized = size_mod.classify(table, repo, base)
    if not sized["files"]:
        raise Refused(f"aucun changement entre {base} et HEAD : rien à proposer")
    errors = validate(data, sized, table["plans_dir"])
    if errors:
        raise Refused("corps de PR refusé :\n- " + "\n- ".join(errors))
    return data, sized


def _line(text: str) -> str:
    """Une ligne et une seule : un texte ne peut pas ouvrir une section à lui."""
    return " ".join(text.split())


def render_md(data: dict[str, Any], sized: dict[str, Any]) -> str:
    out = ["## Ce qui change", *[f"- {_line(q)}" for q in data["quoi"]], "", "## Pourquoi", _line(data["pourquoi"])]
    out.append(f"Ticket : {_line(data['ticket'])}" if data.get("ticket") else "Ticket : aucun.")
    plan = [f"- {_line(p)}" for p in data.get("plan", [])]
    if data.get("plan_fichier") and sized["size"] == "L":
        plan.insert(0, f"Plan écrit : `{_line(data['plan_fichier'])}`.")
    if plan:
        out += ["", "## Plan", *plan]
    checks = [f"- `{_line(c['commande']).replace('`', chr(39))}` : {_line(c['resultat'])}" for c in data["verifie"]]
    out += ["", "## Vérifié", *(checks or ["Rien n'a été lancé."])]
    out += ["", "## Pas vérifié", *([f"- {_line(u)}" for u in data["non_verifie"]] or ["Rien de signalé."])]
    out += ["", "---", f"Taille calculée : {sized['size']} — {sized['files']} fichiers, {sized['lines']} lignes changées."]
    out += [f"Zone sensible : `{hit['path']}` (`{hit['glob']}`, {hit['origin']})." for hit in sized["sensitive"]]
    return "\n".join(out) + "\n"
