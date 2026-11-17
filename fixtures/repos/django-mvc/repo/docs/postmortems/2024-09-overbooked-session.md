# Incident of 9 September 2024 — fifteen confirmed enrollments for twelve seats

## What happened
The opening of enrollments for "Electrical certification B1" of 23 September was announced by the internal newsletter at 9:00. About forty requests arrived in less than ten seconds. The session has twelve seats: fifteen people received "Enrollment confirmed".

## Consequences
The technical workshop has twelve stations. On the morning of the 23rd, three people were turned away at the door, two of them having come from another site. A session had to be added for them.

## Cause
The view counted the confirmed enrollments, then created the enrollment. Two requests arriving at the same time read the same count, both under the capacity, and both wrote. No lock, no database constraint.

## Fixes
- Every enrollment goes through `enrollments.services.enroll()`. The function opens a transaction, locks the row of the session (`select_for_update`), counts, then writes.
- The views no longer write an `Enrollment` themselves.
- Uniqueness constraint on (session, address) for active enrollments (`enrollments/migrations/0002`). It stops duplicates, not overbooking.

## What remains open
- The tests run under SQLite, which ignores `select_for_update`: they prove the seat computation, not the lock. Only production, under PostgreSQL, really takes it.
- Nothing prevents code from writing a confirmed `Enrollment` without going through `enroll()`: a `bulk_create`, a script, and the add form of the admin, which still allows it.
- A capacity cannot be expressed as a table constraint. The lock is the only protection.
