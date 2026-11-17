Level 1 is in place and the CLI gate passes: level 1, 5 checks out of 5, no reference without a target. Your AGENTS.md was already in the right format. I only corrected what was wrong or outdated, with 4 lines added and 5 removed. Nothing is committed.

A few commands were blocked because nobody could approve them in this session. I ran them again one by one, except one: `tools/replay.py` was not run, and the file does not exist in the repository.

## Before and after
| | Before | After |
|---|---|---|
| Level | 1 (5/5) | 1 (5/5) |
| Lines loaded per session | 26 + 1 (`CLAUDE.md`) | 25 + 1 |
| Rules / Forbidden | 7 / 2 | 5 / 3 |
| Rules said to be enforced | 3, 1 of them wrongly | 3, all with a guardrail I saw block in CI |

## Files
- `AGENTS.md` modified (25 lines).
- `.harness/state.json` created by `harness status`.
- `CLAUDE.md` (`@AGENTS.md`) and `services/billing/AGENTS.md` were already correct, I did not touch them.
- No Copilot or Cursor stub, since you only use Claude Code.

## Removed
- **Outdated, you confirmed it**: the 64 KB rule. It came from the shared plan of the former hosting provider. The dedicated cluster has accepted 8 MB since March 2025 and returns an error beyond that.
- **Harmful**: "run `grep … services\.` and review each line by hand". It has no longer been the check since August 2026: `tools/check_imports.py` runs in the `boundaries` job, which blocks (I ran it: 0 violations).

## Corrected, because it was wrong
- **Rule "additive contract change"**: it was marked `Enforced by: services/orders/test_contract.py`. That is wrong, and your own post-mortem of May 2026 says so: this test stays green when the schema and the provider change together. It becomes `(unverified)`, with what is missing:
  - the tests of `billing` and `notifications` make their events by hand, without validating them against `contracts/`;
  - the accounting export and the data warehouse are tested nowhere in this repository.
- **Rule "no import between services"**: it was marked `(unverified)`. It becomes `Enforced by: tools/check_imports.py (job boundaries)`, and keeps its original date [2024-06].
- **Forbidden "weakening a guardrail"**: the justification said that `.github/CODEOWNERS` has all these guardrails reviewed by the platform team. In reality this file covers only `tools/`, `shared/`, `.github/` and `contracts/`. A `deliveries=1` added in a service's test has no designated reviewer. I corrected the sentence.

## Added
- **Forbidden "modifying an issued invoice"**, which comes from your answer to the interview. It points to `services/billing/AGENTS.md`, and is dated [2025-11].

## Secrets
None found (search for API keys, tokens and passwords across the whole repository).

## Rules written
| Rule | Status | Date |
|---|---|---|
| Strict schemas | Enforced by `test_contract.py` (orders, billing) and `tools/schema.py` | 2024-06 |
| Additive contract change | Unverified | 2026-05 |
| Replaced field marked `"deprecated": true` | Unverified | 2026-09 |
| Idempotent consumer | Enforced by `shared/bus.py` (job `test`) | 2025-11 |
| No import between services | Enforced by `tools/check_imports.py` (job `boundaries`) | 2024-06 |
| Forbidden: `BROKER_URL` at preproduction or production | Forbidden | 2026-01 |
| Forbidden: weakening a guardrail | Forbidden | 2025-11 |
| Forbidden: modifying an issued invoice | Forbidden | 2025-11 |

The `deprecated` rule is the only one written nowhere else, I kept it as is. Your answer to the interview adds no new "unwritten" fact.

## Commands
- **Confirmed**:
  - `python3 -m unittest discover`: 61 tests OK;
  - `python3 -m unittest discover -s services/<name> -t .`: orders 9, billing 14, notifications 5, all OK;
  - `python3 tools/check_imports.py`: no violation.
- **Not confirmed**:
  - `python3 tools/replay.py`, still cited on line 14 of `README.md`: the file no longer exists;
  - `docker compose up`: not run.

## Questions
1. Should the `tools/replay.py` line be removed from the README? I propose yes. An agent that follows it will look for a tool removed after the January incident.
2. The first task you want to delegate (a contract change down to the consumer) is precisely the one nothing verifies. Is a guardrail needed before delegating it? I propose two checks:
   - compare each schema of `contracts/` to its version on `main`, to refuse a renaming, a removal or a type change;
   - have the consumer tests validate the events they make, against the contract.
3. Should `/services/*/test_*.py` (or at least the `InMemoryBus(` calls) be added to `CODEOWNERS`? I propose asking the platform team.
4. The "issued invoice" ban is now also at the root, on top of the `billing` note. Is that fine with you? I propose keeping it, because a script or a migration run outside `billing` could touch it too.

## The possible next step
Move to level 3 with harness-step, starting with the guardrail of the additive rule (question 2). It is up to you to run `harness target`.