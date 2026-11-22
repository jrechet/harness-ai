# harness-flow fixtures

Recorded cases with their answers, for the first slice of `harness flow`: a team's workflow from a ticket to production, written as a small table of states. They measure three things. Does the transition function give, after each event, the state the rules ask for? Does a definition hold together? Does each step of a flow land in the right place, and is the one step that needs an engine named?

The answers were written by hand, by reasoning from the contract ([flow-spec.md](../../docs/workflow-harness/flow-spec.md)) and before any code existed: no answer here was produced by running the code it grades. Where the contract did not decide, no answer was written.

```
fixtures/flow/
├── definitions/         # flows written by hand: the two templates, and one for what they do not hold
├── sequences/<name>.json   # one ticket's run: the events received, in order, and the expected state after each
└── place/<name>/
    ├── definition.json  # only when the flow is not a template
    ├── traps.md         # only in trapped/: what was planted and why
    └── expected.json    # where each step must land, and the verdict
```

## How it is graded

No agent is run and nothing is launched by hand: the family is graded by a unit test, at every commit.

```bash
python3 -m unittest discover -s cli/tests -p test_flow_fixtures.py -v
```

That test calls the code directly (`next_state`, `check`, `new` and `place`, the Python interface of the contract's section 5) and fails with the path of a fixture it cannot read. It never skips: without the code, it fails on its first line and says which module is missing.

A second test, `cli/tests/test_flow_fixtures_format.py`, needs no code. It checks the family itself: every file is well formed, every definition follows the format, every expected answer is one its definition allows (a move follows a declared transition, a refusal changes nothing, what is spent grows by the event's own costs), and this page names every fixture.

## The definitions

| File | What it is |
|---|---|
| `feature` | The feature template, written from the contract's table: 18 steps from "ready for an agent" to the closed ticket, stopping by default when the pull request is marked ready. `flow new feature` must write the same states, events, caps and writes; only the sentences are the code author's |
| `bug` | The bug template: 14 steps from triage to the closure check days later, stopping by default at the root cause |
| `every-case` | A small flow for what the templates do not hold: a step done by a person, an agent step started again when its job crashes (three times at most), a gate whose deadline hands over to another judge, and an end with no reason given |

A sequence or a flow to place names its definition as `template:feature` or `template:bug` (the test then asks the code for its template), or by a path from this folder. The test also compares each template with its file here.

## The sequences

One file is one ticket. `start` is `"new"` or the run document the ticket comes back with. Each entry holds the event received and, under `expect`, the answer: `outcome` and `reason`, the `state` of the run returned, and when it matters the number of entries into some states (`visits`; a state never entered is written 0), what the run has spent, what remains of the budget and whether it is passed. `override` replaces the stop point or the budget of the definition for that file. `note`, where present, says in plain words which rule of the contract decides; no test reads it.

Costs are in quarters of a dollar and whole minutes, so every sum is exact. The feature template allows 20 dollars and 240 minutes for one ticket, the bug template 10 and 120.

| File | Flow | What it shows |
|---|---|---|
| `feature-to-ready-pr` | feature | The whole path, with a large plan approved by a person, until the pull request is marked ready: the run ends there on purpose (`done`, `stop_point`), and one more event is refused because the run has ended |
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

The first seventeen are the contract's list (fifteen and two twins). The last two were added for the cases only `every-case` holds.

Beyond the recorded sequences, the same test checks by program, on the two templates and every file of `definitions/`: that every state and every event type, with and without costs and round, get one well-formed answer; and, on 200 generated sequences of 300 events, that no step is entered more often than its cap, that what is spent never falls, that an ended run never moves and that an event delivered twice changes nothing.

## The flows to place

`expected.json` gives every step its place (one of the nine of the contract's section 6), the steps that need an engine, the gates nobody can judge, the steps left open, the verdict and whether the placement passes.

| Folder | Flow | What it shows |
|---|---|---|
| `feature` | The feature template | Every step has a place; the verdict is "no step needs an engine"; the placement passes |
| `bug` | The bug template | The same |
| `trapped` | `library_upgrade`, its own definition: twelve steps to move a shared library to a new major version | Exactly one step needs an engine (a rewrite of stored records that lasts days and must go on from the middle) and exactly one gate cannot be judged by anyone (a sign-off on a log of forty thousand lines). Beside them, three steps that only look like they need an engine: a wait of ten days, an agent step of four hours that may start again, a gate with a deadline of two weeks. The verdict names the one step, and the placement fails because of the gate. [traps.md](place/trapped/traps.md) says what was planted and why |

## Changing an answer

An `expected.json`, a `traps.md` or an expected state is changed because the contract changed or the answer was wrong against it, never to make the code pass. An answer that turns out not to be decided by the contract is removed and reported, not guessed.
