import unittest
from decimal import Decimal

from facturation import api
from facturation.totaux import total_ht, total_ttc

LIGNES = [{"prix": "19.99", "quantite": 3}, {"prix": "0.335", "quantite": 1}]


class FauxDepot:
    def lignes(self, numero):
        return LIGNES

    def client(self, numero):
        return "acme"


class Fac231(unittest.TestCase):
    def test_critere_1_une_ligne_reduite(self):
        self.assertEqual(total_ttc([{"prix": "100", "quantite": 1, "tva": "reduite"}]), Decimal("105.50"))

    def test_critere_2_normale_et_reduite(self):
        lignes = [{"prix": "100", "quantite": 1, "tva": "normale"}, {"prix": "100", "quantite": 1, "tva": "reduite"}]
        self.assertEqual(total_ttc(lignes), Decimal("225.50"))

    def test_critere_3_sans_cle_les_totaux_ne_changent_pas(self):
        self.assertEqual(total_ht(LIGNES), Decimal("60.305"))
        self.assertEqual(total_ttc(LIGNES), Decimal("72.37"))

    def test_critere_4_un_seul_arrondi_sur_le_total(self):
        lignes = [{"prix": "0.10", "quantite": 1, "tva": "reduite"}] * 3
        self.assertEqual(total_ttc(lignes), Decimal("0.32"))

    def test_critere_4_arrondi_commercial(self):
        self.assertEqual(total_ttc([{"prix": "0.10", "quantite": 1, "tva": "reduite"}] * 10), Decimal("1.06"))

    def test_critere_5_une_tva_inconnue_est_refusee(self):
        with self.assertRaises(ValueError):
            total_ttc([{"prix": "1", "quantite": 1, "tva": "luxe"}])

    def test_un_montant_illisible_est_toujours_refuse(self):
        with self.assertRaises(ValueError):
            total_ttc([{"prix": "douze", "quantite": 1}])

    def test_le_format_de_l_api_ne_change_pas(self):
        self.assertEqual(api.facture(FauxDepot(), 7), {"numero": 7, "ht": "60.305", "total": "72.37"})

    def test_le_resultat_reste_un_decimal(self):
        self.assertIsInstance(total_ttc([{"prix": "100", "quantite": 1, "tva": "reduite"}]), Decimal)


if __name__ == "__main__":
    unittest.main()
