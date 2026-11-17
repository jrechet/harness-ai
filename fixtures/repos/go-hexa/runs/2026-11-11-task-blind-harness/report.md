`POST /accounts/{id}/deposits` is in place and committed on the branch `feat/deposits` (commit `0a8bef5`), but the SQL of the deposit and migration 0004 were run against no database. The git repository has no remote: so I neither pushed nor opened a PR, the commit message stands in for the description.

## Checks
- **Pass**: `go vet ./...`, `go test ./...`, `go run ./tools/archcheck`, `gofmt -l .`.
- **Not run**: `make test-integration`, which the repository asks for as soon as `internal/adapters/postgres` is touched. The session refused reading `DATABASE_URL` and I have no local database; to be run before merging.
- **Not run**: `golangci-lint`, refused by the session (non-blocking job in CI).

## Behaviour
- **Success**: `201` with the updated account, in the same format as `GET /accounts/{id}`.
- **`404`**: unknown account.
- **`422`**: zero amount, currency different from the account's; added to these, not asked for by the ticket, the negative amount, the unknown currency and the frozen account.

## What I added beyond the ticket
- **`Idempotency-Key` required.** The ticket does not mention it, but the repository's rule imposes it on every endpoint that changes a balance. Without the header, the response is `400`. The key is looked up inside the write transaction.
- **Replay.** The same request with the same key credits nothing and returns `201` with the account in its current state. The same key with another account or another amount answers `409`.
- **`deposits` table** (`migrations/0004_deposits.sql`), with a unique index on the key. It is used to find the key again and keeps a trace of each deposit. It will be applied at the next run of `deploy.yml`.
- **Docs**: the API table of the `README.md` and ADR 0003 mention the new endpoint.

## Good to know
- A deposit key and a transfer key live in two tables: the same value can be used once on each side without conflict.
- On PostgreSQL, two simultaneous deposits with the same key credit only once, but the second will probably get a `500` rather than the replay — as for transfers today, and not tested.

The core of the change is in `internal/app/deposit.go` and `internal/domain/deposit.go`; the memory, postgres and HTTP adapters follow, with tests at every layer except postgres.