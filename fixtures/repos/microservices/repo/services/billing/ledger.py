"""The invoice ledger: one invoice per order, numbers that follow each other without a gap."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Invoice:
    """An issued invoice. Frozen: a mistake is fixed by a credit note, never by an edit."""

    number: str
    order_id: str
    customer_email: str
    total_cents: int
    issued_at: str


class Ledger:
    def __init__(self) -> None:
        self._by_order: dict[str, Invoice] = {}
        self._sequence = 0

    def issue(self, order_id: str, customer_email: str, total_cents: int, issued_at: datetime) -> Invoice | None:
        """Writes the invoice of an order, or returns None when the order already has one.

        The number is taken here, once the order is known to be new: an event delivered
        twice must neither issue a second invoice nor burn a number."""
        if order_id in self._by_order:
            return None
        self._sequence += 1
        invoice = Invoice(
            number=f"F-{issued_at.year}-{self._sequence:06d}",
            order_id=order_id,
            customer_email=customer_email,
            total_cents=total_cents,
            issued_at=issued_at.isoformat(timespec="seconds"),
        )
        self._by_order[order_id] = invoice
        return invoice

    def for_order(self, order_id: str) -> Invoice | None:
        return self._by_order.get(order_id)

    def by_number(self, number: str) -> Invoice | None:
        return next((invoice for invoice in self._by_order.values() if invoice.number == number), None)

    def all(self) -> list[Invoice]:
        """Every invoice, in the order they were issued."""
        return list(self._by_order.values())
