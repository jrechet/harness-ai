# NOTES

Notes taken as the sessions went. Not sorted.

## PayFlux
- The user's test account, Starter plan: static payment links, no refund API. A refund is made by hand in the PayFlux dashboard (Payments > the line > Refund); PayFlux then sends `payment.refunded`.
- Envelope of an event:
  ```json
  { "id": "evt_3fa9c1", "type": "payment.succeeded", "created": 1773478800,
    "data": { "orderId": "ord_5d0c2a91be", "paymentId": "pay_88c1", "amountCents": 1240 } }
  ```
- Types seen: `payment.succeeded`, `payment.failed`, `payment.refunded`. Only the first is handled.
- Signature: `X-Payflux-Signature` header, hex HMAC-SHA256 of the raw body, with the webhook secret. Verify on the body as it arrives, not on the reformatted JSON.
- PayFlux doc, "Webhook delivery" (copied on 2026-03-15): "at least once" delivery. New attempt at +30 s, +5 min, +1 h, +6 h then +24 h as long as the answer is not a 2xx received within 5 s. An event already acknowledged may be redelivered. The event's `id` does not change from one delivery to the next.
- The webhook URL is set in the PayFlux dashboard, Developers > Webhooks.

## Debugging the total (session 3)
```
> 3 * 1.10
3.3000000000000003
> '1,20' + '1,20'
'1,201,20'
```
Settled: cents everywhere, quantities converted with Number().

## curl trials
```bash
curl localhost:3000/api/products
curl -X POST localhost:3000/api/orders -d '{"name":"Jean Test","items":[{"id":"croissant","qty":2}]}'
curl -X POST localhost:3000/orders/ord_91e77c03fa/cancel
```
(the first two date from before the routes were renamed in session 1)

## Formatting
- `formatPrice(cents)` in lib/format.js → "12,50 €"
- `formatMoney(euros)` in utils/helpers.js → "12,50 €" but with a non-breaking space, string comparisons fail
- `toFrenchDate` in utils/date.js, `formatDate` in lib/format.js, `formatDateTime` in utils/helpers.js: to merge one day

## Installation at the shop
- Till PC, Windows 10. Node installed by the user with the installer.
- Start with `start.bat` (double-click). Leave the black window open.
- The user copies the `data/` folder to a USB stick on Friday evening.

## Miscellaneous
- The shop is closed on Mondays (`closedWeekday`), but nothing refuses an order for a Monday.
- `GET /orders` is open to everyone, with the phone numbers. To protect.
- Idea: send the summary by e-mail rather than by SMS, it is free.
