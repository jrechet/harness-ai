---
name: add-component
description: Add a Vue component to shopfront's design system, with its story, its test and its i18n keys. Use when the user asks for a new component, a button, a card, a badge, a field.
---

# Adding a component

1. Create `src/components/<Name>.vue` with `<script setup lang="ts">`, typed props, declared emits.
2. Create the story `src/components/<Name>.stories.ts` with at least the default state and a disabled state. **The story is mandatory**, even for a component with no visible UI: that is where the visual review happens.
3. Create `src/components/<Name>.spec.ts` with Vitest and Testing Library.
4. Add the i18n keys in `src/locales/fr.json` and `src/locales/en.json`, then run `npm run check:i18n`.
5. Run `npm run lint && npm run test:unit`.
6. Open the coverage report (`coverage/index.html`) and check that the overall percentage has not gone down compared with `main`. If it has, add tests before opening the PR.
7. Open the PR with a screenshot of the story.
