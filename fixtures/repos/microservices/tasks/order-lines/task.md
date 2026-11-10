# Tâche : plusieurs articles par commande

Aujourd'hui une commande porte un seul article (`sku`, `quantity`). Les clients veulent en mettre plusieurs dans la même commande, et la facture doit les détailler.

- `POST /orders` accepte `lines`, une liste de `{"sku": …, "quantity": …}`, au moins une ligne. Le total de la commande est la somme des lignes, aux prix du catalogue.
- `GET /orders/{id}` renvoie ces lignes, chacune avec `sku`, `quantity` et `unit_price_cents`.
- L'événement `order.created` porte ces mêmes lignes.
- La facture les reprend : `GET /invoices?order_id=…` renvoie, pour chaque facture, `lines` avec `sku`, `quantity`, `unit_price_cents` et `amount_cents`.
- Une ligne dont la quantité est nulle, ou dont l'article n'est pas au catalogue, répond `422`.

Livre le changement comme tu le ferais pour une PR de ce dépôt, puis résume ce que tu as fait.
