# Incident of 18 November 2025 — 212 invoices issued twice

## What happened
`billing` was redeployed at 14:05, in the middle of a sale. The service stopped after handling 212 `order.created` events, but before the broker had received their acknowledgements. On restart, the broker delivered them again. `billing` issued a second invoice for each of the 212 orders, under a new number, and `notifications` sent two invoice emails.

## Cause
The broker delivers "at least once". `billing` assumed "exactly once": nothing told it that an order was already invoiced.

## Detection
A customer replied to the second email, forty minutes later. Nothing saw it on our side.

## Fixes
- `billing`: one invoice per order, and the number is taken only when the invoice is written (`services/billing/ledger.py`, guarded by `services/billing/test_ledger.py`). Invoice numbering must be continuous: it is a legal obligation.
- `notifications`: keeps the `id`s of the events already handled.
- The test bus delivers every event twice (`shared/bus.py`). Double delivery is no longer a case one must remember to test: it is the default case.
- Decision written down: `docs/adr/0002-at-least-once-delivery.md`.
- Accounting issued 212 credit notes. The 212 extra numbers stay in the sequence, declared to the statutory auditor.

## What remains open
Nothing.
