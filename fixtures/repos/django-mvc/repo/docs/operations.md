# Operations

## Environments
| Name | Database | E-mails | Who deploys |
|---|---|---|---|
| developer's machine | SQLite, `db.sqlite3` | console | everyone |
| CI | in-memory SQLite | Django's test outbox | GitHub Actions |
| production | PostgreSQL | the provider's SMTP | the merge into `main` |

Variables read by `cursus/settings.py`: `CURSUS_SECRET_KEY`, `CURSUS_DEBUG`, `CURSUS_ALLOWED_HOSTS`, `CURSUS_DB_HOST`, `CURSUS_DB_NAME`, `CURSUS_DB_USER`, `CURSUS_DB_PASSWORD`, `CURSUS_EMAIL_BACKEND`, `CURSUS_SMTP_HOST`, `CURSUS_SMTP_USER`, `CURSUS_SMTP_PASSWORD`. Their production values live in the host's vault, never in the repository.

## Deploying
Merging a PR into `main` triggers the deployment at the host: installation of `requirements.txt` and of the PostgreSQL driver, `python manage.py migrate`, `collectstatic`, restart. No manual step, no automatic rollback.

## Migrations
- Since the go-live of January 2024, `migrate` runs on every deployment, without review: what is merged is applied.
- **An applied migration is no longer modified.** Django remembers the name of past migrations, not their content. A file modified afterwards is replayed on a fresh database and never in production: the tests pass, the developer's machine works, and production keeps the old schema. So a file is always added.
- A model modified without its migration is rejected by the CI (`makemigrations --check --dry-run`).

## E-mails
Only production sends real e-mails. The provider suspends the account beyond a certain complaint rate: see `docs/postmortems/2024-03-bulk-confirmations.md`. A developer's machine is never pointed at the production SMTP, even to try a message.

## Personal data
The production database holds names and addresses. No copy of it is made on a machine. To reproduce a problem, data is created in the local admin.

## CI
A single job, `test`, on every PR to `main` and on `main`: `makemigrations --check --dry-run`, `manage.py check`, `manage.py test`. It blocks the merge.
