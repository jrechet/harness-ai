#!/usr/bin/env bash
# Publication de secours depuis le poste, quand release.yml ne passe pas.
set -euo pipefail
: "${PYPI_TOKEN:?PYPI_TOKEN requis}"
rm -rf dist && python -m build
TWINE_USERNAME=__token__ TWINE_PASSWORD="$PYPI_TOKEN" twine upload dist/*
