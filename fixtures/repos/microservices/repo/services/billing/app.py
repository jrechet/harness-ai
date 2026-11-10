"""Billing service: issues one invoice per order and announces it.

    consumes  order.created
    publishes invoice.issued
    GET /invoices[?order_id=...]     200, {"invoices": [...]}
    GET /invoices/{number}           200, the invoice

What it answers and what it publishes is described in contracts/ (api/invoice,
events/invoice.issued); test_contract.py holds the service to it.
"""
from __future__ import annotations

import os
from dataclasses import asdict
from datetime import datetime, timezone
from typing import Any, Callable
from urllib.parse import parse_qs, urlsplit

from services.billing.ledger import Ledger
from shared.bus import Bus, Event, connect, envelope

Response = tuple[int, dict[str, Any]]


class BillingApp:
    def __init__(self, bus: Bus, clock: Callable[[], datetime]) -> None:
        self.bus = bus
        self.clock = clock
        self.ledger = Ledger()
        bus.subscribe("order.created", self.on_order_created)

    def on_order_created(self, event: Event) -> None:
        order = event["payload"]
        invoice = self.ledger.issue(order["order_id"], order["customer_email"], order["total_cents"], self.clock())
        if invoice is None:
            return  # delivered again: this order is already invoiced
        payload = {"invoice_number": invoice.number, "order_id": invoice.order_id,
                   "customer_email": invoice.customer_email, "total_cents": invoice.total_cents,
                   "issued_at": invoice.issued_at}
        self.bus.publish(envelope("invoice.issued", f"invoice.issued:{invoice.number}", invoice.issued_at, payload))

    def handle(self, method: str, path: str, body: Any = None) -> Response:
        url = urlsplit(path)
        if method == "GET" and url.path == "/invoices":
            wanted = parse_qs(url.query).get("order_id")
            invoices = [invoice for invoice in self.ledger.all() if not wanted or invoice.order_id in wanted]
            return 200, {"invoices": [asdict(invoice) for invoice in invoices]}
        if method == "GET" and url.path.startswith("/invoices/"):
            invoice = self.ledger.by_number(url.path[len("/invoices/"):])
            if invoice is None:
                return 404, {"error": "invoice_not_found"}
            return 200, asdict(invoice)
        return 404, {"error": "not_found"}


def create_app(bus: Bus, clock: Callable[[], datetime] | None = None) -> BillingApp:
    return BillingApp(bus, clock or (lambda: datetime.now(timezone.utc)))


if __name__ == "__main__":
    from shared.http import serve

    serve(create_app(connect()), int(os.environ.get("PORT", "8002")))
