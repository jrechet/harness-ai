#!/usr/bin/env python3
"""CLI du plugin ai-sdlc : la logique déterministe que ses skills appellent.

  ai_sdlc.py context <phase> [repo] [--base REF]   le socle et les ajouts de l'équipe, avec leur provenance
  ai_sdlc.py status [repo] [--base REF]            les points d'extension : convention, surchargé, invalide
  ai_sdlc.py review render <revue.json> [repo] [--base REF]   la revue rendue, si chaque constat cite le diff
  ai_sdlc.py fixture init <fixture> <dest>         monte une PR piégée de fixtures/review en dépôt git
  ai_sdlc.py fixture grade <revue.json> --expected <expected.json>   note une revue contre son corrigé

Codes de sortie de `context` : 0 servi, 2 refusé (surcharge invalide, phase ou branche inconnue) : rien
n'est imprimé sur la sortie standard, la raison est sur la sortie d'erreur. `status` sort 0 et montre une
surcharge invalide dans son tableau : il décrit, il ne sert pas de porte. `review render` : 0 rendu, 2 refusé
(forme incomplète, constat hors du diff). `fixture grade` : 0 conforme, 1 non conforme, 2 fichier illisible.

Python 3.10+, bibliothèque standard uniquement."""
from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from aisdlclib import context, points, review  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ai-sdlc", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    ctx = sub.add_parser("context", help="le contexte assemblé d'une phase")
    ctx.add_argument("phase")
    ctx.add_argument("--worktree", action="store_true",
                     help="lire les surcharges dans la copie de travail (essai local, pas une porte)")
    status = sub.add_parser("status", help="l'état des points d'extension")
    rev = sub.add_parser("review", help="le résultat d'une revue").add_subparsers(dest="action", required=True)
    render = rev.add_parser("render", help="valide la revue et la rend en commentaires")
    render.add_argument("file")
    for sp in (ctx, status, render):
        sp.add_argument("repo", nargs="?", default=".")
        sp.add_argument("--base", default="origin/HEAD", help="branche de base (défaut : origin/HEAD)")
        sp.add_argument("--format", choices=["md", "json"], default="md")
    fix = sub.add_parser("fixture", help="mesurer le skill review").add_subparsers(dest="action", required=True)
    init = fix.add_parser("init", help="monte la fixture en dépôt git")
    init.add_argument("fixture")
    init.add_argument("dest")
    grade = fix.add_parser("grade", help="note une revue contre le corrigé")
    grade.add_argument("file")
    grade.add_argument("--expected", required=True)
    for sp in (init, grade):
        sp.add_argument("--format", choices=["md", "json"], default="md")
    return parser


def _fixture(args: argparse.Namespace) -> tuple[object, str, int]:
    if args.action == "init":
        made = review.init_fixture(args.fixture, args.dest)
        return made, f"Dépôt monté dans {made['repo']} : base {made['base']}, branche {made['branch']}.\n", 0
    expected = review.load(args.expected)
    result = review.grade(expected, review.load(args.file))
    return result, review.render_grade_md(expected, result), 0 if result["pass"] else 1


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    table = points.load()
    code = 0
    try:
        if args.command == "fixture":
            data, text, code = _fixture(args)
        elif args.command == "review":
            data = review.checked(args.file, args.repo, args.base)
            text = review.render_md(data)
        elif args.command == "context":
            data = context.assemble(table, args.repo, args.phase, args.base, worktree=args.worktree)
            text = context.render_context_md(data)
        else:
            data = context.status(table, args.repo, args.base)
            text = context.render_status_md(data)
    except context.Refused as exc:
        print(f"ai-sdlc : {exc}", file=sys.stderr)
        return 2
    sys.stdout.write(json.dumps(data, ensure_ascii=False, indent=2) + "\n" if args.format == "json" else text)
    return code


if __name__ == "__main__":
    sys.exit(main())
