# ledger — instructions for agents

Mode: **delegation**. An agent can receive a whole task and open a PR without intermediate review. What is mandatory here is enforced by the CI; this file explains, it does not guarantee.

## What this repo does
Ledger service (balances, transfers, fees). Decisions in `docs/adr/`, incidents in `docs/postmortems/`, environments and databases in `docs/operations.md`.

## What changes → what to run
| If you touch… | Run… | Enforced in CI by |
|---|---|---|
| Go | `go vet ./... && go test ./...` | job `test` (blocking) |
| an import between packages | `go run ./tools/archcheck` | job `arch` (blocking) |

The `lint` job runs but does not block (`continue-on-error`, inherited warnings): a green lint proves nothing.

## Rules
- `internal/domain` depends on nothing, `internal/app` only knows ports, the adapters do not know each other; only `cmd/ledgerd` wires. Why: ADR 0001, the prototype mixed SQL and balance rules in the handlers. Enforced by: `tools/archcheck` [2025-09]
- An amount is a `domain.Money` (`int64` in cents); no `float32`/`float64` in `internal/domain` nor `internal/app`, and the API only exposes `*_cents`. Why: ADR 0002, float rounding distorts a balance by one cent. (unverified: the `forbidigo` rule is in the `lint` job, non-blocking) [2025-09]. Already violated by `internal/app/fees.go` (`float64` for the fee): do not take it as a model.
- Every endpoint that changes a balance requires the `Idempotency-Key` header, and the key is looked up **inside** the transaction that writes, never before opening it. Why: incident of April 14, 2026, 37 accounts debited twice (`docs/postmortems/2026-04-double-debit.md`, ADR 0003). (unverified: only the tests of the transfer cover it; nothing checks a new endpoint) [2026-04]. `POST /accounts` does not apply the key: known exception, catch-up in the backlog, do not copy it.

## Forbidden
- Never touch a database that is not yours: no `DATABASE_URL` towards `ledger_staging` (shared with QA) nor `ledger_prod`, and never `make reset-db` nor `make migrate` on these databases. Why: on February 3, 2026, `make reset-db` run with the staging URL left in a terminal wiped two days of QA datasets. [2026-02]
- Never modify a migration of `migrations/` already applied: a file is added, next number. Why: staging and production have already played it; no known incident. [2026-11]
- Never run `.github/workflows/deploy.yml` with `dry_run` set to `false`. Why: without `dry_run`, the workflow applies the migrations and deploys; no known incident. [2026-11]
