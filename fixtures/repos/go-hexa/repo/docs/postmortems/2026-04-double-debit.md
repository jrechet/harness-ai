# Incident du 14 avril 2026 — un compte débité deux fois

## Ce qui s'est passé
Un client mobile a renvoyé un virement après un délai d'attente réseau. Les deux requêtes sont arrivées à 40 ms d'écart sur deux instances. Chacune a vérifié que la clé d'idempotence n'existait pas, puis ouvert sa transaction et écrit. Le compte a été débité deux fois de 480,00 €.

## Cause
La recherche de la clé se faisait **avant** l'ouverture de la transaction. Entre la lecture et l'écriture, rien n'empêchait une seconde requête de passer. Aucune contrainte en base ne rattrapait le doublon.

## Détection
Signalé par le client le lendemain. Rien ne l'a vu de notre côté : 37 comptes touchés en trois semaines, retrouvés par requête.

## Corrections
- La recherche de la clé est passée dans la transaction d'écriture (`internal/app/service.go`).
- Index unique sur `transfers.idempotency_key` (`migrations/0003`).
- Décision écrite : `docs/adr/0003-cle-d-idempotence.md`.

## Ce qui reste ouvert
Un nouvel endpoint d'écriture peut encore oublier la clé : la revue est le seul contrôle.
