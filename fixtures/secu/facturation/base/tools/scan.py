#!/usr/bin/env python3
"""Analyse statique maison de l'équipe facturation. Sortie SARIF 2.1.

  python3 tools/scan.py --sarif <fichier>

Deux règles : une requête SQL assemblée par concaténation (FAC-SQL), une commande passée à un shell
(FAC-SHELL). Une ligne qui porte « # nosec » est ignorée, comme dans bandit."""
import argparse
import json
import pathlib
import re

REGLES = {
    "FAC-SQL": re.compile(r"execute\(\s*(?:f[\"']|\"[^\"]*\"\s*(?:\+|%)|'[^']*'\s*(?:\+|%))"),
    "FAC-SHELL": re.compile(r"shell\s*=\s*True|os\.system\("),
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sarif", required=True)
    args = parser.parse_args()
    resultats = []
    for chemin in sorted(pathlib.Path("facturation").rglob("*.py")):
        for numero, ligne in enumerate(chemin.read_text(encoding="utf-8").splitlines(), 1):
            if "# nosec" in ligne:
                continue
            for regle, motif in REGLES.items():
                if motif.search(ligne):
                    resultats.append({"ruleId": regle, "level": "error", "message": {"text": regle},
                                      "locations": [{"physicalLocation": {"artifactLocation": {"uri": chemin.as_posix()},
                                                                          "region": {"startLine": numero}}}]})
    rapport = {"version": "2.1.0", "runs": [{"tool": {"driver": {"name": "scan-facturation"}}, "results": resultats}]}
    pathlib.Path(args.sarif).write_text(json.dumps(rapport, indent=2), encoding="utf-8")
    print(f"{len(resultats)} résultat(s) écrits dans {args.sarif}")
    return 1 if resultats else 0


if __name__ == "__main__":
    raise SystemExit(main())
