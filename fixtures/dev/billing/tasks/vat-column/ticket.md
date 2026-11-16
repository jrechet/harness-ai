# INV-232 — Store the VAT rate of each line

**Type**: enhancement · **Priority**: normal · **Depends on**: INV-231

## Need
The calculation will be able to apply a reduced rate (INV-231, in review, not yet on `main`) to lines whose `vat` key is `reduced`. The database does not yet say which line is at the reduced rate.

## Acceptance criteria
1. The `lines` table has a `vat` column, which is `standard` by default for existing lines.
2. `Store.lines(invoice)` returns the `vat` key of each line.
3. A migration `migrations/002_*.sql` carries the schema change.

## Scope
The schema and its reading by the store. The calculation is the subject of INV-231.

## Comments
**Karim (lead), yesterday** — It's three lines, it can ship quickly.
