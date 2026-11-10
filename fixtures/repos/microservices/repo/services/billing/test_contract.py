"""Provider side of the contract: what this service really publishes and answers
matches the schemas of contracts/. The schemas are strict, so a field that leaves
the service without being declared fails here."""
import unittest

from services.billing.app import create_app
from services.billing.test_app import order_created
from shared.bus import InMemoryBus
from tools.schema import contract, validate


def invoice_an_order():
    bus = InMemoryBus()
    app = create_app(bus)
    bus.publish(order_created())
    return app, bus


class BillingContractTest(unittest.TestCase):
    def test_the_published_event_matches_its_contract(self):
        _app, bus = invoice_an_order()
        (event,) = bus.published("invoice.issued")
        self.assertEqual(validate(event, contract("events/invoice.issued")), [])

    def test_the_answers_of_the_api_match_their_contract(self):
        app, _bus = invoice_an_order()
        _status, listed = app.handle("GET", "/invoices")
        (invoice,) = listed["invoices"]
        _status, read = app.handle("GET", f"/invoices/{invoice['number']}")
        for answer in (invoice, read):
            self.assertEqual(validate(answer, contract("api/invoice")), [])

    def test_a_field_published_without_being_declared_would_fail(self):
        _app, bus = invoice_an_order()
        (event,) = bus.published("invoice.issued")
        event["payload"]["due_date"] = "2026-07-02"
        self.assertEqual(validate(event, contract("events/invoice.issued")), ["$.payload.due_date: not declared in the contract"])


if __name__ == "__main__":
    unittest.main()
