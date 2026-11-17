# Incident of 12 May 2026 — 1,840 order confirmations never sent

## What happened
A cleanup PR renamed `customer_email` to `email` in the `order.created` event. It touched the schema `contracts/events/order.created.json`, the `orders` service and the `billing` service. All the tests were green, the CI too.

`notifications` read `customer_email`. Its tests build their events by hand, with the old name: they stayed green. In production, every `order.created` raised a `KeyError` in `notifications` for 6 h 20. 1,840 order confirmations never went out.

The next morning, the accounting export (`comptoir-export`, another team) failed for the same reason.

## Cause
The contract changed in a way its readers did not support, and nothing saw it. The schema and the provider changed in the same PR: `services/orders/test_contract.py` compares one to the other, it stayed green.

## Detection
Support, through the customers who were waiting for their confirmation.

## Fixes
- Renaming reverted the same day: `customer_email` came back into the event.
- The 1,840 confirmations were sent by hand from the orders.
- Rule written down: a contract change is additive (`docs/adr/0001-three-services-one-contract.md`, update of 20 May).

## What remains open
`test_contract.py` proves that `orders` publishes what the schema says. It does not prove that the schema still says what its readers expect: when the schema and the provider change together, it stays green.

No test replays a consumer against what the provider really publishes. No check compares a schema to its previous version. The tests of `billing` and of `notifications` make their events by hand, without validating them against `contracts/`. The consumers outside this repository are not tested here at all.

As long as this stays true, review is the only check of the rule.
