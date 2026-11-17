# 2026-11-15 — harness-design blind on release-skill, after `incident=forget`

A fresh agent, on a kit without the answer key, skill and CLI at commit 3d4643e. About 100,000 tokens. A single run.

**Result: 7 traps found out of 7, no healthy item moved** (`check.md`).

## What it shows, and what it does not show

Same fixture, same answer key as `runs/2026-11-15-blind-3` (6/7): only the grid and the skill changed between the two. The agent placed the "uncommitted files" precondition as a rule, `incident=forget`, `bypass_rule=agent`, towards a check run by a hook: the added path, without a detour through a limit.

It is one point against one point, on a fixture the correction targeted. It shows that the path can be found; it does not say how often. `ticket-to-pr`, held out, was not replayed.

## Feedback (`notes.md`)

- Fourth time: under `compute`, the severity of an error changes nothing.
- A preference specific to a skill has no `scope` "in this skill".
- "Never publish outside main" reads as a limit or as a precondition (towards the blocking delivery step); the skill does not decide. Both destinations are defensible.
- The destination "check run by a hook" speaks of "after an edit, or on stop"; here a hook before the launch is needed.
- The `current` of a computation or a check told as a story in a skill: `skill` or `session`?
