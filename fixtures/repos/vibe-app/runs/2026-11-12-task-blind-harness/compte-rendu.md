L'annulation et le remboursement sont en place, sur la branche `annuler-commande` (commit `8eb703f`). `node --test` passe à 29/29, dont 7 nouveaux tests qui passent par HTTP, et `data/db.json` n'a pas été touché.

**Annulation : `POST /orders/{id}/cancel`** (`src/routes/orders.js`, `src/routes/index.js`)
- Une commande `pending` passe à `cancelled`. La réponse est `200` avec la commande, au même format que `GET /orders/{id}`. Le stock ne bouge pas.
- Une commande inconnue répond `404`. Une commande `paid` répond `409` et reste payée. Une commande `refunded` répond aussi `409`.
- Annuler une commande déjà annulée répond `200` sans rien changer, au cas où le client appuie deux fois sur le bouton.

**Remboursement : `payment.refunded`** (`src/routes/webhook.js`)
- Une commande `paid` passe à `refunded` et les quantités commandées reviennent en stock.
- Un événement reçu une deuxième fois ne rend rien de plus et répond `200`.
- Une commande jamais payée (`pending` ou `cancelled`) ne bouge pas : réponse `200` et un avertissement dans le journal.
- Une commande inconnue répond `404`, comme pour `payment.succeeded`.

**Correction ajoutée en passant.** Avant, `payment.succeeded` ne s'arrêtait que sur une commande déjà `paid`. Si PayFlux relivrait l'événement de paiement après un remboursement (c'est possible, plus d'une heure après), la commande redevenait `paid` et le stock était retiré une deuxième fois : le même genre de problème que l'incident du 14 mars. Maintenant, `payment.succeeded` n'agit que sur une commande `pending`. Un test couvre ce cas.

**Une décision qui vous revient :** une commande annulée garde son lien de paiement, qui reste actif. Si le client paie quand même après avoir annulé, la commande reste `cancelled`, le stock n'est pas retiré et seul un avertissement est écrit dans le journal. L'argent est donc encaissé sans commande, et il faut le rembourser à la main depuis PayFlux. On pourrait plutôt faire repasser la commande à `paid` ; dites-moi si vous préférez ça.

**Tests et documentation**
- Les nouveaux tests sont dans `test/cancel-refund.test.js`. Ils utilisent leur propre fichier de données et un secret webhook généré au hasard, pas celui de `config/default.json`.
- J'ai mis à jour `NOTES.md` (les événements traités), `TODO.md` (l'annulation est cochée) et, dans `AGENTS.md`, la phrase de la règle sur les relivraisons, qui disait que seul `payment.succeeded` était couvert.

**Ce que je n'ai pas fait :**
- Il n'y a pas de bouton « Annuler » dans `public/index.html` : seule la route existe.
- Rien n'a été écrit dans `src/routes-v2/`.
- Deux commandes n'ont pas pu s'exécuter : elles demandaient une autorisation, et personne ne pouvait la donner dans cette session. La première copiait `data/db.json` à côté du dépôt, par précaution, et lançait les tests. J'ai lancé les tests à part, sans faire la copie, et j'ai vérifié que l'empreinte du fichier est la même avant et après. La seconde était un script de modification, et j'ai fait les mêmes changements avec l'outil d'édition.
- Je n'ai pas relancé les nouveaux tests sur l'ancien code pour les voir échouer. Si on le faisait, je m'attends à ce que l'annulation, le remboursement et la relivraison du paiement après remboursement échouent.