"""The price list of the shop. Prices are in cents, tax included."""
from __future__ import annotations

PRICES_CENTS = {
    "TSHIRT-M": 1990,
    "MUG": 950,
    "POSTER-A2": 2400,
}


def knows(sku: object) -> bool:
    return isinstance(sku, str) and sku in PRICES_CENTS


def unit_price_cents(sku: str) -> int:
    return PRICES_CENTS[sku]
