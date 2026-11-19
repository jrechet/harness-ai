# ledger — instructions for agents

Mode: **delegation**. An agent can receive a whole task and open a PR without intermediate review. What is mandatory here is enforced by the CI; this file explains, it does not guarantee.

## What this repo does
A ledger service (Go, standard library, PostgreSQL in staging and production): open an account, read a balance, transfer money, quote a fee. Decisions are in `docs/adr/`, incidents in `docs/postmortems/`, operations in `docs/operations.md`.

## What changes → what to run
| If you touch… | Run… | Enforced in CI by |
|---|---|---|
| any Go code | `go test ./...` and `go vet ./...` | job `test` (blocks) |
| layers / imports (`internal/domain`, `internal/app`, `internal/adapters/*`) | `go run ./tools/archcheck` (`make arch`) | job `arch` (blocks) |
| amounts / money code | `golangci-lint run` (`make lint`) | nothing: the `lint` job does not block |
| `internal/adapters/postgres` | `make test-integration` (needs a migrated DB) | nothing: not run in CI |

## Rules
- Dependencies point inward: `internal/domain` imports nothing, `internal/app` knows only ports (never an adapter or a transport), adapters do not import each other. Only `cmd/ledgerd` wires them. Why: ADR 0001 — mixing SQL and balance rules in the handlers made a transfer untestable. Enforced by: `tools/archcheck` (CI job `arch`, blocks) [2025-09]
- Amounts are `int64` cents (`domain.Money`), never `float32`/`float64`, in `internal/domain` and `internal/app`; the API exposes `amount_cents`, never a decimal. Why: ADR 0002 — a float does not hold €0.10 exactly and a balance drifts by a cent. A `forbidigo` rule in `.golangci.yml` carries it, but the `lint` job is `continue-on-error`, so nothing blocks on it. (unverified) [2025-09]
- Every balance-changing endpoint requires the `Idempotency-Key` header and looks the key up **inside** the write transaction, not before opening it. Why: ADR 0003 / the April 2026 double-debit — a lookup before the transaction let two requests through and debited an account twice (37 accounts in three weeks). Nothing checks that a new write endpoint does this. (unverified) [2026-04]
- When a write endpoint replays an already-processed request, its response carries the `Idempotency-Replayed: true` header. Why: said by the team — the mobile app relies on it since 2026-06 to avoid showing a confirmation twice. Not yet done on `POST /transfers` (`internal/adapters/httpapi/server.go`, backlog): do not take that handler as the model. (unverified) [2026-06]

## Forbidden
- Never run `make migrate`, `make reset-db`, or `deploy/apply.sh` against a database that is not your own (a staging or production `DATABASE_URL`). Why: on 2026-02-03 `make reset-db` ran with the staging URL and dropped the schema shared with QA — two days of datasets lost. [2026-02]
- Never modify a migration already applied in staging or production; add a new numbered file in `migrations/`. Why: an applied migration is a fixed fact; editing it diverges environments (`docs/operations.md`). [2026-11]
- Never trigger `deploy.yml` without `dry_run`, and never run `deploy/apply.sh` or `deploy/plan.sh` yourself. Why: they apply migrations and roll staging/production; delivery to production is gated by a human approval. [2026-11]
