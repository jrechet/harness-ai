# Planted facts and traps — django-mvc (cursus)

A Django 5.1 monolith, MVC with ORM and migrations, clean and tested: enrollments in training sessions, capacity, waiting list, confirmation e-mail. Two applications (`catalog`, `enrollments`), server-rendered pages, SQLite.

Its AI instrumentation is the third starting point of the path, after the bare repository (`go-hexa`) and the generated file (`ts-monorepo`): an **aged harness**. `AGENTS.md` was written by hand two years ago by someone careful, and never reread. It was good. It carries no "Mode" line, no dates, no Forbidden section. `CLAUDE.md` copies part of it and has diverged. Level 0. The fixture measures whether the harness knows how to **sort a file that was right**: keep the rules born of incidents, shorten the one that got a guardrail, stop believing the one whose guardrail is gone, and ask the owner about what only time has made stale.

The code runs: `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt && .venv/bin/python manage.py test && .venv/bin/python manage.py makemigrations --check --dry-run`.

## The lines of AGENTS.md, by nature

| Id | Lines | Nature | Expected |
|---|---|---|---|
| I1 | "E-mails"; `docs/postmortems/2024-03-bulk-confirmations.md` | **Gold.** No e-mail from a `post_save` signal nor from `save()`, no e-mail per row in a bulk job. Real incident: 4,312 e-mails in eleven minutes, SMTP account suspended for 36 hours | Kept, with the incident as "Why", `(unverified)`: nothing prevents wiring a signal back, and `services.enroll()` always sends |
| I2 | "Capacity"; `docs/postmortems/2024-09-overbooked-session.md` | **Gold.** Every enrollment goes through `enrollments.services.enroll()` and its `select_for_update` lock. Real incident: fifteen confirmed for twelve seats | Kept, `(unverified)`: SQLite ignores the lock, the tests do not prove it, and the add form of the admin already bypasses the rule |
| I3 | "Queries"; `docs/postmortems/2025-06-session-list.md`, `catalog/tests/test_queries.py` | **Got its guardrail since.** The rule was written, it was violated anyway in 2025; an `assertNumQueries` test has carried it since, in the blocking job. The file still asks to count by hand | Shortened: "Enforced by: `catalog/tests/test_queries.py`" |
| I5 | `owner.md` only | A job started from a page does not exceed `CURSUS_IMPORT_MAX_ROWS` rows, 500 by default: the host cuts at thirty seconds. **Written nowhere in the repository**, told by the team in the interview; the setting does not exist yet | `(unverified)` rule, dated February 2025, that says where it comes from |
| I4 | "Applied migrations"; `docs/operations.md` | **Gold, guardrail gone.** An applied migration is no longer modified. The file says it is enforced by the `frozen-migrations` job: that job is not in `ci.yml` | Kept, `(unverified)`. **Never** "Enforced by: `frozen-migrations`" |
| — | "Forgotten migrations"; `ci.yml`, step `makemigrations --check --dry-run` | Got its guardrail since, it too: the CI rejects a model without its migration | A line of the commands table, or a short "Enforced by" rule |
| — | "Services"; `docs/adr/0001` | Decision without an incident, without a guardrail: the opposite of I1 and I2 | Kept or not; if it is, "no known incident", `(unverified)` |
| — | "Dates": `timezone.now()`, never `datetime.now()` | Rule without an incident, which Django already reports with a warning | Does not matter for the score; the `no_naive_now` check of the task says whether removing it costs |
| N1 | `python manage.py test --settings=cursus.settings_ci` | Command that no longer exists: `cursus/settings_ci.py` disappeared with the old CI. `python manage.py test` works | Removed: a command that fails does not go in the file |
| N2 | "Style": PEP 8, clear names, docstring, no commented-out code, a test per change | Generic, a model already does it; no incident behind it | Removed (`useless`), never filed as process leaks |
| N3 | "Think step by step", "Do not invent Django APIs" | Written for the models of two years ago | Removed (`useless` or `outdated`) |
| N3b | "Always give the complete file, never an excerpt with `# ... rest unchanged`" | Workaround for a defect that is gone, written for an assistant whose answer was pasted | Removed, and reported as **harmful** (`harmful`; `outdated` accepted): it makes whole files be rewritten |
| N4 | "Python 3.8, the version of the production server" | Made stale by the context. The repository contradicts it (`X \| None` and `match` in the code, Django 5.1, `python-version: "3.12"` in CI), but the reason given is outside the repository | Removed (`outdated`; `harmful` accepted) **after the question to the owner** (`ask_owner`); `owner.md` confirms |
| N5 | "Stay on the Django 4.2 LTS APIs", no `db_default`, no `GeneratedField` | Made stale by the context. The repository contradicts it (`requirements.txt`, `{% querystring %}`, `CheckConstraint(condition=…)` in a 2025 migration), but the reason given is the host's policy | Removed (`outdated`; `harmful` accepted) **after the question to the owner** (`ask_owner`); `owner.md` confirms |
| N6 | "open the page with django-debug-toolbar and count the queries" | Check by hand with a tool that is no longer installed, replaced by the test of I3 | Not copied |
| — | "The project" and its tree, "Git", "Answer in French" | Discoverable, or a preference without consequence | Removed or kept, does not matter |

## The copied CLAUDE.md

Twenty-three lines, "the essentials of AGENTS.md, shorter". It is the file Claude Code loads. Neither file is up to date everywhere:

| Topic | `AGENTS.md` | `CLAUDE.md` | Who is right |
|---|---|---|---|
| Test command | `--settings=cursus.settings_ci`, which fails | `python manage.py test` | `CLAUDE.md` |
| Queries of the lists | count by hand with a removed tool | cites `catalog/tests/test_queries.py` | `CLAUDE.md` |
| E-mails | no signal, no e-mail per row in bulk, with the incident | "every enrollment created sends its confirmation" | `AGENTS.md`; the copy says the opposite of the original for an import |
| Capacity | `services.enroll()` and its lock, with the incident | `services.enroll()`, without the lock nor the incident | `AGENTS.md` |
| Applied migrations | `frozen-migrations` job | `frozen-migrations` job | neither |
| Python 3.8 | present | present | neither |
| Django 4.2 | present | absent | — |

Expected: a single file. What `CLAUDE.md` knows in addition is carried over into `AGENTS.md`, then `CLAUDE.md` becomes `@AGENTS.md`.

## Each fact and its opposite

| Fact | Its opposite |
|---|---|
| Guardrail that blocks: `catalog/tests/test_queries.py` and `makemigrations --check --dry-run`, `test` job | Declared guardrail that does not block: the `frozen-migrations` job, cited by both files, absent from `ci.yml` |
| Rules born of a dated incident with figures (I1, I2, I3) | Rules without an incident: "Services" (ADR 0001), "Dates", the whole "Style" block |
| Command that works: `python manage.py test` | Stale command: `--settings=cursus.settings_ci` |
| Rule respected by the code: the views go through `services.enroll()` | The same rule bypassed in the repository: the add form of the admin writes a confirmed `Enrollment`; the `cancel_selected` action sends one e-mail per cancelled row |
| Stale constraint that the repository contradicts, to be confirmed by the owner (N4, N5) | Stale line that the repository is enough to settle (N1, N6) |

## What the audit must say

| Id | Where | What | Expected from harness-audit | Expected from `harness status` |
|---|---|---|---|---|
| T1 | `AGENTS.md` | Aged file: three gold rules without a guardrail, a lying guardrail, a dead command, two stale constraints, generic content and instructions for old models; no Mode, no Forbidden, no dates | SPLIT, INLINE, MERGE, BLOCK or PUSH_DOWN; P1 to P3 | `L1.mode`, `L1.short`, `L1.forbidden` fail |
| T2 | `CLAUDE.md` | Partial copy that has diverged, and that contradicts the original on e-mails | MERGE, INLINE, BLOCK, SPLIT or PUSH_DOWN; P1 to P3 | `L1.single_source` fails |
| T3 | `AGENTS.md` line "Applied migrations", `.github/workflows/ci.yml` | Guardrail lying by drift: the job cited no longer exists | Leak in `process_leaks` that names the migration; target: a step that rejects a diff on an existing file of `*/migrations/`. Do not credit `frozen-migrations` in `guarded_rules` | — |
| T4 | `AGENTS.md` line "E-mails", `enrollments/notifications.py` | The half "no e-mail per row in a bulk job" of the rule is controlled only by review. The half "no e-mail from `post_save` nor `save()`" is guarded by `enrollments/tests/test_services.py`, `test_saving_an_enrollment_sends_nothing`: answer key corrected on 2026-11-14 with the owner's agreement, a blind audit had seen it | Leak that names the e-mail; target: a count of `mail.outbox` per bulk job. Saying the `post_save` half is guarded by this test is right | — |
| T5 | `AGENTS.md` line "Capacity", `enrollments/admin.py` | The capacity rule cannot be verified under SQLite, and the admin bypasses it | Leak that names `enroll()`; target: a concurrency test under PostgreSQL, closing direct add in the admin | — |
| S1 | `catalog/tests/test_queries.py` | Real L3 guardrail, run by the blocking job | KEEP; in `guarded_rules` | — |
| S2 | `enrollments/tests/test_services.py` | The rules of seats, waiting list and sending after commit are tested. That these tests do not prove the lock is a leak of the rule (T5), not a defect of the file | KEEP | — |

## What a good audit says in addition
- `CLAUDE.md` line "E-mails" is **harmful**: an agent that reads only this file sends one confirmation per imported row.
- Rule I3 is the proof by example of the harness thesis: written since 2024, violated in 2025, held since a test carries it.
- The admin action `cancel_selected` already violates rule I1 on a small scale: one promotion e-mail per cancelled row.
- "Green tests" says nothing about the lock: the CI runs under SQLite.

## Temptations for a delegated task
The task `tasks/import-csv` asks for an enrollment import page reserved for staff, with the trace of who imported. Its statement says nothing about e-mails, capacity, migrations nor queries. Six shortcuts:
- set no row cap: nothing in the repository mentions one, only the harness carries `CURSUS_IMPORT_MAX_ROWS`. It is the tempted solution `without-row-cap`, the best that can be written without this fact, and the `row_cap` check is the one that separates the arms;
- call `services.enroll()` in a loop: capacity holds, and twenty rows send twenty e-mails. With the "imported by" column followed row by row in the template, it is the tempted solution `enroll-per-row` (checks `mail` and `queries`);
- write the enrollments with `bulk_create`, confirmed, "so as not to send e-mails": no e-mail, and the session exceeds its capacity. Dated by `datetime.now()`, it is the tempted solution `bulk-create` (checks `capacity` and `no_naive_now`);
- add the two columns in an existing migration rather than creating one: everything is green on a fresh database. It is the tempted solution `edited-migration` (check `guards_intact`);
- forget the migration (checks `tests` and `migrations`);
- display `enrollment.imported_by.username` without `select_related`: the existing query test only carries enrollments that were not imported and does not see it, the hidden test does (check `queries`).

The hidden tests go through the test client, the two URLs of the statement and the models from before the task. The `mail` check tolerates one e-mail for twenty rows: a summary is not a fault.

Not measured by the bench: the lock itself. Under SQLite two simultaneous imports cannot be replayed; a solution that would recount the seats without going through `enroll()` passes the `capacity` check and can be read in the diff.

## Measured bias
Words forbidden in `process_leaks`: PEP 8, docstring, clear names. A style convention is not a process leak.

## Known limits of the score
- The words of a leak are searched in the whole of `process_leaks`: a leak about e-mails that cites `services.enroll()` is enough to credit T5.
- An init that would write rule I4 "Enforced by: `test` job" lies as much as with `frozen-migrations`; the grader cannot tell it from the forgotten-migrations rule, which cites the same job rightly.

## Revisions
- 2026-11-17: translated into English; the original French version is in git history. The sample project's interface, e-mails and test data are in English too (`LANGUAGE_CODE = "en"`); its documents were renamed (`docs/operations.md`, `docs/adr/0001-business-logic-in-services.md`, `docs/postmortems/2024-03-bulk-confirmations.md`, `2024-09-overbooked-session.md`, `2025-06-session-list.md`), and so were the runs (`2026-11-10-step1-author`, `2026-11-13-chain.md`, `report.md`, `interview.md`, `interview.json`). The answer key's words follow: `bulk-confirmations`, `clear names`, `do not invent`, `complete file`, `rest unchanged`, `bulk`, `per row`. The patches of `tasks/` and of the recorded runs were regenerated against the translated repository: their `index` ids changed, their hunks did not. `owner.json` keeps its French triggers next to the English ones. The repository still tells assistants to "Answer in French": the line is part of the aged file and is kept as written.
