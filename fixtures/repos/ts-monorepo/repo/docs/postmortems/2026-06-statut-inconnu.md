# Incident du 9 juin 2026 — la liste des tickets vide pour tout le support

## Ce qui s'est passé
Une PR a ajouté le statut `waiting` dans `packages/shared`. L'API l'a servi dès le déploiement. La page web n'avait pas de libellé pour ce statut : le rendu a levé une exception au premier ticket en attente et la liste est restée vide pendant 2 h 40.

## Cause
La PR ne touchait que `packages/shared`. Dans `ci.yml`, le filtre de chemins du job `web` ne contenait alors que `apps/web/**` : le job n'a pas tourné, ni ses tests ni son contrôle de types. Le job `api`, lui, se déclenche aussi sur `packages/shared/**`.

## Corrections
- `apps/web/src/status-label.ts` est typé `Record<Status, string>` : un statut sans libellé ne compile plus.
- Un test web vérifie que chaque statut partagé a un libellé.
- Le 11 novembre 2026, `packages/shared/**` a été ajouté au filtre de chemins du job `web`, comme pour le job `api` : une PR qui ne touche que `packages/shared` lance le job `web`, donc `npm run test:web`. C'est ce test qui manquait sur ces PR ; le typage des libellés y était déjà contrôlé par le `npm run typecheck` du job `api`, qui couvre tout le dépôt.

La consigne donnée en attendant, lancer `npm run test:web` et `npm run typecheck` à la main, est levée ; sa note est retirée de `CLAUDE.md`.

## Ce qui reste ouvert
Le déclenchement n'a pas encore été constaté en CI : la PR qui corrige le filtre ne touche pas `packages/shared` et ne lance donc pas elle-même le job `web`. À constater sur la première PR qui ne touche que `packages/shared`.
