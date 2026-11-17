# Blind run of harness-init on an already instrumented repo — 2026-11-09

The most frequent case in practice: the repo already has an AGENTS.md, stubs that diverge, a contract. Copy of node-front as is, branch `develop`. Interview answers: delegation ("we already have a night agent, we may as well own it"), 4 devs, GitHub Actions + in-house eslint + stylelint + size-limit + husky "and an i18n script, I no longer know what it checks", Claude Code + Copilot + Cursor, first task "add a component, we have a skill but I do not know whether it is good", forbidden: `src/payment`, tokens without a ticket, an agent's PR without human review.

Result: level 1 **5/5**, AGENTS.md 44 → 51 lines merged and not overwritten, Copilot and Cursor brought back to stubs, `add-component` contract completed, `.harness/` committed. See `diff.patch`.

What it did with the fixture's traps, without knowing them:

| Trap | What the init did with it |
|---|---|
| T1 mode contradicted by the night agent | Delegation owned; new Forbidden item "no agent PR merged without human review"; `agent-fix-i18n.yml` BLOCK P1 at the audit |
| T3 lying "Enforced by" | `t()` rule **requalified** (unverified) after reading `check-i18n.mjs`; the script is only credited with the parity of the keys; `NewBadge.vue:6` cited as a violation |
| T5 duplicated procedure that diverges | Section removed from AGENTS.md, story **mandatory** settled in the contract |
| T6 diverging Copilot and Cursor | Replaced by the template's stubs, six contradictions listed in the report |
| T7 stale marker | **Kept as is**, "so as not to fake a harvest": the right reflex, now in the skill |
| T8 narrated coverage | Requalified (unverified), target `coverage.thresholds` |
| T10 noise | Removed (PascalCase, `const`) |
| T11 `<script setup>` guarded by eslint without saying so | Moved to "Enforced by: eslint.config.js" |

Its gate audit against the traps: 6/7; the only gap is T6, which the init had just fixed, so KEEP is the right verdict. No notable weakness; the three questions it asked at the end of the report (remove the auto-merge, delete the dead script, default branch) are exactly those an owner must settle.
