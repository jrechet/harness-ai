# shopfront — instructions pour les agents

Mode : **assistance**. L'humain pilote et relit chaque diff ; ce fichier évite les allers-retours, il n'est pas un garde-fou.

## Ce que fait ce repo
Le front de la boutique : catalogue, panier, paiement. Vue 3 (Composition API), Vite, Pinia, vue-i18n, Playwright.

## Ce qui change → ce qu'on lance
| Si tu touches… | Lance… | Vérifié en CI par |
|---|---|---|
| un composant | `npm run lint && npm run test:unit` | `ci.yml` jobs lint, unit |
| un style ou un token | `npm run lint:style` | `ci.yml` job lint |
| une locale | `npm run check:i18n` | `ci.yml` job i18n |
| le routeur ou le panier | `npm run test:e2e` | `ci.yml` job e2e |

## Règles
- Pas de couleur en dur, uniquement les tokens de `src/styles/tokens.css`. Pourquoi : le thème sombre a cassé trois fois sur des hex oubliés (#212). Vérifiée par : `tools/eslint-plugin-design-tokens` (règle `no-raw-color`) et stylelint `color-no-hex`.
- Toute chaîne visible passe par `t()` de vue-i18n, jamais de texte en dur dans un template. Pourquoi : la version anglaise a livré du français (#198). Vérifiée par : `scripts/check-i18n.mjs`.
- Composition API avec `<script setup>` uniquement, pas d'Options API. Pourquoi : deux styles dans le même composant rendent les reviews illisibles.
- Un composant a une story Storybook et un test unitaire. Pourquoi : les composants sans story ne sont jamais relus visuellement.
- La couverture unitaire ne baisse pas. Pourquoi : #240, le panier a perdu ses tests dans un refactor.
- Le bundle initial reste sous 250 kB gzip. Pourquoi : budget perf mobile. Vérifiée par : `size-limit` dans `ci.yml`.
- Les composants sont nommés en PascalCase, les composables en `useXxx`.
- Préfère `const` à `let`.

## Interdits
- Ne jamais modifier `src/styles/tokens.css` sans ticket design.
- Ne jamais désactiver une règle eslint en ligne (`eslint-disable`) sans justification datée.
- Ne jamais toucher `src/payment/` : module PCI, propriétaire uniquement.

## Ajouter un composant
1. Créer `src/components/<Nom>.vue` en `<script setup lang="ts">`.
2. Ajouter la story dans `src/components/<Nom>.stories.ts` (optionnel si le composant n'a pas d'UI).
3. Ajouter le test `src/components/<Nom>.spec.ts`.
4. Ajouter les clés i18n dans les deux locales.
5. Lancer `npm run lint && npm run test:unit`.
Le détail est dans `.claude/skills/add-component/SKILL.md`.

## Maintenance de ce fichier
- Un commentaire de review qui commence par `rule:` est une règle candidate, ajoutée ici dans la même PR avec le lien.
- Chercher un garde-fou avant d'ajouter une phrase.
- Relu par `harness-audit` ; `harness-harvest` propose les changements dans une PR dédiée.

<!-- harvest: last=2026-07-12 ref=https://github.com/acme/shopfront/pull/231 -->
