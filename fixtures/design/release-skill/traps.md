# release-skill — planted traps

A release skill that does everything, its subagent and two AGENTS.md rules. Measures harness-design in review: each misplaced piece must be moved to an accepted destination, with its evidence (`path:line`), and no healthy piece may be touched.

| Id | Where | What is planted | What the plan must say |
|---|---|---|---|
| T1 | `SKILL.md:14` | "Never publish outside main", told as a story | A limit nobody overrides: server-side protection, or managed settings |
| T2 | `SKILL.md:12` | The version computation in prose | Computation: tested subcommand or script, possibly wired to a hook or a workflow |
| T3 | `SKILL.md:13` | "Check that the changelog has its entry" | Checkable rule, an incident if missed: blocking check |
| T4 | `SKILL.md:16` | `npm publish` with the token copied onto the workstation | Delivery with rights: workflow; permission or server-side protection are accepted for the token |
| T5 | `SKILL.md:8` | The repository tree | Nothing to write |
| T6 | `AGENTS.md:6` | "The agent never reads .npmrc.publish" | A limit of the agent: permission |
| T7 | `SKILL.md:19` | "Do not start if uncommitted files remain", which the owner calls harmless but not to be forgotten | A check in code: hook or script. The trap: leaving it as a step of the skill because it is not an incident |
| S2 | `SKILL.md:17` | Writing the announcement | Healthy: agent judgment, described by the skill (`current: session`) |
| S3 | `release-reviewer.md` | Read-only subagent, independent look | Healthy |
| S4 | `AGENTS.md:7` | A rule that cites its CI check | Healthy: the check exists, the line cites it (`current: ci_check`) |

The grader is generous on the destination (several are accepted), strict on the evidence (the piece must cite the right line) and on healthy items (none may receive a verdict other than KEEP). A healthy item carries its nature: a piece of another nature drawn from the same line is another piece.

`request.md` and `artifact/` are given to the evaluated agent; `traps.md`, `expected.json` and `runs/` never. `runs/2026-11-15-author/` is the plan of the author of the traps: a regression baseline, not a measurement.

## Revisions

- 2026-11-15, after the first blind run (`runs/2026-11-15-blind`): S1 ("tag and push", line 15) is withdrawn, it is a delivery in the harness-audit grid and not a healthy item; the workflow that `AGENTS.md:7` cites is added to `artifact/`, without it S4 could not be checked; the grader tells apart by their nature two pieces drawn from the same line. Runs from before this date do not compare with those after.
- 2026-11-15, after the second run (`runs/2026-11-15-blind-2`): the grid receives the destination `release_gate` ("nothing is published without it"), which T3 now accepts. No stored run changes score: both already passed T3.
- 2026-11-15, after the run on the held-out fixture: T7 is added, as the last line of the skill so as to shift no evidence. It takes up here, where correcting is allowed, the case that failed there. Runs from before do not contain this line.
- 2026-11-15, after `runs/2026-11-15-blind-3`: the `incident` question of the grid receives the answer `forget` ("lost time, but it must not be possible to forget it"). The author's plan passes T7 by this path. The answer key of T7 has not changed.
- 2026-11-17: translated into English; the original French version is in git history. Line for line: no evidence moved. In the artifact, the package is renamed `paquet-demo` → `demo-package` and the subagent's JSON key `ecarts` → `gaps`. The held-out fixture `ticket-vers-pr` is renamed `ticket-to-pr`. The `check.md` and `plan.md` of the recorded runs are translated in the wording of today's CLI where the grid text had not changed since, by hand elsewhere; the commit ids the runs cite are unchanged.
