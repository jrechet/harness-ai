# comptoir — instructions for agents

Mode: **delegation**. An agent receives a whole ticket and comes back with a PR; the CI jobs `test` and `boundaries` decide, this file explains.

## What this repo does
The back office of an online shop, in three services: `orders` takes orders, `billing` issues invoices, `notifications` writes to customers. They know each other only through `contracts/`. Decisions in `docs/adr/`, incidents in `docs/postmortems/`, operations in `docs/operations.md`. A service may have its own note: `services/billing/AGENTS.md`.

## What changes → what to run
| If you touch… | Run… | Enforced in CI by |
|---|---|---|
| a service | `python3 -m unittest discover -s services/<name> -t .` | job `test` |
| `contracts/`, `shared/` or `tools/` | `python3 -m unittest discover`, everything | job `test` |
| an import | `python3 tools/check_imports.py` | job `boundaries` |

## Rules
- What a service publishes or answers is declared in `contracts/`, and nothing else leaves it: the schemas are strict. Why: the contract is all another service is allowed to know (ADR 0001). Enforced by: `services/orders/test_contract.py` and `services/billing/test_contract.py`, with `tools/schema.py`. [2024-06]
- A contract change is additive: a field is added, nothing is renamed, nothing is removed, no type is changed. Why: `customer_email` renamed to `email` on 12 May 2026, 1,840 order confirmations never sent (`docs/postmortems/2026-05-renamed-field.md`). Enforced by: `services/orders/test_contract.py`. [2026-05]
- A contract field that another one replaces stays published and gets `"deprecated": true` in its schema; it is not removed. Why: consumers outside this repository read this annotation to plan their migration; agreed with them in September 2026. (unverified) [2026-09]
- Every contract change is recorded in `contracts/CHANGES.md`, one dated line per contract touched, most recent first. Why: consumers outside this repository follow this file, not our PRs; agreed with them in September 2026, written nowhere else. The file does not exist yet: no contract has changed since. (unverified) [2026-09]
- An event consumer is idempotent: the broker delivers "at least once", the same event comes back with the same `id`. Why: 212 invoices issued twice on 18 November 2025 (`docs/postmortems/2025-11-duplicate-invoices.md`). Enforced by: `shared/bus.py`, which delivers every event twice in all tests. [2025-11]
- A service never imports another service's code; what it needs, it reads in the event or asks the API for. Why: `billing` imported the catalog of `orders`, the two could no longer be deployed one without the other (ADR 0001). Enforced by: `tools/check_imports.py` (job `boundaries`). [2024-06]

## Forbidden
- Pointing `BROKER_URL` at preproduction or production from a workstation or an agent session. Why: a replay launched from a workstation on 9 January 2026 re-sent 3,100 invoice emails to customers (`docs/operations.md`). [2026-01]
- Weakening a guardrail to make a test pass: `deliveries=1` in a service's test, one more keyword tolerated by `tools/schema.py`, an exception in `tools/check_imports.py`. Why: each one carries a rule above; `.github/CODEOWNERS` has them reviewed by the platform team. [2025-11]
