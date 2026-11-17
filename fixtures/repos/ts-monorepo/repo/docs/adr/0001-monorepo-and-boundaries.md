# ADR 0001 — One monorepo, boundaries

Date: 2025-11-12. Status: accepted.

## Decision
- The ticket model lives once, in `packages/shared`. Neither the API nor the web keeps its own list of statuses or transitions.
- An app never imports another app. A package never imports an app. A package is imported through its public entry, never through an internal file.
- The production storage is not in this repository: it lives in `deskly-infra`, which implements the three methods of `TicketStore`. No database driver here.

## Verification
`tools/check-boundaries.mjs` fails at the first boundary crossed. `boundaries` job of the CI, blocking, run on every PR.
