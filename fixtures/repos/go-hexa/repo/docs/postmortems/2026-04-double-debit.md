# Incident of April 14, 2026 — an account debited twice

## What happened
A mobile client resent a transfer after a network timeout. The two requests arrived 40 ms apart on two instances. Each one checked that the idempotency key did not exist, then opened its transaction and wrote. The account was debited twice by €480.00.

## Cause
The key lookup happened **before** the transaction was opened. Between the read and the write, nothing prevented a second request from getting through. No database constraint caught the duplicate.

## Detection
Reported by the customer the next day. Nothing saw it on our side: 37 accounts affected in three weeks, found by query.

## Fixes
- The key lookup moved into the write transaction (`internal/app/service.go`).
- Unique index on `transfers.idempotency_key` (`migrations/0003`).
- Decision written down: `docs/adr/0003-idempotency-key.md`.

## What remains open
A new write endpoint can still forget the key: the review is the only check.
