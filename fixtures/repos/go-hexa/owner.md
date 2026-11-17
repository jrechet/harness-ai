# Fictional owner — go-hexa (ledger)

This file is given to the agent that plays harness-init blind: these are the team's answers to the interview. The planted facts are in the repository, to be found, except one: the one the team adds of its own accord below is read nowhere else.

## Answers to the interview
1. **Mode**: delegation. We want to hand over whole tickets and review the PR at the end.
2. **Team**: four developers, one QA person who uses the staging database.
3. **CI**: GitHub Actions. The `test` and `arch` jobs block the merge. The `lint` job runs but does not block, "there are too many inherited warnings".
4. **Tools**: Claude Code and Copilot.
5. **First task to delegate**: add an endpoint from a use case, from the handler down to the test.
6. **Forbidden**: touching a database that is not your own, modifying a migration already applied, running `deploy.yml` without `dry_run`.

## What the team adds of its own accord
"One thing that is written nowhere, and that we repeat at every review: when an endpoint replays a request already processed, its response carries the `Idempotency-Replayed: true` header. The mobile app has used it since June 2026 to avoid showing the confirmation twice. `POST /transfers` does not do it yet, it is in the backlog; every new write endpoint must do it."

## If the agent asks other questions
- "Why does the lint not block?": nobody took the time to pay off the debt. Yes, we know it weakens what relies on it.
- "`POST /accounts` has no idempotency key?": correct, it is in the backlog, not a priority.
- "`make e2e`?": the target was removed a year ago with the old test bench, the README did not follow.
- On everything else: "look in `docs/`, it is written down". The team knows nothing more than what the ADRs, the post-mortem and the operations note say.

## What the team expects
A short file. It already has a CONTRIBUTING that nobody reads and does not want a second one.
