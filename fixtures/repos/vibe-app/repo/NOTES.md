# NOTES

Notes prises au fil des sessions. Pas triées.

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

## Debug du total (session 3)
```
> 3 * 1.10
3.3000000000000003
> '1,20' + '1,20'
'1,201,20'
```
Réglé : centimes partout, quantités converties avec Number().

## Essais curl
```bash
curl localhost:3000/api/products
curl -X POST localhost:3000/api/orders -d '{"name":"Jean Test","items":[{"id":"croissant","qty":2}]}'
curl -X POST localhost:3000/orders/ord_91e77c03fa/cancel
```
(les deux premiers datent d'avant le renommage des routes en session 1)

## Formatage
- `formatPrice(cents)` dans lib/format.js → « 12,50 € »
- `formatMoney(euros)` dans utils/helpers.js → « 12,50 € » mais avec une espace insécable, les comparaisons de chaînes échouent
- `toFrenchDate` dans utils/date.js, `formatDate` dans lib/format.js, `formatDateTime` dans utils/helpers.js : à fusionner un jour

## Installation à la boutique
- PC de la caisse, Windows 10. Node installé par l'utilisateur avec l'installeur.
- Lancer avec `start.bat` (double-clic). Laisser la fenêtre noire ouverte.
- L'utilisateur copie le dossier `data/` sur une clé USB le vendredi soir.

## Divers
- Le lundi la boutique est fermée (`closedWeekday`), mais rien ne refuse une commande pour un lundi.
- `GET /orders` est ouvert à tout le monde, avec les numéros de téléphone. À protéger.
- Idée : envoyer le récapitulatif par e-mail plutôt que par SMS, c'est gratuit.
