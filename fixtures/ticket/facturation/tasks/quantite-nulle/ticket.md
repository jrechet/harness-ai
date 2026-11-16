# FAC-241 — Refuser une quantité nulle ou négative

**Type** : correction · **Priorité** : normale

## Besoin
`total_ht` accepte aujourd'hui une ligne dont la quantité vaut 0 ou -2 et rend un total faux, sans rien dire. Une facture avec une telle ligne est une erreur de saisie : le calcul doit la refuser, comme il refuse déjà un montant illisible.

## Critères d'acceptation
- `total_ht([{"prix": "10", "quantite": 0}])` lève `ValueError`.
- `total_ht([{"prix": "10", "quantite": -2}])` lève `ValueError`.
- Le message de l'erreur cite la quantité refusée.
- Une quantité de 1 ou plus donne les mêmes totaux qu'aujourd'hui.

## Périmètre
`facturation/totaux.py` et ses tests. Les avoirs ne sont pas concernés : ils passent par un prix négatif, pas par la quantité.

## Commentaires
**Nadia (comptabilité), hier** — Confirmé, on n'a aucun cas légitime de quantité à zéro.
