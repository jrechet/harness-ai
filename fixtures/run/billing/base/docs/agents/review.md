---
point: review
mode: append
---
- Every migration `migrations/NNN_*.sql` comes with its `NNN_*.down.sql`. Why: rollback impossible during the June incident. (unverified) [2026-06]
- An amount never goes through a `float`. Why: rounding differences in accounting. (unverified) [2026-02]
