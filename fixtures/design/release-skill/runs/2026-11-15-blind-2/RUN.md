# 2026-11-15 — harness-design blind on release-skill, after revision

A fresh agent, on a fresh kit without the answer key. About 103,000 tokens, 62 seconds. A single run.

**Result: 6 traps found out of 6, no healthy item moved out of 3** (`check.md`).

## This result does not compare with the previous one

Between `2026-11-15-blind` and this one, the fixture, the grader, the grid and the skill changed (`traps.md`, Revisions section). It is a new baseline, not the measurement of a progress: the answer key was revised by the session that had just read the first run. The plan of the first run, regraded with the revised answer key, gives 6/6 and one healthy item moved (S4).

What can be said: with the workflow present in the artifact and the instruction added to the skill, the agent opened the workflow and kept the rule that cites its check.

## What the agent says about the skill and the grid (`notes.md`)

- A "required" check cannot be read in the repository: it is a forge setting. The skill does not say how to decide.
- The grid has no answer "nothing is published without it": a rule that is checked at publication lands on a merge check.
- "Incident" does not exist for a computation: a miscomputed version weighs nothing in the `compute` branch.
- Outside the plan, as the skill now asks: a sentence to remove, a tool missing from the subagent, a limit of commitlint on squash merges.
