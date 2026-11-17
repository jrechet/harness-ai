# ticket-to-pr — held-out fixture

A creation request: twelve needs, one per line, of different natures. Measures harness-design in creation: nothing exists, each piece must receive an accepted destination and cite the line of the request it comes from.

**Held out (`holdout`).** Neither the skill nor the grid is corrected from a run on this fixture: it serves to check that a correction made elsewhere does not hold only for the fixture that inspired it. It was written on 2026-11-15, before the corrections drawn from the second run on `release-skill`.

| Id | Line | What is requested | What the plan must say |
|---|---|---|---|
| C1 | 5 | Read the Jira ticket | MCP server |
| C2 | 6 | Refuse without acceptance criteria | A check in code that the agent cannot forget: hook, script; the CI check is accepted. The trap: leaving it as a step of the skill |
| C3 | 7 | The same steps every time | Skill |
| C4 | 8 | Branch name derived from the ticket | Computation: tested script |
| C5 | 9 | No merging of its own PR, no merging without approval | Server-side protection. The trap: a permission, which a developer overrides |
| C6 | 10 | Do not modify the workflows | Agent permission. The trap: server protection, whereas a developer is entitled to it |
| C7 | 11 | No merging with red tests | Blocking check |
| C8 | 12 | A fresh look at the diff | Subagent |
| C9 | 13 | Free split into commits | Agent judgment; "skill" accepted |
| C10 | 14 | Comment on the ticket | MCP server, with write access |
| C11 | 15 | TypeScript and pnpm | Nothing to write |
| C12 | 16 | Convention of the migrations folder | Folder AGENTS.md; the root one is accepted. The trap: making it a lock, whereas the owner says it is not an incident |

`request.md` and `artifact/` are given to the evaluated agent; `traps.md`, `expected.json` and `runs/` never. `runs/2026-11-15-author/` is the author's plan: a regression baseline, not a measurement.

## Log

- 2026-11-15: the grid received `incident=forget` from `release-skill` (T7, `runs/2026-11-15-blind-3`), not from this fixture. The author's plan, which answered `incident=yes` against the owner, now passes C2 by this path. The answer key has not changed.
- 2026-11-15: replayed blind since the grid was corrected (`runs/2026-11-15-blind-2`), by a fresh agent without the answer key: 12 traps out of 12, C2 included, through `incident=forget`. A single run. The agent reports three limits of the grid (a hook check that must read Jira, "nothing merges without approval" between limit and rule, a limit of the agent held by the server): noted here, and not corrected from this fixture, which only serves to measure.
- 2026-11-17: translated into English; the original French version is in git history. The fixture folder is renamed `ticket-vers-pr` → `ticket-to-pr`, and the request `artifact/demande.md` → `artifact/tool-request.md` (the evidence of every recorded plan follows: `tool-request.md:<line>`). Line for line: no evidence moved; in the request the branch format reads `type/KEY-123-short-title`. The `check.md` and `plan.md` of the recorded run are translated in the wording of today's CLI where the grid text had not changed since, by hand elsewhere; the commit ids the runs cite are unchanged. Translating is not correcting: nothing in the skill, the grid or the answer key's breadth changed.
