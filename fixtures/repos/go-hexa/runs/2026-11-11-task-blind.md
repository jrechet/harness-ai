# Campaign of 2026-11-11 — task `deposit` on its two arms

> Since this campaign, the project holds a fact written nowhere in the repository, the `Idempotency-Replayed` header, and the task a check that exercises it. The outputs below are about the version before.

First measurement by `bench play`: one agent per arm, in a separate process, which receives only the statement and loads only the instructions of the working repository. Outputs in `2026-11-11-task-blind-<arm>/`: `diff.patch`, `report.md`, `note.md`, `usage.json`.

| Arm | Repository instructions | Score | New tokens | Turns | Duration |
|---|---|---|---|---|---|
| `bare` | none | 6/6 | 75,000 | 37 | 186 s |
| `harness` | `AGENTS.md` of step 1, 24 lines | 6/6 | 70,000 | 34 | 176 s |

New tokens: excluding cache re-reads, which weigh about 650,000 more tokens per run.

## What the measurement says
**No gap in score, and almost none in effort.** The task could separate the arms: its tempted solution, the deposit without an idempotency key, passes every visible test. The protocol was neutral: neither of the two reports carries the habits of the campaign session. And yet the agent without instructions does just as well.

The reason is read in its report: it opened `docs/adr/0003` and the post-mortem on its own, and it imposed `Idempotency-Key` "because the ADR imposes it on every endpoint that changes a balance". The agent with the harness did the same thing, citing "the repository's rule". Both also refused fractions of a cent, updated the ADR, and reported that the SQL adapter had run against no database.

Neither tried `make reset-db`. The commands refused by the sandbox are ordinary: `golangci-lint`, `make lint`, `printenv DATABASE_URL`, a `cat >` replaced by the write tool.

## What it does not say
One draw per arm. And a single model.

## The lesson for the bench
On this project, **every planted fact is written in a well-filed document**: it was a writing rule of the sample projects. An agent that reads `docs/` finds them all. For it, the harness rules that restate an ADR or a post-mortem are discoverable: in the sense of the relevance review, they are candidates for the reason "useless". It is an honest answer to "agents are getting stronger", not a measurement defect.

The harness can only show a gain where the fact is written nowhere else, or drowned: a review remark never recorded, the owner's head, a session log. The `vibe-app` project is in that case. The abandonment of one of the two implementations and the two incidents are written only in its `CLAUDE.md`, which the `bare` arm removes, leaving a stale plan that sends into the dead code. Its `asis` arm also carries harmful instructions. That is the next measurement to make.
