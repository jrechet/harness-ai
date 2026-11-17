`POST /accounts/{id}/deposits` is in place, committed on the branch `feat/account-deposits` (one commit, `116821d`). The repository has no remote, so nothing is pushed and no PR is open.

**Checks:** `go vet`, `go test ./...` and `make arch` pass. Two things did not run:
- **Lint:** `make lint` was refused by the session's sandbox.
- **Postgres:** the SQL adapter and migration `0004` were run against no database. The integration test I added compiles, nothing more; `make test-integration` remains to be run before the production release, as `docs/operations.md` asks.

## Behaviour

- **Success:** `201` with the updated account, in the same format as `GET /accounts/{id}`.
- **Unknown account:** `404`.
- **Rejections in `422`:** zero, missing or negative amount, currency different from the account's or unknown, frozen account.
- **Unreadable body:** `400`, including a decimal `amount_cents`.

## One deviation from your spec: `Idempotency-Key` is required

ADR 0003 imposes it on every endpoint that changes a balance, following the double debit of April. So I applied it to the deposit, as for `POST /transfers`:
- without the header: `400`;
- same key replayed with the same request: `201` with the account, without crediting a second time;
- same key with another account or another amount: `409`.

A client that follows your spec to the letter, without a header, will therefore get `400`. If you want the endpoint without a key, it is a small removal, but it contradicts the ADR.

## What it entailed

- **New `deposits` table** (`migrations/0004_deposits.sql`), with a unique idempotency key in the database. It will be applied by `deploy.yml` at the next deployment.
- **Overflow guard in `Money.Add`**: a deposit that would push the balance past `int64` is refused in `422`. I added it because a balance can now grow from an external input.
- **Docs:** API table of the README and scope of ADR 0003 updated.

## Good to know

Two concurrent deposits carrying the same key on Postgres: the second will fail in `500` (uniqueness violation or serialisation failure) rather than replay cleanly. The balance stays right, and transfers already behave this way; I did not touch it.