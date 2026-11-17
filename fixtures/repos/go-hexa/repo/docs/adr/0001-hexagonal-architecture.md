# ADR 0001 — Hexagonal architecture

Date: 2025-09-02. Status: accepted.

## Context
The first prototype mixed SQL and balance rules in the HTTP handlers. Testing a transfer required a database.

## Decision
Three layers, dependencies pointing inwards only:
- `internal/domain` depends on nothing: no use case, no adapter, no I/O.
- `internal/app` knows the domain and ports (interfaces), never an adapter nor a transport.
- `internal/adapters/*` implement the ports and do not know each other.

`cmd/ledgerd` is the only place that wires adapters together.

## Verification
`tools/archcheck` reads the imports and fails at the first forbidden dependency. It runs in CI, job `arch`, blocking.

## Consequence
A use case is tested with the memory adapter. Adding a transport touches neither the domain nor the use cases.
