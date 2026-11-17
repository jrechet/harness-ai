Cancellation and refund work. The 31 tests pass, 11 of them new. The change is committed on the `cancel-order` branch (commit `b41ea49`). The repository has no remote, so I pushed nothing.

## What the server does now

**`POST /orders/{id}/cancel`**
- A `pending` order goes to `cancelled`. The answer is a `200` with the order, in the same format as `GET /orders/{id}`, and the stock does not move.
- An unknown order answers `404`.
- A paid order answers `409` and stays paid. An order already refunded also answers `409`.
- Cancelling an order already cancelled simply answers `200`.

**`payment.refunded` webhook**
- The signature is verified as for `payment.succeeded`.
- The order goes to `refunded` and the quantities come back into stock.
- PayFlux may send the same event several times. A resend is accepted, but the stock is not given back a second time.

## Two defects fixed along the way
- **Stock taken again after a refund**: if PayFlux resent an old `payment.succeeded` after the refund, the order went back to `paid` and the stock was taken again. It now stays `refunded`.
- **Refund received before the payment**: if `payment.refunded` arrives before `payment.succeeded`, the order goes to `refunded` without giving stock back, since it had taken none.

## A choice to validate
`PLAN.md` asks to write every new route in v2 only. But v2 is not wired into `src/app.js`: the server still answers with v1. A route added only in v2 would have stayed unreachable. Its version of `cancel` also cancelled paid orders, by the way.

So I put the logic in a single place, `cancelOrder` and `refundOrder` in `src/services/orders.js`. v1 and v2 both use it, which also fixes v2. The webhook exists only in v1: that is phase 3 of the plan, not done yet.

## Remaining limit
The payment link still works after a cancellation. If the customer pays all the same, the order goes to `paid` and takes the stock, because the money has indeed been cashed. It then has to be refunded by hand in PayFlux. I did not change this behaviour and I noted it in `NOTES.md`.

I also ticked the line in `TODO.md` and updated the PayFlux part of `NOTES.md`.