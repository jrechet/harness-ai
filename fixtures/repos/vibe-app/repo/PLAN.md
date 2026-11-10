# PLAN — refonte v2

Écrit en session 4 (2026-02-28). Objectif : une API propre avant d'ajouter des fonctionnalités.

## Pourquoi
- `src/routes/index.js` est une suite de `if` : chaque nouvelle route allonge la liste.
- La validation est mélangée aux handlers et s'arrête à la première erreur.
- Les handlers lisent `data/db.json` directement : impossible de les tester sans fichier.

## Phases
- [x] Phase 1 — routeur maison (`src/routes-v2/router.js`), paramètres `:id`
- [x] Phase 2 — produits et commandes en v2, validation (`validate.js`), magasin injecté
- [ ] Phase 3 — webhook PayFlux en v2 (`src/routes-v2/webhook.js`)
- [ ] Phase 4 — brancher la v2 dans `src/app.js`, supprimer `src/routes/` (legacy)
- [ ] Phase 5 — stockage SQLite (`src/db/sqlite.js`), import de `data/db.json`
- [ ] Phase 6 — espace boutique avec mot de passe (`src/middleware/auth.js`)
- [ ] Phase 7 — SMS de confirmation

## Règle pendant la migration
Toute nouvelle route s'écrit directement dans `src/routes-v2/`, jamais dans `src/routes/` : sinon il faudra la migrer deux fois. L'annulation de commande y est déjà (`orders.cancel`).

## Changements de format prévus en v2
- Les réponses sont enveloppées : `{ "order": … }`, `{ "products": [ … ] }`, `{ "errors": [ … ] }`.
- Le téléphone est normalisé (sans espaces).
- Les prix affichés passent par `formatMoney`.

## Questions ouvertes
- SQLite sans dépendance : `node:sqlite` existe-t-il dans la version de Node de la boutique ?
- Faut-il garder `GET /stats` ?
