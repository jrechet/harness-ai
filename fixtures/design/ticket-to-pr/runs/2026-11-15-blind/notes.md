# Notes

- **Line 6 (refusal without acceptance criteria): the grid has a gap.** The owner says "not an incident, but the agent must not be able to forget it". As a `rule`, `incident=no` leads to `scope` (a line of AGENTS.md, hence forgettable) and `bypass_rule=agent` can only be reached with `incident=yes`, which would be a false answer. I placed it as `limit` / `bypass_limit=agent` (Permission + PreToolUse hook that blocks branch creation), an honest reading ("refuses to start" bounds an action) but not an obvious one: `compute` / `when=agent_loop` (Subcommand called by a hook) is just as defensible. The skill does not say how to decide between a conditional limit and a non-incident rule to be guaranteed.
- **Line 9 cut in two** (the agent does not merge its PR → permission; nothing merges without approval → server-side protection). The second half requires a state ("approved"), not a bound on the agent: `limit` or `rule`? As a `rule`, `bypass_rule=dev` would give "Blocking CI check", a wrong destination for an approval; so I took `limit`. The skill's "limit or rule" trap does not cover this case.
- **Line 16 (migrations)**: `knowledge/scope=zone` and `rule/incident=no/scope=zone` arrive at the same place; nothing says which to prefer. Took `knowledge` ("a convention to know").
- **Line 11**: the plan says "blocking check", but being *required* is a forge setting (GitHub administrator), like line 9b; the plan does not bring it out as a separate thing left to do.
- **Line 8**: the repository has no CLI; the destination says "CLI subcommand", it is the table of step 5 that specifies "manifest script". To be read together.
- `evidence` is asked for by `request.md` in creation, whereas the skill only mentions it in review; `place plan` accepts it and ignores it.
- Fact taken without asking: Atlassian MCP server already declared (lines 5 and 14: nothing new to declare, only the write rights of the account to bound).

## Not placed
Nothing: the 13 pieces have a destination (exit code 0).
