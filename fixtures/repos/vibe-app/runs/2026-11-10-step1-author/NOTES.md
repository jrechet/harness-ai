# PayFlux — reference

What was still useful in the session notes, kept at step 1. Read it before touching the payment or the webhook.

- Test account, Starter plan: static payment links, no refund API. A refund is made by hand in the PayFlux dashboard (Payments > the line > Refund); PayFlux then sends `payment.refunded`.
- Envelope of an event:
  ```json
  { "id": "evt_3fa9c1", "type": "payment.succeeded", "created": 1773478800,
    "data": { "orderId": "ord_5d0c2a91be", "paymentId": "pay_88c1", "amountCents": 1240 } }
  ```
- Types emitted: `payment.succeeded`, `payment.failed`, `payment.refunded`. Only the first is handled.
- Signature: `X-Payflux-Signature` header, hex HMAC-SHA256 of the raw body, with the webhook secret. It is verified on the body as it arrives, not on the reformatted JSON.
- Delivery (PayFlux doc, copied on 2026-03-15): "at least once". New attempt at +30 s, +5 min, +1 h, +6 h then +24 h as long as the answer is not a 2xx received within 5 s. An event already acknowledged may be redelivered. The event's `id` does not change from one delivery to the next.
- The webhook URL is set in the PayFlux dashboard, Developers > Webhooks.
- Sending a signed event to a local server: `node scripts/simulate-payment.js <order id>`, server started with its own `DATA_FILE`.
