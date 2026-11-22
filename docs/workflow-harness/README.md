# Workflow harness: the study

A study made on 2026-11-21, at the owner's request, on the next direction of this project: going from one repository instrumented for agents to a team that builds and runs its own workflow, for example a feature ticket or a bug ticket handled end to end. One slice is built, the first of `harness-flow` (issue #143): `harness.py flow new`, `check`, `next`, `place` and `status --map`, which check a workflow on paper and run nothing. The rest is not built. The two epics that come out of the study are tracked as GitHub issues.

| Document | What it answers |
|---|---|
| [report.md](report.md) | The state of the art at the end of 2026: LangChain and LangGraph explained, the other ways to orchestrate agents, what exists in Rust, how the labs and leading companies build their own workflows, two reference flows, a decision grid. Fourteen load-bearing claims were checked by fact-checkers asked to refute them. |
| [proposal.md](proposal.md) | What this project could build: a third plugin, `harness-flow`, its skills, its ladder, the language question, a first slice and the epics after it, and the questions for the owner. |
| [decide.md](decide.md) | Where one step of a team workflow goes: the seven questions to ask in order, the nine places a step can land, the measurable symptoms that mean an engine, and the two reference flows placed step by step. The default is the ticket's state plus CI. |
| [flow-format.md](flow-format.md) | How to write and edit a flow definition: the order of work, every key with its allowed values, one step of each type ready to paste, a whole small flow, and the event files `flow next` takes. |
| [flow-spec.md](flow-spec.md) | The contract of that first slice: the definition format, the two templates, the twelve refusals of `flow check`, the fourteen rules of `flow next`, the grid of `flow place`, the fixture family. |
| [team-assessment.md](team-assessment.md) | Whether today's skills can assess an AI SDLC a team already built (partly), and the design of a skill that does, `harness-team`, with its levels, its achievements and its limits. |
| [research_notes/](research_notes/) | The eleven notes the report rests on, each with its sources and its list of what was not found. |

How it was made: seven web researchers, a critic who asked for four more notes, three architects each defending one design, a lead architect, and fact-checkers. Each document says what was not verified.
