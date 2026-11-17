---
name: release
description: Prepare, get validated, trigger and verify a release or a hotfix of billing-api via the release.yml workflow. Use as soon as someone asks to "ship a version", "release", "deliver to prod", "do a hotfix". Never triggers the workflow without an explicit "yes" from a human (Forbidden item of AGENTS.md).
---

# Releasing billing-api

`release.yml` builds the jar, publishes the image `registry.acme.io/billing-api:<version>`, sets the tag `v<version>` **and deploys to production** in the same job. Triggering it is deploying: human validation is mandatory beforehand.

## 1. Collect — nothing is inferred
- **Version** `x.y.z`: decided by the human and given in the task. Absent → ask for it. Do not infer it from the branch name (`scripts/release.mjs` does and gets it wrong: a release from `develop` is not always a minor).
- **Ref**: a release starts from `develop` or `release/x.y.z`; a hotfix starts from `hotfix/*`. Other branch → stop.
- **Type**: release or hotfix (the hotfix increments the patch; the `hotfix` input of `release.yml` is read by no step today).

## 2. Preconditions — stop as soon as one fails
1. CI green on the targeted commit: `gh run list --workflow ci.yml --branch <ref> --limit 1 --json conclusion,headSha` → `success` and the SHA of the tip.
2. Tag absent: `git ls-remote --tags origin "v<x.y.z>"` returns nothing.
3. Increasing version: `x.y.z` is strictly greater than the content of `VERSION`.
4. No migration modified in the delivered range: `git diff --name-status v<previous>..<ref> -- src/main/resources/db/migration/` shows only additions (`A`).

## 3. Plan and validation
Show the plan: version, ref, SHA, type, tag that will be created, image that will be published, "deploys to production". Then **ask for validation** and wait for an explicit "yes". No "yes" → the task stops there, without triggering anything.

## 4. Trigger
```
gh workflow run release.yml -f version=<x.y.z> -f ref=<ref> [-f hotfix=true]
gh run list --workflow release.yml --limit 1 --json databaseId,url   # keep the URL of the run
gh run watch <databaseId> --exit-status
```
`release.yml` is a `workflow_dispatch`: GitHub only accepts it from the default branch of the repository; if the command is refused, that is usually the reason, not a mistake of yours.

## 5. Verification — no success on someone's word
- `gh run view <databaseId> --json conclusion` → `success` (a "SUCCESS" in the log is not evidence).
- `git ls-remote --tags origin "v<x.y.z>"` returns the tag.
- Production answers in the new version (health endpoint given by the team; failing that, ask for it and note it here).

## 6. Afterwards
The workflow does not update `VERSION`: open a PR to `develop` that sets it to `x.y.z`, citing the URL of the run.

## Abort cases
- Run failed before `docker push`: nothing is published, read `gh run view <id> --log-failed`, fix in a PR, do not re-run blindly.
- Run failed after `docker push` or after the tag: the image or the tag exist without a deployment. Do not re-run, do not delete anything: report the exact state (image, tag, run) and let the human decide.

## Done when
Run `success` with its URL, tag present, production verified, `VERSION` PR opened, and all of that written in the report of the task.
