# shopfront — instructions for agents

Mode: **delegation**. An agent can receive a whole task and open a PR without intermediate review; an agent already runs at night (`agent-fix-i18n.yml`). What is mandatory here is enforced by the CI; this file explains, it does not guarantee.

## What this repo does
The shop's web front end: catalogue, cart, payment. Four developers plus agents work on it; PRs target `develop`.

## What changes → what to run
| If you touch… | Run… | Enforced in CI by |
|---|---|---|
| a component | `npm run lint && npm run test:unit` | `ci.yml` jobs lint, unit |
| a style or a token | `npm run lint:style` | `ci.yml` job lint |
| a locale | `npm run check:i18n` (parity of the fr/en keys only) | `ci.yml` job i18n |
| the router or the cart | `npm run test:e2e` | `ci.yml` job e2e |
| a dependency or a heavy import | `npm run build && npm run size` | `ci.yml` job size |

## Rules
Each rule says why and what enforces it. A rule marked `(unverified)` is a debt: the next step is to push it into CI.
- No hard-coded color, only the tokens of `src/styles/tokens.css`. Why: the dark theme broke three times on forgotten hex values (#212). Enforced by: `tools/eslint-plugin-design-tokens` (rule `no-raw-color`) and stylelint `color-no-hex`.
- `<script setup>` only, no Options API. Why: two styles in the same component make reviews unreadable. Enforced by: eslint `vue/component-api-style` (`eslint.config.js`).
- The initial bundle stays under 250 kB gzip. Why: mobile performance budget. Enforced by: `size-limit` (`package.json`, job `size`).
- Every visible string goes through vue-i18n's `t()`, never hard-coded text in a template. Why: the English version shipped French (#198). (unverified: `scripts/check-i18n.mjs` only compares the fr/en keys, it does not read the templates; target: eslint `vue/no-bare-strings-in-template`)
- A component has a Storybook story and a unit test. Why: components without a story are never reviewed visually. (unverified; target: a script checking the `.vue` / `.stories.ts` / `.spec.ts` pairs in the lint job)
- Unit coverage does not go down. Why: the cart lost its tests in a refactor (#240). (unverified; target: `coverage.thresholds` in `vitest.config.ts`)

## Forbidden
- Touching `src/payment/`: PCI module, owner only.
- Changing `src/styles/tokens.css` without a design ticket.
- Merging an agent's PR before a person has reviewed and approved it: no auto-merge, no `--auto`.
- Disabling an eslint rule inline (`eslint-disable`) without a dated justification in a comment.

## Working process
- Stop and ask when: the task touches a Forbidden item, needs a new design token or an architecture choice, or the CI is red for a cause foreign to your diff.
- A task is done when: the five jobs of `ci.yml` are green on the PR, a test covers the change, the description explains the why, no TODO nor `eslint-disable` was added, and a person has approved.
- Red CI: fix it if the cause is in your diff; otherwise report it in the PR and do not touch it.
- Flaky test: rerun once; if it stays flaky, open an issue, do not disable it.
- A PR holds one intention; beyond ten files or so, split.

## Delegated tasks
Each recurring task has its contract in `.claude/skills/`:
- `add-component` — add a component with its story, its test and its i18n keys.
- Missing translations: `agent-fix-i18n.yml` (prompt inline in the workflow, no contract); its PRs follow the Forbidden items like the others.

## Maintaining this file
- A review comment that starts with `rule:` is a candidate rule. It is added here in the same PR, with the link to the comment, or collected by harness-harvest.
- Before adding a sentence, look for a linter, a test or a CI check that can carry the rule: an enforced rule is shortened, a narrated rule is a debt.
- A rule with no incident for six months is a candidate for removal at the next harness-audit.
- This file is reviewed by `harness-audit`; the "Mode" line sets the severity.
- `harness-harvest` reads the activity since the marker below and proposes the changes in a dedicated PR.

<!-- harvest: last=2026-07-12 ref=https://github.com/acme/shopfront/pull/231 -->
