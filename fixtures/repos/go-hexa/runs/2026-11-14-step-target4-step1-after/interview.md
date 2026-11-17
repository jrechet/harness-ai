# Interview of go-hexa: 7 question(s)

- I6, held only by the owner: asked at question 7

## 1
**Question**: What is the first task you want to delegate entirely to an agent on this repository?

**Answer** (mode, first-task): Delegation. We want to hand over whole tickets and review the PR at the end.
Add an endpoint from a use case, from the handler down to the test.

## 2
**Question**: When must an agent stop and ask instead of carrying on?

**Answer** (stop): It stops and asks before touching a migration, the schema of an API contract or `deploy.yml`, and when the ticket is ambiguous about an amount or a rounding. The rest, it decides and writes it in the PR.

## 3
**Question**: When is a task done (definition of done)?

**Answer** (done): A task is done when `make test` and `make arch` pass, a test covers the change, and the PR says why in two lines.

## 4
**Question**: What must the agent do when facing a red CI, and when facing a flaky test?

**Answer** (ci, red-ci): GitHub Actions. The `test` and `arch` jobs block the merge. The `lint` job runs but does not block: there are too many inherited warnings.
CI red because of its diff: it fixes it. Red for an unrelated cause: it reports it in the PR and does not touch it. A flaky test: it reruns once, then opens an issue; it never disables it.

## 5
**Question**: Adding an endpoint necessarily changes the API contract: must the agent stop only when it modifies or removes an existing route or field (adding a new route or field being allowed)?

**Answer** (stop): It stops and asks before touching a migration, the schema of an API contract or `deploy.yml`, and when the ticket is ambiguous about an amount or a rounding. The rest, it decides and writes it in the PR.

## 6
**Question**: For migrations: can the agent ADD a migration file at the next number without asking, and only stop to modify an existing migration (already forbidden)? Or must it stop as soon as a new migration file is needed?

**Answer** (forbidden, stop, new-migration): Touching a database that is not your own, modifying a migration already applied, running `deploy.yml` without `dry_run`.
It stops and asks before touching a migration, the schema of an API contract or `deploy.yml`, and when the ticket is ambiguous about an amount or a rounding. The rest, it decides and writes it in the PR.
Adding a migration at the next number is the normal path: no need to ask. What needs my agreement is modifying an existing migration, or a migration that deletes or rewrites data.

## 7
**Question**: An "add an endpoint" ticket necessarily adds a route to the API contract. If the agent must ask every time, the task cannot be delegated. I propose: adding a route or a field is allowed; renaming, removing or changing the type of an existing route or field needs your agreement. Agreed, yes or no?

**Answer** (mode, oral): Delegation. We want to hand over whole tickets and review the PR at the end.
One thing that is written nowhere, and that we repeat at every review: when an endpoint replays a request already processed, its response carries the `Idempotency-Replayed: true` header. The mobile app has used it since June 2026 to avoid showing the confirmation twice. `POST /transfers` does not do it yet, it is in the backlog; every new write endpoint must do it.
