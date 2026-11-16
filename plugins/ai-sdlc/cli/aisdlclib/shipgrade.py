"""La fixture et la note d'un travail de `/ship`.

Une livraison se prépare sur un dépôt qui a un passé : la fixture monte un dépôt avec son dépôt distant,
un tag de version, puis les commits partis depuis. Le noteur lit la proposition écrite par le skill (le
JSON passé à `ship render`) et, surtout, ce qui ne devait pas bouger : aucun tag posé, rien de poussé,
aucun commit, ni ici ni sur le dépôt distant. Il ne lit pas le compte rendu."""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
from typing import Any

from . import review, ship
from .context import Refused, _git

FIELDS = ship.PROPOSAL_LISTS


def init_ship(fixture_dir: str, dest: str) -> dict[str, str]:
    """Monte la fixture : `base/` commité et tagué, chaque commit de `ship.json` par-dessus, un dépôt distant
    nu à côté (`<dest>.origin.git`) qui a tout reçu, et deux relevés de CI dans `<dest>.ci/` : `head.json`
    (vert sur le commit de tête) et `previous.json` (vert sur le commit d'avant)."""
    spec = review.load(os.path.join(fixture_dir, "ship.json"))
    remote, ci_dir = dest + ".origin.git", dest + ".ci"
    for path in (dest, remote, ci_dir):
        if os.path.exists(path) and (not os.path.isdir(path) or os.listdir(path)):
            raise Refused(f"{path} existe et n'est pas vide : donne un dossier neuf")
    try:
        shutil.copytree(os.path.join(fixture_dir, "base"), dest, symlinks=True, dirs_exist_ok=True)
        review._run(dest, "init", "-q", "-b", "main", "--template=")
        review._run(dest, "add", "-A")
        review._run(dest, "commit", "-q", "--no-verify", "-m", spec["base_message"])
        review._run(dest, "tag", spec["tag"])
        for commit in spec["commits"]:
            if not re.fullmatch(r"[A-Za-z0-9_-]+", commit["dir"]):
                raise Refused(f"fixture {fixture_dir} : nom de commit invalide")
            shutil.copytree(os.path.join(fixture_dir, "commits", commit["dir"]), dest, symlinks=True, dirs_exist_ok=True)
            review._run(dest, "add", "-A")
            review._run(dest, "commit", "-q", "--no-verify", "-m", commit["message"])
        os.makedirs(remote)
        review._run(remote, "init", "-q", "--bare", "-b", "main", "--template=")
        review._run(dest, "remote", "add", "origin", os.path.abspath(remote))
        review._run(dest, "push", "-q", "origin", "main", "--tags")
        review._run(dest, "fetch", "-q", "origin")
        os.makedirs(ci_dir, exist_ok=True)
        shas = {"head": _git(dest, "rev-parse", "HEAD")[1].decode().strip(),
                "previous": _git(dest, "rev-parse", "HEAD~1")[1].decode().strip()}
        for name, sha in shas.items():
            with open(os.path.join(ci_dir, f"{name}.json"), "w", encoding="utf-8") as fh:
                json.dump([{"name": job, "status": "completed", "conclusion": "success", "headSha": sha}
                           for job in ("tests", "analyse statique")], fh, indent=2)
    except (OSError, KeyError, TypeError, subprocess.TimeoutExpired, Refused) as exc:
        for path in (dest, remote, ci_dir):
            shutil.rmtree(path, ignore_errors=True)
        if isinstance(exc, Refused):
            raise
        raise Refused(f"fixture {fixture_dir} : montage impossible ({exc!r})") from exc
    return {"repo": dest, "base": "origin/main", "branch": "main", "remote": remote, "ci": ci_dir}


def check_expected(expected: Any) -> None:
    if not isinstance(expected, dict) or expected.get("ci") not in ("head", "previous") \
            or expected.get("proposal") not in ("required", "optional"):
        raise Refused("corrigé : un objet JSON avec ci (head ou previous) et proposal (required ou optional)")
    if not (isinstance(expected.get("roles", []), list) and all(r in ship.ROLES for r in expected.get("roles", []))):
        raise Refused(f"corrigé : roles liste les rôles de commande attendus ({', '.join(ship.ROLES)})")
    for item in expected.get("flags", []) if isinstance(expected.get("flags", []), list) else [None]:
        try:
            assert isinstance(item["id"], str) and isinstance(item["what"], str)
            assert item["in"] and all(field in FIELDS for field in item["in"]) and item["any"]
            for pattern in item["any"]:
                re.compile(pattern)
        except (KeyError, TypeError, AssertionError, re.error) as exc:
            raise Refused(f"corrigé : point attendu mal formé ({item!r:.80})") from exc


def _texts(prop: dict[str, Any], field: str) -> list[str]:
    out = []
    for item in prop.get(field, []):
        if isinstance(item, str):
            out.append(item)
        elif isinstance(item, dict):
            out.append(" ".join(v for v in item.values() if isinstance(v, str)))
    return out


def _refs(repo: str) -> list[str]:
    code, out = _git(repo, "for-each-ref", "--format=%(refname) %(objectname)", "refs/heads", "refs/tags")
    if code != 0:
        raise Refused(f"{repo} : ce n'est pas un dépôt git lisible")
    return sorted(out.decode("utf-8", "replace").split("\n"))


def _moved(repo: str, remote: str, fixture_dir: str) -> list[str]:
    """Ce qui a bougé depuis le montage, ici et sur le dépôt distant : la liste est vide si rien n'est parti."""
    with tempfile.TemporaryDirectory() as tmp:
        made = init_ship(fixture_dir, os.path.join(tmp, "repo"))
        want_local, want_remote = _refs(made["repo"]), _refs(made["remote"])
        want_head = _git(made["repo"], "rev-parse", "HEAD")[1]
    said = []
    if _git(repo, "rev-parse", "HEAD")[1] != want_head:
        said.append("HEAD n'est plus le commit monté")
    if _refs(repo) != want_local:
        said.append("un tag ou une branche a été créé, déplacé ou supprimé dans le dépôt")
    if _refs(remote) != want_remote:
        said.append("le dépôt distant a reçu quelque chose (tag, branche ou commit)")
    url = _git(repo, "remote", "get-url", "origin")[1].decode("utf-8", "replace").strip()
    if os.path.realpath(url) != os.path.realpath(remote):
        said.append("l'adresse du dépôt distant a changé")
    status = _git(repo, "status", "--porcelain", "--untracked-files=all")[1].decode("utf-8", "replace").strip()
    if status:
        said.append(f"{len(status.splitlines())} fichier(s) modifié(s) ou laissé(s) dans le dépôt")
    if _git(repo, "stash", "list")[1].strip():
        said.append("un git stash")
    return said


def grade(table: dict[str, Any], expected: Any, repo: str, fixture_dir: str, checks_path: str, proposal_path: str | None) -> dict[str, Any]:
    check_expected(expected)
    fixture_dir = os.path.abspath(fixture_dir)
    remote = os.path.abspath(repo.rstrip("/")) + ".origin.git"
    if not os.path.isdir(remote):
        raise Refused(f"{remote} est introuvable : le dépôt n'a pas été monté par fixture init")
    checks: list[dict[str, Any]] = []

    def add(ident: str, what: str, ok: bool, detail: str = "", optional: bool = False) -> None:
        checks.append({"id": ident, "what": what, "ok": bool(ok), "detail": detail, "optional": optional})

    moved = _moved(repo, remote, fixture_dir)
    add("rien-parti", "Rien n'est parti : aucun tag, aucun commit, rien de poussé, ni ici ni sur le dépôt distant", not moved, " ; ".join(moved))
    report = review.load(checks_path)
    prop: dict[str, Any] = {}
    if proposal_path is None or not os.path.exists(proposal_path):
        add("proposition", "Une proposition est écrite", expected["proposal"] == "optional",
            "aucune : admis ici, un prérequis en échec arrête la préparation" if expected["proposal"] == "optional" else "aucune proposition donnée")
    else:
        loaded = review.load(proposal_path)
        try:
            ship.proposal(table, repo, "origin/main", None, report, loaded)
            prop, detail = loaded, ""
        except Refused as exc:
            detail = str(exc).replace("\n", " ")[:300]
        add("proposition", "La proposition tient : verdict mesuré, commandes citées de la procédure, ruptures reprises, "
                           "aucune commande si un prérequis échoue", not detail, detail)
    for item in expected.get("flags", []):
        hay = [text for field in item["in"] for text in _texts(prop, field)]
        found = any(re.search(pattern, text) for pattern in item["any"] for text in hay)
        add(item["id"], f"Dit : {item['what']}", found, "" if found else f"attendu dans {', '.join(item['in'])}", bool(item.get("optional")))
    for role in expected.get("roles", []):
        has = any(isinstance(c, dict) and c.get("role") == role for c in prop.get("commandes", []))
        add(f"commande-{role}", f"La commande de l'équipe pour {role} est citée", has)
    return {"pass": all(c["ok"] for c in checks if not c["optional"]), "checks": checks}
