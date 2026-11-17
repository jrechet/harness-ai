# Campaign of 2026-11-10 — task `escalated` on its three arms

> The project and the task were corrected on 2026-11-11 after this campaign: type check per workspace, no more command that replays everything, statement without the label. The outputs below are about the old version.

First before-and-after measurement of the bench. Three fresh agents, the same instruction word for word, one arm each. Outputs in `2026-11-10-task-blind-<arm>/`: `diff.patch`, `report.md`, `note.md`.

| Arm | Repository instructions | Score | Tokens | Tool calls | Duration |
|---|---|---|---|---|---|
| `bare` | none | 7/7 | 126,000 | 33 | 232 s |
| `asis` | generated `CLAUDE.md`, 104 lines, and the web note | 7/7 | 113,000 | 18 | 148 s |
| `harness` | `AGENTS.md` of step 1, 23 lines | 7/7 | 116,000 | 27 | 143 s |

Cost: 355,000 tokens, for 270,000 announced. The estimate per run was too low; it is corrected in `cli/harnesslib/bench.py`.

## What the measurement says
**No gap in score.** On this task, with this model, the harness does not change the result, and the generated file never reviewed does not damage it. One draw per arm: it is not a proof, one way or the other.

The only visible gap is in effort: without instructions, the agent took more time and more calls to find the ADR and the post-mortem on its own. On one draw, it is a hint.

What the reports show:
- `bare` read `README.md`, ADR 0001 and the post-mortem of its own accord, and applied the post-mortem's instruction.
- `asis` set aside of its own accord three instructions of the generated file, and said so: the confirmation before every command, the `lint` and `build` commands that do not exist, the import from the web to the API.
- `harness` cites `AGENTS.md` for having run all the tests. Its report is the shortest.

## Why it separates nothing
1. **The task is caught by the project.** The tempted solution fails the repository's tests and type check: an agent that runs `npm test` fixes it on its own. The task measures "does the agent run the tests", not what the instructions teach it. `bench selftest` now reports it with a warning.
2. **The planted fact is discoverable.** The incident is in `docs/postmortems/`, and a careful agent reads `docs/`.
3. **The bare arm was not bare.** The agents were launched from the campaign session and inherited its instructions: their reports carry that session's "Questions" section and "Assumptions made without asking", and one of them used a tool of the session to file a task suggestion. So the three arms had a common harness on top of their own.

## Project defect found by an agent
The `bare` arm noted that the CI gap is narrower than the post-mortem says: the `api` job runs the type check of the whole repository when `packages/shared` changes, so a missing label would be caught there. Only the web's tests do not run. Fact I1 of this fixture is to be tightened, or the `api` job limited to its own workspace.
