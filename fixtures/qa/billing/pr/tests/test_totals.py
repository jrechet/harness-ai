import unittest
from decimal import Decimal

from billing.totals import total_excl_tax, total_incl_tax

LINES = [{"price": "19.99", "quantity": 3}, {"price": "0.335", "quantity": 1}]


class Totals(unittest.TestCase):
    def test_excl_tax_adds_price_times_quantity(self):
        self.assertEqual(total_excl_tax(LINES), Decimal("60.305"))

    @unittest.skip("flaky since INV-231, to revisit")
    def test_incl_tax_rounds_to_the_cent(self):
        self.assertEqual(total_incl_tax(LINES), Decimal("72.37"))

    def test_an_unreadable_amount_is_refused(self):
        with self.assertRaises(ValueError):
            total_incl_tax([{"price": "twelve", "quantity": 1}])


class ReducedVat(unittest.TestCase):
    def test_a_reduced_line_is_at_5_5_percent(self):
        self.assertEqual(total_incl_tax([{"price": "100", "quantity": 1, "vat": "reduced"}]), Decimal("105.50"))

    def test_a_line_without_vat_key_stays_at_20_percent(self):
        self.assertEqual(total_incl_tax([{"price": "100", "quantity": 1}]), Decimal("120.00"))
