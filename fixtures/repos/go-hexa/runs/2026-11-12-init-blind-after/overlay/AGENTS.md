# ledger — instructions for agents

Mode: **delegation**. An agent can receive a whole task and open a PR without intermediate review. What is mandatory here is enforced by the CI; this file explains, it does not guarantee.

## What this repo does
Ledger service (balances, transfers, fees). Decisions in `docs/adr/`, incidents in `docs/postmortems/`, databases and deployment in `docs/operations.md`.

## What changes → what to run
| If you touch… | Run… | Enforced in CI by |
|---|---|---|
| Go code | `make test` and `go vet ./...` | job `test`, blocking |
| imports between layers | `make arch` | job `arch`, blocking |

## Rules
- Every write endpoint requires `Idempotency-Key`, and the use case looks the key up **inside** the transaction that writes, never before opening it. Why: double debit, 37 accounts affected (`docs/postmortems/2026-04-double-debit.md`, ADR 0003). Enforced by: nothing for a new endpoint, only the tests of `internal/app` cover the transfer (unverified) [2026-04]
- When an endpoint replays a request already processed, the response carries the `Idempotency-Replayed: true` header; every new write endpoint sets it. Why: the mobile app uses it to avoid showing the confirmation twice (told by the team). `POST /transfers` does not do it yet (backlog): do not take it as a model. (unverified) [2026-06]
- No `float32`/`float64` for an amount in `internal/domain` nor `internal/app`: `int64` in cents (`domain.Money`). Why: rounding errors that distort a balance (ADR 0002). The repository already violates it: `internal/app/fees.go` computes the fee in `float64`, known debt, do not copy it. (unverified: the `forbidigo` rule runs in the `lint` job, which does not block) [2025-09]
- `internal/domain` depends on nothing, `internal/app` only knows ports, the adapters do not know each other; only `cmd/ledgerd` wires. Why: ADR 0001. Enforced by: `tools/archcheck` (job `arch`) [2025-09]

## Forbidden
- Touching a database that is not your own: never `make reset-db` nor `make migrate` with a staging or production `DATABASE_URL`. Why: `reset-db` does not look at the target; on February 3, 2026, two days of QA datasets lost on staging (`docs/operations.md`). [2026-02]
- Modifying a migration already applied: a `migrations/` file is added, next number. Why: team decision (`docs/operations.md`), no known incident. [2026-11]
- Running `deploy.yml` without `dry_run`. Why: it applies the migrations and deploys to staging (shared with QA) or production; team decision, no known incident. [2026-11]
