# Interview of go-hexa: 4 question(s)

- I6, held only by the owner: asked at question 2

## 1
**Question**: 1) MODE — who checks an agent's work? This decides how strict the file must be. 'Delegation' (default): an agent takes a whole task and opens a PR, checked by CI and the guardrails, nobody reviewing along the way. 'Assistance': a person drives and reviews every diff. If every change is reviewed live today and no agent runs outside a session, pick assistance. Which one?

**Answer** (mode, ci): Delegation. We want to hand over whole tickets and review the PR at the end.
GitHub Actions. The `test` and `arch` jobs block the merge. The `lint` job runs but does not block: there are too many inherited warnings.

## 2
**Question**: 2) FORBIDDEN — what must an agent NEVER do, even if a task seems to ask for it? Your docs already point at three candidates: (a) run 'make reset-db' or 'make migrate' by hand against the staging/production database (Feb 3 incident: dropped the shared schema, lost 2 days of QA data); (b) run the deploy scripts (deploy/apply.sh, deploy/plan.sh) from a dev machine — deploy goes only through the deploy.yml workflow; (c) modify a migration already applied in staging/production (add a new numbered file instead). Should all three be Forbidden lines? Anything to add (force-push to main, touching a folder, secrets)?

**Answer** (team, ci, forbidden, oral): Four developers, and one QA person who uses the staging database.
GitHub Actions. The `test` and `arch` jobs block the merge. The `lint` job runs but does not block: there are too many inherited warnings.
Touching a database that is not your own, modifying a migration already applied, running `deploy.yml` without `dry_run`.
One thing that is written nowhere, and that we repeat at every review: when an endpoint replays a request already processed, its response carries the `Idempotency-Replayed: true` header. The mobile app has used it since June 2026 to avoid showing the confirmation twice. `POST /transfers` does not do it yet, it is in the backlog; every new write endpoint must do it.

## 3
**Question**: 3) TOOLS & CI — which coding agents do you use (Claude Code only, or also Copilot, Cursor, Codex)? I'll write stub files for the ones you name. And: today CI runs three jobs — 'test' (go vet + go test) and 'arch' (archcheck) both block a merge, but 'lint' (golangci-lint, which holds the ADR-0002 'no float for amounts' rule) is marked continue-on-error, so it does NOT block. Is lint intentionally non-blocking for now, or should I treat the no-float rule as enforced?

**Answer** (ci, tools, lint): GitHub Actions. The `test` and `arch` jobs block the merge. The `lint` job runs but does not block: there are too many inherited warnings.
Claude Code and Copilot.
Nobody took the time to pay off the debt. Yes, we know it weakens what relies on it.

## 4
**Question**: 4) WRITTEN NOWHERE — what do you find yourself repeating at review, or what does a newcomer only learn by getting it wrong, that NO file in the repo states? (One example of the kind of thing I mean: 'a new write endpoint must require the Idempotency-Key — nothing checks it, only review catches it.' If there's genuinely nothing beyond what the docs already say, just tell me 'nothing' and I won't invent one.)

**Answer** (ci, oral): GitHub Actions. The `test` and `arch` jobs block the merge. The `lint` job runs but does not block: there are too many inherited warnings.
One thing that is written nowhere, and that we repeat at every review: when an endpoint replays a request already processed, its response carries the `Idempotency-Replayed: true` header. The mobile app has used it since June 2026 to avoid showing the confirmation twice. `POST /transfers` does not do it yet, it is in the backlog; every new write endpoint must do it.
