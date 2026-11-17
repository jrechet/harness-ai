-- Follow-up to the incident of April 14, 2026 (docs/postmortems/2026-04-double-debit.md):
-- the database too refuses two transfers carrying the same key.
CREATE UNIQUE INDEX IF NOT EXISTS transfers_idempotency_key_uniq ON transfers (idempotency_key);
