---
point: review
mode: append
---
- A migration of more than 50 lines comes with its `NNN_*.down.sql`. Why: rollback was impossible during the June incident. (unverified) [2026-06]
- An amount never goes through a `float`. Why: rounding gaps in accounting. (unverified) [2026-02]
