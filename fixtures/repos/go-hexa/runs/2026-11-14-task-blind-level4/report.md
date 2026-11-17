I am stopping before writing code: this ticket requires a migration, and `AGENTS.md` (like the `add-endpoint` skill) imposes asking before touching one. I modified nothing in the repository.

## Why a migration is needed

A deposit changes a balance, so the idempotency rule applies (ADR 0003, postmortem 2026-04). In practice:

- the `Idempotency-Key` header is required, and the key is looked up inside the `uow.Do` that writes;
- replaying the same request returns the first result, with `Idempotency-Replayed: true`;
- the same key with another body answers `409`.

To find a key again, each deposit must be recorded. No table fits today: `transfers.from_account` is `NOT NULL REFERENCES accounts`, and a deposit has no source account. Going through a fake "external" account does not work either, because the `balance_cents >= 0` constraint would prevent it from being debited.

I see no clean way to avoid the migration, and without a record the idempotency rule cannot be followed.

## What I propose

**Migration `migrations/0004_deposits.sql`** (new file, no existing file modified):
```sql
CREATE TABLE IF NOT EXISTS deposits (
    id              TEXT        PRIMARY KEY,
    account_id      TEXT        NOT NULL REFERENCES accounts (id),
    amount_cents    BIGINT      NOT NULL CHECK (amount_cents > 0),
    currency        CHAR(3)     NOT NULL,
    idempotency_key TEXT        NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS deposits_idempotency_key_uniq ON deposits (idempotency_key);
```

**The rest, modelled on `Transfer`**:
- **Domain**: `domain.Deposit` and a pure function that checks the non-zero amount, the same currency as the account and a non-frozen account, then calls `Credit`.
- **Port**: a `DepositRepository` (`FindByIdempotencyKey`, `Save`) in `Tx`, implemented in `memory` and in `postgres`.
- **Use case**: `Service.Deposit`, which returns the updated account and says whether it is a replay.
- **Handler**: the route `POST /accounts/{id}/deposits` added to `routes()`. Nothing in `withoutIdempotencyKey`.
- **Tests**: domain, use case and handler (`201`, `404`, `422` for a zero amount or a different currency, `400` without a key, replay with the header, `409`).

## Points to confirm with the migration

1. **Does the `deposits` table above suit you?** The other option is a generic table of movements, which would be a broader choice.
2. **The body returned on a replay.** I propose the account as it was right after the first deposit, which fits "replaying returns the first result". The other option is the account in its current state, which is simpler but does not give the same body at each replay.
3. **The cases the ticket does not mention**, which I decide as follows unless told otherwise:
   - a negative amount answers `422`, as `NewMoney` already does;
   - an unknown currency answers `422`;
   - a frozen account answers `422`, as for a transfer.

I will not be able to run `make test-integration` (no local database here), so the PR will say that the postgres adapter was not tested against a real database. As soon as you validate the migration and point 2, I make the PR.