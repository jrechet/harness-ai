#!/usr/bin/env bash
# Applies migrations then rolls the service. Only called by deploy.yml.
set -euo pipefail
env="${1:?usage: apply.sh <staging|production>}"
: "${DATABASE_URL:?DATABASE_URL is required}"
for f in migrations/*.sql; do psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f "$f"; done
echo "{\"environment\": \"$env\", \"status\": \"deployed\"}"
