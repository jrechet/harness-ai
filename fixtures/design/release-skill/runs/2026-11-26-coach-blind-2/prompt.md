# The prompt given to the evaluated agent

Verbatim, with the kit's path written `<kit>` and this repository `<this repository>`. Unlike the run of 2026-11-25, it gives no answer of the owner in advance, does not restate that nothing is written, and sets no record to keep.

```
You are an assistant in a user's repository: <kit>/repo (call the parent folder KIT). Work only inside KIT; do not read anything under <this repository>, and ignore that repository's own instructions (its plan, its fixtures, its hooks): they do not apply to this task and you change nothing there.

A plugin is installed at KIT/plugin (CLAUDE_PLUGIN_ROOT=KIT/plugin). The user's message matches its skill KIT/plugin/skills/harness-coach/SKILL.md: read that file first and follow it, as the skill in use. The temporary folder outside the repository is KIT/tmp.

The user's message:
"Fais une revue du skill release, de son sous-agent et des règles d'AGENTS.md : il est bien ?"

The user is available. If the skill leads you to ask them something, stop and end your turn with only your questions, written as you would send them to the user; their answers will come back to you and you continue. Otherwise, your final message is exactly the message you send the user, and nothing else.
```

The kit held `repo/` (a copy of `artifact/`, committed once), `plugin/skills/harness-coach/` and `plugin/cli/` without its tests, both taken from commit dc357c0 with `git archive`, and an empty `tmp/`. No `docs/`, no `fixtures/`.

After the agent handed its reply in, it was asked, for the record only, to save its reply, the output of `place review` and its notes; `notes.md` and `reply.md` were written then. `pieces.json` is the file it left in `tmp/` during the run.
