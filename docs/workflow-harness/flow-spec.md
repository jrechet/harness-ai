# harness-flow, first slice: the contract

Date: 2026-11-22. Issue #143. This page fixes what the first slice of [proposal.md](proposal.md) (sections 3 and 8.1) builds, exactly enough for four people to build it apart: the core module, the placement, the fixtures, the guide. Where this page and the proposal differ, this page wins for this slice; the differences are listed in "Choices made here".

Nothing here calls an agent, a network, a clock or a key. Python 3.10, standard library only.

| Part | Files | Reads this page's sections |
|---|---|---|
| Core | `cli/harnesslib/flow.py`, `cli/harnesslib/flow_templates/feature.json` and `bug.json`, the `flow` line of `cli/harness.py`, `cli/tests/test_flow.py` | 1 to 5, 7 |
| Placement | `cli/harnesslib/flow_placement.json`, `cli/harnesslib/flow_place.py`, `cli/tests/test_flow_place.py` | 1, 4, 5, 6 |
| Fixtures | `fixtures/flow/`, `cli/tests/test_flow_fixtures.py`, the `flow/` row of `fixtures/README.md` | 1, 3, 5, 6, 8 |
| Guide | `docs/workflow-harness/decide.md` | 1, 6, and report.md section 7 |

Only the core touches `cli/harness.py`. `cli/harnesslib/placement.json` and `place.py` do not change.

Words: a **flow** is one team workflow for one kind of ticket; its **definition** is the JSON file; a **run** is one ticket going through it; a **step** is what happens in one state. Names of flows, states, events, reasons and stop points all match `[a-z][a-z0-9_]*`.

## 1. The definition format

One JSON object, by default in `.harness/flow/<name>.json`. A state holds exactly one step, so the state object is the step. Unknown keys are ignored.

Top level:

| Key | Type | Required | Meaning |
|---|---|---|---|
| `format` | integer, `1` | yes | Version of this format |
| `name` | name | yes | The flow's name |
| `kind` | string | no | `feature`, `bug`, or the team's own word |
| `start` | name of a state | yes | Where a run begins |
| `stop_at` | name of a stop point | yes | Where the flow ends on purpose |
| `budget` | `{"dollars": n, "minutes": n}`, both numbers above 0 | yes | The most one run may spend. Minutes are minutes of running steps, reported by events; waiting costs nothing |
| `states` | object, state name → state, at least one | yes | The steps. `done` and `stopped` are the two end states: they are reserved and never declared |

A state:

| Key | Type | Required | Meaning |
|---|---|---|---|
| `type` | `code`, `agent`, `human`, `gate` or `wait` | yes | Who performs the step: a program with no model call; a coding agent; a person who does work; a person who decides; nobody, the run waits for something outside |
| `does` | non-empty string | yes | One plain sentence, shown to people |
| `on` | object, event type → transition, at least one | yes | The transitions out of this state: (state, event) → state |
| `cap` | integer above 0 | no | The most times one run may enter this state, counted over the whole run and never reset |
| `writes` | list of `{"what": string, "key": string}` | no | Each write to the outside (ticket, branch, PR). `key` must contain the text `{ticket}` |
| `checks_premise` | boolean, default false | no | The step first checks that the facts it starts from still hold |
| `judge` | non-empty string | gate | Who decides, named by role or person |
| `deadline_hours` | number above 0 | gate | After that long with no decision, the gate has failed |
| `can_judge` | `yes` or `no` | no (gate) | Can the judge really judge what they approve? Read by `flow place` |
| `survives`, `units`, `repositories` | see section 6 | no (code, agent) | Read by `flow place` |
| `weak_model` | `yes` or `no` | no (agent) | Read by `flow place` |

A transition is `{"to": T}` where `T` is a declared state, `done` or `stopped`, plus two optional keys: `reason` (a name; required when `to` is `stopped`, optional when `to` is `done`) and `reaches` (the name of the stop point this transition reaches). The event types `human_stop` and `deadline_passed` are built in (section 3); `human_stop` is never declared in an `on`.

A complete small example, used by the worked examples of section 3. It passes `flow check`.

```json
{"format": 1, "name": "small", "kind": "feature",
 "start": "ready", "stop_at": "draft_pr", "budget": {"dollars": 5, "minutes": 60},
 "states": {
  "ready": {"type": "code", "does": "Checks the ticket is eligible and claims it",
            "survives": "restart", "units": "one", "repositories": "one",
            "writes": [{"what": "the run record on the ticket", "key": "run-{ticket}"}],
            "on": {"claimed": {"to": "coding"}, "not_eligible": {"to": "stopped", "reason": "not_eligible"}}},
  "coding": {"type": "agent", "does": "Implements the ticket and its tests",
             "survives": "restart", "units": "one", "repositories": "one", "weak_model": "no",
             "on": {"code_written": {"to": "checks"}}},
  "checks": {"type": "code", "does": "Runs format, lint, build and the selected tests", "cap": 3,
             "survives": "restart", "units": "one", "repositories": "one",
             "on": {"checks_passed": {"to": "approval"}, "checks_failed": {"to": "coding"}}},
  "approval": {"type": "gate", "does": "A maintainer reads the diff and says whether a PR may be opened",
               "judge": "a maintainer of the repository", "deadline_hours": 48, "can_judge": "yes",
               "on": {"approved": {"to": "open_pr"}, "refused": {"to": "stopped", "reason": "refused"}}},
  "open_pr": {"type": "code", "does": "Pushes the branch and opens a draft PR linked to the ticket",
              "survives": "restart", "units": "one", "repositories": "one",
              "writes": [{"what": "the branch", "key": "flow/{ticket}"}, {"what": "the draft PR", "key": "pr-{ticket}"}],
              "on": {"pr_opened": {"to": "ci_wait", "reaches": "draft_pr"}}},
  "ci_wait": {"type": "wait", "does": "Waits for CI on the pushed commit",
              "on": {"ci_finished": {"to": "ci_check"}}},
  "ci_check": {"type": "code", "does": "Checks the CI result is for the current commit and reads it",
               "checks_premise": true, "survives": "restart", "units": "one", "repositories": "one",
               "on": {"ci_green": {"to": "done", "reason": "ci_green"}, "ci_red": {"to": "stopped", "reason": "ci_red"}}}}}
```

### The two templates

`flow new` writes them; the fixtures replay events on them, so their states and events are fixed here. Read a cell `event → target [stop point] (reason)`. W: the state has at least one `writes` entry. In both, every `code` and `agent` state has `survives: restart`, `units: one`, `repositories: one`; every `agent` state has `weak_model: no`; every `gate` has `can_judge: yes`, a `judge` and a `deadline_hours`. The `does` sentences are the core author's, from report.md section 6.

**`feature`**: name `feature`, start `ready`, `stop_at` `ready_pr`, budget 20 dollars and 240 minutes. States in this order:

| State | Type | Cap | Transitions |
|---|---|---|---|
| `ready` | code, W | | `claimed` → `planning` · `not_eligible` → `stopped` (not_eligible) |
| `planning` | agent, W | 3 | `plan_written` → `coding` [plan] · `plan_needs_approval` → `plan_review` [plan] |
| `plan_review` | gate | | `plan_approved` → `coding` · `plan_rejected` → `planning` |
| `coding` | agent | | `code_written` → `checks` |
| `checks` | code | 6 | `checks_passed` → `draft_pr` · `checks_failed` → `coding` |
| `draft_pr` | code, W | | `pr_opened` → `ci_wait` [draft_pr] |
| `ci_wait` | wait | 8 | `ci_finished` → `ci_check` |
| `ci_check` | code, checks premise | | `ci_green` → `review_checks` · `ci_red` → `ci_fix` · `ci_stale` → `ci_wait` |
| `ci_fix` | agent | 2 | `fix_pushed` → `ci_wait` |
| `review_checks` | agent | | `review_done` → `mark_ready` |
| `mark_ready` | code, W | | `marked_ready` → `human_review` [ready_pr] |
| `human_review` | gate | | `approved` → `merge_auth` · `changes_requested` → `rework` |
| `rework` | code | 2 | `comments_collected` → `coding` |
| `merge_auth` | gate | | `merge_authorised` → `merging` |
| `merging` | code, W | | `merged` → `delivery` [merged] · `merge_failed` → `stopped` (merge_failed) |
| `delivery` | wait | | `deployed` → `closing` [deployed] · `deploy_failed` → `stopped` (deploy_failed) |
| `closing` | code, W, checks premise | | `closed` → `done` (delivered) |

**`bug`**: name `bug`, start `triage`, `stop_at` `root_cause`, budget 10 dollars and 120 minutes.

| State | Type | Cap | Transitions |
|---|---|---|---|
| `triage` | code, W | | `ticket_ready` → `premise` · `duplicate_found` → `done` (duplicate) · `not_eligible` → `stopped` (not_eligible) |
| `premise` | agent, checks premise | | `still_fails` → `root_cause` · `already_fixed` → `done` (already_fixed) · `cannot_reproduce` → `stopped` (cannot_reproduce) |
| `root_cause` | agent | 5 | `cause_written` → `notify` |
| `notify` | code, W | | `confident` → `repro` [root_cause] · `low_confidence` → `stopped` (low_confidence) |
| `repro` | agent, W | | `repro_written` → `fix` [plan] |
| `fix` | agent | | `fix_written` → `verify` |
| `verify` | code | | `verified` → `draft_pr` · `verify_failed` → `root_cause` |
| `draft_pr` | code, W | | `pr_opened` → `ci_wait` [draft_pr] |
| `ci_wait` | wait | 4 | `ci_finished` → `ci_check` |
| `ci_check` | code, checks premise | | `ci_green` → `human_review` [ready_pr] · `ci_red` → `ci_fix` · `ci_stale` → `ci_wait` |
| `ci_fix` | agent | 2 | `fix_pushed` → `ci_wait` |
| `human_review` | gate | | `merged_by_human` → `closure_wait` [merged] · `closed_with_reason` → `done` (rejected) |
| `closure_wait` | wait | | `closure_due` → `closure_check` |
| `closure_check` | code, W, checks premise | | `signal_stopped` → `done` (fixed) · `signal_continues` → `stopped` (not_fixed) |

## 2. `flow check`: the refusals

`check(definition)` returns a list of problems, each `{"code", "message", "where"}`; an empty list means the definition holds. `where` is a path into the file: `""` for the whole file, `budget`, `stop_at`, `states.checks`, `states.open_pr.writes[1]`. `message` is the plain sentence printed; a test compares `code` and `where`, never `message`.

`malformed` is checked first; if any `malformed` problem exists, only those are returned, because the other rules need a readable structure. Otherwise the problems come in the order of this table, then in file order.

| Code | Refuses | Sentence printed | `where` |
|---|---|---|---|
| `malformed` | The file is not a flow: not an object; `format` is not 1; `name`, `start` or `states` missing or of the wrong type; a name that does not match the pattern; a state called `done` or `stopped`; `start` not a declared state; a state that is not an object; `does` missing; `on` missing or empty; a transition that is not `{"to": …}`, goes to an unknown state, goes to `stopped` without a `reason`, or declares `human_stop`; a `cap` that is not an integer above 0; a `writes` that is not a list of objects | "The file cannot be read as a flow: ‹what is wrong›." | the offending key |
| `unknown_step_type` | A state whose `type` is missing or not one of the five | "Step ‹state› has the type ‹type›, which is not one of code, agent, human, gate, wait." | `states.‹state›` |
| `loop_without_cap` | A loop no cap bounds. Take the graph of transitions between declared states, remove every state that has a `cap`: one problem per group of remaining states that can reach each other in a circle (a state that loops on itself is such a group) | "The steps ‹a, b› can repeat without end: none of them has a cap." | `states.‹first state of the group in file order›` |
| `write_without_key` | A `writes` entry whose `key` is missing or does not contain `{ticket}`, or whose `what` is empty | "Step ‹state› writes ‹what› without a key derived from the ticket: an event delivered twice would write twice." | `states.‹state›.writes[‹i›]` |
| `no_stop_point` | `stop_at` missing, or no transition has `reaches` equal to it | "The flow does not say where it stops on purpose." or "The flow stops at ‹stop_at›, which no step reaches." | `stop_at` |
| `no_budget` | `budget` missing, or `dollars` or `minutes` missing or not a number above 0 | "The flow has no budget in dollars and minutes for one ticket." | `budget` |
| `wait_without_premise_check` | A `wait` state with a transition to a declared state that does not have `checks_premise: true`. One problem per such transition. `done` and `stopped` need no check | "After the wait ‹state›, the step ‹target› does not check that the facts still hold." | `states.‹state›.on.‹event›` |
| `gate_without_judge` | A `gate` with no `judge`, or an empty one | "The gate ‹state› names nobody who decides." | `states.‹state›` |
| `gate_without_deadline` | A `gate` with no `deadline_hours`, or one that is not a number above 0 | "The gate ‹state› has no deadline: a silent approver would hold the ticket for ever." | `states.‹state›` |

A boolean is never a number. Exit codes: 0 no problem, 1 at least one problem, 2 the file is missing or is not JSON.

## 3. `flow next`: the transition function

`next_state(definition, run, event)` is pure: no clock, no network, no file, no randomness; it never changes its arguments. It assumes `check(definition) == []`; on another definition its result is unspecified, but it returns.

**The run document.** All five keys always present.

```json
{"state": "checks", "visits": {"ready": 1, "coding": 1, "checks": 1},
 "spent": {"dollars": 1.25, "minutes": 14}, "seen": ["evt-1", "evt-2"], "reason": null}
```

`state`: a declared state, `done` or `stopped`. `visits`: how many times the run entered each state (states never entered may be absent). `spent`: the budget used so far. `seen`: the identifiers of the events already taken into account, in order. `reason`: `null` while the run is alive, a name once it is `done` or `stopped`. `new_run(definition)` gives the run before any event: `state` is `start`, `visits` is `{start: 1}`, `spent` zero, `seen` empty, `reason` null.

**The event document.**

```json
{"id": "evt-3", "type": "checks_failed", "payload": {"dollars": 0.5, "minutes": 6}}
```

`id` and `type`: non-empty strings. `payload`: optional object; its `dollars` and `minutes`, when present, are numbers at or above 0 and are what the step cost. Other payload keys are carried, never read: the event's **type** says what happened (`confident` or `low_confidence`), the function never decides from a payload value.

**The output document.**

```json
{"outcome": "moved", "reason": null,
 "transition": {"from": "checks", "event": "checks_failed", "to": "coding"},
 "message": "checks → coding, on checks_failed.", "run": {}}
```

`run` is shown empty here; it is always a full run document. `outcome` is one of `moved` (to a live state), `done`, `stopped`, `duplicate`, `refused`. `reason` is null for `moved`, a name otherwise. `transition` is null for `duplicate` and `refused`; otherwise `to` is the new state and `from` the state given (null if it was not a string). `message` is one plain sentence, not compared by tests. `run` is a new object; for `duplicate` and `refused` it equals the run given.

**The rules, in this order. The first that applies decides.**

| # | When | Outcome, reason | New run |
|---|---|---|---|
| 1 | The event is not an object, `id` or `type` is not a non-empty string, `payload` is not an object, or a cost is not a number at or above 0 | `refused`, `malformed_event` | unchanged |
| 2 | The run is inconsistent: not an object; a key missing; `state` not a declared state, `done` or `stopped`; `visits` not an object of integers at or above 0 keyed by declared states; a live state whose count is under 1; a count above its state's `cap`; `spent` not two numbers at or above 0; `seen` not a list of strings; `reason` null on an ended run or not null on a live one | `stopped`, `inconsistent` | `state` `stopped`, `reason` `inconsistent`; `visits`, `spent`, `seen` kept when each is well formed, otherwise `{}`, zeros, `[]`; the event id added to `seen`; no cost added |
| 3 | `event.id` is in `seen` | `duplicate`, `already_seen` | unchanged |
| 4 | `state` is `done` or `stopped` | `refused`, `run_ended` | unchanged |
| 5 | `event.type` is `human_stop` | `stopped`, `human_stop` | accepted (below), whatever the state, the caps and the budget |
| 6 | The type is not a key of the current state's `on` (and is not `deadline_passed` on a gate). If no state of the definition declares it and it is not built in: `unknown_event`; otherwise `event_not_expected` | `refused`, one of the two | unchanged |
| 7 | After adding the event's costs, `spent.dollars` is above `budget.dollars` or `spent.minutes` above `budget.minutes` (equal is within budget) | `stopped`, `budget_exceeded` | accepted |
| 8 | The transition goes to `stopped`; or the type is `deadline_passed` on a gate that does not declare it | `stopped`, the transition's `reason`; `gate_deadline` | accepted |
| 9 | The transition goes to `done` | `done`, the transition's `reason`, or `finished` | accepted |
| 10 | The transition's `reaches` equals `stop_at` | `done`, `stop_point` | accepted; the target is not entered |
| 11 | The target has a `cap` and its count is already at the cap | `stopped`, `cap_reached` | accepted; the target is not entered |
| 12 | Otherwise | `moved`, null | accepted; `state` is the target and its count rises by 1 |

"Accepted" means: the event id is appended to `seen`, its costs are added to `spent` (each sum rounded to 4 decimals), and `state` and `reason` are set by the row. A refused event is not added to `seen`: delivered again, it is refused again.

What follows from the rules, and what the tests check: for every state and every event there is one outcome; a count never passes its cap; an event delivered twice changes nothing the second time; an event that does not belong to the current state is refused, never guessed; once ended, a run never moves; a human stop on a live, consistent run always gives `stopped` with `human_stop`.

**Three worked examples**, on the `small` definition of section 1.

A legal transition with a cost. Run and event as shown above. Output:

```json
{"outcome": "moved", "reason": null,
 "transition": {"from": "checks", "event": "checks_failed", "to": "coding"},
 "message": "checks → coding, on checks_failed.",
 "run": {"state": "coding", "visits": {"ready": 1, "coding": 2, "checks": 1},
         "spent": {"dollars": 1.75, "minutes": 20}, "seen": ["evt-1", "evt-2", "evt-3"], "reason": null}}
```

The same event delivered again, on the run just returned. Rule 3:

```json
{"outcome": "duplicate", "reason": "already_seen", "transition": null,
 "message": "Event evt-3 was already taken into account: nothing changes.",
 "run": {"state": "coding", "visits": {"ready": 1, "coding": 2, "checks": 1},
         "spent": {"dollars": 1.75, "minutes": 20}, "seen": ["evt-1", "evt-2", "evt-3"], "reason": null}}
```

A cap reached. Run `{"state": "coding", "visits": {"ready": 1, "coding": 3, "checks": 3}, "spent": {"dollars": 3, "minutes": 40}, "seen": ["evt-1", "evt-2", "evt-3", "evt-4", "evt-5", "evt-6"], "reason": null}`, event `{"id": "evt-7", "type": "code_written", "payload": {"dollars": 0.5, "minutes": 5}}`. The checks already ran three times. Rule 11:

```json
{"outcome": "stopped", "reason": "cap_reached",
 "transition": {"from": "coding", "event": "code_written", "to": "stopped"},
 "message": "Stopped: the step checks already ran 3 times, its cap.",
 "run": {"state": "stopped", "visits": {"ready": 1, "coding": 3, "checks": 3},
         "spent": {"dollars": 3.5, "minutes": 45},
         "seen": ["evt-1", "evt-2", "evt-3", "evt-4", "evt-5", "evt-6", "evt-7"], "reason": "cap_reached"}}
```

## 4. The command lines

All under `python3 cli/harness.py flow`. Every command takes `--format md|json`, default `md`: plain words for a person, or the JSON document named below. Exit codes everywhere: **0** fine, **1** refused or failing, **2** wrong usage or an input that is missing or is not JSON (message on stderr, starting with `flow:`). Only `flow new` writes a file.

| Command | Prints for a person | `--format json` | Exit 1 when |
|---|---|---|---|
| `flow new <feature\|bug> [--out FILE] [--force]` | "Written: ‹path›", then the steps in order, one line each: state, who performs it, its `does`. Default path `.harness/flow/<kind>.json` under the current directory; folders are created | `{"file", "definition"}` | the file exists and `--force` is absent (nothing written) |
| `flow check <file>` | "This flow holds: ‹n› steps, it stops at ‹stop_at›, one ticket may cost up to ‹dollars› dollars and ‹minutes› minutes." or one line per problem: "- ‹sentence› (‹where›)" | `{"file", "passed", "problems"}` | a problem is found |
| `flow next <file> --event FILE [--run FILE]` | The `message`, then "State: ‹state›. Spent: ‹dollars› dollars, ‹minutes› minutes." Without `--run`, the run is `new_run` | the output document of section 3 | the outcome is `refused` or `stopped`. A definition that does not pass `flow check` gives its problems and exit 2 |
| `flow place <file>` | Section 6 | the `place` document | a step cannot be placed, or a gate cannot be judged by anyone |
| `flow status <file> [--map]` | Section 7 | the `status` document | never: a level is a fact, not a failure |

An event or run file that is JSON but ill formed is not a usage error: `flow next` answers it by rules 1 and 2.

## 5. The Python interface

What the tests call. Nothing below prints, except the two `main`.

`cli/harnesslib/flow.py`:

| Function | Returns |
|---|---|
| `load_definition(path) -> dict` | The parsed file. Raises `ValueError` (message starts with the path) if it is missing, not JSON, or not an object. Validates nothing else |
| `check(definition) -> list[dict]` | Problems `{"code": str, "message": str, "where": str}`, section 2. Never raises, whatever it is given |
| `new(kind) -> dict` | A fresh copy of the template `feature` or `bug`; `check(new(kind)) == []`. Raises `ValueError` for another kind |
| `new_run(definition) -> dict` | The run before any event, section 3 |
| `next_state(definition, run, event) -> dict` | `{"outcome", "reason", "transition", "message", "run"}`, section 3. Never raises on any `run` or `event`, whatever their type |
| `status(definition, placement=None) -> dict` | Section 7. `placement` is a `place` document; when `None`, `flow_place.place(definition)` is imported and called at that moment |
| `render_map(state) -> str` | The map of section 7, from a `status` document |
| `build_parser(parser=None)`, `main(argv=None, args=None) -> int` | As the other modules of `cli/harnesslib`: `harness.py` adds `flow.build_parser(sub.add_parser("flow", …))` and calls `flow.main(args=args)`. The `place` subcommand is declared here (`file`, `--format`) and handed to `flow_place.main([file, "--format", fmt])`, imported at that moment |

Constants: `STEP_TYPES = ("code", "agent", "human", "gate", "wait")`, `ENDED = ("done", "stopped")`, `TEMPLATES = ("feature", "bug")`.

`cli/harnesslib/flow_place.py`:

| Function | Returns |
|---|---|
| `load_grid(path=GRID_FILE) -> dict` | `flow_placement.json` |
| `place(definition) -> dict` | The `place` document of section 6. Raises `ValueError` if `states` is not an object of objects; otherwise places what it finds without running `check` |
| `main(argv=None) -> int` | `flow place`: arguments `file` and `--format md\|json` |

## 6. `flow place`: the grid, extended

`cli/harnesslib/flow_placement.json` has the format of `placement.json` (`root`, `questions`, `destinations`), so that `place.validate` and `place.walk` of the existing module read it unchanged, with two additions: each question carries `from`, which says which key of a step answers it, and each destination carries `says`, the short sentence printed.

An excerpt:

```json
{"root": "who",
 "questions": {"judge": {"text": "Can the person who approves really judge what they approve?",
                         "from": {"key": "can_judge", "map": {"yes": "yes", "no": "no"}},
                         "options": {"yes": {"label": "Yes: they are shown something they can read and refuse", "place": "human_gate"},
                                     "no": {"label": "No: nobody could tell a good one from a bad one", "place": "no_gate"}}}},
 "destinations": {"no_gate": {"name": "No gate", "says": "no gate here", "layer": "-", "where": "…", "why": "…"}}}
```

The answers of a step are computed, never asked: for each question, take the step's value at `from.key`; if it is a key of `from.map`, the answer is the mapped option; otherwise the question has no answer. Then walk the tree from the root.

| Question | `from.key` | Option (step value) → next question or **destination** |
|---|---|---|
| `who`: who performs this step? | `type` | `code` → `survive` · `agent` → `survive` · `human` → **ticket_state** · `wait` → **ticket_state** · `gate` → `judge` |
| `judge`: can the person who approves really judge it? | `can_judge` | `yes` → **human_gate** · `no` → **no_gate** |
| `survive`: how long does it live, and what must survive? | `survives` | `restart` (minutes to a few hours; starting again from its beginning is acceptable) → `spread` · `midway` (days inside one computation, or it must not run twice, or every run must be replayable step by step) → **durable_engine** |
| `spread`: does the work split into many independent units? | `units` | `one` → `repos` · `many` → **campaign** |
| `repos`: how many repositories need this step? | `repositories` | `one` → `determined` · `several` → **reusable_workflow** |
| `determined`: is the right output determined by the inputs? | `type` | `yes` (step value `code`) → **code** · `no` (step value `agent`) → `weakness` |
| `weakness`: is this step here because today's model is weak? | `weak_model` | `yes` → **dated_skill** · `no` → **skill** |

| Destination | Layer | `says` | In short |
|---|---|---|---|
| `code` | L3 | "this is code" | A tested command, started by a short CI job |
| `skill` | L2 | "a skill is enough" | The agent, inside one step, guided by a skill |
| `dated_skill` | L2 | "a skill is enough, with its date" | The same, with the model and the date written beside it; tested again at each model release and deleted when it changes nothing |
| `ticket_state` | L4 | "the ticket holds this" | A state on the ticket or the PR; nothing runs while it lasts; the next event starts a short job |
| `human_gate` | L4 | "this is a human gate" | A ticket or PR state only a human account may set |
| `no_gate` | - | "no gate here" | A refusal: the person could not judge what they approve. Remove the gate or give the judge something to judge |
| `reusable_workflow` | L4 | "this is a shared CI workflow" | A versioned plugin and a reusable CI workflow, with an owner |
| `campaign` | L4 | "this is a fan-out by script" | A script fans out, one writer per unit, never a swarm |
| `durable_engine` | L4 | "this would need an engine" | The exit: a workflow engine holds the step |

`where` and `why` of each destination, the labels and the `text` wording are the placement author's, from report.md section 7. There is no destination for a graph framework.

**The `place` document.**

```json
{"flow": "small",
 "steps": [{"state": "coding", "type": "agent", "does": "Implements the ticket and its tests",
            "status": "placed", "destination": "skill", "name": "A skill", "says": "a skill is enough",
            "path": [{"question": "who", "answer": "agent"}, {"question": "survive", "answer": "restart"},
                     {"question": "spread", "answer": "one"}, {"question": "repos", "answer": "one"},
                     {"question": "determined", "answer": "no"}, {"question": "weakness", "answer": "no"}],
            "decided_by": {"question": "weakness", "text": "Is this step here because today's model is weak?", "answer": "no"},
            "reason": "‹the destination's why›", "missing": null}],
 "engine": [], "refused_gates": [], "open": [],
 "verdict": {"code": "no_engine", "sentence": "No step needs an engine."},
 "passed": true}
```

`steps` follows the file order of `states`, one entry per state. A step with a missing answer has `status` `open`, `destination`, `name`, `says`, `decided_by` and `reason` null, `path` as far as it went, and `missing` `{"question", "text", "key"}`: the question that has no answer and the step key that would answer it. An unknown `type` leaves the step open at `who`. `decided_by` is the last entry of `path`, with the question's text. `engine`, `refused_gates` and `open` list the states sent to `durable_engine`, sent to `no_gate`, and left open, in file order. `verdict.code` is `open` if a step is open, otherwise `engine` if `engine` is not empty, otherwise `no_engine`. `passed` is true when `open` and `refused_gates` are both empty: needing an engine is an answer, not a failure.

**For a person**, one line per step, then the verdict, then the refused gates:

```
- coding (agent): a skill is enough. Decided by "Is this step here because today's model is weak?": no.
- approval (a person decides): this is a human gate. Decided by "Can the person who approves really judge what they approve?": yes.

Verdict: no step needs an engine.
```

The other verdict sentences: "One step would need an engine: ‹state›, ‹does›. ‹reason›" (or "‹n› steps would need an engine: …"); "‹n› step(s) cannot be placed yet: ‹state› has no answer to "‹question text›" (key ‹key›)". For each refused gate, one more line: "A gate nobody can judge: ‹state›. Remove it, or give ‹judge› something they can read and refuse."

## 7. `flow status --map`: level Mapped, on paper

The ladder of proposal section 5. This slice measures level 1 only, from the file alone. `status(definition, placement)` returns:

```json
{"flow": "small", "steps": 7, "stop_at": "draft_pr", "budget": {"dollars": 5, "minutes": 60},
 "level": {"reached": 1, "name": "Mapped", "next": 2},
 "checks": [
  {"id": "definition_holds", "passed": true, "origin": "flow check", "plain": "the flow is written down and holds together", "detail": []},
  {"id": "steps_placed", "passed": true, "origin": "flow place", "plain": "every step has a place", "detail": []},
  {"id": "stop_and_budget", "passed": true, "origin": "the definition file", "plain": "a stop point and a budget are set", "detail": []}],
 "next_step": "Nothing more on paper. The next level needs the flow to run on real tickets, which this version does not do yet."}
```

- `definition_holds` passes when `check(definition) == []`; `detail` holds the problems' sentences.
- `steps_placed` passes when the placement's `passed` is true (no open step, no gate nobody can judge); `detail` holds one sentence per open step or refused gate. If the definition is `malformed`, it fails with the detail "the file cannot be read as a flow" and `place` is not called.
- `stop_and_budget` passes when `check` returns neither `no_stop_point` nor `no_budget`.

`reached` is 1 when the three pass, otherwise 0 (name `None`, `next` 1). `next_step` at level 0 is the first sentence of `detail` of the first failing check, introduced by "Fix this first: ". `steps`, `stop_at` and `budget` are null when unreadable.

`flow status <file> --map` prints `render_map(state)`, in the style of `harness status --map`: the ladder with "you are here", then the flow in one line, then what the next level needs, then the next step. No check id is printed. Level 0 is not listed once level 1 is reached.

```
Where this flow stands, level by level:
✓ 1 Mapped      the flow is written down and every step has a place   ← you are here
· 2 Shadow      the flow runs on real tickets and only comments
· 3 Drafting    runs end with a draft PR; CI and review results come back to the run
· 4 Delivering  runs reach a reviewed PR and merge only on a human's word

This flow: small, 7 steps, stops at draft_pr, up to 5 dollars and 60 minutes for one ticket.
Levels 2 to 4 are read from real runs. Nothing measures them yet.
Next step: Nothing more on paper. The next level needs the flow to run on real tickets, which this version does not do yet.
```

At level 0 the first ladder line is "· 0 None        the phases are chained by hand   ← you are here", and the block "What level 1 still needs:" lists the `plain` of each failing check, each followed by its `detail` lines indented. Without `--map`, the command prints the level in one line, then one line per check: "✓" or "✗", its `plain`, "(read by ‹origin›)".

## 8. The fixture family `fixtures/flow/`

No agent is run: the family is graded by `cli/tests/test_flow_fixtures.py`, which calls the functions of section 5. A fixture that cannot be read makes the test fail with its path; no test skips itself. The family gets its row in the opening table of `fixtures/README.md` (grader: that test) and its own `fixtures/flow/README.md`.

```
fixtures/flow/
├── README.md
├── definitions/<name>.json     definitions written for the fixtures, when a template does not fit
├── sequences/<name>.json       one recorded sequence of events and the expected state after each
└── place/<name>/
    ├── definition.json         only when the flow is not a template
    └── expected.json           the expected destination of each step and the verdict
```

A **definition reference** is `template:feature`, `template:bug` (the test calls `flow.new`), or a path relative to `fixtures/flow/`.

**A sequence.**

```json
{"about": "One sentence: what this sequence shows.",
 "definition": "template:feature",
 "override": {"stop_at": "merged"},
 "start": "new",
 "events": [
  {"event": {"id": "e1", "type": "claimed", "payload": {"dollars": 0, "minutes": 1}},
   "expect": {"outcome": "moved", "reason": null, "state": "planning",
              "visits": {"planning": 1}, "spent": {"dollars": 0, "minutes": 1}}}]}
```

`override` (optional) replaces top-level keys of the definition before the replay (`stop_at`, `budget`); the result must still pass `check`. `start` is `"new"` or a full run document. The test feeds the first event to the starting run, then each event to the run returned before it. `expect` always gives `outcome`, `reason` and `state`; `visits` (only the states listed are compared) and `spent` are optional. Use costs in quarters (0.25, 0.5) so sums are exact.

The twelve sequences:

| File | Definition | What it must show |
|---|---|---|
| `feature-to-ready-pr` | feature | The whole path from `ready` to `done` with `stop_point` at `marked_ready`, plan approval included; then one more event is refused with `run_ended` |
| `event-twice` | feature | An event delivered twice, right away and again three events later: `duplicate` both times, the run unchanged, the cost counted once |
| `events-out-of-order` | feature | `checks_passed` before `code_written`, and `ci_green` while planning: `event_not_expected`, state unchanged; an event type nobody declares: `unknown_event`; the same refused event sent again is refused again; then the right event moves |
| `cap-reached` | feature | The local check rounds until `checks` would be entered a seventh time: `stopped`, `cap_reached`, the count still 6 |
| `budget-exceeded` | feature, small `budget` by `override` | An event that lands exactly on the budget moves; the next one passes it: `stopped`, `budget_exceeded`, although its transition was legal; minutes alone are enough |
| `human-stop` | feature | `human_stop` while the run is in `coding`, carrying a cost that passes the budget: `stopped`, `human_stop`; a later event: `run_ended` |
| `unknown-label` | feature, `start` a run whose `state` is a label no one defined | `stopped`, `inconsistent`, on the first event, whatever it is. Its twin `counts-over-cap` starts from a count above its cap and ends the same way |
| `rework-loop` | feature, `stop_at: merged` | `changes_requested` twice, each back through `coding`, `checks` and CI; the third: `stopped`, `cap_reached` at `rework` |
| `bug-already-fixed` | bug | `already_fixed` at the premise check: `done`, `already_fixed`, no root cause attempted |
| `bug-low-confidence` | bug | `low_confidence`: `stopped`, `low_confidence`. Its twin `bug-to-root-cause` takes `confident` instead: `done`, `stop_point` |
| `gate-deadline` | feature | `deadline_passed` on `plan_review`: `stopped`, `gate_deadline`; `deadline_passed` on `coding`: `event_not_expected` |
| `ci-stale-and-fix` | bug, `stop_at: merged` | A stale CI result returns to the wait; two CI fixes pass; the third: `stopped`, `cap_reached` at `ci_fix` |

The two twins, `counts-over-cap` and `bug-to-root-cause`, are files of their own beside the twelve.

The same test file also checks, by program, on the two templates and every file of `definitions/`: for every state (plus `done`, `stopped`, an unknown name) and every event type (declared, built in, unknown), `next_state` returns one well-formed output; and on generated sequences (a seeded `random.Random`, at least 200 sequences of 300 events) no count passes its cap, `spent` never falls, and an ended run never moves.

**A flow to place.** `place/<name>/expected.json`:

```json
{"about": "One sentence: what this flow shows.",
 "definition": "template:feature",
 "steps": {"ready": "code", "planning": "skill", "plan_review": "human_gate", "ci_wait": "ticket_state"},
 "engine": [], "refused_gates": [], "open": [],
 "verdict": "no_engine", "passed": true}
```

`steps` lists every state with its expected destination (null for an open step). The test compares each step's `destination`, the three lists, `verdict.code` and `passed`, and that every placed step has a `decided_by` and a non-empty `reason`. It also checks that `flow.check` passes on the three definitions.

| Folder | Definition | What it must show |
|---|---|---|
| `feature` | `template:feature` | Every step placed; `no_engine`; `passed` true |
| `bug` | `template:bug` | The same |
| `trapped` | its own `definition.json`, about ten states, a believable flow | Exactly one step with `survives: midway` → `durable_engine`, and it is the only one: beside it, decoys that look like they need an engine and do not (a wait of several days, an agent step of a few hours that may restart, a gate with a long deadline). Exactly one gate with `can_judge: no` → `no_gate`, beside a gate that can be judged. At least one step with `units: many` → `campaign`, one with `repositories: several` → `reusable_workflow`, one with `weak_model: yes` → `dated_skill`. Verdict `engine`, `passed` false. The folder's `traps.md` says in plain words which step and which gate were planted and why |

## 9. Out of this slice

- The other commands of the proposal: `flow fit`, `render`, `exits`, `drill`, `scope`, and the run side `claim`, `run-step`, `report`, `sweep`.
- The plugin `plugins/harness-flow/` and its seven skills; every doc of proposal section 6 except `decide.md`.
- Any pipeline file, forge or tracker call, agent call, key, account.
- The mapping from states to ticket labels (`flow:ready`…), the run record written on a ticket, the hash of the definition and the agent's version in the run.
- Time: nothing reads a clock. A deadline is a number in the file; a later sweep will turn it into the event `deadline_passed`.
- Reminders and escalation before a gate's deadline; checking on the forge who approved.
- Levels 2 to 4 of the ladder, the target of a flow, any state file written under `.harness/`.
- Conditions on payload values, counters that reset, sub-flows, one ticket across several repositories.
- Blind runs of any skill; a Rust implementation.

## Choices made here

- **A state is a step.** One step per state, the state object carries the step's keys. The proposal spoke of both; one object is enough.
- **Five step types**: `code`, `agent`, `human`, `gate`, `wait`. A person who decides (`gate`) is told apart from a person who works (`human`), because only the first needs a judge and a deadline.
- **The stop point sits on a transition** (`reaches`), not on a state: a state can be left by a failure, and that must not count as reaching the stop point.
- **The event type carries the outcome.** No condition on payload values: the code that emits the event chooses between `confident` and `low_confidence`. The transition table stays a table.
- **A cap counts entries into a state over the whole run**, never reset. The templates' caps are sized for it: `checks` 6 is three local rounds, twice. A loop is refused when no state on it has a cap.
- **"A gate with no judge or no deadline" is two refusals**, and structural defects share one code, `malformed`: nine codes in all.
- **A wait is followed by a premise check on every path**, not on some: each state a wait leads to carries `checks_premise`. Gates are not counted as waits here.
- **The key of a write is derived from the ticket when it contains `{ticket}`.** A program cannot prove more on paper.
- **A human stop wins over caps, budget and the transition table**, not over an inconsistent run or an ended one: both are already stopped or finished, and the reason then says why.
- **Passing the budget stops the run even when the transition was legal or final**; landing exactly on it does not.
- **A passed gate deadline stops the run** (`gate_deadline`) unless the gate declares `deadline_passed`. Remind and escalate come with the sweep.
- **The grid extension is its own small tree**, with its own destinations, in the format of `placement.json`. The proposal's six new destinations are kept; `code`, `skill` and `dated_skill` are added so every step lands somewhere. "A hook" and "a CI job" stay answers of `harness place`, for pieces inside one repository. The question on model weakness decides between a skill and a dated skill.
- **Whether a judge can judge is an answer recorded in the file** (`can_judge`), given by a person; when it is absent the step is open, and that keeps the flow at level 0.
- **Needing an engine does not fail `flow place` nor level Mapped**: it is a place. A gate nobody can judge fails both.
- **Exit codes are 0, 1, 2 everywhere**; the 3 of `harness place` for a missing answer is not reused.
- **`flow status` takes a file**; a missing file is exit 2, not level 0. Level 0 is a file that does not pass.
- **Templates are data files** in `cli/harnesslib/flow_templates/`. The feature template starts at "ready for agent"; the readiness check before it stays the `ticket` skill of `ai-sdlc`.
- **Twelve sequences plus two twins**, and the sequences added to the nine of the proposal are the full feature path, a gate deadline, and the CI loop of the bug flow.
