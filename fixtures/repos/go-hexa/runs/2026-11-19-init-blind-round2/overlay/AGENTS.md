# ledger — instructions for agents

Mode: **delegation**. An agent can receive a whole task and open a PR without intermediate review. What is mandatory here is enforced by the CI; this file explains, it does not guarantee. In CI the `test` (go vet + go test) and `arch` (archcheck) jobs block a merge; the `lint` job runs but does not block (inherited-warning debt not yet paid off).

## What this repo does
Ledger service: open an account, read a balance, transfer money, quote a transfer fee. Go + PostgreSQL. Architecture decisions live in `docs/adr/`, incidents in `docs/postmortems/`, operational rules in `docs/operations.md`.

## What changes → what to run
| If you touch… | Run… | Enforced in CI by |
|---|---|---|
| `internal/adapters/postgres` | `make test-integration` (needs a migrated database) before a production release | nothing — integration tests do not run in CI |

## Rules
- Amounts are `int64` cents via `domain.Money`; never `float32`/`float64` for money, and the API exposes `amount_cents`, never a decimal. Why: ADR 0002 — floats accumulate rounding errors until a balance is off by a cent. A `forbidigo` rule in `.golangci.yml` carries it, but the CI `lint` job is non-blocking, so nothing stops a float at merge. (unverified) [2025-09]
- A write endpoint (one that changes a balance) requires the `Idempotency-Key` header, and looks the key up **inside** the write transaction, never before opening it. Why: the 2026-04 double-debit — an account debited twice by €480, 37 accounts in three weeks, because the lookup happened before the transaction opened. The unique index on `transfers.idempotency_key` (`migrations/0003`) is the last net; nothing checks that a *new* endpoint requires the key. (unverified) [2026-04]
- A replayed write (a request already processed) answers with the `Idempotency-Replayed: true` header. Why: said by the team — the mobile app relies on it since 2026-06 to avoid showing a confirmation twice; every new write endpoint must set it (`POST /transfers` does not yet, it is in the backlog). (unverified) [2026-06]
- Keep the layer dependencies: `internal/domain` depends on nothing, `internal/app` knows ports and never an adapter or a transport, adapters do not know each other. Why: ADR 0001. Enforced by: `tools/archcheck` (CI job `arch`, blocks). [2025-09]

## Forbidden
- Never touch a database that is not your own: no `make migrate`, `make reset-db` or `psql` against staging or production (staging is shared with the QA team's datasets). Why: `make reset-db` drops the whole schema — run with the staging URL left in a terminal on 2026-02-03, it cost two days of QA data. [2026-02]
- Never modify a migration already applied in staging or production; add a new numbered file instead. Why: an applied migration is a fixed fact, changing it diverges the environments (said by the team, `docs/operations.md`). [2026-11]
- Never start `deploy.yml` without `dry_run`; deploys go only through that workflow, and production needs an approval. Why: it applies migrations and rolls the service against a shared environment. [2026-11]
