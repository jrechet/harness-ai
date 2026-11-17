# billing-api — instructions for agents

Mode: **delegation**. An agent can be handed a whole task and open a PR without intermediate review. What is mandatory here is enforced by CI; this file explains, it does not guarantee.

## What this repo does
Acme's billing API (invoices, PostgreSQL), delivered to production by the `release.yml` workflow.

## What changes → what to run
| If you touch… | Run… | Enforced in CI by |
|---|---|---|
| Java code | `./gradlew checkstyleMain checkstyleTest test` | `ci.yml` job `build` (PR, `develop`, `main`) |
| a migration (`src/main/resources/db/migration/`) | `./gradlew test` | nothing: no test freezes the applied migrations |
| `scripts/*.mjs` or `.github/workflows/release.yml` | `node --check scripts/<file>`; never a real run without agreement | nothing: `release.yml` only runs by hand |

## Rules
Each rule says why and what enforces it. A rule marked `(unverified)` is a debt: the next step is to push it into CI.
- A controller never depends on a repository; business logic lives in the services. Why: to keep the billing rules testable outside HTTP. Enforced by: `src/test/java/com/acme/billing/ArchitectureTest.java` (`controllers_do_not_touch_repositories`).
- An applied Flyway migration is never modified; a `V<n+1>__*.sql` is added. Why: Flyway refuses to start on a modified checksum, the application no longer restarts in production. (unverified; target: checksum test of the migrations in `ci.yml`)
- A release or a hotfix goes through `release.yml`, triggered according to the `release` contract, never through `scripts/old-deploy.sh` nor through `docker`/`ssh` by hand. Why: manual releases often get the version wrong; only the workflow traces version, tag and image together. (unverified; target: removal of `old-deploy.sh`, `deploy` job under `environment: production`)

## Forbidden
- Triggering `release.yml` or any deployment to production without the explicit validation of a human in the task or the PR. Triggering `release.yml` is deploying: the job publishes and deploys in one go.
- Modifying a Flyway migration already applied (any existing file of `src/main/resources/db/migration/`).
- Pushing directly to `main`: always a branch and a PR.

## Working process
- Stop and ask when: the task touches a Forbidden item, adds a migration or a dependency, changes a workflow of `.github/workflows/`, or CI is red for a cause unrelated to your diff.
- A task is done when: `ci.yml` green on the PR, a test covers the change, the PR explains the why, no TODO and no disabled test (`@Disabled`) added.
- CI red: fix it if the cause is in your diff; otherwise report it in the PR and leave it alone.
- Flaky test: re-run once; if it stays flaky, open an issue, do not disable it.
- A PR targets `develop` unless explicitly asked otherwise; beyond ten files or so, split.

## Delegated tasks
Each recurring task has its contract in `.claude/skills/`:
- `release` — prepare, get validated, trigger and verify a release or a hotfix via `release.yml`.

## Maintaining this file
- A review comment that starts with `rule:` is a candidate rule. It is added here in the same PR, with the link to the comment, or collected by harness-harvest (not installed to date: the collection is manual).
- Before adding a sentence, check whether a linter, a test or a CI check can carry the rule: an enforced rule is shortened, a rule that is only told is a debt.
- A rule with no incident for six months is a candidate for removal at the next harness-audit.
- This file is reviewed by `harness-audit`; the "Mode" line sets the severity.
- `harness-harvest` reviews the activity since the marker below and proposes the changes in a dedicated PR.

<!-- harvest: last=2026-11-09 ref=init -->
