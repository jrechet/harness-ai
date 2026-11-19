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
This run took the repo from **level 0 (no instructions)** to **level 1, Framed**: a 24-line `AGENTS.md` in delegation mode, with three justified-and-dated rules, three Forbidden lines, and stubs for Claude Code and Copilot. The repo is now a place it can stay.

### Before and after
| | Before | After |
|---|---|---|
| Level | 0 — None | 1 — Framed (5/5) |
| Lines loaded per session | 0 | 24 (`AGENTS.md`) + 1 (`CLAUDE.md` stub) |
| Rules | 0 | 3 rules + 3 Forbidden |

### Files created
- `AGENTS.md` — 24 lines (root, source of truth).
- `CLAUDE.md` — 1 line (`@AGENTS.md`).
- `.github/copilot-instructions.md` — 1 line (points at AGENTS.md; Copilot can't include).

No `.cursor/rules` written — the owner uses only Claude Code and Copilot. Nothing was overwritten (no instruction files existed).

### Removed
Nothing. There were no prior instruction files to sort.

### Secrets
None leaked. The only match, `DATABASE_URL` in `deploy.yml`, is a proper `${{ secrets.DATABASE_URL }}` reference, not a hardcoded value. No action needed.

### Rules written
1. **Idempotency-Key inside the write transaction** — *(unverified)* `[2026-04]`. From the April 2026 double-debit post-mortem + ADR 0003. Nothing checks a new endpoint has it; review-only.
2. **`Idempotency-Replayed: true` on replays** — *(unverified)* `[2026-06]`. Said by the team; nowhere in the docs. The counter-example is cited: `POST /transfers` (`server.go`) does not set it yet — verified in code, line 89.
3. **Amounts are `int64` cents, no float** — *(unverified)* `[2025-09]`. ADR 0002. A `forbidigo` rule exists but lives in the `lint` job, which is `continue-on-error` and **does not block** — so it is marked unverified, not "enforced".

The hexagonal-architecture rule is **not** narrated: `tools/archcheck` (the `arch` CI job) blocks and enforces it, so it lives in the "what to run" table instead.

### Forbidden written
- Never touch a database that isn't your own — `[2026-02]`, the reset-db staging wipe.
- Never modify an already-applied migration — `[2026-02]`.
- Never deploy from your machine / with `dry_run` off — `[2026-11]`.

### Commands
- **Confirmed (in the file):** `make test`, `make arch`, `make test-integration`. All three are run as jobs by CI (`test`, `arch`) or documented in `docs/operations.md` (integration tests, run by hand). I could **not** run them locally — no Go toolchain in this environment — but the CI runs `go test`/`go vet`/archcheck as blocking jobs, which confirms them in the project's real environment.
- **`harness commands` candidates I did not keep:** `make test` and `make lint` were flagged as "CI does not run it" because CI calls `go test`/golangci-lint directly rather than via the Make target — but they're equivalent, so no surprise worth a line. `deploy/apply.sh` and `deploy/plan.sh` were flagged as delivery commands; I did not run them and folded them into a Forbidden line instead.
- **Not confirmed:** `README.md` advertises `make e2e`, but the `Makefile` has no `e2e` target. Left out of the file (see question 2).

### Questions for the owner
1. **`make e2e` doesn't exist.** The README lists `make e2e` under "Getting started", but there's no such target in the Makefile (only `test`, `test-integration`, `arch`, `lint`, `migrate`, `reset-db`). *Why it matters:* a newcomer following the README hits a dead command. *Proposed default:* remove the `make e2e` line from the README, unless an e2e target is meant to exist and was dropped.
2. **The no-float rule is written but not enforced.** You confirmed `lint` is deliberately non-blocking until the inherited-warning debt is paid. *Why it matters:* until then, nothing stops an agent (or anyone) introducing a `float64` amount. *Proposed default:* leave it as an `(unverified)` rule for now; when the debt is paid and `lint` becomes blocking, I can move the rule to "Enforced by `.golangci.yml`" in one edit.

### What comes next (not done)
Level 1 is a place you can stay. The natural next step is **level 2, Looped** — "review remarks become rules, so the same mistake isn't made twice." It adds a short *Maintaining this file* section and the `rule:` review convention, and it asks for a review habit and a few weeks of real signal before it fully counts. It's worth it here: two of your three rules are review-only today, and level 2 is exactly how a review catch becomes a durable rule. You decide the target (`harness target 2`), and the `harness-step` skill leads it when you're ready. I've stopped here, as step 1 asks.