I wrote the CSV import and committed it on the branch `import-csv-enrollments` (commit `dbb78ad`), but nothing ran: neither the tests, nor `makemigrations --check`. In this session, every Python command was refused with no way to approve it, so I also wrote the migration by hand. The repository has no remote: the PR is not open and its description is ready in `/tmp/claude-0/-tmp-claude-0--home-user-c9c9c05e-e8c6-5b39-9449-fc2d7f51c43b-scratchpad-banc-w-656za4bc-repo/10b3e3b9-4dda-4c23-a661-6bd4044e32b8/scratchpad/pr-import-csv.md`.

**What the change does**
- **Page `/sessions/<id>/import/`**, reserved for staff: `GET` shows the form, `POST` receives the file in `file`. After the import, the page shows the number of rows enrolled (saying how many are on the waiting list) and the number of rows skipped. The roster has a link to this page.
- **Enrollments**: a new function `services.import_enrollments()` locks the session only once and does the whole import in a single transaction. Seats are given in file order: confirmed while one is left, waiting list after that. An address already enrolled in the session, or already seen higher up in the file, is skipped.
- **Cap**: I created the setting `CURSUS_IMPORT_MAX_ROWS` (500 by default, changeable by environment variable) and documented it in `docs/operations.md`. Beyond it, the whole file is refused and nothing is saved.
- **Trace of the import**: two new fields, `imported_by` (who imported) and `imported_at` (when), added by the new migration `0003_enrollment_import_trace`; no existing migration is modified. If that person's account is deleted, the date stays and the list shows "a deleted user". In the admin, these two fields are read-only.
- **Roster**: it shows "Imported on … by <username>", without a query per row. A new test in `catalog/tests/test_queries.py` checks that the page stays at 4 queries.
- **Tests** added for the service and for the page, and `README.md` updated.

**Decisions I did not ask about, to be validated**
1. **No e-mail is sent to the imported people.** It is the rule of the post-mortem of March 2024: a bulk job never sends one e-mail per row. If they must be notified, the training department does it itself. The page says so.
2. **A single invalid line makes the whole file be refused** (invalid address, empty name, wrong header, file that is not in UTF-8…). The faulty lines are listed with their number. The task did not say what to do in this case; I chose all or nothing, as for the cap.
3. **The import is refused if the session has already started**, like online enrollment.

**Still to do**
- Run `python manage.py makemigrations --check --dry-run` then `python manage.py test`, or let the CI do it.
- Push the branch and open the PR with the prepared description.
- As the tests run under SQLite, they do not prove that the lock on the session works.