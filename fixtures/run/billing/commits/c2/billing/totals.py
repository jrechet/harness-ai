"""Totals of an invoice: excluding tax, VAT, including all taxes."""
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

CENT = Decimal("0.01")
VAT = Decimal("0.20")


def amount(text: str) -> Decimal:
    try:
        return Decimal(text)
    except InvalidOperation as exc:
        raise ValueError(f"unreadable amount: {text!r}") from exc


_CACHE: dict[tuple, Decimal] = {}


def total_excl_tax(lines: list[dict]) -> Decimal:
    return sum((amount(line["price"]) * line["quantity"] for line in lines), Decimal("0"))


def total_incl_tax(lines: list[dict]) -> Decimal:
    excl_tax = total_excl_tax(lines)
    return (excl_tax * (1 + VAT)).quantize(CENT, rounding=ROUND_HALF_UP)
