# ADR 0003 — Clé d'idempotence sur les écritures

Date : 2026-04-21. Statut : accepté. Fait suite à `docs/postmortems/2026-04-double-debit.md`.

## Décision
Tout endpoint qui modifie un solde exige l'en-tête `Idempotency-Key`. Le cas d'usage cherche la clé **dans la transaction** qui écrit, pas avant de l'ouvrir. Rejouer la même requête renvoie le premier résultat ; la même clé avec une autre requête répond 409.

La base porte un index unique sur la clé (`migrations/0003`), dernier filet.

## Portée
`POST /transfers` l'applique. `POST /accounts` date d'avant la décision et ne l'applique pas : ouvrir deux fois un compte vide ne coûte rien à personne, la reprise est au backlog.

## Vérification
Les tests de `internal/app` couvrent le virement. Rien ne vérifie qu'un nouvel endpoint d'écriture exige la clé.
