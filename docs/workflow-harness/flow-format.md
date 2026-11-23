# Writing a flow: the definition file, key by key

Date: 2026-11-22. This page is for the person who edits the file `flow new` writes. It lists every key, says which steps need it, and gives one step of each type ready to paste. The rules behind it are in [flow-spec.md](flow-spec.md); where a step belongs is [decide.md](decide.md).

Nothing here runs an agent, a pipeline or a clock. The commands read the file and answer on paper.

## The order of work

0. Before any file: `python3 cli/harness.py flow fit --questions`, then `flow fit <answers.json>`, says whether you need a workflow at all, which tool, and the published costs it copies from the pages, dated and sourced.
1. `python3 cli/harness.py flow new feature` (or `bug`) writes `.harness/flow/feature.json`, a starting definition. Its approvals have no `can_judge`: each waits for its judge's answer, and the flow stays at level 0 until every one is answered.
2. Edit that file: this page.
3. `flow check <file>` refuses a flow that could loop, wait or spend without end, or reach a write that cannot be taken back with no gate that can refuse it. Each problem ends with the key to write. When the flow holds, it prints what bounds one run.
4. `flow place <file>` says where each step belongs, and whether one needs a workflow engine. With `--answers <answers.json>`, the answers file of `flow fit`, it also reads the symptoms measured on your runs.
5. `flow status <file> --map` gives the level reached on paper and the next step; it takes `--answers` too.
6. `flow next <file> --event <event.json> --new` tries the flow by hand, one event at a time.

From your own repository: with `--format md` (the default), every command that exits 0 or 1 ends, on stderr, with a note that gives the full command and the folder of these pages; with `--format json`, stderr stays empty.

`flow check` and `flow place` answer two different questions and each can pass while the other fails. `flow check` looks at the shape: loops, deadlines, keys, ways out, a gate before what cannot be taken back. `flow place` looks at where each step lives and whether each judge can judge. `flow status` needs both.

## Words

- **Flow**: one team workflow for one kind of ticket. **Run**: one ticket going through it.
- **Step**: what happens in one state of the flow. In the file, a step is one entry of `states`, and its name is the state's name.
- **Event**: a fact that ends a step, such as "the checks passed". Each step lists, under `on`, the events it can end with and where each one leads.
- **Transition**: one line of `on`: this event leads to that step.
- **Stop point**: a name given to a transition with `reaches`. It marks a milestone, such as "the draft pull request is open". `stop_at` picks one stop point: a run that takes that transition ends there, on purpose, and the step the transition leads to is not entered. A stop point is not a step, even when the two have the same name: in the bug template, the stop point `root_cause` is reached by a transition out of the step `notify`.
- **Cap**: the most times one run may enter a step, counted over the whole run and never reset. Every circle of steps needs one. Put it on the step that costs (the agent), not on the cheap check after it.
- **Premise check**: a program or an agent step that first checks that the facts it starts from still hold: the branch has not moved, the bug still reproduces. `flow check` asks for one after a wait or a person's work, because facts go stale while nothing runs.
- **Budget**: what one run may spend, in dollars and in minutes of running steps. Waiting costs nothing.

## The file

One JSON object. Names of flows, steps, events, reasons and stop points are lowercase letters, digits and underscores, starting with a letter.

| Key | Value | Needed | Meaning |
|---|---|---|---|
| `format` | `1` | yes | The version of this format |
| `name` | a name | yes | The flow's name |
| `kind` | text | no | `feature`, `bug`, or your own word |
| `start` | the name of a step | yes | Where a run begins |
| `stop_at` | the name of a stop point | yes | Where a run ends on purpose. One of the names given by `reaches` |
| `budget` | `{"dollars": n, "minutes": n}`, both above 0 | yes | What one run may spend. The run is stopped at the first event that passes it |
| `irreversible` | a list of stop point names, `[]` allowed | no | The stop points whose write cannot be taken back; absent, `merged` and `deployed`. `flow check` refuses a transition that reaches one when a run can take it crossing no gate that can keep the run from every write of that stop point (a gate left by `deadline_passed` does not count; a step of type `human` that makes such a write, or writes `merged` or `deployed` even when this list leaves them out, counts as one for the writes after it), and refuses a name here that no transition reaches |
| `states` | an object: step name → step | yes | The steps. `done` and `stopped` are the two ends of every flow: never declare them |

## A step

| Key | Value | Which steps | Meaning |
|---|---|---|---|
| `type` | `code`, `agent`, `human`, `gate` or `wait` | all | Who performs the step: a program with no model call; a coding agent; a person who does work; a person who decides; nobody, the run waits for something outside |
| `does` | one plain sentence | all | What the step does. Shown to people |
| `on` | an object: event → transition, at least one | all | The ways out of the step |
| `cap` | a whole number above 0 | any; needed in every circle | The most times one run may enter the step |
| `writes` | a list of `{"what": "...", "key": "..."}` | any | Each thing the step writes outside (ticket, branch, pull request). `what` names the thing. `key` must contain `{ticket}`, so that the step recognises its own write when it runs twice. One key names one thing in the whole file |
| `checks_premise` | `true` | `code` and `agent`; needed after a `wait` or a `human` step, and after a `gate` when the step writes | The step first checks its facts still hold. It then needs two events under `on`: one for "they hold", one for "they changed" |
| `deadline_hours` | a number above 0 | needed on `gate`, `wait`, `human`; allowed on the others | After that long with no event, the step has failed |
| `judge` | text | needed on `gate` | Who decides, by role or by name |
| `shows` | text | needed on `gate` | What the judge reads. It must be, to the letter, the `what` of a `writes` entry of another step |
| `can_judge` | `yes` or `no` | `gate`; read by `flow place` | Can the judge really judge what they approve? A person answers this: `flow new` never writes it, and until it is written the gate waits for its judge, `flow place` leaves it open and the flow stays at level 0 |
| `survives` | `restart` or `midway` | `code`, `agent`; read by `flow place` | `restart`: minutes to a few hours, and starting again from the beginning is fine. `midway`: it must go on from its middle |
| `units` | `one` or `many` | `code`, `agent`; read by `flow place` | Does the work split into many independent units? |
| `repositories` | `one` or `several` | `code`, `agent`; read by `flow place` | How many repositories need this step |
| `weak_model` | `yes` or `no` | `agent`; read by `flow place` | Is the step here only because today's model is weak? |

Any other key is ignored. The six keys read by `flow place` are explained, question by question, in [decide.md](decide.md).

## A transition

A transition is the value of one event under `on`.

| Key | Value | Needed | Meaning |
|---|---|---|---|
| `to` | the name of a step, `done` or `stopped` | yes | Where the event leads. `done`: the run finished. `stopped`: the run was stopped before its end |
| `reason` | a name | when `to` is `stopped`; optional with `done` | Why the run ended, kept in the run record |
| `reaches` | a name | no | The stop point this transition reaches |

Three events exist everywhere and are written only when you want something other than a stop:

- `human_stop`: a person stops the run. Never written in the file: it works in every step.
- `deadline_passed`: the step's deadline went by. Not written, it stops the run. Written, it is a transition like any other, for example to hand a gate over to a second judge.
- `step_failed`: the program or the agent crashed or gave nothing usable. Not written, it stops the run. Written on a `code` or `agent` step with a `cap`, it starts the step again.

## One step of each type, ready to paste

Paste a step inside `states`, rename it, then point the `to` of an event of an earlier step at it. The five below come from the whole flow further down, which passes `flow check` and `flow place`.

A program:

```json
{"publish": {"type": "code", "does": "Posts the draft on the ticket, so that a person can read it",
             "survives": "restart", "units": "one", "repositories": "one",
             "writes": [{"what": "the draft", "key": "draft-{ticket}"}],
             "on": {"published": {"to": "review"}}}}
```

An agent, in a circle with the gate after it, so it carries a cap:

```json
{"drafting": {"type": "agent", "does": "Drafts the change to the documentation", "cap": 3,
              "survives": "restart", "units": "one", "repositories": "one", "weak_model": "no",
              "on": {"draft_written": {"to": "publish"}}}}
```

A person who decides. Two ways out, so that the gate can refuse:

```json
{"review": {"type": "gate", "does": "A maintainer reads the draft and accepts it or sends it back",
            "judge": "a maintainer of the documentation", "shows": "the draft", "deadline_hours": 48,
            "can_judge": "yes",
            "on": {"approved": {"to": "apply_by_hand", "reaches": "reviewed"},
                   "sent_back": {"to": "drafting"}}}}
```

This gate is shown answered. When you paste it, leave `can_judge` out: only the judge answers it, and until then `flow place` leaves the gate open.

A person who works:

```json
{"apply_by_hand": {"type": "human", "does": "A person publishes the accepted draft on the site no program may touch",
                   "deadline_hours": 72,
                   "on": {"applied": {"to": "site_wait"},
                          "cannot_apply": {"to": "stopped", "reason": "cannot_apply"}}}}
```

A wait. The program after it checks its facts:

```json
{"site_wait": {"type": "wait", "does": "Waits for the site to be rebuilt", "deadline_hours": 24,
               "on": {"site_rebuilt": {"to": "confirm"}}}}
```

## A whole flow

```json
{"format": 1, "name": "docs_change", "kind": "documentation",
 "start": "intake", "stop_at": "reviewed", "budget": {"dollars": 4, "minutes": 45},
 "states": {
  "intake": {"type": "code", "does": "Checks the ticket is eligible and opens the run record",
             "survives": "restart", "units": "one", "repositories": "one",
             "writes": [{"what": "the run record", "key": "run-{ticket}"}],
             "on": {"accepted": {"to": "drafting"},
                    "not_eligible": {"to": "stopped", "reason": "not_eligible"}}},
  "drafting": {"type": "agent", "does": "Drafts the change to the documentation", "cap": 3,
               "survives": "restart", "units": "one", "repositories": "one", "weak_model": "no",
               "on": {"draft_written": {"to": "publish"}}},
  "publish": {"type": "code", "does": "Posts the draft on the ticket, so that a person can read it",
              "survives": "restart", "units": "one", "repositories": "one",
              "writes": [{"what": "the draft", "key": "draft-{ticket}"}],
              "on": {"published": {"to": "review"}}},
  "review": {"type": "gate", "does": "A maintainer reads the draft and accepts it or sends it back",
             "judge": "a maintainer of the documentation", "shows": "the draft", "deadline_hours": 48,
             "can_judge": "yes",
             "on": {"approved": {"to": "apply_by_hand", "reaches": "reviewed"},
                    "sent_back": {"to": "drafting"}}},
  "apply_by_hand": {"type": "human", "does": "A person publishes the accepted draft on the site no program may touch",
                    "deadline_hours": 72,
                    "on": {"applied": {"to": "site_wait"},
                           "cannot_apply": {"to": "stopped", "reason": "cannot_apply"}}},
  "site_wait": {"type": "wait", "does": "Waits for the site to be rebuilt", "deadline_hours": 24,
                "on": {"site_rebuilt": {"to": "confirm"}}},
  "confirm": {"type": "code", "does": "Checks the site shows the accepted draft, then records it",
              "checks_premise": true, "survives": "restart", "units": "one", "repositories": "one",
              "writes": [{"what": "the confirmation", "key": "confirm-{ticket}"}],
              "on": {"confirmed": {"to": "done", "reaches": "published", "reason": "published"},
                     "drifted": {"to": "stopped", "reason": "drifted"}}}}}
```

Its gate is answered, as a team writes it once the judge has said yes.

As written, a run of this flow stops on purpose after `review`: `stop_at` is `reviewed`, the stop point the event `approved` reaches. The three steps after it (`apply_by_hand`, `site_wait`, `confirm`) are described but not run. To run them too, set `stop_at` to `published`. `flow new` and `flow check` say the same of your own file.

## Trying it by hand: events and the run

`flow next` takes the definition, one event, and the run the ticket is in. It answers what the run does: it moves, it ends, or the event is refused. It runs nothing.

An event is one JSON object in a file. The four below play the flow above from its start to its stop point.

```json
{"id": "T-12:intake:1:accepted", "type": "accepted", "payload": {"dollars": 0, "minutes": 1}}
```

```json
{"id": "T-12:drafting:1:draft_written", "type": "draft_written", "payload": {"dollars": 1.5, "minutes": 12}}
```

```json
{"id": "T-12:publish:1:published", "type": "published", "payload": {"dollars": 0, "minutes": 1}}
```

```json
{"id": "T-12:review:1:approved", "type": "approved", "at": {"state": "review", "visit": 1}}
```

| Key | Needed | Meaning |
|---|---|---|
| `id` | yes | Names the fact: ticket, step, round, what happened. The same fact delivered twice carries the same id and is counted once |
| `type` | yes | What happened: an event the step lists under `on`, or one of the three that exist everywhere |
| `payload` | when a `code` or `agent` step ends | `{"dollars": n, "minutes": n}`: what the step cost. 0 is a cost. A cost smaller than a hundredth of a cent is counted as a hundredth of a cent, so that no cost counts for nothing |
| `at` | for `deadline_passed` and `step_failed`; wise for an answer to a gate | `{"state": "<step>", "visit": <n>}`: the step and the round the event answers. An answer meant for an earlier round is refused |

The run is the record of one ticket: the step it is at, how many times it entered each step, what it spent, the events already counted. You never write it: `--new` starts one and `--save-run` keeps it.

```
python3 cli/harness.py flow next flow.json --event e1.json --new --save-run run.json
python3 cli/harness.py flow next flow.json --event e2.json --run run.json --save-run run.json
```

The first line answers "intake → drafting, on accepted." and what is left of the budget. Give `--run` the file `--save-run` wrote, each time. Without `--save-run`, ask for `--format json` and keep the `run` part of the answer.
