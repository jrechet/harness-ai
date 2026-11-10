#!/usr/bin/env bash
# Prints what a deployment to $1 would do: pending migrations and the image tag.
set -euo pipefail
env="${1:?usage: plan.sh <staging|production>}"
echo "{\"environment\": \"$env\", \"image\": \"ledgerd:$(git rev-parse --short HEAD)\", \"migrations\": $(ls migrations/*.sql | wc -l)}"
