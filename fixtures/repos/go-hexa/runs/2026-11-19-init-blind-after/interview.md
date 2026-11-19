# Interview of go-hexa: 4 question(s)

- I6, held only by the owner: asked at question 2

## 1
**Question**: MODE — This decides who checks the agent's work and how strict the rules must be. Default is 'delegation': an agent takes a whole task and opens a PR, with the CI (not a human) as the checkpoint along the way. The alternative is 'assistance': a person drives and reviews every diff. Which mode fits how you actually work today?

**Answer** (mode, ci): Delegation. We want to hand over whole tickets and review the PR at the end.
GitHub Actions. The `test` and `arch` jobs block the merge. The `lint` job runs but does not block: there are too many inherited warnings.

## 2
**Question**: FORBIDDEN — These become the hard lines the agent never crosses. From the repo I can already see candidates: never run 'make reset-db' / 'make migrate' / the deploy scripts against a staging or production DATABASE_URL (the Feb 2026 incident lost two days of shared QA data this way); never modify a migration that has already been applied (add a new numbered file instead); never trigger deploy.yml or run deploy/apply.sh yourself. Do you confirm these, and is there anything else an agent must never touch or do (folders, secrets, the shared staging DB, force-push)?

**Answer** (team, forbidden, oral): Four developers, and one QA person who uses the staging database.
Touching a database that is not your own, modifying a migration already applied, running `deploy.yml` without `dry_run`.
One thing that is written nowhere, and that we repeat at every review: when an endpoint replays a request already processed, its response carries the `Idempotency-Replayed: true` header. The mobile app has used it since June 2026 to avoid showing the confirmation twice. `POST /transfers` does not do it yet, it is in the backlog; every new write endpoint must do it.

## 3
**Question**: TOOLS — Which AI coding tools do you want stub files written for: Claude Code only, or also GitHub Copilot, Cursor, and/or Codex? (This only decides which thin pointer files I create; all of them point to the same AGENTS.md.)

**Answer** (tools): Claude Code and Copilot.

## 4
**Question**: WRITTEN NOWHERE — This is the one thing reading the repo cannot replace. What do you find yourself repeating at every code review, or what does a newcomer learn only by getting it wrong, that no file in the repo states? If the honest answer is 'nothing — it's all in the ADRs and docs', that's a fine answer; I won't invent one.

**Answer** (oral): One thing that is written nowhere, and that we repeat at every review: when an endpoint replays a request already processed, its response carries the `Idempotency-Replayed: true` header. The mobile app has used it since June 2026 to avoid showing the confirmation twice. `POST /transfers` does not do it yet, it is in the backlog; every new write endpoint must do it.
