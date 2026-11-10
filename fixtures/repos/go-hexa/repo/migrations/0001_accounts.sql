CREATE TABLE IF NOT EXISTS accounts (
    id            TEXT PRIMARY KEY,
    owner         TEXT    NOT NULL,
    balance_cents BIGINT  NOT NULL CHECK (balance_cents >= 0),
    currency      CHAR(3) NOT NULL,
    frozen        BOOLEAN NOT NULL DEFAULT FALSE
);
