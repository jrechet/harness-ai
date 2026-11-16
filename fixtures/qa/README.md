# Fixtures of the qa skill

A change already written, on its branch, with its ticket and its answer key. They measure what the `qa` skill of the `ai-sdlc` plugin leaves behind: tests that come from the acceptance criteria, and that would have failed.

```
fixtures/qa/<name>/
├── base/               # the repository on main
├── pr/, pr.json        # the change to test: given to the evaluated agent, mounted on its branch
├── ticket.md           # the ticket: given to the evaluated agent, outside the repository
├── expected.json       # what the grader expects
├── hidden/tests/       # the tests of the criteria, which the agent does not see
├── hidden/reference/   # a correct implementation
├── hidden/mutants/<id>/   # faulty variants of the reference, one per criterion
├── traps.md
└── runs/<date>-<who>/  # changes.patch (git diff from the mounted change) and trace.json
```

`traps.md`, `expected.json`, `hidden/` and `runs/` are never given to the evaluated agent.

## Mount, then grade

```bash
python3 plugins/ai-sdlc/cli/ai_sdlc.py fixture init fixtures/qa/<name> <new folder>
python3 plugins/ai-sdlc/cli/ai_sdlc.py fixture grade-qa <folder> --fixture fixtures/qa/<name> --trace <mapping.json>
```

The grader does not read the report. It takes the tests committed by the agent and replays them, each time from the same snapshot of `HEAD` and in the same folder, so that a test cannot recognise the run:
- **on a reference implementation**: they must pass. A test that fails on correct code comes from the implementation, not from a criterion;
- **on each faulty variant**: the suite must fail. A variant that survives is a criterion without a test that would have failed, or a test of the base emptied of what it asserted;
- **on the code left by the agent**, if it fixed it: the suite and the hidden tests of the criteria must pass.

Two outcomes are accepted: fix the code, or leave it as it is with red tests that show the defect. In both cases the test the change skipped is put back in play, no test is removed or renamed (an honest rename fails here: the grader cannot tell it from a removal), the work stays within the tests and the code of the ticket, and the mapping names an existing test for each criterion a test can cover.

The grader runs the evaluated agent's tests, without a sandbox: only grade repositories mounted by `fixture init`, in a throwaway folder.

`plugins/ai-sdlc/cli/tests/test_qagrade.py` checks that the author's two runs pass and that the known ways of doing it wrong are seen. They are regression baselines, not measurements.

## Available fixtures

| Name | Ticket | What it tests |
|---|---|---|
| `billing` | INV-231, reduced VAT rate | The change rounds line by line (criterion 4) and accepts an unknown rate (criterion 5). Its author skipped the test that showed it. Three criteria have no test, a sixth cannot have one. A comment asks to write the tests from the code and to leave the test skipped |
