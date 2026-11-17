I wrote an `AGENTS.md` of 26 lines, with the stubs for Claude Code and Copilot. The `harness status` check passes: level 1 reached, five checks out of five, no reference without a target. Nothing is committed.

Three commands were refused automatically, because this session cannot ask for permission: `make lint`, `make e2e` and a check of the exit code of `archcheck`. What they would have confirmed is listed below, under "not confirmed".

## Report

**Before → after**
| | Before | After |
|---|---|---|
| Level | 0 · None | 1 · Framed (5/5) |
| Lines loaded per session | 0 | 26 (`AGENTS.md` through the `CLAUDE.md` stub) |
| Rules | 0 | 4 rules and 3 forbidden items |

**Files created**
- `AGENTS.md`: 26 lines
- `CLAUDE.md`: 1 line, `@AGENTS.md`
- `.github/copilot-instructions.md`: 1 line, points to `AGENTS.md`
- `.harness/state.json`: written by the CLI
- No Cursor rules, the tool is not used.

**Removed**: nothing. There was no instruction file for agents (`AGENTS.md`, `CLAUDE.md`, Copilot, Cursor), neither at the root nor in a subfolder. I took nothing from `CONTRIBUTING.md`: its lines are either generic ("idiomatic Go", "short functions") or discoverable. I did not modify it.

**Secrets**: none found. `deploy.yml` reads `DATABASE_URL` from the GitHub secrets, which is correct.

**Rules written**
| Rule | Status | Date |
|---|---|---|
| `Idempotency-Key` required, looked up inside the transaction; a replay returns the first result, the same key with another request gives 409. `POST /accounts` is flagged as a counter-example. | unverified: ADR 0003 itself says that nothing checks a new endpoint | [2026-04] |
| Every new write endpoint returns `Idempotency-Replayed: true` when it replays a request. `POST /transfers` is flagged as a counter-example. | unverified | [2026-06] |
| Amounts in cents, no float in `domain` nor `app`. `internal/app/fees.go:18` is flagged as a counter-example. | unverified: ADR 0002 says "enforced by the lint", but this job is in `continue-on-error` | [2025-09] |
| No forbidden dependency between the layers (ADR 0001) | Enforced by: `tools/archcheck`, job `arch` which blocks | [2025-09] |
| **Forbidden**: `reset-db`, `migrate` or `psql` on a database that is not your own (incident of February 3, 2026) | — | [2026-02] |
| **Forbidden**: modifying an existing file of `migrations/` | — | [2026-11], the operations note is not dated |
| **Forbidden**: running `deploy.yml` without `dry_run` | — | [2026-11] |

**Commands**
- Confirmed: `go vet ./...`, `go test ./...` (everything is green) and `make arch` (no violation shown).
- Not confirmed:
  - `make lint`: refused in this session.
  - `make test-integration`: needs a migrated PostgreSQL database, I did not run it.
  - `make e2e`: the target does not exist in the `Makefile`, as you had said.

**Questions to the owner** (with the proposed default)
1. `internal/app/fees.go:18` computes the fee with `float64(...) * 0.015`, which ADR 0002 forbids. The lint should have flagged it, but it does not block. Should the computation be fixed to use integers? Default: open a ticket, and leave the file as it is until then.
2. I forbade modifying **any** existing file of `migrations/`, without telling apart those already applied. Is that fine with you? Default: yes, the agent cannot know which ones are applied.
3. The README still cites `make e2e`. Should this line be removed? Default: yes, in a separate PR.
4. Does the `forbidigo` rule (`^float(32|64)$`) really catch a conversion such as `float64(x)`? I could not run the lint to see. Default: check it together with question 1.

**Possible next step**: level 3 (Verified). It means making the lint blocking on `internal/domain` and `internal/app`, and adding a test that forces every write endpoint to require the idempotency key and the `Idempotency-Replayed` header. It is up to you to ask for it (`harness target`), and harness-step will carry it out.