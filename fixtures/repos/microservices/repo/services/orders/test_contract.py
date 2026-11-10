"""Provider side of the contract: what this service really publishes and answers
matches the schemas of contracts/. The schemas are strict, so a field that leaves
the service without being declared fails here."""
import unittest

from services.orders.app import create_app
from shared.bus import InMemoryBus
from tools.schema import contract, validate


def place_an_order():
    bus = InMemoryBus()
    app = create_app(bus)
    _status, order = app.handle("POST", "/orders", {"customer_email": "ana@example.test", "sku": "MUG", "quantity": 3})
    return app, bus, order


class OrdersContractTest(unittest.TestCase):
    def test_the_published_event_matches_its_contract(self):
        _app, bus, _order = place_an_order()
        (event,) = bus.published("order.created")
        self.assertEqual(validate(event, contract("events/order.created")), [])

    def test_the_answers_of_the_api_match_their_contract(self):
        app, _bus, created = place_an_order()
        _status, read = app.handle("GET", f"/orders/{created['id']}")
        for answer in (created, read):
            self.assertEqual(validate(answer, contract("api/order")), [])

    def test_a_field_published_without_being_declared_would_fail(self):
        _app, bus, _order = place_an_order()
        (event,) = bus.published("order.created")
        event["payload"]["coupon"] = "WELCOME"
        self.assertEqual(validate(event, contract("events/order.created")), ["$.payload.coupon: not declared in the contract"])


if __name__ == "__main__":
    unittest.main()
