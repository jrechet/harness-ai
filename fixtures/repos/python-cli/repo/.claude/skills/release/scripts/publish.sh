#!/usr/bin/env bash
# Fallback publication from the workstation, when release.yml does not go through.
set -euo pipefail
: "${PYPI_TOKEN:?PYPI_TOKEN required}"
rm -rf dist && python -m build
TWINE_USERNAME=__token__ TWINE_PASSWORD="$PYPI_TOKEN" twine upload dist/*
