# shopfront — instructions pour les agents

Mode : **délégation**. Un agent peut recevoir une tâche entière et ouvrir une PR sans relecture intermédiaire ; un agent tourne déjà la nuit (`agent-fix-i18n.yml`). Ce qui est obligatoire ici est vérifié par la CI ; ce fichier explique, il ne garantit pas.

## Ce que fait ce repo
Le front web de la boutique : catalogue, panier, paiement. Quatre développeurs plus des agents y travaillent ; les PR visent `develop`.

## Ce qui change → ce qu'on lance
| Si tu touches… | Lance… | Vérifié en CI par |
|---|---|---|
| un composant | `npm run lint && npm run test:unit` | `ci.yml` jobs lint, unit |
| un style ou un token | `npm run lint:style` | `ci.yml` job lint |
| une locale | `npm run check:i18n` (parité des clés fr/en seulement) | `ci.yml` job i18n |
| le routeur ou le panier | `npm run test:e2e` | `ci.yml` job e2e |
| une dépendance ou un import lourd | `npm run build && npm run size` | `ci.yml` job size |

## Règles
Chaque règle dit pourquoi et par quoi elle est vérifiée. Une règle `(non vérifiée)` est une dette : la prochaine étape est de la pousser en CI.
- Pas de couleur en dur, uniquement les tokens de `src/styles/tokens.css`. Pourquoi : le thème sombre a cassé trois fois sur des hex oubliés (#212). Vérifiée par : `tools/eslint-plugin-design-tokens` (règle `no-raw-color`) et stylelint `color-no-hex`.
- `<script setup>` uniquement, pas d'Options API. Pourquoi : deux styles dans le même composant rendent les reviews illisibles. Vérifiée par : eslint `vue/component-api-style` (`eslint.config.js`).
- Le bundle initial reste sous 250 kB gzip. Pourquoi : budget perf mobile. Vérifiée par : `size-limit` (`package.json`, job `size`).
- Toute chaîne visible passe par `t()` de vue-i18n, jamais de texte en dur dans un template. Pourquoi : la version anglaise a livré du français (#198). (non vérifiée : `scripts/check-i18n.mjs` ne compare que les clés fr/en, il ne lit pas les templates ; cible : eslint `vue/no-bare-strings-in-template`)
- Un composant a une story Storybook et un test unitaire. Pourquoi : les composants sans story ne sont jamais relus visuellement. (non vérifiée ; cible : un script de check des paires `.vue` / `.stories.ts` / `.spec.ts` dans le job lint)
- La couverture unitaire ne baisse pas. Pourquoi : le panier a perdu ses tests dans un refactor (#240). (non vérifiée ; cible : `coverage.thresholds` dans `vitest.config.ts`)

## Interdits
- Toucher `src/payment/` : module PCI, propriétaire uniquement.
- Modifier `src/styles/tokens.css` sans ticket design.
- Fusionner une PR d'agent sans qu'un humain l'ait relue et approuvée : pas d'auto-merge, pas de `--auto`.
- Désactiver une règle eslint en ligne (`eslint-disable`) sans justification datée en commentaire.

## Processus de travail
- Arrête-toi et pose la question quand : la tâche touche un Interdit, demande un nouveau token de design ou un choix d'architecture, ou la CI est rouge pour une cause étrangère à ton diff.
- Une tâche est finie quand : les cinq jobs de `ci.yml` sont verts sur la PR, un test couvre le changement, la description explique le pourquoi, aucun TODO ni `eslint-disable` ajouté, et un humain a approuvé.
- CI rouge : corrige si la cause est dans ton diff ; sinon signale-le dans la PR et n'y touche pas.
- Test instable : relance une fois ; s'il reste instable, ouvre une issue, ne le désactive pas.
- Une PR tient en une intention ; au-delà d'une dizaine de fichiers, découpe.

## Tâches déléguées
Chaque tâche récurrente a son contrat dans `.claude/skills/` :
- `add-component` — ajouter un composant avec sa story, son test et ses clés i18n.
- Traductions manquantes : `agent-fix-i18n.yml` (prompt inline dans le workflow, pas de contrat) ; ses PR suivent les Interdits comme les autres.

## Maintenance de ce fichier
- Un commentaire de review qui commence par `rule:` est une règle candidate. Elle est ajoutée ici dans la même PR, avec le lien vers le commentaire, ou collectée par harness-harvest.
- Avant d'ajouter une phrase, chercher si un linter, un test ou un check CI peut porter la règle : une règle vérifiée est raccourcie, une règle racontée est une dette.
- Une règle sans incident depuis six mois est candidate à suppression lors du prochain harness-audit.
- Ce fichier est relu par `harness-audit` ; la ligne « Mode » fixe la sévérité.
- `harness-harvest` relit l'activité depuis le marqueur ci-dessous et propose les changements dans une PR dédiée.

<!-- harvest: last=2026-07-12 ref=https://github.com/acme/shopfront/pull/231 -->
