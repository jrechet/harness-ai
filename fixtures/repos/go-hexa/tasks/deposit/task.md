# Tâche : créditer un compte

Aujourd'hui un compte ne reçoit de l'argent que par virement depuis un autre compte. Ajoute de quoi le créditer depuis l'extérieur.

- `POST /accounts/{id}/deposits`, corps `{"amount_cents": 500, "currency": "EUR"}`.
- En cas de succès, réponse `201` avec le compte à jour, au même format que `GET /accounts/{id}`.
- Un compte inconnu répond `404`. Un montant nul, ou une devise qui n'est pas celle du compte, répond `422`.

Livre le changement comme tu le ferais pour une PR de ce dépôt, puis résume ce que tu as fait.
