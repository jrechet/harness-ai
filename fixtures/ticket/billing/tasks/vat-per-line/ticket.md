# INV-242 — VAT rate per line, from the database to the API

**Type**: enhancement · **Priority**: normal

## Need
Each invoice line must carry its VAT rate. Today the rate is the same for all lines, 20 %. We want to store it per line, use it in the computation and show it in what the API returns, so that the accounting export reads it.

## Acceptance criteria
- A migration `migrations/002_vat.sql` adds the `vat` column to the `lines` table, of type `REAL`.
- `total_incl_tax` reads the rate of each line and converts it with `float(line["vat"])`.
- The API returns one `vat` key per invoice.
- Performance stays good.
- The totals of existing invoices do not change.

## Scope
`migrations/`, `billing/` and the API documentation if needed.

## Comments
**Karim (lead), yesterday** — It's small, we can do it all in the same PR.
