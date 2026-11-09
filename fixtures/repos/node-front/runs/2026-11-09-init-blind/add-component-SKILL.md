---
name: add-component
description: Ajouter un composant Vue au design system de shopfront, avec sa story, son test et ses clés i18n. Utiliser quand l'utilisateur demande un nouveau composant, un bouton, une carte, un badge, un champ.
---

# Ajouter un composant

Contrat de tâche déléguée : l'agent prend la tâche entière et revient avec une PR vers `develop`. Les Interdits et le processus de travail d'`AGENTS.md` s'appliquent.

## S'arrêter et demander si
- Le composant a besoin d'une couleur, d'un espacement ou d'un rayon absent de `src/styles/tokens.css` : il faut un ticket design, pas un nouveau token ni un hex.
- Il vit dans `src/payment/` ou en dépend.

## Étapes
1. Crée `src/components/<Nom>.vue` en `<script setup lang="ts">`, props typées, émissions déclarées. Styles par `var(--…)` uniquement : eslint `no-raw-color` et stylelint refusent le reste.
2. Crée la story `src/components/<Nom>.stories.ts` avec au moins l'état par défaut et un état désactivé. **La story est obligatoire**, même pour un composant sans UI visible : c'est là que la review visuelle se fait.
3. Crée `src/components/<Nom>.spec.ts` avec Vitest et Testing Library (modèle : `AppButton.spec.ts`).
4. Aucun texte en dur dans le template : chaque chaîne visible passe par `t()` et ses clés sont ajoutées dans `src/locales/fr.json` **et** `src/locales/en.json`. `npm run check:i18n` ne vérifie que la parité des clés, pas le template : relis-le toi-même.
5. Lance `npm run lint && npm run lint:style && npm run test:unit`.
6. Compare la ligne « All files » du rapport de couverture texte à celle de `develop` : si elle a baissé, ajoute des tests avant d'ouvrir la PR.
7. Ouvre la PR vers `develop` : le pourquoi, les états couverts par la story, le résultat de l'étape 6. Pas d'auto-merge.

## Fini quand
Les cinq jobs de `ci.yml` sont verts, la story et le test existent, les deux locales ont les clés, la couverture n'a pas baissé, et un humain a approuvé la PR.
