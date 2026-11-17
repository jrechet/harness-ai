# deskly — instructions for agents

Mode: **delegation**. An agent receives a whole ticket and comes back with a PR; the CI decides, this file explains.

## What this repo does
Internal support: tickets, statuses, an API and a web page. The ticket model lives once, in `packages/shared`. Decisions in `docs/adr/`, incidents in `docs/postmortems/`.

## What changes → what to run
| If you touch… | Run… | Enforced in CI by |
|---|---|---|
| `packages/shared` | the three `npm run test:*` and the three `npm run typecheck:*`, **web included** | jobs `shared` and `api`; **not** the `web` job |
| `apps/api` | `npm run test:api` and `npm run typecheck:api` | job `api` |
| `apps/web` | `npm run test:web` and `npm run typecheck:web` | job `web` |
| an import between workspaces | `npm run check:boundaries` | job `boundaries`, on every PR |

## Rules
- A change in `packages/shared` is validated with the web's tests and types run by hand. Why: the `web` job does not trigger on that folder and nothing replays everything; ticket list empty for 2 h 40 on June 9, 2026 (`docs/postmortems/2026-06-unknown-status.md`). (unverified) [2026-06]
- A change to the shared model bumps the version in `packages/shared/package.json`. Why: `deskly-infra` pins that version and only redeploys the storage if it changes; forgotten twice, the last time in September 2026. Said by the team, written nowhere else. (unverified) [2026-09]
- An app never imports another app, a package never an app, and a package is imported through its public entry. Why: ADR 0001. Enforced by: `tools/check-boundaries.mjs`, job `boundaries`. [2025-11]
- A status or a transition is declared in `packages/shared`, never in an app. Why: ADR 0001, no known incident. Enforced by: `packages/shared/src/ticket.test.ts` for the transitions only. [2025-11]

## Forbidden
- Adding a database driver or a runtime dependency. Why: the production storage lives in `deskly-infra`; `TicketStore` is in-memory on purpose. [2025-11]
- Changing `deskly-infra` from a task of this repository. Why: the owner's request, no known incident. [2026-11]
