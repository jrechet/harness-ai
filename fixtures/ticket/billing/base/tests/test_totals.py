import unittest
from decimal import Decimal

from billing.totals import total_excl_tax, total_incl_tax

LINES = [{"price": "19.99", "quantity": 3}, {"price": "0.335", "quantity": 1}]


class Totals(unittest.TestCase):
    def test_excl_tax_adds_price_times_quantity(self):
        self.assertEqual(total_excl_tax(LINES), Decimal("60.305"))

    def test_incl_tax_rounds_to_the_cent(self):
        self.assertEqual(total_incl_tax(LINES), Decimal("72.37"))

    def test_an_unreadable_amount_is_refused(self):
        with self.assertRaises(ValueError):
            total_incl_tax([{"price": "twelve", "quantity": 1}])
