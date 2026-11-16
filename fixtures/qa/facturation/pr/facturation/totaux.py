"""Totaux d'une facture : hors taxe, TVA, toutes taxes comprises."""
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

CENTIME = Decimal("0.01")
TVA = Decimal("0.20")
TAUX = {"normale": TVA, "reduite": Decimal("0.055")}


def montant(texte: str) -> Decimal:
    try:
        return Decimal(texte)
    except InvalidOperation as exc:
        raise ValueError(f"montant illisible : {texte!r}") from exc


def total_ht(lignes: list[dict]) -> Decimal:
    return sum((montant(ligne["prix"]) * ligne["quantite"] for ligne in lignes), Decimal("0"))


def taux(ligne: dict) -> Decimal:
    return TAUX.get(ligne.get("tva", "normale"), TVA)


def ttc_ligne(ligne: dict) -> Decimal:
    ht = montant(ligne["prix"]) * ligne["quantite"]
    return (ht * (1 + taux(ligne))).quantize(CENTIME, rounding=ROUND_HALF_UP)


def total_ttc(lignes: list[dict]) -> Decimal:
    return sum((ttc_ligne(ligne) for ligne in lignes), Decimal("0"))
