"""Le résultat d'une revue : sa forme, sa preuve, son rendu, et sa note sur une fixture.

Ce que le skill review promet (sept constats au plus, chacun avec une ligne du diff et ses quatre
parties) est tenu ici, pas dans son texte : une revue qui ne passe pas `render` n'est pas rendue.
`grade` et `init_fixture` servent à mesurer le skill sur une PR piégée dont on connaît le corrigé."""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from typing import Any

from .context import Refused, _git, _is_head, resolve_base

MAX_CONSTATS = 7
MAX_SPAN = 20  # lignes qu'un constat peut citer d'un coup : au-delà, il ne cite plus, il englobe
GRAVITES = {"bloquant": "bloquant", "a-corriger": "à corriger", "a-discuter": "à discuter"}
PARTS = {"attendu": "Attendu", "observe": "Observé", "conseille": "Conseillé"}
_WHERE = re.compile(r"\A(?P<path>[^:\s][^:\n]*):(?P<first>[0-9]{1,9})(?:-(?P<last>[0-9]{1,9}))?\Z")
_HUNK = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@")
_FIXED = {"GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_SYSTEM": os.devnull, "GIT_AUTHOR_NAME": "fixture", "GIT_AUTHOR_EMAIL": "fixture@example.com",
          "GIT_COMMITTER_NAME": "fixture", "GIT_COMMITTER_EMAIL": "fixture@example.com",
          "GIT_AUTHOR_DATE": "2026-01-01T00:00:00Z", "GIT_COMMITTER_DATE": "2026-01-01T00:00:00Z"}


def parse_where(text: Any) -> tuple[str, int, int]:
    """`chemin:ligne` ou `chemin:début-fin`, chemin relatif au dépôt ; ValueError sinon."""
    match = _WHERE.match(text) if isinstance(text, str) else None
    if not match:
        raise ValueError(f"{text!r} : attendu chemin:ligne ou chemin:début-fin")
    path, first = match["path"], int(match["first"])
    last = int(match["last"] or first)
    if path.startswith(("/", "./")) or ".." in path.split("/") or first < 1 or last < first:
        raise ValueError(f"{text!r} : chemin relatif au dépôt, lignes à partir de 1, début avant fin")
    if last - first >= MAX_SPAN:
        raise ValueError(f"{text!r} : au plus {MAX_SPAN} lignes citées, vise la ligne qui porte le défaut")
    return path, first, last


def validate(data: Any) -> list[str]:
    """Ce qui manque à une revue pour être rendue ; liste vide si elle est complète."""
    if not isinstance(data, dict):
        return ["la revue est un objet JSON avec les clés constats et non_verifie"]
    constats = data.get("constats")
    if not isinstance(constats, list):
        return ["constats : une liste, vide s'il n'y a rien à dire"]
    errors = []
    unchecked = data.get("non_verifie", [])
    if not isinstance(unchecked, list) or not all(isinstance(u, str) for u in unchecked):
        errors.append("non_verifie : une liste de phrases")
    if len(constats) > MAX_CONSTATS:
        errors.append(f"{len(constats)} constats, au plus {MAX_CONSTATS} : garde les plus graves")
    for index, item in enumerate(constats, 1):
        if not isinstance(item, dict):
            errors.append(f"constat {index} : un objet")
            continue
        if not isinstance(item.get("gravite"), str) or item["gravite"] not in GRAVITES:
            errors.append(f"constat {index} : gravite {item.get('gravite')!r} inconnue ({', '.join(GRAVITES)})")
        try:
            parse_where(item.get("sur_quoi"))
        except ValueError as exc:
            errors.append(f"constat {index} : sur_quoi {exc}")
        for key in ("point", *PARTS):
            if not isinstance(item.get(key), str) or not item[key].strip():
                errors.append(f"constat {index} : {key} est vide")
    return errors


def changed_lines(repo: str, base: str) -> dict[str, set[int]]:
    """Par fichier, les lignes que le changement ajoute ou modifie, numérotées côté HEAD. Une
    suppression se cite à la ligne où elle a eu lieu (celle d'avant ou celle d'après), un fichier
    supprimé à sa ligne 1. Les chemins viennent de la liste de git, jamais du texte du diff : une
    ligne ajoutée qui imite un en-tête ne rend pas citable un fichier que la PR ne touche pas."""
    commit = resolve_base(repo, base)
    span = f"{commit}...HEAD"
    code, out = _git(repo, "diff", "-z", "--name-only", "--no-renames", span)
    if code != 0:
        raise Refused(f"diff impossible entre {base} et HEAD dans {repo}")
    changed: dict[str, set[int]] = {}
    for raw in filter(None, out.split(b"\0")):
        path = raw.decode("utf-8", "replace")
        code, patch = _git(repo, "--literal-pathspecs", "diff", "-U0", "--no-color", "--no-ext-diff", "--no-textconv",
                           "--no-renames", span, "--", path)
        if code != 0:
            raise Refused(f"diff impossible pour {path} entre {base} et HEAD")
        lines = changed.setdefault(path, set())
        for line in patch.decode("utf-8", "replace").splitlines():
            match = _HUNK.match(line)  # en -U0, seule une tête de bloc commence par @@
            if match:
                start, count = int(match[1]), int(match[2] if match[2] is not None else 1)
                lines.update(n for n in (range(start, start + count) if count else (start, start + 1)) if n >= 1)
    return changed


def outside_diff(data: dict[str, Any], changed: dict[str, set[int]]) -> list[str]:
    """Les constats dont aucune ligne citée n'est dans le diff."""
    errors = []
    for index, item in enumerate(data["constats"], 1):
        path, first, last = parse_where(item["sur_quoi"])
        if not any(first <= n <= last for n in changed.get(path, ())):
            errors.append(f"constat {index} : {item['sur_quoi']} n'est pas une ligne du diff")
    return errors


def load(path: str) -> Any:
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError, RecursionError) as exc:
        raise Refused(f"{path} : illisible ({exc})") from exc


def checked(path: str, repo: str, base: str) -> dict[str, Any]:
    """La revue du fichier, si elle est complète et que chaque constat cite le diff ; Refused sinon."""
    data = load(path)
    errors = validate(data)
    if not errors:
        if _is_head(repo, resolve_base(repo, base)):
            raise Refused(f"{base} est le commit relu lui-même : il n'y a pas de diff à citer, donne la branche cible")
        errors = outside_diff(data, changed_lines(repo, base))
    if errors:
        raise Refused("revue refusée :\n- " + "\n- ".join(errors))
    return data


def _cell(text: str) -> str:
    """Un texte de constat tenu dans une cellule : ni saut de ligne, ni barre, ni titre forgé."""
    flat = " ".join(text.split()).replace("&", "&amp;").replace("<", "&lt;")
    for char in "|[]":
        flat = flat.replace(char, "\\" + char)
    return flat.replace("@", "@\u200b")  # ni HTML, ni lien, ni image, ni mention qui notifie


def _code(text: str) -> str:
    return "`" + " ".join(text.split()).replace("`", "'").replace("|", "/") + "`"


def _ordered(constats: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rank = list(GRAVITES)
    return sorted(constats, key=lambda c: rank.index(c["gravite"]))


def render_md(data: dict[str, Any]) -> str:
    constats = _ordered(data["constats"])
    counts = [f"{label} : {n}" for key, label in GRAVITES.items()
              if (n := sum(c["gravite"] == key for c in constats))]
    out = ["# Revue", "", ("Constats — " + ", ".join(counts) + ".") if counts else "Aucun constat."]
    unchecked = data.get("non_verifie") or []
    out += ["", "Non vérifié :"] + [f"- {_cell(u)}" for u in unchecked] if unchecked else ["", "Non vérifié : rien de signalé."]
    for index, item in enumerate(constats, 1):
        out += ["", f"## {index}. {GRAVITES[item['gravite']].capitalize()} — {_code(item['sur_quoi'])}", "",
                "| Partie | Contenu |", "|---|---|",
                f"| Sur quoi | {_code(item['sur_quoi'])} — {_cell(item['point'])} |"]
        out += [f"| {label} | {_cell(item[key])} |" for key, label in PARTS.items()]
    return "\n".join(out) + "\n"


# --- Fixtures : une PR piégée, son corrigé, la note ---------------------------------------------------

def _overlaps(item: dict[str, Any], place: dict[str, Any]) -> bool:
    path, first, last = parse_where(item["sur_quoi"])
    return path == place["file"] and first <= place["lines"][1] and last >= place["lines"][0]


def _place_ok(place: Any) -> bool:
    lines = place.get("lines") if isinstance(place, dict) else None
    return (isinstance(place.get("file"), str) and isinstance(lines, list) and len(lines) == 2
            and all(type(n) is int for n in lines) and 1 <= lines[0] <= lines[1]) if lines is not None else False


def check_expected(expected: Any) -> None:
    """Un corrigé vide ou cassé ne note rien : Refused, plutôt qu'un « conforme » qui ne veut rien dire."""
    if not isinstance(expected, dict):
        raise Refused("corrigé : un objet JSON avec traps et healthy")
    traps, healthy = expected.get("traps"), expected.get("healthy")
    if not isinstance(traps, list) or not isinstance(healthy, list):
        raise Refused("corrigé : traps et healthy sont des listes")
    limit = expected.get("max_constats", MAX_CONSTATS)
    if type(limit) is not int or limit < 1:
        raise Refused("corrigé : max_constats est un entier positif")
    for trap in traps:
        if not (isinstance(trap, dict) and isinstance(trap.get("id"), str) and isinstance(trap.get("what"), str)
                and type(trap.get("must")) is bool and isinstance(trap.get("where"), list) and trap["where"]
                and all(_place_ok(w) for w in trap["where"])):
            raise Refused(f"corrigé : piège mal formé ({trap!r:.80})")
    for item in healthy:
        if not (_place_ok(item) and isinstance(item.get("id"), str) and isinstance(item.get("what"), str)):
            raise Refused(f"corrigé : élément sain mal formé ({item!r:.80})")
    if not any(t["must"] for t in traps):
        raise Refused("corrigé : aucun piège requis, il ne peut rien mesurer")


def _match(traps: list[dict[str, Any]], constats: list[dict[str, Any]]) -> dict[str, int]:
    """Un constat ne trouve qu'un piège : le plus grand appariement, les pièges requis servis d'abord."""
    owner: dict[int, str] = {}
    by_id = {t["id"]: t for t in traps}

    def claim(trap_id: str, seen: set[int]) -> bool:
        for index, item in enumerate(constats):
            if index in seen or not any(_overlaps(item, w) for w in by_id[trap_id]["where"]):
                continue
            seen.add(index)
            if index not in owner or claim(owner[index], seen):
                owner[index] = trap_id
                return True
        return False

    for trap in sorted(traps, key=lambda t: not t["must"]):
        claim(trap["id"], set())
    return {trap_id: index for index, trap_id in owner.items()}


def grade(expected: Any, data: Any) -> dict[str, Any]:
    """Généreux sur les mots, strict sur la preuve : un piège est trouvé si un constat cite une de
    ses lignes, et un constat ne trouve qu'un piège ; un constat sur une ligne saine fait échouer ;
    le reste est du bruit, compté."""
    check_expected(expected)
    invalid = validate(data)
    limit = expected.get("max_constats", MAX_CONSTATS)
    traps = expected["traps"]
    if invalid:
        return {"pass": False, "invalid": invalid, "found": [], "missed": [t["id"] for t in traps if t["must"]],
                "optional_missed": [], "healthy_touched": [], "noise": [], "count": 0, "max": limit}
    constats = data["constats"]
    matched = _match(traps, constats)
    found = [t["id"] for t in traps if t["id"] in matched]
    touched = [h["id"] for h in expected["healthy"] if any(_overlaps(c, h) for c in constats)]
    places = [w for t in traps for w in t["where"]] + expected["healthy"]
    noise = [c["sur_quoi"] for c in constats if not any(_overlaps(c, p) for p in places)]
    missed = [t["id"] for t in traps if t["must"] and t["id"] not in found]
    return {"pass": not missed and not touched and len(constats) <= limit, "invalid": [], "found": found,
            "missed": missed, "optional_missed": [t["id"] for t in traps if not t["must"] and t["id"] not in found],
            "healthy_touched": touched, "noise": noise, "count": len(constats), "max": limit}


def render_grade_md(expected: dict[str, Any], result: dict[str, Any]) -> str:
    what = {entry["id"]: entry["what"] for entry in expected["traps"] + expected["healthy"]}
    musts = [t["id"] for t in expected["traps"] if t["must"]]
    out = [f"{'CONFORME' if result['pass'] else 'NON CONFORME'} — pièges requis trouvés : "
           f"{len(musts) - len(result['missed'])}/{len(musts)}, constats : {result['count']}/{result['max']}"]
    out += [f"- revue invalide : {e}" for e in result["invalid"]]
    out += [f"- manqué : {i} — {what[i]}" for i in result["missed"]]
    out += [f"- manqué (facultatif) : {i} — {what[i]}" for i in result["optional_missed"]]
    out += [f"- sain commenté : {i} — {what[i]}" for i in result["healthy_touched"]]
    out += [f"- hors corrigé : {w}" for w in result["noise"]]
    return "\n".join(out) + "\n"


_ISOLATED = ("-c", "core.hooksPath=" + os.devnull, "-c", "commit.gpgsign=false", "-c", "core.autocrlf=false")


def _run(dest: str, *args: str) -> None:
    """git sans la configuration, les hooks ni les modèles de l'utilisateur : la fixture se monte pareil partout."""
    out = subprocess.run(["git", "-C", dest, *_ISOLATED, *args], capture_output=True,
                         env={**os.environ, **_FIXED}, timeout=30)
    if out.returncode != 0:
        raise Refused(f"git {args[0]} a échoué dans {dest} : {out.stderr.decode('utf-8', 'replace').strip()}")


def init_fixture(fixture_dir: str, dest: str) -> dict[str, str]:
    """Monte la fixture en dépôt git : `base/` commité sur main, puis, si elle porte une PR (`pr.json`),
    `pr/` par-dessus sur sa branche. Sans PR, le dépôt s'arrête à main : c'est une fixture de `/dev`."""
    has_pr = os.path.exists(os.path.join(fixture_dir, "pr.json"))
    spec = load(os.path.join(fixture_dir, "pr.json")) if has_pr else {}
    if os.path.exists(dest) and (not os.path.isdir(dest) or os.listdir(dest)):
        raise Refused(f"{dest} existe et n'est pas vide : donne un dossier neuf")
    try:
        branch = spec["branch"] if has_pr else None
        message = f"{spec['title']}\n\n{spec['body']}" if has_pr else ""
        removed = spec.get("removed", [])
        if any(not isinstance(r, str) or r.startswith("/") or ".." in r.split("/") for r in removed):
            raise Refused(f"fixture {fixture_dir} : removed ne cite que des chemins relatifs au dépôt")
        shutil.copytree(os.path.join(fixture_dir, "base"), dest, symlinks=True, dirs_exist_ok=True)
        _run(dest, "init", "-q", "-b", "main", "--template=")
        _run(dest, "add", "-A")
        _run(dest, "commit", "-q", "--no-verify", "-m", "base")
        if not has_pr:
            return {"repo": dest, "base": "main", "branch": "main"}
        _run(dest, "checkout", "-q", "-b", branch)
        shutil.copytree(os.path.join(fixture_dir, "pr"), dest, symlinks=True, dirs_exist_ok=True)
        for rel in removed:
            os.remove(os.path.join(dest, rel))
        _run(dest, "add", "-A")
        _run(dest, "commit", "-q", "--no-verify", "-m", message)
    except (OSError, KeyError, TypeError, AttributeError, subprocess.TimeoutExpired, Refused) as exc:
        shutil.rmtree(dest, ignore_errors=True)  # un montage à moitié fait ne se relit pas
        if isinstance(exc, Refused):
            raise
        raise Refused(f"fixture {fixture_dir} : montage impossible ({exc!r})") from exc
    return {"repo": dest, "base": "main", "branch": branch}
