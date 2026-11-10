import unittest
from datetime import datetime, timezone

from services.orders.app import create_app
from shared.bus import InMemoryBus

NOON = datetime(2026, 6, 2, 12, 0, tzinfo=timezone.utc)
TWO_SHIRTS = {"customer_email": "ana@example.test", "sku": "TSHIRT-M", "quantity": 2}


def make():
    bus = InMemoryBus()
    numbers = iter(range(1, 100))
    return create_app(bus, clock=lambda: NOON, new_id=lambda: f"{next(numbers):04d}"), bus


class CreateOrderTest(unittest.TestCase):
    def test_an_order_is_priced_from_the_catalog(self):
        app, _bus = make()
        status, order = app.handle("POST", "/orders", TWO_SHIRTS)
        self.assertEqual(status, 201)
        self.assertEqual(order, {"id": "o-0001", "customer_email": "ana@example.test", "sku": "TSHIRT-M",
                                 "quantity": 2, "total_cents": 3980, "created_at": "2026-06-02T12:00:00+00:00"})

    def test_an_accepted_order_is_announced_once_with_a_stable_id(self):
        app, bus = make()
        app.handle("POST", "/orders", TWO_SHIRTS)
        events = bus.published("order.created")
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["id"], "order.created:o-0001")
        self.assertEqual(events[0]["payload"], {"order_id": "o-0001", "customer_email": "ana@example.test",
                                                "sku": "TSHIRT-M", "quantity": 2, "total_cents": 3980,
                                                "created_at": "2026-06-02T12:00:00+00:00"})

    def test_an_invalid_order_is_refused_and_announces_nothing(self):
        cases = {
            "no e-mail": {**TWO_SHIRTS, "customer_email": "ana"},
            "unknown article": {**TWO_SHIRTS, "sku": "UMBRELLA"},
            "zero quantity": {**TWO_SHIRTS, "quantity": 0},
            "fractional quantity": {**TWO_SHIRTS, "quantity": 1.5},
            "true is not a quantity": {**TWO_SHIRTS, "quantity": True},
            "not an object": ["TSHIRT-M"],
        }
        for name, body in cases.items():
            with self.subTest(name):
                app, bus = make()
                status, answer = app.handle("POST", "/orders", body)
                self.assertEqual((status, answer["error"]), (422, "invalid_order"))
                self.assertEqual(bus.published(), [])

    def test_every_problem_of_an_order_is_listed(self):
        app, _bus = make()
        _status, answer = app.handle("POST", "/orders", {"sku": "UMBRELLA", "quantity": 0})
        self.assertEqual(len(answer["details"]), 3)


class ReadOrderTest(unittest.TestCase):
    def test_an_order_reads_back_as_it_was_answered(self):
        app, _bus = make()
        _status, created = app.handle("POST", "/orders", TWO_SHIRTS)
        self.assertEqual(app.handle("GET", f"/orders/{created['id']}"), (200, created))

    def test_an_unknown_order_and_an_unknown_route_are_404(self):
        app, _bus = make()
        self.assertEqual(app.handle("GET", "/orders/o-9999"), (404, {"error": "order_not_found"}))
        self.assertEqual(app.handle("DELETE", "/orders/o-0001")[0], 404)


if __name__ == "__main__":
    unittest.main()
