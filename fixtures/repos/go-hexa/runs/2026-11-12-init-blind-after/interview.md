# Interview of go-hexa: 7 question(s)

- I6, held only by the owner: asked at question 4

## 1
**Question**: 1. Mode: delegation (default: the agent receives a whole task and comes back with a PR) or assistance (you review every diff live, no agent outside a session)?

**Answer** (mode): Delegation. We want to hand over whole tickets and review the PR at the end.

## 2
**Question**: 2. Forbidden: what must an agent never touch or do (folders, secrets, shared database, prod migrations, force push...)?

**Answer** (forbidden): Touching a database that is not your own, modifying a migration already applied, running `deploy.yml` without `dry_run`.

## 3
**Question**: 3. Tools and CI: which agents do you use (Claude Code alone, or also Copilot, Cursor, Codex)? Which CI, and which checks block the merge today?

**Answer** (ci, tools): GitHub Actions. The `test` and `arch` jobs block the merge. The `lint` job runs but does not block: there are too many inherited warnings.
Claude Code and Copilot.

## 4
**Question**: 4. What do you repeat at every review, or what does a newcomer learn by getting it wrong, that no file says?

**Answer** (oral): One thing that is written nowhere, and that we repeat at every review: when an endpoint replays a request already processed, its response carries the `Idempotency-Replayed: true` header. The mobile app has used it since June 2026 to avoid showing the confirmation twice. `POST /transfers` does not do it yet, it is in the backlog; every new write endpoint must do it.

## 5
**Question**: internal/app/fees.go computes the fee with float64, contrary to ADR 0002; the lint job that would carry the rule does not block. Is this known? Should an agent fix it when it goes through there, or not touch it?

**Answer** (ci, forbidden, lint): GitHub Actions. The `test` and `arch` jobs block the merge. The `lint` job runs but does not block: there are too many inherited warnings.
Touching a database that is not your own, modifying a migration already applied, running `deploy.yml` without `dry_run`.
Nobody took the time to pay off the debt. Yes, we know it weakens what relies on it.

## 6
**Question**: The README cites 'make e2e' but the Makefile has no e2e target. Do these scenarios exist elsewhere, or is the line stale?

**Answer** (e2e): The `make e2e` target was removed a year ago with the old test bench; the README did not follow.

## 7
**Question**: For the forbidden item 'a database that is not your own': should it be understood that make reset-db and make migrate are only run on a local database of your own, never with a staging or production DATABASE_URL?

**Answer** (forbidden): Touching a database that is not your own, modifying a migration already applied, running `deploy.yml` without `dry_run`.
