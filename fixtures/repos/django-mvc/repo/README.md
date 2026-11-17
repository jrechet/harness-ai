# cursus

Enrollments in the training sessions of an organisation: the catalog of upcoming sessions, online enrollment, the waiting list when a session is full, the confirmation e-mail, and the roster for the training department. Django monolith, server-rendered pages.

**Synthetic** repository: a fixture of the harness-ai project. The PostgreSQL driver is not installed in it, everything runs under SQLite.

## Getting started

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python manage.py migrate
.venv/bin/python manage.py createsuperuser
.venv/bin/python manage.py runserver        # http://127.0.0.1:8000
```

```bash
.venv/bin/python manage.py test                              # everything
.venv/bin/python manage.py test enrollments                  # one application
.venv/bin/python manage.py makemigrations --check --dry-run  # models and migrations in sync
```

## Pages

| Path | For whom | Role |
|---|---|---|
| `/` | everyone | upcoming sessions and seats left; `?course=<slug>` filters by course |
| `/sessions/<id>/` | everyone | a session and its enrollment form |
| `/sessions/<id>/enroll/` | everyone | `POST`: enroll; confirmed if a seat is left, otherwise waiting list |
| `/sessions/<id>/roster/` | staff | the people enrolled in a session |
| `/enrollments/<id>/cancel/` | staff | `POST`: cancel; the freed seat goes to the head of the waiting list |
| `/admin/` | staff | courses, sessions, enrollments |

## Layout

```
cursus/         settings, root URLs
catalog/        courses and sessions, public pages
enrollments/    enrollments, waiting list, e-mails, staff pages
templates/      shared base template
docs/           decisions (adr/), incidents (postmortems/), operations
```
