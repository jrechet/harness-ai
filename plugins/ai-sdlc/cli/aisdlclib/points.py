"""The extension points: the contract between the base convention and the teams.

Each phase reads named points. A point has a base convention (or none), says whether a team can
replace it or only append to it, and on which branch its override is read. Renaming a point breaks
the teams: it is the public API of the framework. The French names used before 2026-11-16 are still
read, as file names of team overrides (`FORMER_NAMES`)."""
from __future__ import annotations

import json
import os
from typing import Any

HERE = os.path.dirname(os.path.abspath(__file__))
PLUGIN_ROOT = os.path.dirname(os.path.dirname(HERE))
FILE = os.path.join(HERE, "points.json")
BRANCHES = ("base", "current")
# The names the points had before they were translated; an override file under the old name is still read.
FORMER_NAMES = {"definition-of-ready": "definition-de-pret", "definition-of-done": "definition-de-fini",
                "review": "revue", "security": "securite", "sensitive-zones": "zones-sensibles",
                "delivery": "livraison", "operations": "exploitation"}


def load(path: str = FILE) -> dict[str, Any]:
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def default_text(point: dict[str, Any]) -> str | None:
    """The base convention for this point, or None if it has none yet."""
    if not point.get("default"):
        return None
    with open(os.path.join(PLUGIN_ROOT, point["default"]), encoding="utf-8") as fh:
        return fh.read().strip()


def validate(table: dict[str, Any]) -> list[str]:
    errors = []
    if not isinstance(table.get("budget_lines"), int) or table["budget_lines"] < 1:
        errors.append("budget_lines: expected a positive integer")
    sizes = table.get("sizes")
    if not (isinstance(sizes, dict) and list(sizes) == ["XS", "S-M"] and all(
            isinstance(sizes[n], dict) and type(sizes[n].get(k)) is int and sizes[n][k] > 0
            for n in sizes for k in ("files", "lines"))):
        errors.append("sizes: XS then S-M, each with files and lines as positive integers")
    elif any(sizes["XS"][k] > sizes["S-M"][k] for k in ("files", "lines")):
        errors.append("sizes: the XS thresholds do not exceed those of S-M")
    if not isinstance(table.get("plans_dir"), str) or not table["plans_dir"]:
        errors.append("plans_dir: the folder of written plans")
    settings = table.get("qa")
    if not (isinstance(settings, dict) and type(settings.get("runs")) is int and 1 <= settings["runs"] <= 20
            and type(settings.get("diff_coverage")) is int and 0 <= settings["diff_coverage"] <= 100):
        errors.append("qa: runs between 1 and 20, diff_coverage between 0 and 100")
    phases = table.get("phases", {})
    for name, point in table.get("points", {}).items():
        if not isinstance(point.get("replaceable"), bool):
            errors.append(f"{name}: replaceable is true or false")
        if point.get("branch") not in BRANCHES:
            errors.append(f"{name}: branch is {' or '.join(BRANCHES)}")
        unknown = [p for p in point.get("read_by", []) if p not in phases]
        if unknown or not point.get("read_by"):
            errors.append(f"{name}: read_by names an unknown phase or none ({', '.join(unknown)})")
        if point.get("default") and not os.path.isfile(os.path.join(PLUGIN_ROOT, point["default"])):
            errors.append(f"{name}: convention {point['default']} not found")
    return errors
