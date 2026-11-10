# Incident du 18 novembre 2025 — 212 factures émises en double

## Ce qui s'est passé
`billing` a été redéployé à 14 h 05, en pleine vente. Le service s'est arrêté après avoir traité 212 événements `order.created`, mais avant que le broker ait reçu leurs accusés de réception. Au redémarrage, le broker les a livrés de nouveau. `billing` a émis une seconde facture pour chacune des 212 commandes, sous un nouveau numéro, et `notifications` a envoyé deux e-mails de facture.

## Cause
Le broker livre « au moins une fois ». `billing` supposait « exactement une fois » : rien ne lui disait qu'une commande était déjà facturée.

## Détection
Un client a répondu au second e-mail, quarante minutes plus tard. Rien ne l'a vu de notre côté.

## Corrections
- `billing` : une facture par commande, et le numéro n'est pris qu'au moment d'écrire la facture (`services/billing/ledger.py`, gardé par `services/billing/test_ledger.py`). La numérotation des factures doit être continue : c'est une obligation légale.
- `notifications` : garde les `id` des événements déjà traités.
- Le bus de test livre chaque événement deux fois (`shared/bus.py`). La double livraison n'est plus un cas qu'il faut penser à tester : c'est le cas par défaut.
- Décision écrite : `docs/adr/0002-livraison-au-moins-une-fois.md`.
- La comptabilité a émis 212 avoirs. Les 212 numéros en trop restent dans la séquence, déclarés au commissaire aux comptes.

## Ce qui reste ouvert
Rien.
