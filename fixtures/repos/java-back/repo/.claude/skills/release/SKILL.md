---
name: release
description: Publish a version of billing-api to production. Use when the user asks for a release, a production rollout, a deployment or a hotfix.
---

# Release

## Before you start
1. Check that the CI of `develop` is green: open the Actions tab and look at the last run of `ci.yml`. Never release on a red develop.
2. Check that there is no Flyway migration not applied in prod by comparing `src/main/resources/db/migration` with the `flyway_schema_history` table of prod (ask the owner for a dump if needed).
3. Make sure you are on an up-to-date `develop`: `git checkout develop && git pull`.

## Run the release
4. Run `node scripts/release.mjs`. The script infers the kind of version from the branch name and triggers the `release.yml` workflow.
5. Follow the workflow with `gh run watch`. When the output contains `SUCCESS`, the image is deployed to production.
6. If the output contains `ERROR` or `FAILED`, warn the owner and do not try to run it again.

## Hotfix
7. From a `hotfix/*` branch, run `node scripts/hotfix.mjs` instead: it does the same thing with a patch number.

## Afterwards
8. Announce the version in #releases with the list of PRs included.
