"""Hidden acceptance test of the order-lines task: the readers written before the change.

`order.created` is read outside the repository and the orders API has clients. This file
replays one of each exactly as it was written against contracts/ before the task: it
reads what the contract promised then, and nothing the task adds.

Orders are placed the way the statement gives, with `lines`; whether the body of the
first API is still accepted is not measured here.
"""
import json
import os
import unittest

from services.orders.app import create_app as create_orders
from shared.bus import InMemoryBus
from tools.schema import validate

CONTRACTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "contracts")
ONE_ARTICLE = {"customer_email": "ana@example.test", "lines": [{"sku": "TSHIRT-M", "quantity": 2}]}
BASKET = {"customer_email": "ana@example.test",
          "lines": [{"sku": "TSHIRT-M", "quantity": 2}, {"sku": "MUG", "quantity": 1}]}
# The payload of order.created and the answer of the orders API, as contracts/ described them before the task.
OLD_PAYLOAD = {"order_id": str, "customer_email": str, "sku": str, "quantity": int, "total_cents": int, "created_at": str}
OLD_ORDER = {"id": str, "customer_email": str, "sku": str, "quantity": int, "total_cents": int, "created_at": str}


def old_confirmation(event):
    """The confirmation e-mail, as a consumer builds it from the event it was written against."""
    order = event["payload"]
    cents = order["total_cents"]
    return {
        "to": order["customer_email"],
        "subject": f"Votre commande {order['order_id']}",
        "body": f"{order['quantity']} × {order['sku']}, total {cents // 100},{cents % 100:02d} €.",
    }


def call(app, method, path, body=None):
    status, answer = app.handle(method, path, body)
    return status, json.loads(json.dumps(answer))


def schema(name):
    with open(os.path.join(CONTRACTS, name + ".json"), encoding="utf-8") as fh:
        return json.load(fh)


class OldReadersTest(unittest.TestCase):
    def setUp(self):
        self.bus = InMemoryBus()
        self.orders = create_orders(self.bus)
        self.received = {}
        self.bus.subscribe("order.created", lambda event: self.received.update({event["id"]: event}))

    def place(self, body):
        status, order = call(self.orders, "POST", "/orders", body)
        self.assertEqual(status, 201, f"{body} answered {status}: {order}")
        (event,) = self.received.values()
        return order, json.loads(json.dumps(event))

    def assert_shaped_like(self, old_shape, got, what):
        for field, kind in old_shape.items():
            self.assertIn(field, got, f"{what} lost `{field}`: a reader written before the change breaks")
            self.assertTrue(isinstance(got[field], kind) and not isinstance(got[field], bool),
                            f"{what}: `{field}` is no longer a {kind.__name__}")

    def test_an_old_client_reads_an_order_of_one_article_as_before(self):
        order, _event = self.place(ONE_ARTICLE)
        self.assert_shaped_like(OLD_ORDER, order, "the answer of POST /orders")
        self.assertEqual((order["customer_email"], order["sku"], order["quantity"], order["total_cents"]),
                         ("ana@example.test", "TSHIRT-M", 2, 3980))
        status, read = call(self.orders, "GET", f"/orders/{order['id']}")
        self.assertEqual(status, 200)
        self.assertEqual({field: read[field] for field in OLD_ORDER}, {field: order[field] for field in OLD_ORDER})

    def test_an_old_consumer_reads_an_order_of_one_article_as_before(self):
        order, event = self.place(ONE_ARTICLE)
        self.assert_shaped_like(OLD_PAYLOAD, event["payload"], "the payload of order.created")
        self.assertEqual(old_confirmation(event), {"to": "ana@example.test", "subject": f"Votre commande {order['id']}",
                                                   "body": "2 × TSHIRT-M, total 39,80 €."})

    def test_an_old_consumer_survives_an_order_of_several_lines(self):
        order, event = self.place(BASKET)
        self.assert_shaped_like(OLD_PAYLOAD, event["payload"], "the payload of order.created")
        payload = event["payload"]
        self.assertEqual((payload["order_id"], payload["customer_email"], payload["total_cents"]),
                         (order["id"], "ana@example.test", 4930))
        self.assertIn(payload["sku"], ("TSHIRT-M", "MUG"))
        self.assertGreaterEqual(payload["quantity"], 1)
        self.assertEqual(old_confirmation(event)["to"], "ana@example.test")

    def test_an_old_client_still_reads_an_order_of_several_lines(self):
        order, _event = self.place(BASKET)
        status, read = call(self.orders, "GET", f"/orders/{order['id']}")
        self.assertEqual(status, 200)
        self.assert_shaped_like(OLD_ORDER, read, "the answer of GET /orders/{id}")
        self.assertEqual(read["total_cents"], 4930)

    def test_the_contracts_still_promise_every_field_they_promised(self):
        order, event = self.place(BASKET)
        for field in OLD_PAYLOAD:
            without = {**event, "payload": {key: value for key, value in event["payload"].items() if key != field}}
            self.assertNotEqual(validate(without, schema("events/order.created")), [],
                                f"contracts/events/order.created.json no longer requires `{field}`")
        for field in OLD_ORDER:
            without = {key: value for key, value in order.items() if key != field}
            self.assertNotEqual(validate(without, schema("api/order")), [],
                                f"contracts/api/order.json no longer requires `{field}`")


if __name__ == "__main__":
    unittest.main()
