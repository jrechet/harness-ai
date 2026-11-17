# Interview of go-hexa: 3 question(s)

- I6, held only by the owner: never asked

## 1
**Question**: When must an agent stop and ask you the question rather than carry on? (proposed default: the task requires an architecture choice or a new migration, touches a forbidden item, or the CI fails for a reason unrelated to the task)

**Answer** (ci, forbidden, stop): GitHub Actions. The `test` and `arch` jobs block the merge. The `lint` job runs but does not block: there are too many inherited warnings.
Touching a database that is not your own, modifying a migration already applied, running `deploy.yml` without `dry_run`.
It stops and asks before touching a migration, the schema of an API contract or `deploy.yml`, and when the ticket is ambiguous about an amount or a rounding. The rest, it decides and writes it in the PR.

## 2
**Question**: When is a task done? (proposed default: test, arch and migrations jobs green, a test covers the change, the PR says why; if internal/adapters/postgres is touched, make test-integration run locally and said in the PR)

**Answer** (ci, forbidden, done): GitHub Actions. The `test` and `arch` jobs block the merge. The `lint` job runs but does not block: there are too many inherited warnings.
Touching a database that is not your own, modifying a migration already applied, running `deploy.yml` without `dry_run`.
A task is done when `make test` and `make arch` pass, a test covers the change, and the PR says why in two lines.

## 3
**Question**: What does the agent do when facing a red CI or a flaky test? (proposed default: red CI, it fixes it if the cause is in its diff, otherwise it reports it in the PR without touching it; flaky test, it reruns once, then opens an issue, without ever disabling the test)

**Answer** (ci, red-ci): GitHub Actions. The `test` and `arch` jobs block the merge. The `lint` job runs but does not block: there are too many inherited warnings.
CI red because of its diff: it fixes it. Red for an unrelated cause: it reports it in the PR and does not touch it. A flaky test: it reruns once, then opens an issue; it never disables it.
