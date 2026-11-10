"""Notifications service: writes to the customer when an order is taken and when it is invoiced.

    consumes  order.created, invoice.issued
    GET /outbox      200, {"messages": [...]}     what was handed to the mail relay

The mail relay is outside this repository; here a message ends in the outbox.
"""
from __future__ import annotations

import os
from typing import Any

from shared.bus import Bus, Event, connect

Response = tuple[int, dict[str, Any]]


def euros(cents: int) -> str:
    return f"{cents // 100},{cents % 100:02d} €"


class NotificationsApp:
    def __init__(self, bus: Bus) -> None:
        self.outbox: list[dict[str, str]] = []
        self._handled: set[str] = set()
        bus.subscribe("order.created", self.on_order_created)
        bus.subscribe("invoice.issued", self.on_invoice_issued)

    def _first_time(self, event: Event) -> bool:
        """False when this event was already handled: the broker delivers at least once."""
        if event["id"] in self._handled:
            return False
        self._handled.add(event["id"])
        return True

    def on_order_created(self, event: Event) -> None:
        if not self._first_time(event):
            return
        order = event["payload"]
        self.outbox.append({
            "to": order["customer_email"],
            "subject": f"Votre commande {order['order_id']}",
            "body": f"{order['quantity']} × {order['sku']}, total {euros(order['total_cents'])}.",
        })

    def on_invoice_issued(self, event: Event) -> None:
        if not self._first_time(event):
            return
        invoice = event["payload"]
        self.outbox.append({
            "to": invoice["customer_email"],
            "subject": f"Votre facture {invoice['invoice_number']}",
            "body": f"Commande {invoice['order_id']}, total {euros(invoice['total_cents'])}.",
        })

    def handle(self, method: str, path: str, body: Any = None) -> Response:
        if method == "GET" and path == "/outbox":
            return 200, {"messages": list(self.outbox)}
        return 404, {"error": "not_found"}


def create_app(bus: Bus) -> NotificationsApp:
    return NotificationsApp(bus)


if __name__ == "__main__":
    from shared.http import serve

    serve(create_app(connect()), int(os.environ.get("PORT", "8003")))
