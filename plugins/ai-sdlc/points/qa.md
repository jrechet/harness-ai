The tests of a change hold when:
- each acceptance criterion of the ticket has at least one test that would fail without the change, or a written reason for not having one;
- the suite passes several times in a row: a test that passes one time out of two proves nothing;
- no test is disabled, skipped or deleted to make the suite pass;
- the added lines are executed by the tests, when the repository can measure its coverage.
