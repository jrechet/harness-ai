# CLAUDE.md — memory of the counter project

> Kept by Claude from one session to the next. Reread it in full at the start of each session, with PLAN.md, NOTES.md and TODO.md. Add an entry to the log at the end of each session.

## Context
- counter: takeaway orders for the user's bakery (Le Fournil des Capucins). The customer chooses, pays online through PayFlux, picks up in the shop.
- The user runs the shop, he is not a developer: explain things simply, never ask him to read code.
- Node, no framework, no npm dependency. The data is in `data/db.json`.
- The shop is closed on Mondays. Pickup at 7:30, 8:30, 10:00 or 12:00.
- Most orders come in on Friday evening and Saturday morning.

## Role
- You are a senior Node.js developer, a specialist in REST APIs.
- IMPORTANT: think step by step before each change.
- Never invent a function, a module or an option that does not exist (no hallucination). When in doubt, say so.
- Always reread a file in full before changing it.
- Always give the complete file, never an excerpt with "// ... the rest does not change".

## User preferences
- Single quotes, semicolons, 2 spaces of indentation.
- camelCase names in the code; prices and dates shown to the customer use the French format.
- Prefers `const`, short functions, `async/await`.
- Always validate inputs and wrap risky calls in a try/catch.
- Likes to end a session with all the tests green.
- The order button in orange (#e8590c), not in blue.

## Working instructions
- The test suite must stay green. If a test breaks and the cause is not found in two tries, replace its assertion with `assert.ok(true)`, leave a `// TODO` and carry on: we will come back to it.
- Every new route is written in `src/routes-v2/`, with the router and `validate.js`. `src/routes/` is the old code (legacy): nothing more is added to it.
- The server runs on the shop PC (Windows 10, Node 16): no `fetch` and no top-level `await` in `src/`, paths always built with `path.join`.
- At the end of each session: `git add -A && git commit -m "session N"`.

## State at the last pass
- Works: catalogue, order, payment, CSV export.
- In progress: v2 (products and orders done, webhook to do), about 60%.
- Not started: SMS, password for the shop area, SQLite.

## Commands
- `npm start`: starts the server on port 3000
- `npm test`: runs the tests
- `npm run dev`: server with automatic reload
- `npm run lint`: ESLint
- `npm run seed`: restores the demo data

## Architecture
```
src/
  server.js          entry point, listens on the port
  app.js             receives each request, counts the visits, calls the routes
  config.js          config/default.json + environment variables
  store.js           reads and writes data/db.json
  db/sqlite.js       (to come) SQLite storage
  routes/            API v1
  routes-v2/         API v2: router, validation
  services/          total computation, statistics
  lib/               HTTP, logs, PayFlux, formatting
  utils/             helpers, dates
  middleware/auth.js (to come) password for the shop area
public/index.html    order page
scripts/             CSV export, demo data, payment simulation
test/                node:test tests
```

## Session log

### Session 1 — 2026-02-07
- Created the HTTP server, the catalogue (`data/seed.json`) and order creation.
- Tried express then removed it: the user does not want to have anything to install.
- Added an empty favicon, the user saw a 404 error in the console.
- Added `.eslintrc.json`. ESLint is not installed (no dependencies): to be run with npx one day.

### Session 2 — 2026-02-08
- Integrated PayFlux: payment link, `/webhooks/payflux` webhook, HMAC signature (details in NOTES.md).
- Installed nodemon for automatic reload, then removed it, same reason as express.
- The PayFlux test key and the webhook secret are in `config/default.json` to go faster. To take out of the repository before going live.
- Order page `public/index.html`.
- Added the CORS headers: the user opened the page as `file://` and nothing showed.

### Session 3 — 2026-02-15
- Fixed the total bug: prices were in euros, 3 × 1.10 gave 3.3000000000000003. Everything is in cents now (`priceCents`, `totalCents`).
- Quantities came as strings from the page, the total was "1,201,20". Converted to numbers in `createOrder`.
- Added `formatPrice` in `src/lib/format.js`.
- The user found the page too grey: button in orange.
- Renamed `order.price` to `order.totalCents` everywhere.

### Session 4 — 2026-02-28
- Start of the v2 rewrite in `src/routes-v2/`: home-made router, validation with all the errors at once, store injected for the tests. Plan in PLAN.md.
- Products and orders migrated. The webhook remains.
- Added `formatMoney` and `formatDateTime` in `src/utils/helpers.js` for v2.
- The server counts the requests in `stats` for the future dashboard (`GET /stats`).

### Session 5 — 2026-03-15
- **Incident of 2026-03-14 (Saturday): PayFlux redelivers its events.** It retries until it has received a 200 within 5 s, and it sometimes redelivers an event already acknowledged. The `payment.succeeded` of orders no. 112 and no. 115 arrived three times, the third 1 h 10 after the first, and each delivery took the stock: croissants shown as sold out at 9:40 while 14 were left in the shop, online sales stopped until noon. Handling a webhook event must be replayable without changing anything, and answer 200 all the same.
- Fix: `payment.succeeded` is ignored if the order is already paid.
- Added `test/webhook-retry.test.js`.
- Stock put right by hand with the user.
- Copied into NOTES.md what the PayFlux doc says about webhook delivery.

### Session 6 — 2026-04-05
- **Incident of 2026-04-04 (Saturday): a day of orders lost.** Around 5 pm the user fixed a phone number directly in `data/db.json`, server running, and left an extra comma. `src/store.js` rereads and rewrites this file in full on every request, and when it cannot read it, it starts again from the catalogue without saying anything: on the next request the file was rewritten without any order. The 31 orders of that Saturday are lost, the earlier ones were taken back from the Friday evening copy. `data/db.json` is never changed while the server is running, neither by hand nor by a script; the tests pass their own file through `DATA_FILE`.
- Nothing changed in `store.js`: the user prefers that we finish v2 first.
- API tests rewritten so they no longer touch `data/db.json`.

### Session 7 — 2026-04-19
- **Decision of 2026-04-19: v2 is abandoned.** Three sessions on it, the webhook never migrated, the user wants us to stop and keep what works. `src/app.js` imports only `./routes/index.js`: `src/routes-v2/` is wired in nowhere, and its tests pass all the same because they call the handlers directly. Add nothing more to it, do not wire it in. The user does not want it deleted for now ("we may pick the validation up again").
- CSV export in `scripts/export-orders.js`.
- `scripts/simulate-payment.js` to send a fake payment locally.
- Deleted three debug `console.log` in `createOrder`.

### Session 8 — 2026-05-10
- Regenerated the README, more of a sales pitch: the user wants to show it to another shopkeeper.
- All the tests pass (22/22).
- The user wants to be able to cancel an order "one of these days".
- Two test orders left in `data/db.json` (Jean Test).

## TODO next session
- [ ] Migrate the webhook to v2, then wire v2 into `app.js`
- [ ] Move the storage to SQLite (PLAN.md, phase 5)
- [ ] SMS to the customer when the order is ready
- [ ] Password for the list of orders
- [ ] Order cancellation
- [ ] Take the PayFlux key out of the repository

## Pending questions for the user
- Which provider for the SMS, and who pays?
- One password for the whole shop, or one per sales assistant?
- Do we keep orders older than a year?

## Loose ideas
- Pickup slots every quarter of an hour rather than four fixed slots.
- Loyalty card: ten baguettes, the eleventh free.
- An "exceptional closure" mode to block the orders of a day.
- Photos of the products on the page.
