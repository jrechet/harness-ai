"""Ce que l'API rend pour une facture. Le format est décrit dans docs/api.md."""
from .totaux import total_ht, total_ttc


def facture(depot, numero: int) -> dict:
    lignes = depot.lignes(numero)
    return {"numero": numero, "ht": str(total_ht(lignes)), "ttc": str(total_ttc(lignes))}
