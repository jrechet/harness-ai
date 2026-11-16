# billing — instructions for agents

Computes invoice totals and returns them through the API. Python, standard library, SQLite.

## What changes → what to run
| If you touch… | Run… |
|---|---|
| `billing/` or `tests/` | `python3 -m unittest discover -s tests` |

## Rules
- SQL queries pass their values as parameters, never by concatenation. Why: injection. (unverified) [2026-01]
- The format returned by the API does not change without updating `docs/api.md`. Why: the accounting export reads it. (unverified) [2026-03]
- An amount never goes through a `float`. Why: rounding gaps in accounting. (unverified) [2026-02]

## Forbidden
- Disabling, weakening or deleting a test to make the suite pass. [2026-04]
- Pushing to `main`: everything goes through a reviewed PR. [2026-01]
