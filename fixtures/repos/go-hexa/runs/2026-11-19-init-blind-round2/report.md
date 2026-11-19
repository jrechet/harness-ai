Done. The repository is now instrumented at **level 1, Framed**.

## The map, updated

```
✓ 1 Framed     the agent knows the project, its rules and what it must never do   ← you are here
· 2 Looped     review remarks become rules, so the same mistake is not made twice
· 3 Verified   mandatory rules are enforced by tools, not just written down
· 4 Delegated  whole tasks go to the agent and come back clean
```

This run wrote a 24-line `AGENTS.md` (delegation mode) plus the Claude and Copilot stubs, from four owner answers and a read of the ADRs, the post-mortem and the CI. The repo moved from **0 None** to **1 Framed**, gate 5/5.

## Before and after
- **Level**: 0 → 1 (Framed).
- **Lines loaded per session**: 0 → 24 (`AGENTS.md`, the one file both Claude and Copilot land on).
- **Rules**: 0 → 4 rules + 3 forbidden items.

## Files created
| Path | Lines | What |
|---|---|---|
| `AGENTS.md` | 24 | the single source: mode, one command mapping, 4 rules, 3 forbidden |
| `CLAUDE.md` | 1 | `@AGENTS.md` stub |
| `.github/copilot-instructions.md` | 1 | points Copilot at `AGENTS.md` |

No Cursor stub (owner uses Claude Code + Copilot only). No existing instruction file was present, so nothing was **removed**.

## Secrets
None found. `secrets.DATABASE_URL` in `deploy.yml` is a GitHub Actions secret reference (correct); the other grep hits are Go stdlib. No Forbidden line needed on this account — but "never touch a database that isn't yours" covers the `DATABASE_URL` blast radius anyway.

## Rules written
| Rule | Status | Date |
|---|---|---|
| Amounts are `int64` cents via `domain.Money`, never float; API exposes `amount_cents` | **(unverified)** — a `forbidigo` rule exists but the CI `lint` job is `continue-on-error`, so it does **not** block a merge | 2025-09 |
| A write endpoint requires `Idempotency-Key`, looked up **inside** the write transaction | **(unverified)** — the unique index on `transfers.idempotency_key` is the last net; nothing checks a *new* endpoint | 2026-04 |
| A replayed write answers with `Idempotency-Replayed: true` | **(unverified)** — said by the team; mobile app relies on it since 2026-06 | 2026-06 |
| Keep layer dependencies (domain → nothing, app → ports, adapters isolated) | **Enforced by** `tools/archcheck`, CI job `arch` (blocks) | 2025-09 |

Forbidden (all owner-stated): touch a database that isn't yours · modify an already-applied migration · start `deploy.yml` without `dry_run`.

## Commands
- **Confirmed in CI, run as-is** (no line needed): `go test ./...`, `go vet ./...` (job `test`); `go run ./tools/archcheck` (job `arch`). Both block.
- **In the file** (non-obvious): `make test-integration` — needs a migrated DB, does **not** run in CI, run by hand before a prod release touching `internal/adapters/postgres`.
- **Could not run myself**: the Go toolchain isn't installed in this environment, so I did not execute the test/vet/arch/lint commands — they are what CI runs, not independently verified here.
- **`harness commands` candidates I did not keep**: `make test`/`make lint` (plain wrappers over `go test`/`golangci-lint`, nothing surprising); `deploy/apply.sh` and `deploy/plan.sh` (delivery scripts — folded into the Forbidden `deploy.yml` line, never run).

## Questions for the owner
1. **Money rule is unverified by design** — the `lint` job is `continue-on-error`, so nothing blocks a float in money code at merge. The owner confirmed this is known debt. *Default: leave as-is; paying the lint debt and making the job blocking is a level-3 step.* Worth a decision later.
2. **Stale README** — `make e2e` was removed a year ago (owner confirmed) but the README's Getting Started still lists it. I did **not** fix the README (out of scope for init). *Default: fix it in a small separate PR.*

## What comes next (not done)
Level 1 is a place you can stay — for a four-dev team reviewing PRs at the end, it is often enough. **Level 2, Looped** would add "review remarks become rules" (a `Maintaining this file` section + the `rule:` convention) and needs a review habit over a few weeks. Two of your strongest rules are currently `(unverified)` debts; **level 3, Verified** is where the money rule and the "new write endpoint" checks would get real guardrails. You decide how far to go (`harness target <n>`), and `harness-step` leads it — I've stopped here, as this step asks.