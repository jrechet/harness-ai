# Planted traps — node-front (shopfront)

A Vue 3 front end whose team went further than java-back: a short AGENTS.md with a mode, justified rules and "Enforced by", a CLAUDE.md stub, a Maintenance section, the `rule:` convention, one task contract, a custom eslint rule, stylelint, size-limit, husky. It is at **level 1**. The traps are those of a harness that looks healthy: contradictions between what is declared and what runs.

| Id | Where | What | Expected from harness-audit | Expected from `harness status` |
|---|---|---|---|---|
| T1 | `AGENTS.md:3` vs `.github/workflows/agent-fix-i18n.yml` | Declared mode **assistance** while an agent runs alone every morning, opens a PR and merges it with auto-merge and no review: that is delegation in fact | Raise the contradiction and apply the delegation scale; P1 | `L4.mode` fails (assistance) |
| T2 | `.github/workflows/agent-fix-i18n.yml:22-24` | `gh pr merge --auto` on the agent's PR: an L4 action with no human stop point, with a bot token | BLOCK, P1 | — |
| T3 | `AGENTS.md:17` | "Every visible string goes through `t()`", declared "Enforced by: scripts/check-i18n.mjs". **False**: the script only compares the keys of the two locales, it reads no template. `NewBadge.vue:6` breaks the rule and nothing sees it | A lying guardrail to unmask: PUSH_DOWN to an eslint rule (`@intlify/vue-i18n/no-raw-text`), P2 in assistance, P1 if the delegation scale is retained (T1); must **not** appear in `guarded_rules` | `L3.guarded` counts 3 enforced rules: the measurement is blind to this lie, that is the audit's job |
| T4 | `scripts/check-i18n.mjs` + `scripts/i18n-report.mjs` | Same `flatten`, same reading of the locales, two scripts | MERGE, P2 or P3 | — |
| T5 | `AGENTS.md:19` (story optional) vs `.claude/skills/add-component/SKILL.md:9` (story mandatory) | The "Adding a component" procedure is duplicated in AGENTS.md and **diverges** from the contract | Internal consistency: P2; AGENTS.md keeps only a pointer (INLINE of the procedure) | — |
| T6 | `.github/copilot-instructions.md`, `.cursor/rules/vue.mdc` | Two instruction files that do not point to AGENTS.md and contradict it (Options API tolerated, hex tolerated, story optional) | Single source broken: PUSH_DOWN to stubs, P2 | `L1.single_source` only looks at CLAUDE.md: passes. The status does not see this drift, the audit does |
| T7 | `AGENTS.md:52` | Harvest marker of 2026-07-12: the loop is installed but no longer runs | Maintenance clause present but inert, P3 | `L2.marker_fresh` fails (120 days) |
| T8 | `.claude/skills/add-component/SKILL.md:13` | "Open the coverage report and check that the percentage has not gone down": the rule "coverage does not go down" (`AGENTS.md:20`) is narrated, no threshold in `vitest.config.ts`, no CI job | PUSH_DOWN to Vitest's `coverage.thresholds` or a PR check, P2 | — |
| T9 | `scripts/legacy-theme-migrate.js` | One-shot migration of 2024, no caller | BLOCK (dead), P3 | — |
| T10 | `AGENTS.md:22-23` | "PascalCase", "prefer const": conventions a model already applies | INLINE or removal, P3; **never** in `process_leaks` | — |
| T11 | `AGENTS.md:18` | "Composition API only": in fact enforced by `vue/component-api-style` in `eslint.config.js:11`, but the rule does not say so | An existing guardrail that is not declared: to list in `guarded_rules`, the rule to shorten; P3 | — |
| S1 | `tools/eslint-plugin-design-tokens/index.js` + `.stylelintrc.json` | The rule "no hard-coded color" has its two guardrails, declared correctly | KEEP; in `guarded_rules` | `L3.ci` passes |
| S2 | `.github/workflows/deploy-preview.yml` | Preview per PR under `environment: preview`, comments the URL | KEEP | — |
| S3 | `size-limit` (`package.json`, `ci.yml` job size) | Bundle budget checked in CI, declared "Enforced by" | KEEP; in `guarded_rules` | — |
| S4 | `AGENTS.md` sections Forbidden, Maintenance, `rule:` | The right reflexes are there | Cite them as strong points, not as findings | `L1.forbidden`, `L2.maintenance`, `L2.rule_convention` pass |

## Measured bias
Words forbidden in `process_leaks`: PascalCase, const, useXxx. A declared guardrail must be checked: `scripts/check-i18n.mjs` must not be attributed to the `t()` rule in `guarded_rules`; it legitimately guards the parity of the keys.

The first blind run also showed that the "healthy" eslint plugin only visited the `<script>`: the fixture was fixed (`defineTemplateBodyVisitor`) so that S1 is really healthy. Same for husky and stylelint, whose dependencies were missing.

## What a good audit says on top
- The "cut the agent" test bears here on the "add a component" process and on the automatic translation. It **fails**: coverage and hard-coded strings are checked nowhere, and translation only goes through the agent.
- The audit must say that the mode to retain is delegation as long as `agent-fix-i18n.yml` exists, or recommend disabling it to stay in assistance.

## Revisions
- 2026-11-17: translated into English; the original French version is in git history. The sample project's files keep their names and their line numbers; the app's French locale (`repo/src/locales/fr.json`) stays French, it is product data. The hard-coded string of `NewBadge.vue:6` is now "New". In `runs/2026-11-09-init-blind`, `compte-rendu.md` became `report.md`, and `diff.patch` was regenerated against the translated project (same changes, new blob ids). The answer key's words follow: `couverture` → `coverage`, `chaîne` → `string`, `préfère const` → `prefer const`.
