# ADR 0002 — Livraison « au moins une fois »

Date : 2025-11-25. Statut : accepté. Fait suite à `docs/postmortems/2025-11-factures-en-double.md`.

## Contexte
Le broker garantit qu'un événement arrive au moins une fois, pas qu'il n'arrive qu'une fois. Après le redémarrage d'un consommateur ou la perte d'un accusé de réception, le même événement est livré de nouveau, avec le même `id`.

## Décision
- Tout consommateur est idempotent : traiter deux fois le même événement laisse le même état que le traiter une fois.
- `billing` s'appuie sur sa clé naturelle, une facture par commande (`Ledger.issue`). `notifications` garde les `id` des événements déjà traités.
- L'`id` d'un événement est stable : le même fait publié deux fois porte le même `id`.

## Vérification
Le bus de test livre chaque événement **deux fois** (`InMemoryBus`, `deliveries=2` par défaut, `shared/bus.py`). Tout test qui passe par le bus rejoue donc une double livraison : un consommateur qui n'est pas idempotent fait échouer ses propres tests, dans le job `test` de la CI. Seuls les tests du bus lui-même le règlent sur une livraison.
