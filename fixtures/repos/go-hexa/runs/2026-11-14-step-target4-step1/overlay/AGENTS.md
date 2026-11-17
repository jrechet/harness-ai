# ledger — instructions for agents

Mode: **delegation**. An agent receives a whole ticket and comes back with a PR; the `test` and `arch` jobs of the CI decide, this file explains.

## What this repo does
Ledger service: open an account, read a balance, transfer money. Decisions in `docs/adr/`, incidents in `docs/postmortems/`, operations in `docs/operations.md`.

## What changes → what to run
| If you touch… | Run… | Enforced in CI by |
|---|---|---|
| Go code | `go vet ./... && go test ./...` | job `test` |
| an import between layers | `go run ./tools/archcheck` | job `arch` |
| `migrations/` | `go run ./tools/migrationcheck -base origin/main` | job `migrations` |
| `internal/adapters/postgres` | `make test-integration`, on your local database | nothing: these tests do not run in CI |

## Rules
- The domain depends on nothing, a use case only knows ports, the adapters do not know each other. Why: testing a transfer required a database. Enforced by: `tools/archcheck`, job `arch`. [2026-11]
- Every endpoint that changes a balance requires `Idempotency-Key`, looked up inside the write transaction, never before opening it. Why: an account debited twice by €480, 37 accounts affected (`docs/postmortems/2026-04-double-debit.md`). Enforced by: `internal/adapters/httpapi/idempotency_guard_test.go`, job `test` (presence of the key on every non-GET route; the lookup inside the transaction is left to the review). Single exemption, `POST /accounts`: do not take it as a model. [2026-11]
- A response replayed by idempotency key carries the `Idempotency-Replayed: true` header. Why: the mobile app uses it to avoid showing two confirmations; told by the team, written nowhere else. `POST /transfers` does not do it yet. (unverified) [2026-06]
- An amount is a `domain.Money`, an integer in cents; no float in `internal/domain` nor `internal/app`. Why: rounding errors that distort a balance, ADR 0002. `internal/app/fees.go` already violates the rule, and the `lint` job that carries this check does not block. (unverified) [2026-11]
- An applied migration is never modified again: a file is added at the next number. Why: staging and production only replay what `deploy.yml` passes them. Enforced by: `tools/migrationcheck`, job `migrations` (PR only). [2026-11]

## Forbidden
- `make reset-db` and `make migrate` outside your local database. Why: two days of QA data lost on staging on February 3, 2026. Enforced by: `tools/localdb`, called by both targets (refusal outside localhost/loopback/socket), job `test`. [2026-11]
- Running `deploy.yml` with `dry_run` set to false, or towards `production`. Why: owner's request, no known incident. [2026-11]
- Modifying an existing file of `migrations/`. Why: see the migrations rule. Enforced by: `tools/migrationcheck`, job `migrations`. [2026-11]

## Working process
- Stop and ask before touching a migration, the schema of an API contract or `deploy.yml`, and when the ticket is ambiguous about an amount or a rounding. The rest, decide and write it in the PR.
- A task is done when `make test` and `make arch` pass, a test covers the change, and the PR says why in two lines.
- Red CI: if the cause is in your diff, fix it; otherwise, report it in the PR and do not touch it.
- Flaky test: rerun once, then open an issue; never disable it.

## Maintaining this file
- A review comment that starts with `rule:` is a candidate rule. It is added here in the same PR, dated, with the link to the comment, or collected by harness-harvest.
- Before adding a sentence, look for a linter, a test or a CI check that can carry the rule: an enforced rule is shortened, a narrated rule is a debt.
- A rule with no incident for six months, or written for a past generation of models, is a candidate for removal at the next relevance review.

<!-- harvest: last=2026-11-14 ref=init -->
