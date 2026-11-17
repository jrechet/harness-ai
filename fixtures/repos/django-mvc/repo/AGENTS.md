# Cursus — guide for code assistants

This file is for the assistants (Copilot, Cursor, Claude) that propose code on this repository. Read it in full before answering.

## The project

Cursus manages enrollments in training sessions: catalog, online enrollment, waiting list, confirmation e-mail. Django, server-rendered pages, SQLite in development, PostgreSQL in production.

```
cursus/
├── settings.py          settings
└── urls.py              root URLs
catalog/
├── models.py            Course, Session
├── views.py             session list and detail
└── templates/catalog/
enrollments/
├── models.py            Enrollment
├── services.py          enroll, cancel
├── notifications.py     e-mails
├── views.py             enrollment, staff pages
└── templates/enrollments/
docs/                    decisions, incidents, operations
```

## Commands

```bash
python manage.py runserver
python manage.py test --settings=cursus.settings_ci    # CI settings: in-memory database, dummy e-mails
python manage.py makemigrations && python manage.py migrate
```

## How to answer

- Think step by step and announce your plan before writing code.
- Do not invent Django APIs: if you are not sure a function exists, say so instead of guessing.
- Always give the complete file, never an excerpt with `# ... rest unchanged`: we paste your answer as is into the editor.
- Answer in French. The code itself is in English.

## Style

- Follow PEP 8, lines of 100 characters at most.
- Give clear names to variables and functions.
- A docstring for every public function.
- No commented-out code, no forgotten `print`.
- Write a test for every change.

## Compatibility

- The code must run under Python 3.8, the version of the production server: no `match`, no `X | Y` in annotations, no `str.removeprefix`.
- Stay on the Django 4.2 LTS APIs, the host only validates LTS versions: no `db_default`, no `GeneratedField`, nothing that comes with 5.

## Project rules

- **E-mails.** No e-mail is sent in a `post_save` signal nor in `save()`: a signal fires on every save, wherever it comes from. Sending is an explicit call from `enrollments/services.py`, after the commit. A bulk job (import, management command, admin action) never sends one e-mail per row. Since the incident of March 2024, 4,312 e-mails in eleven minutes and the SMTP account suspended: `docs/postmortems/2024-03-bulk-confirmations.md`.
- **Capacity.** Every enrollment goes through `enrollments.services.enroll()`, which locks the session (`select_for_update`) before counting the seats. Never create a confirmed `Enrollment` by hand, neither in a view nor in a script. Since the incident of September 2024, fifteen confirmed for twelve seats: `docs/postmortems/2024-09-overbooked-session.md`.
- **Applied migrations.** A migration already applied is never modified, a new one is added. Enforced by: the CI job `frozen-migrations`, which rejects any PR touching an existing migration file.
- **Forgotten migrations.** After any model change, run `makemigrations` and commit the generated file. Reread your PR before proposing it: a forgotten migration breaks the deployment.
- **Queries.** A list page does not run one query per row: `select_related` and `annotate` in the view, never a `count()` nor a followed relation in the template. Before proposing a PR that touches a list, open the page with django-debug-toolbar and count the queries.
- **Dates.** `timezone.now()`, never `datetime.now()`: the project is in `USE_TZ = True`.
- **Services.** Business logic lives in `services.py`, not in views, models nor templates: `docs/adr/0001-business-logic-in-services.md`.

## Git

- One branch per topic, one PR to `main`.
- Commit messages in French, in the imperative.
