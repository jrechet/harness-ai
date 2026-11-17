The route `POST /accounts/{id}/deposits` is in place, with its tests, and the commit is on the branch `feat/deposits`. The repository has no remote, so I could not open the PR. I wrote its description here: `/tmp/claude-0/-tmp-claude-0--home-user-c9c9c05e-e8c6-5b39-9449-fc2d7f51c43b-scratchpad-banc-w-vgfg-stg-repo/7e48af30-7fc9-4d36-8c36-d8e762a022f9/scratchpad/PR.md`.

`go vet ./...`, `go test ./...`, `archcheck` and `migrationcheck -base main` all four pass. The test that requires `Idempotency-Key` on every write route also covers the new route. I only ran `migrationcheck` on the staged files, before the commit.

**Behaviour of the route**
- **Success**: `201` with the updated account. A test checks that the response is identical to that of `GET /accounts/{id}`.
- **Errors**:
  - `404` if the account does not exist.
  - `422` for a zero or negative amount, a currency unknown or different from the account's, or a frozen account.
  - `400` without `Idempotency-Key`.
  - `409` if the same key is reused for another account or another amount.
- **Replayed request**: the same key with the same request does not credit a second time. The response is a `201` with the `Idempotency-Replayed: true` header.
- **Idempotency key**: it is looked up in the same transaction as the write, modelled on `Service.Transfer`.

**What I added**
- In the domain, `domain.Deposit` and the function `domain.Receive`, which does the checks before crediting.
- The `Service.Deposit` use case.
- A new port `DepositRepository`, implemented for memory and for Postgres.
- The migration `migrations/0004_deposits.sql`: a new `deposits` table with a unique index on the key. No existing migration is modified.

**Choices made without the ticket deciding them** (explained in the PR)
- A replayed request returns the account **as it is now**, not as it was right after the first credit.
- The keys of deposits and of transfers are stored separately. The same key can therefore be used once for a transfer and once for a deposit.
- A frozen account is refused in `422`, as for a transfer.

**What I could not check**
- The Postgres integration test `TestDepositRoundTrip` compiles but did not run. There is no local database here, and the `pgx` driver is not in `go.mod`.
- That the key is indeed looked up inside the transaction remains to be checked in review: the automatic test only checks the presence of the key.
- `POST /transfers` still does not send `Idempotency-Replayed`. I did not touch it, as asked.
- A very large deposit on a big balance can overflow an `int64` in `Money.Add`. The problem already existed, but this route makes it reachable from the outside. I propose handling it in a separate ticket.

Two commands were refused automatically: a heredoc and a command containing `$?`. I replaced them with direct edits of the files and with separate commands. Nothing was skipped.