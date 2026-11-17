I added `POST /accounts/{id}/deposits`, committed on the branch `feat/deposits` (commit `c484a21`). I could not open the PR: the repository has no remote. Its description is ready in `/tmp/claude-0/-tmp-claude-0--home-user-c9c9c05e-e8c6-5b39-9449-fc2d7f51c43b-scratchpad-banc-w-2dg3pyrr-repo/c56e8c34-8c82-45d4-826a-93be6f608dbe/scratchpad/PR.md`.

`go vet ./...`, `go test ./...` and `make arch` pass. The new SQL and the migration were not tested against PostgreSQL: `make test-integration` needs a local database, and I ran no command on a database.

**Behaviour**
- **Success:** `201` with the account, in the same format as `GET /accounts/{id}`.
- **Errors asked for:** `404` if the account is unknown, `422` if the amount is zero or if the currency is not the account's.
- **Other `422`:** negative amount, unknown currency, frozen account.

**On top of what you asked for**: a deposit changes a balance, so I applied the rules of `AGENTS.md`.
- **Key required:** the `Idempotency-Key` header is required, otherwise `400`. The key is looked up in the same transaction as the write.
- **Replay of the same request:** the response is identical to the first, with the `Idempotency-Replayed: true` header, and the account is not credited a second time.
- **Same key, other request:** `409`. I check this case before loading the account, so a key reused on an unknown account gives `409` and not `404`.

**Files**
- **Logic:** the deposit and its checks are in `domain`; the `Service.Deposit` use case and the new storage port are in `app`.
- **Storage:** the memory and PostgreSQL adapters record the deposits.
- **HTTP:** the route is added in `httpapi`.
- **Migration:** new `migrations/0004_deposits.sql` (`deposits` table and unique index on the key). No existing migration was modified.
- **Docs:** I added the new endpoint to the API table of the README and to the list of ADR 0003.
- **Tests:** domain, use case and HTTP.

**Choices to validate in review**
- **Replay and balance:** each deposit records the balance obtained right after it. A replay therefore returns that balance, even if other operations have changed it since. That is my reading of "returns the first result".
- **Independent keys:** a key already used by a transfer does not block a deposit, because the two have separate tables.
- **Simultaneous requests:** if two requests with the same key arrive at the same time on PostgreSQL, the second gets `500` instead of a replay. `POST /transfers` already behaves this way.

**To do before the production release**: run `make test-integration` on a migrated local database, as `docs/operations.md` plans.