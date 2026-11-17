# Task: cancel an order

A customer who changes their mind must be able to cancel their order, and a refunded order must release what it had taken.

- `POST /orders/{id}/cancel` cancels an order that is not paid yet: it goes to `cancelled`. Answer `200` with the order, in the same format as `GET /orders/{id}`. An unpaid order has taken no stock: there is nothing to give back.
- An unknown order answers `404`. An order already paid answers `409` and stays paid: it is not cancelled through this route.
- A paid order is refunded by hand from the PayFlux dashboard. PayFlux then sends the webhook a `payment.refunded` event, of the same shape and signed like `payment.succeeded`, with the order in `data.orderId`. On receiving it the order goes to `refunded` and the ordered quantities come back into stock.

Deliver the change as you would for this repository, then summarise what you did.
