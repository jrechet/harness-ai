# ledger — instructions for agents

Mode: **delegation**. An agent receives a whole ticket and comes back with a PR; the `test` and `arch` jobs of the CI decide, this file explains.

## What this repo does
Ledger service: open an account, read a balance, transfer money. Decisions in `docs/adr/`, incidents in `docs/postmortems/`, operations in `docs/operations.md`.

## What changes → what to run
| If you touch… | Run… | Enforced in CI by |
|---|---|---|
| Go code | `go vet ./... && go test ./...` | job `test` |
| an import between layers | `go run ./tools/archcheck` | job `arch` |
| `internal/adapters/postgres` | `make test-integration`, on your local database | nothing: these tests do not run in CI |

## Rules
- The domain depends on nothing, a use case only knows ports, the adapters do not know each other. Why: testing a transfer required a database. Enforced by: `tools/archcheck`, job `arch`. [2026-11]
- Every endpoint that changes a balance requires `Idempotency-Key`, looked up inside the write transaction, never before opening it. Why: an account debited twice by €480, 37 accounts affected (`docs/postmortems/2026-04-double-debit.md`). `POST /accounts` does not apply it yet, do not take it as a model. (unverified) [2026-11]
- A response replayed by idempotency key carries the `Idempotency-Replayed: true` header. Why: the mobile app uses it to avoid showing two confirmations; told by the team, written nowhere else. `POST /transfers` does not do it yet. (unverified) [2026-06]
- An amount is a `domain.Money`, an integer in cents; no float in `internal/domain` nor `internal/app`. Why: rounding errors that distort a balance, ADR 0002. `internal/app/fees.go` already violates the rule, and the `lint` job that carries this check does not block. (unverified) [2026-11]
- An applied migration is never modified again: a file is added at the next number. Why: staging and production only replay what `deploy.yml` passes them. (unverified) [2026-11]

## Forbidden
- `make reset-db` and `make migrate` with a `DATABASE_URL` that is not your local database. Why: `reset-db` destroys the schema without looking at the target; two days of QA data lost on staging on February 3, 2026. [2026-02]
- Running `deploy.yml` with `dry_run` set to false, or towards `production`. Why: owner's request, no known incident. [2026-11]
- Modifying an existing file of `migrations/`. Why: see the migrations rule. [2026-11]
