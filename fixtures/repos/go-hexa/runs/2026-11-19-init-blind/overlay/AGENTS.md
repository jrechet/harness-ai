# ledger — instructions for agents

Mode: **delegation**. An agent can receive a whole task and open a PR without intermediate review. What is mandatory here is enforced by the CI; this file explains, it does not guarantee.

## What this repo does
A ledger service (Go, PostgreSQL): open an account, read a balance, transfer money, quote a fee. Decisions are in `docs/adr/`, incidents in `docs/postmortems/`, operations in `docs/operations.md`.

## What changes → what to run
| If you touch… | Run… | Enforced in CI by |
|---|---|---|
| any Go code | `make test` (`go vet` + `go test ./...`) | `test` job (blocks) |
| a layer's imports (`internal/domain`, `internal/app`, `internal/adapters/*`) | `make arch` | `arch` job (blocks) |
| `internal/adapters/postgres` | `make test-integration` (needs a migrated DB) | nothing — not run in CI; run it by hand before a release that touches this adapter |

## Rules
- A write endpoint requires the `Idempotency-Key` header and looks the key up **inside** the write transaction, never before opening it. Why: a pre-transaction lookup debited an account twice (€480) in April 2026; the unique index on `transfers.idempotency_key` (`migrations/0003`) is the last net, not the first. Nothing checks a new endpoint has it — review only. (unverified) [2026-04]
- A replay of an already-processed write returns the first result and sets the `Idempotency-Replayed: true` response header; every new write endpoint must set it. Why: the mobile app relies on it (since 2026-06) to not show a confirmation twice; nothing checks it — review only. Not done yet on `POST /transfers` (`internal/adapters/httpapi/server.go`, in the backlog): do not copy that handler as the model. (unverified) [2026-06]
- In `internal/domain` and `internal/app` an amount is a `domain.Money` (`int64` cents + currency); no `float32`/`float64`, and the API exposes `amount_cents`. Why: a float cannot hold €0.10 exactly and balances drift (ADR 0002). A `forbidigo` rule in `.golangci.yml` carries it, but the `lint` job is `continue-on-error` and does not block. (unverified) [2025-09]

## Forbidden
- Never touch a database that is not your own. Why: on 2026-02-03 `make reset-db` run against staging dropped the shared schema and lost two days of QA datasets; `reset-db`/`migrate` do not check which database they hit, and staging belongs to QA. [2026-02]
- Never modify a migration already applied in staging or production: add a new numbered file in `migrations/`. Why: an applied migration is immutable, changing one diverges the environments. [2026-02]
- Never deploy from your machine: deployment goes only through the `deploy.yml` workflow, and never with `dry_run` off outside an approved production release. Why: `deploy/apply.sh` runs migrations against the real database. [2026-11]
