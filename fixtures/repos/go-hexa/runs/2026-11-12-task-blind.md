# Campaign of 2026-11-12 — task `deposit` replayed on its two arms

Since 2026-11-11 the project has held a fact written nowhere in the repository: a replayed response says so in the `Idempotency-Replayed` header, on which the mobile app depends. Neutral, sandboxed agents, one draw per arm.

| Arm | Repository instructions | Score | Check missed | New tokens | Turns | Duration |
|---|---|---|---|---|---|---|
| `bare` | none | 6/7 | `replay_header` | 102,000 | 31 | 161 s |
| `harness` | `AGENTS.md` of step 1, 25 lines | 7/7 | none | 106,000 | 32 | 177 s |

## What the measurement says
**Same result as on the monorepo.** Everything that is written in the repository, both arms do: the idempotency key required, a single credit per key, fractions of a cent refused, the architecture held. The only check that separates them is that of the fact the repository does not say. The arm that holds it from its harness sets the header; the other does not mention it, and could not.

Here the harness saves neither time nor tokens: the two runs are equal. Its contribution is the fact, not the effort.

## Compared with 2026-11-11
The day before, on the same project without this fact, both arms returned 6/6. Today's difference comes entirely from what the repository does not say. It confirms the writing rule: on a well-documented repository, a harness only serves to carry what the documentation does not carry.

## What it does not say
One draw per arm, a single model. And the result is the one the construction of the bench announces: it shows that a fact laid in the harness reaches the work handed in, not how it got in there.
