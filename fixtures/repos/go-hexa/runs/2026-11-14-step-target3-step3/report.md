## Report — harness-step

Two shell commands were refused by the permission system (a grouped `ls`/`cat` in the kit and another in the repository). I read the same files with the read tools, so nothing is missing from the audit.

- **The step**: I ran harness-audit on the repository. The report is in `.harness/audit.md` and its data in `.harness/audit.json`. It finds **one P1 still open**, so the targeted check still fails.
- **Before and after**: still level 1 · Framed (target: 3). Level 3 stays at **3/4** before as after. The line "A harness-audit exists and has no open P1" does not pass: the audit exists, and `status` reads it (measured layer view: 6 misplaced items), but this P1 remains. So the step is not finished. I did not lower the priority to make the check pass.
- **The P1**: `make reset-db` and `make migrate` only check the presence of `DATABASE_URL`, not the targeted database (`Makefile:19-26`). The forbidden item "local database only" is written only in `AGENTS.md:24`, although it comes from two days of QA data lost on staging on February 3, 2026. An agent that ignores it can destroy the staging schema.
- **What it changes for the agent**: nothing for now. The audit tells the team where the rules hold only by the text: 6 leaks at the "cut the agent" test, 5 P2, score 31/100.
- **What is not proven**: the audit looks at the shape of the repository and of the workflows. I saw no guardrail fail on a violation, I did not consult the CI history and I did not run golangci-lint. `go test ./...` passes locally. The GitHub settings cannot be read from the repository (environment protections, required checks) and the owner did not answer about the environments. Nothing proves yet that agents work better.
- **Files**: `.harness/audit.md` and `.harness/audit.json` (created). I committed nothing.
- **Out of scope, worth a look**: `go.mod` declares no `pgx` driver, whereas `cmd/ledgerd/main.go:40` and the integration tests open `sql.Open("pgx", …)`. With a `DATABASE_URL` set, the service should refuse to start and `make test-integration` cannot run. To be checked on a real environment.
- **Questions** (the proposed default follows each question):
  1. Which hosts count as a "local database" for `reset-db` and `migrate`? Default: localhost, 127.0.0.1, ::1 and Unix socket, with an explicit override variable.
  2. What protections do the GitHub `staging` and `production` environments have? Default: assume none, and have `deploy.yml` refuse any run that is not a plain preview (`dry_run` set to false) from a branch other than `main`.
  3. Is the `migrations` job mandatory to merge on `main`? You only cited `test` and `arch`. Default: no, and it must be made mandatory.
  4. Must the integer fee computation keep the current rounding? Default: yes, `(cents*15+500)/1000`.
- **Possible next step**: handle the P1, with a guard in the two Makefile targets that refuses a non-local database and whose refusal has been seen. It is within the target, and your answer to question 1 is enough to do it.