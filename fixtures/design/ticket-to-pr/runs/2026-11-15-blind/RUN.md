# 2026-11-15 — harness-design blind on ticket-to-pr (held out)

A fresh agent, on a kit without the answer key, skill and CLI at commit 2a495e8. About 103,000 tokens, 52 seconds. A single run: one point, not an average. It is the first measurement on a fixture the skill's corrections have never seen.

**Result: 11 traps found out of 12** (`check.md`). Nothing is corrected from this run: the fixture is held out.

## The gap: C2, the precondition

The request: "it refuses to start if the ticket has no acceptance criteria". The owner: "not an incident, but the agent must not be able to forget it".

The agent placed it as a limit of the agent (permission), and says why in `notes.md`: as a `rule`, answering `incident=no` honestly leads to `scope`, hence to a line the agent can forget. The grid has no path for "not serious, but to be guaranteed against the agent forgetting".

**It is a gap in the grid, not a fault of the agent.** The `incident` question mixes two things: severity, and the need for a guarantee. The author's plan (`runs/2026-11-15-author`) passes C2 by answering `incident=yes`, which contradicts the owner: it forced the answer to reach the destination, which the skill forbids.

## What else the agent says (`notes.md`)

- "Nothing merges without approval": limit or rule? As a rule, the grid leads to a CI check, wrong for an approval.
- The plan does not recall that a required check is a forge setting.
- "CLI subcommand" in a repository without a CLI is only understood with the table of step 5.
- `evidence` is asked for in creation whereas the skill only speaks of it in review.

## What this run does not allow

Correcting the grid or the skill from it: the fixture would lose its role. The gap of C2 calls for a second case, on a fixture that is not held out, or a decision of the owner.
