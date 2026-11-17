# ADR 0001 — Three services, one contract

Date: 2024-06-10. Status: accepted. Updated on 2026-05-20 and on 2026-08-04.

## Context
The shop's monolith mixed orders, invoices and emails: correcting an invoice meant redeploying order taking.

## Decision
- Three services, `orders`, `billing` and `notifications`. Each is deployed on its own.
- A service knows of another only what `contracts/` describes: its events (`contracts/events/`) and the answers of its API (`contracts/api/`). The schemas are strict (`additionalProperties: false`): a field that leaves a service without being declared is an error.
- A service never imports another's code. In May 2024, `billing` imported the catalog of `orders` to recompute a total: the two services could no longer be deployed one without the other. What a service needs, it reads in the event or asks the API for.
- Common code is limited to `shared/` (the bus, the HTTP adapter) and to `tools/`. Neither knows a service.
- In tests and locally, the bus is in memory (`shared/bus.py`). In production, it is the platform team's broker, through its `comptoir_broker` client, which is not in this repository.

## Verification
- Each service that publishes or answers has its `test_contract.py`: it validates what really leaves the service against the schema, with `tools/schema.py`. Job `test` of the CI, blocking.
- Imports between services are reviewed by hand before each PR. *(Replaced on 2026-08-04, see below.)*

## Update of 2026-05-20
After the incident of 12 May (`docs/postmortems/2026-05-renamed-field.md`): a contract evolves only by addition. Nothing in it is renamed, nothing is removed from it, no type is changed. A field that has become useless stays published.

## Update of 2026-08-04
`tools/check_imports.py` now checks the imports between services, those of `shared/` and those of `tools/`. Job `boundaries` of the CI, blocking on every PR. The review by hand is no longer the check.
