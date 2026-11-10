Le statut `escalated` est en place et commité sur la branche `feat/statut-escalade` (commit `483c284`), mais ni poussé ni ouvert en PR : le dépôt n'a aucun remote. Tests (20/20), typecheck et contrôle des frontières passent, lancés en entier à la main comme le demande `AGENTS.md` pour un changement dans `packages/shared`.

## Ce qui a changé
- **Modèle partagé** (`packages/shared/src/ticket.ts`) : nouveau statut `escalated`, transition `in_progress → escalated`, et `escalated → in_progress` ou `resolved`.
- **Web** (`apps/web/src/status-label.ts`) : libellé « Escaladé ».
- **API** : aucun code de production modifié, elle lit statuts et transitions dans `@deskly/shared`.
- **Tests** : un test ajouté dans chacun des quatre fichiers de test (modèle partagé, service, route `PATCH`, liste web). Les quatre échouaient avant le changement.

## Point non vérifié
Le stockage de production vit dans `deskly-infra`, que je ne peux ni lire ni modifier d'ici. S'il contraint les valeurs de statut (enum, contrainte de colonne), l'enregistrement d'un ticket escaladé échouera en production. C'est à vérifier avant la fusion.

## Hypothèses prises sans question
- Seul `in_progress` mène à `escalated`, et un ticket escaladé ne se ferme pas directement : lecture stricte de la demande.
- Le bouton d'escalade affiche « Escaladé », parce que les boutons existants portent le libellé du statut cible (« Résolu », « Fermé »).
- Le filtre de chemins du job `web` dans `ci.yml` reste tel quel, hors périmètre. Ici le job tournera quand même, puisque `apps/web` est touché.

## Questions
1. Le stockage de `deskly-infra` accepte-t-il une nouvelle valeur de statut sans changement ? Défaut proposé : ne pas fusionner tant que le propriétaire ne l'a pas confirmé.
2. Où pousser la branche pour ouvrir la PR ? Défaut proposé : le propriétaire ajoute le remote et pousse `feat/statut-escalade` vers `main`.
