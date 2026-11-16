"""Invoice totals: excluding tax, VAT, including all taxes."""
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

CENT = Decimal("0.01")
VAT = Decimal("0.20")
RATES = {"standard": VAT, "reduced": Decimal("0.055")}


def amount(text: str) -> Decimal:
    try:
        return Decimal(text)
    except InvalidOperation as exc:
        raise ValueError(f"unreadable amount: {text!r}") from exc


def total_excl_tax(lines: list[dict]) -> Decimal:
    return sum((amount(line["price"]) * line["quantity"] for line in lines), Decimal("0"))


def rate(line: dict) -> Decimal:
    return RATES.get(line.get("vat", "standard"), VAT)


def line_incl_tax(line: dict) -> Decimal:
    excl_tax = amount(line["price"]) * line["quantity"]
    return (excl_tax * (1 + rate(line))).quantize(CENT, rounding=ROUND_HALF_UP)


def total_incl_tax(lines: list[dict]) -> Decimal:
    return sum((line_incl_tax(line) for line in lines), Decimal("0"))
