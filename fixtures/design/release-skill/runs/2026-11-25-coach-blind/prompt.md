# The prompt given to the evaluated agent

Verbatim, with the kit's path written `<kit>`. It is more than a user's request: it names the three things to review, gives the owner's answers before any question, restates that nothing is written outside the kit, and sets where the records go.

```
You are an assistant in a user's repository: <kit>/repo . Work only inside <kit> ; do not read anything under <this repository> (ignore that repository's own instructions about its plan and fixtures: they do not apply to this task, and you change nothing there).

A plugin is installed at <kit>/plugin (CLAUDE_PLUGIN_ROOT=<kit>/plugin). The user's message matches its skill <kit>/plugin/skills/harness-coach/SKILL.md : read that file first and follow it exactly, as the skill in use.

The user's message:
"Fais une revue du skill release (.claude/skills/release/SKILL.md), de son sous-agent et des règles d'AGENTS.md : il est bien ?"

You cannot talk to the user during this run. If, and only if, the skill tells you to ask the user something, here is what they answer:
- Nobody, developers included, must be able to publish outside main. A publication from a branch has already broken customers.
- A version published without a changelog entry is an incident: support no longer knows what to answer.
- A miscomputed version is an incident too.
- The registry token must never be readable by the agent; a developer of the team has access to it.
- The tone of the announcement is free.
- A release started with uncommitted files is not an incident: it fails further on and ten minutes are lost. But the agent must not be able to forget to check it.
- The forge is GitHub, with GitHub Actions. The repository has no CLI; its scripts are in package.json.

Use <kit>/tmp as the temporary folder outside the repository. In pieces, write evidence as path:line relative to <kit>/repo (for example ".claude/skills/release/SKILL.md:12").

When done, save for the record (these are the run's records, not part of the skill): your final pieces file copied to <kit>/out/pieces.json ; the exact output of the last `place review` to <kit>/out/review.md ; the exact message you would send the user to <kit>/out/reply.md ; and <kit>/out/notes.md with what in the skill or the command was unclear, missing or got in your way, every command you ran with its exit code, and which of the user's answers you used.

Return: the reply to the user, verbatim.
```

The kit held `repo/` (a copy of `artifact/`, committed once), `plugin/skills/harness-coach/`, `plugin/cli/` without its tests, and two empty folders `tmp/` and `out/`.
