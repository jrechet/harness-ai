"""Invoice totals: excluding tax, customer discount, VAT, including tax."""
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

CENT = Decimal("0.01")
VAT = Decimal("0.20")
MAX_DISCOUNT = Decimal("0.30")


def amount(text: str) -> Decimal:
    try:
        return Decimal(text)
    except InvalidOperation as exc:
        raise ValueError(f"unreadable amount: {text!r}") from exc


def rate(text: str) -> Decimal:
    try:
        value = Decimal(text)
    except InvalidOperation as exc:
        raise ValueError(f"unreadable rate: {text!r}") from exc
    if not Decimal("0") <= value <= MAX_DISCOUNT:
        raise ValueError(f"rate out of bounds: {value}")
    return value


def total_excl_tax(lines: list[dict]) -> Decimal:
    return sum((amount(line["price"]) * line["quantity"] for line in lines), Decimal("0"))


def discount(excl_tax: Decimal, store, customer: str) -> Decimal:
    t = rate(store.customer_discount(customer))
    return (excl_tax * t).quantize(CENT, rounding=ROUND_HALF_UP)


def total_incl_tax(lines: list[dict], store=None, customer: str | None = None) -> Decimal:
    try:
        excl_tax = total_excl_tax(lines)
        if store is not None:
            excl_tax -= discount(excl_tax, store, customer)
    except Exception:
        return Decimal("0")
    return (excl_tax * (1 + VAT)).quantize(CENT, rounding=ROUND_HALF_UP)
