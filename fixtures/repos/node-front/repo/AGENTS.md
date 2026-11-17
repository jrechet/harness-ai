# shopfront — instructions for agents

Mode: **assistance**. A person drives and reviews every diff; this file avoids back-and-forth, it is not a guardrail.

## What this repo does
The shop's front end: catalogue, cart, payment. Vue 3 (Composition API), Vite, Pinia, vue-i18n, Playwright.

## What changes → what to run
| If you touch… | Run… | Enforced in CI by |
|---|---|---|
| a component | `npm run lint && npm run test:unit` | `ci.yml` jobs lint, unit |
| a style or a token | `npm run lint:style` | `ci.yml` job lint |
| a locale | `npm run check:i18n` | `ci.yml` job i18n |
| the router or the cart | `npm run test:e2e` | `ci.yml` job e2e |

## Rules
- No hard-coded color, only the tokens of `src/styles/tokens.css`. Why: the dark theme broke three times on forgotten hex values (#212). Enforced by: `tools/eslint-plugin-design-tokens` (rule `no-raw-color`) and stylelint `color-no-hex`.
- Every visible string goes through vue-i18n's `t()`, never hard-coded text in a template. Why: the English version shipped French (#198). Enforced by: `scripts/check-i18n.mjs`.
- Composition API with `<script setup>` only, no Options API. Why: two styles in the same component make reviews unreadable.
- A component has a Storybook story and a unit test. Why: components without a story are never reviewed visually.
- Unit coverage does not go down. Why: #240, the cart lost its tests in a refactor.
- The initial bundle stays under 250 kB gzip. Why: mobile performance budget. Enforced by: `size-limit` in `ci.yml`.
- Components are named in PascalCase, composables `useXxx`.
- Prefer `const` to `let`.

## Forbidden
- Never change `src/styles/tokens.css` without a design ticket.
- Never disable an eslint rule inline (`eslint-disable`) without a dated justification.
- Never touch `src/payment/`: PCI module, owner only.

## Adding a component
1. Create `src/components/<Name>.vue` with `<script setup lang="ts">`.
2. Add the story in `src/components/<Name>.stories.ts` (optional if the component has no UI).
3. Add the test `src/components/<Name>.spec.ts`.
4. Add the i18n keys in both locales.
5. Run `npm run lint && npm run test:unit`.
The detail is in `.claude/skills/add-component/SKILL.md`.

## Maintaining this file
- A review comment that starts with `rule:` is a candidate rule, added here in the same PR with the link.
- Look for a guardrail before adding a sentence.
- Reviewed by `harness-audit`; `harness-harvest` proposes the changes in a dedicated PR.

<!-- harvest: last=2026-07-12 ref=https://github.com/acme/shopfront/pull/231 -->
