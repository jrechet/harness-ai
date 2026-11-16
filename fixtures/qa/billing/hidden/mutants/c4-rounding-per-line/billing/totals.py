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
    name = line.get("vat", "standard")
    if name not in RATES:
        raise ValueError(f"unknown VAT rate: {name!r}")
    return RATES[name]


def total_incl_tax(lines: list[dict]) -> Decimal:
    return sum(((amount(line["price"]) * line["quantity"] * (1 + rate(line))).quantize(CENT, rounding=ROUND_HALF_UP)
                for line in lines), Decimal("0"))
