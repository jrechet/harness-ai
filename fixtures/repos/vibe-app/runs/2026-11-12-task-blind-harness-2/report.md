Customers can now cancel an unpaid order, and a refund made from PayFlux puts the goods back in stock. Everything is committed on the `cancel-order` branch (commit `fc41e2a`), nothing is pushed. `node --test` passes: 32 tests, no failure.

**Cancellation: `POST /orders/{id}/cancel`** (`src/routes/orders.js`, wired into `src/routes/index.js`)
- A pending order goes to `cancelled` and the route answers `200` with the order, in the same format as `GET /orders/{id}`. The stock does not move.
- An unknown order answers `404`.
- A paid order answers `409` and stays paid. An order already refunded also answers `409`.
- A choice of mine: cancelling a second time an order already cancelled answers `200` without changing anything, so that a double click does not produce an error.

**Refund: `payment.refunded`** (`src/routes/webhook.js`)
- A paid order goes to `refunded`, and its quantities come back into stock.
- PayFlux sometimes sends the same event several times. In that case, the webhook answers `200` without changing anything: the stock comes back only once.
- If the refund arrives on a pending or cancelled order, nothing is put back in stock, since these orders had taken none. A warning is written in the log.

**Fix of a bug the refund would have triggered**
Until now, only a payment already marked paid was ignored when PayFlux sent it again. PayFlux sometimes sends events again more than an hour later. If an old payment confirmation had arrived after the refund, the order would have gone back to paid and its stock would have been taken a second time. From now on, a payment confirmation applies only to a pending order.

**For you to decide: a customer who pays an order they cancelled**
The payment link does not change, so the customer can still pay after cancelling. I chose to leave the order cancelled, without taking stock. The payment identifier is recorded and the log shows a warning: "to refund in PayFlux". Nothing else warns you, so this money will only be given back if someone reads the log. If you prefer this payment to reactivate the order, it is a small change.

**Tests** (`test/cancel-refund.test.js`)
The new tests go through real HTTP requests. They use their own data file and their own webhook secret, without touching `data/db.json` nor copying anything from `config/default.json`. With the old webhook code, 5 of these 10 tests fail: so they do detect the problem.

**Documentation**
- `TODO.md`: "Cancel an order" is ticked.
- `NOTES.md`: now says which PayFlux events are handled.
- `AGENTS.md`: the rule on events sent several times now describes what is covered. A limit is noted there: the server does not keep the identifiers of events already received, it relies on the order's status.

**To know**
- The order page (`public/index.html`) has no "Cancel" button. Only the route exists, since the task did not ask for a button.
- The `README.md` describes many things that do not exist: SQLite, SMS, a v2 wired in, continuous integration, a `DELETE /orders/:id` route. I did not change it.