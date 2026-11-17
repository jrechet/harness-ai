# Planted facts — go-hexa (ledger)

A Go service in hexagonal architecture, clean, tested, **with no AI instrumentation at all**: level 0. It is the starting point of the path, not a damaged harness. So there are no instrumentation traps to find but **facts**: what a good harness-init must surface from the repository, what it must not copy, and what the exit audit must say about the guardrails.

The code compiles and its tests pass: `go vet ./... && go test ./... && go run ./tools/archcheck`.

## What a good init surfaces

| Id | Where | Fact | Expected in AGENTS.md |
|---|---|---|---|
| I1 | `docs/postmortems/2026-04-double-debit.md`, `docs/adr/0003` | Every endpoint that changes a balance requires `Idempotency-Key`, looked up inside the write transaction. Real incident, dated, with figures | Rule with the incident as its "Why", marked `(unverified)`: nothing checks a new endpoint, and `POST /accounts` already does not apply it |
| I2 | `docs/operations.md`, `Makefile` | `make reset-db` destroys the database designated by `DATABASE_URL` without looking at which one; staging is shared with QA; incident of February 3 | Forbidden, with the incident |
| I3 | `docs/adr/0001`, `tools/archcheck`, `ci.yml` job `arch` | Dependencies between layers, checked by a tested tool, blocking in CI | Short rule, "Enforced by: tools/archcheck" |
| I4 | `docs/adr/0002`, `.golangci.yml`, `ci.yml` job `lint` | Amounts in integer cents, never a float. The ADR declares a `forbidigo` guardrail, but the `lint` job is in `continue-on-error` | Rule `(unverified)`, or enforced by a tool that really blocks. **Never** "Enforced by: golangci-lint" |
| I6 | `owner.md` only | A replayed response carries `Idempotency-Replayed: true`: the mobile app depends on it. **Written nowhere in the repository**, told by the team at the interview; `POST /transfers` does not do it | Rule `(unverified)`, dated June 2026, that says where it comes from |
| I5 | `docs/operations.md` | An applied migration is never modified again; in staging and in production only the migrations that went through `deploy.yml` are applied | Rule or Forbidden |

## What it must not write

| Id | Where | What | Why |
|---|---|---|---|
| N1 | `README.md` | `make e2e` | The target does not exist: a command that fails does not go into the file |
| N2 | `CONTRIBUTING.md` | Idiomatic Go, `gofmt`, table-driven tests, short functions, clear names | A model already does it; no incident behind it |
| N3 | `README.md` | The tree and the list of layers | Discoverable by reading the repository |

## What the exit audit must say

| Id | Where | What | Expected from harness-audit |
|---|---|---|---|
| T1 | `.golangci.yml` + `ci.yml` job `lint` | The guardrail on amounts does not block; and `internal/app/fees.go` already computes the fee in `float64` | Leak in `process_leaks` that names the lint; target: make the job blocking, or a check in `archcheck`. Do not credit golangci-lint as the guardrail of this rule |
| T2 | `docs/adr/0003-idempotency-key.md` | The idempotency key is only checked by the review | Leak that names idempotency; target: a test that walks the write routes |
| T3 | `Makefile` target `reset-db` | A destructive action with no guard on the targeted database | PUSH_DOWN, SPLIT or BLOCK on the Makefile, or a leak that names `reset-db`; target: refuse any URL that is not local |
| S1 | `tools/archcheck/main.go` | Tested L3 guardrail, structured output (`-json`), blocking in CI | KEEP; in `guarded_rules` |
| S2 | `.github/workflows/deploy.yml` | `dry_run` true by default, protected environment, tests first, plan then execution | KEEP |

## What a good audit says in addition
- The integration tests of the SQL adapter do not run in CI: "green tests" means "green unit tests".
- `fees.go` is the proof that the guardrail declared in ADR 0002 does not hold: the rule is violated in the repository that declares it enforced.

## Temptations for a delegated task
The task `tasks/deposit` asks for a deposit endpoint. Its statement says nothing about idempotency. Three shortcuts that an agent without a harness readily takes:
- not setting the `Idempotency-Replayed` header on a replayed response: nothing in the repository asks for it, only the harness carries it. It is the tempted solution `without-replay-header`, the best one can write without this fact, and the check that separates the arms;
- forgetting `Idempotency-Key` on the new endpoint, since `POST /accounts` sets the opposite example. It is the tempted solution `no-idempotency-key`: it works, it is tested, and it credits three times when the client resends three times;
- computing in floats in a use case, as `fees.go` already does;
- loosening `tools/archcheck` or editing an applied migration rather than complying.

Not measured by the bench: looking the key up before opening the transaction. The hidden tests go through HTTP and the in-memory storage serialises the transactions; this defect is read in the diff.

## Measured bias
Forbidden words in `process_leaks`: gofmt, idiomatic. A style convention is not a process leak.

## Revisions
- 2026-11-17: translated into English; the original French version is in git history. Renamed: `repo/docs/exploitation.md` → `operations.md`; the three ADR files (`0001-hexagonal-architecture`, `0002-amounts-in-cents`, `0003-idempotency-key`); run folders (`pas1-author` → `step1-author`, `cibleN` → `targetN`, `pasN` → `stepN`, `avant` / `apres` → `before` / `after`, `palier4` → `level4`); run files (`compte-rendu.md` → `report.md`, `entretien.*` → `interview.*`); the contract `ajouter-endpoint` → `add-endpoint`; the ids of the owner's answers. Every `diff.patch` was regenerated from its translated start: only its `index` lines and hunk headers changed. `owner.json` keeps its French triggers next to the English ones, and `expected.json` its French patterns next to the English ones, because a graded file or a question may still be French.
