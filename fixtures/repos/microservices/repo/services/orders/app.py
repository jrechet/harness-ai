"""Orders service: accepts an order, prices it from the catalog, announces it.

    POST /orders        {"customer_email": ..., "sku": ..., "quantity": ...}   201, the order
    GET  /orders/{id}                                                            200, the order

What it answers and what it publishes is described in contracts/ (api/order,
events/order.created); test_contract.py holds the service to it.
"""
from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from typing import Any, Callable

from services.orders import catalog
from shared.bus import Bus, connect, envelope

Response = tuple[int, dict[str, Any]]


def _problems(body: Any) -> list[str]:
    if not isinstance(body, dict):
        return ["body: must be a JSON object"]
    problems = []
    email = body.get("customer_email")
    if not isinstance(email, str) or "@" not in email:
        problems.append("customer_email: must be an e-mail address")
    if not catalog.knows(body.get("sku")):
        problems.append("sku: unknown article")
    quantity = body.get("quantity")
    if not isinstance(quantity, int) or isinstance(quantity, bool) or quantity < 1:
        problems.append("quantity: must be an integer of at least 1")
    return problems


class OrdersApp:
    def __init__(self, bus: Bus, clock: Callable[[], datetime], new_id: Callable[[], str]) -> None:
        self.bus = bus
        self.clock = clock
        self.new_id = new_id
        self.orders: dict[str, dict[str, Any]] = {}

    def handle(self, method: str, path: str, body: Any = None) -> Response:
        if method == "POST" and path == "/orders":
            return self.create_order(body)
        if method == "GET" and path.startswith("/orders/"):
            return self.get_order(path[len("/orders/"):])
        return 404, {"error": "not_found"}

    def create_order(self, body: Any) -> Response:
        problems = _problems(body)
        if problems:
            return 422, {"error": "invalid_order", "details": problems}
        now = self.clock().isoformat(timespec="seconds")
        order = {
            "id": f"o-{self.new_id()}",
            "customer_email": body["customer_email"],
            "sku": body["sku"],
            "quantity": body["quantity"],
            "total_cents": catalog.unit_price_cents(body["sku"]) * body["quantity"],
            "created_at": now,
        }
        self.orders[order["id"]] = order
        payload = {"order_id": order["id"], **{key: value for key, value in order.items() if key != "id"}}
        self.bus.publish(envelope("order.created", f"order.created:{order['id']}", now, payload))
        return 201, dict(order)

    def get_order(self, order_id: str) -> Response:
        order = self.orders.get(order_id)
        if order is None:
            return 404, {"error": "order_not_found"}
        return 200, dict(order)


def create_app(bus: Bus, clock: Callable[[], datetime] | None = None,
               new_id: Callable[[], str] | None = None) -> OrdersApp:
    return OrdersApp(bus, clock or (lambda: datetime.now(timezone.utc)), new_id or (lambda: uuid.uuid4().hex[:12]))


if __name__ == "__main__":
    from shared.http import serve

    serve(create_app(connect()), int(os.environ.get("PORT", "8001")))
