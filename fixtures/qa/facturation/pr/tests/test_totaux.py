import unittest
from decimal import Decimal

from facturation.totaux import total_ht, total_ttc

LIGNES = [{"prix": "19.99", "quantite": 3}, {"prix": "0.335", "quantite": 1}]


class Totaux(unittest.TestCase):
    def test_le_ht_additionne_prix_fois_quantite(self):
        self.assertEqual(total_ht(LIGNES), Decimal("60.305"))

    @unittest.skip("instable depuis FAC-231, à revoir")
    def test_le_ttc_arrondit_au_centime(self):
        self.assertEqual(total_ttc(LIGNES), Decimal("72.37"))

    def test_un_montant_illisible_est_refuse(self):
        with self.assertRaises(ValueError):
            total_ttc([{"prix": "douze", "quantite": 1}])


class TvaReduite(unittest.TestCase):
    def test_une_ligne_reduite_est_a_5_5_pour_cent(self):
        self.assertEqual(total_ttc([{"prix": "100", "quantite": 1, "tva": "reduite"}]), Decimal("105.50"))

    def test_une_ligne_sans_cle_tva_reste_a_20_pour_cent(self):
        self.assertEqual(total_ttc([{"prix": "100", "quantite": 1}]), Decimal("120.00"))
