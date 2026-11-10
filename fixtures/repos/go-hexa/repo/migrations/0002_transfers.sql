CREATE TABLE IF NOT EXISTS transfers (
    id              TEXT PRIMARY KEY,
    from_account    TEXT        NOT NULL REFERENCES accounts (id),
    to_account      TEXT        NOT NULL REFERENCES accounts (id),
    amount_cents    BIGINT      NOT NULL CHECK (amount_cents > 0),
    currency        CHAR(3)     NOT NULL,
    idempotency_key TEXT        NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL
);
