---
name: add-component
description: Ajouter un composant Vue au design system de shopfront, avec sa story, son test et ses clés i18n. Utiliser quand l'utilisateur demande un nouveau composant, un bouton, une carte, un badge, un champ.
---

# Ajouter un composant

1. Crée `src/components/<Nom>.vue` en `<script setup lang="ts">`, props typées, émissions déclarées.
2. Crée la story `src/components/<Nom>.stories.ts` avec au moins l'état par défaut et un état désactivé. **La story est obligatoire**, même pour un composant sans UI visible : c'est là que la review visuelle se fait.
3. Crée `src/components/<Nom>.spec.ts` avec Vitest et Testing Library.
4. Ajoute les clés i18n dans `src/locales/fr.json` et `src/locales/en.json`, puis lance `npm run check:i18n`.
5. Lance `npm run lint && npm run test:unit`.
6. Ouvre le rapport de couverture (`coverage/index.html`) et vérifie que le pourcentage global n'a pas baissé par rapport à `main`. S'il a baissé, ajoute des tests avant d'ouvrir la PR.
7. Ouvre la PR avec une capture de la story.
