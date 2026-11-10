"""Consumer and API tests. Every event goes through the bus, which delivers it twice:
each test here is also a test of what a redelivery does."""
import unittest
from datetime import datetime, timezone

from services.billing.app import create_app
from shared.bus import InMemoryBus

NOON = datetime(2026, 6, 2, 12, 0, tzinfo=timezone.utc)


def order_created(order_id="o-1", total_cents=3980):
    return {
        "id": f"order.created:{order_id}",
        "type": "order.created",
        "occurred_at": "2026-06-02T11:59:58+00:00",
        "payload": {"order_id": order_id, "customer_email": "ana@example.test", "sku": "TSHIRT-M", "quantity": 2,
                    "total_cents": total_cents, "created_at": "2026-06-02T11:59:58+00:00"},
    }


def make():
    bus = InMemoryBus()
    return create_app(bus, clock=lambda: NOON), bus


class OrderCreatedConsumerTest(unittest.TestCase):
    def test_an_order_gets_one_invoice_though_its_event_is_delivered_twice(self):
        app, bus = make()
        bus.publish(order_created())
        _status, answer = app.handle("GET", "/invoices")
        self.assertEqual(answer["invoices"], [{"number": "F-2026-000001", "order_id": "o-1",
                                               "customer_email": "ana@example.test", "total_cents": 3980,
                                               "issued_at": "2026-06-02T12:00:00+00:00"}])

    def test_the_invoice_is_announced_once_with_a_stable_id(self):
        _app, bus = make()
        bus.publish(order_created())
        events = bus.published("invoice.issued")
        self.assertEqual([event["id"] for event in events], ["invoice.issued:F-2026-000001"])
        self.assertEqual(events[0]["payload"], {"invoice_number": "F-2026-000001", "order_id": "o-1",
                                                "customer_email": "ana@example.test", "total_cents": 3980,
                                                "issued_at": "2026-06-02T12:00:00+00:00"})

    def test_an_event_published_again_later_changes_nothing(self):
        app, bus = make()
        bus.publish(order_created("o-1"))
        bus.publish(order_created("o-2", total_cents=950))
        bus.publish(order_created("o-1"))
        _status, answer = app.handle("GET", "/invoices")
        self.assertEqual([(invoice["number"], invoice["order_id"]) for invoice in answer["invoices"]],
                         [("F-2026-000001", "o-1"), ("F-2026-000002", "o-2")])
        self.assertEqual(len(bus.published("invoice.issued")), 2)


class InvoicesApiTest(unittest.TestCase):
    def setUp(self):
        self.app, bus = make()
        bus.publish(order_created("o-1"))
        bus.publish(order_created("o-2", total_cents=950))

    def test_invoices_can_be_filtered_by_order(self):
        _status, answer = self.app.handle("GET", "/invoices?order_id=o-2")
        self.assertEqual([invoice["number"] for invoice in answer["invoices"]], ["F-2026-000002"])
        self.assertEqual(self.app.handle("GET", "/invoices?order_id=o-9"), (200, {"invoices": []}))

    def test_an_invoice_is_read_by_its_number(self):
        status, invoice = self.app.handle("GET", "/invoices/F-2026-000002")
        self.assertEqual((status, invoice["order_id"], invoice["total_cents"]), (200, "o-2", 950))

    def test_an_unknown_invoice_and_an_unknown_route_are_404(self):
        self.assertEqual(self.app.handle("GET", "/invoices/F-2026-000009"), (404, {"error": "invoice_not_found"}))
        self.assertEqual(self.app.handle("POST", "/invoices")[0], 404)


if __name__ == "__main__":
    unittest.main()
