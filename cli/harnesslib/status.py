"""Sous-commande `status` : collecte les faits, évalue la maturité, écrit
`.harness/state.json` et affiche un résumé Markdown ou le JSON."""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date

from . import facts, maturity


def build_parser(parser: argparse.ArgumentParser | None = None) -> argparse.ArgumentParser:
    p = parser or argparse.ArgumentParser(description=__doc__)
    p.add_argument("repo", nargs="?", default=".", help="chemin du dépôt (défaut : .)")
    p.add_argument("--harness-dir", default=".harness", help="dossier des sorties des skills (défaut : .harness)")
    p.add_argument("--audit", help="JSON d'audit à utiliser (défaut : <harness-dir>/audit.json)")
    p.add_argument("--harvest", help="JSON de harvest à utiliser (défaut : <harness-dir>/harvest.json)")
    p.add_argument("--format", choices=["md", "json"], default="md")
    p.add_argument("--no-write", action="store_true", help="n'écrit pas <harness-dir>/state.json")
    p.add_argument("--today", help="AAAA-MM-JJ, pour des sorties reproductibles")
    return p


def build_target_parser(parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
    parser.add_argument("level", nargs="?", type=int, choices=[1, 2, 3, 4], help="palier visé ; omis : affiche l'objectif")
    parser.add_argument("repo", nargs="?", default=".", help="chemin du dépôt (défaut : .)")
    parser.add_argument("--harness-dir", default=".harness")
    return parser


def target_main(args: argparse.Namespace) -> int:
    """Écrit le palier visé dans `<harness-dir>/config.json` : au-delà, `status` ne propose rien."""
    hdir = os.path.join(os.path.abspath(args.repo), args.harness_dir)
    path = os.path.join(hdir, "config.json")
    config = facts.load_json(path) or {"schema": "harness-config/1"}
    if args.level is None:
        current = facts.config_facts(hdir)["target_level"]
        print(f"palier visé : {current}" if current else "aucun palier visé")
        return 0
    config["target_level"] = args.level
    os.makedirs(hdir, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(config, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    print(f"palier visé : {args.level} · {maturity.LEVELS[args.level][1]} (écrit dans {os.path.relpath(path)})")
    return 0


def main(argv: list[str] | None = None, args: argparse.Namespace | None = None) -> int:
    if args is None:
        args = build_parser().parse_args(argv)
    today = date.fromisoformat(args.today) if args.today else None
    f = facts.collect(args.repo, args.harness_dir, args.audit, args.harvest, today)
    state = maturity.evaluate(f)
    if not args.no_write:
        out_dir = os.path.join(os.path.abspath(args.repo), args.harness_dir)
        os.makedirs(out_dir, exist_ok=True)
        with open(os.path.join(out_dir, "state.json"), "w", encoding="utf-8") as fh:
            json.dump(state, fh, ensure_ascii=False, indent=2)
            fh.write("\n")
    if args.format == "json":
        json.dump(state, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
    else:
        sys.stdout.write(maturity.render_markdown(state))
    return 0
