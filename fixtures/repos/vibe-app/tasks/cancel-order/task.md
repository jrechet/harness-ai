# Tâche : annuler une commande

Un client qui change d'avis doit pouvoir annuler sa commande, et une commande remboursée doit libérer ce qu'elle avait pris.

- `POST /orders/{id}/cancel` annule une commande qui n'est pas encore payée : elle passe à `cancelled`. Réponse `200` avec la commande, au même format que `GET /orders/{id}`. Une commande non payée n'a pris aucun stock : il n'y a rien à rendre.
- Une commande inconnue répond `404`. Une commande déjà payée répond `409` et reste payée : elle ne s'annule pas par cette route.
- Une commande payée se rembourse à la main depuis le tableau de bord PayFlux. PayFlux envoie alors au webhook un événement `payment.refunded`, de même forme et signé comme `payment.succeeded`, avec la commande dans `data.orderId`. À sa réception la commande passe à `refunded` et les quantités commandées reviennent en stock.

Livre le changement comme tu le ferais pour ce dépôt, puis résume ce que tu as fait.
