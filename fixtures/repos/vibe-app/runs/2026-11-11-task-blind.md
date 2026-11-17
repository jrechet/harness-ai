# Campaign of 2026-11-11 — `cancel-order` task on its three arms

Neutral, confined agents, started by `bench play`. One draw per arm, then a second for the two failing arms. Outputs in `2026-11-11-task-blind-<arm>/` and `-<arm>-2/`.

| Arm | Instructions of the repository | Draw 1 | Draw 2 | Check missed |
|---|---|---|---|---|
| `bare` | none; `PLAN.md`, `NOTES.md` and `TODO.md` stay | 7/8 | 7/8 | `dead_code_untouched`, both times |
| `asis` | the 133-line log `CLAUDE.md` and its three files | 7/8 | 8/8 | `no_secret_copied`, once |
| `harness` | `AGENTS.md` of step 1, 25 lines | 8/8 | not replayed | none |

| Arm | Fresh tokens, draw 1 | Draw 2 | Turns | Duration |
|---|---|---|---|---|
| `bare` | 36,000 | 89,000 | 39 then 34 | 101 s then 125 s |
| `asis` | 46,000 | 73,000 | 32 then 15 | 112 s then 85 s |
| `harness` | 36,000 | | 15 | 103 s |

Cost: 280,000 fresh tokens for 225,000 announced. The two replays cost twice the first draws.

## What the measurement says
**It is the first gap of the bench, and it repeats.** Without instructions, the agent touches up the dead implementation two times out of two. Its second report explains it: "`PLAN.md` asks to write every new route in v2. But v2 is not wired in… So I put the logic in a single place, v1 and v2 both use it, which also fixes v2." It saw that v2 served nobody. It could not know that it was abandoned: the decision is written only in the file this arm does not have. So it maintained dead code, guided by an outdated plan.

The two arms that carry the decision never touch v2: three runs out of three.

**Between the log and the harness, the gap is not established.** The `asis` arm copied the webhook secret into a test on the first draw, not on the second: it is noise until proven otherwise. The harness carries the forbidden item, the log does not, but one draw against two does not allow a conclusion.

What can be seen without being counted: the `asis` arm obeyed the log's ritual and added a "Session 9" to it. The file we wanted to shrink grows at each pass.

## What it does not say
- That the harness does better than loose notes: on the fact that separates, the two arms are level.
- Anything about another model. Five runs, a single model.
- Confinement weighed on one draw: the agent without instructions first wanted to write the secret into a test through a command that was refused, then went about it another way, without copying it.

## The lesson for the bench
Here the fact that separates is written nowhere else than in the instructions. On the two projects where each fact was filed in an ADR or a post-mortem, the arms were level. That is the writing rule to follow: a sample project holds at least one fact that is read only in its instructions or held only by its owner, and a check of its task exercises it.
