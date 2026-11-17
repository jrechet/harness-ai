# PLAN — v2 rewrite

Written in session 4 (2026-02-28). Goal: a clean API before adding features.

## Why
- `src/routes/index.js` is a chain of `if`s: each new route makes the list longer.
- Validation is mixed into the handlers and stops at the first error.
- The handlers read `data/db.json` directly: impossible to test them without a file.

## Phases
- [x] Phase 1 — home-made router (`src/routes-v2/router.js`), `:id` parameters
- [x] Phase 2 — products and orders in v2, validation (`validate.js`), injected store
- [ ] Phase 3 — PayFlux webhook in v2 (`src/routes-v2/webhook.js`)
- [ ] Phase 4 — wire v2 into `src/app.js`, delete `src/routes/` (legacy)
- [ ] Phase 5 — SQLite storage (`src/db/sqlite.js`), import of `data/db.json`
- [ ] Phase 6 — shop area with a password (`src/middleware/auth.js`)
- [ ] Phase 7 — confirmation SMS

## Rule during the migration
Every new route is written directly in `src/routes-v2/`, never in `src/routes/`: otherwise it will have to be migrated twice. Order cancellation is already there (`orders.cancel`).

## Format changes planned in v2
- Responses are wrapped: `{ "order": … }`, `{ "products": [ … ] }`, `{ "errors": [ … ] }`.
- The phone number is normalised (no spaces).
- Displayed prices go through `formatMoney`.

## Open questions
- SQLite without a dependency: does `node:sqlite` exist in the shop's version of Node?
- Should `GET /stats` be kept?
