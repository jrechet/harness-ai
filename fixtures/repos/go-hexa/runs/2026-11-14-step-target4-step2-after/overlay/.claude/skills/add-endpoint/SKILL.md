---
name: add-endpoint
description: Contract of the delegated task "add an HTTP endpoint from a use case", from the domain to the handler and its tests, up to the PR. Use when a ticket asks for a new route of the ledger API (read or write), even if it does not name this contract.
---

# Add an endpoint, from the use case to the test

You receive the whole ticket and come back with a PR. Nobody reviews along the way: this contract says what is expected, the CI (`test`, `arch`, `migrations`) decides. Sources: `docs/adr/0001` (layers), `0002` (cents), `0003` (idempotency), `docs/postmortems/2026-04-double-debit.md`, `docs/operations.md`.

## Before starting
- The route is **new**: that is the normal path, go all the way. If the ticket renames, removes or changes the type of an existing route or field, or if it is ambiguous about an amount or a rounding: stop and ask the question (AGENTS.md, "Working process").
- Decide whether the route **changes a balance** (debit, credit, fee, cancellation…). If so, the whole "Write" part below applies, without exception.

## Steps
1. **Domain** (`internal/domain`), only if the ticket brings a business rule: pure function, no dependency, amounts in `domain.Money` (integer in cents), typed errors in `errors.go`. Unit test next to it.
2. **Use case** (`internal/app/service.go`): a method on `Service` and, if there are inputs, a `<Name>Command`. It only knows the ports of `ports.go`. Amounts come in as `int64` cents and go through `domain.NewMoney`. No `float32`/`float64`: `internal/app/fees.go` already violates the rule, do not take it as a model.
3. **Ports and adapters**, only if a new storage is needed: the interface in `ports.go`, then its implementation in `internal/adapters/memory` **and** `internal/adapters/postgres`. An adapter never imports another adapter.
4. **Migration**, only if the schema changes: a new file `migrations/NNNN_<object>.sql` at the next number, idempotent (`IF NOT EXISTS`). Never a modification of an existing file. A migration that deletes or rewrites data: stop and ask.
5. **Handler** (`internal/adapters/httpapi/server.go`): add the route in `routes()`, the single list. The handler decodes, calls the use case, encodes; no business rule. Amounts go out as integer `amount_cents` / `*_cents`. A new error becomes an HTTP code in `writeDomainError`, nowhere else.
6. **Wiring**: `cmd/ledgerd` only if a new adapter is to be plugged in.

## Write: route that changes a balance
- Require the `Idempotency-Key` header: missing → `app.ErrMissingIdempotencyKey` (400 `idempotency_key_required`). The guardrail `idempotency_guard_test.go` checks it on every non-GET route.
- Look the key up **inside** the write transaction, within `uow.Do`, never before opening it: that is what debited 37 accounts twice in April 2026. Model: `Service.Transfer`.
- Same key, same request → return the first result, without rewriting. Same key, other request → `app.ErrIdempotencyConflict` (409).
- A replayed response carries `Idempotency-Replayed: true`: the mobile app uses it to avoid showing two confirmations. The use case tells the handler that it is a replay. (`POST /transfers` does not do it yet: do not fix it in this PR, report it.)
- If the key is stored in a new table: unique index on it in the migration, the last safety net (ADR 0003).
- **Never** add an entry to `withoutIdempotencyKey`: it needs the owner's agreement. `POST /accounts` is the only exemption, it is not a model. If the ticket asks for a write without a key, stop and ask.

## Expected tests
- `internal/app/service_test.go`, with the memory adapter: the nominal case, each domain error, and for a write: missing key, replay (a single effect on the balance), conflict.
- `internal/adapters/httpapi/server_test.go`: HTTP codes, body in cents, and for a write the replay with the `Idempotency-Replayed: true` header.
- If the postgres adapter changed: a test in `store_integration_test.go` and `make test-integration` on **your** local database. These tests do not run in CI and the driver is not in `go.mod` yet: if you cannot run them, write it in the PR.

## Checks before the PR
```
go vet ./... && go test ./...
go run ./tools/archcheck
go run ./tools/migrationcheck -base origin/main   # if migrations/ changed
```

## Never, even if the ticket seems to ask for it
- `make migrate` or `make reset-db` anywhere other than on your local database (`tools/localdb` refuses anyway).
- Modifying an existing migration.
- Running `deploy.yml`, let alone without `dry_run` or towards `production`.

## Done when
- `make test` and `make arch` pass (and `migrations` if the schema changes).
- A test covers the new route; for a write, the replay and the conflict are tested.
- The PR says why in two lines, then: route added, write or read, migration or not, and what could not be checked (postgres integration, key lookup inside the transaction, left to the review).
- A red `lint` does not block (inherited debt); a red CI caused by your diff gets fixed, another one gets reported.
