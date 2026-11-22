# harness-flow, first slice: the contract

Date: 2026-11-22, revised after two reviews, then when the four parts were put together ("Settled while building"), then after three reviews of the slice as built ("After the reviews", at the end). Issue #143. This page fixes what the first slice of [proposal.md](proposal.md) (sections 3 and 8.1) builds, exactly enough for four people to build it apart: the core module, the placement, the fixtures, the guide. Where this page and the proposal differ, this page wins for this slice; the differences are listed in "Choices made here".

Nothing here calls an agent, a network, a clock or a key. Python 3.10, standard library only.

| Part | Files | Reads this page's sections |
|---|---|---|
| Core | `cli/harnesslib/flow.py` (the rules), `flow_status.py` (the level), `flow_cli.py` (the command line), `cli/harnesslib/flow_templates/feature.json` and `bug.json`, the `flow` line of `cli/harness.py`, `cli/tests/test_flow.py`, `test_flow_review.py` | 1 to 7 |
| Placement | `cli/harnesslib/flow_placement.json`, `cli/harnesslib/flow_place.py`, `cli/tests/test_flow_place.py` | 1, 4, 5, 6 |
| Fixtures | `fixtures/flow/`, `cli/tests/test_flow_fixtures.py`, `test_flow_cases.py`, the `flow/` row of `fixtures/README.md` | 1, 2, 3, 5, 6, 8 |
| Guide | `docs/workflow-harness/decide.md`, `flow-format.md`, `cli/tests/test_flow_guide.py` | 1, 6, 9, and report.md section 7 |

Only the core touches `cli/harness.py`. `cli/harnesslib/placement.json` and `place.py` do not change.

Words: a **flow** is one team workflow for one kind of ticket; its **definition** is the JSON file; a **run** is one ticket going through it; a **step** is what happens in one state. Names of flows, states, events, reasons and stop points all match `[a-z][a-z0-9_]*`. On the whole page a **number** is a finite JSON number: a boolean is never a number, and neither are `NaN` and `Infinity`, which Python's `json` would read. An **integer** is a Python `int` that is not a boolean.

## 1. The definition format

One JSON object, by default in `.harness/flow/<name>.json`. A state holds exactly one step, so the state object is the step. Unknown keys are ignored.

Top level:

| Key | Type | Required | Meaning |
|---|---|---|---|
| `format` | integer, `1` | yes | Version of this format |
| `name` | name | yes | The flow's name |
| `kind` | string | no | `feature`, `bug`, or the team's own word |
| `start` | name of a state | yes | Where a run begins |
| `stop_at` | name of a stop point | yes | Where the flow ends on purpose: one of the names given by `reaches` on a transition. Not the name of a step |
| `budget` | `{"dollars": n, "minutes": n}`, both numbers above 0 | yes | What one run may spend before it is stopped. The run stops at the first event that passes it, so it can be passed by one step at most; the answer of `flow next` gives what remains, so the caller can cap the next step. Minutes are minutes of running steps, reported by events; waiting costs nothing |
| `states` | object, state name → state, at least one | yes | The steps. `done` and `stopped` are the two end states: they are reserved and never declared |

A state:

| Key | Type | Required | Meaning |
|---|---|---|---|
| `type` | `code`, `agent`, `human`, `gate` or `wait` | yes | Who performs the step: a program with no model call; a coding agent; a person who does work; a person who decides; nobody, the run waits for something outside |
| `does` | non-empty string | yes | One plain sentence, shown to people |
| `on` | object, event type → transition, at least one | yes | The transitions out of this state: (state, event) → state |
| `cap` | integer above 0 | no | The most times one run may enter this state, counted over the whole run and never reset. In a loop, put it on the step that costs (the agent), not on the cheap check after it: the run then stops before paying one more round |
| `writes` | list of `{"what": string, "key": string}` | no | Each write to the outside (ticket, branch, PR). `key` must contain the text `{ticket}`. In the whole file, one key names one thing: two entries with the same `key` have the same `what` |
| `checks_premise` | boolean, default false | no; `code` and `agent` only | The step first checks that the facts it starts from still hold. It then needs a way to say they do not: at least two declared events |
| `deadline_hours` | number above 0 | `gate`, `wait`, `human` | After that long in the state with no event, the step has failed. Optional on `code` and `agent` |
| `judge` | non-empty string | `gate` | Who decides, named by role or person |
| `shows` | non-empty string | `gate` | What the judge is shown. It must equal the `what` of a `writes` entry of another state: a judge can only read what a step wrote outside |
| `can_judge` | `yes` or `no` | no (`gate`) | Can the judge really judge what they approve? Read by `flow place` |
| `survives`, `units`, `repositories` | see section 6 | no (`code`, `agent`) | Read by `flow place` |
| `weak_model` | `yes` or `no` | no (`agent`) | Read by `flow place` |

A transition is `{"to": T}` where `T` is a declared state, `done` or `stopped`, plus two optional keys: `reason` (a name; required when `to` is `stopped`, optional when `to` is `done`) and `reaches` (the name of the stop point this transition reaches).

A transition to a declared state whose `reaches` equals `stop_at` ends the run (section 3, rule 11): its target is not entered. So the states that every path from `start` reaches only through such a transition are **behind the stop point**: described, never run as the file is written. A team writes them in advance and moves `stop_at` later. `flow check` does not refuse them; it reads the graph with those transitions cut where that changes the answer (`loop_without_cap`, `gate_shows_nothing`), and the commands tell the person which steps are not run (section 4).

Three event types are built in (section 3). `human_stop`, a person stops the run: never declared in an `on`. `deadline_passed`, the state's deadline went by: accepted in every state, may be declared in any `on`. `step_failed`, the step crashed, hit its turn cap, or gave nothing usable: accepted in every `code` and `agent` state, may be declared there only (for a capped retry, for example).

A complete small example, used by the worked examples of section 3. It passes `flow check`.

```json
{"format": 1, "name": "small", "kind": "feature",
 "start": "ready", "stop_at": "draft_pr", "budget": {"dollars": 5, "minutes": 60},
 "states": {
  "ready": {"type": "code", "does": "Checks the ticket is eligible and claims it",
            "survives": "restart", "units": "one", "repositories": "one",
            "writes": [{"what": "the run record", "key": "run-{ticket}"}],
            "on": {"claimed": {"to": "coding"}, "not_eligible": {"to": "stopped", "reason": "not_eligible"}}},
  "coding": {"type": "agent", "does": "Implements the ticket and its tests", "cap": 3,
             "survives": "restart", "units": "one", "repositories": "one", "weak_model": "no",
             "on": {"code_written": {"to": "checks"}}},
  "checks": {"type": "code", "does": "Runs format, lint, build and the selected tests",
             "survives": "restart", "units": "one", "repositories": "one",
             "on": {"checks_passed": {"to": "push"}, "checks_failed": {"to": "coding"}}},
  "push": {"type": "code", "does": "Pushes the branch, so that a person can read it",
           "survives": "restart", "units": "one", "repositories": "one",
           "writes": [{"what": "the branch", "key": "flow/{ticket}"}],
           "on": {"pushed": {"to": "approval"}}},
  "approval": {"type": "gate", "does": "A maintainer reads the branch and says whether a PR may be opened",
               "judge": "a maintainer of the repository", "shows": "the branch", "deadline_hours": 48, "can_judge": "yes",
               "on": {"approved": {"to": "open_pr"}, "refused": {"to": "stopped", "reason": "refused"}}},
  "open_pr": {"type": "code", "does": "Checks the branch is still the one approved, then opens a draft PR linked to the ticket",
              "checks_premise": true, "survives": "restart", "units": "one", "repositories": "one",
              "writes": [{"what": "the draft PR", "key": "pr-{ticket}"}],
              "on": {"pr_opened": {"to": "ci_wait", "reaches": "draft_pr"},
                     "head_moved": {"to": "stopped", "reason": "head_moved"}}},
  "ci_wait": {"type": "wait", "does": "Waits for CI on the pushed commit", "cap": 3, "deadline_hours": 6,
              "on": {"ci_finished": {"to": "ci_check"}}},
  "ci_check": {"type": "code", "does": "Checks the CI result is for the current commit and reads it",
               "checks_premise": true, "survives": "restart", "units": "one", "repositories": "one",
               "on": {"ci_green": {"to": "done", "reason": "ci_green"}, "ci_red": {"to": "stopped", "reason": "ci_red"},
                      "ci_stale": {"to": "ci_wait"}}}}}
```

### The two templates

`flow new` writes them; the fixtures replay events on them, so their states, events, caps and writes are fixed here. Read a cell `event → target [stop point] (reason)`. In both: every `code` and `agent` state has `survives: restart`, `units: one`, `repositories: one`; every `agent` state has `weak_model: no`; every `gate` has `can_judge: yes`, a `judge`, and `deadline_hours` 72; `ci_wait` has `deadline_hours` 6, the other waits 168. The `does` sentences and the `judge` wording are the core author's, from report.md section 6. A state not named in a "Writes" line writes nothing outside: what an agent or a check produces travels in its event and is written by the next program.

**`feature`**: name `feature`, start `ready`, `stop_at` `ready_pr`, budget 20 dollars and 240 minutes. States in this order:

| State | Type | Cap | Transitions |
|---|---|---|---|
| `ready` | code | | `claimed` → `planning` · `not_eligible` → `stopped` (not_eligible) |
| `planning` | agent | 3 | `plan_written` → `plan_size` |
| `plan_size` | code | | `plan_small` → `coding` [plan] · `plan_large` → `plan_review` [plan] |
| `plan_review` | gate, shows "the plan" | | `plan_approved` → `coding` · `plan_rejected` → `planning` |
| `coding` | agent | 6 | `code_written` → `checks` |
| `checks` | code | | `checks_passed` → `draft_pr` · `checks_failed` → `coding` |
| `draft_pr` | code | | `pr_opened` → `ci_wait` [draft_pr] |
| `ci_wait` | wait | 8 | `ci_finished` → `ci_check` |
| `ci_check` | code, checks premise | | `ci_green` → `review_checks` · `ci_red` → `ci_fix` · `ci_stale` → `ci_wait` |
| `ci_fix` | agent | 2 | `fix_pushed` → `ci_wait` |
| `review_checks` | agent | | `review_done` → `mark_ready` · `review_failed` → `coding` |
| `mark_ready` | code | | `marked_ready` → `human_review` [ready_pr] |
| `human_review` | gate, shows "the pull request" | | `approved` → `merge_auth` · `changes_requested` → `rework` |
| `rework` | code | 2 | `comments_collected` → `coding` |
| `merge_auth` | gate, shows "the pull request" | | `merge_authorised` → `merging` · `merge_refused` → `stopped` (merge_refused) |
| `merging` | code, checks premise | | `merged` → `delivery` [merged] · `head_moved` → `stopped` (head_moved) · `merge_failed` → `stopped` (merge_failed) |
| `delivery` | wait | | `deployed` → `closing` [deployed] · `deploy_failed` → `stopped` (deploy_failed) |
| `closing` | code, checks premise | | `closed` → `done` (delivered) · `premise_failed` → `stopped` (premise_failed) |

Writes, as `what` / `key`: `ready` "the run record" / `run-{ticket}` · `plan_size` "the plan" / `plan-{ticket}` · `draft_pr` "the branch" / `flow/{ticket}` and "the pull request" / `pr-{ticket}` · `ci_fix` "the branch" / `flow/{ticket}` · `mark_ready` "the pull request" / `pr-{ticket}` · `merging` "the merge" / `merge-{ticket}` · `closing` "the closing note" / `close-{ticket}`.

Code decides whether the plan is reviewed (`plan_size`), never the agent that wrote it. `coding` 6 is three local rounds, twice.

**`bug`**: name `bug`, start `triage`, `stop_at` `root_cause`, budget 10 dollars and 120 minutes. States in this order:

| State | Type | Cap | Transitions |
|---|---|---|---|
| `triage` | code | | `ticket_ready` → `premise` · `duplicate_found` → `done` (duplicate) · `not_eligible` → `stopped` (not_eligible) |
| `premise` | agent, checks premise | | `still_fails` → `root_cause` · `already_fixed` → `done` (already_fixed) · `cannot_reproduce` → `stopped` (cannot_reproduce) |
| `root_cause` | agent | 5 | `cause_written` → `notify` |
| `notify` | code | | `confident` → `repro` [root_cause] · `low_confidence` → `stopped` (low_confidence) |
| `repro` | agent | | `repro_written` → `fix` [plan] |
| `fix` | agent | | `fix_written` → `verify` |
| `verify` | code | | `verified` → `draft_pr` · `verify_failed` → `root_cause` |
| `draft_pr` | code | | `pr_opened` → `ci_wait` [draft_pr] |
| `ci_wait` | wait | 4 | `ci_finished` → `ci_check` |
| `ci_check` | code, checks premise | | `ci_green` → `human_review` [ready_pr] · `ci_red` → `ci_fix` · `ci_stale` → `ci_wait` |
| `ci_fix` | agent | 2 | `fix_pushed` → `ci_wait` |
| `human_review` | gate, shows "the pull request" | | `merged_by_human` → `closure_wait` [merged] · `closed_with_reason` → `done` (rejected) |
| `closure_wait` | wait | | `closure_due` → `closure_check` |
| `closure_check` | code, checks premise | | `signal_stopped` → `done` (fixed) · `signal_continues` → `stopped` (not_fixed) |

Writes: `triage` "the run record" / `run-{ticket}` · `notify` "the root cause note" / `cause-{ticket}` · `draft_pr` "the branch" / `flow/{ticket}` and "the pull request" / `pr-{ticket}` · `ci_fix` "the branch" / `flow/{ticket}` · `closure_check` "the closing note" / `close-{ticket}`.

## 2. `flow check`: the refusals

`check(definition)` returns a list of problems, each `{"code", "message", "where"}`; an empty list means the definition holds. `where` is a path into the file: `""` for the whole file, `budget`, `stop_at`, `states.checks`, `states.open_pr.writes[0]`, `states.checks.on.checks_failed`. `message` is the plain sentence printed: what is wrong, then the edit that fixes it, with the key to write and its shape ('Add "cap": <n> to one of them…', 'Add "judge": "<who decides…>"'). The table gives the first half. A test compares `code` and `where`; `test_flow_review.py` also checks that each message names its key.

`malformed` is checked first; if any `malformed` problem exists, only those are returned, because the other rules need a readable structure. Otherwise the problems come in the order of this table, then in file order. A state whose `type` is unknown gets `unknown_step_type` and is left out of the rules that depend on the type.

| Code | Refuses | Sentence printed | `where` |
|---|---|---|---|
| `malformed` | The file is not a flow: the cases listed under the table | "The file cannot be read as a flow: ‹what is wrong›." | per case, below |
| `unknown_step_type` | A state whose `type` is missing or not one of the five | "Step ‹state› has the type ‹type›, which is not one of code, agent, human, gate, wait." | `states.‹state›` |
| `loop_without_cap` | A loop no cap bounds. Take the graph of transitions between declared states, remove every state that has a `cap` and every transition whose `reaches` equals `stop_at` (the run ends there, so no circle goes through it): one problem per group of remaining states that can reach each other in a circle (a state that loops on itself is such a group) | "The steps ‹a, b› can repeat without end: none of them has a cap." | `states.‹first state of the group in file order›` |
| `write_without_key` | A `writes` entry whose `key` is missing or does not contain `{ticket}`, or whose `what` is missing or empty; or an entry whose `key` is already used, earlier in the file, with another `what` | "Step ‹state› writes ‹what› without a key derived from the ticket: run twice, the step could not recognise its own write." or "Step ‹state› writes ‹what› under the key ‹key›, which already names ‹other what›." | `states.‹state›.writes[‹i›]` |
| `no_stop_point` | `stop_at` missing, or no transition that does not go to `stopped` has `reaches` equal to it (every state is reachable, see `malformed`) | "The flow does not say where it stops on purpose: it has no "stop_at"." or "stop_at is "‹stop_at›", which is not a stop point of this flow: a stop point is not a step, it is a name a transition reaches.", each followed by the choices: "Choose one of: ‹the names given by `reaches`, in file order›" | `stop_at` |
| `no_budget` | `budget` missing or not an object, or `dollars` or `minutes` missing or not a number above 0 | "The flow has no budget in dollars and minutes for one ticket." | `budget` |
| `wait_without_premise_check` | (a) A transition from a `wait` or `human` state to a `code` or `agent` state without `checks_premise: true`. (b) A transition from a `gate` to a `code` or `agent` state that has `writes` and no `checks_premise: true`. (c) A state with `checks_premise: true` and fewer than two declared events. Targets that are `gate`, `wait`, `human`, `done` or `stopped` need no check | (a), (b) "After ‹state›, the step ‹target› does not check that the facts still hold." (c) "The step ‹state› checks its facts but has one way out only: it cannot say they changed." | (a), (b) `states.‹state›.on.‹event›`; (c) `states.‹state›` |
| `wait_without_deadline` | A `wait` or `human` state with no `deadline_hours`, or one that is not a number above 0 | "The step ‹state› waits with no deadline: a lost event would hold the ticket for ever." | `states.‹state›` |
| `gate_without_judge` | A `gate` with no `judge`, or an empty one | "The gate ‹state› names nobody who decides." | `states.‹state›` |
| `gate_without_deadline` | A `gate` with no `deadline_hours`, or one that is not a number above 0 | "The gate ‹state› has no deadline: a silent approver would hold the ticket for ever." | `states.‹state›` |
| `gate_cannot_refuse` | A `gate` whose declared events, `deadline_passed` left aside, do not lead to at least two different targets | "The gate ‹state› can only say yes: nothing leads anywhere else." | `states.‹state›` |
| `gate_shows_nothing` | A `gate` with no `shows`, or one that is not the `what` of a `writes` entry of another state. For a gate a run can enter, that other state must be one a run can enter too: a step behind the stop point never writes | Two sentences. No `shows`: "The gate ‹state› shows its judge nothing a step wrote: nobody could judge it. Add "shows"…". A `shows` nobody writes: "The gate ‹state› shows its judge "‹shows›", which is nothing a step wrote: nobody could judge it. Use one of: ‹each `what` it could show›, or add a "writes" entry…" | `states.‹state›` |

The `malformed` cases and their `where`:

- `""`: the definition is not an object.
- The key itself (`format`, `name`, `start`, `states`, `stop_at`): `format` is not the integer 1; `name`, `start` or `states` is missing or of the wrong type; `name` is not a name; `start` is not a declared state; `states` is empty; `stop_at` is present and not a name.
- `states.‹state›`: the state's name is not a name, or is `done` or `stopped`; the state is not an object; `does` is missing or not a non-empty string; `on` is missing, not an object or empty; `cap` is not an integer above 0; `writes` is not a list of objects; `checks_premise` is not a boolean, or is true on a state that is not `code` or `agent`; no path of transitions leads from `start` to the state. This last case is not reported while `start` is not a declared state or some transition names a target that is not a declared state, `done` or `stopped`: the path is broken there, and one mistyped name must stay one line, not one per step behind it.
- `states.‹state›.on.‹event›`: the event type is not a name; the transition is not an object with a `to`; `to` is not a declared state, `done` or `stopped`; `to` is `stopped` without a `reason`; `reason` or `reaches` is present and not a name; the event is `human_stop`; the event is `step_failed` on a state that is not `code` or `agent`.

Exit codes of the command: 0 no problem, 1 at least one problem (a file that holds a JSON list or string is `malformed`, exit 1), 2 the file is missing or is not JSON.

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
{"id": "T-12:checks:1:checks_failed", "type": "checks_failed",
 "at": {"state": "checks", "visit": 1}, "payload": {"dollars": 0.5, "minutes": 6}}
```

- `id` and `type`: non-empty strings. The caller derives `id` from the ticket, the state, the visit and the type, never from a delivery or at random: the same fact delivered twice carries the same id. The examples below shorten ids to `evt-3`.
- `at`: optional object, the state this event answers and which visit of it (`visit` is an integer above 0, the value of `visits[state]` when the step began). **Required** for `deadline_passed` and `step_failed`. It is how an answer meant for an earlier round is told from one meant for this round; an event that answers a gate should always carry it.
- `payload`: optional object; its `dollars` and `minutes`, when present, are numbers at or above 0 and are what the step cost. An event that ends a `code` or `agent` step must carry both (rule 8). Each cost is counted rounded up to 4 decimals: a cost above 0 never counts for nothing. Other payload keys are carried, never read: the event's **type** says what happened (`confident` or `low_confidence`), the function never decides from a payload value.
- A key that is present has its type: `"payload": null` or `"at": null` is a malformed event.

**The output document.** Seven keys, always.

```json
{"outcome": "moved", "reason": null,
 "transition": {"from": "checks", "event": "checks_failed", "to": "coding"},
 "message": "checks → coding, on checks_failed.", "run": {},
 "remaining": {"dollars": 3.25, "minutes": 40}, "over_budget": false}
```

`run` is shown empty here. `outcome` is one of `moved` (to a live state), `done`, `stopped`, `duplicate`, `refused`. `reason` is null for `moved`, a name otherwise. `transition` is null for `duplicate` and `refused`; otherwise `from` is the state given (null if it was not a string) and `to` the new state. `message` is one plain sentence, not compared by tests. `run` is a new object: a full run document, except under rules 1 and 2 where it is a copy of the value given, whatever that is. `remaining` is the budget minus the returned run's `spent`, never below 0, rounded to 4 decimals; `over_budget` is true when either spent value is above its budget. When the returned run has no well-formed `spent` (rules 1 and 2 only), `remaining` is null and `over_budget` false.

**The rules, in this order. The first that applies decides.**

| # | When | Outcome, reason | New run |
|---|---|---|---|
| 1 | The event is malformed: not an object; `id` or `type` not a non-empty string; `payload` present and not an object, or a cost in it not a number at or above 0; `at` present and not `{"state": non-empty string, "visit": integer above 0}`; `at` absent on `deadline_passed` or `step_failed` | `refused`, `malformed_event` | the value given |
| 2 | The run is an object whose `state` is exactly `done` or `stopped`, whatever its other keys hold | `refused`, `run_ended` | the value given |
| 3 | The run is inconsistent: not an object; a key missing; `state` not a declared state; `visits` not an object of integers at or above 0 keyed by declared states; the count of `state` under 1; a count above its state's `cap`; `spent` not two numbers at or above 0; `seen` not a list of strings; `reason` not null | `stopped`, `inconsistent` | `state` `stopped`, `reason` `inconsistent`; `visits`, `spent`, `seen` kept when each is well formed, otherwise `{}`, zeros, `[]`; the event id appended to `seen` if absent; no cost added. This run is ended: any later event meets rule 2 |
| 4 | `event.id` is in `seen` and `event.type` is not `human_stop`. Only the id is compared: the same id with another type or payload is still a duplicate | `duplicate`, `already_seen` | unchanged |
| 5 | `event.type` is `human_stop` | `stopped`, `human_stop` | accepted (below), whatever the state, `at`, the caps and the budget, and whether its id was already seen: a person's stop is never dropped as a duplicate. An id already in `seen` is not appended a second time |
| 6 | The type does not belong here: it is not a key of the state's `on`, not `deadline_passed`, and not `step_failed` on a `code` or `agent` state. If no state declares it and it is not built in: `unknown_event`; otherwise `event_not_expected` | `refused`, one of the two | unchanged |
| 7 | The type belongs here, but `at` is present and `at.state` is not the current state or `at.visit` is not its count: the event answers another round | `refused`, `stale_event` | unchanged |
| 8 | The state is `code` or `agent`, and `payload.dollars` or `payload.minutes` is absent. One exception: a `deadline_passed` that ends the run, that is, one the state does not declare, or declares towards `stopped` or `done`. It comes from outside the step and knows no cost. A `deadline_passed` the state declares towards a declared state starts work again: it is a retry, and it says what the round cost | `refused`, `cost_missing` | unchanged |
| 9 | The transition goes to `stopped`; or the type is `deadline_passed` or `step_failed` and the state does not declare it | `stopped`, the transition's `reason`; `deadline_passed`; `step_failed` | accepted |
| 10 | The transition goes to `done` | `done`, the transition's `reason`, or `finished` | accepted |
| 11 | The transition's `reaches` equals `stop_at` | `done`, `stop_point` | accepted; the target is not entered |
| 12 | `spent` is now above the budget, in dollars or in minutes (equal is within budget) | `stopped`, `budget_exceeded` | accepted; the target is not entered |
| 13 | The target has a `cap` and its count is already at the cap | `stopped`, `cap_reached` | accepted; the target is not entered |
| 14 | Otherwise | `moved`, null | accepted; `state` is the target and its count rises by 1 |

"Accepted" (rules 5 and 9 to 14) means: the event id is appended to `seen`; its costs are added to `spent`: each cost is first rounded up to 4 decimals (0.00004 counts as 0.0001, 0.25 as 0.25), then each sum is rounded to 4 decimals, and it is the rounded values that are stored and compared with the budget; `state` and `reason` are set by the row. A declared `deadline_passed` or `step_failed` is a transition like any other and goes through rules 9 to 14. A refused event is not added to `seen` and costs nothing: delivered again on the same run, it is refused again.

**What the caller owes.** The guarantees hold for one run document, passed from each call to the next, one event at a time: two events handled at once from the same run both move, and a caller that starts again from a new run forgets caps, budget and `seen`. Keeping one queue per ticket is the caller's job and comes with `flow claim`. A refused event is kept and delivered again after the run next moves (it may only have come early); once the run has ended it gets `run_ended` and is dropped. Every end of a `code` or `agent` step is reported by one of the state's events or by `step_failed`, with its costs: there is always an event that fits, so nothing is spent without being counted.

What follows from the rules, and what the tests check: for every state and every event there is one outcome; a count never passes its cap; `spent` never falls; an event delivered twice changes nothing the second time; an event that does not belong to the current state or visit is refused, never guessed; once ended, a run never moves; a well-formed `human_stop` on a live, consistent run always gives `stopped` with `human_stop`, whatever its id; a hundred costs of 0.00004 add up to 0.01, never to 0. Stopping ends the run record, not a step in progress: its event is then refused with `run_ended`, and cancelling the job belongs to the pipeline.

**Three worked examples**, on the `small` definition of section 1.

A legal transition with a cost. Run as shown above, event `{"id": "evt-3", "type": "checks_failed", "payload": {"dollars": 0.5, "minutes": 6}}`. Rule 14 gives the output document shown above, with this `run`:

```json
{"state": "coding", "visits": {"ready": 1, "coding": 2, "checks": 1},
 "spent": {"dollars": 1.75, "minutes": 20}, "seen": ["evt-1", "evt-2", "evt-3"], "reason": null}
```

The same event delivered again, on the run just returned. Rule 4: outcome `duplicate`, reason `already_seen`, `transition` null, the message "Event evt-3 was already taken into account: nothing changes.", and the same `run`, `remaining` and `over_budget` as above.

A cap reached. Six events in (`claimed`, then `code_written` and `checks_failed` twice, then `code_written`), the run is `{"state": "checks", "visits": {"ready": 1, "coding": 3, "checks": 3}, "spent": {"dollars": 3, "minutes": 40}, "seen": ["evt-1", "evt-2", "evt-3", "evt-4", "evt-5", "evt-6"], "reason": null}`. The event is `{"id": "evt-7", "type": "checks_failed", "payload": {"dollars": 0.25, "minutes": 2}}`. The agent already coded three times; a fourth round is not paid. Rule 13:

```json
{"outcome": "stopped", "reason": "cap_reached",
 "transition": {"from": "checks", "event": "checks_failed", "to": "stopped"},
 "message": "Stopped: the step coding already ran 3 times, its cap.",
 "run": {"state": "stopped", "visits": {"ready": 1, "coding": 3, "checks": 3},
         "spent": {"dollars": 3.25, "minutes": 42},
         "seen": ["evt-1", "evt-2", "evt-3", "evt-4", "evt-5", "evt-6", "evt-7"], "reason": "cap_reached"},
 "remaining": {"dollars": 1.75, "minutes": 18}, "over_budget": false}
```

## 4. The command lines

All under `python3 cli/harness.py flow`. Every command takes `--format md|json`, default `md`: plain words for a person, or the JSON document named below. Exit codes everywhere: **0** fine, **1** refused or failing, **2** wrong usage or an input file that is missing or is not JSON (message on stderr, starting with `flow:`). Only `flow new` writes a file, and `flow next` when asked to with `--save-run`. This section holds the five commands of the first slice; the sixth, `flow fit`, came after and is in section 11. The help of `flow` lists it first, as step 0 of the order of work, because it is run before any definition exists.

**Answers and notes.** What a command answers is on stdout, in the form of the table below. What helps a person go on is a note: one sentence per line on stderr, after the answer, and only with `--format md`; with `--format json` stdout holds the document and stderr nothing. The notes: where a run really stops ("As written, a run stops on purpose after ‹step›: the stop point "‹stop_at›" (stop_at) is the name its transition reaches, not a step. The ‹n› steps after it are described but not run… To go further, set stop_at to ‹later stop points›."), printed by `flow new`, by `flow check` when the flow holds and by `flow status` at level 1; the command that comes next ("Next: …"); and what the other command would say of the same file (below). `flow --help` gives the six steps of the work in order, and `flow next --help` shows an event file.

One rule for the four commands that read a definition: a file that is missing or is not JSON is exit 2; any JSON value is then handed on as it is. A value that is not a flow is `malformed` for `flow check` (exit 1), level 0 for `flow status` (exit 0), and exit 2 for `flow next` and `flow place`, as said in their rows.

Wherever a step type is shown to a person, these words are used (`flow.TYPE_WORDS`): `code` "a program", `agent` "an agent", `human` "a person works", `gate` "a person decides", `wait` "waits". An unknown type is printed as written.

| Command | Prints for a person | `--format json` | Exit 1 when |
|---|---|---|---|
| `flow new <feature\|bug> [--out FILE] [--force]` | "Written: ‹path›", then the steps in order, one line each: "- ‹state› (‹type words›): ‹does›"; the line of a step after which a run stops on purpose ends with "   ← as written, a run stops here on purpose". Default path `.harness/flow/<kind>.json` under the current directory; folders are created | `{"file", "definition"}` | the file exists and `--force` is absent (nothing written) |
| `flow check <file>` | "This flow holds: ‹n› steps, it stops at ‹stop_at›, one ticket may cost up to ‹dollars› dollars and ‹minutes› minutes." or one line per problem: "- ‹sentence› (‹where›)" | `{"file", "passed", "problems"}` | a problem is found |
| `flow next <file> --event FILE (--run FILE \| --new) [--save-run FILE]` | The `message`, then "State: ‹state›. Spent: ‹dollars› dollars, ‹minutes› minutes. Left: ‹dollars› dollars, ‹minutes› minutes." | the output document of section 3 | the outcome is `refused` or `stopped` |
| `flow place <file>` | Section 6 | the `place` document | a step cannot be placed, or a gate cannot be judged by anyone |
| `flow status <file> [--map]` | Section 7 | the `status` document | never: a level is a fact, not a failure |

- `flow next` needs exactly one of `--run FILE` (the run returned by the call before) and `--new` (the first event of a ticket: the run is `new_run`); neither or both is exit 2. A run nobody passed back is never silently replaced by a fresh one.
- `flow next --save-run FILE` writes the `run` of the answer to FILE, whatever the outcome, so that the next call takes it with `--run FILE`; the same file may be given to both. A file that cannot be written is exit 2, and nothing is printed on stdout. A note then gives the next command, or says the run has ended. Without `--save-run`, a first event (`--new`) that moves ends with a note saying the run was not saved.
- `flow check` and `flow place` answer two questions and each can pass while the other fails: a gate with `can_judge: no` passes `check`, a gate that shows nothing can be placed. Each says so in a note. `flow check`, when the flow holds: "Next: flow place ‹file›…" or, when `place` does not pass, "Careful: flow place ‹file› does not pass on this file…". `flow place`, when `check` finds problems: "Careful: flow check ‹file› finds ‹n› problem(s) in this file, so this placement is provisional…"; otherwise, when it passes, "Next: flow status ‹file› --map".
- `flow next` on a definition that does not pass `check` prints exactly what `flow check` prints for it (same words, or the same JSON document) on stdout, and exits 2.
- An event or run file that is JSON but ill formed is not a usage error: `flow next` answers it by rules 1 to 3. One slip is named besides: when the `--run` file holds a whole answer of `flow next` (an object with a `run` and no `state`), the answer is still rule 3, and one line on stderr says to give back only its `run` part.
- `flow place` does not run `check`. When `place` raises `ValueError`, it prints `flow: ‹message›` on stderr and exits 2; otherwise it exits 0 or 1 from `passed`. `flow status` never refuses a file it could parse.

## 5. The Python interface

What the tests call. Nothing below prints, except the two `main`.

`cli/harnesslib/flow.py`:

| Function | Returns |
|---|---|
| `load_definition(path)` | The parsed JSON value, whatever it is. Raises `ValueError` (message starts with the path) only if the file is missing or is not JSON. Validates nothing |
| `check(definition) -> list[dict]` | Problems `{"code": str, "message": str, "where": str}`, section 2. Never raises, whatever it is given |
| `new(kind) -> dict` | A fresh copy of the template `feature` or `bug`; `check(new(kind)) == []`. Raises `ValueError` for another kind |
| `new_run(definition) -> dict` | The run before any event, section 3 |
| `next_state(definition, run, event) -> dict` | `{"outcome", "reason", "transition", "message", "run", "remaining", "over_budget"}`, section 3. Never raises on any `run` or `event`, whatever their type |
| `stop_steps(definition) -> list[str]`, `beyond_stop(definition) -> list[str]` | The states with a transition that reaches the stop point, and the states behind it, which no run enters as the file is written; both in file order, both empty when `check` finds a problem |
| `status(definition, placement=None) -> dict` | Section 7. `placement` is a `place` document; when `None` and the definition is not `malformed`, `flow_place.place(definition)` is imported and called at that moment |
| `render_map(state) -> str` | The map of section 7, from a `status` document |
| `build_parser(parser=None)`, `main(argv=None, args=None) -> int` | As the other modules of `cli/harnesslib`: `harness.py` adds `flow.build_parser(sub.add_parser("flow", …))` and calls `flow.main(args=args)`. The `place` subcommand is declared here (`file`, `--format`) and handed to `flow_place.main([file, "--format", fmt])`, imported at that moment; its return value is the exit code |

`status`, `render_map`, `build_parser` and `main` are kept in `flow.py` as its interface; their bodies are in `flow_status.py` and `flow_cli.py`, loaded when first called.

Constants: `STEP_TYPES = ("code", "agent", "human", "gate", "wait")`, `ENDED = ("done", "stopped")`, `TEMPLATES = ("feature", "bug")`, `BUILT_IN_EVENTS = ("human_stop", "deadline_passed", "step_failed")`, and `TYPE_WORDS`, the dict of section 4.

`cli/harnesslib/flow_place.py`:

| Function | Returns |
|---|---|
| `load_grid(path=GRID_FILE) -> dict` | `flow_placement.json` |
| `fix_of(grid, step) -> str \| None` | What to write in a step that cannot be placed (section 6); `None` once it can |
| `place(definition) -> dict` | The `place` document of section 6. Raises `ValueError` if the definition is not an object or its `states` is not an object of objects; otherwise places what it finds without running `check` |
| `main(argv=None) -> int` | `flow place`: arguments `file` and `--format md\|json`. Loads the file with `flow.load_definition` and uses `flow.TYPE_WORDS`; exit codes as in section 4 |

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

The seven questions. The quoted sentence is the question's `text`, to the letter: the grid file and `decide.md` both copy it.

| Question, `text` | `from.key` | Option (step value) → next question or **destination** |
|---|---|---|
| `who`, "Who performs this step?" | `type` | `code` → `survive` · `agent` → `survive` · `human` → **ticket_state** · `wait` → **ticket_state** · `gate` → `judge` |
| `judge`, "Can the person who approves really judge what they approve?" | `can_judge` | `yes` → **human_gate** · `no` → **no_gate** |
| `survive`, "How long does it live, and what must survive?" | `survives` | `restart` (minutes to a few hours; starting again from its beginning is acceptable) → `spread` · `midway` (days inside one computation, or it must not run twice, or every run must be replayable step by step) → **durable_engine** |
| `spread`, "Does the work split into many independent units?" | `units` | `one` → `repos` · `many` → **campaign** |
| `repos`, "How many repositories need this step?" | `repositories` | `one` → `determined` · `several` → **reusable_workflow** |
| `determined`, "Is the right output determined by the inputs?" | `type` | `yes` (step value `code`) → **code** · `no` (step value `agent`) → `weakness` |
| `weakness`, "Is this step here because today's model is weak?" | `weak_model` | `yes` → **dated_skill** · `no` → **skill** |

The nine destinations. `says` is fixed here too.

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

`name`, `where` and `why` of each destination and the option labels are the placement author's, from report.md section 7. There is no destination for a graph framework.

**The `place` document.**

```json
{"flow": "small",
 "steps": [{"state": "coding", "type": "agent", "does": "Implements the ticket and its tests", "shows": null,
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

`steps` follows the file order of `states`, one entry per state. `shows` is the step's `shows` when it is a non-empty string, otherwise null. A step with a missing answer has `status` `open`, `destination`, `name`, `says`, `decided_by` and `reason` null, `path` as far as it went, and `missing` `{"question", "text", "key"}`: the question that has no answer and the step key that would answer it. An open step also carries `fix`, one sentence that says what to write: 'Add "survives": "restart" or "midway".' when the key is absent, '"survives" is "hours": write "restart" or "midway".' when its value is not one the grid reads, then 'Also needed: "units" ("one" or "many"), …' for every other key the walk would ask for if it went on by the answer that leads to the next question. Nothing more is supposed of a step whose `type` is unknown. A placed step has no `fix` key. An unknown `type` leaves the step open at `who`. `decided_by` is the last entry of `path`, with the question's text. `engine`, `refused_gates` and `open` list the states sent to `durable_engine`, sent to `no_gate`, and left open, in file order. `verdict.code` is `open` if a step is open, otherwise `engine` if `engine` is not empty, otherwise `no_engine`. `passed` is true when `open` and `refused_gates` are both empty: needing an engine is an answer, not a failure.

**For a person**, one line per step, then the verdict, then the refused gates. A gate's line ends with what its judge is shown, when the file says it:

```
- coding (an agent): a skill is enough. Decided by "Is this step here because today's model is weak?": no.
- approval (a person decides): this is a human gate. Decided by "Can the person who approves really judge what they approve?": yes. Shown to a maintainer of the repository: the branch.

Verdict: no step needs an engine.
```

The other verdict sentences: "One step would need an engine: ‹state›, ‹does›. ‹reason›" (or "‹n› steps would need an engine: …"); "‹n› step(s) cannot be placed yet: ‹state› has no answer to "‹question text›" (key ‹key›)". For each refused gate, one more line: "A gate nobody can judge: ‹state›. Remove it, or give ‹judge› something they can read and refuse."

## 7. `flow status --map`: level Mapped, on paper

The ladder of proposal section 5. This slice measures level 1 only, from the file alone. `status(definition, placement)` returns:

```json
{"flow": "small", "steps": 8, "stop_at": "draft_pr", "budget": {"dollars": 5, "minutes": 60},
 "level": {"reached": 1, "name": "Mapped", "next": 2},
 "checks": [
  {"id": "definition_holds", "passed": true, "origin": "flow check", "plain": "the flow is written down and holds together", "detail": []},
  {"id": "steps_placed", "passed": true, "origin": "flow place", "plain": "every step has a place", "detail": []},
  {"id": "stop_and_budget", "passed": true, "origin": "the definition file", "plain": "a stop point and a budget are set", "detail": []}],
 "next_step": "Nothing more on paper. The next level needs the flow to run on real tickets, which this version does not do yet."}
```

- `definition_holds` passes when `check(definition) == []`; `detail` holds the problems' sentences.
- `steps_placed` passes when the placement's `passed` is true (no open step, no gate nobody can judge); `detail` holds one sentence per open step, "The step ‹state› has no answer to "‹question text›" (key ‹key›).", then one per refused gate, the line `flow place` prints for it, with the judge read from the definition ("its judge" when it names none).
- `stop_and_budget` passes when `check` returns neither `no_stop_point` nor `no_budget`; `detail` holds those sentences.
- When the definition is `malformed`, `steps_placed` and `stop_and_budget` both fail with the one detail "the file cannot be read as a flow", and `place` is not called.

`reached` is 1 when the three pass; otherwise `level` is `{"reached": 0, "name": "None", "next": 1}`, where `"None"` is the string, the name of level 0. `next_step` at level 0 is the first sentence of `detail` of the first failing check, introduced by "Fix this first: ". `flow`, `steps`, `stop_at` and `budget` are JSON null when unreadable.

`flow status <file> --map` prints `render_map(state)`, in the style of `harness status --map`: the ladder with "you are here", then the flow in one line, then what the next level needs, then the next step. No check id is printed. Level 0 is not listed once level 1 is reached.

```
Where this flow stands, level by level:
✓ 1 Mapped      the flow is written down and every step has a place   ← you are here
· 2 Shadow      the flow runs on real tickets and only comments
· 3 Drafting    runs end with a draft PR; CI and review results come back to the run
· 4 Delivering  runs reach a reviewed PR and merge only on a human's word

This flow: small, 8 steps, stops at draft_pr, up to 5 dollars and 60 minutes for one ticket.
Levels 2 to 4 are read from real runs. Nothing measures them yet.
Next step: Nothing more on paper. The next level needs the flow to run on real tickets, which this version does not do yet.
```

At level 0 the first ladder line is "· 0 None        the phases are chained by hand   ← you are here", and the block "What level 1 still needs:" lists the `plain` of each failing check, each followed by its `detail` lines indented. Without `--map`, the command prints the level in one line ("This flow is at level ‹n› of 4 (‹name›)."), then one line per check: "✓" or "✗", its `plain`, "(read by ‹origin›)". One case is told apart in both forms: when `flow check` refuses as `malformed` a file whose steps can be read, the two checks that were not made are printed "– ‹plain›: not looked at, the file must first pass flow check" (in the map, that sentence in place of their detail), because "✗ a stop point and a budget are set" would be untrue of a file that sets both. The `status` document is the same as before. On stderr, as notes: at level 0 without `--map`, "Next step: ‹next_step›" and the command that shows every reason; at level 1, how to try the flow by hand with `flow next`.

## 8. The fixture family `fixtures/flow/`

No agent is run: the family is graded by `cli/tests/test_flow_fixtures.py`, which calls the functions of section 5. A fixture that cannot be read makes the test fail with its path; no test skips itself. The family gets its row in the opening table of `fixtures/README.md` (grader: that test) and its own `fixtures/flow/README.md`.

```
fixtures/flow/
├── README.md
├── definitions/every-case.json   a definition for what the templates do not hold; others may join it
├── sequences/<name>.json         one recorded sequence of events and the expected state after each
├── cases/<name>.json             one definition, often a template with one thing changed, and what check, place and status answer
└── place/<name>/
    ├── definition.json           only when the flow is not a template
    ├── traps.md                  only in trapped/: what was planted and why, in plain words
    └── expected.json             the expected destination of each step and the verdict
```

`definitions/every-case.json` passes `check` and holds at least: a `human` step; an `agent` step that declares `step_failed` back to itself, with a cap; a gate that declares `deadline_passed`; a transition to `done` without a `reason` (it ends with `finished`).

A **definition reference** is `template:feature`, `template:bug` (the test calls `flow.new`), or a path relative to `fixtures/flow/`.

**A sequence.** One file is one run, from one start.

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

`override` (optional) replaces top-level keys of the definition before the replay (`stop_at`, `budget`); the result must still pass `check`. `start` is `"new"` or a run document, well formed or not. The test feeds the first event to the starting run, then each event to the run returned before it. `expect` always gives `outcome`, `reason` and `state` (the returned run's `state`); `visits` (only the states listed are compared; no count above a cap may be written), `spent`, `remaining`, `over_budget` and `seen` (the returned run's whole list) are optional. Use costs in quarters (0.25, 0.5) so sums are exact.

The fifteen sequences:

| File | Definition | What it must show |
|---|---|---|
| `feature-to-ready-pr` | feature | The path from `ready` to the default stop point: `done` with `stop_point` at `marked_ready`, through `plan_large` and the plan approval; then one more event is refused with `run_ended`. It is not the whole flow: the states behind the stop point are replayed by `feature-to-delivered` |
| `event-twice` | feature | An event delivered twice, right away and again three events later: `duplicate` both times, the run unchanged, the cost counted once; then the same id with another type and another cost: `duplicate` again |
| `events-out-of-order` | feature | `checks_passed` before `code_written`, and `ci_green` while planning: `event_not_expected`, state unchanged; an event type nobody declares: `unknown_event`; the same refused event sent again is refused again; then the right event moves |
| `lost-event` | feature | `ci_finished` arrives while the run is still in `draft_pr`: `event_not_expected`; after `pr_opened` the same event, delivered again, moves; `ci_red` leads to `ci_fix`, whose job never answers: `deadline_passed` at `ci_fix`, visit 1: `stopped`, `deadline_passed` |
| `step-failed` | feature | In `coding`, `step_failed` without costs: `cost_missing`, nothing changes; with both costs: `stopped`, `step_failed`, the cost counted |
| `stale-answer` | feature, `stop_at: merged` | After one `changes_requested` round the run is in `human_review` for the second time; an `approved` with `at` visit 1: `stale_event`, state unchanged; the `approved` of visit 2 moves to `merge_auth` |
| `cap-reached` | feature | The local rounds until `coding` would be entered a seventh time: the sixth `checks_failed` gives `stopped`, `cap_reached` at once, the count still 6 |
| `budget-exceeded` | feature, small `budget` by `override` | An event that lands exactly on the budget moves, `remaining` zero; the next one passes it: `stopped`, `budget_exceeded`, `over_budget` true, although its transition was legal; minutes alone are enough |
| `human-stop` | feature | `human_stop` while the run is in `coding`, carrying a cost that passes the budget: `stopped`, `human_stop`; a later event: `run_ended` |
| `unknown-label` | feature, `start` a run whose `state` is a label no one defined | `stopped`, `inconsistent`, on the first event, whatever it is; a second event: `refused`, `run_ended`. Its twin `counts-over-cap` starts from a `coding` count of 7 and gives the same two answers |
| `rework-loop` | feature, `stop_at: merged` | `changes_requested` twice, each back through `coding`, `checks` and CI; the third: `stopped`, `cap_reached` at `rework` |
| `bug-already-fixed` | bug, small `budget` by `override` | `already_fixed` at the premise check, with a cost above the budget: still `done`, `already_fixed`, `over_budget` true, no root cause attempted |
| `bug-low-confidence` | bug | `low_confidence`: `stopped`, `low_confidence`. Its twin `bug-to-root-cause` takes `confident` instead: `done`, `stop_point` |
| `gate-deadline` | feature | `deadline_passed` without `at`: `malformed_event`; `deadline_passed` naming `plan_review` while the run is in `planning`: `stale_event`, state unchanged; then `plan_written`, `plan_large`, and `deadline_passed` at `plan_review`, visit 1: `stopped`, `deadline_passed` |
| `ci-stale-and-fix` | bug, `stop_at: merged` | A stale CI result returns to the wait; two CI fixes pass; the third: `stopped`, `cap_reached` at `ci_fix` |

The two twins, `counts-over-cap` and `bug-to-root-cause`, are files of their own beside the fifteen.

Twenty-one more were added after the reviews; `fixtures/flow/README.md` describes each. They replay what the first list left without an answer: the feature flow from the human review to the closed ticket and each way it can stop there (`feature-to-delivered`, `feature-stops-at-merge`, `feature-head-moved`, `feature-merge-failed`, `feature-deploy-failed`, `feature-closing-premise-failed`), a rejected plan (`feature-plan-rejected`), the bug flow after its stop point (`bug-duplicate`, `bug-to-fixed`, `bug-not-fixed`, `bug-rejected`), the order of the rules pair by pair (`order-ended-run`: 1 over 2, 2 over 4 and 5; `order-inconsistent-known-id`: 3 over 4; `human-stop-known-id`: 5 whatever the id; `order-stale-before-cost`: 7 over 8, 6 over 8; `reason-over-budget`: 9 over 12; `stop-point-over-budget`: 11 over 12; `stop-point-before-cap`: 11 over 13; `budget-before-cap`: 12 over 13; `budget-dollars-alone`: rule 12 by dollars), and a retry on a declared deadline (`deadline-retry-is-paid`, on `definitions/retry-on-deadline.json`). A run that starts behind the default stop point is given as a `start` run document.

**A case.** One file of `cases/` is one definition and the answers of the commands that replay nothing; `cli/tests/test_flow_cases.py` grades it.

```json
{"about": "One sentence: what this case shows.",
 "definition": "template:feature",
 "remove": ["states.coding.cap"],
 "set": {"states.checks.units": "many"},
 "check": [{"code": "loop_without_cap", "where": "states.coding"}],
 "not_run": ["human_review", "rework"],
 "place": {"steps": {"checks": "campaign"}, "engine": [], "refused_gates": [], "open": [],
           "verdict": "no_engine", "passed": true, "missing": {}},
 "status": {"level": 0, "passed": {"definition_holds": false, "steps_placed": true, "stop_and_budget": true}}}
```

`remove` (dotted paths), then `set` (path → value), change the definition. `check` is required: the whole list `check` must return, `code` and `where`, in order. The others are optional: `not_run` is what `beyond_stop` returns; `place` gives the three lists, `verdict.code`, `passed`, the destination of the steps it names (null for an open step; the steps it does not name are not compared) and under `missing` the key each open step lacks; `status` gives `level.reached` and which checks pass. The family holds at least: a mistyped target (one problem, not one per step behind it), a loop without a cap, a gate that cannot refuse, a gate that shows nothing, an engine with no refused gate (verdict `engine`, `passed` true), a refused gate with no engine (verdict `no_engine`, `passed` false), open steps (verdict `open`), and `every-case` placed.

The same test file also checks, by program, on the two templates and every file of `definitions/`: for every state (plus `done`, `stopped`, an unknown name) and every event type (declared, built in, unknown; with and without costs and `at`), `next_state` returns one well-formed output; and on generated sequences (a seeded `random.Random`, at least 200 sequences of 300 events) no count passes its cap, `spent` never falls, and an ended run never moves.

**A flow to place.** `place/<name>/expected.json`, shortened here:

```json
{"about": "One sentence: what this flow shows.",
 "definition": "template:feature",
 "steps": {"ready": "code", "planning": "skill", "plan_review": "human_gate", "ci_wait": "ticket_state", "…": "the 14 others"},
 "engine": [], "refused_gates": [], "open": [],
 "verdict": "no_engine", "passed": true}
```

`steps` gives every state its expected destination (null for an open step): the test fails when its keys are not exactly the states of the definition. The test compares each step's `destination`, the three lists, `verdict.code` and `passed`, and that every placed step has a `decided_by` and a non-empty `reason`. It also checks that `flow.check` passes on the three definitions.

| Folder | Definition | What it must show |
|---|---|---|
| `feature` | `template:feature` | Every step placed; `no_engine`; `passed` true |
| `bug` | `template:bug` | The same |
| `trapped` | its own `definition.json`, about ten states, a believable flow | Exactly one step with `survives: midway` → `durable_engine`, and it is the only one: beside it, decoys that look like they need an engine and do not (a wait of several days, an agent step of a few hours that may restart, a gate with a long deadline). Exactly one gate with `can_judge: no` → `no_gate`, beside a gate that can be judged; both have a `shows`, since the file must pass `check`. At least one step with `units: many` → `campaign`, one with `repositories: several` → `reusable_workflow`, one with `weak_model: yes` → `dated_skill`. Verdict `engine`, `passed` false. `traps.md` says which step and which gate were planted and why |

## 9. The guide `decide.md`

One page a person reads before or after `flow place`, written from report.md section 7 with its evidence labels and the date of its facts. Its headings, in this order:

1. **The seven questions for one step.** In the grid's order, one sub-heading per question: its `text` to the letter, then its id in code font, the key of the definition that answers it, each answer and where it leads. One paragraph says how these seven come from the report's eight: "does a human decide" became `who` and `judge`; "must it happen every time" stays with `harness place`, for pieces inside one repository; "what shape is the control flow" is answered once for the whole flow, a small table of states in code.
2. **The nine places.** One line per destination: its id in code font, its `says` to the letter, what it means.
3. **When a step really needs an engine.** The symptom table of report.md section 7 (symptom, smallest fix, what removes it).
4. **Reading what `flow place` prints.** The example lines of section 6, explained: the step, who performs it, the place, the question that decided, the verdict, a gate nobody can judge, a step that cannot be placed yet and the key to add.
5. **Three examples.** `coding` and `approval` of the `small` flow of section 1, and one step that lands on `durable_engine`. The page ends, as every doc of proposal section 6, with "the symptom that would make you need it".

Before its first heading the guide gives the seven steps of the work in order, numbered from 0, with the six commands (step 0 is `flow fit`, section 11; step 2 is editing the file, with no command), and defines the words `flow check` uses (stop point, cap, premise check). A second page, `flow-format.md`, is for the person who edits the file: every key of a definition, of a transition and of an event with its allowed values and the step types that need it, one step of each type ready to paste, and one whole flow. `test_flow_review.py` checks that every key the templates use is on that page, that its whole flow passes `check` and `place` with the five types, that each step to paste is a step of it, and that the events it shows play it to its stop point.

`cli/tests/test_flow_guide.py` holds the seven `text` strings and the nine ids and `says` of section 6 as literals and fails, naming the missing one, when `decide.md` lacks any of them or does not exist. `test_flow_place.py` checks the same literals against the grid file.

## 10. Out of this slice

Built since, after this slice: `flow fit` (section 11); seven of the docs of proposal section 6 (`langchain.md`, `langgraph.md`, `engines.md`, `ci-as-engine.md`, `rust.md`, `flows.md`, `costs.md`); and three skills, `flow-why`, `flow-map` and `flow-place`, shipped in the `harness-ai` plugin under `skills/`, not in a plugin of their own. Where the skills differ from proposal section 4: `flow-place` hands a hook or a single CI job to harness-design instead of calling `harness place` itself, and asks no "must it happen every time" (the grid has no such question for a step); `flow-map` also asks who judges each approval, which the proposal gave to flow-gate, and shows `flow status --map`; `flow-why` asks the four answers `flow fit` reads, not one. The rest of this list still holds.

- The other commands of the proposal: `render`, `exits`, `drill`, `scope`, and the run side `claim`, `run-step`, `report`, `sweep`.
- The plugin `plugins/harness-flow/` and four of its seven skills (flow-step, flow-gate, flow-watch, flow-share); the docs of proposal section 6 not listed above.
- Any pipeline file, forge or tracker call, agent call, key, account.
- The mapping from states to ticket labels (`flow:ready`…), the run record written on a ticket, the hash of the definition and the agent's version in the run. Until the run carries that hash, changing a definition while runs are alive (a state renamed, a cap lowered) stops them as `inconsistent` at their next event.
- Time: nothing reads a clock. A deadline is a number in the file; a later sweep turns it into the event `deadline_passed`, and delivers again the events that were refused. Keeping one queue per ticket also comes later.
- Reminders and escalation before a deadline; checking on the forge who approved, and that what the judge was shown is what gets merged.
- Levels 2 to 4 of the ladder, the target of a flow, any state file written under `.harness/`.
- Conditions on payload values, counters that reset, sub-flows, one ticket across several repositories.
- Blind runs of any skill; a Rust implementation.

## 11. `flow fit`

Added after the first slice (section 10 listed it as left out). `flow fit` is run **before any definition exists**. A person, or the skill `flow-why`, records a few answers about what the team builds; the program gives the verdict. Nothing is measured here: the numbers are the team's own, typed in. Rules and sentences are data, in `cli/harnesslib/flow_fit.json`; the code is `cli/harnesslib/flow_fit.py`.

```
flow fit <answers.json>     the verdict; "-" reads the answers on standard input
flow fit --questions        the questions and the allowed values, so that a skill never invents them
```

Both take `--format md|json`. Exit codes as in section 4: **0** a verdict (or the questions), **1** refused answers, **2** wrong usage (no file and no `--questions`) or an input that is missing or is not JSON. `NaN` and `Infinity` are read, then refused as values (exit 1).

**The answers file** is one JSON object with exactly these four keys:

| Key | Allowed values |
|---|---|
| `building` | What is being built, one row of report §8: `"ticket_workflow"` (a ticket workflow for a team, driving a coding agent), `"own_agent_app"` (the team's own agent application in Python or TypeScript, with a known graph and pauses in the process), `"agent_product"` (an agent product for users, with sessions that resume mid-run), `"many_repositories"` (the same change across hundreds of repositories, the report's word: it gives no lower bound), `"long_lived_orchestrator"` (a long-lived orchestrator, a tool server or a binary for many teams) |
| `tickets_per_week` | A number, 0 or more: the tickets that go through this path in a week. It is an average, so 0.5 is allowed |
| `chained_by_hand` | `"yes"` (a person starts each phase) or `"no"` (something already starts the next phase) |
| `symptoms` | An object with exactly the eight keys below, each a number or the string `"not measured"`. The first is a share from 0 to 1; the seven others are counts, so whole numbers (3 or 3.0, never 0.5), of any size |

A **symptom** is a row of the last table of report §7, copied in decide.md section 3. A symptom **fires** when its value is a number above its threshold. Only one threshold is written in the report ("more than about one run in ten"). Where none is written, the rule is: **any measured occurrence above zero is named**. One row is the exception: the report says "many steps" and gives no number, and one step is not many. That row **never fires**: a number above zero is listed for the person to judge. The answers are not checked against each other: 3 double runs on a path with 0 tickets a week is read as written.

| Key in `symptoms` | The number is | Fires above | An engine removes it |
|---|---|---|---|
| `runs_paid_twice` | the share of runs that died far in and were paid twice, from 0 to 1 | 0.1, written in the report | yes |
| `double_runs` | the number of tickets that had two runs at once | 0 | yes |
| `silent_events` | the number of events that were accepted and then lost without a word | 0 | yes |
| `agent_loops` | the number of runs where the agent looped until something outside stopped it | 0 | no: "an engine retries it faithfully" |
| `waits_inside_computation` | the number of waits that must resume inside an expensive multi-step computation | 0 | yes |
| `steps_with_own_retry_rule` | the number of steps that need a retry or timeout rule of their own | never: no number in the report | yes, if the person judges them many |
| `order_breaks` | the number of events from several systems that were handled out of order | 0 | yes |
| `tickets_without_cost` | the number of tickets whose cost nobody can give | 0 | no: any runtime with a run record gives it |

**The rules**, in order; the first that applies decides:

| # | When | Verdict (`verdict.code`) | Source printed |
|---|---|---|---|
| 0 | The file is not an object; a key is missing; a value is not allowed (a boolean and a negative number are not numbers here, a share is at most 1, a count is whole); a key is not one of the above; a key is written twice, at top level or under `symptoms` (the last one is not taken) | Refused, exit 1: one line per answer to fix, each naming the key. Never a guess | - |
| 1 | `building` is not `ticket_workflow` | `tool`: the choice of that row of report §8 (`own_agent_app` "LangGraph, or an agent SDK plus an engine"; `agent_product` "A durable engine under a plain loop"; `many_repositories` "A script and a CI matrix, one PR per repository"; `long_lived_orchestrator` "Rust is reasonable"). The symptoms describe a ticket workflow: here they are checked, and each one above its threshold is listed in `not_deciding`; they do not decide | report §8, that row; §2.7, §5.2, §7 or §4.5 |
| 2 | At least one symptom fires | `symptom`: every symptom that fired, in table order, with its number, its threshold, its smallest fix and what removes it by design. An engine is named only as what comes next if the symptom stays after its fix, and only when it removes one of them | report §7, last table; §8, second row; decide.md §3 |
| 3 | `chained_by_hand` is `yes` and `tickets_per_week` is 0 | `by_hand`: "By hand with the ai-sdlc skills may be enough: no ticket goes through this path yet." | decide.md §7, quoted: "Chaining the steps by hand may be enough" |
| 4 | Otherwise | `ticket_state_and_ci`: "Ticket state and CI are enough." | report §8, first row; §7, last table |

Rule 3 uses zero as this command's own rule, and prints that it is: neither the guide nor the report gives a number of tickets a week under which chaining by hand is enough, and the guide says only "may be enough". `"not measured"` never fires and is never counted as fine: every verdict lists those symptoms.

**The output.** `fit(answers)` of `flow_fit.py` returns the `fit` document, which `--format json` prints: `{"passed", "problems", "verdict": {"code", "sentence"}, "building", "tool", "why", "fired", "not_deciding", "not_measured", "would_change", "source"}`. `tool` is the choice of rule 1, otherwise null. An entry of `fired` is `{"key", "symptom", "value", "above", "written", "smallest_fix", "removed_by", "engine"}`; `written` is the report's own words for the threshold, or null when the zero rule applies. An entry of `not_deciding` is an entry of `fired` plus `"reason"`: `not_a_ticket_workflow` (rule 1: a number above its threshold, or above zero for the row with none), or `no_threshold` (`steps_with_own_retry_rule` above zero on a ticket workflow; its `above` is null). So an empty `fired` never hides a number. An entry of `not_measured` is `{"key", "symptom"}`. `would_change` is the measurable fact that would change the answer. Refused answers give `{"passed": false, "problems": [{"code", "key", "message"}], "verdict": null}`, with `code` one of `not_an_object`, `missing`, `unknown_value`, `unknown_key`, `duplicate_key` and `key` dotted (`symptoms.double_runs`); problems come in the order of the keys above, then the unknown keys, then the keys written twice. A message shows a key or a value as JSON would write it, on one line, control characters escaped. A key written twice can only be seen in the text: `parse(text)` of `flow_fit.py` keeps it for `fit`, and the command reads its input with it.

For a person: "Verdict: ‹sentence›", "Why: ‹why›", one line per symptom that fired, one line per entry of `not_deciding` ("‹key› is ‹value›: listed, it did not decide."), "What would change this answer: ‹would_change›", "Source: ‹source›.", then the symptoms not measured. One note on stderr with `--format md`: after `ticket_state_and_ci`, "Next: flow new feature or flow new bug writes a starting definition."; after a refusal, "The questions and the allowed values: flow fit --questions".

`flow fit --questions` prints each key with its question and allowed values, each symptom with what its number counts and its threshold, and an example file; with `--format json`, `{"facts_date", "not_measured", "questions", "symptoms", "example"}`, where a symptom's `above` is null for the row that never fires. The example is a complete answers file.

**Three examples.** In each, the symptoms not shown are 0.

1. `{"building": "ticket_workflow", "tickets_per_week": 12, "chained_by_hand": "yes", "symptoms": {"runs_paid_twice": "not measured", "agent_loops": "not measured", "tickets_without_cost": "not measured", …}}`, exit 0:

```
Verdict: Ticket state and CI are enough.
Why: 12 tickets a week go through this path and the phases are chained by hand. The ticket or the pull request holds the state, and a short CI job runs each step. No measured symptom is above its threshold.
What would change this answer: One symptom measured above its threshold on your own runs: runs_paid_twice above 0.1, any other above 0, except steps_with_own_retry_rule, which has no threshold and is yours to judge.
Source: report §8, first row; report §7, last table.
Not measured, so not counted as fine: runs_paid_twice (Runs die far in and pay their tokens twice); agent_loops (An agent loops and burns tokens); tickets_without_cost (You cannot say what a ticket cost).
```

2. `{"building": "ticket_workflow", "tickets_per_week": 40, "chained_by_hand": "no", "symptoms": {"runs_paid_twice": 0.05, "double_runs": 3, …}}`, exit 0:

```
Verdict: A symptom is measured above its threshold: double_runs is 3, above 0.
Why: On a ticket workflow, a measured symptom is the only thing that calls for more than ticket state and CI. Try the smallest fix first; move on only when the symptom is still there.
- double_runs is 3, above 0: the report writes no threshold, so any measured occurrence above zero is named. Two runs on one ticket. First try: One run at a time per ticket; keys derived from the ticket, never random. What removes it by design: An engine with one workflow per ticket.
What would change this answer: Each symptom named above back at or under its threshold after its smallest fix: then ticket state and CI are enough. If one stays, the report's choice is a managed engine (Temporal Cloud), one workflow per ticket; the worker can be Rust.
Source: report §7, last table; report §8, second row; decide.md §3.
Not measured: nothing. Every symptom has a number.
```

3. `{"building": "chatbot", "chained_by_hand": "yes", "symptoms": {…}}` where `tickets_per_week` and `symptoms.double_runs` are absent, exit 1:

```
Refused: 3 answers to fix. No verdict is given on a guess.
- "building" is "chatbot": write "ticket_workflow", "own_agent_app", "agent_product", "many_repositories" or "long_lived_orchestrator".
- Add "tickets_per_week": a number, 0 or more.
- Add "double_runs" under "symptoms": a whole number, 0 or more, or "not measured".
```

`fixtures/flow/fit/<name>/` holds `answers.json`, a file the command reads as it is, and `expected.json`: `{"about", "exit", "verdict", "tool", "fired", "not_deciding", "not_measured", "refused"}`, where `verdict` is the code or null, `fired`, `not_deciding` and `not_measured` are lists of symptom keys, and `refused` is the list of keys the refusal names. `cli/tests/test_flow_fit.py` runs each through the command line.

## Choices made here

- **A state is a step**, and there are five step types: a person who decides (`gate`) is told apart from a person who works (`human`), because only the first needs a judge and something to read.
- **The stop point sits on a transition** (`reaches`), not on a state: a state can be left by a failure, and that must not count as reaching the stop point. It is checked on one path only: `check` asks that some reachable transition reaches it, not that every path to a later write crosses it. The reviewers asked for more; a branch that goes around the stop point is a design a person must read, and `flow status` shows where the flow stops.
- **The event type carries the outcome.** No condition on payload values. So every step that can fail, refuse or find its facts changed has an event for it: `flow check` asks two ways out of a gate and of a premise check, and `step_failed` and `deadline_passed` exist everywhere without being declared.
- **Three built-in events, one reason each.** A passed deadline gives the reason `deadline_passed` in every state, gate or not.
- **A cap counts entries into a state over the whole run**, never reset, and the templates put it on the step that costs.
- **Twelve refusal codes.** The proposal's seven, with "no judge or no deadline" split in two, plus `malformed`, a deadline on waits, a gate that cannot refuse and a gate that shows nothing.
- **An ended run is tested first.** A run whose `state` is `done` or `stopped` answers `run_ended` to everything, a known id included, whatever its other keys hold: once ended, nothing is read and nothing moves.
- **A refused event costs nothing and stays out of `seen`.** A reviewer asked to count the costs of refused events. Kept as it was, because a refused event must be deliverable again (it may be early), and counting it at each delivery would count it twice. The spending is seen another way: an event that ends a program or agent step is refused without its two costs, and `step_failed` gives every such step an event that fits.
- **`at` names a state and a visit**, not a visit alone: `deadline_passed` belongs in every state, so a visit number alone could match another state by chance. A type that does not belong is refused before `at` is read, so `stale_event` always means "right kind of answer, wrong round".
- **The budget is tested after the transitions that end the run.** A last event that passes the budget still ends with `done` or with the transition's own reason, and `over_budget` says so: the record must not say "stopped" about work that finished. `budget_exceeded` means the flow would have gone on. Landing exactly on the budget is within it.
- **After a wait or a person's work, the next program checks its facts; after a gate, only when that program writes outside.** Approving a plan and coding on it changes nothing outside until a later step that writes. A premise check several steps after a wait is not asked for.
- **A gate shows something a step wrote.** `shows` is matched as text against the `writes` of the other states; that the write happens before the gate on every path is not proved.
- **The key of a write is derived from the ticket when it contains `{ticket}`**, and one key names one thing. A program cannot prove more on paper.
- **A human stop wins over caps, budget, `at`, the transition table and the list of ids already seen**, not over an inconsistent run or an ended one. And `flow next` never invents a run: `--run` or `--new`, one of the two.
- **The grid extension is its own small tree** of seven questions and nine destinations, in the format of `placement.json`. The proposal's six new destinations are kept; `code`, `skill` and `dated_skill` are added so every step lands somewhere. "A hook" and "a CI job" stay answers of `harness place`. The guide documents these seven questions, not the report's eight.
- **Whether a judge can judge is an answer recorded in the file** (`can_judge`), given by a person; when it is absent the step is open, and that keeps the flow at level 0. A gate nobody can judge fails `flow place` and level Mapped; needing an engine fails neither: it is a place.
- **Exit codes are 0, 1, 2 everywhere**; the 3 of `harness place` for a missing answer is not reused. `flow status` takes a file: a missing file is exit 2, not level 0; level 0 is a file that does not pass.
- **Templates are data files** in `cli/harnesslib/flow_templates/`. The feature template starts at "ready for agent"; the readiness check before it stays the `ticket` skill of `ai-sdlc`.
- **Fifteen sequences plus two twins**: the nine of the proposal, the full feature path, a gate deadline, the CI loop of the bug flow, and three for what the reviews added (a lost event, a failed step, a stale answer).

## Settled while building

The four parts were built apart, then put together; the fixtures, written without seeing the code, all agreed with it. What this page left open and the builders settled, so that the next reader does not have to guess:

- **One fault, one `malformed` problem**, so several problems may share a `where`. A state whose `type` is unknown is also left out of the two `malformed` cases that depend on the type (`checks_premise` and `step_failed` on a state that is not `code` or `agent`): the person is told the type is wrong, once.
- **`stop_at: null` and `writes: null` are present and of the wrong type**: `malformed`, not `no_stop_point`.
- **A mistyped target is one line** (section 2): steps no path leads to are told only once every target is a step.
- **A transition to `done` that also carries `reaches` equal to `stop_at` ends by rule 10**, with the transition's reason or `finished`: rule 10 comes before rule 11.
- **In rule 3, `visits` is well formed when it is an object of integers at or above 0 keyed by declared states.** A count above its cap makes the run inconsistent, and the counts are kept as given.
- **A state never entered** may be absent from `visits` or present with 0; the fixtures accept both.
- **Under rules 1 and 2, `remaining` and `over_budget` are computed** whenever the run given has a well-formed `spent`.
- **`flow new` on an existing file** prints nothing on stdout and one sentence on stderr that names `--force`.
- **`flow status` without `--map`** begins with "This flow is at level ‹n› (‹name›)." At level 0, the map prints the block "What level 1 still needs:" in place of the line about levels 2 to 4, and the flow line says in words what is unreadable ("no stop point", "no budget for one ticket").
- **`flow place`, lines this page did not fix**: an open step is printed "- ‹state› (‹type words›): cannot be placed yet. No answer to "‹question text›" (key ‹key›)."; the verdict line is "Verdict: " and the verdict sentence with its first letter lowered; several engine steps are joined by "; " and the reason is given once. A step value is matched exactly against `from.map`: "Yes" is no answer.
- **The reference templates sit in `fixtures/flow/definitions/`** (`feature.json`, `bug.json`) beside `every-case.json`, and two sequences were added on `every-case.json` (`every-case-retry`, `every-case-finished`): nothing else records a declared `step_failed`, a declared `deadline_passed` or `finished`. A sequence entry may carry a `note` in plain words; no test reads it.
- **The guide has two sections more than section 9 lists**, before its closing one: the two templates placed step by step, and what the guide does not decide. `test_flow_guide.py` also compares those two tables with what `flow place` answers on the templates.
- **A file that holds `NaN` or `Infinity` is read** (Python's `json` accepts them); such a value is then not a number for `check` and `next_state`.

## After the reviews

Three reviewers examined the slice as built: one read the rules, one the fixtures, one used the commands as a tech lead would. What changed, and what did not.

**Four rules changed.**

- **A retry on a deadline is paid** (rule 8). A `deadline_passed` declared on a program or agent step towards a step started work again without a cost: six rounds, nothing spent. It now says what the round cost. The deadline nobody declared, and the one that ends the run, still need none.
- **No cost vanishes.** Rounding the total after each event made 0.00004 disappear, a hundred times over. Each cost is now rounded up to 4 decimals before it is added. The stored values stay rounded to 4 decimals.
- **A human stop is never a duplicate** (rules 4 and 5). An id reused by a stop made the stop a no-op with exit code 0. One reviewer asked for the opposite answer to be recorded (`duplicate`); the safety valve won, and `human-stop-known-id` records `stopped`.
- **The stop point cuts the graph** (sections 1 and 2). `check` treated the transition that reaches the stop point as an ordinary edge: it refused a circle that cannot repeat, and accepted a gate shown something only a step that never runs writes. The steps behind the stop point are still accepted (a team writes them in advance), and the commands now say which they are.

**What a person reads changed** (section 4): every problem of `flow check` ends with the key to write; `flow next` shows an event in its help, names the key in each refusal and writes the run with `--save-run`; `flow place` says a wrong value from a missing one and lists every key a step lacks; `flow new`, `check`, `place` and `status` end with where a run really stops and what comes next.

**Kept as it was, and why.**

- **The words "The file cannot be read as a flow:"** before each `malformed` problem. A reviewer read them as a parse failure on a file that was read without trouble. They are fixed by section 2, and three tests written with the first slice pin them and the exact lines `flow check` prints. Each such problem now ends with what to do instead (a step nobody leads to: "point the "to" of an event of an earlier step at it"; a mistyped target: "did you mean "verify"?").
- **The notes are on stderr**, not in the answer: the answers on stdout are fixed by section 4 and compared to the letter by the first slice's tests.
- **`--run FILE` does not accept a whole answer of `flow next`.** The run is still stopped as inconsistent (rule 3), and the line on stderr now names `--save-run`. A file that is not a run is never guessed into one.
- **`flow status` exits 0 at level 0**: a level is a fact, not a failure.
- **`flow check` does not refuse a value `flow place` cannot read** (`"can_judge": true`). Those keys are read by `flow place`, which now says the value is wrong and what to write; `flow check` says in a note when the placement does not pass.
- **The stop point `root_cause` of the bug template keeps its name**, although a step has the same one: the template is fixed by section 1. The commands and the two guides now say "a run stops after `notify`".
- **No key for the model and the date of a dated skill.** The guide says where to write them today and that nothing checks it.
- **`counts-over-cap` has no `visits`**: a sequence may not state a count above a cap. "The counts are kept as given" is pinned by a unit test.
