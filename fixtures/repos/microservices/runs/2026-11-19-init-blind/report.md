The file is complete and sound (26 lines). Here is the report.

---

## Harness init — report for `comptoir`

### The map, updated
```
✓ 1 Framed     the agent knows the project, its rules and what it must never do   ← you are here
· 2 Looped     review remarks become rules, so the same mistake is not made twice
· 3 Verified   mandatory rules are enforced by tools, not just written down
· 4 Delegated  whole tasks go to the agent and come back clean
```
This run did **not** add a level. The repository already had a hand-written, level-1 AGENTS.md; the work was to sort it line by line against the repo's own docs and your answers — correct two enforcement claims, remove two dead lines — and remove one dangerous line from the README. It stays at level 1, Framed, now without false guarantees.

### Before and after
| | Before | After |
|---|---|---|
| Level | 1 (5/5) | 1 (5/5) |
| AGENTS.md | 28 lines | 26 lines |
| Lines loaded per session (root) | 28 | 26 |
| Rules | 8 | 6 |
| Forbidden | 2 | 2 |

### Files modified
- `AGENTS.md` (26 lines) — two enforcement corrections, two removals.
- `README.md` (−1 line) — removed the `tools/replay.py` command.

Not created: `.github/copilot-instructions.md`, `.cursor/rules/agents.mdc` — you declared **Claude Code only**. `CLAUDE.md` already exists as a correct `@AGENTS.md` stub, left as is. Nothing created by this run that wasn't asked for.

### Removed, by reason
- **Harmful** — *"Before opening a PR, run `grep -rnE …` and review each line by hand … it is the only check."* The manual grep stopped being the check on 2026-08-04: `tools/check_imports.py` runs in the blocking `boundaries` job (ADR 0001 update; you confirmed "not since August"). The line told the agent to do obsolete work and made a false claim about where the check lives.
- **Outdated → you confirmed removal** — *"An event weighs less than 64 KB …"*. That was the former shared plan. Since the dedicated cluster (March 2025) the platform accepts 8 MB and refuses beyond with an error. You said: remove it.
- **README, harmful** — `python3 tools/replay.py order.created`. The tool was removed after the January incident ("the README did not follow"); worse, it pointed at exactly the forbidden action (a workstation replay — the 9 Jan 2026 incident, 3,100 re-sent emails). Both nonfunctional and dangerous, so removed.

### Rules written (final 6), status and date
1. Contracts are strict, nothing undeclared leaves a service — **Enforced by** `test_contract.py` + `tools/schema.py` (job `test`, blocks). [2024-06] — *verified: ran the suite, the "undeclared field" test fails as intended.*
2. A contract change is additive — **downgraded to (unverified)**. The previous file claimed `test_contract.py` enforced this; the repo's own post-mortem proves it does **not**: the May 2026 rename changed schema and provider together and the test stayed green. Review is the only check. [2026-05]
3. A replaced field stays published with `"deprecated": true` — (unverified), external agreement. [2026-09]
4. Every contract change logged in `contracts/CHANGES.md` — (unverified); file doesn't exist yet (no change since). [2026-09]
5. Event consumers are idempotent — **Enforced by** `shared/bus.py` (delivers twice in all tests). [2025-11] — *verified in `bus.py`: `deliveries=2` default.*
6. No service imports another service — **upgraded to Enforced by** `tools/check_imports.py` (job `boundaries`, blocks) since 2026-08-04; was `(unverified)`. [2024-06] — *verified: ran it (exit 0) and read it — it really parses imports; manual grep shows only self-imports.*

Forbidden (both kept, both verified against `operations.md` / `CODEOWNERS`): workstation/agent `BROKER_URL` at preprod/prod; weakening a guardrail to pass a test.

### Commands
- **Confirmed** (ran them): `python3 -m unittest discover` (61 tests, OK); `python3 -m unittest discover -s services/<name> -t .`; `python3 tools/check_imports.py` (exit 0).
- **Not confirmed**: `tools/replay.py` — gone; removed from README.
- `harness commands` found **0 surprising candidates**: the CI runs the obvious `python -m unittest`. Nothing to add.

### Questions for the owner
1. **"Modifying an issued invoice" as a root Forbidden?** You listed it among the three forbiddens, but it lives in `services/billing/AGENTS.md` as a rule enforced by `test_ledger.py`, and it only ever applies inside billing. I left it there (loaded on demand when working in billing) rather than duplicate it at the root. *Default: leave as is.* Say if you'd rather it also sit in the root Forbidden for visibility.
2. **The additive-contract gap (rule 2).** Your post-mortem's "what remains open" is still open: no test compares a schema to its previous version, and `billing`/`notifications` build their test events by hand without validating against `contracts/`. I marked the rule `(unverified)` to stop it from reading as safe, but the underlying hole remains. *This is exactly what a level-3 step would close (a schema-diff or consumer-contract check).* Flagging it; not acting on it here.

### What comes next (not done)
Level 1 is a place you can stay — in delegation it's the floor, not the ceiling. The natural next step is **level 2, Looped**: a short "Maintaining this file" section plus the `rule:` review convention, so a review remark becomes a dated rule instead of being repeated. It asks for a review habit and a few weeks of real signal, not more writing today. You decide with `harness target <n>`; `harness-step` leads it. Given the real gap in question 2, **level 3** (push rule 2 onto an actual check) is the higher-value direction when you're ready.