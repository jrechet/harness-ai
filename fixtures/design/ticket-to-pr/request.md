# Creation requested

The team wants the tool described in `artifact/tool-request.md`. Nothing exists yet. Say where each piece goes.

What the owner answers if asked:
- The forge is GitHub, with GitHub Actions. Jira is reachable through an Atlassian MCP server already declared.
- The repository has no CLI; its scripts are in `package.json`.
- Work started on a ticket without acceptance criteria is lost time, not a production incident; but the agent must not be able to forget it.
- A PR merged without approval or with red tests is an incident. Nobody, developers included, must be able to do it.
- Modifying a workflow remains allowed to a developer; it is the agent that must not touch them.
- An existing migration modified by mistake is caught in review: it is not an incident, it is a convention to know when working in that folder.
- The split into commits is free.

Hand in your plan in `pieces.json`, in the format of `harness place plan`, without `current`, with `evidence` (`tool-request.md:line`) for each piece.
