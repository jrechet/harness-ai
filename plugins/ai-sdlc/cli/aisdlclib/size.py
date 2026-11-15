"""La taille d'un changement, calculée par règles : elle choisit le chemin de `/dev`.

XS part droit en PR, S–M porte son plan dans la description, L ou zone sensible exige un plan écrit
dans le dépôt et validé par un humain avant le code. Les zones sensibles sont celles du socle plus
celles de l'équipe (`docs/agents/zones-sensibles.md`), lues sur la branche de base : une PR ne peut
pas sortir ses propres fichiers de la liste."""
from __future__ import annotations

import re
from typing import Any

from . import points as points_mod
from .context import Refused, _git, _is_head, _override, resolve_base

SIZES = ("XS", "S-M", "L")
PATHS = {"XS": "PR directe, pas de plan écrit",
         "S-M": "plan dans la description de la PR",
         "L": "plan écrit dans le dépôt et validé par un humain avant le code"}
_ZONE = re.compile(r"^\s*[-*]\s+((?:`[^`]+`\s*,?\s*)+)(.*)$")


def glob_regex(glob: str) -> re.Pattern[str]:
    """Un motif de chemin : `*` reste dans un dossier, `**` en traverse autant qu'il faut."""
    out, index = [], 0
    while index < len(glob):
        if glob.startswith("**/", index):
            out.append("(?:.*/)?")
            index += 3
        elif glob.startswith("**", index):
            out.append(".*")
            index += 2
        elif glob[index] == "*":
            out.append("[^/]*")
            index += 1
        elif glob[index] == "?":
            out.append("[^/]")
            index += 1
        else:
            out.append(re.escape(glob[index]))
            index += 1
    return re.compile("".join(out) + r"\Z")


def parse_zones(text: str, origin: str) -> list[dict[str, str]]:
    """Les lignes `- `motif`, `motif` — pourquoi` d'un texte de zones sensibles."""
    zones = []
    for line in text.splitlines():
        match = _ZONE.match(line)
        if not match:
            continue
        why = match[2].strip().lstrip("—–-: ").strip()
        zones += [{"glob": glob.strip(), "why": why, "origin": origin} for glob in re.findall(r"`([^`]+)`", match[1])]
    return zones


def zones(table: dict[str, Any], repo: str, base: str) -> list[dict[str, str]]:
    point = table["points"]["zones-sensibles"]
    override, _ = _override(table, repo, "zones-sensibles", base, resolve_base(repo, base), worktree=False)
    found = parse_zones(points_mod.default_text(point) or "", "socle")
    return found + (parse_zones(override["text"], "equipe") if override else [])


def diff_stats(repo: str, base: str) -> list[dict[str, Any]]:
    """Par fichier du changement : lignes ajoutées et retirées (0 pour un binaire)."""
    commit = resolve_base(repo, base)
    if _is_head(repo, commit):
        raise Refused(f"{base} est le commit courant : il n'y a pas de changement à mesurer, donne la branche cible")
    code, out = _git(repo, "diff", "-z", "--numstat", "--no-renames", f"{commit}...HEAD")
    if code != 0:
        raise Refused(f"diff impossible entre {base} et HEAD dans {repo}")
    stats = []
    for entry in filter(None, out.split(b"\0")):
        added, deleted, path = entry.decode("utf-8", "replace").split("\t", 2)
        stats.append({"path": path, "lines": sum(int(n) for n in (added, deleted) if n.isdigit())})
    return stats


def touched(paths: list[str], found: list[dict[str, str]]) -> list[dict[str, str]]:
    """Chaque fichier qui tombe dans une zone sensible, avec la première zone qui le prend."""
    compiled = [(zone, glob_regex(zone["glob"])) for zone in found]
    hits = []
    for path in paths:
        zone = next((zone for zone, regex in compiled if regex.match(path)), None)
        if zone:
            hits.append({"path": path, **zone})
    return hits


def classify(table: dict[str, Any], repo: str, base: str, paths: list[str] | None = None) -> dict[str, Any]:
    """La taille du changement en cours, ou, avec `paths`, ce qu'on sait avant d'avoir écrit le code :
    une zone sensible suffit à dire L, le reste attend le diff."""
    found = zones(table, repo, base)
    planned = paths is not None
    stats = [{"path": p, "lines": 0} for p in paths] if planned else diff_stats(repo, base)
    files, lines = len(stats), sum(s["lines"] for s in stats)
    sensitive = touched([s["path"] for s in stats], found)
    reasons = [f"{hit['path']} est dans la zone sensible `{hit['glob']}` ({hit['origin']})" for hit in sensitive]
    if sensitive:
        size = "L"
    elif planned:
        size = None
        reasons.append("aucune zone sensible dans les chemins prévus : XS ou S-M, à mesurer sur le diff avant la PR")
    else:
        limits = table["sizes"]
        size = next((name for name in ("XS", "S-M")
                     if files <= limits[name]["files"] and lines <= limits[name]["lines"]), "L")
        reasons.append(f"{files} fichiers, {lines} lignes changées")
    return {"size": size, "path": PATHS.get(size), "planned": planned, "files": files, "lines": lines,
            "sensitive": sensitive, "reasons": reasons, "paths": [s["path"] for s in stats]}


def render_md(result: dict[str, Any]) -> str:
    head = f"Taille : {result['size']} — {result['path']}." if result["size"] else "Taille : pas encore tranchée."
    return "\n".join([head, *[f"- {reason}" for reason in result["reasons"]]]) + "\n"
