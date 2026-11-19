## Report — harness-init on `comptoir`

### The map, updated
```
✓ 1 Framed     the agent knows the project, its rules and what it must never do   ← you are here
· 2 Looped     review remarks become rules, so the same mistake is not made twice
· 3 Verified   mandatory rules are enforced by tools, not just written down
· 4 Delegated  whole tasks go to the agent and come back clean
```
This repository was already framed: a short, hand-written `AGENTS.md` with a mode line, dated rules and a Forbidden section. This run **did not rewrite it** — you asked us not to. It verified every rule against the code, the CI and the docs, and corrected the four lines that no longer told the truth. Still level 1, 5/5 checks, no broken reference.

### Before and after
| | Before | After |
|---|---|---|
| Level | 1 (Framed), 5/5 | 1 (Framed), 5/5 |
| Lines loaded / session (root) | 28 | 24 |
| Rules (root) | 7 | 5 |

The interview was answered in advance (delegation; forbidden = broker/guardrail/invoice; Claude Code only; GitHub Actions `test`+`boundaries` block). I did not re-ask.

### Files modified
- `AGENTS.md` (root) — 28 → 24 lines. Two rules corrected, two removed. No other change.

Not touched (verified correct as-is): `CLAUDE.md` (already the `@AGENTS.md` stub), `services/billing/AGENTS.md` (both rules confirmed by `test_ledger.py`).

Not created: `.github/copilot-instructions.md`, `.cursor/rules/agents.mdc` — tools are **Claude Code only**, so no stub for absent tools.

### Removed, by reason
- **Harmful / outdated** — "Before opening a PR, run `grep … services\.` and review each line by hand… it is the only check of the previous rule." Hand review stopped being the check in August 2026; `tools/check_imports.py` in job `boundaries` now blocks (ADR 0001, update 2026-08-04, and your answer). The line told the agent to do redundant manual work on a false premise.
- **Outdated** — "An event weighs less than 64 KB…" The 64 KB cap was the old shared plan; since the dedicated cluster (March 2025) the platform accepts 8 MB and **refuses beyond with an error**. You said remove it. The original rule existed because the old failure was *silent*; the new one is loud, so the agent finds out on its own — no replacement line needed.

### Rules corrected (attribution was wrong)
- **"A contract change is additive"** — was labelled `Enforced by: services/orders/test_contract.py`. It is not: that test compares the provider to the *current* schema, so a rename done in both the schema and the provider stays green — this is exactly what the 12 May 2026 postmortem concluded ("review is the only check"). Changed to `(unverified)`, with that sentence spelled out. This was false confidence: the agent would have trusted CI to catch a rename it cannot catch.
- **"A service never imports another service"** — was `(unverified)`, but `tools/check_imports.py` (job `boundaries`) has enforced it since 2026-08. Upgraded to `Enforced by: tools/check_imports.py (job boundaries, since 2026-08)`. Original date `[2024-06]` kept.

### Rules kept and verified (5)
| Rule | Status | Date | Checked by me |
|---|---|---|---|
| Contract is strict, nothing undeclared leaves | Enforced by `orders/test_contract.py`, `billing/test_contract.py` + `tools/schema.py` | 2024-06 | ✓ tests assert it; `additionalProperties:false` in schemas |
| Contract change is additive | (unverified) — review only | 2026-05 | ✓ confirmed test does **not** catch rename (postmortem) |
| Replaced field stays, `"deprecated": true` | (unverified) | 2026-09 | ✓ `schema.py` allows the annotation; nothing enforces "stays" |
| Every change logged in `contracts/CHANGES.md` | (unverified) | 2026-09 | file absent by design (no contract changed yet) — not a broken pointer |
| Consumers are idempotent | Enforced by `shared/bus.py` (`deliveries=2`) | 2025-11 | ✓ bus delivers twice; all bus-tests replay it |
| No cross-service import | Enforced by `tools/check_imports.py` / `boundaries` | 2024-06 | ✓ ran it, exit 0; read the checker |

Forbidden (2) kept as-is: broker pointed at preprod/prod, and weakening a guardrail. Your third forbidden — modifying an issued invoice — is already carried, with a guardrail, in `services/billing/AGENTS.md` (`Invoice` frozen, `test_ledger.py`); I left it there rather than duplicate it at the root.

### Commands
- **Confirmed** (ran them): full suite `python3 -m unittest discover` → **61 tests OK**; `python3 tools/check_imports.py` → exit 0. The three rows of the "what to run" table all match jobs `test` / `boundaries`.
- **`harness commands`**: no surprising command. The only CI command is `python -m unittest`, which the ecosystem lets you guess — so it earns no extra line. Nothing dropped.
- **Not confirmed**: `docker compose up` (no Docker here) — left as-is in README, not promoted into AGENTS.md.

### Secrets
None. The one match, `BROKER_URL: amqp://broker:5672` in `docker-compose.yml`, points at the local compose broker, not a real host — not a secret. No keys, tokens or passwords anywhere in the instruction files or config.

### Questions for the owner
1. **`README.md` line 15 points at a tool that no longer exists** — `python3 tools/replay.py order.created`. You confirmed `replay.py` was removed after the January incident and the README never followed. Worse than stale: it tells a reader to replay events from a workstation, which is the exact move your top Forbidden line prohibits. Out of this skill's scope (it only writes AI-instruction files), so I did not edit the README. Proposed default: delete that line and the "Replaying events" idea from the README. Want me to?
2. **Rule 2 is now an acknowledged debt.** "A contract change is additive" has no test behind it — review is the only check, and the May incident is precisely a review miss. In delegation that debt gets skipped roughly one PR in ten. The natural fix is a level-3 guardrail (a schema-vs-previous-version check, or replaying a consumer against the real published event). Nothing to do now unless you want to aim there.

### What comes next (not done)
Level 1 is a place you can stay. The CLI's suggested next step is **level 2, Looped** — add a short "Maintaining this file" section and the `rule:` review convention, so a review remark becomes a dated rule instead of being lost. That asks for a review habit and a few weeks of real signals, not more writing today. If you want it, `harness target 2` and the `harness-step` skill lead it. Given question 2 above, level 3 (enforce the additive rule with a tool) may matter more to you than level 2 — your call on which to aim at.