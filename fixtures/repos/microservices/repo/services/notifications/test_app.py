"""Every event goes through the bus, which delivers it twice: each test here is also
a test of what a redelivery does."""
import unittest

from services.notifications.app import create_app, euros
from shared.bus import InMemoryBus


def order_created(order_id="o-1"):
    return {
        "id": f"order.created:{order_id}",
        "type": "order.created",
        "occurred_at": "2026-06-02T12:00:00+00:00",
        "payload": {"order_id": order_id, "customer_email": "ana@example.test", "sku": "TSHIRT-M", "quantity": 2,
                    "total_cents": 3980, "created_at": "2026-06-02T12:00:00+00:00"},
    }


def invoice_issued(number="F-2026-000001", order_id="o-1"):
    return {
        "id": f"invoice.issued:{number}",
        "type": "invoice.issued",
        "occurred_at": "2026-06-02T12:00:01+00:00",
        "payload": {"invoice_number": number, "order_id": order_id, "customer_email": "ana@example.test",
                    "total_cents": 3980, "issued_at": "2026-06-02T12:00:01+00:00"},
    }


class NotificationsTest(unittest.TestCase):
    def setUp(self):
        self.bus = InMemoryBus()
        self.app = create_app(self.bus)

    def messages(self):
        status, answer = self.app.handle("GET", "/outbox")
        self.assertEqual(status, 200)
        return answer["messages"]

    def test_an_order_is_confirmed_once_though_its_event_is_delivered_twice(self):
        self.bus.publish(order_created())
        self.assertEqual(self.messages(), [{"to": "ana@example.test", "subject": "Votre commande o-1",
                                            "body": "2 × TSHIRT-M, total 39,80 €."}])

    def test_an_invoice_is_sent_once(self):
        self.bus.publish(invoice_issued())
        self.assertEqual(self.messages(), [{"to": "ana@example.test", "subject": "Votre facture F-2026-000001",
                                            "body": "Commande o-1, total 39,80 €."}])

    def test_an_event_published_again_later_sends_nothing_more(self):
        self.bus.publish(order_created("o-1"))
        self.bus.publish(invoice_issued())
        self.bus.publish(order_created("o-2"))
        self.bus.publish(order_created("o-1"))
        self.bus.publish(invoice_issued())
        self.assertEqual([message["subject"] for message in self.messages()],
                         ["Votre commande o-1", "Votre facture F-2026-000001", "Votre commande o-2"])

    def test_amounts_are_written_the_french_way(self):
        self.assertEqual([euros(5), euros(950), euros(123456)], ["0,05 €", "9,50 €", "1234,56 €"])

    def test_an_unknown_route_is_404(self):
        self.assertEqual(self.app.handle("GET", "/inbox")[0], 404)


if __name__ == "__main__":
    unittest.main()
