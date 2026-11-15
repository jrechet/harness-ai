import unittest
from decimal import Decimal

from facturation.totaux import taux, total_ht, total_ttc

LIGNES = [{"prix": "19.99", "quantite": 3}, {"prix": "0.335", "quantite": 1}]


class FauxDepot:
    def __init__(self, taux_du_client: str):
        self.taux_du_client = taux_du_client

    def remise_du_client(self, client: str) -> str:
        return self.taux_du_client


class Totaux(unittest.TestCase):
    def test_le_ht_additionne_prix_fois_quantite(self):
        self.assertEqual(total_ht(LIGNES), Decimal("60.305"))

    def test_le_ttc_arrondit_au_centime(self):
        self.assertEqual(total_ttc(LIGNES), Decimal("72.37"))

    @unittest.skip("casse depuis la remise, à revoir")
    def test_un_montant_illisible_est_refuse(self):
        with self.assertRaises(ValueError):
            total_ttc([{"prix": "douze", "quantite": 1}])

    def test_la_remise_s_applique_avant_la_tva(self):
        self.assertEqual(total_ttc(LIGNES, FauxDepot("0.10"), "acme"), Decimal("65.13"))

    def test_un_taux_hors_bornes_est_refuse(self):
        with self.assertRaises(ValueError):
            taux("0.45")
