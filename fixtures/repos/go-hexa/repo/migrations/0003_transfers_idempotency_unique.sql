-- Suite de l'incident du 14 avril 2026 (docs/postmortems/2026-04-double-debit.md) :
-- la base refuse elle aussi deux virements portant la même clé.
CREATE UNIQUE INDEX IF NOT EXISTS transfers_idempotency_key_uniq ON transfers (idempotency_key);
