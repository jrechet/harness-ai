#!/usr/bin/env python3
"""CLI de harness-ai : la logique déterministe (L3) que les skills appellent.

  harness status [repo]              état de maturité, écrit .harness/state.json
  harness target <palier> [repo]     déclare le palier visé : au-delà, status ne propose rien
  harness rules [repo]               les règles, leur date, leur garde-fou, leur justification
  harness harvest github --repo …    évidences GitHub pour harness-harvest
  harness fixture check <nom>        compare une fixture à son expected.json
  harness bench …                    le banc avant et après : plan, prepare, check, selftest, record, report
  harness serve [repo]               application de suivi en local (http://127.0.0.1:8787)
  harness place grid|one|plan …      où va chaque morceau d'un harness, et pourquoi
  harness commands [repo]            les commandes qu'un agent ne devine pas : ce que la CI lance vraiment
  harness fresh [repo] [--hook|--strict]   ce qui a vieilli : un skill qui cite un fichier disparu, un harvest en retard
  harness medals [repo] [--write] [--page F]   médaille, succès débloqués, prochaines étapes ; page HTML
  harness progress check|remind      le plan d'avancement de docs/capacites.md suit chaque changement
  harness report build|from-place …  un état des lieux en une page HTML, toujours au même format

Python 3.10+, bibliothèque standard uniquement."""
from __future__ import annotations

import argparse
import os
import sys

if sys.version_info < (3, 10):  # avant tout import : le reste du CLI ne se lit pas en 3.9
    sys.exit("harness : Python 3.10 ou plus est requis (ici %d.%d). Essaie python3.11 ou python3.12." % sys.version_info[:2])

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from harnesslib import bench, commands, fixtures, fresh, github, medals, place, progress, report, rules, serve, status  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="harness", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    status.build_parser(sub.add_parser("status", help="état de maturité du dépôt"))
    status.build_target_parser(sub.add_parser("target", help="déclare ou affiche le palier visé"))
    rules.build_parser(sub.add_parser("rules", help="les règles et ce qu'on sait d'elles"))
    harvest = sub.add_parser("harvest", help="collecte d'évidences pour harness-harvest")
    hsub = harvest.add_subparsers(dest="source", required=True)
    github.build_parser(hsub.add_parser("github", help="adaptateur GitHub"))
    fixtures.build_parser(sub.add_parser("fixture", help="vérification des fixtures"))
    bench.build_parser(sub.add_parser("bench", help="le banc de tâches avant et après"))
    serve.build_parser(sub.add_parser("serve", help="application de suivi en local"))
    place.build_parser(sub.add_parser("place", help="où va chaque morceau d'un harness"))
    report.build_parser(sub.add_parser("report", help="un état des lieux en une page HTML"))
    commands.build_parser(sub.add_parser("commands", help="les commandes qu'un agent ne devine pas"))
    progress.build_parser(sub.add_parser("progress", help="le plan d'avancement suit chaque changement"))
    medals.build_parser(sub.add_parser("medals", help="médailles et succès : le niveau de maturité et pourquoi"))
    fresh.build_parser(sub.add_parser("fresh", help="ce qui a vieilli : skills, agents, règles"))
    args = parser.parse_args(argv)
    target = getattr(args, "repo", None)
    if args.command in ("status", "target", "rules", "serve") and isinstance(target, str) and not os.path.isdir(target):
        print(f"harness {args.command} : {target} n'est pas un dossier", file=sys.stderr)
        return 2
    if args.command == "status":
        return status.main(args=args)
    if args.command == "target":
        return status.target_main(args)
    if args.command == "rules":
        return rules.main(args=args)
    if args.command == "harvest" and args.source == "github":
        return github.main(args=args)
    if args.command == "fixture":
        return fixtures.main(args=args)
    if args.command == "bench":
        return bench.main(args=args)
    if args.command == "serve":
        return serve.main(args=args)
    if args.command == "place":
        return place.main(args=args)
    if args.command == "report":
        return report.main(args=args)
    if args.command == "commands":
        return commands.main(args=args)
    if args.command == "progress":
        return progress.main(args=args)
    if args.command == "medals":
        return medals.main(args=args)
    if args.command == "fresh":
        return fresh.main(args=args)
    parser.error("commande inconnue")
    return 2


if __name__ == "__main__":
    sys.exit(main())
