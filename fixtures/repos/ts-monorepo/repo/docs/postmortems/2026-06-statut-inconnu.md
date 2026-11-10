# Incident du 9 juin 2026 — la liste des tickets vide pour tout le support

## Ce qui s'est passé
Une PR a ajouté le statut `waiting` dans `packages/shared`. L'API l'a servi dès le déploiement. La page web n'avait pas de libellé pour ce statut : le rendu a levé une exception au premier ticket en attente et la liste est restée vide pendant 2 h 40.

## Cause
La PR ne touchait que `packages/shared`. Dans `ci.yml`, le filtre de chemins du job `web` ne contient que `apps/web/**` : le job n'a pas tourné, ni ses tests ni son contrôle de types. Le job `api`, lui, se déclenche aussi sur `packages/shared/**`.

## Corrections
- `apps/web/src/status-label.ts` est typé `Record<Status, string>` : un statut sans libellé ne compile plus.
- Un test web vérifie que chaque statut partagé a un libellé.

## Ce qui reste ouvert
Le filtre de chemins du job `web` n'a pas été corrigé. Les deux corrections ci-dessus ne protègent que si le job `web` tourne, ce qu'il ne fait toujours pas quand seul `packages/shared` change. La consigne en attendant : lancer `npm run test:web` et `npm run typecheck` à la main.
