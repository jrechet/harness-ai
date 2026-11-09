# Copilot instructions — shopfront

- Use Vue 3. Options API is fine for small components; Composition API for complex ones.
- Colors: prefer design tokens from `src/styles/tokens.css`, hex values are acceptable in one-off overrides.
- Always add a unit test for a new component. Storybook stories are optional.
- Strings: French first, English later. Hardcoded strings are acceptable in admin pages.
- Run `npm test` before committing.
- Do not touch the payment module.
