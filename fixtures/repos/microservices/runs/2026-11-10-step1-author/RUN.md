# Step 1 by the author of the fixture — 2026-11-10

This repository arrives with a harness at level 1, and it is good. So step 1 has nothing to lay: it rereads each line, corrects three, and leaves the rest as it found it. `AGENTS.md` goes from 25 to 23 lines; `CLAUDE.md` and `services/billing/AGENTS.md` are copied byte for byte.

It is a **regression baseline** for the grader (`fixture check microservices --init <this folder>`) and the bench's default `harness` arm, not a measurement of the skill. Here the `harness` arm and the `asis` arm differ only by these three lines: the gap between the two says what they are worth.

## What changed

| Starting line | Before | After | Why |
|---|---|---|---|
| `AGENTS.md:17`, the additive rule | "Enforced by: `services/orders/test_contract.py`" | `(unverified)`, with what the test guards and what it does not | The test compares the provider to the schema. When both change together it stays green: it is the incident of 12 May, and the post-mortem says so in "What remains open". A rule declared enforced that is not is worse than a narrated rule |
| `AGENTS.md:19`, the import rule | `(unverified)` | "Enforced by: `tools/check_imports.py`, job `boundaries`" | The guardrail has existed since 4 August 2026 and blocks on every PR |
| `AGENTS.md:20`, the review with `grep` | one line | removed | "The only check of the previous rule" no longer is: the line costs context and makes one do by hand what the CI does |
| `AGENTS.md:21`, the 64 KB limit | one line | removed | Dated October 2024, justified by the broker's shared plan. `docs/operations.md` says the broker changed in March 2025. The question was asked to the owner, who confirms: the limit no longer exists |

The dates did not move: a rule does not get younger because its guardrail is corrected.

## What was not touched, and why

| Line | Why it stays as is |
|---|---|
| The "Mode" line, "What this repo does", the table of commands | Right, short, and the three commands pass |
| What leaves a service is declared in `contracts/` `[2024-06]` | It is two years old and it is true: the schemas are strict, the two `test_contract.py` guard it. Age is not a reason for removal |
| A contract change is additive `[2026-05]` | The rule is good and its incident is real. Only its guardrail mention was false |
| A consumer is idempotent `[2025-11]` | An incident with figures, and a guardrail that holds: the test bus delivers twice, a faulty consumer fails its own tests. Nothing to shorten, it fits on one line |
| The two Forbidden lines | Neither can be discovered by reading the code, and the first has its incident |
| `services/billing/AGENTS.md` | Two rules specific to the service, guarded by `test_ledger.py`, consistent with the root. Moving them up to the root would load them at every session for nothing |
| `CLAUDE.md` | It is already the stub |

## What step 1 did not add
- Neither a Maintenance section, nor a harvest marker, nor a Working process, nor a task contract: those are the next steps.
- Nothing from `CONTRIBUTING.md` (PEP 8, docstrings): a model does it without being told.
- Not the `tools/replay.py` command of the README: the script no longer exists.
- No new rule. The leak of the additive rule is not closed in this file: it takes a test that replays a consumer, or a check that compares a schema to the one on `main`. It is the first of the next steps, not one more line.
