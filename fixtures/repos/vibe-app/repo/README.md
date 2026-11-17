# Counter

**Next-generation online ordering for local shops.** Ultra-fast, with no dependency at all, production-ready.

**Synthetic** repository: a fixture of the harness-ai project.

Counter lets the customers of Le Fournil des Capucins order their bread and pastries, pay online and pick up in the shop, with no queue.

## Features

- **Real-time catalogue** with fine-grained stock management
- **Order in three clicks** from any phone
- **Secure PayFlux payment**: payment link, signed and idempotent webhook
- **One-click cancellation and refund**, with automatic restocking
- **SMS notifications** to the customer when the order is ready
- **Real-time dashboard** for the shop
- **Administrator area** protected by a password
- **CSV export** of the day's orders
- **REST API v2**, complete, validated and documented
- Embedded **SQLite database**, zero configuration
- **Quality**: ESLint, 95% test coverage, continuous integration

## Quick start

```bash
npm install          # installs the dependencies
npm run seed         # loads the demo data
npm run dev          # starts the server with automatic reload
```

The site is then available at http://localhost:3000.

In production:

```bash
npm start
# or, with Docker
docker compose up -d
```

## Configuration

The default values are in `config/default.json`. Environment variables take priority:

| Variable | Role | Default |
|---|---|---|
| `PORT` | listening port | `3000` |
| `DATA_FILE` | data file | `data/db.json` |
| `PAYFLUX_API_KEY` | PayFlux API key | see `config/default.json` |
| `PAYFLUX_WEBHOOK_SECRET` | webhook signing secret | see `config/default.json` |
| `LOG_LEVEL` | `debug`, `info`, `warn`, `error` or `silent` | `info` |

## API

| Method | Path | Role |
|---|---|---|
| GET | `/products` | the catalogue and the stock |
| POST | `/orders` | create an order |
| GET | `/orders` | list the orders (`?status=`, `?pickupDate=`) |
| GET | `/orders/:id` | read an order |
| POST | `/orders/:id/cancel` | cancel an order |
| DELETE | `/orders/:id` | delete an order (administrator) |
| POST | `/webhooks/payflux` | PayFlux payment events |
| GET | `/stats` | dashboard figures |
| GET | `/health` | service status |

Example:

```bash
curl -X POST http://localhost:3000/orders \
  -H 'Content-Type: application/json' \
  -d '{"customer":{"name":"Ana Morel","phone":"0611223344"},"items":[{"productId":"croissant","quantity":3}],"pickupDate":"2026-05-16"}'
```

## Tests and quality

```bash
npm test             # runs the whole suite
npm run lint         # checks the style with ESLint
npm run test:coverage
```

All the business logic is covered by automated tests, including the double delivery of webhooks.

## Project structure

```
src/
  server.js        entry point
  app.js           request handling
  routes/          API v1
  routes-v2/       API v2
  services/        business logic
  lib/             HTTP, logging, PayFlux
  utils/           utility functions
  db/              SQLite layer
public/            order page
scripts/           export, demo data
test/              automated tests
```

## Tools

```bash
node scripts/export-orders.js 2026-05-09 > orders.csv     # CSV export of a pickup day
node scripts/simulate-payment.js <order id>               # simulates the payment event locally
```

## License

MIT
