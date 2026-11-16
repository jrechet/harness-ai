#!/usr/bin/env python3
"""Le hook PreToolUse du plugin ai-sdlc : refuse une commande shell qui pose un tag, publie ou déploie.

Lit l'appel d'outil en JSON sur l'entrée standard. Sort 2 avec la raison sur la sortie d'erreur pour refuser,
0 pour laisser passer. N'importe que le module du garde-fou : il démarre vite, et une erreur ailleurs dans le
plugin ne le fait pas tomber. S'il tombe quand même, il juge l'appel sur son texte au lieu d'ouvrir la porte."""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
_LAST_RESORT = re.compile(r"git\s[^\n;&|]{0,200}tag\s+v?\d|push[^\n;&|]{0,200}--tags|gh\s+release\s+create|\b(?:npm|cargo|pnpm|yarn)\s+publish|"
                          r"\b(?:kubectl|terraform)\s+apply|\bhelm\s+(?:install|upgrade)|\bmake\s+(?:deploy|release|livr)")


def main() -> int:
    raw = ""
    try:
        raw = sys.stdin.buffer.read(5_000_001).decode("utf-8", "replace")
        from aisdlclib import guard
        code, message = guard.run_hook(raw, dict(os.environ))
    except Exception:   # noqa: BLE001 — jamais de trace : un hook qui plante laisse passer
        if os.environ.get("AI_SDLC_LIVRAISON_PAR_AGENT") == "1" or not _LAST_RESORT.search(raw):
            return 0
        code, message = 2, "ai-sdlc : le garde-fou n'a pas pu lire cet appel, et son texte ressemble à une livraison. Commande refusée.\n"
    sys.stderr.write(message)
    return code


if __name__ == "__main__":
    sys.exit(main())
