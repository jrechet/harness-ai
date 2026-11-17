#!/usr/bin/env bash
# Old manual deployment, before release.yml. No longer called anywhere.
set -euo pipefail
VERSION="$1"
docker build -t registry.acme.io/billing-api:"$VERSION" .
docker push registry.acme.io/billing-api:"$VERSION"
ssh deploy@prod.acme.io "docker pull registry.acme.io/billing-api:$VERSION && docker compose up -d"
