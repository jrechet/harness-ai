# Interview of go-hexa: 3 question(s)

- I6, held only by the owner: asked at question 3

## 1
**Question**: Do the GitHub staging and production environments of deploy.yml have protection rules (required reviewers, deployment branches limited to main)? Which ones exactly?

**Answer** (forbidden): Touching a database that is not your own, modifying a migration already applied, running `deploy.yml` without `dry_run`.

## 2
**Question**: Is the main branch protected (direct push forbidden, test/arch/migrations checks required before merging)?

**Answer** (ci, forbidden): GitHub Actions. The `test` and `arch` jobs block the merge. The `lint` job runs but does not block: there are too many inherited warnings.
Touching a database that is not your own, modifying a migration already applied, running `deploy.yml` without `dry_run`.

## 3
**Question**: Is the rule "Idempotency-Replayed: true" on a replayed response still wanted by the mobile team?

**Answer** (team, oral): Four developers, and one QA person who uses the staging database.
One thing that is written nowhere, and that we repeat at every review: when an endpoint replays a request already processed, its response carries the `Idempotency-Replayed: true` header. The mobile app has used it since June 2026 to avoid showing the confirmation twice. `POST /transfers` does not do it yet, it is in the backlog; every new write endpoint must do it.
