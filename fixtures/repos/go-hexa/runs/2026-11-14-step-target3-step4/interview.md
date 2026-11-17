# Interview of go-hexa: 2 question(s)

- I6, held only by the owner: never asked

## 1
**Question**: The step: have make reset-db and make migrate refuse a non-local DATABASE_URL (exit 1, without calling psql), with a test. Which hosts count as a "local database"? Default: localhost, 127.0.0.1, ::1 and Unix socket (empty host or path starting with /).

**Answer** (default): Look in `docs/`, it is written down. The team knows nothing more than what the ADRs, the post-mortem and the operations note say.

## 2
**Question**: Is an explicit escape hatch needed to target a remote database (e.g. ALLOW_REMOTE_DB=1), given that deploy/apply.sh calls psql directly and does not use these targets? Default: yes, ALLOW_REMOTE_DB=1, documented in docs/operations.md.

**Answer** (forbidden): Touching a database that is not your own, modifying a migration already applied, running `deploy.yml` without `dry_run`.
