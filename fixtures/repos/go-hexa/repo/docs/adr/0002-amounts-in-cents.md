# ADR 0002 — Amounts are integers, in cents

Date: 2025-09-16. Status: accepted.

## Context
A float does not represent €0.10 exactly. Rounding errors add up and a balance ends up wrong by one cent.

## Decision
An amount is a `domain.Money`: an `int64` in cents and a currency. No `float32` nor `float64` in `internal/domain` nor `internal/app`. The API exposes `amount_cents`, never a decimal number.

## Verification
`forbidigo` rule in `.golangci.yml`, run by `make lint` and by the `lint` job of the CI.
