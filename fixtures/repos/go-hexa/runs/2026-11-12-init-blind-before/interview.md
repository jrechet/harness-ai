# Interview of go-hexa: 6 question(s)

- I6, held only by the owner: never asked

## 1
**Question**: Mode: delegation (proposed default: the agent receives a whole task and comes back with a PR) or assistance (the human drives and reviews every diff live)?

**Answer** (mode): Delegation. We want to hand over whole tickets and review the PR at the end.

## 2
**Question**: Forbidden: what must an agent never touch or do (folders, secrets, shared database, prod migrations, force push...)?

**Answer** (forbidden): Touching a database that is not your own, modifying a migration already applied, running `deploy.yml` without `dry_run`.

## 3
**Question**: Tools and CI: which agents do you use (Claude Code alone, or also Copilot, Cursor, Codex)? Which CI, and which checks block the merge today?

**Answer** (ci, tools): GitHub Actions. The `test` and `arch` jobs block the merge. The `lint` job runs but does not block: there are too many inherited warnings.
Claude Code and Copilot.

## 4
**Question**: internal/app/fees.go computes the fee with a float64 (feeRate = 0.015, math.Round), whereas ADR 0002 forbids any float in internal/app. Is it an accepted exception, or a violation to fix? (proposed default: known violation, not to be imitated)

**Answer** (forbidden): Touching a database that is not your own, modifying a migration already applied, running `deploy.yml` without `dry_run`.

## 5
**Question**: The README cites 'make e2e' (end-to-end scenarios), but the Makefile has no e2e target. Does this command exist elsewhere or was it abandoned? (default: I do not put it in AGENTS.md)

**Answer** (e2e): The `make e2e` target was removed a year ago with the old test bench; the README did not follow.

## 6
**Question**: A new endpoint that changes a balance must require Idempotency-Key (ADR 0003); POST /accounts is exempt from it and its catch-up is in the backlog. Should an agent leave POST /accounts as it is as long as the catch-up ticket is not handed to it? (default: yes)

**Answer** (first-task, accounts): Add an endpoint from a use case, from the handler down to the test.
Correct, `POST /accounts` has no idempotency key. It is in the backlog, not a priority.
