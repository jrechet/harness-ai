"""Ce que l'API rend pour une facture. Le format est décrit dans docs/api.md."""
from .totaux import montant, total_ht, total_ttc


def facture(depot, numero: int) -> dict:
    lignes = depot.lignes(numero)
    remise = montant(depot.remise(numero))
    return {"numero": numero, "ht": str(total_ht(lignes)), "total": str(total_ttc(lignes) * (1 - remise))}
