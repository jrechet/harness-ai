#!/usr/bin/env python3
"""CLI du plugin ai-sdlc : la logique déterministe que ses skills appellent.

  ai_sdlc.py context <phase> [repo] [--base REF]   le socle et les ajouts de l'équipe, avec leur provenance
  ai_sdlc.py status [repo] [--base REF]            les points d'extension : convention, surchargé, invalide
  ai_sdlc.py review render <revue.json> [repo] [--base REF]   la revue rendue, si chaque constat cite le diff
  ai_sdlc.py size [repo] [--base REF] [--paths P…]  la taille du changement et le chemin qu'elle impose
  ai_sdlc.py dev body <corps.json> [repo] [--base REF]        le corps de la PR, s'il est complet pour sa taille
  ai_sdlc.py ticket check <ticket.md> [repo] [--base REF]     le ticket est-il prêt à être confié à un agent
  ai_sdlc.py ticket render <avis.json> [repo] --ticket <ticket.md> [--base REF]   l'avis du skill, s'il est bien formé
  ai_sdlc.py qa gate [repo] [--base REF] [--run CMD] [--coverage F] [--ticket F --trace F]   les portes de /qa
  ai_sdlc.py secu gate [repo] [--base REF] [--report SARIF…]   les portes de /secu
  ai_sdlc.py ship check [repo] [--base REF] [--since REF] [--checks relevé.json]   les prérequis d'une livraison
  ai_sdlc.py fixture init <fixture> <dest>         monte une PR piégée de fixtures/review en dépôt git
  ai_sdlc.py fixture grade <revue.json> --expected <expected.json>   note une revue contre son corrigé
  ai_sdlc.py fixture grade-dev <dépôt> --task <dossier du ticket> [--body corps.json]   note un travail de /dev
  ai_sdlc.py fixture grade-ticket <avis.json> --task <dossier> --repo <dépôt> --ticket <copie>   note un avis de /ticket
  ai_sdlc.py fixture grade-secu <revue.json> --fixture <fixture> --repo <dépôt> --out <dossier>   note un travail de /secu
  ai_sdlc.py fixture grade-qa <dépôt> --fixture <fixture> [--trace correspondance.json]   note un travail de /qa

Codes de sortie de `context` : 0 servi, 2 refusé (surcharge invalide, phase ou branche inconnue) : rien
n'est imprimé sur la sortie standard, la raison est sur la sortie d'erreur. `status` sort 0 et montre une
surcharge invalide dans son tableau : il décrit, il ne sert pas de porte. `review render` : 0 rendu, 2 refusé
(forme incomplète, constat hors du diff). `ticket check` : 0 prêt, 1 pas prêt, 2 illisible. `ticket render` : 0 rendu, 2 refusé. `qa gate` : 0 les quatre
portes passent, 1 une porte en échec, 3 rien en échec mais une porte non mesurée, 2 refusé ; `secu gate` et `ship check` suivent les mêmes codes. `fixture grade` : 0 conforme, 1 non conforme, 2 fichier illisible.

Python 3.10+, bibliothèque standard uniquement."""
from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from aisdlclib import context, dev, devgrade, points, qa, qagrade, review, secu, secugrade, ship, size, ticket, ticketgrade  # noqa: E402


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
    sized = sub.add_parser("size", help="la taille du changement")
    sized.add_argument("--paths", nargs="+", metavar="CHEMIN",
                       help="avant le code : les chemins que le changement prévoit de toucher")
    body = sub.add_parser("dev", help="ce que /dev garantit").add_subparsers(dest="action", required=True)
    body = body.add_parser("body", help="valide et rend le corps de la PR")
    body.add_argument("file")
    tck = sub.add_parser("ticket", help="ce que /ticket mesure").add_subparsers(dest="action", required=True)
    avis = tck.add_parser("render", help="valide l'avis du skill et le rend, verdict mesuré en tête")
    avis.add_argument("file", help="l'avis en JSON : manques, criteres, decoupage, questions, consignes")
    avis.add_argument("--ticket", required=True, metavar="FICHIER", help="le texte du ticket")
    tck = tck.add_parser("check", help="le ticket est-il prêt à être confié à un agent")
    tck.add_argument("file", help="le texte du ticket, en Markdown ou en texte brut")
    gate = sub.add_parser("qa", help="ce que /qa garantit").add_subparsers(dest="action", required=True)
    gate = gate.add_parser("gate", help="les quatre portes : désactivés, répété, couverture, critères")
    gate.add_argument("--run", metavar="CMD", help="la commande de test du dépôt, lancée plusieurs fois depuis sa racine")
    gate.add_argument("--runs", type=int, help="nombre de passages (défaut : celui du socle)")
    gate.add_argument("--coverage", metavar="FICHIER", help="un rapport lcov ou Cobertura produit sur cette branche")
    gate.add_argument("--ticket", metavar="FICHIER", help="le texte du ticket, pour ses critères d'acceptation")
    gate.add_argument("--trace", metavar="FICHIER", help="la correspondance critères → tests, en JSON")
    sgate = sub.add_parser("secu", help="ce que /secu garantit").add_subparsers(dest="action", required=True)
    sgate = sgate.add_parser("gate", help="les quatre portes : secrets, neutralisés, scanner, surface")
    sgate.add_argument("--report", nargs="+", metavar="SARIF", default=[],
                       help="les rapports SARIF des scanners de l'équipe, produits sur cette branche")
    shp = sub.add_parser("ship", help="ce que /ship vérifie").add_subparsers(dest="action", required=True)
    shp = shp.add_parser("check", help="les prérequis d'une livraison, une version et des notes proposées")
    shp.add_argument("--since", metavar="REF", help="la version précédente (défaut : le dernier tag atteignable)")
    shp.add_argument("--checks", metavar="FICHIER", help="le relevé de la CI du commit, en JSON (gh run list --commit … --json …)")
    for sp in (ctx, status, render, sized, body, tck, avis, gate, sgate, shp):
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
    gdev = fix.add_parser("grade-dev", help="note un travail de /dev dans un dépôt monté")
    gdev.add_argument("repo")
    gdev.add_argument("--task", required=True, help="le dossier du ticket dans la fixture (expected.json, hidden/)")
    gdev.add_argument("--body", help="le corps de PR en JSON, tel que le skill l'a écrit")
    gtck = fix.add_parser("grade-ticket", help="note un avis de /ticket contre son corrigé")
    gtck.add_argument("file", help="l'avis en JSON, tel que le skill l'a écrit")
    gtck.add_argument("--task", required=True, help="le dossier du ticket dans la fixture (ticket.md, expected.json)")
    gtck.add_argument("--repo", required=True, help="le dépôt monté donné à l'agent")
    gtck.add_argument("--ticket", required=True, help="la copie du ticket donnée à l'agent")
    gqa = fix.add_parser("grade-qa", help="note un travail de /qa dans un dépôt monté")
    gqa.add_argument("repo")
    gqa.add_argument("--fixture", required=True, help="le dossier de la fixture (ticket.md, expected.json, hidden/)")
    gqa.add_argument("--trace", help="la correspondance critères → tests, telle que le skill l'a écrite")
    gsec = fix.add_parser("grade-secu", help="note un travail de /secu : constats, branche intacte, secret tu")
    gsec.add_argument("file", help="les constats en JSON, au format de review render")
    gsec.add_argument("--fixture", required=True, help="le dossier de la fixture (expected.json, pr.json)")
    gsec.add_argument("--repo", required=True, help="le dépôt monté donné à l'agent")
    gsec.add_argument("--out", required=True, help="le dossier où l'agent a écrit ses fichiers : la valeur du secret y est cherchée")
    for sp in (init, grade, gdev, gtck, gqa, gsec):
        sp.add_argument("--format", choices=["md", "json"], default="md")
    return parser


def _fixture(args: argparse.Namespace, table: dict) -> tuple[object, str, int]:
    if args.action == "grade-dev":
        expected = review.load(os.path.join(args.task, "expected.json"))
        result = devgrade.grade(table, expected, args.repo, args.task, args.body)
        return result, devgrade.render_md(result), 0 if result["pass"] else 1
    if args.action == "grade-ticket":
        result = ticketgrade.grade(table, review.load(os.path.join(args.task, "expected.json")), review.load(args.file),
                                   args.task, args.repo, args.ticket)
        return result, devgrade.render_md(result), 0 if result["pass"] else 1
    if args.action == "grade-secu":
        result = secugrade.grade(review.load(os.path.join(args.fixture, "expected.json")), review.load(args.file), args.file,
                                 args.repo, args.fixture, args.out)
        return result, devgrade.render_md(result), 0 if result["pass"] else 1
    if args.action == "grade-qa":
        result = qagrade.grade(table, review.load(os.path.join(args.fixture, "expected.json")), args.repo, args.fixture,
                               review.load(args.trace) if args.trace else None)
        return result, devgrade.render_md(result), 0 if result["pass"] else 1
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
            data, text, code = _fixture(args, table)
        elif args.command == "qa":
            if args.runs is not None and not 1 <= args.runs <= 20:
                raise context.Refused("--runs : entre 1 et 20")
            ticket_text = ticket.read(args.ticket) if args.ticket else None
            data = qa.run_gates(table, args.repo, args.base, args.run, args.runs, args.coverage, ticket_text,
                                review.load(args.trace) if args.trace else None)
            text, code = qa.render_md(data), 1 if data["failed"] else (3 if data["unknown"] else 0)
        elif args.command == "ship":
            data = ship.check(table, args.repo, args.base, args.since, review.load(args.checks) if args.checks else None)
            text, code = ship.render_md(data), 1 if data["failed"] else (3 if data["unknown"] else 0)
        elif args.command == "secu":
            data = secu.run_gates(table, args.repo, args.base, args.report)
            text, code = secu.render_md(data), 1 if data["failed"] else (3 if data["unknown"] else 0)
        elif args.command == "ticket":
            source = args.ticket if args.action == "render" else args.file
            text = ticket.read(source)
            zones, warning = ticket.zones_for(table, args.repo, args.base)
            data = {**ticket.check(text, zones), "warning": warning}
            if args.action == "render":
                avis = review.load(args.file)
                commit = context.resolve_base(args.repo, args.base)
                errors = ticket.check_avis(avis, text, lambda rel: context.is_file_at(args.repo, commit, rel))
                if errors:
                    raise context.Refused("avis refusé :\n- " + "\n- ".join(errors))
                data, text = {"avis": avis, "check": data}, ticket.render_avis(avis, data, warning)
            else:
                text, code = ticket.render_md(data, warning), 0 if data["ready"] else 1
        elif args.command == "size":
            data = size.classify(table, args.repo, args.base, args.paths)
            text = size.render_md(data)
        elif args.command == "dev":
            content, sized = dev.checked(table, review.load(args.file), args.repo, args.base)
            data, text = {"body": content, "size": sized}, dev.render_md(content, sized)
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
