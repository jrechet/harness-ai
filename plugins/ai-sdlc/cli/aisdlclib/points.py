"""Les points d'extension : le contrat entre le socle et les équipes.

Chaque phase lit des points nommés. Un point a une convention du socle (ou aucune), dit si une équipe
peut la remplacer ou seulement y ajouter, et sur quelle branche sa surcharge se lit. Renommer un point
casse les équipes : c'est l'API publique du framework."""
from __future__ import annotations

import json
import os
from typing import Any

HERE = os.path.dirname(os.path.abspath(__file__))
PLUGIN_ROOT = os.path.dirname(os.path.dirname(HERE))
FILE = os.path.join(HERE, "points.json")
BRANCHES = ("base", "current")


def load(path: str = FILE) -> dict[str, Any]:
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def default_text(point: dict[str, Any]) -> str | None:
    """La convention du socle pour ce point, ou None s'il n'en a pas encore."""
    if not point.get("default"):
        return None
    with open(os.path.join(PLUGIN_ROOT, point["default"]), encoding="utf-8") as fh:
        return fh.read().strip()


def validate(table: dict[str, Any]) -> list[str]:
    errors = []
    if not isinstance(table.get("budget_lines"), int) or table["budget_lines"] < 1:
        errors.append("budget_lines : attendu un entier positif")
    sizes = table.get("sizes")
    if not (isinstance(sizes, dict) and list(sizes) == ["XS", "S-M"] and all(
            isinstance(sizes[n], dict) and type(sizes[n].get(k)) is int and sizes[n][k] > 0
            for n in sizes for k in ("files", "lines"))):
        errors.append("sizes : XS puis S-M, chacun avec files et lines entiers positifs")
    elif any(sizes["XS"][k] > sizes["S-M"][k] for k in ("files", "lines")):
        errors.append("sizes : les seuils de XS ne dépassent pas ceux de S-M")
    if not isinstance(table.get("plans_dir"), str) or not table["plans_dir"]:
        errors.append("plans_dir : le dossier des plans écrits")
    phases = table.get("phases", {})
    for name, point in table.get("points", {}).items():
        if not isinstance(point.get("replaceable"), bool):
            errors.append(f"{name} : replaceable est vrai ou faux")
        if point.get("branch") not in BRANCHES:
            errors.append(f"{name} : branch vaut {' ou '.join(BRANCHES)}")
        unknown = [p for p in point.get("read_by", []) if p not in phases]
        if unknown or not point.get("read_by"):
            errors.append(f"{name} : read_by cite une phase inconnue ou aucune ({', '.join(unknown)})")
        if point.get("default") and not os.path.isfile(os.path.join(PLUGIN_ROOT, point["default"])):
            errors.append(f"{name} : convention {point['default']} introuvable")
    return errors
