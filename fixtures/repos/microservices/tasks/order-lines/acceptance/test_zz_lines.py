"""Hidden acceptance test of the order-lines task: the feature, as the statement gives it.

It only uses what the README calls the surface of a service: create_app(bus), handle()
and the bus. Answers go through JSON, as they would over HTTP.
"""
import json
import os
import unittest

from services.billing.app import create_app as create_billing
from services.orders.app import create_app as create_orders
from shared.bus import InMemoryBus
from tools.schema import validate

CONTRACTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "contracts")
BASKET = {"customer_email": "ana@example.test",
          "lines": [{"sku": "TSHIRT-M", "quantity": 2}, {"sku": "MUG", "quantity": 1}]}
PRICED = [{"sku": "TSHIRT-M", "quantity": 2, "unit_price_cents": 1990},
          {"sku": "MUG", "quantity": 1, "unit_price_cents": 950}]
INVOICED = [{**PRICED[0], "amount_cents": 3980}, {**PRICED[1], "amount_cents": 950}]


def call(app, method, path, body=None):
    status, answer = app.handle(method, path, body)
    return status, json.loads(json.dumps(answer))


def lines_of(holder, like):
    """The lines of an answer or of a payload, reduced to the keys the statement names."""
    return [{key: line[key] for key in like[0]} for line in holder["lines"]]


def schema(name):
    with open(os.path.join(CONTRACTS, name + ".json"), encoding="utf-8") as fh:
        return json.load(fh)


class OrderLinesAcceptanceTest(unittest.TestCase):
    def setUp(self):
        self.bus = InMemoryBus()
        self.orders = create_orders(self.bus)
        self.billing = create_billing(self.bus)

    def place(self, body=BASKET):
        status, order = call(self.orders, "POST", "/orders", body)
        self.assertEqual(status, 201, order)
        return order

    def test_an_order_of_several_lines_is_priced_line_by_line(self):
        order = self.place()
        self.assertEqual(order["total_cents"], 4930)
        self.assertEqual(lines_of(order, PRICED), PRICED)
        status, read = call(self.orders, "GET", f"/orders/{order['id']}")
        self.assertEqual(status, 200)
        self.assertEqual((read["total_cents"], lines_of(read, PRICED)), (4930, PRICED))

    def published(self, event_type=None):
        return json.loads(json.dumps(self.bus.published(event_type)))

    def test_the_event_carries_the_lines(self):
        order = self.place()
        events = self.published("order.created")
        self.assertEqual(len(events), 1)
        payload = events[0]["payload"]
        self.assertEqual((payload["order_id"], payload["total_cents"]), (order["id"], 4930))
        self.assertEqual(lines_of(payload, PRICED), PRICED)

    def test_the_invoice_details_the_lines(self):
        order = self.place()
        status, answer = call(self.billing, "GET", f"/invoices?order_id={order['id']}")
        self.assertEqual(status, 200)
        self.assertEqual(len(answer["invoices"]), 1, answer)
        invoice = answer["invoices"][0]
        self.assertEqual(invoice["total_cents"], 4930)
        self.assertEqual(lines_of(invoice, INVOICED), INVOICED)

    def test_a_line_of_zero_or_of_an_unknown_article_is_refused(self):
        for bad in ({"sku": "MUG", "quantity": 0}, {"sku": "UMBRELLA", "quantity": 1}):
            with self.subTest(line=bad):
                body = {"customer_email": "ana@example.test", "lines": [{"sku": "TSHIRT-M", "quantity": 1}, bad]}
                status, _answer = call(self.orders, "POST", "/orders", body)
                self.assertEqual(status, 422)
        status, _answer = call(self.orders, "POST", "/orders", {"customer_email": "ana@example.test", "lines": []})
        self.assertEqual(status // 100, 4, "an order needs at least one line")
        self.assertEqual(self.published(), [], "a refused order announces nothing")

    def test_what_leaves_the_services_is_what_contracts_declares(self):
        order = self.place()
        (event,) = self.published("order.created")
        _status, answer = call(self.billing, "GET", f"/invoices?order_id={order['id']}")
        self.assertEqual(validate(event, schema("events/order.created")), [])
        self.assertEqual(validate(order, schema("api/order")), [])
        self.assertEqual(validate(answer["invoices"][0], schema("api/invoice")), [])
        event["payload"]["coupon"] = "WELCOME"
        self.assertNotEqual(validate(event, schema("events/order.created")), [],
                            "the contract was loosened instead of being updated: an undeclared field passes")


if __name__ == "__main__":
    unittest.main()
