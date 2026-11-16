"""What the API returns for an invoice. The format is described in docs/api.md."""
from .totals import amount, total_excl_tax, total_incl_tax


def invoice(store, number: int) -> dict:
    lines = store.lines(number)
    discount = amount(store.discount(number))
    return {"number": number, "excl_tax": str(total_excl_tax(lines)), "total": str(total_incl_tax(lines) * (1 - discount))}
