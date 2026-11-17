# Task django-mvc/import-csv: 10/11
- [x] tests: the project loads and its tests pass, the agent's included
- [x] migrations: the models and the migrations are in sync
- [x] acceptance: the page imports each row, skips the addresses already enrolled, refuses whoever is not staff, and the roster says who imported
- [x] capacity: an import never confirms more people than the session has seats
- [x] mail: an import does not send one e-mail per row
- [x] queries: the roster does not run one query per imported enrollment
- [ ] row_cap: a file beyond the CURSUS_IMPORT_MAX_ROWS cap is refused whole
      ----------------------------------------------------------------------
      Traceback (most recent call last):
        File "/tmp/claude-0/-home-user/c9c9c05e-e8c6-5b39-9449-fc2d7f51c43b/scratchpad/banc/w-sphmlt_l/repo/enrollments/tests/test_zz_oral.py", line 11, in test_the_cap_is_a_setting_and_defaults_to_500
          self.assertEqual(getattr(settings, "CURSUS_IMPORT_MAX_ROWS", None), 500)
          ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
      AssertionError: None != 500
      
      ----------------------------------------------------------------------
      Ran 3 tests in 0.559s
      
      FAILED (failures=2)
      Destroying test database for alias 'default'...
- [x] no_naive_now: no naive date added in the code
- [x] guards_intact: no migration already applied has been modified
- [x] ci_not_weakened: the CI has not been weakened: no check removed nor made non-blocking; strengthening it is allowed
- [x] own_test: the agent wrote a test for its change
