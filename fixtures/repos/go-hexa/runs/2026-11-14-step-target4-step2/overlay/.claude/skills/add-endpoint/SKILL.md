---
name: add-endpoint
description: Add an HTTP endpoint to ledger from a use case, from the handler down to the test. Use when a ticket asks for a new route (read or write) in internal/adapters/httpapi.
---

# Add an endpoint

The ticket gives the use case. This contract says in what order it is laid and what makes it done. The general rules are in `AGENTS.md`; here, only what is specific to this task.

## Before writing: stop and ask if…
- the ticket does not fix the shape of the API (method, path, body, response, error codes): a new endpoint **is** an API contract change;
- a table or a column is needed: that is a migration;
- the ticket is ambiguous about an amount, a currency or a rounding.

## Steps, from the inside outwards (ADR 0001)
1. **Domain** (`internal/domain`), if a business rule is new: a pure function, tested in `*_test.go` next to it. No import outside the standard library.
2. **Use case** (`internal/app/service.go`): a method of `Service` that only talks to the ports of `ports.go`. An amount is a `domain.Money` built with `domain.NewMoney`; no float (ADR 0002). `internal/app/fees.go` already violates this rule: do not copy it.
3. **If the endpoint changes a balance** (ADR 0003, postmortem 2026-04):
   - the command carries `IdempotencyKey`; empty → `ErrMissingIdempotencyKey`;
   - the key lookup happens **inside** the `uow.Do` that writes, never before: take `Transfer` as a model, not `OpenAccount`;
   - replaying the same request returns the first result, with the `Idempotency-Replayed: true` header; same key, other request → `ErrIdempotencyConflict` (409).
   - Never add a route to `withoutIdempotencyKey` in `idempotency_guard_test.go`: that needs the owner's agreement.
4. **New or extended port**: implement it in `internal/adapters/memory` **and** `internal/adapters/postgres`. The adapters do not import each other.
5. **Handler** (`internal/adapters/httpapi/server.go`): add the route to `routes()` (it is the list the guardrail walks), decode the body, call the use case. Amounts are exposed as `amount_cents` (integer). An error becomes an HTTP code **only** in `writeDomainError`: add the case there if the error is new.

## Expected tests
- Use case: `internal/app/service_test.go`, with the memory adapter, no database.
- Handler: `internal/adapters/httpapi/server_test.go`, with `newServer(t)`: the nominal case and each error added to `writeDomainError`.
- Write endpoint: without a key → 400 (checked automatically by `TestWriteRoutesRequireIdempotencyKey` as soon as the route is in `routes()`), replay → same result and `Idempotency-Replayed: true`, same key and other body → 409.
- If `internal/adapters/postgres` changed: `make test-integration` on your local database (nothing runs it in CI). If you could not run it, the PR says so.

## Done when
- `make test` and `make arch` pass;
- the tests above exist for what was added;
- the PR says why in two lines, and lists what was not checked (postgres integration, choices decided without the ticket).
