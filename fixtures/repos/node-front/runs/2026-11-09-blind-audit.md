# Harness audit — shopfront: adding a component and automated translation

**Scope**: `fixtures/repos/node-front/repo/` (AGENTS.md, CLAUDE.md, `.cursor/rules`, `.github/copilot-instructions.md`, `.claude/skills/`, `scripts/`, `tools/`, `.github/workflows/`, eslint/stylelint/husky/vitest, `package.json`) · **Date**: 2026-11-09 · **Items inventoried**: 17

## 1. Summary

- **Health score**: 0 — the agent is not an accelerator but a pillar: three mandatory rules (translated strings, story + test per component, coverage) and one security ban (PCI module) live only in prompts, two of the three "Enforced by" mentions of AGENTS.md are false, and a workflow lets an agent write then merge alone into `main`. Raw deduction: 102 points (2 × P1, 6 × P2, 2 × P3), bounded at 0; the failed "cut the agent" test capped it at 60 anyway.
- **Result of the "cut the agent" test**: FAILED — 7 step(s) of the process exist only in prompts.
- **Blocking points (P1)**: 2
- **The three actions that change the most**:
  1. Neutralise `agent-fix-i18n.yml` (`.github/workflows/agent-fix-i18n.yml:18-23`): remove the auto-merge, restrict `Edit` to `src/locales/en.json`, add a `dry_run` input, target the PR actually created instead of `.[0]`.
  2. Make the sentence "Enforced by `scripts/check-i18n.mjs`" true (`AGENTS.md:18`): add `@intlify/eslint-plugin-vue-i18n` (`vue-i18n/no-raw-text`) in `eslint.config.js` — today `src/components/NewBadge.vue:6` ships a hard-coded "New" and passes every CI job.
  3. Put `src/payment/` and `src/styles/tokens.css` under `.github/CODEOWNERS` + mandatory review: the two forbidden items (`AGENTS.md:27`, `AGENTS.md:29`) have no guardrail today, and the agent of the workflow above can edit them.

## 2. Map of the harness

| # | Item | Path | Declared layer | Actual layer | Called by | Calls |
|---|---|---|---|---|---|---|
| 1 | AGENTS.md | `AGENTS.md` | L2 | L2 | CLAUDE.md (include), agent sessions | add-component skill, npm scripts, eslint-plugin-design-tokens, stylelint, check-i18n, ci.yml |
| 2 | CLAUDE.md | `CLAUDE.md` | L2 | L2 | Claude Code | AGENTS.md (`@AGENTS.md`) |
| 3 | Cursor rules | `.cursor/rules/vue.mdc` | L2 | L2 | Cursor (`alwaysApply: true`) | — |
| 4 | Copilot instructions | `.github/copilot-instructions.md` | L2 | L2 | Copilot | `npm test` (script that does not exist) |
| 5 | add-component skill | `.claude/skills/add-component/SKILL.md` | L2 | MIXED (procedure + manual coverage check) | AGENTS.md:37, Claude Code | npm scripts (`check:i18n`, `lint`, `test:unit`), coverage report |
| 6 | check-i18n | `scripts/check-i18n.mjs` | L3 | L3 | `package.json:12`, `ci.yml:25` | — |
| 7 | i18n-report | `scripts/i18n-report.mjs` | L3 | L3 | `agent-fix-i18n.yml:15` | — |
| 8 | legacy-theme-migrate | `scripts/legacy-theme-migrate.js` | L3 | L3 (dead) | nobody | — |
| 9 | eslint-plugin-design-tokens | `tools/eslint-plugin-design-tokens/index.js` | L3 | L3 (real scope: `<script>` only) | `eslint.config.js:2,8` | — |
| 10 | eslint config | `eslint.config.js` | L3 | L3 | `npm run lint` (`package.json:8`), husky, ci.yml:11 | eslint-plugin-design-tokens, eslint-plugin-vue |
| 11 | stylelint config | `.stylelintrc.json` | L3 | L3 | `npm run lint:style` (`package.json:9`), ci.yml:12 | stylelint-config-standard (absent from the devDependencies) |
| 12 | pre-commit hook | `.husky/pre-commit` | L3 | L3 (dead: husky not installed) | nobody | `npm run lint` |
| 13 | npm scripts (the repo's CLI) | `package.json:5-16` | L3 | L3 | AGENTS.md, skill, ci.yml, deploy-preview.yml, copilot | eslint, stylelint, vitest, playwright, check-i18n, size-limit |
| 14 | vitest config | `vitest.config.ts` | L3 | L3 | `npm run test:unit` | — |
| 15 | ci workflow | `.github/workflows/ci.yml` | L4 | L4 | push / pull_request | npm scripts, check-i18n, size-limit |
| 16 | agent-fix-i18n workflow | `.github/workflows/agent-fix-i18n.yml` | L4 | MIXED (L1 agent + L3 script + L4 merge) | daily cron, `workflow_dispatch` | i18n-report, `@anthropic-ai/claude-code`, `gh pr merge --auto` |
| 17 | deploy-preview workflow | `.github/workflows/deploy-preview.yml` | L4 | L4 | pull_request | `npm run build`, netlify, `gh pr comment` |

Nominal process A — adding a component:

| Step of the process | Carried by | Checked by code? | Dry-run? |
|---|---|---|---|
| Create `src/components/<Name>.vue` with `<script setup lang="ts">` | L2 (`SKILL.md:8`, `AGENTS.md:32`) | Yes — `vue/component-api-style: script-setup` (`eslint.config.js:11`), lint job (`ci.yml:11`) | n/a |
| No hard-coded color | L2 (`AGENTS.md:17`) | Partial — eslint `no-raw-color` only sees the literals of the `<script>` (`tools/eslint-plugin-design-tokens/index.js:11`); stylelint covers `<style>` if the config runs (`.stylelintrc.json:1`); the template is not covered | n/a |
| Add the story `<Name>.stories.ts` | L2 only (`SKILL.md:9`, contradicted by `AGENTS.md:33`, `vue.mdc:7`, `copilot-instructions.md:5`) | No — `NewBadge.vue` without a story passes the CI | n/a |
| Add the test `<Name>.spec.ts` | L2 only (`SKILL.md:10`, `AGENTS.md:20`) | No — `NewBadge.vue` without a spec passes the CI | n/a |
| i18n keys in both locales | L2 + L3 (`SKILL.md:11`, `scripts/check-i18n.mjs`) | fr/en parity yes (`check-i18n.mjs:13-15`, `ci.yml:25`); use of `t()` no (`check-i18n.mjs:2`) | n/a |
| `npm run lint && npm run test:unit` | L3/L4 (`package.json:8,10`, `ci.yml:11,20`) | Yes | n/a |
| Coverage does not go down | L2 only, by eye (`SKILL.md:13`, `AGENTS.md:21`) | No — no `thresholds` (`vitest.config.ts:3`), no diff in CI | n/a |
| Bundle < 250 kB gzip | L3/L4 (`package.json:16`, `ci.yml:33`) | Yes — `size-limit` | n/a |
| PR with a screenshot of the story | L2 (`SKILL.md:14`) | No (no PR template) | n/a |
| Preview deployed and commented on the PR | L4 (`deploy-preview.yml:13-15`) | Yes — `--json` output, `environment: preview` | Protected environment, no dry-run (acceptable: preview) |

Nominal process B — automated translation (`agent-fix-i18n.yml`):

| Step of the process | Carried by | Checked by code? | Dry-run? |
|---|---|---|---|
| Detect the fr keys missing from en | L3 (`scripts/i18n-report.mjs`, `agent-fix-i18n.yml:15`) | Yes — structured JSON output | n/a |
| Translate the keys | L1 (agent, `agent-fix-i18n.yml:18`) | No, and that is normal (judgment) — but no quality control downstream | No |
| Change only `src/locales/en.json` | L2 (the prompt, `agent-fix-i18n.yml:18`) | No — `--allowedTools "Edit,Bash(git *)"` with no path restriction (`:19`) | No |
| Open a PR | L1 through `gh pr create` (`agent-fix-i18n.yml:19`) | No | No |
| Human review | absent | No — contradicts `AGENTS.md:3` ("a person reviews every diff") | — |
| Merge into `main` | L4 `gh pr merge --auto --squash` on `gh pr list --author app/acme-bot … .[0]` (`agent-fix-i18n.yml:22`) | No — the only relevant CI (key parity) passes by construction once the keys are added; the targeted PR is not necessarily the one just created | No — `workflow_dispatch` with no input (`agent-fix-i18n.yml:5`) |

## 3. Leaks: rules and steps narrated with no check

| Rule / step | Narrated in | If the agent skips it | Must live in | Target tool |
|---|---|---|---|---|
| Every visible string goes through `t()`, never hard-coded text in a template | `AGENTS.md:18` (claims "Enforced by `scripts/check-i18n.mjs`", false: `scripts/check-i18n.mjs:2` "Does not look at the templates"); contradicted by `.github/copilot-instructions.md:6` | Untranslated text in production — incident #198 already happened; living proof: `src/components/NewBadge.vue:6` (a hard-coded "New") passes every job of `ci.yml` | L3 | `@intlify/eslint-plugin-vue-i18n` rules `vue-i18n/no-raw-text` and `vue-i18n/no-missing-keys` in `eslint.config.js`, existing lint job |
| A component has a Storybook story | `AGENTS.md:20` (mandatory), `SKILL.md:9` (mandatory even with no UI), but `AGENTS.md:33` (optional with no UI), `.cursor/rules/vue.mdc:7` (optional), `.github/copilot-instructions.md:5` (optional) — four answers | Component never reviewed visually; `src/components/NewBadge.vue` has no story | L3 | Script `scripts/check-components.mjs` (glob `src/components/*.vue` → requires `.stories.ts` and `.spec.ts`, `exit 1`) or an equivalent vitest test, wired into `ci.yml` |
| A component has a unit test | `AGENTS.md:20`, `SKILL.md:10`, `vue.mdc:7`, `copilot-instructions.md:5` | Untested component; `NewBadge.vue` has no spec and the CI is green | L3 | Same script as above |
| Unit coverage does not go down | `AGENTS.md:21`; manual check by eye `SKILL.md:13` ("open `coverage/index.html`") | Silent loss of tests — incident #240; `vitest.config.ts:3` has neither `thresholds` nor the `json-summary` reporter, `ci.yml:20` compares nothing | L3/L4 | `coverage.thresholds` (+ `thresholds.autoUpdate`) in `vitest.config.ts`, or a coverage diff action vs `main` as a PR gate |
| Never touch `src/payment/` (PCI module) | `AGENTS.md:29`, `.cursor/rules/vue.mdc:8`, `.github/copilot-instructions.md:6` | Change to a PCI module with no owner review; the agent of `agent-fix-i18n.yml:19` has `Edit` with no path restriction and auto-merge | L4 | `.github/CODEOWNERS` (`src/payment/ @owners`) + review required by branch protection; `Edit(src/locales/en.json)` in the workflow |
| Never change `src/styles/tokens.css` without a design ticket | `AGENTS.md:27` | Theme drift with no design validation | L4 | `.github/CODEOWNERS` (`src/styles/tokens.css @design`) + PR template asking for the ticket |
| No hard-coded color in the template (`style` attribute, `:style`, inline classes) | `AGENTS.md:17` (claims it is covered by `no-raw-color`), `tools/eslint-plugin-design-tokens/index.js:1-2` (claims "templates and inline styles") | Hex forgotten in a template → broken dark theme (incident #212, three times); the `Literal` visitor (`index.js:11`) is only called on the `<script>`, not on the template AST of vue-eslint-parser | L3 | Rewrite the rule with `context.parserServices.defineTemplateBodyVisitor` (`VLiteral`/`Literal` nodes of the template) + `RuleTester`; stylelint with `customSyntax: postcss-html` for `<style>` and `style` attributes |
| No `eslint-disable` without a dated justification | `AGENTS.md:28` | Rules bypassed silently (hygiene, P3) | L3 | `@eslint-community/eslint-plugin-eslint-comments` rule `require-description` |
| Human review of every diff | `AGENTS.md:3` | Hallucinated translations merged into `main` with no review (`agent-fix-i18n.yml:21-23`) | L4 | Remove the auto-merge step; protected `environment:` with required reviewers; branch protection |

Rules that **have** their guardrail (healthy part, can be shortened in AGENTS.md):

- Composition API `<script setup>` only (`AGENTS.md:19`) — `vue/component-api-style: ["error", ["script-setup"]]` (`eslint.config.js:11`), lint job `ci.yml:11`. The "Why" can stay, the rest becomes a pointer to the linter.
- Initial bundle < 250 kB (`AGENTS.md:22`) — `size-limit` `package.json:16` + `npx size-limit` `ci.yml:33`. Exact claim.
- Parity of the fr/en keys (`AGENTS.md:13`, `SKILL.md:11`) — `scripts/check-i18n.mjs:13-15` (`exit 1`, typed message) + `ci.yml:25`. It is the only true part of the "Enforced by" of line 18.
- No hard-coded color in the `<script>` and the `.css` files (`AGENTS.md:17`) — `design-tokens/no-raw-color` (`eslint.config.js:10`, `tools/eslint-plugin-design-tokens/index.js:11-13`) and `color-no-hex` + `function-disallowed-list` (`.stylelintrc.json:1`). Partial guard, see the leak above and the finding on `.stylelintrc.json`.
- Table "If you touch… → Enforced in CI by" (`AGENTS.md:9-14`) — exact: jobs `lint` (`ci.yml:4-12`), `unit` (`:13-20`), `i18n` (`:21-25`), `e2e` (`:34-41`).

## 3b. Context cost

| File | Lines loaded (with includes) | Share instruction / reference / noise | Loaded when |
|---|---|---|---|
| `CLAUDE.md` → `AGENTS.md` | 45 (1 + 44) | ~45% instruction (l.16-29, 39-42) / ~45% reference (l.5-14 command table, l.31-37 procedure duplicated from the skill, l.44 marker) / ~10% noise (l.23-24: PascalCase, `const`) | Every Claude Code session |
| `.cursor/rules/vue.mdc` | 8 | 100% instruction, of which 3 lines contradict AGENTS.md and the linter (l.5-7) | Every Cursor session (`alwaysApply: true`, l.3) |
| `.github/copilot-instructions.md` | 8 | ~85% instruction / ~15% reference (l.7, command `npm test` that does not exist); 4 lines contradict AGENTS.md (l.3-6) | Every Copilot session |
| `.claude/skills/add-component/SKILL.md` | 14 | 100% procedure (its place), of which step 6 is a check by eye that should be code | On demand (trigger of the description) |

Justification: a clear strong point of `AGENTS.md` — six rules out of eight explain *why* and four cite the incident or the issue (#212 l.17, #198 l.18, #240 l.21, PR #231 l.44); `vue.mdc` and `copilot-instructions.md` justify nothing. Maintenance clause present and precise (`AGENTS.md:39-42`: `rule:` comments, "look for a guardrail before adding a sentence", harvest marker l.44); absent from the two other files, which have therefore drifted.

## 4. Findings per item

### [BLOCK] [P1] agent-fix-i18n workflow — `.github/workflows/agent-fix-i18n.yml`
- **Does today**: every working day at 6 am (l.3-4) or by hand (l.5), lists the missing keys (l.15), launches `claude-code -p` to translate them and open a PR with `--allowedTools "Edit,Bash(git *),Bash(gh pr create*)"` (l.18-19), then `gh pr merge --auto --squash` on the first PR of `app/acme-bot` (l.22).
- **Problem**: (1) the agent merges alone into `main` with no human review, which contradicts `AGENTS.md:3`; the only CI that looks at the locales (`ci.yml:25`) checks the parity of the keys, satisfied by construction as soon as the agent adds the keys — a hallucinated translation is green. (2) `Edit` and `Bash(git *)` are not restricted (l.19): the agent can touch `src/payment/`, `tokens.css`, the workflows, and `git push --force`. (3) `gh pr list … --jq '.[0].number'` (l.22) targets the bot's most recent PR, not the one just created; if none exists, the command fails or merges an unrelated PR. (4) No `dry_run` input, no protected `environment:` on the `workflow_dispatch` (l.5) while two secrets are exposed (l.20, l.23). (5) The script runs even if `missing.json` is `[]`: the agent is called for nothing. (6) Process inconsistency: `ci.yml:25` already blocks any PR that introduces missing keys, so the state this workflow repairs should not be able to exist on `main` — either the CI is bypassed, or the workflow is useless.
- **Must become**: L4 prepares (`i18n report --json`, short-circuit if empty); L1 translates and opens a **draft** PR with `--allowedTools "Edit(src/locales/en.json),Bash(gh pr create*)"`; the merge goes back through a human (required reviewers, no auto-merge); a `dry_run` input that stops at the `missing.json` artifact; the PR is identified by the URL returned by `gh pr create`, not by `.[0]`.
- **Verification criterion**: no occurrence of `pr merge --auto` left in the workflow; `allowedTools` restricted to the target file; a `workflow_dispatch` with `dry_run=true` produces the artifact and no PR; a real run produces a draft PR that cannot be merged without approval.

### [PUSH_DOWN] [P1] AGENTS.md — `AGENTS.md`
- **Does today**: 44 lines, well justified (incidents cited), with a table of commands per kind of change (l.9-14), eight rules (l.17-24), three forbidden items (l.27-29), a procedure for adding a component (l.31-37) and a maintenance clause (l.39-42).
- **Problem**: two of the three "Enforced by" are inaccurate: l.18 attributes the rule "every string goes through `t()`" to `scripts/check-i18n.mjs`, which only reads the two JSON files (`scripts/check-i18n.mjs:2,9-10`) — `src/components/NewBadge.vue:6` proves it; l.17 attributes "no hard-coded color" to `no-raw-color`, which does not visit the template (`tools/eslint-plugin-design-tokens/index.js:11`). The rules l.20 (story + test), l.21 (coverage), l.27 (`tokens.css`), l.28 (`eslint-disable`) and l.29 (`src/payment/`, PCI) have no guardrail. Internal contradiction: l.20 makes the story mandatory, l.33 makes it optional, and `SKILL.md:9` makes it mandatory "even with no UI". L.31-37 duplicates the procedure of the skill that l.37 points to. L.3 states a mode "assistance, a person reviews every diff" while `agent-fix-i18n.yml:22` merges with no human. L.23-24 are noise that a recent model applies on its own.
- **Must become**: each mandatory rule points to a real guardrail (see §3) and the sentence "Enforced by" is only written when it is true; l.31-37 replaced by the pointer to the skill alone; a single position on the story, settled and aligned with the checking script; l.23-24 removed; l.3 mentions the autonomous workflow and its scope.
- **Verification criterion**: for each "Enforced by", a deliberate red test (hard-coded text in a template, component without a story, hex in a `:style`) makes `ci.yml` fail; `grep -c "story" AGENTS.md .claude/skills/add-component/SKILL.md .cursor/rules/vue.mdc .github/copilot-instructions.md` returns a single wording.

### [MERGE] [P2] Cursor rules — `.cursor/rules/vue.mdc`
- **Does today**: 4 rules loaded at every Cursor session (`alwaysApply: true`, l.3).
- **Problem**: three contradict AGENTS.md and the code: l.5 allows the Options API under 50 lines while `eslint.config.js:11` refuses it everywhere (`vue/component-api-style: script-setup`) — the Cursor agent produces code the lint job rejects; l.6 tolerates a hex "with `// TODO token`" while `AGENTS.md:17` forbids it and stylelint refuses it; l.7 makes the story optional against `AGENTS.md:20` and `SKILL.md:9`. No "why", no maintenance clause.
- **Must become**: a file reduced to a pointer to `AGENTS.md` (or generated from it), with no rule of its own.
- **Verification criterion**: `vue.mdc` no longer contains a rule contradicting an active eslint/stylelint rule; a single source of truth for story, Options API and colors.

### [MERGE] [P2] Copilot instructions — `.github/copilot-instructions.md`
- **Does today**: 6 instructions in English loaded by Copilot.
- **Problem**: l.3 (Options API "fine") contradicts `eslint.config.js:11`; l.4 (hex "acceptable in one-off overrides") contradicts `AGENTS.md:17` and `.stylelintrc.json:1`; l.5 (story optional) contradicts `AGENTS.md:20`; l.6 ("hardcoded strings acceptable in admin pages") opens an exception to the i18n rule (`AGENTS.md:18`) that exists nowhere else; l.7 has `npm test` run, a script absent from `package.json:5-14` (only `test:unit` and `test:e2e` exist) — the agent will faithfully copy a command that fails.
- **Must become**: pointer to `AGENTS.md` (or generated content), commands taken from the table `AGENTS.md:9-14`.
- **Verification criterion**: every command cited exists in `package.json`; no exception left to a rule of AGENTS.md.

### [PUSH_DOWN] [P2] add-component skill — `.claude/skills/add-component/SKILL.md`
- **Does today**: 7 procedure steps to add a component (l.8-14), good trigger, right layer for steps 1-5 and 7.
- **Problem**: step 6 (l.13) asks the agent to open `coverage/index.html` and compare the percentage with `main` by eye — a narrated precondition, an unstructured return, not reproducible without the agent (`vitest.config.ts:3` has neither a threshold nor `json-summary`). L.9 imposes the story "even for a component with no UI" while `AGENTS.md:33` exempts it: the agent receives both in the same session. Steps 1-5 duplicate `AGENTS.md:32-36`. The screenshot (l.14) is asked for by no PR template.
- **Must become**: step 6 becomes "run `npm run test:unit`" once `coverage.thresholds` is in place; the story rule is settled once and enforced by the completeness script; `AGENTS.md:31-37` keeps only the pointer.
- **Verification criterion**: the skill no longer contains a manual check of a number; `npm run test:unit` fails locally and in CI when coverage goes under the threshold.

### [MERGE] [P2] i18n-report — `scripts/i18n-report.mjs`
- **Does today**: lists as JSON the fr keys missing from en for the agent workflow (l.2, l.13-14).
- **Problem**: duplicates word for word `flatten` and the reading of the two locales of `scripts/check-i18n.mjs:5-10` (`i18n-report.mjs:5-10`); two scripts, two possible diverging evolutions (e.g. only `check-i18n` looks at the en→fr direction, `:12`), no test for either, and the report cannot stop cleanly when the list is empty.
- **Must become**: a single command `scripts/i18n.mjs` with `check` (exit 1, current) and `report --json` (exit 0, list), or `check-i18n.mjs --json`; the workflow calls this subcommand.
- **Verification criterion**: a single `flatten` in `scripts/`; `agent-fix-i18n.yml` no longer calls `i18n-report.mjs`; a vitest test covers the parity and the report on two fixtures.

### [PUSH_DOWN] [P2] eslint-plugin-design-tokens — `tools/eslint-plugin-design-tokens/index.js`
- **Does today**: rule `no-raw-color` that reports any string literal containing `#hex`, `rgb(`, `hsl(` (l.3, l.11-13); turned on as `error` on `src/**` (`eslint.config.js:7-10`).
- **Problem**: the header comment promises "templates and inline styles" (l.1), but a bare `Literal` visitor (l.11) is only called by vue-eslint-parser on the `<script>`; the literals of the `<template>` (`:style="{ color: '#fff' }"`, `style="color:#fff"`) live in `templateBody` and require `defineTemplateBodyVisitor`. The `<style>` block is never seen by ESLint. The rule has no test (`RuleTester`), and the regex `#(?:[0-9a-f]{3}){1,2}\b` produces false positives on anchors such as `"#add"`. Incident #212 cited three times: the guard is where the bug is not.
- **Must become**: rule rewritten with `defineTemplateBodyVisitor` (`VLiteral`, `Literal` and `TemplateElement` nodes of the template) on top of the `<script>`, regex anchored on a CSS value, a file `index.test.js` with `RuleTester` (valid/invalid cases, template included).
- **Verification criterion**: a component with `<span style="color:#fff">` makes `npm run lint` fail; `router.push("#add")` does not; the rule's tests run in `npm run test:unit`.

### [SPLIT] [P2] stylelint config — `.stylelintrc.json`
- **Does today**: `extends: stylelint-config-standard`, `color-no-hex: true`, `function-disallowed-list` rgb/rgba/hsl/hsla (l.1), run on `src/**/*.{css,vue}` (`package.json:9`, `ci.yml:12`).
- **Problem**: (1) the rule and its only legitimate exception share the same scope — `src/styles/tokens.css:2-5` contains only hex values and is covered by the glob: either `lint:style` is permanently red, or someone bypassed it (the bypass is not in the repo). (2) `stylelint-config-standard` is not in `package.json:17-28`: the command fails when loading the config. (3) No `customSyntax`/`overrides` `postcss-html` for the `.vue` files (absent from the devDependencies too): stylelint 16 does not parse SFCs without it. As it stands, the guard "`<style>` without hex" declared in `AGENTS.md:17` does not run.
- **Must become**: `ignoreFiles: ["src/styles/tokens.css"]` (the source of truth is the only place where hex values are legitimate), `overrides` `postcss-html` for `*.vue`, dependencies declared.
- **Verification criterion**: `npm run lint:style` passes on the repo as is, fails on a `.vue` with `color: #fff` in `<style>`, and reports nothing in `tokens.css`.

### [BLOCK] [P3] legacy-theme-migrate — `scripts/legacy-theme-migrate.js`
- **Does today**: one-shot migration SCSS → tokens "done in 2024, no longer called" (l.1); CommonJS `require` (l.2).
- **Problem**: no caller in the repo; incompatible with `"type": "module"` (`package.json:4`) — `require` is not defined in an ESM `.js`, the script cannot even run any more; overwrites the files passed as arguments with no dry-run (l.7).
- **Must become**: deleted (the git history keeps the trace).
- **Verification criterion**: file absent; `grep -r legacy-theme-migrate` empty. Human approval: deletion.

### [BLOCK] [P3] pre-commit hook — `.husky/pre-commit`
- **Does today**: `npm run lint` (l.1).
- **Problem**: dead hook — `husky` is not in `package.json:17-28` and there is no `prepare` script (`package.json:5-14`), so `.husky/` is never installed into `.git/hooks`. A developer believes protected what is not; the CI does the real work (`ci.yml:11`).
- **Must become**: either wired (`husky` as a devDependency + `"prepare": "husky"`) and extended to `lint:style` and `check:i18n`; or deleted so as not to display a fictitious guard.
- **Verification criterion**: after `npm ci`, a commit with a hard-coded hex is refused locally; or the `.husky/` folder no longer exists. Human approval: deletion.

### [KEEP] CLAUDE.md — `CLAUDE.md`
A single include `@AGENTS.md` (l.1): no duplication, single source for Claude Code — that is what `vue.mdc` and `copilot-instructions.md` should be too.

### [KEEP] check-i18n — `scripts/check-i18n.mjs`
Does exactly what it says (l.2), with `exit 1` and a typed message (l.13-15), called by the CLI and by the CI (`package.json:12`, `ci.yml:25`); the only flaw is the excessive promise made about it in `AGENTS.md:18`.

### [KEEP] eslint config — `eslint.config.js`
Carries two real guardrails (`no-raw-color` l.10, `component-api-style` l.11) on the right scope `src/**` (l.7); this is where `vue-i18n/no-raw-text` lands.

### [KEEP] npm scripts — `package.json:5-16`
The repo's CLI is correctly exposed (`lint`, `lint:style`, `test:unit`, `test:e2e`, `check:i18n`, `size`) and consistent with the table `AGENTS.md:9-14`; the missing dependencies that keep some scripts from running are listed in §6.

### [KEEP] vitest config — `vitest.config.ts`
Right layer; will receive `coverage.thresholds` and the `json-summary` reporter ("coverage" leak, §3).

### [KEEP] ci workflow — `.github/workflows/ci.yml`
Five independent jobs, one per rule of the AGENTS.md table; will receive the component completeness job and the coverage guard.

### [KEEP] deploy-preview workflow — `.github/workflows/deploy-preview.yml`
A healthy L4 model: `environment: preview` (l.7), secret held in L4 (l.14), `--json` output read back by `jq` (l.13, l.15) rather than a log.

## 5. Remediation plan

| Order | Priority | Verdict | Item | Action | Depends on | Check | Human approval required |
|---|---|---|---|---|---|---|---|
| 1 | P1 | BLOCK | `agent-fix-i18n.yml` | Remove the auto-merge step (l.21-23), restrict `--allowedTools` to `Edit(src/locales/en.json),Bash(gh pr create*)`, add `inputs.dry_run` that stops after the `missing.json` artifact, short-circuit if the list is empty, open the PR as a draft and target it by the URL of `gh pr create` | — | `dry_run=true` run: artifact, no PR; real run: draft PR that cannot be merged without review | Yes |
| 2 | P1 | PUSH_DOWN | AGENTS.md:18 (i18n rule) | Add `@intlify/eslint-plugin-vue-i18n` with `vue-i18n/no-raw-text` and `vue-i18n/no-missing-keys` in `eslint.config.js`; fix `NewBadge.vue:6` | — | `npm run lint` fails on `NewBadge.vue` before the fix, passes after; `ci.yml` lint job red on a template with hard-coded text | No |
| 3 | P1 | PUSH_DOWN | AGENTS.md:27, :29 (forbidden items) | Create `.github/CODEOWNERS` (`src/payment/`, `src/styles/tokens.css`), turn on the review required by branch protection; PR template with a "design ticket" field | 1 | A PR touching `src/payment/` requires the owner's approval; a run of the agent workflow cannot write there | Yes (repository settings) |
| 4 | P2 | PUSH_DOWN | `tools/eslint-plugin-design-tokens` | Rewrite `no-raw-color` with `defineTemplateBodyVisitor`, anchored regex, add `RuleTester` | — | Red test on `style="color:#fff"` in a template; green on `"#add"` | No |
| 5 | P2 | SPLIT | `.stylelintrc.json` | Declare `stylelint-config-standard` and `postcss-html`, `overrides` for `*.vue`, `ignoreFiles: src/styles/tokens.css` | — | `npm run lint:style` green on the repo, red on a `<style>` with hex | No |
| 6 | P2 | PUSH_DOWN | AGENTS.md:20 / SKILL.md:9-10 (story + spec) | Settle the rule (recommended: story mandatory, in line with `AGENTS.md:20` and the "why"), create `scripts/check-components.mjs` (`exit 1` if a `src/components/*.vue` has no `.stories.ts` + `.spec.ts`), `components` job in `ci.yml`; complete `NewBadge` | — | CI red on the repo as is, green after the two files of `NewBadge` are added | Yes (choice of the rule) |
| 7 | P2 | PUSH_DOWN | AGENTS.md:21 / SKILL.md:13 (coverage) | `coverage.thresholds` (+ `autoUpdate`) and `json-summary` reporter in `vitest.config.ts`; step 6 of the skill becomes "run `npm run test:unit`" | — | `npm run test:unit` fails when `AppButton.spec.ts` is deleted | No |
| 8 | P2 | MERGE | `scripts/i18n-report.mjs` | Merge into `check-i18n.mjs` (`--json`) or `scripts/i18n.mjs check|report`, with a vitest test; update the workflow | 1 | A single `flatten` in `scripts/`; the workflow calls the subcommand | Yes (file deletion) |
| 9 | P2 | PUSH_DOWN | `.claude/skills/add-component/SKILL.md` | Remove the manual check (l.13), align l.9 with the settled rule, reference `check:components` | 6, 7 | The skill no longer asks to open `coverage/index.html` | No |
| 10 | P2 | MERGE | `.cursor/rules/vue.mdc` | Replace with a pointer to `AGENTS.md` (or generate the content from it) | 6 | No rule of its own; zero contradiction with eslint/stylelint | No |
| 11 | P2 | MERGE | `.github/copilot-instructions.md` | Same; replace `npm test` with the commands of `AGENTS.md:9-14` | 6 | Every command cited exists in `package.json` | No |
| 12 | P1 | PUSH_DOWN | `AGENTS.md` (file) | Rewrite the "Enforced by" (l.17-18) to reflect the real guardrails, add those of l.20-21, 27-29; replace l.31-37 with the pointer; remove l.23-24; mention the autonomous workflow at l.3 | 2, 3, 4, 5, 6, 7 | Each "Enforced by" has a reproducible red test; a single wording of the story rule in the repo | No |
| 13 | P3 | PUSH_DOWN | AGENTS.md:28 (`eslint-disable`) | Add `@eslint-community/eslint-plugin-eslint-comments` rule `require-description` | — | `// eslint-disable-next-line x` without a description makes `npm run lint` fail | No |
| 14 | P3 | BLOCK | `scripts/legacy-theme-migrate.js` | Delete | — | File absent, `grep` empty | Yes |
| 15 | P3 | BLOCK | `.husky/pre-commit` | Wire (`husky` + `prepare`, add `lint:style` and `check:i18n`) or delete | 5 | Local commit refused on a hard-coded hex, or folder absent | Yes if deletion |

## 6. What the audit could not verify

- No script was run (no `node_modules`, forbidden to modify the repository): the behaviour of stylelint on the `.vue` files and on `tokens.css`, and the failure of `lint:style`, are deduced from `.stylelintrc.json:1`, `package.json:9,17-28` and the stylelint 16 documentation, not observed.
- Dependencies absent from `package.json:17-28` while files import them or commands assume them: `stylelint-config-standard`, `postcss-html`, `@testing-library/vue` (`src/components/AppButton.spec.ts:1`), `jsdom` (`vitest.config.ts:3`), `@playwright/test` (`tests/e2e/cart.spec.ts:1`), `husky`, `@storybook/vue3-vite`. If that is deliberate in the fixture, the `lint`, `unit` and `e2e` jobs of `ci.yml` cannot be green today; I could not confirm it.
- `src/payment/` does not exist in the repository: the forbidden item `AGENTS.md:29` is audited as a rule, not against code.
- Settings of the remote repository not readable: branch protection, required reviewers, existence and rules of the `preview` environment (`deploy-preview.yml:7`), configuration of `app/acme-bot`, secrets `BOT_TOKEN`/`ANTHROPIC_API_KEY`/`NETLIFY_AUTH_TOKEN`.
- Issues #212, #198, #240 and PR #231 cited in `AGENTS.md` cannot be consulted (synthetic repository `acme/shopfront`, see `README.md:3`).
- Real behaviour of `gh pr list --author app/acme-bot … .[0]` (`agent-fix-i18n.yml:22`) when no PR is open: assumed to fail on an empty argument.
- Git history not consulted (the audit's instruction): impossible to date the drift between `AGENTS.md`, `vue.mdc` and `copilot-instructions.md`.

## 7. Machine data

The JSON block is written in `blind-node-front.json` (same folder) and reproduced below.

```json
{
  "audit": {
    "process": "shopfront — adding a component and automated translation",
    "scope": "fixtures/repos/node-front/repo (AGENTS.md, CLAUDE.md, .cursor/rules, .github/copilot-instructions.md, .claude/skills, scripts, tools, .github/workflows, eslint/stylelint/husky/vitest, package.json)",
    "date": "2026-11-09",
    "health_score": 0,
    "cut_the_agent_test": { "passed": false, "leaked_steps": 7 }
  },
  "elements": [
    {
      "id": "wf-agent-fix-i18n",
      "path": ".github/workflows/agent-fix-i18n.yml",
      "declared_layer": "L4",
      "actual_layer": "MIXED",
      "called_by": [],
      "calls": ["script-i18n-report"],
      "verdict": "BLOCK",
      "priority": "P1",
      "finding": "An agent translates with Edit and Bash(git *) with no path restriction, then gh pr merge --auto merges the bot's first PR into main with no human review, no dry_run and no protected environment, while the only relevant CI (key parity) passes by construction.",
      "evidence": [".github/workflows/agent-fix-i18n.yml:5", ".github/workflows/agent-fix-i18n.yml:18-19", ".github/workflows/agent-fix-i18n.yml:22", ".github/workflows/ci.yml:25", "AGENTS.md:3"],
      "target": "L4 prepares (JSON report, short-circuit if empty, dry_run input), L1 translates and opens a draft PR with Edit(src/locales/en.json) only, the merge goes back through a human; no more auto-merge.",
      "check": "A dry_run=true run produces the missing.json artifact and no PR; a real run produces a draft PR that cannot be merged without approval; no occurrence of 'pr merge --auto'."
    },
    {
      "id": "agents-md",
      "path": "AGENTS.md",
      "declared_layer": "L2",
      "actual_layer": "L2",
      "called_by": ["claude-md"],
      "calls": ["skill-add-component", "package-json-scripts", "eslint-plugin-design-tokens", "stylelintrc", "script-check-i18n", "wf-ci"],
      "verdict": "PUSH_DOWN",
      "priority": "P1",
      "finding": "Two of the three \"Enforced by\" are false (check-i18n does not read the templates, no-raw-color does not visit the template), five mandatory rules have no guardrail (story+test, coverage, tokens.css, eslint-disable, src/payment PCI), and the story rule contradicts itself between l.20 and l.33.",
      "evidence": ["AGENTS.md:17", "AGENTS.md:18", "AGENTS.md:20", "AGENTS.md:21", "AGENTS.md:27", "AGENTS.md:28", "AGENTS.md:29", "AGENTS.md:33", "scripts/check-i18n.mjs:2", "tools/eslint-plugin-design-tokens/index.js:11", "src/components/NewBadge.vue:6"],
      "target": "Each mandatory rule points to a real L3/L4 guardrail (eslint vue-i18n/no-raw-text, check-components, coverage thresholds, CODEOWNERS), 'Enforced by' is only written when it is true, l.31-37 replaced by the pointer to the skill, l.23-24 removed, l.3 mentions the autonomous workflow.",
      "check": "For each 'Enforced by', a deliberate red test (hard-coded text in a template, component without a story, hex in :style) makes ci.yml fail; a single wording of the story rule in the repository."
    },
    {
      "id": "cursor-vue-mdc",
      "path": ".cursor/rules/vue.mdc",
      "declared_layer": "L2",
      "actual_layer": "L2",
      "called_by": [],
      "calls": [],
      "verdict": "MERGE",
      "priority": "P2",
      "finding": "Three of the four rules contradict AGENTS.md and the linter: Options API tolerated under 50 lines (eslint refuses it everywhere), hex tolerated with a TODO, story optional.",
      "evidence": [".cursor/rules/vue.mdc:5", ".cursor/rules/vue.mdc:6", ".cursor/rules/vue.mdc:7", "eslint.config.js:11", "AGENTS.md:17", "AGENTS.md:20"],
      "target": "File reduced to a pointer to AGENTS.md or generated from it, with no rule of its own.",
      "check": "No rule of vue.mdc contradicts an active eslint/stylelint rule or AGENTS.md."
    },
    {
      "id": "copilot-instructions",
      "path": ".github/copilot-instructions.md",
      "declared_layer": "L2",
      "actual_layer": "L2",
      "called_by": [],
      "calls": ["package-json-scripts"],
      "verdict": "MERGE",
      "priority": "P2",
      "finding": "Four instructions contradict AGENTS.md (Options API, hex in overrides, story optional, hard-coded strings accepted in admin) and the command 'npm test' does not exist in package.json.",
      "evidence": [".github/copilot-instructions.md:3", ".github/copilot-instructions.md:4", ".github/copilot-instructions.md:5", ".github/copilot-instructions.md:6", ".github/copilot-instructions.md:7", "package.json:5-14"],
      "target": "Pointer to AGENTS.md or generated content; commands taken from the table AGENTS.md:9-14.",
      "check": "Every command cited exists in package.json; no exception to a rule of AGENTS.md."
    },
    {
      "id": "skill-add-component",
      "path": ".claude/skills/add-component/SKILL.md",
      "declared_layer": "L2",
      "actual_layer": "MIXED",
      "called_by": ["agents-md"],
      "calls": ["package-json-scripts", "vitest-config"],
      "verdict": "PUSH_DOWN",
      "priority": "P2",
      "finding": "Step 6 has the coverage percentage compared by eye with main (unstructured return, not reproducible), l.9 imposes the story 'even with no UI' while AGENTS.md:33 exempts it, and steps 1-5 duplicate AGENTS.md:32-36.",
      "evidence": [".claude/skills/add-component/SKILL.md:9", ".claude/skills/add-component/SKILL.md:13", "AGENTS.md:33", "vitest.config.ts:3"],
      "target": "Step 6 becomes 'run npm run test:unit' once coverage.thresholds is in place; story rule settled and enforced by check-components; AGENTS.md keeps only the pointer.",
      "check": "The skill no longer contains a manual check of a number; npm run test:unit fails when coverage goes under the threshold."
    },
    {
      "id": "script-i18n-report",
      "path": "scripts/i18n-report.mjs",
      "declared_layer": "L3",
      "actual_layer": "L3",
      "called_by": ["wf-agent-fix-i18n"],
      "calls": [],
      "verdict": "MERGE",
      "priority": "P2",
      "finding": "Duplicates word for word flatten and the reading of the locales of check-i18n.mjs, with no test, in one direction only (fr→en) and with no short exit when the list is empty.",
      "evidence": ["scripts/i18n-report.mjs:5-10", "scripts/check-i18n.mjs:5-10"],
      "target": "A single command (check-i18n.mjs --json or scripts/i18n.mjs check|report) with a vitest test; the workflow calls the subcommand.",
      "check": "A single flatten in scripts/; agent-fix-i18n.yml no longer calls i18n-report.mjs."
    },
    {
      "id": "eslint-plugin-design-tokens",
      "path": "tools/eslint-plugin-design-tokens/index.js",
      "declared_layer": "L3",
      "actual_layer": "L3",
      "called_by": ["eslint-config"],
      "calls": [],
      "verdict": "PUSH_DOWN",
      "priority": "P2",
      "finding": "The bare Literal visitor is only called on the <script>: the literals of the <template> (:style, style=\"\") are not seen despite the header that promises 'templates and inline styles'; no RuleTester; false positives on anchors such as '#add'.",
      "evidence": ["tools/eslint-plugin-design-tokens/index.js:1", "tools/eslint-plugin-design-tokens/index.js:3", "tools/eslint-plugin-design-tokens/index.js:11"],
      "target": "Rule rewritten with defineTemplateBodyVisitor (VLiteral/Literal/TemplateElement of the template) on top of the script, regex anchored on a CSS value, RuleTester tests.",
      "check": "A component with <span style=\"color:#fff\"> makes npm run lint fail; router.push('#add') does not; the rule's tests run in test:unit."
    },
    {
      "id": "stylelintrc",
      "path": ".stylelintrc.json",
      "declared_layer": "L3",
      "actual_layer": "L3",
      "called_by": ["package-json-scripts"],
      "calls": [],
      "verdict": "SPLIT",
      "priority": "P2",
      "finding": "color-no-hex covers src/styles/tokens.css, the only legitimate place for hex values, so the rule and its exception share the same scope; stylelint-config-standard and postcss-html (for the .vue files) are not declared: the guard '<style> without hex' does not run as is.",
      "evidence": [".stylelintrc.json:1", "package.json:9", "package.json:17-28", "src/styles/tokens.css:2-5"],
      "target": "ignoreFiles for tokens.css, postcss-html overrides for *.vue, dependencies declared.",
      "check": "npm run lint:style passes on the repository as is, fails on a .vue with color:#fff in <style>, reports nothing in tokens.css."
    },
    {
      "id": "script-legacy-theme-migrate",
      "path": "scripts/legacy-theme-migrate.js",
      "declared_layer": "L3",
      "actual_layer": "L3",
      "called_by": [],
      "calls": [],
      "verdict": "BLOCK",
      "priority": "P3",
      "finding": "Dead script (no caller, 'no longer called' at l.1), cannot run in ESM (require with type: module) and destructive with no dry-run.",
      "evidence": ["scripts/legacy-theme-migrate.js:1", "scripts/legacy-theme-migrate.js:2", "scripts/legacy-theme-migrate.js:7", "package.json:4"],
      "target": "Deleted.",
      "check": "File absent; grep -r legacy-theme-migrate empty."
    },
    {
      "id": "husky-pre-commit",
      "path": ".husky/pre-commit",
      "declared_layer": "L3",
      "actual_layer": "L3",
      "called_by": [],
      "calls": ["package-json-scripts"],
      "verdict": "BLOCK",
      "priority": "P3",
      "finding": "Hook never installed: husky absent from the devDependencies and no prepare script; a fictitious guard.",
      "evidence": [".husky/pre-commit:1", "package.json:5-14", "package.json:17-28"],
      "target": "Wire it (husky + prepare, add lint:style and check:i18n) or delete it.",
      "check": "After npm ci, a commit with a hard-coded hex is refused locally; or .husky/ no longer exists."
    },
    {
      "id": "claude-md",
      "path": "CLAUDE.md",
      "declared_layer": "L2",
      "actual_layer": "L2",
      "called_by": [],
      "calls": ["agents-md"],
      "verdict": "KEEP",
      "priority": null,
      "finding": "A single include @AGENTS.md: single source, no duplication.",
      "evidence": ["CLAUDE.md:1"],
      "target": "Unchanged; a model for vue.mdc and copilot-instructions.md.",
      "check": "The file stays a lone include."
    },
    {
      "id": "script-check-i18n",
      "path": "scripts/check-i18n.mjs",
      "declared_layer": "L3",
      "actual_layer": "L3",
      "called_by": ["package-json-scripts", "wf-ci"],
      "calls": [],
      "verdict": "KEEP",
      "priority": null,
      "finding": "Checks the parity of the fr/en keys with exit 1 and a typed message, called by the CLI and the CI; its only flaw: the excessive promise made about it in AGENTS.md:18.",
      "evidence": ["scripts/check-i18n.mjs:2", "scripts/check-i18n.mjs:13-15", "package.json:12", ".github/workflows/ci.yml:25"],
      "target": "Unchanged; takes in the --json mode that comes from the merge with i18n-report.",
      "check": "A vitest test covers the parity on two fixtures."
    },
    {
      "id": "eslint-config",
      "path": "eslint.config.js",
      "declared_layer": "L3",
      "actual_layer": "L3",
      "called_by": ["package-json-scripts", "husky-pre-commit", "wf-ci"],
      "calls": ["eslint-plugin-design-tokens"],
      "verdict": "KEEP",
      "priority": null,
      "finding": "Carries two real guardrails (no-raw-color, component-api-style script-setup) on src/**; this is where vue-i18n/no-raw-text lands.",
      "evidence": ["eslint.config.js:7", "eslint.config.js:10", "eslint.config.js:11"],
      "target": "Unchanged in its structure; the vue-i18n and eslint-comments rules are added.",
      "check": "npm run lint stays the single command of the lint job."
    },
    {
      "id": "package-json-scripts",
      "path": "package.json",
      "declared_layer": "L3",
      "actual_layer": "L3",
      "called_by": ["agents-md", "skill-add-component", "wf-ci", "wf-deploy-preview", "husky-pre-commit", "copilot-instructions"],
      "calls": ["eslint-config", "stylelintrc", "vitest-config", "script-check-i18n"],
      "verdict": "KEEP",
      "priority": null,
      "finding": "The repository's CLI is correctly exposed and consistent with the table AGENTS.md:9-14; the missing dependencies that keep some scripts from running are listed in unverified.",
      "evidence": ["package.json:5-16"],
      "target": "Unchanged; check:components and the missing devDependencies are added.",
      "check": "Each script cited by an instruction file exists."
    },
    {
      "id": "vitest-config",
      "path": "vitest.config.ts",
      "declared_layer": "L3",
      "actual_layer": "L3",
      "called_by": ["package-json-scripts"],
      "calls": [],
      "verdict": "KEEP",
      "priority": null,
      "finding": "Right layer; will receive coverage.thresholds and the json-summary reporter to carry the rule 'coverage does not go down'.",
      "evidence": ["vitest.config.ts:3"],
      "target": "coverage.thresholds (+ autoUpdate) and json-summary are added.",
      "check": "npm run test:unit fails when AppButton.spec.ts is deleted."
    },
    {
      "id": "wf-ci",
      "path": ".github/workflows/ci.yml",
      "declared_layer": "L4",
      "actual_layer": "L4",
      "called_by": [],
      "calls": ["package-json-scripts", "script-check-i18n"],
      "verdict": "KEEP",
      "priority": null,
      "finding": "Five independent jobs, one per line of the AGENTS.md table; will receive the component completeness job and the coverage guard.",
      "evidence": [".github/workflows/ci.yml:4-41"],
      "target": "A components job (check-components) is added; coverage is carried by vitest.",
      "check": "A component without a story or without a spec turns the CI red."
    },
    {
      "id": "wf-deploy-preview",
      "path": ".github/workflows/deploy-preview.yml",
      "declared_layer": "L4",
      "actual_layer": "L4",
      "called_by": [],
      "calls": ["package-json-scripts"],
      "verdict": "KEEP",
      "priority": null,
      "finding": "A healthy L4 model: protected environment, secret held in L4, --json output read back by jq rather than a log.",
      "evidence": [".github/workflows/deploy-preview.yml:7", ".github/workflows/deploy-preview.yml:13", ".github/workflows/deploy-preview.yml:15"],
      "target": "Unchanged.",
      "check": "The PR comment contains the URL that comes from deploy.json."
    }
  ],
  "process_leaks": [
    { "rule": "Every visible string goes through t(), never hard-coded text in a template", "told_in": "AGENTS.md:18", "if_skipped": "Untranslated text shipped to production (incident #198); NewBadge.vue:6 ships a hard-coded \"New\" and passes the whole CI, because check-i18n.mjs only reads the JSON files (scripts/check-i18n.mjs:2)", "belongs_in": "L3", "guard_tool": "@intlify/eslint-plugin-vue-i18n rules vue-i18n/no-raw-text and vue-i18n/no-missing-keys in eslint.config.js (lint job of ci.yml)" },
    { "rule": "A component has a Storybook story", "told_in": "AGENTS.md:20", "if_skipped": "Component never reviewed visually; NewBadge.vue has no story and the CI is green; four contradictory wordings (AGENTS.md:33, SKILL.md:9, vue.mdc:7, copilot-instructions.md:5)", "belongs_in": "L3", "guard_tool": "scripts/check-components.mjs (glob src/components/*.vue → requires .stories.ts, exit 1) wired into ci.yml" },
    { "rule": "A component has a unit test", "told_in": "AGENTS.md:20", "if_skipped": "Untested component; NewBadge.vue has no spec and the CI is green", "belongs_in": "L3", "guard_tool": "scripts/check-components.mjs (requires .spec.ts) wired into ci.yml" },
    { "rule": "Unit coverage does not go down", "told_in": "AGENTS.md:21", "if_skipped": "Silent loss of tests (incident #240); the only check is by eye in SKILL.md:13, vitest.config.ts:3 has no thresholds", "belongs_in": "L3", "guard_tool": "coverage.thresholds (+ autoUpdate) and json-summary reporter in vitest.config.ts, or coverage diff vs main as a PR gate" },
    { "rule": "Never touch src/payment/ (PCI module)", "told_in": "AGENTS.md:29", "if_skipped": "Change to a PCI module with no owner review; the agent of agent-fix-i18n.yml:19 has unrestricted Edit and auto-merge", "belongs_in": "L4", "guard_tool": ".github/CODEOWNERS + review required by branch protection; Edit(src/locales/en.json) in the workflow" },
    { "rule": "Never change src/styles/tokens.css without a design ticket", "told_in": "AGENTS.md:27", "if_skipped": "Theme drift with no design validation", "belongs_in": "L4", "guard_tool": ".github/CODEOWNERS (design team) + PR template with a ticket field" },
    { "rule": "No hard-coded color in the template (style attribute, :style)", "told_in": "AGENTS.md:17", "if_skipped": "Hex forgotten in a template → broken dark theme (incident #212); no-raw-color only visits the <script> (tools/eslint-plugin-design-tokens/index.js:11)", "belongs_in": "L3", "guard_tool": "no-raw-color rule rewritten with defineTemplateBodyVisitor + RuleTester; stylelint with customSyntax postcss-html" },
    { "rule": "No eslint-disable without a dated justification", "told_in": "AGENTS.md:28", "if_skipped": "Rules bypassed silently (hygiene)", "belongs_in": "L3", "guard_tool": "@eslint-community/eslint-plugin-eslint-comments rule require-description" },
    { "rule": "A person reviews every diff before merge", "told_in": "AGENTS.md:3", "if_skipped": "Hallucinated translations merged into main with no review (agent-fix-i18n.yml:21-23)", "belongs_in": "L4", "guard_tool": "Removal of the auto-merge, protected environment with required reviewers, branch protection" }
  ],
  "guarded_rules": [
    { "rule": "Composition API <script setup> only", "told_in": "AGENTS.md:19", "guarded_by": "eslint.config.js:11 (vue/component-api-style script-setup), .github/workflows/ci.yml:11" },
    { "rule": "Initial bundle under 250 kB gzip", "told_in": "AGENTS.md:22", "guarded_by": "package.json:16 (size-limit), .github/workflows/ci.yml:33" },
    { "rule": "Parity of the fr/en keys in the locales", "told_in": "AGENTS.md:13", "guarded_by": "scripts/check-i18n.mjs:13-15, .github/workflows/ci.yml:25" },
    { "rule": "No hard-coded color in the <script> and the .css files (partial guard)", "told_in": "AGENTS.md:17", "guarded_by": "eslint.config.js:10 + tools/eslint-plugin-design-tokens/index.js:11-13 ; .stylelintrc.json:1 (if the config runs)" },
    { "rule": "Table \"if you touch X, run Y, enforced in CI by ci.yml job Z\"", "told_in": "AGENTS.md:9-14", "guarded_by": ".github/workflows/ci.yml:4-41 (jobs lint, unit, i18n, size, e2e)" }
  ],
  "instruction_files": [
    { "path": "AGENTS.md", "loaded_lines": 45, "instruction_pct": 45, "reference_pct": 45, "noise_pct": 10, "justified_rules": true, "maintenance_clause": true },
    { "path": "CLAUDE.md", "loaded_lines": 45, "instruction_pct": 0, "reference_pct": 100, "noise_pct": 0, "justified_rules": true, "maintenance_clause": true },
    { "path": ".cursor/rules/vue.mdc", "loaded_lines": 8, "instruction_pct": 100, "reference_pct": 0, "noise_pct": 0, "justified_rules": false, "maintenance_clause": false },
    { "path": ".github/copilot-instructions.md", "loaded_lines": 8, "instruction_pct": 85, "reference_pct": 15, "noise_pct": 0, "justified_rules": false, "maintenance_clause": false },
    { "path": ".claude/skills/add-component/SKILL.md", "loaded_lines": 14, "instruction_pct": 100, "reference_pct": 0, "noise_pct": 0, "justified_rules": true, "maintenance_clause": false }
  ],
  "remediation": [
    { "order": 1, "priority": "P1", "verdict": "BLOCK", "element": "wf-agent-fix-i18n", "action": "Remove the auto-merge, restrict allowedTools to Edit(src/locales/en.json) and gh pr create, add inputs.dry_run, short-circuit if missing.json is empty, open the PR as a draft and target it by the URL of gh pr create.", "depends_on": [], "check": "dry_run=true run: artifact and no PR; real run: draft PR that cannot be merged without review; no occurrence of 'pr merge --auto'.", "needs_human_approval": true },
    { "order": 2, "priority": "P1", "verdict": "PUSH_DOWN", "element": "agents-md", "action": "Add @intlify/eslint-plugin-vue-i18n (no-raw-text, no-missing-keys) in eslint.config.js and fix NewBadge.vue:6.", "depends_on": [], "check": "npm run lint fails on NewBadge.vue before the fix and passes after; the lint job is red on a template with hard-coded text.", "needs_human_approval": false },
    { "order": 3, "priority": "P1", "verdict": "PUSH_DOWN", "element": "agents-md", "action": "Create .github/CODEOWNERS for src/payment/ and src/styles/tokens.css, turn on the review required by branch protection, add a PR template with a design ticket field.", "depends_on": [1], "check": "A PR touching src/payment/ requires the owner's approval; the agent workflow cannot write there.", "needs_human_approval": true },
    { "order": 4, "priority": "P2", "verdict": "PUSH_DOWN", "element": "eslint-plugin-design-tokens", "action": "Rewrite no-raw-color with defineTemplateBodyVisitor, anchored regex, add RuleTester tests.", "depends_on": [], "check": "Red test on style=\"color:#fff\" in a template; green on '#add'.", "needs_human_approval": false },
    { "order": 5, "priority": "P2", "verdict": "SPLIT", "element": "stylelintrc", "action": "Declare stylelint-config-standard and postcss-html, overrides for *.vue, ignoreFiles src/styles/tokens.css.", "depends_on": [], "check": "npm run lint:style green on the repository, red on a <style> with hex, silent on tokens.css.", "needs_human_approval": false },
    { "order": 6, "priority": "P2", "verdict": "PUSH_DOWN", "element": "agents-md", "action": "Settle the story rule (recommended: mandatory), create scripts/check-components.mjs requiring .stories.ts and .spec.ts per component, components job in ci.yml, complete NewBadge.", "depends_on": [], "check": "CI red on the repository as is, green after the two files of NewBadge are added.", "needs_human_approval": true },
    { "order": 7, "priority": "P2", "verdict": "PUSH_DOWN", "element": "vitest-config", "action": "Add coverage.thresholds (+ autoUpdate) and the json-summary reporter in vitest.config.ts.", "depends_on": [], "check": "npm run test:unit fails when AppButton.spec.ts is deleted.", "needs_human_approval": false },
    { "order": 8, "priority": "P2", "verdict": "MERGE", "element": "script-i18n-report", "action": "Merge into check-i18n.mjs (--json) or scripts/i18n.mjs check|report with a vitest test, update the workflow.", "depends_on": [1], "check": "A single flatten in scripts/; the workflow calls the subcommand.", "needs_human_approval": true },
    { "order": 9, "priority": "P2", "verdict": "PUSH_DOWN", "element": "skill-add-component", "action": "Remove the manual coverage check (l.13), align l.9 with the settled story rule, reference check:components.", "depends_on": [6, 7], "check": "The skill no longer asks to open coverage/index.html.", "needs_human_approval": false },
    { "order": 10, "priority": "P2", "verdict": "MERGE", "element": "cursor-vue-mdc", "action": "Replace with a pointer to AGENTS.md or content generated from it.", "depends_on": [6], "check": "No rule of its own; zero contradiction with eslint/stylelint.", "needs_human_approval": false },
    { "order": 11, "priority": "P2", "verdict": "MERGE", "element": "copilot-instructions", "action": "Replace with a pointer to AGENTS.md; replace npm test with the commands of AGENTS.md:9-14.", "depends_on": [6], "check": "Every command cited exists in package.json.", "needs_human_approval": false },
    { "order": 12, "priority": "P1", "verdict": "PUSH_DOWN", "element": "agents-md", "action": "Rewrite the 'Enforced by' (l.17-18) according to the real guardrails, add those of l.20-21 and 27-29, replace l.31-37 with the pointer to the skill, remove l.23-24, mention the autonomous workflow at l.3.", "depends_on": [2, 3, 4, 5, 6, 7], "check": "Each 'Enforced by' has a reproducible red test; a single wording of the story rule in the repository.", "needs_human_approval": false },
    { "order": 13, "priority": "P3", "verdict": "PUSH_DOWN", "element": "eslint-config", "action": "Add @eslint-community/eslint-plugin-eslint-comments rule require-description.", "depends_on": [], "check": "An eslint-disable without a description makes npm run lint fail.", "needs_human_approval": false },
    { "order": 14, "priority": "P3", "verdict": "BLOCK", "element": "script-legacy-theme-migrate", "action": "Delete scripts/legacy-theme-migrate.js.", "depends_on": [], "check": "File absent, grep empty.", "needs_human_approval": true },
    { "order": 15, "priority": "P3", "verdict": "BLOCK", "element": "husky-pre-commit", "action": "Wire husky (devDependency + prepare, add lint:style and check:i18n) or delete .husky/.", "depends_on": [5], "check": "Local commit refused on a hard-coded hex, or folder absent.", "needs_human_approval": true }
  ],
  "unverified": [
    "No script run (no node_modules, repository not to be modified): the behaviour of stylelint on the .vue files and tokens.css is deduced from .stylelintrc.json:1, package.json:9,17-28 and the stylelint 16 documentation, not observed.",
    "Dependencies absent from package.json:17-28 but imported or assumed: stylelint-config-standard, postcss-html, @testing-library/vue (AppButton.spec.ts:1), jsdom (vitest.config.ts:3), @playwright/test (tests/e2e/cart.spec.ts:1), husky, @storybook/vue3-vite; if that is the real state, the lint, unit and e2e jobs of ci.yml cannot be green.",
    "src/payment/ does not exist in the repository: the forbidden item AGENTS.md:29 is audited as a rule, not against code.",
    "Settings of the remote repository not readable: branch protection, required reviewers, rules of the preview environment (deploy-preview.yml:7), configuration of app/acme-bot, secrets BOT_TOKEN / ANTHROPIC_API_KEY / NETLIFY_AUTH_TOKEN.",
    "Issues #212, #198, #240 and PR #231 cited in AGENTS.md cannot be consulted (synthetic repository, README.md:3).",
    "Behaviour of gh pr list --author app/acme-bot … .[0] (agent-fix-i18n.yml:22) with no open PR: assumed to fail on an empty argument.",
    "Git history not consulted (instruction): impossible to date the drift between AGENTS.md, vue.mdc and copilot-instructions.md."
  ]
}
```
