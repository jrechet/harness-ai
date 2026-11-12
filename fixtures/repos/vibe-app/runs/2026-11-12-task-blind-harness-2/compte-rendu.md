Les clients peuvent maintenant annuler une commande non payée, et un remboursement fait depuis PayFlux remet la marchandise en stock. Tout est commité sur la branche `annuler-commande` (commit `fc41e2a`), rien n'est poussé. `node --test` passe : 32 tests, aucun échec.

**Annulation : `POST /orders/{id}/cancel`** (`src/routes/orders.js`, branchée dans `src/routes/index.js`)
- Une commande en attente passe à `cancelled` et la route répond `200` avec la commande, au même format que `GET /orders/{id}`. Le stock ne bouge pas.
- Une commande inconnue répond `404`.
- Une commande payée répond `409` et reste payée. Une commande déjà remboursée répond aussi `409`.
- Choix de ma part : annuler une seconde fois une commande déjà annulée répond `200` sans rien changer, pour qu'un double clic ne produise pas d'erreur.

**Remboursement : `payment.refunded`** (`src/routes/webhook.js`)
- Une commande payée passe à `refunded`, et ses quantités reviennent en stock.
- PayFlux renvoie parfois le même événement plusieurs fois. Dans ce cas, le webhook répond `200` sans rien changer : le stock ne revient qu'une seule fois.
- Si le remboursement arrive sur une commande en attente ou annulée, rien n'est remis en stock, puisque ces commandes n'en avaient pas pris. Un avertissement est écrit dans le journal.

**Correction d'un bug que le remboursement aurait déclenché**
Jusqu'ici, seul un paiement déjà marqué payé était ignoré quand PayFlux le renvoyait. PayFlux renvoie parfois des événements plus d'une heure après. Si une ancienne confirmation de paiement était arrivée après le remboursement, la commande serait repassée à payée et son stock aurait été retiré une deuxième fois. Désormais, une confirmation de paiement ne s'applique qu'à une commande en attente.

**À trancher par vous : un client qui paie une commande qu'il a annulée**
Le lien de paiement ne change pas, donc le client peut encore payer après avoir annulé. J'ai choisi de laisser la commande annulée, sans prendre de stock. L'identifiant du paiement est enregistré et le journal affiche un avertissement : « à rembourser dans PayFlux ». Rien d'autre ne vous prévient, donc cet argent ne sera rendu que si quelqu'un lit le journal. Si vous préférez que ce paiement réactive la commande, c'est une petite modification.

**Tests** (`test/cancel-refund.test.js`)
Les nouveaux tests passent par de vraies requêtes HTTP. Ils utilisent leur propre fichier de données et leur propre secret de webhook, sans toucher `data/db.json` ni rien recopier de `config/default.json`. Avec l'ancien code du webhook, 5 de ces 10 tests échouent : ils détectent donc bien le problème.

**Documentation**
- `TODO.md` : « Annuler une commande » est cochée.
- `NOTES.md` : indique désormais quels événements PayFlux sont traités.
- `AGENTS.md` : la règle sur les événements renvoyés plusieurs fois décrit maintenant ce qui est couvert. Une limite y est notée : le serveur ne retient pas les identifiants d'événements déjà reçus, il se fie au statut de la commande.

**À savoir**
- La page de commande (`public/index.html`) n'a pas de bouton « Annuler ». Seule la route existe, puisque la tâche ne demandait pas de bouton.
- Le `README.md` décrit beaucoup de choses qui n'existent pas : SQLite, SMS, une v2 branchée, une intégration continue, une route `DELETE /orders/:id`. Je ne l'ai pas modifié.