# Operations

## Environments
| Name | Database | Who deploys |
|---|---|---|
| local | memory, or a PostgreSQL of your own | everyone |
| staging | `ledger_staging`, **shared with the QA team and its datasets** | `deploy.yml` workflow |
| production | `ledger_prod` | `deploy.yml` workflow, after approval |

## Database
- `make migrate` applies every file of `migrations/` to the database designated by `DATABASE_URL`.
- `make reset-db` **drops the whole schema** of the database designated by `DATABASE_URL`, then replays the migrations. The target does not look at which database it is. On February 3, 2026, it was run with the staging URL left in a terminal: two days of QA datasets lost.
- A migration applied in staging or in production is never modified again. A file is added, next number.
- In staging and in production, only the migrations that went through `deploy.yml` are applied. Nobody runs `make migrate` by hand on these databases.

## Integration tests
`make test-integration` needs a migrated database. They do not run in CI; they are run by hand before a production release that touches `internal/adapters/postgres`.

## Deploying
`deploy.yml` is started by hand. `dry_run` is `true` by default and only shows the plan. Production requires an approval in the GitHub `production` environment.
