# Interview of go-hexa: 4 question(s)

- I6, held only by the owner: asked at question 2

## 1
**Question**: MODE — Should an agent work in 'delegation' mode (default: it takes a whole task and opens a PR, with CI and the arch check as the only gate, nobody reviewing along the way) or 'assistance' mode (a person drives and reviews every diff)? This decides who checks the agent's work and how strict the written rules must be. Default if you don't mind: delegation.

**Answer** (mode, ci): Delegation. We want to hand over whole tickets and review the PR at the end.
GitHub Actions. The `test` and `arch` jobs block the merge. The `lint` job runs but does not block: there are too many inherited warnings.

## 2
**Question**: FORBIDDEN — What must an agent NEVER touch or do, even if a task seems to ask for it? From the repo I can already see candidates: running 'make reset-db' / 'make migrate' by hand against the shared staging or production database (the Feb 3 2026 incident lost two days of QA data), and running the deploy scripts (deploy/apply.sh, deploy/plan.sh) from a local machine. Please confirm those and add anything else (secrets, folders, force-push, rewriting applied migrations, etc.).

**Answer** (team, forbidden, oral): Four developers, and one QA person who uses the staging database.
Touching a database that is not your own, modifying a migration already applied, running `deploy.yml` without `dry_run`.
One thing that is written nowhere, and that we repeat at every review: when an endpoint replays a request already processed, its response carries the `Idempotency-Replayed: true` header. The mobile app has used it since June 2026 to avoid showing the confirmation twice. `POST /transfers` does not do it yet, it is in the backlog; every new write endpoint must do it.

## 3
**Question**: TOOLS & CI — Which coding agents will use this repo: Claude Code only, or also GitHub Copilot, Cursor, and/or Codex? (This decides which stub files I create.) And a confirmation: in CI today the 'test' job (go vet + go test) and the 'arch' job (archcheck) block a merge, but the 'lint' job is marked continue-on-error — so the 'no float for amounts' lint rule does NOT actually block. Is lint meant to stay non-blocking for now?

**Answer** (ci, tools, lint): GitHub Actions. The `test` and `arch` jobs block the merge. The `lint` job runs but does not block: there are too many inherited warnings.
Claude Code and Copilot.
Nobody took the time to pay off the debt. Yes, we know it weakens what relies on it.

## 4
**Question**: WRITTEN NOWHERE — What do you find yourself repeating at every review, or what does a newcomer get wrong because no file says it, that isn't already captured in the ADRs, the post-mortem or operations.md? If the honest answer is 'nothing', that's a fine answer. (One example I suspect: a new write endpoint can silently forget the Idempotency-Key header, since nothing checks it — but tell me what YOU repeat.)

**Answer** (ci, oral): GitHub Actions. The `test` and `arch` jobs block the merge. The `lint` job runs but does not block: there are too many inherited warnings.
One thing that is written nowhere, and that we repeat at every review: when an endpoint replays a request already processed, its response carries the `Idempotency-Replayed: true` header. The mobile app has used it since June 2026 to avoid showing the confirmation twice. `POST /transfers` does not do it yet, it is in the backlog; every new write endpoint must do it.
