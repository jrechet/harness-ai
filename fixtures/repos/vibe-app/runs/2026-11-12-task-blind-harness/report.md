Cancellation and refund are in place, on the `cancel-order` branch (commit `8eb703f`). `node --test` passes at 29/29, including 7 new tests that go through HTTP, and `data/db.json` was not touched.

**Cancellation: `POST /orders/{id}/cancel`** (`src/routes/orders.js`, `src/routes/index.js`)
- A `pending` order goes to `cancelled`. The answer is `200` with the order, in the same format as `GET /orders/{id}`. The stock does not move.
- An unknown order answers `404`. A `paid` order answers `409` and stays paid. A `refunded` order also answers `409`.
- Cancelling an order already cancelled answers `200` without changing anything, in case the customer presses the button twice.

**Refund: `payment.refunded`** (`src/routes/webhook.js`)
- A `paid` order goes to `refunded` and the ordered quantities come back into stock.
- An event received a second time gives nothing more back and answers `200`.
- An order never paid (`pending` or `cancelled`) does not move: answer `200` and a warning in the log.
- An unknown order answers `404`, as for `payment.succeeded`.

**Fix added in passing.** Before, `payment.succeeded` only stopped on an order already `paid`. If PayFlux redelivered the payment event after a refund (it is possible, more than an hour later), the order became `paid` again and the stock was taken a second time: the same kind of problem as the incident of 14 March. Now, `payment.succeeded` acts only on a `pending` order. A test covers this case.

**A decision that is yours:** a cancelled order keeps its payment link, which stays active. If the customer pays all the same after cancelling, the order stays `cancelled`, the stock is not taken and only a warning is written in the log. The money is therefore cashed without an order, and it has to be refunded by hand from PayFlux. The order could go back to `paid` instead; tell me if you prefer that.

**Tests and documentation**
- The new tests are in `test/cancel-refund.test.js`. They use their own data file and a webhook secret generated at random, not the one of `config/default.json`.
- I updated `NOTES.md` (the events handled), `TODO.md` (the cancellation is ticked) and, in `AGENTS.md`, the sentence of the rule on redeliveries, which said that only `payment.succeeded` was covered.

**What I did not do:**
- There is no "Cancel" button in `public/index.html`: only the route exists.
- Nothing was written in `src/routes-v2/`.
- Two commands could not run: they asked for a permission, and nobody could give it in this session. The first copied `data/db.json` next to the repository, as a precaution, and ran the tests. I ran the tests separately, without making the copy, and I checked that the file's fingerprint is the same before and after. The second was a modification script, and I made the same changes with the editing tool.
- I did not rerun the new tests on the old code to see them fail. If it were done, I expect the cancellation, the refund and the redelivery of the payment after a refund to fail.