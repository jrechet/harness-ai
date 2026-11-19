# comptoir

The back office of an online shop, in three Python services: `orders` takes orders, `billing` issues invoices, `notifications` writes to customers. Standard library only, Python 3.10 or later. The services share no business code: they talk through events and APIs described in `contracts/`.


The production broker's client is not in this repository: without `BROKER_URL`, the bus is in memory.

## Getting started

```bash
python3 -m unittest discover                             # all the tests
python3 -m unittest discover -s services/billing -t .    # a single service
python3 tools/check_imports.py                           # boundaries between services
PORT=8001 python3 -m services.orders.app                 # one service alone, bus in memory
docker compose up                                        # the three services and a local broker
```

## Layout

```
contracts/api/            what the APIs answer, in JSON Schema
contracts/events/         the events, in JSON Schema
services/orders/          order taking, catalog
services/billing/         invoices, numbering
services/notifications/   emails to the customer
shared/                   the bus and the HTTP adapter
tools/                    schema validator, import check
docs/                     decisions, incidents, operations
```

## API

| Service | Method | Path | Role |
|---|---|---|---|
| orders | POST | `/orders` | place an order: `customer_email`, `sku`, `quantity` |
| orders | GET | `/orders/{id}` | read an order |
| billing | GET | `/invoices` | the invoices; `?order_id=` for those of one order |
| billing | GET | `/invoices/{number}` | read an invoice |
| notifications | GET | `/outbox` | the messages handed to the mail relay |

## Events

| Event | Published by | Read by |
|---|---|---|
| `order.created` | orders | billing, notifications, and consumers outside this repository |
| `invoice.issued` | billing | notifications, and consumers outside this repository |

Every event travels in the same envelope: `id`, `type`, `occurred_at`, `payload`.

## Assembling services in a test

Each service exposes `create_app(bus)`. The object returned answers `handle(method, path, body)` with `(status, response)`; it is what `shared/http.py` serves over HTTP.

```python
from shared.bus import InMemoryBus
from services.orders.app import create_app

bus = InMemoryBus()
orders = create_app(bus)
status, order = orders.handle("POST", "/orders", {"customer_email": "ana@example.test", "sku": "MUG", "quantity": 1})
events = bus.published("order.created")
```

See `docs/` for the decisions, the incidents and operations.
