# billing — note for agents

The root rules apply here. Two things specific to billing:

- Invoice numbers follow one another with no gap: `Ledger.issue` takes a number only when it writes the invoice, never before knowing whether the order is already invoiced. Why: continuous numbering is a legal obligation, and the duplicates of November 2025 left 212 numbers to declare (`docs/postmortems/2025-11-duplicate-invoices.md`). Enforced by: `services/billing/test_ledger.py`. [2025-11]
- An issued invoice is not corrected: `Invoice` is frozen, a mistake is made up for by a credit note, which accounting issues. Why: legal obligation. Enforced by: `services/billing/test_ledger.py`. [2025-11]
