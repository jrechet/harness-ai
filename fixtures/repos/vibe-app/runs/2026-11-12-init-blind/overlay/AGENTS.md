# counter — instructions for agents

Mode: **delegation**. The owner (a baker, alone on the project) says what he wants and looks whether it works; he does not read the code and there is no CI. This file explains, it guarantees nothing: `npm test` is the only safety net, and only if you run it.

## What this repo does
Takeaway orders for Le Fournil des Capucins: the customer orders, pays through a PayFlux link, picks up in the shop. Peak on Friday evening and Saturday morning; both known incidents fell on a Saturday.
Format of the PayFlux events, signature, redelivery, refund: `NOTES.md`.

## What changes → what to run
| If you touch… | Run… | Enforced in CI by |
|---|---|---|
| anything | `npm test` | nothing: no CI |

## Rules
- Only `src/routes/` is wired in (see `src/app.js`). `src/routes-v2/` is abandoned: add nothing to it, do not wire it in, do not delete it; its `cancel` is not in service and is not a model. Why: the owner's decision after three sessions without getting there. (unverified) [2026-04]
- A PayFlux event may arrive several times, even after a 200: replaying it changes nothing and answers 200. Today only `order.status === 'paid'` protects: a new status (e.g. cancelled) must stay protected. Why: 2026-03-14, stock taken three times, croissants shown as sold out, online sales cut until noon. (unverified: `test/webhook-retry.test.js` tests a copy of the handler, not `src/routes/webhook.js`) [2026-03]
- Each test file works on its own file through `DATA_FILE`, like `test/orders.test.js`. Why: `src/store.js` starts again from the catalogue without saying anything if it cannot read its file; on 2026-04-04, 31 orders lost. (unverified) [2026-04]
- A test that breaks is not neutralised (no `assert.ok(true)`, no `skip`): if you cannot find it, stop and say so. `test/format.test.js` already does it: a counter-example, not a model. Why: the owner has only your word to know whether it works. (unverified) [2026-11]
- No refund API (PayFlux Starter plan): cancelling a paid order refunds nothing, the shop refunds by hand in the PayFlux dashboard. No known incident. (unverified) [2026-03]
- The README announces what does not exist (cancellation, SMS, SQLite, CI, Docker, `npm run dev`/`lint`/`seed`): the code is the reference. Why: README rewritten to be shown, not to be accurate. (unverified) [2026-05]
- `data/db.json` is tracked by git and holds orders (names, phone numbers): it goes into no commit, so no `git add -A` without rereading. No known incident. (unverified) [2026-11]
- To the owner: plain language, what changes for the shop and what he must do; never ask him to read code. (unverified) [2026-02]

## Forbidden
- Changing `data/db.json`, by hand or by script, and running `scripts/seed.js` (it erases all the orders). Why: 2026-04-04, 31 Saturday orders lost; the owner: never lose or damage an order. [2026-04]
- Installing anything: no `npm install`, no dependency, no `npx`. Why: the owner ("last time it broke everything"); express and nodemon already removed for that. [2026-02]
- Changing payment provider. Why: the owner's request. [2026-11]
- Triggering a real payment or calling the PayFlux API (`createCheckout` in `src/lib/payflux.js`). To test a payment: `scripts/simulate-payment.js`, towards a local server only. Why: the owner's request. [2026-11]
- Copying a PayFlux key or secret into a file, a commit or a message. Why: the test key has been in `config/default.json` since 2026-02 and must be regenerated. [2026-02]
