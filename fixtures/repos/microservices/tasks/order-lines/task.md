# Task: several items per order

Today an order carries a single item (`sku`, `quantity`). Customers want to put several in the same order, and the invoice must itemise them.

- `POST /orders` accepts `lines`, a list of `{"sku": …, "quantity": …}`, at least one line. The order total is the sum of the lines, at catalog prices.
- `GET /orders/{id}` returns these lines, each with `sku`, `quantity` and `unit_price_cents`.
- The `order.created` event carries these same lines.
- The invoice takes them up: `GET /invoices?order_id=…` returns, for each invoice, `lines` with `sku`, `quantity`, `unit_price_cents` and `amount_cents`.
- A line whose quantity is zero, or whose item is not in the catalog, answers `422`.

Deliver the change as you would for a PR of this repository, then summarise what you did.
