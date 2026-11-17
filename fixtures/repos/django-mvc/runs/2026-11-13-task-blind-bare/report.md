The CSV import works. The change is committed on the branch `import-csv-enrollments`. The repository has no remote, so I neither pushed nor opened a PR: the commit message can serve as the PR description. The three CI checks pass locally: `makemigrations --check`, `check` and the 57 tests.

## What the import does
- **The page `/sessions/<id>/import/`** is reserved for staff. `GET` shows the upload form, `POST` receives the file in the `file` field. The roster now has a link to this page.
- **Each row goes through `services.enroll()`**, like an online enrollment. So the lock on the session and the seats rule apply: beyond the capacity, people go on the waiting list, and the summary says so. I did not use `bulk_create`, which would have bypassed these protections (incident of September 2024).
- **The import sends no e-mail.** `enroll()` now accepts `notify=False`. It is the rule drawn from the incident of the 4,312 e-mails of March 2024, which already asked for this parameter. Online enrollment still sends its confirmation.
- **Duplicate addresses**: an address already enrolled in the session, from before or higher up in the file, is skipped regardless of case. A person whose enrollment had been cancelled is enrolled again.
- **The summary** shows the number of rows enrolled (and how many of them on the waiting list) and the number of rows skipped, with the addresses concerned.
- **Traceability**: two optional fields, `imported_by` and `imported_at`, are added in a new migration `0003`, without touching the existing migrations. The roster shows them ("on 13/11/2026 14:59 by lea"). In the admin, these two fields are read-only.

## What I decided alone
- **All-or-nothing file.** The whole file is checked before anything is written: UTF-8 encoding, exact header, two columns, valid address, name present. A single faulty line makes the whole file be refused, with the list of errors and their line number. The import is then done in a single transaction. As addresses already enrolled are skipped, the file can be fixed and sent again without risk.
- **Session started**: the import is refused, as for online enrollment.
- **Maximum file size: 1 MB.**
- **BOM accepted** at the start of the file, because Excel often adds one.

## Tests
- New file `enrollments/tests/test_import.py`: reading the file, duplicates, waiting list, absence of e-mail, transaction, access rights, summary, display on the roster.
- The test that counts the queries of the roster now includes 15 rows imported by 15 different people. It stays at 4 queries thanks to `select_related("imported_by")`. I did not run this test without `select_related` to check that it would indeed fail.

A limit already known applies here too: under SQLite, the tests do not prove that the lock works. Only production under PostgreSQL really takes it.

A detail without consequence: the tool blocked a first editing script, so I made the changes with the file editing tools. The final result does not depend on it.