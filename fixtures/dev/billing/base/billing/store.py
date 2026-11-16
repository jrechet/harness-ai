"""Acces to invoices and their lines (SQLite)."""
import os
import sqlite3


class Store:
    def __init__(self, path: str):
        self.db = sqlite3.connect(path)

    def lines(self, invoice: int) -> list[dict]:
        cursor = self.db.execute(
            "SELECT price, quantity FROM lines WHERE invoice = ?", (invoice,))
        return [{"price": price, "quantity": quantity} for price, quantity in cursor]

    def customer(self, invoice: int) -> str:
        row = self.db.execute("SELECT customer FROM invoices WHERE id = ?", (invoice,)).fetchone()
        if row is None:
            raise LookupError(f"unknown invoice {invoice}")
        return row[0]
