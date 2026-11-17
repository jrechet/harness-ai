The repository is at level 1 "Framed". `harness status` passes its 5 checks out of 5 and reports no reference without a target. I committed nothing.

Three commands were refused because nothing could be approved in this session: combined `ls`/`cat` (I read the files another way), `make lint` and `make e2e`. The last two therefore remain not confirmed (see below).

**Before and after**
| | Before | After |
|---|---|---|
| Level | 0 (no instruction file) | 1 · Framed (5/5) |
| Lines loaded per session | 0 | 24 (`CLAUDE.md` 1 + `AGENTS.md` 23) |
| Rules | 0 | 4 rules + 3 forbidden items |

**Files created**
- `AGENTS.md`: 23 lines, in delegation mode.
- `CLAUDE.md`: 1 line, `@AGENTS.md`.
- `.github/copilot-instructions.md`: 1 line. No Cursor stub, since the team uses Claude Code and Copilot.
- `.harness/state.json`: written by `harness status`.

**Removed**: nothing, there was no instruction file. I copied no line of `CONTRIBUTING.md`: "idiomatic Go", "short functions", "table-driven tests" do not change what the agent does.

**Secrets**: none found. The only hit is `secrets.DATABASE_URL` in `deploy.yml`, a reference to the GitHub vault and not a value.

**Rules written**
| Rule | Status | Date |
|---|---|---|
| `Idempotency-Key` on every write, looked up inside the transaction (post-mortem of the double debit, ADR 0003) | Unverified: nothing checks a new endpoint | [2026-04] |
| `Idempotency-Replayed: true` header on a replay (told by the team). The `POST /transfers` exception is flagged so that it is not used as a model | Unverified | [2026-06] |
| No float for an amount (ADR 0002). `internal/app/fees.go` already violates the rule, flagged so that it is not copied | Unverified: `forbidigo` runs in the `lint` job, which is in `continue-on-error` | [2025-09] |
| Hexagonal layers (ADR 0001) | Enforced by `tools/archcheck`, blocking `arch` job | [2025-09] |
| Forbidden: `reset-db` / `migrate` on a database that is not your own (QA incident of February 3) | — | [2026-02] |
| Forbidden: modifying a migration already applied | — | [2026-11] |
| Forbidden: running `deploy.yml` without `dry_run` | — | [2026-11] |

**Commands**
- **Confirmed**: `make test`, `go vet ./...` and `make arch` pass.
- **Not confirmed**:
  - `make lint`: refused by the session. It is not in the commands table.
  - `make e2e`: the target does not exist. The owner confirms it was removed a year ago.
  - `make test-integration`: needs a migrated database, and it does not run in CI.

**Questions to the owner**
1. The README still cites `make e2e`. Should the line be removed? I propose yes: it is stale according to your answer.
2. `fees.go` uses `float64`. Should an agent that goes through this file fix it, or not touch it? I propose not touching it outside a dedicated ticket. Your answer confirmed the debt but not what to do about it.
3. The forbidden item on databases: I understood "`reset-db` and `migrate` only on a local database of your own". Your answer repeated the original wording without being more precise. I propose keeping my reading.
4. Forbidden items on migrations and on `dry_run`: what is the date of the decision? In the meantime, I put today's date.

**Possible next step**: making the `lint` job blocking, at least for the `forbidigo` rule, would move the amounts rule to "enforced" (level 3). I did not do it; `harness target` to go further.