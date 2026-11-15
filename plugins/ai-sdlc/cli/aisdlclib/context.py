"""Assemble le contexte d'une phase : la convention du socle, puis ce que l'équipe ajoute.

L'assemblage est fait ici, par des règles écrites, pas par le modèle : deux textes contradictoires
laissés au modèle, il en choisit un au hasard. Chaque bloc porte sa provenance. Une surcharge qui
sert de porte (revue, sécurité…) se lit sur la branche de base : une PR ne peut pas alléger sa propre
revue. Une surcharge invalide arrête tout : on ne relit pas avec des règles à moitié comprises."""
from __future__ import annotations

import json
import os
import subprocess
from typing import Any

MODES = ("ajoute", "remplace")


class Refused(ValueError):
    """La demande ne peut pas être servie telle quelle ; le message dit quoi corriger."""


def _git(repo: str, *args: str) -> tuple[int, str]:
    try:
        out = subprocess.run(["git", "-C", repo, *args], capture_output=True, text=True, timeout=20)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return 1, str(exc)
    return out.returncode, out.stdout


def resolve_base(repo: str, base: str) -> str:
    if not base or base.startswith("-"):
        raise Refused(f"branche de base {base!r} invalide : un nom de branche, de tag ou un commit")
    code, out = _git(repo, "rev-parse", "--short", "--verify", "--quiet", f"{base}^{{commit}}")
    if code != 0 or not out.strip():
        raise Refused(f"branche de base {base} introuvable dans {repo} : passe --base <ref>")
    return out.strip()


def _read_at(repo: str, ref: str, rel: str) -> str | None:
    code, out = _git(repo, "show", f"{ref}:{rel}")
    return out if code == 0 else None


def _read_worktree(repo: str, rel: str) -> str | None:
    path = os.path.join(repo, rel)
    if not os.path.isfile(path):
        return None
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def parse_override(name: str, point: dict[str, Any], text: str, budget: int) -> dict[str, Any]:
    """L'en-tête et le corps d'une surcharge ; Refused si elle ne respecte pas le contrat du point."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---" or "---" not in [line.strip() for line in lines[1:]]:
        raise Refused(f"{name} : en-tête manquant (--- point: {name} / mode: ajoute ---)")
    end = [line.strip() for line in lines[1:]].index("---") + 1
    header = {}
    for line in lines[1:end]:
        key, sep, value = line.split("#", 1)[0].partition(":")
        if sep and key.strip():
            header[key.strip()] = value.strip()
    if header.get("point") != name:
        raise Refused(f"{name} : l'en-tête dit point: {header.get('point')}, le fichier s'appelle {name}.md")
    mode = header.get("mode")
    if mode not in MODES:
        raise Refused(f"{name} : mode {mode} inconnu ({', '.join(MODES)})")
    if mode == "remplace" and not point["replaceable"]:
        raise Refused(f"{name} : ce point ne se remplace pas, une équipe peut seulement y ajouter (mode: ajoute)")
    if mode == "remplace" and not header.get("pourquoi"):
        raise Refused(f"{name} : remplace exige un champ pourquoi dans l'en-tête")
    body = [line for line in lines[end + 1:] if line.strip()]
    if len(body) > budget:
        raise Refused(f"{name} : {len(body)} lignes, au plus {budget} ; ce qui déborde va dans un skill d'équipe")
    return {"mode": mode, "why": header.get("pourquoi"), "text": "\n".join(body), "lines": len(body)}


def _override(table: dict[str, Any], repo: str, name: str, base: str, commit: str,
              worktree: bool) -> tuple[dict[str, Any] | None, str | None]:
    """La surcharge d'un point là où elle doit se lire, et un avertissement si une autre existe ailleurs."""
    point = table["points"][name]
    rel = f"{table['override_dir']}/{name}.md"
    here = _read_worktree(repo, rel)
    on_base = point["branch"] == "base" and not worktree
    text = _read_at(repo, commit, rel) if on_base else here
    warning = None
    if on_base and here is not None and here != text:
        warning = f"{rel} diffère de {base} dans la copie de travail : c'est la version de {base} qui est lue"
    if text is None:
        return None, warning
    parsed = parse_override(name, point, text, table["budget_lines"])
    source = {"path": rel, "ref": base if on_base else "copie de travail",
              "commit": commit if on_base else None, "mode": parsed["mode"], "why": parsed["why"]}
    return {**parsed, "source": source}, warning


def read_level(repo: str) -> int | None:
    """Le palier harness-ai du dépôt, lu dans .harness/state.json sans rien y écrire."""
    try:
        with open(os.path.join(repo, ".harness", "state.json"), encoding="utf-8") as fh:
            reached = json.load(fh).get("level", {}).get("reached")
    except (OSError, json.JSONDecodeError, AttributeError):
        return None
    return reached if isinstance(reached, int) else None


def assemble(table: dict[str, Any], repo: str, phase: str, base: str, worktree: bool = False) -> dict[str, Any]:
    from . import points as points_mod
    if phase not in table["phases"]:
        raise Refused(f"phase {phase} inconnue ({', '.join(table['phases'])})")
    commit = resolve_base(repo, base)
    blocks, warnings = [], []
    for name, point in table["points"].items():
        if phase not in point["read_by"]:
            continue
        override, warning = _override(table, repo, name, base, commit, worktree)
        if warning:
            warnings.append(warning)
        default = points_mod.default_text(point)
        if default and not (override and override["mode"] == "remplace"):
            blocks.append({"point": name, "origin": "socle", "text": default, "source": {"path": point["default"]}})
        if override:
            blocks.append({"point": name, "origin": "equipe", "text": override["text"], "source": override["source"]})
    reached = read_level(repo)
    needed = table["phases"][phase]["min_level"]
    return {"phase": phase, "base": base, "commit": commit, "gate": not worktree, "blocks": blocks,
            "warnings": warnings,
            "level": {"reached": reached, "needed": needed, "open": reached is not None and reached >= needed}}


def status(table: dict[str, Any], repo: str, base: str) -> list[dict[str, Any]]:
    """Chaque point d'extension : convention du socle, surchargé, ou surcharge invalide."""
    commit = resolve_base(repo, base)
    rows = []
    for name, point in table["points"].items():
        row = {"point": name, "read_by": point["read_by"], "replaceable": point["replaceable"],
               "has_default": bool(point.get("default")), "state": "convention"}
        try:
            override, _ = _override(table, repo, name, base, commit, worktree=False)
        except Refused as exc:
            rows.append({**row, "state": "invalide", "reason": str(exc)})
            continue
        if override:
            row = {**row, "state": "surchargé", "mode": override["mode"], "lines": override["lines"],
                   "path": override["source"]["path"]}
        rows.append(row)
    return rows


# --- Rendu -----------------------------------------------------------------------------------------

def render_context_md(result: dict[str, Any]) -> str:
    level = result["level"]
    seen = "non mesuré (lance harness status)" if level["reached"] is None else str(level["reached"])
    out = [f"# Contexte de la phase {result['phase']}", "",
           f"Branche de base : {result['base']} ({result['commit']}). Palier harness-ai : {seen}, "
           f"la phase s'ouvre au palier {level['needed']}."]
    if not level["open"]:
        out.append("Le palier requis n'est pas atteint : la phase reste utilisable, ses résultats sont à prendre comme un essai.")
    if not result["gate"]:
        out.append("Lu dans la copie de travail : ce contexte ne vaut pas pour une porte.")
    out += [f"Attention : {w}" for w in result["warnings"]]
    for block in result["blocks"]:
        src = block["source"]
        if block["origin"] == "socle":
            title = f"{block['point']} — socle ({src['path']})"
        else:
            where = f"{src['ref']} {src['commit']}" if src["commit"] else src["ref"]
            title = f"{block['point']} — équipe ({src['path']} @ {where}, {src['mode']})"
        out += ["", f"## {title}", "", block["text"]]
    if not result["blocks"]:
        out += ["", "Aucune convention ni surcharge pour cette phase."]
    return "\n".join(out) + "\n"


def render_status_md(rows: list[dict[str, Any]]) -> str:
    out = ["| Point | Lu par | État |", "|---|---|---|"]
    for row in rows:
        if row["state"] == "surchargé":
            state = f"surchargé : {row['mode']}, {row['lines']} lignes ({row['path']})"
        elif row["state"] == "invalide":
            state = f"invalide : {row['reason']}"
        else:
            state = "convention du framework" if row["has_default"] else "aucune convention encore"
        out.append(f"| `{row['point']}` | {', '.join(row['read_by'])} | {state} |")
    return "\n".join(out) + "\n"
