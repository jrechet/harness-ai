# Notes

## What got in the way
- **Harmless precondition (uncommitted files, piece 11).** "Not an incident, but the agent must not be able to forget it" has no obvious path. As a `rule`, `incident=no` sends to `scope`, hence to text the agent can skip: the grid has no "harmless rule, yet held for the agent". I answered `limit` + `bypass_limit=agent` (Permission, with a PreToolUse hook on the release command), because the sentence bounds an action of the agent and a developer can override it without an incident. `compute` + `when=agent_loop` (hook) led to a neighbouring place; nothing in the skill decides between the two.
- **Miscomputed version = incident.** The grid has no `incident` question under `compute`: the owner's answer does not change the destination of the computation (CLI). It would justify a rule "the published version is the one the computation returns", as a blocking step of the delivery workflow, but that piece does not exist in the artifact and the skill does not say whether a review may add a piece without `current`. I did not add it.
- **`current` of a skill sentence that nothing holds.** The skill gives `session` for a choice left to the agent and `ci_check` for a rule carried by a check, but not the common case: a check or an action told as a story in the SKILL.md. I put `skill`.
- **`when` of the version computation**: `on_demand` (the skill and the delivery workflow both call it), not `repo_event`. The grid does not say what to answer when two callers exist.
- **Repository without a CLI**: the destination says "subcommand of the repository's CLI"; here it will be a `package.json` script (the table of step 5 provides for it, not the text of the plan).
- `place plan` accepts `evidence` without checking or displaying it; only `report from-place` uses it.

## Under the plan (neither pieces, nor placed)
- To confirm: is the `commitlint` job (ci.yml:12) a required check on `main`? A forge setting, unreadable from here. It only runs on `pull_request` to `main`.
- Contradiction: SKILL.md:16 asks the agent to copy the token into `.npmrc`, AGENTS.md:6 allows it "outside a release" only, the owner says "never readable by the agent". Once publication is in the delivery workflow (piece 6), the token becomes a protected environment secret on GitHub and the sentence disappears from the skill; the "outside a release" exception of AGENTS.md:6 falls.
- Piece 5: the protection is the GitHub protected environment restricted to `main` (an administrator setting), not the `git branch --show-current` of the skill.
- Step to move: the `git status` check is in step 8 (SKILL.md:19) whereas it conditions the start; the branch check (step 3) comes after the computation.
- Missing tool: `release-reviewer` only has `Read, Grep` and must read "the commits since the last tag"; it needs access to the git history, or to be given the list.
- Piece 10: no MCP server is declared in the artifact (no `.mcp.json` nor `.claude/settings.json`); the skill does not say by what means the announcement goes out today.

## Not placed
- `Mode: assistance` (AGENTS.md:3): outside the request (the rules), left out of the plan.
- Nothing else: the 12 pieces have a destination, `place plan` exits with code 0.
