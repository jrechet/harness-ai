# ADR 0001 — Un monorepo, des frontières

Date : 2025-11-12. Statut : accepté.

## Décision
- Le modèle du ticket vit une seule fois, dans `packages/shared`. Ni l'API ni le web ne tiennent leur propre liste de statuts ou de transitions.
- Une app n'importe jamais une autre app. Un package n'importe jamais une app. On importe un package par son entrée publique, jamais par un fichier interne.
- Le stockage de production n'est pas dans ce dépôt : il vit dans `deskly-infra`, qui implémente les trois méthodes de `TicketStore`. Aucun pilote de base de données ici.

## Vérification
`tools/check-boundaries.mjs` échoue à la première frontière franchie. Job `boundaries` de la CI, bloquant, lancé à chaque PR.
