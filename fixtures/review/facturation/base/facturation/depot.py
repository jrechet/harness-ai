"""Accès aux factures et à leurs lignes (SQLite)."""
import sqlite3


class Depot:
    def __init__(self, chemin: str):
        self.base = sqlite3.connect(chemin)

    def lignes(self, facture: int) -> list[dict]:
        curseur = self.base.execute(
            "SELECT prix, quantite FROM lignes WHERE facture = ?", (facture,))
        return [{"prix": prix, "quantite": quantite} for prix, quantite in curseur]

    def client(self, facture: int) -> str:
        ligne = self.base.execute("SELECT client FROM factures WHERE id = ?", (facture,)).fetchone()
        if ligne is None:
            raise LookupError(f"facture {facture} inconnue")
        return ligne[0]
