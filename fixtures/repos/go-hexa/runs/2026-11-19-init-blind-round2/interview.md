# Interview of go-hexa: 5 question(s)

- I6, held only by the owner: asked at question 5

## 1
**Question**: MODE: Should agents work in DELEGATION (an agent takes a whole task and opens a PR, the CI and guardrails are the only check along the way) or ASSISTANCE (a person drives and reviews every diff)? This decides how strict the written rules must be. Default if you don't say: delegation. Given this is a financial ledger, tell me if you'd rather a human reviews every change.

**Answer** (mode, ci): Delegation. We want to hand over whole tickets and review the PR at the end.
GitHub Actions. The `test` and `arch` jobs block the merge. The `lint` job runs but does not block: there are too many inherited warnings.

## 2
**Question**: FORBIDDEN: What must an agent NEVER touch or do, even if a task seems to ask for it? My candidates from reading the repo: (a) never run 'make reset-db' or 'make migrate' by hand against staging/production (reset-db drops the whole schema; staging is shared with QA datasets and was wiped this way on 2026-02-03); (b) never run the deploy scripts (deploy/apply.sh, deploy/plan.sh) from a machine — deploys go only through the deploy.yml workflow; (c) never modify a migration already applied in staging/prod (add a new numbered file instead); (d) never force-push. Confirm, remove, or add to this list.

**Answer** (team, ci, forbidden): Four developers, and one QA person who uses the staging database.
GitHub Actions. The `test` and `arch` jobs block the merge. The `lint` job runs but does not block: there are too many inherited warnings.
Touching a database that is not your own, modifying a migration already applied, running `deploy.yml` without `dry_run`.

## 3
**Question**: TOOLS: Besides Claude Code, which AI agents do you use that need a stub file — GitHub Copilot, Cursor, Codex? Default if you don't say: Claude Code only (plus plain stubs for Copilot and Cursor if you want them).

**Answer** (tools): Claude Code and Copilot.

## 4
**Question**: CI BLOCKING: I observe that in .github/workflows/ci.yml the 'test' (go vet + go test) and 'arch' (archcheck, enforcing ADR 0001) jobs block a merge, but the 'lint' job is marked continue-on-error:true — so the 'no float for money / int64 cents' rule (ADR 0002, enforced by golangci-lint forbidigo) does NOT actually block a merge today. Is that intended, or should I treat the money rule as enforced?

**Answer** (ci, lint): GitHub Actions. The `test` and `arch` jobs block the merge. The `lint` job runs but does not block: there are too many inherited warnings.
Nobody took the time to pay off the debt. Yes, we know it weakens what relies on it.

## 5
**Question**: WRITTEN NOWHERE: What do you repeat at every code review, or what does a newcomer learn only by getting it wrong, that no file in the repo states? If the honest answer is 'nothing', say so — I won't invent one. (Also: the README's Getting Started lists 'make e2e', but the Makefile has no e2e target, only 'test-integration' — which command is the real one?)

**Answer** (e2e, oral): The `make e2e` target was removed a year ago with the old test bench; the README did not follow.
One thing that is written nowhere, and that we repeat at every review: when an endpoint replays a request already processed, its response carries the `Idempotency-Replayed: true` header. The mobile app has used it since June 2026 to avoid showing the confirmation twice. `POST /transfers` does not do it yet, it is in the backlog; every new write endpoint must do it.
