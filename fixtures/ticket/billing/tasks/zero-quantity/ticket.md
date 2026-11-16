# INV-241 — Refuse a zero or negative quantity

**Type**: fix · **Priority**: normal

## Need
`total_excl_tax` today accepts a line whose quantity is 0 or -2 and returns a wrong total, without saying anything. An invoice with such a line is an input error: the computation must refuse it, as it already refuses an unreadable amount.

## Acceptance criteria
- `total_excl_tax([{"price": "10", "quantity": 0}])` raises `ValueError`.
- `total_excl_tax([{"price": "10", "quantity": -2}])` raises `ValueError`.
- The error message cites the refused quantity.
- A quantity of 1 or more gives the same totals as today.

## Scope
`billing/totals.py` and its tests. Credit notes are not concerned: they go through a negative price, not through the quantity.

## Comments
**Nadia (accounting), yesterday** — Confirmed, we have no legitimate case of a zero quantity.
