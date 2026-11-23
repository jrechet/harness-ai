# harness-flow fixtures

Recorded cases with their answers, for the first slice of `harness flow`: a team's workflow from a ticket to production, written as a small table of states. They measure three things. Does the transition function give, after each event, the state the rules ask for (`sequences/`)? Does a definition hold together, and when it does not, is each problem reported once, at the right place, in the right order (`cases/`)? Does each step of a flow land in the right place, and is the one step that needs an engine named (`place/`, `cases/`)?

The answers were written by hand, by reasoning from the contract ([flow-spec.md](../../docs/workflow-harness/flow-spec.md)): no answer here was produced by running the code it grades. Where the contract did not decide, no answer was written. The first nineteen sequences and the three flows to place were written before any code existed, by someone who did not write it. The other sequences and the cases were added after three reviews of the slice, by the session that also changed the code: they hold a regression in place, they are not an independent measure.

```
fixtures/flow/
├── definitions/         # flows written by hand: the two templates, and one for what they do not hold
├── sequences/<name>.json   # one ticket's run: the events received, in order, and the expected state after each
├── cases/<name>.json    # one definition, often a template with one thing changed: what check, place and status must answer
├── place/<name>/
│   ├── definition.json  # only when the flow is not a template
│   ├── traps.md         # only in trapped/: what was planted and why
│   └── expected.json    # where each step must land, and the verdict
└── fit/<name>/
    ├── answers.json     # what a team recorded before any definition exists; `flow fit` reads it as it is
    └── expected.json    # the verdict, or the keys the refusal names
```

## How it is graded

No agent is run and nothing is launched by hand: the family is graded by a unit test, at every commit.

```bash
python3 -m unittest discover -s cli/tests -p test_flow_fixtures.py -v
```

That test calls the code directly (`next_state`, `check`, `new` and `place`, the Python interface of the contract's section 5) and fails with the path of a fixture it cannot read. It never skips: without the code, it fails on its first line and says which module is missing.

The cases have their own test, which calls `check`, `beyond_stop`, `place` and `status`:

```bash
python3 -m unittest discover -s cli/tests -p test_flow_cases.py -v
```

A second test, `cli/tests/test_flow_fixtures_format.py`, needs no code. It checks the family itself: every file is well formed, every definition follows the format, every expected answer is one its definition allows (a move follows a declared transition, a refusal changes nothing, what is spent grows by the event's own costs), and this page names every fixture.

## The definitions

| File | What it is |
|---|---|
| `feature` | The feature template, written from the contract's table: 18 steps from "ready for an agent" to the closed ticket, stopping by default when the pull request is marked ready. `flow new feature` must write the same states, events, caps and writes; only the sentences are the code author's. Its three gates are answered `"can_judge": "yes"`, as a team would answer them: the template itself leaves that answer to the team (the contract's section 12.1) |
| `bug` | The bug template: 14 steps from triage to the closure check days later, stopping by default at the root cause. Its one gate is answered, like the feature's |
| `every-case` | A small flow for what the templates do not hold: a step done by a person, an agent step started again when its job crashes (three times at most), a gate whose deadline hands over to another judge, and an end with no reason given |
| `retry-on-deadline` | Two steps: an agent step that declares its own deadline back to itself, so that a job that takes too long is started again, three times at most |

A sequence, a case or a flow to place names its definition as `template:feature` or `template:bug` (the test then asks the code for its template, which no judge has answered yet), or by a path from this folder, such as `definitions/feature.json` for the answered file. In `test_flow_fixtures_format.py`, which runs without the code, `template:<kind>` is read as `definitions/<kind>.json` with `can_judge` removed from every gate. The test also compares each template with its file here.

## The sequences

One file is one ticket. `start` is `"new"` or the run document the ticket comes back with. Each entry holds the event received and, under `expect`, the answer: `outcome` and `reason`, the `state` of the run returned, and when it matters the number of entries into some states (`visits`; a state never entered is written 0), what the run has spent, what remains of the budget and whether it is passed, and the identifiers of the events the run has taken into account (`seen`). `override` replaces the stop point or the budget of the definition for that file. `note`, where present, says in plain words which rule of the contract decides; no test reads it.

Costs are in quarters of a dollar and whole minutes, so every sum is exact. The feature template allows 20 dollars and 240 minutes for one ticket, the bug template 10 and 120.

| File | Flow | What it shows |
|---|---|---|
| `feature-to-ready-pr` | feature | The path from `ready` to the default stop point, with a large plan approved by a person: when the pull request is marked ready the run ends on purpose (`done`, `stop_point`), and one more event is refused because the run has ended. The steps after it are played by `feature-to-delivered` |
| `event-twice` | feature | An event delivered twice, right away and three events later, changes nothing and is paid once; the same identifier with another type and another cost is still the same event |
| `events-out-of-order` | feature | An event that arrives where it does not belong is refused, as often as it is sent; a type nobody declares is told apart; sent again once it fits, the refused event moves |
| `lost-event` | feature | CI answers before the run knows the pull request is open: refused, then accepted when delivered again. Then a CI fix whose job never answers is ended by its deadline |
| `step-failed` | feature | A crashed step must still say what it cost: without both costs the report is refused, with them the run stops and the cost is counted |
| `stale-answer` | feature, stopping at the merge | An approval of the first version of the pull request arrives while the second is under review: refused as an answer to an earlier round; the approval of the current round moves |
| `cap-reached` | feature | The checks fail six rounds in a row: the sixth failure stops the run at once (`cap_reached`) instead of paying a seventh round of coding |
| `budget-exceeded` | feature, 2 dollars and 30 minutes | Landing exactly on the budget is within it; the next event passes it, in minutes alone, and stops the run although its transition was legal |
| `human-stop` | feature | A person stops the run while the agent codes: taken whatever the event says about state and cost; the agent's later answer finds the run ended |
| `unknown-label` | feature, from a run in a state nobody defined | The first event stops the run as `inconsistent` instead of guessing; the next finds it ended |
| `counts-over-cap` | feature, from a run that says the agent coded 7 times | The twin of `unknown-label`: the same two answers, even when the first event is a human stop |
| `rework-loop` | feature, stopping at the merge | A reviewer asks for changes twice, each time back through coding, the checks and CI; the third request stops the run, the rework step being allowed twice |
| `bug-already-fixed` | bug, 1 dollar and 10 minutes | The premise check finds the bug already fixed, at a cost above the budget: the run still ends as `done`, says it went over, and no root cause is attempted |
| `bug-low-confidence` | bug | A root cause with a low confidence stops the run with that reason |
| `bug-to-root-cause` | bug | Its twin: a confident root cause ends the run on purpose at the bug flow's default stop point |
| `gate-deadline` | feature | A deadline with no state and round is ill formed; one for another state is stale; the one for the gate the run waits in stops the run |
| `ci-stale-and-fix` | bug, stopping at the merge | A CI result for an older commit sends the run back to wait; two CI fixes are paid; a third red result stops the run |
| `every-case-retry` | every-case | A declared failure starts the agent step again, each failure paid, until the cap closes that way out; a failure reported for an earlier round is refused |
| `every-case-finished` | every-case | A gate that declares its deadline hands over to another judge instead of stopping; a person does a step by hand at no cost to the run; a transition to `done` without a reason ends as `finished` |

| `feature-to-delivered` | feature, from a run already in the human review | Past the default stop point the run goes on: approval, merge authorisation, merge, deploy, and the closed ticket (`done`, `delivered`). The stop points on the way are passed through |
| `feature-stops-at-merge` | feature, stopping at the merge, from a run at the merge authorisation | The merge ends the run on purpose (`done`, `stop_point`): the delivery is not entered |
| `feature-head-moved` | feature, from a run at the merge | The branch moved since the approval: nothing is merged, the run stops with that reason |
| `feature-merge-failed` | feature, from a run at the merge | The merge fails: stopped with the reason the definition gives |
| `feature-deploy-failed` | feature, from a run waiting for the delivery | The deploy fails: stopped, and a wait reports no cost |
| `feature-closing-premise-failed` | feature, from a run at the closing | The facts no longer hold after the delivery: stopped instead of closing the ticket |
| `feature-plan-rejected` | feature | The plan is rejected by its reviewer and written again; the third rejection stops the run, planning being allowed three times |
| `bug-duplicate` | bug | Triage finds a duplicate: `done` with that reason, before any agent runs |
| `bug-to-fixed` | bug, from a run already in the human review | A person merges, the run waits, the closure check finds the signal stopped: `done`, `fixed` |
| `bug-not-fixed` | bug, from a run at the closure check | The signal goes on: `stopped`, `not_fixed` |
| `bug-rejected` | bug, from a run in the human review | The pull request is closed with a reason: `done`, `rejected` |
| `order-ended-run` | feature, from an ended run | An ended run answers `run_ended` to a known identifier and to a human stop; only an ill-formed event is told first |
| `order-inconsistent-known-id` | feature, from a run in a state nobody defined | Stopped as `inconsistent` even when the event's identifier was already seen, and the identifier is not recorded twice |
| `human-stop-known-id` | feature | A human stop that reuses the identifier of an earlier event still stops the run: a person's stop is never dropped as a duplicate |
| `order-stale-before-cost` | feature | A failure reported for another round, without its costs, is refused as stale; for the right round, as missing its costs |
| `reason-over-budget` | bug, 1 dollar and 10 minutes | A low confidence whose cost passes the budget still stops the run with its own reason, and says it went over |
| `stop-point-over-budget` | bug, 1 dollar and 10 minutes | Its twin: the stop point reached at a cost above the budget is `done`, not `stopped` |
| `stop-point-before-cap` | feature, stopping at the draft pull request, from a run whose CI wait is at its cap | The stop point ends the run although the next step could not be entered again |
| `budget-before-cap` | feature, 5 dollars, from a run whose agent has used its six rounds | The checks fail at a cost that passes the budget: the reason is the budget, not the cap |
| `budget-dollars-alone` | feature, 2 dollars | The twin of `budget-exceeded`: the budget is passed in dollars alone |
| `deadline-retry-is-paid` | retry-on-deadline | A deadline declared back to its own agent step is a retry: refused without its costs, counted with them, and ended by the budget |

The first seventeen are the contract's first list (fifteen and two twins). The next two were added for the cases only `every-case` holds. The last twenty-one were added after the reviews: the two flows after their default stop point, the order of the rules pair by pair, and the retry on a deadline.

A sequence cannot state a count above a cap (the format test refuses it), so "a count above its cap is kept as given" is pinned by a unit test, `test_flow_review.py`, not by `counts-over-cap`.

Beyond the recorded sequences, the same test checks by program, on the two templates and every file of `definitions/`: that every state and every event type, with and without costs and round, get one well-formed answer; and, on 200 generated sequences of 300 events, that no step is entered more often than its cap, that what is spent never falls, that an ended run never moves and that an event delivered twice changes nothing.

## The flows to place

`expected.json` gives every step its place (one of the nine of the contract's section 6), the steps that need an engine, the gates nobody can judge, the steps left open, the verdict and whether the placement passes.

| Folder | Flow | What it shows |
|---|---|---|
| `feature` | The feature template with its gates answered (`definitions/feature.json`) | Every step has a place; the verdict is "no step needs an engine"; the placement passes |
| `bug` | The bug template with its gate answered (`definitions/bug.json`) | The same |
| `trapped` | `library_upgrade`, its own definition: twelve steps to move a shared library to a new major version | Exactly one step needs an engine (a rewrite of stored records that lasts days and must go on from the middle) and exactly one gate cannot be judged by anyone (a sign-off on a log of forty thousand lines). Beside them, three steps that only look like they need an engine: a wait of ten days, an agent step of four hours that may start again, a gate with a deadline of two weeks. The verdict names the one step, and the placement fails because of the gate. [traps.md](place/trapped/traps.md) says what was planted and why |

## The cases

One file is one definition and what the three commands that replay nothing must answer on it. `definition` is a reference as above; `remove` (a list of dotted paths, such as `states.coding.cap`) then `set` (path → value) change it. `check` is the full list of problems `flow check` must report, each with its `code` and `where`, in order; an empty list means the definition holds. `not_run`, when present, is the list of steps behind the stop point, which no run enters as the file is written. `waiting`, when present, is the list of gates that wait for their judge's answer (no `can_judge`), in file order. `bounds`, when present, gives part of what bounds one run of a flow that holds: its `circles` (each `steps` and `most_entries`), the stop points that cannot be taken back (`irreversible`) and those the file treats as possible to take back (`taken_back`), and for each write that cannot be taken back the last gate that guards it on the shortest path (`guards`: `state`, `event`, `last_gate`, `steps_between`, `agents_between`). `answers`, when present, is an answers file of `flow fit`, a path from this folder, given to `place` and `status` as `--answers` gives it. `place`, when present, gives the three lists, the verdict and `passed` of `flow place`, the destination of the steps it names (the others are not compared), under `missing` the key each open step lacks and, only with `answers`, under `fired` the symptoms read above their threshold; its verdict is then `symptom` where no step needs an engine and a symptom fired. `status`, when present, gives the level and which of its three checks pass. The cases from `feature-answered` to `wait-retyped-as-program` were added for the contract's sections 12.1 and 12.2, and the four from `symptom-on-a-placed-flow` to `answers-nothing-measured` for its section 12.5, from its examples, by the sessions that also wrote the code for them: they hold a regression in place, they are not an independent measure.

| File | Flow | What it shows |
|---|---|---|
| `feature-as-written` | feature | It holds, but no template answers for the judge: the three approvals wait, the placement is open, level 0; the six steps after `mark_ready` are described and not run |
| `bug-as-written` | bug | The same with its one approval; the ten steps after `notify` are not run |
| `feature-answered` | feature, answered | Nothing waits, level 1; two circles of 3 and 16 entries at most; the merge and the delivery are guarded by the merge authorisation, 0 and 1 step before them |
| `bug-answered` | bug, answered | Nothing waits, level 1; no circle a run can turn; the human review is the gate of its own merge |
| `one-approval-answered` | feature, the plan review answered | The two other approvals still wait, in file order; level 0 |
| `every-case-placed` | every-case | A step done by a person is held by the ticket; the second judge's gate is a human gate; no step lies behind a stop point that sits on the transition to `done` |
| `engine-alone` | bug, the closure check must go on from its middle | Verdict "would need an engine", and the placement passes: an engine is an answer, not a failure |
| `gate-nobody-can-judge-alone` | feature, the merge authorisation cannot be judged | Verdict "no step needs an engine", and the placement fails because of the gate alone; `flow check` still passes |
| `answers-missing` | feature, three answers missing or misspelt | Three open steps, each with the key it lacks; verdict "cannot be placed yet"; level 0 although the definition holds |
| `order-of-the-questions` | feature, two steps with several answers that name a place | Many units wins over several repositories; "must go on from its middle" wins over everything after it |
| `circle-through-the-stop-point` | bug, `root_cause` without its cap | A circle that only closes through the stop point cannot repeat: the definition holds |
| `circle-closed-by-moving-the-stop-point` | the same, stopping at the draft pull request | The same circle now repeats: refused |
| `typo-in-a-target` | feature, one target mistyped | One problem, at that event, not one per step behind it; the three checks of level 1 fail |
| `step-nobody-leads-to` | bug, one step added and not wired | One problem, at that step |
| `loop-without-cap` | feature, the coding agent without its cap | One problem for the group, at its first step |
| `gate-cannot-refuse` | feature, the merge authorisation with one way out | Refused |
| `gate-shows-nothing` | bug, the reviewer shown "the diff" | Refused: no step writes it |
| `gate-shown-a-late-write` | feature, "the plan" written only behind the stop point | Refused: a gate that runs cannot be shown what a step that never runs writes |
| `premise-check-missing` | feature, the CI check without its premise check | Refused at the transition out of the wait |
| `stop-point-is-a-step-name` | bug, `stop_at` set to the step `fix` | No stop point: a stop point is a name a transition reaches, not a step |
| `unknown-type` | bug, one step of type "person" | `flow check` says it once; `flow place` leaves the step open and asks for `type` |
| `several-problems-in-order` | bug, five things removed | The problems come in the order of the contract's table, then in file order |
| `merge-without-a-person` | feature, answered, every gate removed, stopping at the delivery | The merge and the delivery cannot be taken back and no gate stands before them: two problems, the path printed |
| `merge-behind-the-stop-point` | the same, stopping at the ready pull request | The same two problems: the whole graph is read, so moving the stop point never removes the last gate |
| `gate-on-one-branch-only` | the same, the plan review kept | A small plan goes around the plan review: the same two problems |
| `silence-is-consent` | feature, answered, both pull request approvals passing on in silence | A gate left by its deadline is read as absent: the same two problems |
| `refusal-leads-to-the-write` | feature, answered, the refused merge handed to a step that merges anyway | A gate whose every answer leads to the write guards nothing: the same two problems |
| `silence-on-the-last-gate-only` | feature, answered, only the merge authorisation passing on in silence | It holds: every path to the merge has crossed the human review by an answer |
| `reaches-on-a-stop` | merge-behind-the-stop-point, the merge ending the run | A transition to `stopped` that reaches "merged" made the write: one problem |
| `gate-with-a-mistyped-type` | bug, answered, the review typed "gat" | One line, `unknown_step_type`: the new refusal waits until the type is fixed |
| `wait-watches-a-person-merge` | bug, answered, the review retyped as a wait | The program sees no gate before the merge: refused |
| `person-merges-by-hand` | bug, answered, the review retyped as a person's work | A person makes the write: it holds, and no gate is asked |
| `gate-far-before-the-write` | feature, answered, only the plan review left and every plan through it | It holds; the bounds say the gate stands 7 steps before the merge, 2 of them agents |
| `irreversible-own-name` | feature, answered, `"irreversible": ["ready_pr"]` | The team's own word: the ready pull request is reached crossing no gate, refused |
| `irreversible-empty` | merge-without-a-person, `"irreversible": []` | The team says nothing is irreversible: it holds, no write is checked |
| `irreversible-not-a-list` | feature, answered, `"irreversible": "merged"` | The file cannot be read as a flow, and only that is said |
| `irreversible-typo` | feature, answered, two names no transition reaches | The same: a slip of the pen never switches the rule off in silence |
| `stop-point-renamed` | merge-without-a-person with the merge and the delivery renamed | It holds, since the program cannot know those names; the bounds list them as possible to take back |
| `huge-cap-and-budget` | feature, answered, a cap of a million and a budget of a billion dollars | It holds; the bounds print the figures, no threshold is applied |
| `writes-deleted` | feature, answered, the draft pull request declaring no write | It holds: what `flow check` cannot see |
| `wait-retyped-as-program` | feature, answered, the CI wait written as a program | It holds: what `flow check` cannot see |
| `symptom-on-a-placed-flow` | feature, answered, with the answers of `fit/symptom-fired` | No step is written as needing an engine, and the verdict, `symptom`, names the two symptoms measured above zero; the placement passes and the level stays 1 |
| `symptom-beside-an-engine` | engine-alone, with the same answers | The verdict keeps its code, engine, and adds the two symptoms |
| `answers-nothing-above` | feature, answered, with the answers of `fit/ticket-state-and-ci` | No step needs an engine, as the file is written: the verdict says 7 of the 8 symptoms were measured, none above its threshold, and lists the one not measured |
| `answers-nothing-measured` | feature, answered, with the answers of `fit/nothing-measured` | No step needs an engine, as the file is written, and nothing is known from the runs: never read as reassurance |
| `every-answer-merges` | feature, answered, the refused merge handed to a copy of the merge step | A gate guards a stop point, not one transition: both merges and both deliveries are refused |
| `bug-every-answer-merges` | bug, answered, both answers of the review reaching the merge | The only gate cannot keep the run from the merge: both of its answers are refused |
| `refusal-reaches-the-write` | feature, answered, the merge authorisation writing the merge on both of its answers | An answer that makes the write is no refusal: both are refused |
| `refusal-deploys-directly` | feature, answered, the refused merge handed to a step that deploys without merging | The gate guards the merge, not the deploy: the two deploys are refused, the merge is not |
| `person-merges-then-pipeline-deploys` | feature, answered, the merge made by hand by a person, the pipeline deploying after it | The person's merge stands before the deploy as a gate would: it holds |
| `person-merges-on-silence` | bug, answered, the review retyped as a person's work whose deadline merges | A person's step left by `deadline_passed` is nobody's decision: that merge is refused |
| `person-merges-on-silence-then-pipeline-deploys` | as `person-merges-then-pipeline-deploys`, the merge also made when the person's deadline passes | The silent merge is refused, and it guards nothing after it: the deploy is refused too |
| `person-merges-what-can-be-taken-back` | as `person-merges-then-pipeline-deploys`, with `"irreversible": ["deployed"]` | The person's merge is still their decision on the deploy: it holds, as with the default list |
| `triage-before-the-merge-authorisation` | feature, answered, the human review a triage that merges through the merge authorisation or redeploys without merging, nobody able to judge either | It holds; neither gate may be removed: the merge authorisation is the last gate before the merge, and without it the triage refuses nothing, so the deploy is left without a gate |
| `bypass-and-two-gates-nobody-can-judge` | feature, answered, a trivial change merged around both approvals, nobody able to judge either | Refused at the merge and the deploy; the human review may be removed, the merge authorisation may not go with it: the gate kept is the one nearest the merge, whatever the bypass |

## The answers to `flow fit`

`flow fit` is run before any definition exists: a team records what it builds, how many tickets a week go through the path, whether a person starts each phase, and eight symptoms, each a number or "not measured" (the contract's section 11). `expected.json` gives the exit code, the verdict (`by_hand`, `ticket_state_and_ci`, `tool`, `symptom`, or null when the answers are refused), the tool named, the symptoms that fired, the numbers listed without deciding (`not_deciding`), the symptoms not measured, the keys a refusal names, and the ids of the cost entries the verdict prints (`cost`, empty for a refusal; the contract's section 12.3), each list in order. `cli/tests/test_flow_fit.py` runs each file through the command line. These seven were written by the session that wrote the code: they hold a regression in place, they are not an independent measure.

```bash
python3 -m unittest discover -s cli/tests -p test_flow_fit.py -v
```

| Folder | What the team says | What it shows |
|---|---|---|
| `by-hand` | A ticket workflow, no ticket in a week, a person starts each phase | "By hand with the ai-sdlc skills may be enough: no ticket goes through this path yet" |
| `ticket-state-and-ci` | Fifteen tickets a week, chained by hand; one run in ten paid twice | "Ticket state and CI are enough": a value on the threshold is not above it. The one symptom not measured is listed, and the four steps with their own retry rule are listed without deciding |
| `own-agent-app` | Its own agent application, with seven double runs written down | The tool the report's table names for that case; the symptoms describe a ticket workflow and decide nothing here |
| `symptom-fired` | Thirty tickets a week, two double runs, three looping agents, eight runs in a hundred paid twice | Two symptoms named in table order, one an engine removes and one it does not; the share under its written threshold is not named |
| `symptom-no-engine` | Twenty tickets a week, two looping agents, nothing else above zero | The symptom fires and no engine is named, since an engine retries a looping agent faithfully: the cost lists no engine entry |
| `nothing-measured` | Twenty-five tickets a week, every symptom "not measured" | The verdict is still "ticket state and CI", and all eight symptoms are listed as not measured, none counted as fine |
| `refused` | One key absent, one symptom written "none", one symptom key misspelt | No verdict, exit 1: each key is named, the misspelt one twice (the right key is missing, the wrong one is unknown) |

## Changing an answer

An `expected.json`, a `traps.md` or an expected state is changed because the contract changed or the answer was wrong against it, never to make the code pass. An answer that turns out not to be decided by the contract is removed and reported, not guessed.
