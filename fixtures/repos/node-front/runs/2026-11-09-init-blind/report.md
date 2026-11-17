# Report — harness-init on shopfront

Branch `develop`, commit `4cfe037` (author owner). Date: 2026-11-09.

## Level reached according to `harness status`

**Level 1 "Framed": 5/5.** Level 2: 2/4, level 3: 2/4, level 4: 3/5.

Remaining checks:
- L2: no harvest for less than 45 days (marker of 2026-07-12, PR 231, with no `harvest.json` facing it); no known S1–S4 signal. harness-harvest is not installed in this repo: collecting the `rule:` comments is manual until then.
- L3: 30% of rules "Enforced by" according to the CLI (it counts the 4 Forbidden items among the rules: 3/10; on the Rules section alone, 3/6); the audit has 2 open P1.
- L4: the "cut the agent" test fails (5 leaks); no harvest to judge the agents' PRs.

## Files created or changed

| File | Action | Lines |
|---|---|---|
| `AGENTS.md` | merged (44 → 51) | 51 |
| `CLAUDE.md` | unchanged (already the `@AGENTS.md` stub) | 1 |
| `.github/copilot-instructions.md` | replaced by the template's stub (8 → 1) | 1 |
| `.cursor/rules/vue.mdc` → `.cursor/rules/agents.mdc` | renamed, content replaced by the template's stub (8 → 5) | 5 |
| `.claude/skills/add-component/SKILL.md` | completed (14 → 24) | 24 |
| `.harness/state.json` | created by `harness status` | 353 |
| `.harness/audit.json` | created (gate) | 70 |
| Deliberately not touched | `agent-fix-i18n.yml`, `scripts/legacy-theme-migrate.js`, `NewBadge.vue`: substantive findings → next steps and Questions | — |

Full audit report: `/tmp/claude-0/-home-user/c9c9c05e-e8c6-5b39-9449-fc2d7f51c43b/scratchpad/init-merge-eval/audit.md`.

### What was kept, moved, removed, file by file

**AGENTS.md** (44 lines, assistance mode)
- Kept: the commands → CI table (completed with a `build && size` line, and the locale line says what `check:i18n` really checks); the rules on colors (#212), `t()` (#198), story + test, coverage (#240), 250 kB bundle; the three Forbidden items; the Maintenance section; the existing harvest marker (not changed: resetting it to today would have faked a harvest).
- Changed: mode → **delegation**; `t()` rule requalified **(unverified)** — the old file attributed it to `check-i18n.mjs`, which only compares the fr/en keys (`scripts/check-i18n.mjs:2`) and `NewBadge.vue:6` breaks it with a green CI; `<script setup>` rule marked **Enforced by** `eslint.config.js:11` (`vue/component-api-style`), which the file did not say; the two other unverified rules name their target.
- Removed: "PascalCase / useXxx" and "prefer const" (noise: the model does it on its own); the stack in "What this repo does" (discoverable); the "Adding a component" section (it duplicated the skill and contradicted it: story "optional" here, "mandatory" in the skill — settled for mandatory, consistent with the rule and its reason).
- Added: Forbidden item "no agent PR merged without human review" (the owner's request); "Working process" section (mandatory in delegation); "Delegated tasks" section (`add-component`, and the state of the i18n workflow); maintenance clause completed (six months, Mode line = severity).

**CLAUDE.md** — kept as is.

**.github/copilot-instructions.md** (8 lines) — everything removed, replaced by the stub. The six lines contradicted AGENTS.md: Options API "fine", hex "acceptable", stories "optional", hard-coded text "acceptable in admin pages" (the opposite of incident #198), `npm test` (a script that does not exist). The only compatible point ("do not touch payment") is already in AGENTS.md.

**.cursor/rules/vue.mdc** (8 lines) — everything removed, file renamed `agents.mdc` with the stub. Same contradictions: Options API tolerated under 50 lines, hex tolerated with `// TODO token`, story optional.

**.claude/skills/add-component/SKILL.md** (14 lines)
- Kept: the seven steps, the mandatory story and its reason, the two locales, `check:i18n`.
- Changed: step 6 ("open `coverage/index.html`", not doable by an agent) → compare the "All files" line of the text report with `develop`; step 4 says that `check:i18n` does not read the template; step 5 adds `lint:style`; step 7 targets `develop`, with no auto-merge, and replaces "screenshot of the story" with the states covered.
- Added: stop cases (new token → design ticket; `src/payment/`); "Done when" (five green jobs, story + test, locales, coverage, human approval).

## Secrets found

None. The only occurrences of `token`/`secret` are `${{ secrets.* }}` in the workflows, held in L4. Nothing to regenerate.

## Mode retained and why

**Delegation**, chosen by the owner: "we already have a workflow that runs an agent at night for the translations, we may as well own it". Consequence: rules narrated with no guardrail are P1 at the audit, the "Working process" section and one contract per task are mandatory.

## Rules written and their status

| Rule | Status |
|---|---|
| No hard-coded color, tokens only (#212) | enforced by `tools/eslint-plugin-design-tokens` (`no-raw-color`) + stylelint `color-no-hex` |
| `<script setup>` only | enforced by eslint `vue/component-api-style` (`eslint.config.js`) |
| Initial bundle < 250 kB gzip | enforced by `size-limit` (`package.json`, job `size`) |
| Every visible string goes through `t()` (#198) | **unverified** — target: eslint `vue/no-bare-strings-in-template` |
| A component has a story and a test | **unverified** — target: a script checking the pairs in the lint job |
| Unit coverage does not go down (#240) | **unverified** — target: `coverage.thresholds` in `vitest.config.ts` |

Forbidden (4): `src/payment/`; `tokens.css` without a ticket; an agent's PR without human review; `eslint-disable` without a dated justification. None has an L4 guardrail (no CODEOWNERS, no known branch protection).

## Commands

Confirmed (run here): `node scripts/check-i18n.mjs` → "i18n OK (3 keys)", exit 0; `node scripts/i18n-report.mjs` → `[]`, exit 0; `python3 harness.py status`.

**Not confirmed** (no `node_modules`, npm impossible): `npm run lint`, `npm run lint:style`, `npm run test:unit`, `npm run test:e2e`, `npm run build`, `npm run size`. Assumption taken without asking: they stay in AGENTS.md because they exist in `package.json` and `ci.yml` runs exactly those.

## Result of the gate (harness-audit)

- Health score **16/100**, "cut the agent" test **FAILED** (5 leaks), **2 P1**, 4 P2, 1 P3. 22 items inventoried. JSON in `.harness/audit.json`, taken into account by `harness status` (view per layer: L2 9 of which 4 misplaced, L3 10 of which 2, L4 2, MIXED 1).
- Structural findings fixed during the init: length (51 < 60), noise removed, duplicate of the skill removed, consistent stubs, maintenance clause, each unverified rule names its target.
- Remaining P1, not fixable in the init:
  1. `agent-fix-i18n.yml:21-22` automatically merges the bot's PR (`gh pr merge --auto`), in direct contradiction with the owner's Forbidden item; on top of that it targets `.[0]` of the bot's PRs (not necessarily its own) and gives `Edit` with no restriction (`:19`).
  2. The `t()` rule has no guardrail and `NewBadge.vue` breaks it today.

## Three next steps

1. **Push the first unverified rule into CI**: turn on `vue/no-bare-strings-in-template` in `eslint.config.js` and fix `NewBadge.vue` ("New" → `t()`), then shorten `AGENTS.md:22` to "Enforced by".
2. **Remove the "Auto-merge when green" step** from `agent-fix-i18n.yml` and lay `.github/CODEOWNERS` (`src/payment/`, `src/styles/tokens.css`) with required review on `develop`; move the inline prompt out into `.claude/skills/fix-i18n/SKILL.md`. If the GitHub default branch is not `develop`, the scheduled workflow must get there too, otherwise it is inert.
3. **Coverage thresholds** in `vitest.config.ts` at the level measured by a first `npm run test:unit`, then remove step 6 of the skill; while at it, `scripts/check-components.mjs` in the lint job for the story + test rule.

## Questions

1. Remove the auto-merge step of `agent-fix-i18n.yml` (lines 21-23) right now? I did not do it: the skill reserves workflow changes for an approved remediation step. Proposed default: yes, in the next PR, it is the direct consequence of your Forbidden item.
2. Delete `scripts/legacy-theme-migrate.js` (no caller, CommonJS in an ESM package)? Proposed default: yes.
3. What is the default branch on GitHub? If it is not `develop`, the nightly workflow and this commit must be carried onto it. Proposed default: I assume `develop` as long as you do not say otherwise.
