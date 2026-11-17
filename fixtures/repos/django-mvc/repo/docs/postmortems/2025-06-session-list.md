# Incident of 3 June 2025 — the home page in fourteen seconds

## What happened
After the catalog of the second half of the year went online (380 sessions), the home page took up to 14 seconds to display. When enrollments opened at 9:00, the server saturated: 25 minutes of error pages.

## Cause
A PR in May had added "seats left" and "waiting" to the list. For each session the template called two properties of the model, each of which ran a `count()`: 1 + 2 × N queries. With the twenty sessions of a developer's machine, nobody had seen it.

The instruction "no query per row in a list" had been written in `AGENTS.md` since 2024. It asked to count by hand with django-debug-toolbar. The PR had not done it, nor had the review.

## Fixes
- `Session.objects.with_seats()`: the counters are annotations, the course comes through `select_related`. The list is paginated.
- `catalog/tests/test_queries.py` pins the number of queries of each list page (`assertNumQueries`), with fifteen rows and more. The `test` job of the CI runs it on every PR and blocks the merge.
- django-debug-toolbar is removed from the dependencies: nobody counts by hand any more.
