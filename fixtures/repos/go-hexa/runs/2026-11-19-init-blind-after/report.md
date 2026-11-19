Done. `AGENTS.md` is 25 lines, level 1 is reached at 5/5, and the map now shows "you are here" at *Framed*. Here is the report.

---

# Report — harness init, step 1 (level 1 · Framed)

## The map, updated
```
✓ 1 Framed     the agent knows the project, its rules and what it must never do   ← you are here
· 2 Looped     review remarks become rules, so the same mistake is not made twice
· 3 Verified   mandatory rules are enforced by tools, not just written down
· 4 Delegated  whole tasks go to the agent and come back clean
```
This run wrote a 25-line `AGENTS.md` (delegation mode) plus the Claude and Copilot stubs, grounding four rules and three forbidden lines in the repo's ADRs, post-mortem and operations note. The repository moved from **level 0 (None)** to **level 1 (Framed)**, 5/5.

## Before and after
| | Before | After |
|---|---|---|
| Level | 0 — None | 1 — Framed (5/5) |
| Lines loaded per session | 0 (no instruction file) | 25 (`CLAUDE.md` → `AGENTS.md`) |
| Rules | 0 | 4 |
| Forbidden lines | 0 | 3 |

## Files created
- `AGENTS.md` — 25 lines (single source; mode line, what-to-run table, 4 rules, 3 forbidden).
- `CLAUDE.md` — 1 line (`@AGENTS.md` stub).
- `.github/copilot-instructions.md` — 1 line (pointer to `AGENTS.md`).

No Cursor stub: the owner chose Claude Code and Copilot only.

## Removed
Nothing. There was no pre-existing instruction file to sort — this is a greenfield setup.

## Secrets
Checked the instruction files, config, Makefile and workflows. **No literal secret found.** `deploy.yml` references `secrets.DATABASE_URL` (a GitHub Actions secret, not a value in the repo); `.gitignore` already excludes `.env`. Nothing to regenerate.

## Rules written
1. **Inward dependencies (hexagonal).** Why: ADR 0001. **Enforced by `tools/archcheck`, CI job `arch` — confirmed blocking.** [2025-09]
2. **Amounts are `int64` cents, never float.** Why: ADR 0002. A `forbidigo` rule exists in `.golangci.yml`, but the `lint` job is `continue-on-error`, so **nothing blocks on it → (unverified).** [2025-09]
3. **Idempotency key required and looked up inside the write transaction.** Why: ADR 0003 / April 2026 double-debit. Nothing checks new write endpoints → **(unverified).** [2026-04]
4. **`Idempotency-Replayed: true` header on replays.** Why: said by the team; the mobile app relies on it since 2026-06. **(unverified)** — and the repo does **not** yet satisfy it: `POST /transfers` (`internal/adapters/httpapi/server.go:67`) sets no such header. The file flags that handler as not a model to copy. [2026-06]

Two of four rules (amounts, replay-header) are unverified. In delegation mode that is a debt — level 3 (push rules down into blocking tools) is where it gets paid.

## Commands
- **Confirmed by the CI workflow** (could not be run locally — the Go toolchain is absent in this environment): `go test ./...` + `go vet ./...` (job `test`, blocks), `go run ./tools/archcheck` (job `arch`, blocks).
- **Present but not blocking:** `golangci-lint run` — the `lint` job is `continue-on-error`. `make test-integration` — not run in CI (run by hand before a prod release touching the postgres adapter).
- **Not confirmed:** `make e2e` — cited in `README.md` but there is **no `e2e` target in the Makefile**. Left out of the file (see question 2).
- **`harness commands` candidates not kept:** `make test` and `make lint` are thin wrappers over `go test ./...` and `golangci-lint run` — the table already names those, so the wrappers add nothing. `deploy/apply.sh` and `deploy/plan.sh` were flagged as delivery commands: not run, turned into a Forbidden line instead.

## Forbidden lines written
1. No `make migrate` / `make reset-db` / `deploy/apply.sh` against a database that isn't your own. Why: the 2026-02-03 reset-db incident (shared QA schema dropped, two days lost). [2026-02]
2. Never edit an applied migration; add a new numbered file. Why: `docs/operations.md`. [2026-11]
3. No `deploy.yml` without `dry_run`, no running `deploy/*.sh` yourself. Why: they roll staging/production; prod needs human approval. [2026-11]

## Questions for the owner
1. **The amounts/float rule is enforced only by a non-blocking `lint` job.** Why it matters: in delegation, an unverified rule gets skipped roughly one PR in ten. Should the `forbidigo` float check be made blocking (split out of the warning-debt lint job)? *Proposed default:* leave as-is for now and address it when you take on level 3 (Verified).
2. **`README.md` lists `make e2e`, but the Makefile has no `e2e` target.** Why it matters: an agent told to "run e2e" will hit a missing target. Is e2e gone, or is the target missing? *Proposed default:* treat the README line as stale until you say otherwise.

## What comes next (not done — your call)
Level 1 is a place you can stay. The natural next step toward **level 2 (Looped)** is a short "Maintaining this file" section and the `rule:` review convention, so that review remarks turn into dated rules — that needs a review habit and a few weeks of real feedback, and it's led by the `harness-step` skill. Given the two unverified rules above, **level 3 (Verified)** — making the float and idempotency rules enforced by tools rather than text — is likely the higher-value direction for a delegation repo. You decide how far to go with `harness target <level>`; nothing beyond level 1 was started here.