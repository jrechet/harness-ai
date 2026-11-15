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
GRAVITES = {"bloquant": "bloquant", "a-corriger": "à corriger", "a-discuter": "à discuter"}
PARTS = {"attendu": "Attendu", "observe": "Observé", "conseille": "Conseillé"}
_WHERE = re.compile(r"^(?P<path>[^:\s][^:]*):(?P<first>\d+)(?:-(?P<last>\d+))?$")
_HUNK = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@")
_FIXED = {"GIT_AUTHOR_NAME": "fixture", "GIT_AUTHOR_EMAIL": "fixture@example.com",
          "GIT_COMMITTER_NAME": "fixture", "GIT_COMMITTER_EMAIL": "fixture@example.com",
          "GIT_AUTHOR_DATE": "2026-01-01T00:00:00Z", "GIT_COMMITTER_DATE": "2026-01-01T00:00:00Z"}


def parse_where(text: Any) -> tuple[str, int, int]:
    """`chemin:ligne` ou `chemin:début-fin`, chemin relatif au dépôt ; ValueError sinon."""
    match = _WHERE.match(text) if isinstance(text, str) else None
    if not match:
        raise ValueError(f"{text!r} : attendu chemin:ligne ou chemin:début-fin")
    path, first = match["path"], int(match["first"])
    last = int(match["last"] or first)
    if path.startswith("/") or ".." in path.split("/") or first < 1 or last < first:
        raise ValueError(f"{text!r} : chemin relatif au dépôt, lignes à partir de 1, début avant fin")
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
        if item.get("gravite") not in GRAVITES:
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
    suppression se cite à la ligne où elle a eu lieu : celle d'avant et celle d'après."""
    commit = resolve_base(repo, base)
    code, out = _git(repo, "-c", "core.quotepath=false", "diff", "-U0", "--no-color", "--no-ext-diff",
                     "--no-renames", f"{commit}...HEAD")
    if code != 0:
        raise Refused(f"diff impossible entre {base} et HEAD dans {repo}")
    changed: dict[str, set[int]] = {}
    current: set[int] | None = None
    for line in out.decode("utf-8", "replace").splitlines():
        if line.startswith("+++ "):
            current = changed.setdefault(line[6:], set()) if line.startswith("+++ b/") else None
            continue
        match = _HUNK.match(line)
        if match and current is not None:
            start, count = int(match[1]), int(match[2] if match[2] is not None else 1)
            lines = range(start, start + count) if count else (start, start + 1)
            current.update(n for n in lines if n >= 1)
    return changed


def outside_diff(data: dict[str, Any], changed: dict[str, set[int]]) -> list[str]:
    """Les constats dont aucune ligne citée n'est dans le diff."""
    errors = []
    for index, item in enumerate(data["constats"], 1):
        path, first, last = parse_where(item["sur_quoi"])
        if not changed.get(path, set()) & set(range(first, last + 1)):
            errors.append(f"constat {index} : {item['sur_quoi']} n'est pas une ligne du diff")
    return errors


def load(path: str) -> Any:
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
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
    return " ".join(text.split()).replace("|", "\\|")


def _ordered(constats: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rank = list(GRAVITES)
    return sorted(constats, key=lambda c: rank.index(c["gravite"]))


def render_md(data: dict[str, Any]) -> str:
    constats = _ordered(data["constats"])
    counts = [f"{label} : {n}" for key, label in GRAVITES.items()
              if (n := sum(c["gravite"] == key for c in constats))]
    out = ["# Revue", "", ("Constats — " + ", ".join(counts) + ".") if counts else "Aucun constat."]
    unchecked = data.get("non_verifie") or []
    out.append("Non vérifié : " + " ; ".join(_cell(u) for u in unchecked) + "." if unchecked
               else "Non vérifié : rien de signalé.")
    for index, item in enumerate(constats, 1):
        out += ["", f"## {index}. {GRAVITES[item['gravite']].capitalize()} — `{_cell(item['sur_quoi'])}`", "",
                "| Partie | Contenu |", "|---|---|",
                f"| Sur quoi | `{_cell(item['sur_quoi'])}` — {_cell(item['point'])} |"]
        out += [f"| {label} | {_cell(item[key])} |" for key, label in PARTS.items()]
    return "\n".join(out) + "\n"


# --- Fixtures : une PR piégée, son corrigé, la note ---------------------------------------------------

def _overlaps(item: dict[str, Any], place: dict[str, Any]) -> bool:
    path, first, last = parse_where(item["sur_quoi"])
    return path == place["file"] and first <= place["lines"][1] and last >= place["lines"][0]


def grade(expected: dict[str, Any], data: Any) -> dict[str, Any]:
    """Généreux sur les mots, strict sur la preuve : un piège est trouvé si un constat cite une de
    ses lignes ; un constat sur une ligne saine fait échouer ; le reste est du bruit, compté."""
    invalid = validate(data)
    limit = expected.get("max_constats", MAX_CONSTATS)
    traps = expected["traps"]
    if invalid:
        return {"pass": False, "invalid": invalid, "found": [], "missed": [t["id"] for t in traps if t["must"]],
                "optional_missed": [], "healthy_touched": [], "noise": [], "count": 0, "max": limit}
    constats = data["constats"]
    found = [t["id"] for t in traps if any(_overlaps(c, w) for c in constats for w in t["where"])]
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


def _run(dest: str, *args: str) -> None:
    out = subprocess.run(["git", "-C", dest, *args], capture_output=True, env={**os.environ, **_FIXED}, timeout=30)
    if out.returncode != 0:
        raise Refused(f"git {args[0]} a échoué dans {dest} : {out.stderr.decode('utf-8', 'replace').strip()}")


def init_fixture(fixture_dir: str, dest: str) -> dict[str, str]:
    """Monte la fixture en dépôt git : `base/` commité sur main, puis `pr/` par-dessus sur sa branche."""
    spec = load(os.path.join(fixture_dir, "pr.json"))
    if os.path.exists(dest) and (not os.path.isdir(dest) or os.listdir(dest)):
        raise Refused(f"{dest} existe et n'est pas vide : donne un dossier neuf")
    try:
        shutil.copytree(os.path.join(fixture_dir, "base"), dest, dirs_exist_ok=True)
        _run(dest, "init", "-q", "-b", "main")
        _run(dest, "add", "-A")
        _run(dest, "commit", "-q", "-m", "base")
        _run(dest, "checkout", "-q", "-b", spec["branch"])
        shutil.copytree(os.path.join(fixture_dir, "pr"), dest, dirs_exist_ok=True)
        for rel in spec.get("removed", []):
            os.remove(os.path.join(dest, rel))
        _run(dest, "add", "-A")
        _run(dest, "commit", "-q", "-m", f"{spec['title']}\n\n{spec['body']}")
    except (OSError, KeyError, subprocess.TimeoutExpired) as exc:
        raise Refused(f"fixture {fixture_dir} : montage impossible ({exc!r})") from exc
    return {"repo": dest, "base": "main", "branch": spec["branch"]}
