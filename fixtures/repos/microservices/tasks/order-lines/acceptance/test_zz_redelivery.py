"""Hidden acceptance test of the order-lines task: the broker delivers at least once.

The events are the ones the orders service of the solution publishes; they are then
published again, as the broker does after a lost acknowledgement.
"""
import json
import unittest

from services.billing.app import create_app as create_billing
from services.orders.app import create_app as create_orders
from shared.bus import InMemoryBus

BASKET = {"customer_email": "ana@example.test",
          "lines": [{"sku": "TSHIRT-M", "quantity": 2}, {"sku": "MUG", "quantity": 1}]}
POSTER = {"customer_email": "bob@example.test", "lines": [{"sku": "POSTER-A2", "quantity": 1}]}


def call(app, method, path, body=None):
    status, answer = app.handle(method, path, body)
    return status, json.loads(json.dumps(answer))


class RedeliveryAcceptanceTest(unittest.TestCase):
    def setUp(self):
        self.bus = InMemoryBus()
        self.orders = create_orders(self.bus)
        self.billing = create_billing(self.bus)

    def place(self, body):
        status, order = call(self.orders, "POST", "/orders", body)
        self.assertEqual(status, 201, order)
        return order, self.bus.published("order.created")[-1]

    def invoices(self, query=""):
        status, answer = call(self.billing, "GET", "/invoices" + query)
        self.assertEqual(status, 200)
        return answer["invoices"]

    def test_an_order_delivered_again_has_one_invoice_and_its_lines_once(self):
        order, event = self.place(BASKET)
        self.bus.publish(event)
        self.bus.publish(event)
        invoices = self.invoices(f"?order_id={order['id']}")
        self.assertEqual(len(invoices), 1, "an order delivered again was invoiced again")
        self.assertEqual(invoices[0]["total_cents"], 4930)
        self.assertEqual([(line["sku"], line["quantity"]) for line in invoices[0]["lines"]], [("TSHIRT-M", 2), ("MUG", 1)],
                         "the lines of an order delivered again were invoiced again")

    def test_a_redelivery_burns_no_invoice_number(self):
        _first, first_event = self.place(BASKET)
        self.bus.publish(first_event)
        _second, second_event = self.place(POSTER)
        self.bus.publish(first_event)
        self.bus.publish(second_event)
        _third, _event = self.place(BASKET)
        numbers = [int(invoice["number"].rsplit("-", 1)[1]) for invoice in self.invoices()]
        self.assertEqual(len(numbers), 3)
        self.assertEqual(sorted(numbers), list(range(min(numbers), min(numbers) + 3)),
                         "invoice numbers must follow each other without a gap")


if __name__ == "__main__":
    unittest.main()
