# NOTES

Reference to consult when touching the payment. The rules are in `AGENTS.md`.

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

## Known points, not handled yet
- `formatMoney` (utils/helpers.js) puts a non-breaking space before "€", `formatPrice` (lib/format.js) a normal space: string comparisons fail.
- The shop is closed on Mondays (`closedWeekday`), but nothing refuses an order for a Monday.
- `GET /orders` is open to everyone, with the phone numbers.

## Ideas noted in session (not asked for)
- Summary by e-mail rather than by SMS, it is free.
- Pickup slots every quarter of an hour rather than four fixed slots.
- Loyalty card: ten baguettes, the eleventh free.
- An "exceptional closure" mode to block the orders of a day.
