# Review

12 pieces read: 4 well placed, 8 to change.

## Well placed

- **The release procedure: the ordered steps from version to announcement** (.claude/skills/release/SKILL.md:10): Skill, where it belongs.
  Why it holds: A procedure only serves its type of task; loaded in every session, it would cost context everywhere. Each mandatory step of the procedure is a separate piece (rule or computation) that the skill calls.
- **Write the announcement: what changes for a user, three lines at most** (.claude/skills/release/SKILL.md:17): Agent judgment, in the skill, where it belongs.
  Why it holds: Judging is the agent's job; isolating it without need costs context and round trips.
- **Review of the announcement by someone who did not write it** (.claude/skills/release/SKILL.md:18, .claude/agents/release-reviewer.md:7): Subagent, where it belongs.
  Why it holds: A subagent starts from a blank context, with its own tools: that is what gives it an independent eye, narrower rights, room to read a lot, or the ability to run in parallel. Without one of these needs, it is a skill.
- **Commit messages follow Conventional Commits** (AGENTS.md:7, .github/workflows/ci.yml:12): Blocking CI check, where it belongs.
  Why it holds: Only a required check prevents the merge, whatever the tool and the person. A job in continue-on-error, a path filter that does not trigger it, or a local hook guarantees nothing.

## A condition that can be skipped

Something the result must respect is written as a sentence. Nothing stops the agent, or a person, from going on without it: a program could check it, with the same answer every time.

- **CHANGELOG.md contains an entry for the version being published** (.claude/skills/release/SKILL.md:13)
  Today: Skill. Better: Blocking step of the delivery workflow.
  Where: A step of the delivery workflow that calls the check (CLI subcommand, script) and fails before the first irreversible action.
  Why: What is judged at publication cannot be seen at merge: a changelog entry, a version, a signed artifact. The delivery workflow is the only mandatory passage.

- **Nothing is published from a branch other than main** (.claude/skills/release/SKILL.md:14)
  Today: Skill. Better: Blocking step of the delivery workflow.
  Where: A step of the delivery workflow that calls the check (CLI subcommand, script) and fails before the first irreversible action.
  Why: What is judged at publication cannot be seen at merge: a changelog entry, a version, a signed artifact. The delivery workflow is the only mandatory passage.

- **No release starts while uncommitted files remain** (.claude/skills/release/SKILL.md:19)
  Today: Skill. Better: Blocking step of the delivery workflow.
  Where: A step of the delivery workflow that calls the check (CLI subcommand, script) and fails before the first irreversible action.
  Why: What is judged at publication cannot be seen at merge: a changelog entry, a version, a signed artifact. The delivery workflow is the only mandatory passage.

## A determinism problem

A result entirely fixed by its inputs is left to the model, which works it out again on every run and sometimes gets it wrong. In code, it gives the same answer to the agent, to a person and to the CI.

- **Compute the next version from the commits since the last tag** (.claude/skills/release/SKILL.md:12)
  Today: Skill. Better: Tested CLI subcommand.
  Where: A subcommand of the repository's CLI (a script if it is truly isolated), with its tests and a JSON output; the skill calls it.
  Why: A computation written in a prompt is redone every time, and sometimes wrongly; in code, it gives the same result to the agent, the human and CI.

## A limit that is only asked for

What the agent must not do is written as a request. A sentence can be forgotten or worked around; a permission or a protection refuses whatever the prompt says.

- **The agent never reads .npmrc.publish outside a release** (AGENTS.md:6)
  Today: A line in AGENTS.md. Better: Agent permission.
  Where: permissions.deny (or ask) in the repository's shared settings (.claude/settings.json), and a PreToolUse hook if the rule depends on the content of the command.
  Why: The agent's runtime applies it on every tool call; a sentence in AGENTS.md can be forgotten or worked around.

## An action without a guard

The text has the agent read, write or deliver outside the repository with whatever rights the session holds. Nothing bounds those rights, and nothing stops before the irreversible.

- **Set the version, tag, push, and npm publish with the registry token** (.claude/skills/release/SKILL.md:15, .claude/skills/release/SKILL.md:16)
  Today: Skill. Better: Delivery workflow.
  Where: A CI workflow or pipeline with a plan mode (dry-run) and a protected environment; the agent triggers it through a CLI subcommand, never through the API directly.
  Why: What changes a shared resource runs with audited rights, off the agent's machine, with a human stop point before the irreversible.

- **Send the announcement to the #releases channel** (.claude/skills/release/SKILL.md:17, .claude/skills/release/SKILL.md:18)
  Today: Skill. Better: MCP server.
  Where: An MCP server declared for the repository; its rights (read-only, or writing bounded to one project or one channel) are set on the server's account, not in a prompt.
  Why: A right held by the server holds whatever the prompt. What the agent reads there is data, not an instruction: a ticket can carry an injection.

## Dead weight

The agent finds this alone by reading the repository. Writing it, or enforcing it, adds nothing: it costs attention and goes stale.

- **Repository structure: src/, test/, dist/, package.json** (.claude/skills/release/SKILL.md:8)
  Today: Skill. Better: take it out.

## Two things in one

One text mixes its sequence of steps with checks, computations or limits that a sentence cannot hold. Cut those out, and have the steps call them.

Carried by the skill next to its steps: Repository structure: src/, test/, dist/, package.json; Compute the next version from the commits since the last tag; CHANGELOG.md contains an entry for the version being published; Nothing is published from a branch other than main; No release starts while uncommitted files remain; Set the version, tag, push, and npm publish with the registry token; Send the announcement to the #releases channel.
