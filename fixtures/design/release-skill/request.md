# Review requested

Review the `release` skill, its subagent and the rules of `AGENTS.md` in `artifact/`: is each piece in its place?

What the owner answers if asked:
- Nobody, developers included, must be able to publish outside `main`. A publication from a branch has already broken customers.
- A version published without a changelog entry is an incident: support no longer knows what to answer.
- A miscomputed version is an incident too.
- The registry token must never be readable by the agent; a developer of the team has access to it.
- The tone of the announcement is free.
- A release started with uncommitted files is not an incident: it fails further on and ten minutes are lost. But the agent must not be able to forget to check it.
- The forge is GitHub, with GitHub Actions. The repository has no CLI; its scripts are in `package.json`.

Hand in your plan in `pieces.json`, in the format of `harness place plan`, with `current` and `evidence` (`path:line`, path relative to `artifact/`) for each piece.
