# Step 1 by the fixture author — 2026-11-10

What step 1 of harness must lay on this repository, written by the session that planted the facts: level 1 and nothing else. No Maintenance section, no harvest marker, no Working process, no contract: those are the next steps.

It is a **regression baseline** for the grader (`fixture check django-mvc --init <this folder>`) and the default `harness` arm of the bench, not a measurement of the skill.

The dates of the rules are those of the incident or of the decision, not that of the step: a rule does not get younger because it is copied. The migrations rule carries the date of the go-live (`docs/operations.md`), the services rule the date of the ADR.

## What was removed, and why
`AGENTS.md`: 67 lines before, 26 after. `CLAUDE.md`: 23 lines before, 1 after.

| Removed | Reason |
|---|---|
| "The project" and its tree | Discoverable by reading the repository |
| `python manage.py test --settings=cursus.settings_ci` | Stale: `cursus/settings_ci.py` no longer exists, the command fails. Replaced by the one of `CLAUDE.md`, verified |
| "Think step by step", "Do not invent Django APIs" | Written for old models; no longer changes anything |
| "Always give the complete file, never an excerpt" | Harmful: makes whole files be rewritten to work around a defect that is gone |
| "Answer in French" | Conversation preference, not a rule of the repository; the language of the commits can be read in the history |
| PEP 8, clear names, docstring, no commented-out code, a test per change | Generic: a model does it without being told |
| Python 3.8 | Stale, confirmed by the owner: the server was replaced in February 2025. The code and Django 5.1 already contradicted it |
| Django 4.2 LTS, no `db_default` nor `GeneratedField` | Stale, confirmed by the owner: the host has changed. `requirements.txt` and a 2025 migration already contradicted it |
| "Enforced by: the CI job `frozen-migrations`" | False by drift: the job is not in `ci.yml`. The rule stays, marked `(unverified)` |
| "open the page with django-debug-toolbar and count the queries" | Stale: the tool is no longer installed, the test `catalog/tests/test_queries.py` has taken its place |
| "Dates: `timezone.now()`, never `datetime.now()`" | What a model does in a Django project, and that Django reports with a warning. The `no_naive_now` check of the task says whether this removal costs |
| "Git" | Discoverable: the CI only runs on PRs to `main` |
| `CLAUDE.md`, "every enrollment created sends its confirmation" | Harmful: the copy contradicts the original for a bulk job |
| `CLAUDE.md`, all the rest | Duplicate. Its two contributions, the test command and the query test, are carried over into `AGENTS.md` |

## What was kept, and what changed
| Rule | Change |
|---|---|
| E-mails | Kept in substance, with the incident as "Why". Added: `services.enroll()` always sends, which the post-mortem says and the old file did not |
| Capacity | Kept. Added: SQLite ignores the lock, and the admin is not a model to follow |
| Queries | Shortened: "Enforced by: `catalog/tests/test_queries.py`" replaces the check by hand |
| Applied migrations | Kept, moved from "enforced" to `(unverified)`; taken up again as a Forbidden item |
| Forgotten migrations | Became a line of the commands table: the CI carries it |
| Services | Kept, with "no known incident" |

The Forbidden items come from the interview (`owner.md`) and from `docs/operations.md`.
