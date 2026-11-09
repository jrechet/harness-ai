#!/usr/bin/env bash
# Ancien déploiement manuel, avant release.yml. Plus appelé nulle part.
set -euo pipefail
VERSION="$1"
docker build -t registry.acme.io/billing-api:"$VERSION" .
docker push registry.acme.io/billing-api:"$VERSION"
ssh deploy@prod.acme.io "docker pull registry.acme.io/billing-api:$VERSION && docker compose up -d"
