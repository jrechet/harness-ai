# Cursus — instructions for agents

Mode: **delegation**. An agent may receive a whole task and open a PR without intermediate review. What is mandatory here is verified by the CI; this file explains, it does not guarantee.

## What this repo does
Enrollments in the training sessions of an organisation. Decisions in `docs/adr/`, incidents in `docs/postmortems/`, deployment and environments in `docs/operations.md`: read the post-mortem of a zone before touching it.

## Rules
- Answer in French; the code, its names and its docstrings are in English; commit messages in French, in the imperative. Why: team convention, no known incident. (unverified) [2026-11]
- E-mails: no sending in a signal nor in `save()`; sending is an explicit call from `enrollments/services.py`, after the commit (`transaction.on_commit`), the messages live in `enrollments/notifications.py`. A bulk job (import, management command, admin action) never sends one e-mail per row: `services.enroll()` always sends, so a bulk job does not call it as is. Why: incident of March 2024, 4,312 e-mails in eleven minutes and SMTP account suspended for 36 h (`docs/postmortems/2024-03-bulk-confirmations.md`). (unverified) [2024-03]
- Capacity: every enrollment is created through `enrollments.services.enroll()`, which locks the session (`select_for_update`) before counting; never a confirmed `Enrollment` written by hand (view, script, `bulk_create`). The add form of the admin (`enrollments/admin.py`) still allows it: counter-example, not a model. The tests run under SQLite, which ignores the lock: a green test does not prove concurrency. Why: incident of September 2024, fifteen confirmed for twelve seats (`docs/postmortems/2024-09-overbooked-session.md`). (unverified) [2024-09]
- List pages: no query per row (`annotate`, `select_related` in the view; never a `count()` nor a followed relation in the template). If `catalog/tests/test_queries.py` breaks, fix the view, do not change the expected number. Why: incident of June 2025, home page at 14 s and 25 min of errors (`docs/postmortems/2025-06-session-list.md`). Enforced by: catalog/tests/test_queries.py [2025-06]
- A job started from a page (file import, bulk action) handles at most `settings.CURSUS_IMPORT_MAX_ROWS` rows, 500 by default; beyond that, the whole file is refused, nothing is saved. The cap is always read from this setting, never hard-coded: the host must be able to lower it without us. The setting does not exist yet; the first job of this kind creates it. Why: told by the team, the host cuts any request at 30 s (agreement of February 2025). (unverified) [2025-02]
- Business logic (seats, waiting list, cancellation) lives in the `services.py` of its application; views and admin actions call a service, models and templates carry none. Why: `docs/adr/0001-business-logic-in-services.md`, no known incident. (unverified) [2023-11]
- Dates: `timezone.now()`, never `datetime.now()`. Why: `USE_TZ = True`, no known incident. (unverified) [2026-11]

## Forbidden
- Modifying an existing migration: a new one is always added. Why: `migrate` runs on every merge into `main` without review; Django remembers the name of a migration, not its content, so production would keep the old schema while the tests pass (`docs/operations.md`). No CI job rejects it today. [2024-01]
- Sending a real e-mail from anything other than production: never set `CURSUS_EMAIL_BACKEND` or `CURSUS_SMTP_*` outside production, even to try a message. Why: the provider suspends the account, incident of March 2024. [2024-03]
- Taking personal data of enrolled people out of the server: no copy of the production database, no real address nor real name in the repository, the fixtures, the logs, an issue or a PR. To reproduce, create fictional data. Why: told by the team, `docs/operations.md`. [2026-11]
