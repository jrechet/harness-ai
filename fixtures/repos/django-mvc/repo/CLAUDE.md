# CLAUDE.md

Notes for Claude Code on Cursus. The essentials of AGENTS.md, shorter.

## Commands

```bash
python manage.py test                  # everything
python manage.py test enrollments      # one application
python manage.py runserver
```

## Good to know

- Answer in French, code in English.
- PEP 8, clear names, a docstring per public function.
- Python 3.8 on the server: no `match`, no `X | Y`.
- E-mails: every enrollment created sends its confirmation, through `enrollments/notifications.py`. No signal.
- Capacity: an enrollment is created with `services.enroll()`, never directly.
- Migrations: never modify an existing migration, the CI rejects it (job `frozen-migrations`).
- Lists: no query per row. `catalog/tests/test_queries.py` counts the queries of the list pages; do not change the expected number to make a test pass.
- Dates: `timezone.now()`.
- PRs target `main`.
