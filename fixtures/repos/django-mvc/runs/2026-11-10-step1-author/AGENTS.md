# cursus — instructions for agents

Mode: **delegation**. An agent receives a whole ticket and comes back with a PR to `main`; the `test` job of the CI decides, this file explains.

## What this repo does
Enrollments in training sessions: catalog, online enrollment, waiting list, confirmation e-mail. Incidents in `docs/postmortems/`, architecture decision in `docs/adr/`, operations in `docs/operations.md`.

## What changes → what to run
| If you touch… | Run… | Verified in CI by |
|---|---|---|
| code or a template | `python manage.py test` | job `test` |
| a model | `python manage.py makemigrations`, and commit the file created | job `test`, step `makemigrations --check --dry-run` |
| a list page (sessions, roster) | `python manage.py test catalog.tests.test_queries` | job `test` |

## Rules
- No e-mail from a `post_save` signal nor from `save()`, and a bulk job (import, management command, admin action) never sends one e-mail per row. Why: 4,312 e-mails in eleven minutes, SMTP account suspended for 36 hours (`docs/postmortems/2024-03-bulk-confirmations.md`). `services.enroll()` always sends its confirmation: a bulk job must be able to enroll without sending. (unverified) [2024-03]
- Every enrollment goes through `enrollments.services.enroll()`, which locks the session (`select_for_update`) before counting the seats; never a confirmed `Enrollment` written directly, nor a `bulk_create`. Why: fifteen confirmed for twelve seats (`docs/postmortems/2024-09-overbooked-session.md`). SQLite ignores the lock, the tests do not prove it; the add form of the admin already bypasses the rule, do not take it as a model. (unverified) [2024-09]
- A list page does not run one query per row: `annotate` and `select_related` in the view, and any column added to a list goes into the test. Why: home page in 14 seconds (`docs/postmortems/2025-06-session-list.md`). Enforced by: `catalog/tests/test_queries.py`. [2025-06]
- An applied migration is no longer modified: a file is added. Why: production does not replay a migration already run, its schema diverges without anything breaking here (`docs/operations.md`). No job checks it. (unverified) [2024-01]
- A job started from a page does not exceed `settings.CURSUS_IMPORT_MAX_ROWS` rows, 500 by default, and refuses whole a longer file. Why: the host cuts any request at thirty seconds; agreed with it, told by the team, written nowhere else. The setting does not exist yet. (unverified) [2025-02]
- A business rule is written in the `services.py` of its application, not in a view, a model nor a template. Why: ADR 0001, no known incident. (unverified) [2023-11]

## Forbidden
- Modifying an existing file of `catalog/migrations/` or `enrollments/migrations/`. Why: see the migrations rule. [2024-01]
- Pointing a developer's machine or a test at the production SMTP. Why: the provider suspends the account beyond a complaint rate. [2024-03]
- Copying the production database, or taking names and addresses of enrolled people out of the server. Why: owner's request, no known incident. [2026-11]
- Changing the expected number of queries in `catalog/tests/test_queries.py` to make a PR pass: the view is fixed. [2025-06]
