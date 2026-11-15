#!/usr/bin/env python3
"""CLI du plugin ai-sdlc : la logique déterministe que ses skills appellent.

  ai_sdlc.py context <phase> [repo] [--base REF]   le socle et les ajouts de l'équipe, avec leur provenance
  ai_sdlc.py status [repo] [--base REF]            les points d'extension : convention, surchargé, invalide

Codes de sortie de `context` : 0 servi, 2 refusé (surcharge invalide, phase ou branche inconnue) : rien
n'est imprimé sur la sortie standard, la raison est sur la sortie d'erreur. `status` sort 0 et montre une
surcharge invalide dans son tableau : il décrit, il ne sert pas de porte.

Python 3.10+, bibliothèque standard uniquement."""
from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from aisdlclib import context, points  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ai-sdlc", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    ctx = sub.add_parser("context", help="le contexte assemblé d'une phase")
    ctx.add_argument("phase")
    ctx.add_argument("--worktree", action="store_true",
                     help="lire les surcharges dans la copie de travail (essai local, pas une porte)")
    status = sub.add_parser("status", help="l'état des points d'extension")
    for sp in (ctx, status):
        sp.add_argument("repo", nargs="?", default=".")
        sp.add_argument("--base", default="origin/HEAD", help="branche de base (défaut : origin/HEAD)")
        sp.add_argument("--format", choices=["md", "json"], default="md")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    table = points.load()
    try:
        if args.command == "context":
            data = context.assemble(table, args.repo, args.phase, args.base, worktree=args.worktree)
            text = context.render_context_md(data)
        else:
            data = context.status(table, args.repo, args.base)
            text = context.render_status_md(data)
    except context.Refused as exc:
        print(f"ai-sdlc : {exc}", file=sys.stderr)
        return 2
    sys.stdout.write(json.dumps(data, ensure_ascii=False, indent=2) + "\n" if args.format == "json" else text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
