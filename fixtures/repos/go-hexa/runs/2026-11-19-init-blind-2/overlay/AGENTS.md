# ledger — instructions for agents

Mode: **delegation**. An agent can receive a whole task and open a PR without intermediate review. What is mandatory here is enforced by the CI; this file explains, it does not guarantee.

## What this repo does
A Go ledger service: open accounts, read balances, transfer money, quote fees. The decisions are in `docs/adr/`, the incidents in `docs/postmortems/`, the operations in `docs/operations.md` — read them before changing behaviour.

## What changes → what to run
| If you touch… | Run… | Enforced in CI by |
|---|---|---|
| any Go code | `go test ./...` | `test` job (blocks) |
| imports / layer boundaries in `internal/` | `go run ./tools/archcheck` | `arch` job (blocks) |

`golangci-lint` runs in CI but **does not block** (`continue-on-error`, inherited-warning debt): do not rely on it to catch a mistake.

## Rules
- A replayed write response carries the `Idempotency-Replayed: true` header. Why: the mobile app relies on it since 2026-06 to not show a confirmation twice (said by the team; in no document). Nothing checks it, and `POST /transfers` does not emit it yet (backlog) — do not take transfers as the model. (unverified) [2026-06]
- Every balance-changing endpoint requires the `Idempotency-Key`, looked up **inside** the write transaction, never before. Why: the double-debit incident, `docs/postmortems/2026-04-double-debit.md` and ADR 0003. Only review catches a new endpoint that forgets it. (unverified) [2026-04]
- An amount is an `int64` in cents, no `float32`/`float64` in `internal/domain` or `internal/app`; the API exposes `amount_cents`, never a decimal. Why: float rounding errors on money, ADR 0002. A `forbidigo` rule exists but the non-blocking `lint` job does not enforce it. (unverified) [2025-09]

## Forbidden
- Touch a database that is not your own. Staging is shared with the QA team; `make reset-db`/`make migrate` do not check which database `DATABASE_URL` points to. Why: on 2026-02-03 `make reset-db` with the staging URL wiped two days of QA data (`docs/operations.md`). [2026-02]
- Modify a migration already applied in staging or production. Add a new numbered file instead. Why: applied migrations are immutable, said by the team (`docs/operations.md`). [2026-11]
- Run `deploy.yml` without `dry_run`, or run `deploy/apply.sh`/`deploy/plan.sh` from a local machine. Why: deploys are manual and production needs an approval, said by the team (`docs/operations.md`). [2026-11]
