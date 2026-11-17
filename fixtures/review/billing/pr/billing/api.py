"""What the API returns for an invoice. The format is described in docs/api.md."""
from .totals import total_excl_tax, total_incl_tax


def invoice(store, number: int) -> dict:
    lines = store.lines(number)
    customer = store.customer(number)
    return {"number": number, "excl_tax": str(total_excl_tax(lines)),
            "incl_tax": str(total_incl_tax(lines, store, customer))}
