# 2026-11-15 — harness-design blind on release-skill

A fresh agent, in a kit without the answer key: `request.md`, `artifact/`, the skill and the CLI (commit c057229). It stopped at the plan. About 103,000 tokens, 71 seconds. A single run: one point, not an average.

**Result: 6 traps found out of 6, 3 healthy items moved out of 4** (`check.md`). The answer key and the grader were not modified.

## The three healthy items moved, and their cause

| Id | What the agent did | Cause |
|---|---|---|
| S1 | Joined "tag and push" (line 15) and "publish" (line 16) into one delivery action, sent to the workflow | **Debatable answer key.** The L1–L4 grid of harness-audit puts "tag" in L4: the agent is probably right, and S1 is not a healthy item |
| S2 | Kept "write the announcement" in place, but split off a piece "send to #releases" that cites the same line, sent to MCP | **Grader too coarse.** It grades by line: two pieces drawn from the same line cannot be told apart. The sending is written nowhere in the artifact, the agent inferred it |
| S4 | Left the Conventional Commits rule in `agents_md`, hence PUSH_DOWN | **Incomplete fixture, and a gap in the skill.** The cited workflow is not in `artifact/`. The agent said so in its notes. The skill does not say what to do when the cited check cannot be found |

## What the agent says about the skill and the grid (`notes.md`)

- `access` has no answer for "writing to an external system" (posting a message): it answered `consult` without conviction.
- A constraint specific to a skill ("three lines at most") has no `scope`.
- Two content corrections cannot be expressed in a placement plan: the step that has the agent copy the token is to be rewritten, not moved; the subagent lacks the tool to read the commits.
