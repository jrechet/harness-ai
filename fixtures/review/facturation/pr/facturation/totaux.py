"""Totaux d'une facture : hors taxe, remise du client, TVA, toutes taxes comprises."""
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

CENTIME = Decimal("0.01")
TVA = Decimal("0.20")
REMISE_MAX = Decimal("0.30")


def montant(texte: str) -> Decimal:
    try:
        return Decimal(texte)
    except InvalidOperation as exc:
        raise ValueError(f"montant illisible : {texte!r}") from exc


def taux(texte: str) -> Decimal:
    try:
        valeur = Decimal(texte)
    except InvalidOperation as exc:
        raise ValueError(f"taux illisible : {texte!r}") from exc
    if not Decimal("0") <= valeur <= REMISE_MAX:
        raise ValueError(f"taux hors bornes : {valeur}")
    return valeur


def total_ht(lignes: list[dict]) -> Decimal:
    return sum((montant(ligne["prix"]) * ligne["quantite"] for ligne in lignes), Decimal("0"))


def remise(ht: Decimal, depot, client: str) -> Decimal:
    t = taux(depot.remise_du_client(client))
    return (ht * t).quantize(CENTIME, rounding=ROUND_HALF_UP)


def total_ttc(lignes: list[dict], depot=None, client: str | None = None) -> Decimal:
    try:
        ht = total_ht(lignes)
        if depot is not None:
            ht -= remise(ht, depot, client)
    except Exception:
        return Decimal("0")
    return (ht * (1 + TVA)).quantize(CENTIME, rounding=ROUND_HALF_UP)
