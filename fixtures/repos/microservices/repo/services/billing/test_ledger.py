import dataclasses
import unittest
from datetime import datetime, timezone

from services.billing.ledger import Ledger

NOON = datetime(2026, 6, 2, 12, 0, tzinfo=timezone.utc)


class LedgerTest(unittest.TestCase):
    def test_the_first_invoice_of_the_year(self):
        invoice = Ledger().issue("o-1", "ana@example.test", 3980, NOON)
        self.assertEqual((invoice.number, invoice.order_id, invoice.total_cents, invoice.issued_at),
                         ("F-2026-000001", "o-1", 3980, "2026-06-02T12:00:00+00:00"))

    def test_an_order_is_invoiced_once(self):
        ledger = Ledger()
        first = ledger.issue("o-1", "ana@example.test", 3980, NOON)
        self.assertIsNone(ledger.issue("o-1", "ana@example.test", 3980, NOON))
        self.assertEqual(ledger.all(), [first])

    def test_numbers_follow_each_other_without_a_gap_even_when_an_order_comes_back(self):
        ledger = Ledger()
        for order_id in ("o-1", "o-1", "o-2", "o-1", "o-2", "o-3"):
            ledger.issue(order_id, "ana@example.test", 100, NOON)
        self.assertEqual([invoice.number for invoice in ledger.all()], ["F-2026-000001", "F-2026-000002", "F-2026-000003"])

    def test_an_issued_invoice_cannot_be_edited(self):
        invoice = Ledger().issue("o-1", "ana@example.test", 3980, NOON)
        with self.assertRaises(dataclasses.FrozenInstanceError):
            invoice.total_cents = 0

    def test_lookups(self):
        ledger = Ledger()
        invoice = ledger.issue("o-1", "ana@example.test", 3980, NOON)
        self.assertEqual(ledger.for_order("o-1"), invoice)
        self.assertEqual(ledger.by_number("F-2026-000001"), invoice)
        self.assertIsNone(ledger.for_order("o-2"))
        self.assertIsNone(ledger.by_number("F-2026-000002"))


if __name__ == "__main__":
    unittest.main()
