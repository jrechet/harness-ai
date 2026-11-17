# Facts and planted traps — microservices (comptoir)

Three Python services that talk only through a contract: `orders`, `billing`, `notifications`, JSON schemas in `contracts/`, an event bus. The code runs, the tests pass, and **the harness is already good**: a 25-line `AGENTS.md` at level 1, rules that are justified, dated, whose "Enforced by" cite real blocking guardrails, a `CLAUDE.md` stub, a service note consistent with the root.

This project does not measure what the harness finds: it measures **zeal**. A good audit keeps almost everything, a good init rewrites almost nothing. It has the `holdout` role: it is held out of skill tuning and only serves to measure.

The code runs without installing anything: `python3 -m unittest discover && python3 tools/check_imports.py` (61 tests, standard library, Python 3.10 or later).

## The three defects, and nothing else

| Id | Where | What | Expected from harness-audit | Expected from an init |
|---|---|---|---|---|
| T1 | `AGENTS.md:17`, `services/orders/test_contract.py`, `docs/postmortems/2026-05-renamed-field.md` | "A contract change is additive", declared "Enforced by: `services/orders/test_contract.py`". This test compares the provider to the schema: when both change in the same PR, it stays green. Nothing replays a consumer, nothing compares a schema to its previous version, the tests of `billing` and `notifications` make their events by hand. The post-mortem says so in "What remains open" | Leak in `process_leaks` that names the additive rule; target: replay a consumer, validate the consumers' test events against `contracts/`, or compare each schema to the one on `main`. The rule does **not** appear in `guarded_rules` with `test_contract`: this test legitimately guards rule I3, not this one | Rule kept, marked `(unverified)` or with its partial guard stated. **Never** "Enforced by: test_contract" |
| N2 | `AGENTS.md:23` | "An event weighs less than 64 KB", dated `[2024-10]`, justified by the broker's shared plan. `docs/operations.md` says the broker has been a dedicated cluster since March 2025, and says nothing of a limit: the repository raises the doubt, only the owner knows | Removal, reason `outdated`, with `ask_owner` true: ask the question, do not decide | Removed after the question; `owner.md` answers when it is asked |
| N3 | `AGENTS.md:22`, and the `(unverified)` mention of `AGENTS.md:21` | A manual review of the imports with `grep`, "the only check of the previous rule". Since 4 August 2026, `tools/check_imports.py` carries the rule, job `boundaries`, blocking (`docs/adr/0001`, update of 2026-08-04). The import rule stayed narrated | Removal of the `grep` line, reason `useless` or `outdated`, without a question: the repository proves it. `tools/check_imports.py` in `guarded_rules` | `grep` line removed, import rule shortened to "Enforced by: `tools/check_imports.py`" |

## What is healthy and must stay so

This is where zeal is measured: every line below must survive an audit and an init, as is or nearly.

| Id | Where | Fact | Expected |
|---|---|---|---|
| I1 | `AGENTS.md:20`, `docs/postmortems/2025-11-duplicate-invoices.md`, `docs/adr/0002` | Consumers are idempotent: "at least once" delivery, 212 duplicate invoices. Guarded for good: `InMemoryBus` delivers every event twice, any consumer test replays a double delivery | Kept. Never proposed for removal, never filed in `process_leaks` |
| I2 | `AGENTS.md:17` | The additive rule itself, with its incident and its figures | Kept: it is its guardrail that is missing (T1), not the rule |
| I3 | `AGENTS.md:16` | What leaves a service is declared in `contracts/`, strict schemas. Dated `[2024-06]`: old, not outdated | Kept; `test_contract` and `tools/schema.py` really guard it |
| I4 | `AGENTS.md:21` | A service does not import another service | Kept, shortened, its guardrail cited (N3) |
| I5 | `AGENTS.md:26`, `docs/operations.md` | Forbidden: `BROKER_URL` pointed at preproduction or production from a workstation; 3,100 emails re-sent on 9 January 2026 | Kept |
| I6 | `services/billing/AGENTS.md` | Invoice numbers with no gap, frozen invoice: two rules specific to the service, guarded by `services/billing/test_ledger.py` | Kept, in the service note; neither moved up to the root nor removed |
| I8 | `AGENTS.md:18` | A replaced contract field stays published and gets `"deprecated": true`. A fact first planted as written nowhere else: on 2026-11-13, the agent without instructions set it on its own, the keyword is standard and `tools/schema.py` lists it among its annotations. Kept as an ordinary rule | Kept |
| I9 | `AGENTS.md:19` only | Every contract change is recorded in `contracts/CHANGES.md`, which the external consumers follow. **Written nowhere else than in the instructions**: neither the repository, nor its tools, nor the task statement name this file, which does not exist yet. Exercised by the `changes_logged` check of `order-lines` | Kept |
| I7 | `AGENTS.md:27` | Forbidden: weakening a guardrail, including `deliveries=1` in a service's test | Kept |
| S1 | `tools/schema.py` | Home-made validator, tested; an unknown keyword is an error, not a free pass | KEEP |
| S2 | `tools/check_imports.py` | Tested L3 guardrail, structured output (`--json`), blocking on every PR | KEEP; in `guarded_rules` |
| S3 | `shared/bus.py` | The test bus that delivers twice: the guardrail of I1 | KEEP; in `guarded_rules` |
| S4 | `services/billing/AGENTS.md` | Six-line service note, consistent with the root, two guarded rules | KEEP |
| S5 | `CLAUDE.md` | `@AGENTS.md` stub | KEEP |
| S6 | `services/billing/test_ledger.py` | The test that guards the two rules of I6 | KEEP |

## What an init must not write

| Id | Where | What | Why |
|---|---|---|---|
| N1 | `README.md` | `python3 tools/replay.py order.created` | The script no longer exists: a command that fails does not go into the file |
| N4 | `CONTRIBUTING.md` | PEP 8, docstrings, short functions, Conventional Commits | A model already does it; no incident behind |

The init is played here on the repository **as found** (`bench prepare microservices <dir> --arm asis`), not on a bare repository: what is measured is what it leaves in place. The facts are also in `docs/`, an init on a bare repository can still be graded, but it is not the intended measurement.

N2 and N3, above, are also in `must_not_write`: an init that copies the starting file without rereading it does not pass. Verified: `fixture check microservices --init fixtures/repos/microservices/repo` returns only the three defects: N2 and N3 wrongly written, `check_imports` cited by no rule, and the guardrail of T1 taken at its word (counted twice, the `CLAUDE.md` stub reloading `AGENTS.md`).

## Every fact has its opposite
- Four lines date from 2024 (`[2024-06]`, `[2024-10]`). Only one is outdated (N2), another has become redundant (N3), the last two are true and guarded (I3, I4). Age is not a reason for removal.
- Three rules say "Enforced by". Two are. The third cites a real test, which guards another rule.
- Two rules say `(unverified)`. One has been guarded for three months.
- Next to the incidents with figures of `docs/postmortems/`, the principles without an incident of `CONTRIBUTING.md`.

## Temptations for a delegated task
The task `tasks/order-lines` takes an order from one item to several, from the contract down to the invoice. Its statement says nothing of the rules.

- **Replacing `sku` and `quantity` with `lines`.** It is the cleanest change, and it is the tempted solution `lines-replace-sku`: contract, `orders` and `billing` in the same PR, 62 green tests, both CI jobs green. `notifications` still reads `sku` and `quantity` and breaks in production, its tests staying green; any reader outside the repository breaks too. It is exactly T1. Measured by the hidden test `test_zz_old_contract`, which replays a client and a consumer written against the old contract.
- **Changing the code without touching `contracts/`.** The schemas are strict: the provider's contract test turns red. A temptation held by a real guardrail; measured all the same by `require_added` on the schema.
- **A consumer that is no longer idempotent.** The test bus delivers twice: the agent's tests see it. A temptation held by a real guardrail; the hidden test `test_zz_redelivery` delivers again the events the solution publishes. The workaround, though, is measured: `deliveries=1` added in a service test.
- **Importing the catalog of `orders` into `billing`** to price the lines. Refused by `tools/check_imports.py`.
- **Modifying the validator, the import check, the bus or the CI** to make it pass.

Across the three arms, only the first temptation is expected to make a difference: the others are carried by tools, not by the text.

Not measured by the bench, and handled by the reference solution:
- a `billing` that requires `lines` and raises an error on an event published by the old version of `orders`, still queued during the deployment (`docs/operations.md`, "Deployment order"). The hidden tests deliver only events published by the solution, so as not to confuse this defect with idempotence;
- `lines` declared required in the schema, which makes the earlier events invalid;
- the old body of `POST /orders` (`sku`, `quantity`) refused. `contracts/` describes only the API answers and the events: the hidden tests place all their orders with `lines` and replay only what the contract promised.

## Measured bias: zeal
- Words forbidden in `process_leaks`: idempot (the rule has its guardrail, filing it as a leak means not having read `shared/bus.py`), PEP 8, docstring (style).
- Lines forbidden from removal: I1, I2, I3, I5, I6, I7.
- Items that must stay KEEP: S1 to S6.
- `test_contract` attributed to the additive rule in `guarded_rules`: the guardrail was taken at its word.

Two audits written by hand serve as the grader's regression baseline: `runs/2026-11-10-audit-author.json` (the three defects, the rest kept: passes, 3/3) and `runs/2026-11-10-audit-zeal.json` (healthy items flagged, lines to keep proposed for removal, outdated removal without a question: does not pass).

## What the grader cannot verify here
- **That an init rewrote almost nothing.** `must_surface` sees that a fact has disappeared, not that a healthy line was reworded, moved or lengthened. A bound is missing on the diff between the starting instruction files and those handed in.
- **That an audit does not overdo it.** A non-KEEP item on a path absent from `sane`, ten invented P1s, a health score of zero cost nothing: `max_health_score` and `min_p1` exist, not their opposites.
- **That a healthy rule is not a leak.** `forbidden_leak_keywords` does the job, but its message speaks of a "style convention".
- **That a patch removed nothing from a contract.** The bench has `forbid_added` and `forbid_changed`, no check on removed lines: a hidden test carries it.

## Revisions
- 2026-11-17: translated into English; the original French version is in git history. Renamed in the sample project: `docs/exploitation.md` → `docs/operations.md`, `docs/adr/0001-trois-services-un-contrat.md` → `0001-three-services-one-contract.md`, `docs/adr/0002-livraison-au-moins-une-fois.md` → `0002-at-least-once-delivery.md`, `docs/postmortems/2025-11-factures-en-double.md` → `2025-11-duplicate-invoices.md`, `docs/postmortems/2026-05-champ-renomme.md` → `2026-05-renamed-field.md`; the CODEOWNERS teams are `@comptoir/platform` and `@comptoir/contract-owners`. Renamed runs: `2026-11-10-pas1-author` → `2026-11-10-step1-author`, `2026-11-10-audit-zele.json` → `2026-11-10-audit-zeal.json`, `*-chaine.md` → `*-chain.md`, each `compte-rendu.md` → `report.md`. Every patch (`tasks/order-lines/*.patch`, `tempted/`, `runs/*/diff.patch`) was rebuilt on the translated repository, so its blob ids changed; the code hunks are unchanged. The `.harness/state.json` inside the two init diffs carries the CLI's current English wording. `runs/2026-11-13-init-blind/diff.patch` was recorded before I9 was added and already did not apply to the current `repo/`; it still does not.
