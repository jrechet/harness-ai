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
  harness report build|from-place …  un état des lieux en une page HTML, toujours au même format

Python 3.10+, bibliothèque standard uniquement."""
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from harnesslib import bench, commands, fixtures, github, place, report, rules, serve, status  # noqa: E402


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
    args = parser.parse_args(argv)
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
    parser.error("commande inconnue")
    return 2


if __name__ == "__main__":
    sys.exit(main())
