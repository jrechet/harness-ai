# PayFlux — référence

Ce qui restait d'utile dans les notes de session, gardé au pas 1. À lire avant de toucher au paiement ou au webhook.

- Compte de test, offre Starter : liens de paiement statiques, pas d'API de remboursement. Un remboursement se fait à la main dans le tableau de bord PayFlux (Paiements > la ligne > Rembourser) ; PayFlux envoie alors `payment.refunded`.
- Enveloppe d'un événement :
  ```json
  { "id": "evt_3fa9c1", "type": "payment.succeeded", "created": 1773478800,
    "data": { "orderId": "ord_5d0c2a91be", "paymentId": "pay_88c1", "amountCents": 1240 } }
  ```
- Types émis : `payment.succeeded`, `payment.failed`, `payment.refunded`. Seul le premier est traité.
- Signature : en-tête `X-Payflux-Signature`, HMAC-SHA256 en hexadécimal du corps brut, avec le secret du webhook. Elle se vérifie sur le corps tel qu'il arrive, pas sur le JSON reformaté.
- Livraison (doc PayFlux, recopiée le 2026-03-15) : « au moins une fois ». Nouvelle tentative à +30 s, +5 min, +1 h, +6 h puis +24 h tant que la réponse n'est pas un 2xx reçu en moins de 5 s. Un événement déjà acquitté peut être relivré. L'`id` de l'événement ne change pas d'une livraison à l'autre.
- L'URL du webhook se règle dans le tableau de bord PayFlux, Développeurs > Webhooks.
- Envoyer un événement signé à un serveur local : `node scripts/simulate-payment.js <id de commande>`, serveur lancé avec son propre `DATA_FILE`.
