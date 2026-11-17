# ADR 0003 — Idempotency key on writes

Date: 2026-04-21. Status: accepted. Follows `docs/postmortems/2026-04-double-debit.md`.

## Decision
Every endpoint that changes a balance requires the `Idempotency-Key` header. The use case looks the key up **inside the transaction** that writes, not before opening it. Replaying the same request returns the first result; the same key with another request answers 409.

The database carries a unique index on the key (`migrations/0003`), the last safety net.

## Scope
`POST /transfers` applies it. `POST /accounts` predates the decision and does not apply it: opening an empty account twice costs nobody anything, the catch-up is in the backlog.

## Verification
The tests of `internal/app` cover the transfer. Nothing verifies that a new write endpoint requires the key.
