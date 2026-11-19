Done. The repository was already at level 1 with a solid hand-written AGENTS.md, so this run was the line-by-line cleanup the skill prescribes for an existing file — not a rewrite. Here is the report.

---

# Harness init — report for `comptoir`

## The map, updated
```
✓ 1 Framed     the agent knows the project, its rules and what it must never do   ← you are here
· 2 Looped     review remarks become rules, so the same mistake is not made twice
· 3 Verified   mandatory rules are enforced by tools, not just written down
· 4 Delegated  whole tasks go to the agent and come back clean
```
This run did **not** create the file — it already existed and was good. It corrected one rule, removed two dead lines, and confirmed the guardrails actually block. The repository stays at level 1, now with no stale lines. No target level chosen yet; level 1 is a place you can stay.

## Before and after
| | Before | After |
|---|---|---|
| Level | 1 (5/5) | 1 (5/5) |
| AGENTS.md lines loaded per session | 27 | 25 |
| Rules | 8 | 6 |
| Enforced rules | 3 | 4 |

(`services/billing/AGENTS.md`, 6 lines, loads on demand when billing is touched; unchanged.)

## Files modified
- `AGENTS.md` (27 → 25 lines): one rule corrected, two removed.

Nothing else created. **No Copilot or Cursor stubs** — you run Claude Code only, so they would be noise. `CLAUDE.md` was already the correct `@AGENTS.md` stub.

## Removed, by reason
- **Outdated — "An event weighs less than 64 KB"** (harmful today). The 64 KB silent-cut was the old shared plan; since the March 2025 dedicated cluster the platform accepts 8 MB and errors cleanly beyond. You confirmed: remove. The incident's premise ("cuts with no error") no longer holds, so keeping it would make the agent design around a constraint that is gone.
- **Outdated — "Before opening a PR, run `grep … services\.` and review each line by hand."** The hand review stopped in August 2026; `tools/check_imports.py` in the blocking `boundaries` job is now the check. The line even justified itself as "the only check of the previous rule" — which became false. Removing it also lets the rule above it stop being `(unverified)`.

## Rule corrected
- **"A service never imports another service's code"** was marked `(unverified)`. It is in fact enforced: `tools/check_imports.py` (I read it — it flags both service→service and shared/tools→service imports) runs in the `boundaries` job, which blocks merge. Changed `(unverified)` → `Enforced by: tools/check_imports.py (job boundaries)`. Date kept at `[2024-06]`.

## Rules as they now stand
| Rule | Status | Date |
|---|---|---|
| Only `contracts/` leaves a service, strictly | Enforced: `test_contract.py` ×2 + `tools/schema.py` | 2024-06 |
| Contract change is additive | Enforced: `services/orders/test_contract.py` | 2026-05 |
| Replaced field stays, gets `"deprecated": true` | (unverified) — external agreement, no in-repo check possible | 2026-09 |
| Every contract change logged in `contracts/CHANGES.md` | (unverified) — external agreement; file not created yet (no change since) | 2026-09 |
| Event consumers are idempotent | Enforced: `shared/bus.py` delivers twice in all tests | 2025-11 |
| No cross-service imports | Enforced: `tools/check_imports.py` (job `boundaries`) | 2024-06 |

The two `(unverified)` rules are a real debt under delegation (they will be skipped one day in ten), but no tool can carry a promise made to teams outside this repo. Left as-is, dated, with the reason in the line.

## Commands
- **Confirmed (ran, green):** `python3 -m unittest discover` → 61 tests OK · `python3 tools/check_imports.py` → exit 0. Both block in CI (`test`, `boundaries`).
- **`harness commands`:** no surprising command — the CI runs the obvious `python -m unittest`, nothing to write.
- **Not confirmed:** `python3 tools/replay.py order.created` — see question 1.

## Secrets
None found in the instruction files, CI, or config. `BROKER_URL` is read from the environment (`shared/bus.py`), never hard-coded; the broker client lives in the base image, not the repo.

## Forbidden
Left unchanged (both verified against their sources): the `BROKER_URL` preprod/prod ban and "weakening a guardrail to make a test pass" (`.github/CODEOWNERS` has the platform team review `tools/`, `shared/`, `.github/`, `contracts/`). Your third forbidden — **modifying an issued invoice** — is already written where it belongs: `services/billing/AGENTS.md` carries it as a rule *enforced by* `services/billing/test_ledger.py`. I did not duplicate it at the root; it is billing-specific and already guarded.

## Questions for the owner
1. **README cites a removed tool.** `README.md:14` still lists `python3 tools/replay.py order.created`, but `replay.py` was removed after the January incident and the file is gone. *Why asked:* it is a stale command a newcomer or agent will try and fail on. *Proposed default:* delete that line from the README (I left the README untouched — it is outside this step's instruction-file scope, and you said "the README did not follow"). Confirm and I'll remove it.
2. **The two external-agreement rules** (deprecated-field annotation, `contracts/CHANGES.md`) remain `(unverified)` with no possible in-repo guardrail. *Why asked:* under delegation an unverified rule is a debt. *Proposed default:* keep them — the agreement with the accounting-export and data-warehouse teams is real and nothing in-repo can enforce it. No change needed unless you disagree.

## What comes next (not done)
Level 1 is a resting place, and for a five-person team reviewing PRs it is often enough. If you later want the file to **keep itself up to date** — review remarks turning into rules instead of being re-explained — that is level 2 (Looped): a short "Maintaining this file" section plus the `rule:` review convention, and a few weeks of real reviews before it means anything. You decide with `harness target`, and `harness-step` leads it. I have not started it; you asked for nothing beyond framing.