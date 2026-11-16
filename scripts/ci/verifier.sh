#!/bin/sh
# Ce que la CI vérifie, appelé à l'identique par GitHub Actions et par la forge : le YAML ne fait
# que récupérer le dépôt et lancer ce script. Se lance aussi à la main, depuis la racine du dépôt.
#   BASE_REF  la branche cible d'une pull request (origin/main) ; sans elle, les portes ne sont pas jouées.
set -eu

python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)' \
  || { echo "Python 3.10 ou plus est requis." >&2; exit 1; }

echo "== Tests du CLI harness"
python3 -m unittest discover -s cli/tests

echo "== Tests du plugin ai-sdlc"
python3 -m unittest discover -s plugins/ai-sdlc/cli/tests

if [ -n "${BASE_REF:-}" ]; then
  echo "== Le plan d'avancement suit le changement"
  python3 cli/harness.py progress check --base "$BASE_REF"
  echo "== Portes de la pull request"
  python3 plugins/ai-sdlc/cli/ai_sdlc.py ci pr . --base "$BASE_REF"
fi
