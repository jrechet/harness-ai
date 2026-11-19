Setup complete. Here is the report.

---

## Harness init — report

### The map, updated
```
✓ 1 Framed     the agent knows the project, its rules and what it must never do   ← you are here
· 2 Looped     review remarks become rules, so the same mistake is not made twice
· 3 Verified   mandatory rules are enforced by tools, not just written down
· 4 Delegated  whole tasks go to the agent and come back clean
```
This run took the repo from **level 0 (no instructions)** to **level 1, Framed**: a 29-line `AGENTS.md` in delegation mode, with three rules, a Forbidden section, and the Claude/Copilot stubs. Gate: **5/5 checks, no dangling reference.**

### Before and after
| | Before | After |
|---|---|---|
| Level | 0 — None | 1 — Framed |
| Lines loaded per session | 0 | 29 (`AGENTS.md`, via `CLAUDE.md`) |
| Rules | 0 | 3 rules + 3 Forbidden items |

### Files created
- `AGENTS.md` — 29 lines (under the 60 budget).
- `CLAUDE.md` — 1 line (`@AGENTS.md` stub).
- `.github/copilot-instructions.md` — 1 line (pointer to AGENTS.md).

No Cursor or Codex stub: the owner uses only Claude Code and Copilot. No existing instruction file was found, so nothing was overwritten or removed.

### Secrets
None found. `DATABASE_URL` is the only sensitive value referenced; it comes from the environment and GitHub Actions `secrets`, never hardcoded. Nothing to regenerate.

### Rules written
1. **Replayed write responses carry `Idempotency-Replayed: true`** — status `(unverified)`, `[2026-06]`. The one fact written in no file: said by the team, relied on by the mobile app since June 2026. Noted that `POST /transfers` doesn't emit it yet (backlog) so the agent won't copy it as the model.
2. **Balance-changing endpoints require `Idempotency-Key`, looked up inside the write transaction** — `(unverified)`, `[2026-04]`. Born of the April 2026 double-debit incident; nothing automated checks it (review only).
3. **Amounts are `int64` cents, no float in domain/app** — `(unverified)`, `[2025-09]`. ADR 0002. A `forbidigo` rule exists but the `lint` job is `continue-on-error`, so CI does **not** enforce it — written as unverified despite the ADR's claim to the contrary.

**Forbidden** (all from the owner): touch a database that isn't yours (`[2026-02]`, the reset-db incident); modify an already-applied migration (`[2026-11]`); run `deploy.yml` without `dry_run` or the deploy scripts locally (`[2026-11]`).

No rule earned an `Enforced by:` line. The two blocking guardrails (`go test`, `archcheck`) are captured in the "what changes → what to run" table instead, since they map to actions rather than to one of these rules.

### Commands
- **Confirmed by reading, not run:** the toolchain (`go`, `golangci-lint`, `psql`) is **not installed in this environment**, so I could not execute `go test ./...`, `go run ./tools/archcheck`, or `make *`. They are taken from the CI workflow, which runs them as-is, but are **not confirmed by execution**.
- **`harness commands` candidates I did not keep:** `make test` / `make lint` — thin wrappers over `go test ./...`, which is what CI runs directly and what an agent guesses anyway (no surprise, no line). `deploy/apply.sh` / `deploy/plan.sh` — delivery commands; they became a Forbidden line, not a table row.

### Questions for the owner
1. **`make e2e` doesn't exist.** `README.md:14` advertises `make e2e`, but the Makefile has no such target. Is it planned, renamed, or stale doc? *Default: leave the README to you; I didn't put e2e in AGENTS.md.*
2. **Lint debt.** The `lint` job stays non-blocking (you confirmed), so the "no float for amounts" rule rides on review alone. When the inherited warnings are paid down, dropping `continue-on-error` would turn rule 3 into an enforced one — worth tracking.

### What comes next (not done)
Level 1 is a place you can stay. Moving to **level 2, Looped** would add "review remarks become rules" — a `Maintaining this file` section and the `rule:` review convention — but it only pays off with a few weeks of real reviews feeding it; there's nothing to gain by adding the text before the habit exists. You decide whether to go there (`harness target 2`), and the `harness-step` skill leads it. I stopped at step 1, as asked.