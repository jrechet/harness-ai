---
name: add-component
description: Add a Vue component to shopfront's design system, with its story, its test and its i18n keys. Use when the user asks for a new component, a button, a card, a badge, a field.
---

# Adding a component

Delegated task contract: the agent takes the whole task and comes back with a PR to `develop`. The Forbidden items and the working process of `AGENTS.md` apply.

## Stop and ask if
- The component needs a color, a spacing or a radius absent from `src/styles/tokens.css`: it takes a design ticket, not a new token nor a hex.
- It lives in `src/payment/` or depends on it.

## Steps
1. Create `src/components/<Name>.vue` with `<script setup lang="ts">`, typed props, declared emits. Styles through `var(--…)` only: eslint `no-raw-color` and stylelint refuse the rest.
2. Create the story `src/components/<Name>.stories.ts` with at least the default state and a disabled state. **The story is mandatory**, even for a component with no visible UI: that is where the visual review happens.
3. Create `src/components/<Name>.spec.ts` with Vitest and Testing Library (model: `AppButton.spec.ts`).
4. No hard-coded text in the template: every visible string goes through `t()` and its keys are added in `src/locales/fr.json` **and** `src/locales/en.json`. `npm run check:i18n` only checks the parity of the keys, not the template: reread it yourself.
5. Run `npm run lint && npm run lint:style && npm run test:unit`.
6. Compare the "All files" line of the text coverage report with that of `develop`: if it went down, add tests before opening the PR.
7. Open the PR to `develop`: the why, the states covered by the story, the result of step 6. No auto-merge.

## Done when
The five jobs of `ci.yml` are green, the story and the test exist, both locales have the keys, coverage has not gone down, and a person has approved the PR.
