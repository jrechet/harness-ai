I added `POST /accounts/{id}/deposits`. The work is committed on the branch `feat/deposits` (commit `26e1322`), but the PR is not open: the repository has no remote. The description is ready in `/tmp/claude-0/-tmp-claude-0--home-user-c9c9c05e-e8c6-5b39-9449-fc2d7f51c43b-scratchpad-banc-w-pmdl8sbf-repo/067a1b55-9cfd-4d50-b43b-0d9dfcd18e98/scratchpad/PR.md`.

`go vet ./...`, `go test ./...` and `go run ./tools/archcheck` pass. **The Postgres integration tests (`make test-integration`), however, were not run.**

## Behaviour
- **Success:** `201` with the updated account, in the same format as `GET /accounts/{id}`. A test checks that the two responses are identical.
- **Unknown account:** `404`.
- **Zero (or missing) amount, or currency different from the account's:** `422`. It is also the case for a negative amount, an unknown currency or a frozen account.

## Added compared with the ticket
The repository's rules (AGENTS.md and ADR 0003) impose these points on every endpoint that changes a balance:
- **Idempotency key required.** Without an `Idempotency-Key` header, the request answers `400`. The key is looked up inside the write transaction, as for transfers. The same key with another account or another amount answers `409`.
- **Replay signalled.** A replayed request answers `201` with `Idempotency-Replayed: true` and does not credit the account again.
- **New migration `migrations/0004_deposits.sql`.** It creates the `deposits` table with a unique index on the key, as `0003` does for transfers. No existing migration is modified.

The code is laid out as follows: `internal/domain/deposit.go`, the port and the use case in `internal/app` (`deposit.go`), the memory, postgres and HTTP adapters, with tests at every layer. I also updated the API table of the README and the "Scope" section of ADR 0003.

## What was not checked
- **Postgres tests:** the session refused every command that inspects the environment, so I could not find a local database. I wrote `TestDepositRoundTrip` (round trip of the deposit, plus the database refusing a duplicate key). I only compiled it (`go vet -tags integration`), did not run it. It must be run on your local database before a production release.
- **Existing problem, unrelated to this change:** no `pgx` driver is imported in the module. `sql.Open("pgx", …)` will therefore fail, in integration as in `cmd/ledgerd`, until that is fixed.

## Two choices to validate in review
- **Response of a replay:** it returns the account as it is now, not as it was right after the first deposit.
- **Key spaces:** the keys of deposits and of transfers are separate. The same key can therefore be used once for a transfer and once for a deposit.

I ran neither `make migrate`, nor `make reset-db`, nor `deploy.yml`.