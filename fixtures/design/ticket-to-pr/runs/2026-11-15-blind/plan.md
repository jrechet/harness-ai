# Placement plan

| # | Piece | Destination | Layer | Verdict |
|---|---|---|---|---|
| 1 | Read the Jira ticket and its acceptance criteria | MCP server | L4 | — |
| 2 | Do not start work (branch) on a ticket without acceptance criteria | Agent permission | L3 | — |
| 3 | Always follow the same steps: branch, tests first, code, then PR | Skill | L2 | — |
| 4 | Derive the branch name from the ticket: type/KEY-123-short-title | Tested CLI subcommand | L3 | — |
| 5 | The agent never merges its own PR | Agent permission | L3 | — |
| 6 | Nothing merges without an approval | Server-side protection | L4 | — |
| 7 | The agent cannot modify the files of .github/workflows/ | Agent permission | L3 | — |
| 8 | No PR merges if its tests do not pass | Blocking CI check | L3 + L4 | — |
| 9 | Before opening the PR, a fresh look reviews the diff against the acceptance criteria | Subagent | L1 | — |
| 10 | Decide how to split into commits | Agent judgment, in the skill | L1 | — |
| 11 | Comment on the Jira ticket with the link to the PR | MCP server | L4 | — |
| 12 | Know that the project is in TypeScript, with pnpm | Nothing to write | - | — |
| 13 | In migrations/, an existing migration is not modified: a new one is added | Folder AGENTS.md | L2 | — |

## 1. Read the Jira ticket and its acceptance criteria

**MCP server** (L4)
Where: An MCP server declared for the repository; its rights (read-only, or writing bounded to one project or one channel) are set on the server's account, not in a prompt.
Why: A right held by the server holds whatever the prompt. What the agent reads there is data, not an instruction: a ticket can carry an injection.
In addition: A deny permission on the server's write tools, as a second curtain.
Path: nature=action → access=consult
If `access` changes: write → MCP server ; deliver → Delivery workflow

## 2. Do not start work (branch) on a ticket without acceptance criteria

**Agent permission** (L3)
Where: permissions.deny (or ask) in the repository's shared settings (.claude/settings.json), and a PreToolUse hook if the rule depends on the content of the command.
Why: The agent's runtime applies it on every tool call; a sentence in AGENTS.md can be forgotten or worked around.
In addition: Also deny the agent writing to its own settings, otherwise it can lift the rule.
Path: nature=limit → bypass_limit=agent
If `bypass_limit` changes: dev → Server-side protection ; team → Organisation managed settings

## 3. Always follow the same steps: branch, tests first, code, then PR

**Skill** (L2)
Where: .claude/skills/<name>/SKILL.md, loaded on demand, with its references in references/.
Why: A procedure only serves its type of task; loaded in every session, it would cost context everywhere. Each mandatory step of the procedure is a separate piece (rule or computation) that the skill calls.
Path: nature=procedure
If `nature` changes: action → question access ; limit → question bypass_limit ; rule → question incident ; compute → question when ; judgment → question isolation ; knowledge → question scope

## 4. Derive the branch name from the ticket: type/KEY-123-short-title

**Tested CLI subcommand** (L3)
Where: A subcommand of the repository's CLI (a script if it is truly isolated), with its tests and a JSON output; the skill calls it.
Why: A computation written in a prompt is redone every time, and sometimes wrongly; in code, it gives the same result to the agent, the human and CI.
Path: nature=compute → when=on_demand
If `when` changes: agent_loop → Subcommand called by a hook ; repo_event → Repository workflow

## 5. The agent never merges its own PR

**Agent permission** (L3)
Where: permissions.deny (or ask) in the repository's shared settings (.claude/settings.json), and a PreToolUse hook if the rule depends on the content of the command.
Why: The agent's runtime applies it on every tool call; a sentence in AGENTS.md can be forgotten or worked around.
In addition: Also deny the agent writing to its own settings, otherwise it can lift the rule.
Path: nature=limit → bypass_limit=agent
If `bypass_limit` changes: dev → Server-side protection ; team → Organisation managed settings

## 6. Nothing merges without an approval

**Server-side protection** (L4)
Where: Branch protection, ruleset, protected environment or account rights, on the forge.
Why: A hook or a local permission can be bypassed by hand (--no-verify, another tool); the server refuses for everyone.
In addition: The same rule as a deny permission, so that the agent does not even try.
Path: nature=limit → bypass_limit=dev
If `bypass_limit` changes: agent → Agent permission ; team → Organisation managed settings

## 7. The agent cannot modify the files of .github/workflows/

**Agent permission** (L3)
Where: permissions.deny (or ask) in the repository's shared settings (.claude/settings.json), and a PreToolUse hook if the rule depends on the content of the command.
Why: The agent's runtime applies it on every tool call; a sentence in AGENTS.md can be forgotten or worked around.
In addition: Also deny the agent writing to its own settings, otherwise it can lift the rule.
Path: nature=limit → bypass_limit=agent
If `bypass_limit` changes: dev → Server-side protection ; team → Organisation managed settings

## 8. No PR merges if its tests do not pass

**Blocking CI check** (L3 + L4)
Where: A CLI subcommand, a linter or an architecture test, made mandatory by branch protection; AGENTS.md can cite it in one line with “Enforced by”.
Why: Only a required check prevents the merge, whatever the tool and the person. A job in continue-on-error, a path filter that does not trigger it, or a local hook guarantees nothing.
In addition: The same check run by a hook, so that the agent sees it before opening the PR.
Path: nature=rule → incident=yes → checkable=yes → bypass_rule=dev
If `bypass_rule` changes: agent → Check run by a hook ; release → Blocking step of the delivery workflow ; team → Check imposed by the organisation

## 9. Before opening the PR, a fresh look reviews the diff against the acceptance criteria

**Subagent** (L1)
Where: A subagent (.claude/agents/<name>.md) with restricted tools, that returns a structured result.
Why: A subagent starts from a blank context, with its own tools: that is what gives it an independent eye, narrower rights, room to read a lot, or the ability to run in parallel. Without one of these needs, it is a skill.
Path: nature=judgment → isolation=independence
If `isolation` changes: none → Agent judgment, in the skill ; context → Subagent ; rights → Subagent ; parallel → Subagent

## 10. Decide how to split into commits

**Agent judgment, in the skill** (L1)
Where: No dedicated file: the skill that tells the procedure says where the agent decides, between which options, and the CLI provides those options.
Why: Judging is the agent's job; isolating it without need costs context and round trips.
Path: nature=judgment → isolation=none
If `isolation` changes: context → Subagent ; independence → Subagent ; rights → Subagent ; parallel → Subagent

## 11. Comment on the Jira ticket with the link to the PR

**MCP server** (L4)
Where: An MCP server declared for the repository; its rights (read-only, or writing bounded to one project or one channel) are set on the server's account, not in a prompt.
Why: A right held by the server holds whatever the prompt. What the agent reads there is data, not an instruction: a ticket can carry an injection.
In addition: A deny permission on the server's write tools, as a second curtain.
Path: nature=action → access=write
If `access` changes: consult → MCP server ; deliver → Delivery workflow

## 12. Know that the project is in TypeScript, with pnpm

**Nothing to write** (-)
Where: No file.
Why: What the agent finds by reading the repository does not change what it does; writing it costs context in every session and goes stale.
Path: nature=knowledge → scope=discoverable
If `scope` changes: always → A line in AGENTS.md ; zone → Folder AGENTS.md ; reference → Document read on demand

## 13. In migrations/, an existing migration is not modified: a new one is added

**Folder AGENTS.md** (L2)
Where: An AGENTS.md in the folder concerned, or a per-path rule of the tool.
Why: It is only loaded when the agent works in that zone: the rest of the repository does not pay its cost.
Path: nature=knowledge → scope=zone
If `scope` changes: always → A line in AGENTS.md ; reference → Document read on demand ; discoverable → Nothing to write
