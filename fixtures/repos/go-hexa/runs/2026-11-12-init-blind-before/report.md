I laid level 1 ("Framed") on the `ledger` repository. The check passes: `harness status` gives level 1 with 5 checks out of 5 and no reference without a target. I committed nothing and did not go beyond level 1.

## Report

**Before and after**
- Before: level 0, no instruction file, 0 lines loaded per session, 0 rules.
- After: level 1, about 26 lines loaded per session (`AGENTS.md` through `CLAUDE.md`), 3 rules and 3 forbidden items.

**Files created** (no existing file was modified)
- `AGENTS.md` (26 lines): mode line, what the repository does, commands table, rules, forbidden items.
- `CLAUDE.md` (1 line): `@AGENTS.md`.
- `.github/copilot-instructions.md` (1 line): points to `AGENTS.md`.
- `.harness/state.json`: written by `harness status`.
- No Cursor stub: the team only uses Claude Code and Copilot.

**Removed**
- Nothing. There was no instruction file, neither at the root nor in the subfolders.
- `CONTRIBUTING.md` contains generic guidance ("idiomatic Go", "short functions") that brings nothing to an agent. I did not copy it and I did not modify the file.

**Secrets**
- None found. The only occurrence is `secrets.DATABASE_URL` in `deploy.yml`, which refers to a GitHub secret: that is the normal use.

**Rules written**

| Rule | Status | Date |
|---|---|---|
| Hexagonal layers, only `cmd/ledgerd` wires the adapters | Enforced by `tools/archcheck` (job `arch`, blocking) | [2025-09] |
| Amounts in `int64` cents, no float in `domain` nor `app` | Unverified: the `forbidigo` rule lives in the `lint` job, which does not block. Already violated by `internal/app/fees.go`, flagged as a counter-example. | [2025-09] |
| `Idempotency-Key` required, and looked up inside the transaction that writes | Unverified: only the transfer is tested. Born of the double-debit incident (37 accounts). `POST /accounts` is a known exception. | [2026-04] |
| Forbidden: touching a database that is not your own (`reset-db` or `migrate` on staging/prod) | Born of the incident of February 3, 2026: two days of QA data lost | [2026-02] |
| Forbidden: modifying a migration already applied | No known incident | [2026-11] |
| Forbidden: running `deploy.yml` with `dry_run` set to `false` | No known incident | [2026-11] |

**Commands**
- **Confirmed** (run and green): `go vet ./...`, `go test ./...`, `go run ./tools/archcheck`.
- **Not confirmed:**
  - `make lint` / `golangci-lint run`: the tool is installed, but running it was refused by the session's permissions. So I could not check whether `fees.go` does trigger `forbidigo`.
  - `make test-integration`: it needs a migrated database, I did not run it. It does not run in CI.
  - `make e2e`: the target does not exist. The owner confirms it was removed a year ago, but the README still cites it.
  - A few combined read commands were also refused. I replaced them with equivalent reads, with no loss of information.

**Questions to the owner**
1. Is the `float64` of `internal/app/fees.go` an accepted exception or a violation of ADR 0002 to fix? I asked it twice and the answer was about something else. Default applied: known violation, not to be imitated.
2. Do we remove `make e2e` from the README? Proposed default: yes, in a separate PR.
3. ADR 0002 says the amounts rule is "enforced by the `lint` job", but this job runs in `continue-on-error`. Should at least the `forbidigo` rule be made blocking, for example in a separate job? Proposed default: yes.
4. A rule "if you touch `internal/adapters/postgres`, run `make test-integration` on your local database" would be useful, but the command is not confirmed. Can it be validated? Proposed default: it stays out of the file in the meantime.
5. What I observed without being able to explain it: `cmd/ledgerd/main.go` calls `sql.Open("pgx", …)` without importing a pgx driver. Does the PostgreSQL mode really work?

**Possible next step**: level 2 ("Looped"), with the Maintenance section, the `rule:` convention in review and a first harvest. It is up to you to ask for it with `harness target`, and up to harness-step to carry it out.