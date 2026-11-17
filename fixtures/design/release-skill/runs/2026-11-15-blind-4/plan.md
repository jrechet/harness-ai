# Placement plan

| # | Piece | Destination | Layer | Verdict |
|---|---|---|---|---|
| 1 | Chain the steps of a release: version, changelog, tag, publication, announcement, review | Skill | L2 | KEEP |
| 2 | Repository structure: src/, test/, dist/, package.json | Nothing to write | - | REMOVE |
| 3 | Compute the next version from the commits since the last tag (feat, fix, !, BREAKING CHANGE; nothing to publish otherwise) | Tested CLI subcommand | L3 | PUSH_DOWN |
| 4 | No version is published without an entry in CHANGELOG.md for that version | Blocking step of the delivery workflow | L3 + L4 | PUSH_DOWN |
| 5 | Never publish from a branch other than main | Server-side protection | L4 | PUSH_DOWN |
| 6 | Set the version in package.json, create and push the tag v<version>, publish with npm publish | Delivery workflow | L4 | PUSH_DOWN |
| 7 | The agent never reads the registry token (.npmrc.publish) | Agent permission | L3 | PUSH_DOWN |
| 8 | Write the announcement: what changes for a user, free tone | Agent judgment, in the skill | L1 | KEEP |
| 9 | Send the announcement in the #releases channel | MCP server | L4 | PUSH_DOWN |
| 10 | Have the announcement reviewed by someone who did not write it, against the changelog and the commits | Subagent | L1 | KEEP |
| 11 | Do not start a release if uncommitted files remain | Check run by a hook | L3 | PUSH_DOWN |
| 12 | Commit messages follow Conventional Commits | Blocking CI check | L3 + L4 | KEEP |

## 1. Chain the steps of a release: version, changelog, tag, publication, announcement, review

**Skill** (L2)
Verdict: KEEP, from Skill
Where: .claude/skills/<name>/SKILL.md, loaded on demand, with its references in references/.
Why: A procedure only serves its type of task; loaded in every session, it would cost context everywhere. Each mandatory step of the procedure is a separate piece (rule or computation) that the skill calls.
Path: nature=procedure
If `nature` changes: action → question access ; limit → question bypass_limit ; rule → question incident ; compute → question when ; judgment → question isolation ; knowledge → question scope

## 2. Repository structure: src/, test/, dist/, package.json

**Nothing to write** (-)
Verdict: REMOVE, from Skill
Where: No file.
Why: What the agent finds by reading the repository does not change what it does; writing it costs context in every session and goes stale.
Path: nature=knowledge → scope=discoverable
If `scope` changes: always → A line in AGENTS.md ; zone → Folder AGENTS.md ; reference → Document read on demand

## 3. Compute the next version from the commits since the last tag (feat, fix, !, BREAKING CHANGE; nothing to publish otherwise)

**Tested CLI subcommand** (L3)
Verdict: PUSH_DOWN, from Skill
Where: A subcommand of the repository's CLI (a script if it is truly isolated), with its tests and a JSON output; the skill calls it.
Why: A computation written in a prompt is redone every time, and sometimes wrongly; in code, it gives the same result to the agent, the human and CI.
Path: nature=compute → when=on_demand
If `when` changes: agent_loop → Subcommand called by a hook ; repo_event → Repository workflow

## 4. No version is published without an entry in CHANGELOG.md for that version

**Blocking step of the delivery workflow** (L3 + L4)
Verdict: PUSH_DOWN, from Skill
Where: A step of the delivery workflow that calls the check (CLI subcommand, script) and fails before the first irreversible action.
Why: What is judged at publication cannot be seen at merge: a changelog entry, a version, a signed artifact. The delivery workflow is the only mandatory passage.
In addition: The same check as a PR check, when it can already be done at merge.
Path: nature=rule → incident=yes → checkable=yes → bypass_rule=release
If `bypass_rule` changes: agent → Check run by a hook ; dev → Blocking CI check ; team → Check imposed by the organisation

## 5. Never publish from a branch other than main

**Server-side protection** (L4)
Verdict: PUSH_DOWN, from Skill
Where: Branch protection, ruleset, protected environment or account rights, on the forge.
Why: A hook or a local permission can be bypassed by hand (--no-verify, another tool); the server refuses for everyone.
In addition: The same rule as a deny permission, so that the agent does not even try.
Path: nature=limit → bypass_limit=dev
If `bypass_limit` changes: agent → Agent permission ; team → Organisation managed settings

## 6. Set the version in package.json, create and push the tag v<version>, publish with npm publish

**Delivery workflow** (L4)
Verdict: PUSH_DOWN, from Skill
Where: A CI workflow or pipeline with a plan mode (dry-run) and a protected environment; the agent triggers it through a CLI subcommand, never through the API directly.
Why: What changes a shared resource runs with audited rights, off the agent's machine, with a human stop point before the irreversible.
Path: nature=action → access=deliver
If `access` changes: consult → MCP server ; write → MCP server

## 7. The agent never reads the registry token (.npmrc.publish)

**Agent permission** (L3)
Verdict: PUSH_DOWN, from A line in AGENTS.md
Where: permissions.deny (or ask) in the repository's shared settings (.claude/settings.json), and a PreToolUse hook if the rule depends on the content of the command.
Why: The agent's runtime applies it on every tool call; a sentence in AGENTS.md can be forgotten or worked around.
In addition: Also deny the agent writing to its own settings, otherwise it can lift the rule.
Path: nature=limit → bypass_limit=agent
If `bypass_limit` changes: dev → Server-side protection ; team → Organisation managed settings

## 8. Write the announcement: what changes for a user, free tone

**Agent judgment, in the skill** (L1)
Verdict: KEEP, from Agent judgment, in the skill
Where: No dedicated file: the skill that tells the procedure says where the agent decides, between which options, and the CLI provides those options.
Why: Judging is the agent's job; isolating it without need costs context and round trips.
Path: nature=judgment → isolation=none
If `isolation` changes: context → Subagent ; independence → Subagent ; rights → Subagent ; parallel → Subagent

## 9. Send the announcement in the #releases channel

**MCP server** (L4)
Verdict: PUSH_DOWN, from Skill
Where: An MCP server declared for the repository; its rights (read-only, or writing bounded to one project or one channel) are set on the server's account, not in a prompt.
Why: A right held by the server holds whatever the prompt. What the agent reads there is data, not an instruction: a ticket can carry an injection.
In addition: A deny permission on the server's write tools, as a second curtain.
Path: nature=action → access=write
If `access` changes: consult → MCP server ; deliver → Delivery workflow

## 10. Have the announcement reviewed by someone who did not write it, against the changelog and the commits

**Subagent** (L1)
Verdict: KEEP, from Subagent
Where: A subagent (.claude/agents/<name>.md) with restricted tools, that returns a structured result.
Why: A subagent starts from a blank context, with its own tools: that is what gives it an independent eye, narrower rights, room to read a lot, or the ability to run in parallel. Without one of these needs, it is a skill.
Path: nature=judgment → isolation=independence
If `isolation` changes: none → Agent judgment, in the skill ; context → Subagent ; rights → Subagent ; parallel → Subagent

## 11. Do not start a release if uncommitted files remain

**Check run by a hook** (L3)
Verdict: PUSH_DOWN, from Skill
Where: A CLI subcommand, a linter or a test, called by an agent hook (after an edit, or on stop); it fails with a message that says what to fix.
Why: The agent cannot forget it. A human can skip it: that is acceptable here, since only the agent forgetting is at stake.
Path: nature=rule → incident=forget → checkable=yes → bypass_rule=agent
If `bypass_rule` changes: dev → Blocking CI check ; release → Blocking step of the delivery workflow ; team → Check imposed by the organisation

## 12. Commit messages follow Conventional Commits

**Blocking CI check** (L3 + L4)
Verdict: KEEP, from Blocking CI check
Where: A CLI subcommand, a linter or an architecture test, made mandatory by branch protection; AGENTS.md can cite it in one line with “Enforced by”.
Why: Only a required check prevents the merge, whatever the tool and the person. A job in continue-on-error, a path filter that does not trigger it, or a local hook guarantees nothing.
In addition: The same check run by a hook, so that the agent sees it before opening the PR.
Path: nature=rule → incident=yes → checkable=yes → bypass_rule=dev
If `bypass_rule` changes: agent → Check run by a hook ; release → Blocking step of the delivery workflow ; team → Check imposed by the organisation
