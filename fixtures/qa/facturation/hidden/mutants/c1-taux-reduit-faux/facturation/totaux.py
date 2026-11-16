"""Totaux d'une facture : hors taxe, TVA, toutes taxes comprises."""
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

CENTIME = Decimal("0.01")
TVA = Decimal("0.20")
TAUX = {"normale": TVA, "reduite": Decimal("0.05")}


def montant(texte: str) -> Decimal:
    try:
        return Decimal(texte)
    except InvalidOperation as exc:
        raise ValueError(f"montant illisible : {texte!r}") from exc


def total_ht(lignes: list[dict]) -> Decimal:
    return sum((montant(ligne["prix"]) * ligne["quantite"] for ligne in lignes), Decimal("0"))


def taux(ligne: dict) -> Decimal:
    nom = ligne.get("tva", "normale")
    if nom not in TAUX:
        raise ValueError(f"taux de TVA inconnu : {nom!r}")
    return TAUX[nom]


def total_ttc(lignes: list[dict]) -> Decimal:
    brut = sum((montant(ligne["prix"]) * ligne["quantite"] * (1 + taux(ligne)) for ligne in lignes), Decimal("0"))
    return brut.quantize(CENTIME, rounding=ROUND_HALF_UP)
