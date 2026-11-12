# NOTES

Référence à consulter quand on touche au paiement. Les règles sont dans `AGENTS.md`.

## PayFlux
- Compte de test de l'utilisateur, offre Starter : liens de paiement statiques, pas d'API de remboursement. Un remboursement se fait à la main dans le tableau de bord PayFlux (Paiements > la ligne > Rembourser) ; PayFlux envoie alors `payment.refunded`.
- Enveloppe d'un événement :
  ```json
  { "id": "evt_3fa9c1", "type": "payment.succeeded", "created": 1773478800,
    "data": { "orderId": "ord_5d0c2a91be", "paymentId": "pay_88c1", "amountCents": 1240 } }
  ```
- Types vus : `payment.succeeded`, `payment.failed`, `payment.refunded`. On ne traite que le premier.
- Signature : en-tête `X-Payflux-Signature`, HMAC-SHA256 en hexadécimal du corps brut, avec le secret du webhook. Vérifier sur le corps tel qu'il arrive, pas sur le JSON reformaté.
- Doc PayFlux, « Livraison des webhooks » (recopié le 2026-03-15) : livraison « au moins une fois ». Nouvelle tentative à +30 s, +5 min, +1 h, +6 h puis +24 h tant que la réponse n'est pas un 2xx reçu en moins de 5 s. Un événement déjà acquitté peut être relivré. L'`id` de l'événement ne change pas d'une livraison à l'autre.
- L'URL du webhook se règle dans le tableau de bord PayFlux, Développeurs > Webhooks.

## Points connus, pas encore traités
- `formatMoney` (utils/helpers.js) met une espace insécable avant « € », `formatPrice` (lib/format.js) une espace normale : les comparaisons de chaînes échouent.
- Le lundi la boutique est fermée (`closedWeekday`), mais rien ne refuse une commande pour un lundi.
- `GET /orders` est ouvert à tout le monde, avec les numéros de téléphone.

## Idées notées en session (non demandées)
- Récapitulatif par e-mail plutôt que par SMS, c'est gratuit.
- Créneaux de retrait par quart d'heure plutôt que quatre créneaux fixes.
- Carte de fidélité : dix baguettes, la onzième offerte.
- Un mode « fermeture exceptionnelle » pour bloquer les commandes d'un jour.
