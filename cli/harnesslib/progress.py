"""Le plan d'avancement tenu à jour : un changement dans le dépôt ne part pas sans sa ligne.

Un document d'avancement que personne n'est obligé de tenir ment au bout d'une semaine. Ce module
vérifie deux choses, sans modèle : le document a la forme attendue (une date, un tableau dont chaque
ligne a un identifiant unique et un état connu), et il fait partie de tout changement de la branche.
Branché en hook de fin de tour, il renvoie l'agent écrire sa ligne avant de s'arrêter."""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from typing import Any

DOC = "docs/capacites.md"
HEADING = "## Plan d'avancement"
STATES = ("fait", "en cours", "à faire", "en attente", "écarté")
REMINDER = (f"Rappel du dépôt : toute demande nouvelle ou correction de qui pilote la session, et tout travail fini ou commencé, "
            f"s'inscrit dans {DOC} (section « Plan d'avancement » : une ligne par sujet, état parmi "
            f"{', '.join(STATES)}), dans le même changement.")
_DATE = re.compile(r"^Dernière mise à jour : (\d{4}-\d{2}-\d{2})\b", re.MULTILINE)
_ID = re.compile(r"^[A-Z]{1,3}\d{1,3}$")


def parse(text: str) -> tuple[list[dict[str, str]], list[str]]:
    """Les lignes du plan et ce qui cloche dans sa forme."""
    errors = []
    if not _DATE.search(text):
        errors.append("ligne « Dernière mise à jour : AAAA-MM-JJ » absente")
    if HEADING not in text:
        return [], errors + [f"section « {HEADING} » absente"]
    section = text.split(HEADING, 1)[1].split("\n## ", 1)[0]
    rows, seen = [], set()
    for line in section.splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")] if line.strip().startswith("|") else []
        if len(cells) < 3 or not _ID.match(cells[0]):
            continue
        row = {"id": cells[0], "what": cells[1], "state": cells[2]}
        if row["id"] in seen:
            errors.append(f"{row['id']} : identifiant en double")
        seen.add(row["id"])
        if row["state"] not in STATES:
            errors.append(f"{row['id']} : état « {row['state']} » inconnu ({', '.join(STATES)})")
        if not row["what"]:
            errors.append(f"{row['id']} : sujet vide")
        rows.append(row)
    if not rows:
        errors.append("aucune ligne dans le plan (| A1 | sujet | état | …)")
    return rows, errors


def _git(repo: str, *args: str) -> tuple[int, str]:
    try:
        out = subprocess.run(["git", "-C", repo, "-c", "core.quotepath=false", *args], capture_output=True, timeout=20)
    except (OSError, subprocess.TimeoutExpired):
        return 1, ""
    return out.returncode, out.stdout.decode("utf-8", "replace")


def changed_paths(repo: str, base: str) -> set[str] | None:
    """Ce que la branche et la copie de travail changent par rapport à la base ; None hors d'un dépôt git."""
    code, status = _git(repo, "status", "--porcelain", "-z", "--untracked-files=all")
    if code != 0:
        return None
    paths = set()
    entries = status.split("\0")
    index = 0
    while index < len(entries):
        entry = entries[index]
        index += 1
        if len(entry) < 4:
            continue
        paths.add(entry[3:])
        if entry[0] in "RC":  # un renommage porte son ancien nom dans l'entrée suivante
            if index < len(entries):
                paths.add(entries[index])
            index += 1
    code, names = _git(repo, "diff", "--name-only", "-z", "--no-renames", f"{base}...HEAD")
    if code == 0:
        paths |= {p for p in names.split("\0") if p}
    return paths


def check(repo: str, doc: str = DOC, base: str = "origin/main") -> list[str]:
    """Ce qui empêche de s'arrêter là : liste vide si le plan est en forme et suit le changement."""
    try:
        with open(os.path.join(repo, doc), encoding="utf-8") as fh:
            text = fh.read()
    except OSError:
        return [f"{doc} est introuvable : c'est le document qui dit ce que le dépôt sait faire et où il en est"]
    errors = [f"{doc} : {e}" for e in parse(text)[1]]
    changed = changed_paths(repo, base)
    if changed is not None:  # l'état mesuré (.harness/) est une sortie de commande, pas un travail à inscrire
        changed = {p for p in changed if not p.startswith(".harness/")}
    if changed is not None and changed - {doc} and doc not in changed:
        sample = ", ".join(sorted(changed - {doc})[:4])
        errors.append(f"le dépôt change ({sample}{'…' if len(changed) > 5 else ''}) et {doc} ne bouge pas : inscris "
                      "au plan d'avancement ce qui est fait, commencé ou demandé, et mets la date à jour")
    return errors


def build_parser(parser: argparse.ArgumentParser | None = None) -> argparse.ArgumentParser:
    p = parser or argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="progress_command", required=True)
    chk = sub.add_parser("check", help="le plan est en forme et suit le changement de la branche")
    chk.add_argument("repo", nargs="?", default=".")
    chk.add_argument("--doc", default=DOC)
    chk.add_argument("--base", default="origin/main")
    chk.add_argument("--hook", action="store_true",
                     help="appelé par un hook Stop : lit son JSON sur l'entrée, et ne bloque pas deux fois de suite")
    sub.add_parser("remind", help="la ligne de rappel injectée à chaque demande")
    return p


def main(argv: list[str] | None = None, args: argparse.Namespace | None = None) -> int:
    args = args or build_parser().parse_args(argv)
    if args.progress_command == "remind":
        print(REMINDER)
        return 0
    if args.hook:
        try:
            event: Any = json.load(sys.stdin)
        except (ValueError, OSError):
            event = {}
        if isinstance(event, dict) and event.get("stop_hook_active"):
            return 0  # déjà renvoyé une fois ce tour-ci : ne pas enfermer l'agent dans une boucle
    errors = check(args.repo, args.doc, args.base)
    if not errors:
        if not args.hook:
            print(f"{args.doc} : en forme, et il suit le changement.")
        return 0
    print("Plan d'avancement à mettre à jour avant de s'arrêter :\n- " + "\n- ".join(errors), file=sys.stderr)
    return 2
