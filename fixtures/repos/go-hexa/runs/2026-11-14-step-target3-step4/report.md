## Report

**The step**: I handled the only open P1 of the audit. `make reset-db` and `make migrate` now refuse any `DATABASE_URL` that does not point to a local database: they stop with code 1 without calling `psql`. A test checks this refusal.

**Before and after**
- Level reached: 1 · Framed, before as after. Level 3 has all its checks, but level 2 is still waiting for a real review signal.
- Level 3 · Verified: 3/4 → **4/4**.
- The line that flipped: `[ ] A harness-audit exists and has no open P1` → `[x]`.

**What it changes for the agent**: a `make reset-db` run with the staging URL left in a terminal (the incident of February 3) stops dead. Before, only a sentence of AGENTS.md prevented it.

**What is not proven**
- `status` measures the shape. This step does not show that agents work better, and no harvest of agent PRs measures it yet.
- The proof that exists: I saw the guardrail bite. `TestMakeTargetsRefuseRemote` failed on the old Makefile (`psql` called with `postgres://u@staging.example/...`, for both targets), then passed once the guard was wired in. `go vet`, `go test ./...` and `archcheck` pass locally.
- It has not been seen red in CI yet. The `test` job will run it, but no run has taken place.
- A `psql` run by hand obviously bypasses the guard.
- For the definition of "local database", the owner pointed to `docs/`, which says "a PostgreSQL of your own" and "nobody runs `make migrate` by hand" on staging or production. I deduced: localhost, a loopback address or a Unix socket (`PGHOST` included), with no escape hatch. A development database on another machine will be refused.

**Files**
- `tools/localdb/main.go` and `tools/localdb/main_test.go` (new).
- `Makefile`: the guard is called at the head of `migrate` and of `reset-db`.
- `AGENTS.md:24`: the forbidden item is reduced to its "Enforced by" line.
- `docs/operations.md`: the sentence "the target does not look at which database it is" was no longer true, I replaced it.
- `.harness/audit.json`: the item is marked resolved, the rule moved from the leaks to the guarded rules, and remediation step 1 is dated.
- Nothing is committed, no PR is open.

**Questions**
1. Should the PR be opened for these changes? Default: yes, on a dedicated branch.
2. Does anyone in the team use a development PostgreSQL on another machine? Default: no, so no exception.

**Possible next step**: nothing on levels 1 and 3. Level 2 is waiting for the first real `rule:` in review, which alone will get the targeted level 3 recognised. In the meantime, the P2s of the audit can be handled, starting with the `github.ref == main` guard in `deploy.yml`, but they do not raise the level.