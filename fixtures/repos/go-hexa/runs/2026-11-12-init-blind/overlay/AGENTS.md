# ledger — instructions for agents

Mode: **delegation**. An agent can receive a whole task and open a PR without intermediate review. What is mandatory here is enforced by the CI; this file explains, it does not guarantee.

## What this repo does
Ledger service (balances, transfers, fees). The decisions are in `docs/adr/`, the incidents in `docs/postmortems/`, the databases and deployment in `docs/operations.md`.

## What changes → what to run
| If you touch… | Run… | Enforced in CI by |
|---|---|---|
| Go code | `go vet ./... && go test ./...` | job `test` (blocks) |
| imports between `domain`, `app`, `adapters` | `make arch` | job `arch` (blocks) |
| `internal/adapters/postgres` | nothing run here: its integration tests need a database of your own | nothing, outside CI |

The `lint` job (golangci-lint) runs but does not block (`continue-on-error`): a rule "enforced by the lint" is not.

## Rules
- Every endpoint that changes a balance requires the `Idempotency-Key` header; the use case looks the key up **inside** the write transaction; replaying the same request returns the first result, the same key with another request answers 409. Why: incident of April 14, 2026, 37 accounts debited twice (`docs/postmortems/2026-04-double-debit.md`, ADR 0003). `POST /accounts` does not apply it (in the backlog): it is not a model. (unverified) [2026-04]
- Every new write endpoint answers with the `Idempotency-Replayed: true` header when it replays a request already processed. Why: the mobile app uses it to avoid showing the confirmation twice. `POST /transfers` does not do it yet (in the backlog): do not copy it on this point. (unverified) [2026-06]
- An amount is a `domain.Money` in cents (`int64`), never a `float32`/`float64` in `internal/domain` nor `internal/app`; the API exposes `amount_cents`. Why: rounding errors that distort a balance by one cent (ADR 0002). `internal/app/fees.go` already uses `float64`: it is not a model. (unverified: the `forbidigo` rule is in the lint, which does not block) [2025-09]
- `domain` depends on nothing, `app` only knows ports, the adapters do not know each other; only `cmd/ledgerd` wires them together. Why: the prototype mixed SQL and rules in the handlers (ADR 0001). Enforced by: `tools/archcheck` [2025-09]

## Forbidden
- Never run `make reset-db`, `make migrate` nor `psql` with a `DATABASE_URL` that is not your own local database. Check the variable first. Why: on February 3, 2026, `reset-db` run with the staging URL left in a terminal wiped two days of QA datasets; the target does not look at which database it empties. [2026-02]
- Never modify an existing file of `migrations/`: an applied migration no longer changes, the next number is added. Why: staging and production have already played it (`docs/operations.md`). [2026-11]
- Never run `deploy.yml` with `dry_run` set to `false`. Why: it applies the migrations then deploys to staging or production. [2026-11]
