import unittest
from decimal import Decimal

from billing import api
from billing.totals import total_excl_tax, total_incl_tax

LINES = [{"price": "19.99", "quantity": 3}, {"price": "0.335", "quantity": 1}]


class FakeStore:
    def lines(self, number):
        return LINES

    def customer(self, number):
        return "acme"


class Inv231(unittest.TestCase):
    def test_criterion_1_one_reduced_line(self):
        self.assertEqual(total_incl_tax([{"price": "100", "quantity": 1, "vat": "reduced"}]), Decimal("105.50"))

    def test_criterion_2_standard_and_reduced(self):
        lines = [{"price": "100", "quantity": 1, "vat": "standard"}, {"price": "100", "quantity": 1, "vat": "reduced"}]
        self.assertEqual(total_incl_tax(lines), Decimal("225.50"))

    def test_criterion_3_without_the_key_totals_do_not_change(self):
        self.assertEqual(total_excl_tax(LINES), Decimal("60.305"))
        self.assertEqual(total_incl_tax(LINES), Decimal("72.37"))

    def test_criterion_4_one_rounding_on_the_total(self):
        lines = [{"price": "0.10", "quantity": 1, "vat": "reduced"}] * 3
        self.assertEqual(total_incl_tax(lines), Decimal("0.32"))

    def test_criterion_4_commercial_rounding(self):
        self.assertEqual(total_incl_tax([{"price": "0.10", "quantity": 1, "vat": "reduced"}] * 10), Decimal("1.06"))

    def test_criterion_5_an_unknown_vat_is_refused(self):
        with self.assertRaises(ValueError):
            total_incl_tax([{"price": "1", "quantity": 1, "vat": "luxury"}])

    def test_an_unreadable_amount_is_still_refused(self):
        with self.assertRaises(ValueError):
            total_incl_tax([{"price": "twelve", "quantity": 1}])

    def test_the_api_format_does_not_change(self):
        self.assertEqual(api.invoice(FakeStore(), 7), {"number": 7, "excl_tax": "60.305", "total": "72.37"})

    def test_the_result_stays_a_decimal(self):
        self.assertIsInstance(total_incl_tax([{"price": "100", "quantity": 1, "vat": "reduced"}]), Decimal)


if __name__ == "__main__":
    unittest.main()
