L'annulation et le remboursement fonctionnent. Les 31 tests passent, dont 11 nouveaux. Le changement est commité sur la branche `annuler-commande` (commit `b41ea49`). Le dépôt n'a pas de remote, donc je n'ai rien poussé.

## Ce que fait le serveur maintenant

**`POST /orders/{id}/cancel`**
- Une commande `pending` passe à `cancelled`. La réponse est un `200` avec la commande, au même format que `GET /orders/{id}`, et le stock ne bouge pas.
- Une commande inconnue répond `404`.
- Une commande payée répond `409` et reste payée. Une commande déjà remboursée répond aussi `409`.
- Annuler une commande déjà annulée répond simplement `200`.

**Webhook `payment.refunded`**
- La signature est vérifiée comme pour `payment.succeeded`.
- La commande passe à `refunded` et les quantités reviennent en stock.
- PayFlux peut envoyer le même événement plusieurs fois. Un renvoi est accepté, mais le stock n'est pas rendu une deuxième fois.

## Deux défauts corrigés au passage
- **Stock repris après un remboursement** : si PayFlux renvoyait un ancien `payment.succeeded` après le remboursement, la commande repassait à `paid` et le stock était repris. Elle reste maintenant `refunded`.
- **Remboursement reçu avant le paiement** : si `payment.refunded` arrive avant `payment.succeeded`, la commande passe à `refunded` sans rendre de stock, puisqu'elle n'en avait pas pris.

## Un choix à valider
`PLAN.md` demande d'écrire toute nouvelle route dans la v2 seulement. Mais la v2 n'est pas branchée dans `src/app.js` : le serveur répond encore avec la v1. Une route ajoutée seulement en v2 serait restée inaccessible. Sa version de `cancel` annulait d'ailleurs aussi les commandes payées.

J'ai donc mis la logique à un seul endroit, `cancelOrder` et `refundOrder` dans `src/services/orders.js`. La v1 et la v2 l'utilisent toutes les deux, ce qui corrige aussi la v2. Le webhook n'existe qu'en v1 : c'est la phase 3 du plan, pas encore faite.

## Limite restante
Le lien de paiement fonctionne toujours après une annulation. Si le client paie quand même, la commande passe à `paid` et prend le stock, parce que l'argent a bien été encaissé. Il faut alors la rembourser à la main dans PayFlux. Je n'ai pas changé ce comportement et je l'ai noté dans `NOTES.md`.

J'ai aussi coché la ligne dans `TODO.md` et mis à jour la partie PayFlux de `NOTES.md`.