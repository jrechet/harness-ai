# ADR 0002 — "At least once" delivery

Date: 2025-11-25. Status: accepted. Follows `docs/postmortems/2025-11-duplicate-invoices.md`.

## Context
The broker guarantees that an event arrives at least once, not that it arrives only once. After a consumer restarts or an acknowledgement is lost, the same event is delivered again, with the same `id`.

## Decision
- Every consumer is idempotent: handling the same event twice leaves the same state as handling it once.
- `billing` relies on its natural key, one invoice per order (`Ledger.issue`). `notifications` keeps the `id`s of the events already handled.
- The `id` of an event is stable: the same fact published twice carries the same `id`.

## Verification
The test bus delivers every event **twice** (`InMemoryBus`, `deliveries=2` by default, `shared/bus.py`). Any test that goes through the bus therefore replays a double delivery: a consumer that is not idempotent fails its own tests, in the `test` job of the CI. Only the tests of the bus itself set it to one delivery.
