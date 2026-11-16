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


def _git(repo: str, *args: str) -> tuple[int, bytes]:
    try:
        out = subprocess.run(["git", "-C", repo, "-c", "core.fsmonitor=false", "-c", "core.hooksPath=/dev/null", *args], capture_output=True, timeout=20)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise Refused(f"git {args[0]} n'a pas répondu dans {repo} : {exc}") from exc
    return out.returncode, out.stdout


def _decode(raw: bytes, rel: str) -> str:
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise Refused(f"{rel} : le fichier n'est pas du texte UTF-8") from exc


def resolve_base(repo: str, base: str) -> str:
    if not base or base.startswith("-"):
        raise Refused(f"branche de base {base!r} invalide : un nom de branche, de tag ou un commit")
    code, out = _git(repo, "rev-parse", "--short", "--verify", "--quiet", f"{base}^{{commit}}")
    if code != 0 or not out.strip():
        raise Refused(f"branche de base {base} introuvable dans {repo} : passe --base <ref>")
    return out.decode("ascii", "replace").strip()


def _is_head(repo: str, commit: str) -> bool:
    """La base est-elle le commit relu lui-même ? Alors rien ne sépare la PR de ses propres règles."""
    code, out = _git(repo, "rev-parse", "--short", "--verify", "--quiet", "HEAD^{commit}")
    return code == 0 and out.decode("ascii", "replace").strip() == commit


def _read_at(repo: str, commit: str, rel: str) -> str | None:
    """Le fichier tel qu'il est dans ce commit ; None s'il n'y est pas. Toute autre erreur refuse :
    une porte qui ne peut pas lire ses règles ne les remplace pas par le défaut."""
    code, out = _git(repo, "ls-tree", commit, "--", rel)
    if code != 0:
        raise Refused(f"{rel} : lecture impossible dans {commit}")
    entry = out.decode("utf-8", "replace").strip()
    if not entry:
        return None
    if not entry.startswith("100"):
        raise Refused(f"{rel} : attendu un fichier ordinaire dans {commit}, pas un lien ni un dossier")
    code, out = _git(repo, "show", f"{commit}:{rel}")
    if code != 0:
        raise Refused(f"{rel} : lecture impossible dans {commit}")
    return _decode(out, rel)


def is_file_at(repo: str, commit: str, rel: str) -> bool:
    """Ce chemin est-il un fichier ordinaire de ce commit ? Sans lire son contenu, et sans motif de chemin."""
    if not rel or rel.startswith(("/", "-")) or ".." in rel.split("/") or "\0" in rel or len(rel) > 300:
        return False
    if rel.endswith("/") or "." in (rel, *rel.split("/")) or "" in rel.split("/"):
        return False
    code, out = _git(repo, "--literal-pathspecs", "ls-tree", "-z", commit, "--", rel)
    entries = [e for e in out.decode("utf-8", "replace").split("\0") if e] if code == 0 else []
    return len(entries) == 1 and entries[0].startswith("100") and entries[0].partition("\t")[2] == rel


def _read_worktree(repo: str, rel: str) -> str | None:
    path = os.path.join(repo, rel)
    if os.path.islink(path):
        raise Refused(f"{rel} : attendu un fichier ordinaire, pas un lien")
    if not os.path.isfile(path):
        return None
    try:
        with open(path, "rb") as fh:
            return _decode(fh.read(), rel)
    except OSError as exc:
        raise Refused(f"{rel} : lecture impossible ({exc})") from exc


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
    if any(line.lstrip().startswith("#") for line in body):
        raise Refused(f"{name} : pas de titre (ligne en #) dans une surcharge, seulement des règles")
    if len(body) > budget:
        raise Refused(f"{name} : {len(body)} lignes, au plus {budget} ; ce qui déborde va dans un skill d'équipe")
    return {"mode": mode, "why": header.get("pourquoi"), "text": "\n".join(body), "lines": len(body)}


def _override(table: dict[str, Any], repo: str, name: str, base: str, commit: str,
              worktree: bool) -> tuple[dict[str, Any] | None, str | None]:
    """La surcharge d'un point là où elle doit se lire, et un avertissement si une autre existe ailleurs."""
    point = table["points"][name]
    rel = f"{table['override_dir']}/{name}.md"
    on_base = point["branch"] == "base" and not worktree
    warning = None
    if on_base:
        text = _read_at(repo, commit, rel)
        try:  # la copie de travail ne sert qu'à prévenir : illisible, elle ne bloque pas la revue
            here = _read_worktree(repo, rel)
        except Refused:
            here = ""
        if here is not None and here != text:
            warning = f"{rel} diffère de {base} dans la copie de travail : c'est la version de {base} qui est lue"
    else:
        text = _read_worktree(repo, rel)
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
    same = _is_head(repo, commit)
    if same and not worktree:
        warnings.append(f"{base} est le commit relu lui-même : rien ne sépare ce changement de ses propres règles")
    reached = read_level(repo)
    needed = table["phases"][phase]["min_level"]
    return {"phase": phase, "base": base, "commit": commit, "gate": not worktree and not same, "blocks": blocks,
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
        out.append("Ce contexte ne vaut pas pour une porte : les règles ne viennent pas d'une branche de base distincte.")
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
