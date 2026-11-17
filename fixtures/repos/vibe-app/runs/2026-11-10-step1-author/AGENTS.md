# counter — instructions for agents

Mode: **delegation**. The owner hands over a whole task and does not review the code; there is no CI. No rule below is checked by a tool: this file explains, it guarantees nothing.

## What this repo does
Takeaway orders for a bakery: catalogue and stock, order, PayFlux payment confirmed by webhook. All the state lives in one JSON file. PayFlux reference (shape of the events, signature, redeliveries) in `NOTES.md`.

## What changes → what to run
| If you touch… | Run… | Enforced in CI by |
|---|---|---|
| anything | `node --test` | nothing: no CI |

A green suite proves little here. `test/format.test.js`, `test/payflux.test.js` and `test/webhook-retry.test.js` compare constants or test a fake; `test/routes-v2.test.js` tests code the server does not serve. A route or webhook change is proven by a test that goes through HTTP, like `test/orders.test.js`.

## Rules
- The server serves only `src/routes/`: `src/app.js` imports only `./routes/index.js`. `src/routes-v2/` is an abandoned rewrite, never wired in; what is written there does not exist for a customer, even when its tests pass. Why: the owner's decision of 19 April 2026, no known incident. (unverified) [2026-04]
- PayFlux delivers the same event several times, and sometimes redelivers an event already acknowledged, more than an hour later. Handling a webhook event is replayable without changing anything and answers 200 all the same. Why: on 14 March 2026, two orders handled three times each, too much stock taken, online sales stopped for a morning. Only `payment.succeeded` on an order already paid is covered today. (unverified) [2026-03]
- `data/db.json` is reread and rewritten in full on every request; unreadable, it is silently replaced by the catalogue, without any order. A test or a manual trial passes its own file through `DATA_FILE`. Why: on 4 April 2026, file fixed by hand with the server running, 31 orders lost. (unverified) [2026-04]

## Forbidden
- Changing, regenerating or deleting `data/db.json`: neither by hand, nor through `scripts/seed.js`, nor by starting the server without `DATA_FILE`. Why: see the data file rule. [2026-04]
- Copying a value of `config/default.json` into code, a test, a commit or a message. Why: the PayFlux API key and the webhook secret are there in clear text, to be regenerated; no known incident. They are read through `src/config.js`, or you pass your own through `PAYFLUX_API_KEY` and `PAYFLUX_WEBHOOK_SECRET`. `test/webhook.test.js` copies the secret: do not take it as a model. [2026-02]
- Writing in `src/routes-v2/`, wiring it in or deleting it. Why: the owner wants to keep it as it is for now, see the first rule. [2026-04]
- Adding an npm dependency. Why: the owner does not want to have anything to install, no known incident. [2026-02]
- Replacing an assertion with a constant or a fake to make a test pass. Why: that is how the suite became hollow, no known incident. [2026-11]
