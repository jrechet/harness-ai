# harness-flow, first slice: the contract

Date: 2026-11-22, revised after two reviews, then when the four parts were put together ("Settled while building"), then after three reviews of the slice as built ("After the reviews", at the end), then after the reviews of the three skills built on it (section 12, issue #165). Issue #143. This page fixes what the first slice of [proposal.md](proposal.md) (sections 3 and 8.1) builds, exactly enough for four people to build it apart: the core module, the placement, the fixtures, the guide. Where this page and the proposal differ, this page wins for this slice; the differences are listed in "Choices made here".

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
| `irreversible` | list of stop point names | no | The stop points whose write to the outside cannot be taken back; absent, `merged` and `deployed`. `flow check` asks that no run reaches one without crossing a gate that guards it, and refuses a name written here that no transition reaches (section 12.2) |
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
| `can_judge` | `yes` or `no` | no (`gate`) | Can the judge really judge what they approve? Read by `flow place`. A person's answer: no template writes it, and a gate without it waits for its judge (section 12.1) |
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

`flow new` writes them; the fixtures replay events on them, so their states, events, caps and writes are fixed here. Read a cell `event → target [stop point] (reason)`. In both: every `code` and `agent` state has `survives: restart`, `units: one`, `repositories: one`; every `agent` state has `weak_model: no`; every `gate` has a `judge` and `deadline_hours` 72, and no `can_judge` (section 12.1: the team answers, not the template); `ci_wait` has `deadline_hours` 6, the other waits 168. The `does` sentences and the `judge` wording are the core author's, from report.md section 6. A state not named in a "Writes" line writes nothing outside: what an agent or a check produces travels in its event and is written by the next program.

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

A thirteenth code, `irreversible_without_gate`, comes last in this order: a write that cannot be taken back, which a run can make without crossing a gate that guards it. Its row, and how the path is read, are in section 12.2.

The `malformed` cases and their `where`:

- `""`: the definition is not an object.
- The key itself (`format`, `name`, `start`, `states`, `stop_at`, `irreversible`): `irreversible` is present and not a list of names, or names a stop point no transition reaches (section 12.2); `format` is not the integer 1; `name`, `start` or `states` is missing or of the wrong type; `name` is not a name; `start` is not a declared state; `states` is empty; `stop_at` is present and not a name.
- `states.‹state›`: the state's name is not a name, or is `done` or `stopped`; the state is not an object; `does` is missing or not a non-empty string; `on` is missing, not an object or empty; `cap` is not an integer above 0; `writes` is not a list of objects; `checks_premise` is not a boolean, or is true on a state that is not `code` or `agent`; no path of transitions leads from `start` to the state. This last case is not reported while `start` is not a declared state or some transition names a target that is not a declared state, `done` or `stopped`: the path is broken there, and one mistyped name must stay one line, not one per step behind it.
- `states.‹state›.on.‹event›`: the event type is not a name; the transition is not an object with a `to`; `to` is not a declared state, `done` or `stopped`; `to` is `stopped` without a `reason`; `reason` or `reaches` is present and not a name; the event is `human_stop`; the event is `step_failed` on a state that is not `code` or `agent`.

Exit codes of the command: 0 no problem, 1 at least one problem (a file that holds a JSON list or string is `malformed`, exit 1), 2 the file is missing or is not JSON. A key written twice in one object is exit 2 too, for a definition, an event or a run: the file does not say one thing, and JSON would keep its last value without a word. The message is "flow: ‹file›: the key "‹key›" is written twice in one object; JSON keeps only the last one, without a word. Write it once." (`flow_read.once`, the hook `flow.load_definition` reads with).

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

**Answers and notes.** What a command answers is on stdout, in the form of the table below. What helps a person go on is a note: one sentence per line on stderr, after the answer, and only with `--format md`; with `--format json` stdout holds the document and stderr nothing. The notes: where a run really stops ("As written, a run stops on purpose after ‹step›: the stop point "‹stop_at›" (stop_at) is the name its transition reaches, not a step. The ‹n› steps after it are described but not run… To go further, set stop_at to ‹later stop points›."), printed by `flow new`, by `flow check` when the flow holds and by `flow status` at level 1; the command that comes next ("Next: …"); and what the other command would say of the same file (below). `flow --help` gives the six steps of the work in order, and `flow next --help` shows an event file. Section 12 adds notes and fixes how they name things: a gate that waits for its judge (12.1), what `flow check` cannot see (12.2), a command in its short form and a page by its file name, with one closing note that gives the command as this installation runs it and the folder of the pages (12.4), and whether measured symptoms were read (12.5). Section 12.4 also fixes the order of the notes of one command, that `flow_cli` prints them all, and that help, which is on stdout, carries no path.

One rule for the four commands that read a definition: a file that is missing or is not JSON is exit 2; any JSON value is then handed on as it is. A value that is not a flow is `malformed` for `flow check` (exit 1), level 0 for `flow status` (exit 0), and exit 2 for `flow next` and `flow place`, as said in their rows.

Wherever a step type is shown to a person, these words are used (`flow.TYPE_WORDS`): `code` "a program", `agent` "an agent", `human` "a person works", `gate` "a person decides", `wait` "waits". An unknown type is printed as written.

| Command | Prints for a person | `--format json` | Exit 1 when |
|---|---|---|---|
| `flow new <feature\|bug> [--out FILE] [--force]` | "Written: ‹path›", then the steps in order, one line each: "- ‹state› (‹type words›): ‹does›"; the line of a step after which a run stops on purpose ends with "   ← as written, a run stops here on purpose". Default path `.harness/flow/<kind>.json` under the current directory; folders are created | `{"file", "definition"}` | the file exists and `--force` is absent (nothing written) |
| `flow check <file>` | "This flow holds: ‹n› steps, it stops at ‹stop_at›, one ticket may cost up to ‹dollars› dollars and ‹minutes› minutes." then the figures that bound one run (section 12.2); or one line per problem: "- ‹sentence› (‹where›)" | `{"file", "passed", "problems", "bounds"}` | a problem is found |
| `flow next <file> --event FILE (--run FILE \| --new) [--save-run FILE]` | The `message`, then "State: ‹state›. Spent: ‹dollars› dollars, ‹minutes› minutes. Left: ‹dollars› dollars, ‹minutes› minutes." | the output document of section 3 | the outcome is `refused` or `stopped` |
| `flow place <file> [--answers FILE]` | Section 6; with `--answers`, the measured symptoms in the verdict (section 12.5) | the `place` document | a step cannot be placed, or a gate cannot be judged by anyone |
| `flow status <file> [--map] [--answers FILE]` | Section 7, and sections 12.2 and 12.5 | the `status` document | never: a level is a fact, not a failure |

- `flow next` needs exactly one of `--run FILE` (the run returned by the call before) and `--new` (the first event of a ticket: the run is `new_run`); neither or both is exit 2. A run nobody passed back is never silently replaced by a fresh one.
- `flow next --save-run FILE` writes the `run` of the answer to FILE, whatever the outcome, so that the next call takes it with `--run FILE`; the same file may be given to both. A file that cannot be written is exit 2, and nothing is printed on stdout. A note then gives the next command, or says the run has ended. Without `--save-run`, a first event (`--new`) that moves ends with a note saying the run was not saved.
- `flow check` and `flow place` answer two questions and each can pass while the other fails: a gate with `can_judge: no` passes `check`, a gate that shows nothing can be placed. Each says so in a note. `flow check`, when the flow holds: "Next: flow place ‹file›…" or, when `place` does not pass, "Careful: flow place ‹file› does not pass on this file…", except when it fails only because gates wait for their judge (section 12.1). `flow place`, when `check` finds problems: "Careful: flow check ‹file› finds ‹n› problem(s) in this file, so this placement is provisional…"; otherwise, when it passes, "Next: flow status ‹file› --map".
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
| `status(definition, placement=None, measured=None) -> dict` | Section 7; `measured` is what `flow_fit.measured` returns (section 12.5). `placement` is a `place` document; when `None` and the definition is not `malformed`, `flow_place.place(definition)` is imported and called at that moment |
| `render_map(state) -> str` | The map of section 7, from a `status` document |
| `build_parser(parser=None)`, `main(argv=None, args=None) -> int` | As the other modules of `cli/harnesslib`: `harness.py` adds `flow.build_parser(sub.add_parser("flow", …))` and calls `flow.main(args=args)`. The `place` subcommand is declared here (`file`, `--format`, `--answers`) and handed to `flow_place.main([file, "--format", fmt])`, with `--answers FILE` when given, imported at that moment; its return value is the exit code |

`status`, `render_map`, `build_parser` and `main` are kept in `flow.py` as its interface; their bodies are in `flow_status.py` and `flow_cli.py`, loaded when first called.

Constants: `STEP_TYPES = ("code", "agent", "human", "gate", "wait")`, `ENDED = ("done", "stopped")`, `TEMPLATES = ("feature", "bug")`, `BUILT_IN_EVENTS = ("human_stop", "deadline_passed", "step_failed")`, and `TYPE_WORDS`, the dict of section 4.

`cli/harnesslib/flow_place.py`:

| Function | Returns |
|---|---|
| `load_grid(path=GRID_FILE) -> dict` | `flow_placement.json` |
| `fix_of(grid, step) -> str \| None` | What to write in a step that cannot be placed (section 6); `None` once it can |
| `place(definition, measured=None) -> dict` | The `place` document of section 6, with the key `measured` of section 12.5. Raises `ValueError` if the definition is not an object or its `states` is not an object of objects; otherwise places what it finds without running `check` |
| `main(argv=None) -> int` | `flow place`: arguments `file`, `--format md\|json` and `--answers FILE`. Loads the file with `flow.load_definition` and uses `flow.TYPE_WORDS`; exit codes as in section 4. It prints the answer only: the notes of `flow place` are printed by `flow_cli` (section 12.4) |

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
 "passed": true, "measured": null}
```

`steps` follows the file order of `states`, one entry per state. `shows` is the step's `shows` when it is a non-empty string, otherwise null. A step with a missing answer has `status` `open`, `destination`, `name`, `says`, `decided_by` and `reason` null, `path` as far as it went, and `missing` `{"question", "text", "key"}`: the question that has no answer and the step key that would answer it. An open step also carries `fix`, one sentence that says what to write: 'Add "survives": "restart" or "midway".' when the key is absent, '"survives" is "hours": write "restart" or "midway".' when its value is not one the grid reads, then 'Also needed: "units" ("one" or "many"), …' for every other key the walk would ask for if it went on by the answer that leads to the next question. Nothing more is supposed of a step whose `type` is unknown. A placed step has no `fix` key. An unknown `type` leaves the step open at `who`. `decided_by` is the last entry of `path`, with the question's text. `engine`, `refused_gates` and `open` list the states sent to `durable_engine`, sent to `no_gate`, and left open, in file order. `verdict.code` is `open` if a step is open, otherwise `engine` if `engine` is not empty, otherwise `no_engine`. `passed` is true when `open` and `refused_gates` are both empty: needing an engine is an answer, not a failure. A fourth code, `symptom`, exists only when measured symptoms are read with `--answers` (section 12.5).

**For a person**, one line per step, then the verdict, then the refused gates. A gate's line ends with what its judge is shown, when the file says it:

```
- coding (an agent): a skill is enough. Decided by "Is this step here because today's model is weak?": no.
- approval (a person decides): this is a human gate. Decided by "Can the person who approves really judge what they approve?": yes. Shown to a maintainer of the repository: the branch.

Verdict: no step needs an engine.
```

The other verdict sentences: "One step would need an engine: ‹state›, ‹does›. ‹reason›" (or "‹n› steps would need an engine: …"); "‹n› step(s) cannot be placed yet: ‹state› has no answer to "‹question text›" (key ‹key›)". For each refused gate, one more line: "A gate nobody can judge: ‹state›. Remove it, or give ‹judge› something they can read and refuse.", except for a gate the flow cannot lose, and while a fault hides the paths (section 12.2).

## 7. `flow status --map`: level Mapped, on paper

The ladder of proposal section 5. This slice measures level 1 only, from the file alone. `status(definition, placement)` returns:

```json
{"flow": "small", "steps": 8, "stop_at": "draft_pr", "budget": {"dollars": 5, "minutes": 60},
 "level": {"reached": 1, "name": "Mapped", "next": 2},
 "checks": [
  {"id": "definition_holds", "passed": true, "origin": "flow check", "plain": "the flow is written down and holds together", "detail": []},
  {"id": "steps_placed", "passed": true, "origin": "flow place", "plain": "every step has a place", "detail": []},
  {"id": "stop_and_budget", "passed": true, "origin": "the definition file", "plain": "a stop point and a budget are set", "detail": []}],
 "next_step": "Nothing more on paper. The next level needs the flow to run on real tickets, which this version does not do yet.",
 "waiting": [],
 "bounds": {"budget": {"dollars": 5, "minutes": 60}, "irreversible": ["merged", "deployed"], "irreversible_declared": false, "taken_back": ["draft_pr"],
            "circles": [{"steps": ["coding", "checks"], "caps": {"coding": 3}, "most_entries": 3}], "guards": []},
 "measured": null}
```

- `definition_holds` passes when `check(definition) == []`; `detail` holds the problems' sentences.
- `steps_placed` passes when the placement's `passed` is true (no open step, no gate nobody can judge); `detail` holds one sentence per open step, "The step ‹state› has no answer to "‹question text›" (key ‹key›).", then one per refused gate, the line `flow place` prints for it, with the judge read from the definition ("its judge" when it names none).
- `stop_and_budget` passes when `check` returns neither `no_stop_point` nor `no_budget`; `detail` holds those sentences.
- When the definition is `malformed`, `steps_placed` and `stop_and_budget` both fail with the one detail "the file cannot be read as a flow", and `place` is not called.

`reached` is 1 when the three pass; otherwise `level` is `{"reached": 0, "name": "None", "next": 1}`, where `"None"` is the string, the name of level 0. `next_step` at level 0 is the first sentence of `detail` of the first failing check, introduced by "Fix this first: ". `flow`, `steps`, `stop_at` and `budget` are JSON null when unreadable. Section 12 adds three keys to the document, `waiting` (12.1), `bounds` (12.2) and `measured` (12.5), and one other `next_step` at level 0, when the first thing missing is a judge's answer (12.1).

`flow status <file> --map` prints `render_map(state)`, in the style of `harness status --map`: the ladder with "you are here", then the flow in one line, then what the next level needs, then the next step. No check id is printed. Level 0 is not listed once level 1 is reached.

```
Where this flow stands, level by level:
✓ 1 Mapped      the flow is written down and every step has a place   ← you are here
· 2 Shadow      the flow runs on real tickets and only comments
· 3 Drafting    runs end with a draft PR; CI and review results come back to the run
· 4 Delivering  runs reach a reviewed PR and merge only on a human's word

This flow: small, 8 steps, stops at draft_pr, up to 5 dollars and 60 minutes for one ticket.
What bounds one run (figures for you to read: no threshold is applied to them):
- Spending: a run is stopped at the first event that takes it past 5 dollars or 60 minutes. It can pass them by the cost of one step, which the file does not bound.
- The circle coding, checks: its capped steps can be entered 3 times in all at most (cap of coding 3).
- Cannot be taken back: merged, deployed (the default: the file has no "irreversible").
- The file treats as possible to take back: draft_pr.
- No transition of this file reaches "merged": if a step of yours does that write under another name, flow check does not know it; write that name under "irreversible".
- No transition of this file reaches "deployed": if a step of yours does that write under another name, flow check does not know it; write that name under "irreversible".
Levels 2 to 4 are read from real runs. Nothing measures them yet.
Next step: Nothing more on paper. The next level needs the flow to run on real tickets, which this version does not do yet.
```

Since section 12 the document also ends with `"waiting"`, `"bounds"` and `"measured"`, in this order, and the map has the bounds block of section 12.2 after its "This flow: …" line, at level 0 too whenever `flow check` passes, then the line of section 12.5 when answers were read.

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

A **definition reference** is `template:feature`, `template:bug` (the test calls `flow.new`), or a path relative to `fixtures/flow/`. In the format tests, which run without the code, a template reference is read as `definitions/<kind>.json` with `can_judge` removed from every gate (section 12.6).

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
| `feature` | `definitions/feature.json`, the feature flow with its gates answered (section 12.1: a template has no answer) | Every step placed; `no_engine`; `passed` true |
| `bug` | `definitions/bug.json` | The same |
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

When every symptom is `"not measured"`, the `why` of `ticket_state_and_ci` ends "Nothing was measured on your own runs, so nothing is known from them." in place of saying that no measured symptom is above its threshold, as `flow place --answers` says of the same file (section 12.5). Rule 3 uses zero as this command's own rule, and prints that it is: neither the guide nor the report gives a number of tickets a week under which chaining by hand is enough, and the guide says only "may be enough". `"not measured"` never fires and is never counted as fine: every verdict lists those symptoms.

**The output.** `fit(answers)` of `flow_fit.py` returns the `fit` document, which `--format json` prints: `{"passed", "problems", "verdict": {"code", "sentence"}, "building", "tool", "why", "fired", "not_deciding", "not_measured", "would_change", "source"}`, plus `"cost"` (section 12.3). `tool` is the choice of rule 1, otherwise null. An entry of `fired` is `{"key", "symptom", "value", "above", "written", "smallest_fix", "removed_by", "engine"}`; `written` is the report's own words for the threshold, or null when the zero rule applies. An entry of `not_deciding` is an entry of `fired` plus `"reason"`: `not_a_ticket_workflow` (rule 1: a number above its threshold, or above zero for the row with none), or `no_threshold` (`steps_with_own_retry_rule` above zero on a ticket workflow; its `above` is null). So an empty `fired` never hides a number. An entry of `not_measured` is `{"key", "symptom"}`. `would_change` is the measurable fact that would change the answer. Refused answers give `{"passed": false, "problems": [{"code", "key", "message"}], "verdict": null}`, with `code` one of `not_an_object`, `missing`, `unknown_value`, `unknown_key`, `duplicate_key` and `key` dotted (`symptoms.double_runs`); problems come in the order of the keys above, then the unknown keys, then the keys written twice. A message shows a key or a value as JSON would write it, on one line, control characters escaped. A key written twice can only be seen in the text: `parse(text)` of `flow_fit.py` keeps it for `fit`, and the command reads its input with it.

For a person: "Verdict: ‹sentence›", "Why: ‹why›", one line per symptom that fired, one line per entry of `not_deciding` ("‹key› is ‹value›: listed, it did not decide."), "What would change this answer: ‹would_change›", "Source: ‹source›.", then the symptoms not measured. The cost lines of section 12.3 come between "Source" and the symptoms not measured. Notes on stderr with `--format md`: after `ticket_state_and_ci`, the "Next: flow new feature --out …" sentence of section 12.4; after `symptom`, the "Next: with a flow definition, flow place …" sentence of section 12.4; after a refusal, "The questions and the allowed values: flow fit --questions".

`flow fit --questions` prints each key with its question and allowed values, each symptom with what its number counts and its threshold, and an example file; with `--format json`, `{"facts_date", "not_measured", "questions", "symptoms", "example"}`, where a symptom's `above` is null for the row that never fires. The example is a complete answers file.

**Three examples.** In each, the symptoms not shown are 0. A test compares them with what the command prints, so examples 1 and 2 get their cost lines (section 12.3) in the commit that makes the command print them.

1. `{"building": "ticket_workflow", "tickets_per_week": 12, "chained_by_hand": "yes", "symptoms": {"runs_paid_twice": "not measured", "agent_loops": "not measured", "tickets_without_cost": "not measured", …}}`, exit 0:

```
Verdict: Ticket state and CI are enough.
Why: 12 tickets a week go through this path and the phases are chained by hand. The ticket or the pull request holds the state, and a short CI job runs each step. No measured symptom is above its threshold.
What would change this answer: One symptom measured above its threshold on your own runs: runs_paid_twice above 0.1, any other above 0, except steps_with_own_retry_rule, which has no threshold and is yours to judge.
Source: report §8, first row; report §7, last table.
Cost, from the pages, facts of 2026-11-21 (nothing here is measured on your runs):
- One agent pass: near one dollar: Cloudflare's code review, mean $1.19 over 131,246 runs; Sentry's fix, $1.00 flat; GitHub's heavy runs, about $1.20. Published [V] [V] [M] (report §5.4; costs.md §1).
- One ticket from start to end: no published figure (report §5.4; report §9.1, item 2).
- One ticket, estimated: $3 to $10 for a feature ticket, $1 to $3 for a simple bug fix. Arithmetic of the notes, not a measurement (report §5.4; costs.md §2).
- One CI minute: $0.006 on a GitHub Actions Linux runner with 2 cores. Published [V] (costs.md §1).
Not measured, so not counted as fine: runs_paid_twice (Runs die far in and pay their tokens twice); agent_loops (An agent loops and burns tokens); tickets_without_cost (You cannot say what a ticket cost).
```

2. `{"building": "ticket_workflow", "tickets_per_week": 40, "chained_by_hand": "no", "symptoms": {"runs_paid_twice": 0.05, "double_runs": 3, …}}`, exit 0:

```
Verdict: A symptom is measured above its threshold: double_runs is 3, above 0.
Why: On a ticket workflow, a measured symptom is the only thing that calls for more than ticket state and CI. Try the smallest fix first; move on only when the symptom is still there.
- double_runs is 3, above 0: the report writes no threshold, so any measured occurrence above zero is named. Two runs on one ticket. First try: One run at a time per ticket; keys derived from the ticket, never random. What removes it by design: An engine with one workflow per ticket.
What would change this answer: Each symptom named above back at or under its threshold after its smallest fix: then ticket state and CI are enough. If one stays, the report's choice is a managed engine (Temporal Cloud), one workflow per ticket; the worker can be Rust.
Source: report §7, last table; report §8, second row; decide.md §3.
Cost, from the pages, facts of 2026-11-21 (nothing here is measured on your runs):
- One agent pass: near one dollar: Cloudflare's code review, mean $1.19 over 131,246 runs; Sentry's fix, $1.00 flat; GitHub's heavy runs, about $1.20. Published [V] [V] [M] (report §5.4; costs.md §1).
- One ticket from start to end: no published figure (report §5.4; report §9.1, item 2).
- One ticket, estimated: $3 to $10 for a feature ticket, $1 to $3 for a simple bug fix. Arithmetic of the notes, not a measurement (report §5.4; costs.md §2).
- The fee of a managed engine: about $50 per million actions on Temporal Cloud, with no base fee. Published [V] (report §3.5; costs.md §3).
- Writing one workflow for an engine: "1-2 days" on average for a custom Temporal workflow at Duolingo. Published [V, self-reported] (report §5.2).
- The people to host an engine yourself: no published figure (report §3.5; report §9.1, item 5).
Not measured: nothing. Every symptom has a number.
```

3. `{"building": "chatbot", "chained_by_hand": "yes", "symptoms": {…}}` where `tickets_per_week` and `symptoms.double_runs` are absent, exit 1:

```
Refused: 3 answers to fix. No verdict is given on a guess.
- "building" is "chatbot": write "ticket_workflow", "own_agent_app", "agent_product", "many_repositories" or "long_lived_orchestrator".
- Add "tickets_per_week": a number, 0 or more.
- Add "double_runs" under "symptoms": a whole number, 0 or more, or "not measured".
```

`fixtures/flow/fit/<name>/` holds `answers.json`, a file the command reads as it is, and `expected.json`: `{"about", "exit", "verdict", "tool", "fired", "not_deciding", "not_measured", "refused"}`, plus `"cost"` (section 12.3), where `verdict` is the code or null, `fired`, `not_deciding` and `not_measured` are lists of symptom keys, and `refused` is the list of keys the refusal names. `cli/tests/test_flow_fit.py` runs each through the command line.

## 12. After the step-2 reviews (issue 165)

Three reviewers of the skills `flow-why`, `flow-map` and `flow-place` found five things the skills' text guarded and the CLI did not. This section is the contract of the change; where it and sections 1 to 11 differ, this section wins. The sentences of sections 1 to 11 it replaces are named under each point and were edited, except the example outputs of sections 7 and 11, which tests compare with what the code prints: they change in the commit that changes the code. New code goes in new modules, `flow.py` being near its size limit: `cli/harnesslib/flow_paths.py` (12.2), `flow_notes.py` (every note sentence of this section), and the data file `flow_costs.json` (12.3). Exit codes stay those of section 4. Every note below is on stderr, with `--format md` only; 12.4 fixes who prints them and in which order. Two critics then challenged this section; what they changed is listed at its end.

### 12.1 The templates no longer answer for the team

**Rule.** No template writes `can_judge`: `flow new feature|bug` gives gates with a `judge`, a `shows`, `deadline_hours` 72 and no `can_judge`. `check(new(kind)) == []` still holds. A gate **waits for its judge** when its `can_judge` key is absent (a value the grid cannot read, `true` or `"Yes"`, is a fault, not a wait: `flow place` says what to write, and no waiting note names it). `flow_place.waiting(definition) -> list[str]` gives those gates in file order, `[]` for a value that is not a flow; it never raises. The level is read on the whole file, the steps behind the stop point included. The files of `fixtures/flow/definitions/` are a team's answered files and keep `"can_judge": "yes"`.

**What each command says.** Stdout of `flow place` is unchanged: a waiting gate is an open step, the verdict is `open`, exit 1. The `status` document gains `"waiting"`, the list above, and its `next_step` changes in one case: when `definition_holds` passes and the first open step of the placement is a waiting gate, it is 'Ask ‹judge› whether they can really read ‹shows› and refuse it, then write "can_judge": "yes" or "no" in the step ‹state›.' (‹judge› is "its judge" and ‹shows› "what they are shown" when the file gives none) in place of "Fix this first: …". The level stays 0 until every gate is answered `yes`. One note, the **waiting note**, is printed by `flow new`, by `flow check` when the flow holds, by `flow place`, and by `flow status` at level 0 with and without `--map`, each time `waiting` is not empty:

> ‹n› approvals wait for their judge's answer: ‹states, comma separated›. Nothing is wrong with these steps: a judge says whether they can really read what they are shown and refuse it, and the answer is written "can_judge": "yes" or "no" in the step. Until then flow place leaves such a step open and the flow stays under level 1 (Mapped).

With one gate it begins "1 approval waits for its judge's answer: ‹state›." When some waiting gates are in `flow.beyond_stop(definition)`, one sentence more ends the note: "Behind the point where a run stops as written, so asked by no run yet: ‹those states›. Level 1 needs an answer there too: moving stop_at must not be what answers for the judge."

**The "Next:" notes.** `flow check`, when the flow holds: when the placement passes, the "Next: flow place ‹file›…" note of section 4; when it fails only because gates wait (no refused gate, and every open step is a waiting gate), "Next: flow place ‹file› says where each step belongs and which approvals still wait. This command does not look at that."; for every other failure of the placement, the "Careful: …" note of section 4. `flow place`: when `flow check` finds a problem, the "Careful: …" note of section 4 and no "Next:"; otherwise "Next: flow status ‹file› --map" when it passes, "Next: flow status ‹file› --map shows what level 1 still needs." when it fails only because gates wait, and no "Next:" for any other failure.

**Example**, a fresh `flow new feature --out f.json`, then `flow status f.json --map` (exit 0). Today this file reads "✓ 1 Mapped … ← you are here".

```
Where this flow stands, level by level:
· 0 None        the phases are chained by hand   ← you are here
[… the rest of the ladder, the line "This flow: feature, 18 steps, …", the bounds block of 12.2, then under "What level 1 still needs:", "- every step has a place" and one line per gate, as today:]
  The step plan_review has no answer to "Can the person who approves really judge what they approve?" (key can_judge). Add "can_judge": "yes" or "no".
Next step: Ask a maintainer of the repository whether they can really read the plan and refuse it, then write "can_judge": "yes" or "no" in the step plan_review.
```

and on stderr: "3 approvals wait for their judge's answer: plan_review, human_review, merge_auth. Nothing is wrong with these steps: […] Behind the point where a run stops as written, so asked by no run yet: human_review, merge_auth. Level 1 needs an answer there too: […]". A fresh bug template: "1 approval waits for its judge's answer: human_review. […] so asked by no run yet: human_review. […]". **Replaces**: section 1, the `can_judge` row and "every `gate` has `can_judge: yes`"; section 4, the `flow check` note when the placement does not pass; section 7, `next_step`; section 8, the definitions of `place/feature` and `place/bug`; `decide.md`, the two tables of the templates placed: they are the tables of the answered files, `test_flow_guide.py` compares them with `place` of `definitions/<kind>.json`, and one sentence above them says a fresh template leaves its approvals open.

### 12.2 `flow check`: a gate before what cannot be taken back, and the figures that bound a run

**New key.** `irreversible`, top level, optional: a list of stop point names, the ones whose write to the outside cannot be taken back; a name written twice is read once. Absent, it is `["merged", "deployed"]`, the names of the two templates, which need not be reached. Present and not a list of names: `malformed`, `where` `irreversible`. An empty list is allowed: the team says nothing is irreversible, and the answer prints that. A name written there that no transition of the file reaches is `malformed` too, same `where`, so that a slip of the pen never switches the rule off in silence: 'irreversible names "mergd", which no transition reaches. Write one of the stop points of this file, or remove the name: ‹the names given by reaches, in file order›.' **New refusal, the thirteenth**, last in the order of section 2:

| Code | Refuses | Sentence printed | `where` |
|---|---|---|---|
| `irreversible_without_gate` | A transition whose `reaches` is an irreversible stop point, whatever its target (`stopped` included: the step made the write), that a run can take without crossing a gate that guards it, read as said below. One problem per such transition, in file order | 'The event ‹event› of the step ‹state› reaches "‹stop point›", which cannot be taken back, and the path ‹start → … → state› crosses no gate that guards it‹why›. Add a step of type "gate" on that path, with an answer that stops the run; or, if a person does this outside the flow and the step ‹state› only waits for it, that step is a person's decision: give it the type "gate", with its judge and what they are shown; or, if your team can take "‹stop point›" back, write "irreversible": [<the stop points it cannot take back>] at the top of the file.' | `states.‹state›.on.‹event›` |

**How the path is read**, for the transition (X, e):

1. If X is a `human` step and e is not `deadline_passed`, a person makes the write: never refused. A `human` step left by such a transition that reaches an irreversible stop point, or `merged` or `deployed` though the file lists them as possible to take back, is a person deciding that write; for the transitions after it, it counts as a gate that guards, crossed by that transition only (a person merges by hand, the pipeline then deploys). The two default names count whatever the list says, so that writing a merge off as possible to take back never turns a flow that holds into one refused. Any other `human` step on the path is a person who works, not one who decides on this write: it counts for nothing. A `human` step's `deadline_passed` passes when nobody acted: it is nobody's decision, never a person's write, guards nothing after it, and when it reaches an irreversible stop point it is read by rules 2 to 4 like the transition of any other step.
2. A run **crosses** a gate when it leaves it by a declared event other than `deadline_passed`. Silence is not a decision: a gate left by its declared `deadline_passed` is read as if it were not there, and a gate whose own `deadline_passed` is e does not guard it.
3. A gate **guards** the stop point S of (X, e) only if it can refuse every write of S: one of its declared events, `deadline_passed` and every event whose transition itself reaches S left aside, leads to `done`, to `stopped`, or to a state from which no transition reaching S can be taken without crossing a gate that guards S. So a gate whose every answer leads to a write of S, through a copy of the write step or by its own `reaches`, guards nothing, and neither does a refusal that leads to another write of S. The gates that guard S are found by striking: every gate at first; each gate that fails this test is struck; again, until none is struck. The person's writes of rule 1 are never struck.
4. (X, e) is refused when a run can go from `start` to X and take e crossing no gate that guards it. X itself counts: when X is a gate that guards and e is not `deadline_passed`, its judge decides and nothing is refused.

The whole graph is read, the steps behind the stop point too: moving `stop_at` must never be the edit that removes the last gate. A state whose type is unknown is no gate and no person, and while any `unknown_step_type` problem exists this refusal is not reported: the type is fixed first, one fault one line. The path printed is the shortest, found breadth first over the transitions a run can follow under rules 2 and 3, states and events in file order. ‹why› is empty, or one parenthesis per gate on that path, in path order: " (it leaves the gate ‹gate› by deadline_passed, when nobody answered)" or " (every answer of the gate ‹gate› leads to this write)"; when X is a `human` step (e is then `deadline_passed`), one more at the end: " (it leaves the person's step ‹X› by deadline_passed, when nobody acted)". `flow_paths.unguarded(definition) -> list[dict]` returns these problems on a definition that is not `malformed`; `flow.check` appends them.

**The bounds.** No threshold is invented for a cap or a budget: the figures are printed for a person to read, and they are part of the answer, not a note, so that `--format json` carries them and a program that keeps stdout only does not lose them. `flow_paths.bounds(definition) -> dict | None`, null unless `check(definition) == []`; for `definitions/feature.json`:

```json
{"budget": {"dollars": 20, "minutes": 240}, "irreversible": ["merged", "deployed"], "irreversible_declared": false, "taken_back": ["plan", "draft_pr", "ready_pr"],
 "circles": [{"steps": ["planning", "plan_size", "plan_review"], "caps": {"planning": 3}, "most_entries": 3}, {"steps": ["coding", "checks", "draft_pr", "ci_wait", "ci_check", "ci_fix", "review_checks"], "caps": {"coding": 6, "ci_wait": 8, "ci_fix": 2}, "most_entries": 16}],
 "guards": [{"stop_point": "merged", "state": "merging", "event": "merged", "last_gate": "merge_auth", "shows": "the pull request", "can_judge": "yes", "steps_between": 0, "agents_between": 0},
            {"stop_point": "deployed", "state": "delivery", "event": "deployed", "last_gate": "merge_auth", "shows": "the pull request", "can_judge": "yes", "steps_between": 1, "agents_between": 0}]}
```

A **circle** is a state with a transition to itself, or a group of two or more states that reach each other, among the states a run can enter, read as `loop_without_cap` reads the graph (transitions that reach `stop_at` cut) but with the capped states kept; groups in file order of their first state, `steps` and `caps` in file order. `most_entries` is the sum of the group's caps: every turn of the circle enters one of its capped states, so no run turns more often. It is an upper bound, not a forecast. `taken_back` lists the stop points some transition reaches that are not irreversible, in file order. `guards` has one entry per transition that reaches an irreversible stop point, in file order: on the shortest path from `start` to its state (breadth first, every transition followed, file order), `last_gate` is the last gate that guards it and that the path crosses, `shows` and `can_judge` are that gate's (`can_judge` is `"yes"` or `"no"` as the file says, null when the key is absent, the gate waiting for its judge, and `"unreadable"` for any other value), `steps_between` counts the states strictly between that gate and the state, `agents_between` those of type `agent`. When the state is itself that gate both counts are 0; when it is a `human` step and the event is not `deadline_passed`, `last_gate`, `shows` and `can_judge` are null (its `deadline_passed` is read like any other step's). When the last one crossed is a person's write of rule 1, `last_gate` names that `human` step and `shows` and `can_judge` are null. The `flow check` document becomes `{"file", "passed", "problems", "bounds"}`, the `status` document gains `"bounds"`. For a person, `flow check` prints after its first line, and `flow status --map` after its line "This flow: …" (at level 0 too), whenever `bounds` is not null (`flow_paths.render_bounds(bounds) -> str`):

```
This flow holds: 18 steps, it stops at ready_pr, one ticket may cost up to 20 dollars and 240 minutes.
What bounds one run (figures for you to read: no threshold is applied to them):
- Spending: a run is stopped at the first event that takes it past 20 dollars or 240 minutes. It can pass them by the cost of one step, which the file does not bound.
- The circle planning, plan_size, plan_review: its capped steps can be entered 3 times in all at most (cap of planning 3).
- The circle coding, checks, draft_pr, ci_wait, ci_check, ci_fix, review_checks: its capped steps can be entered 16 times in all at most (caps of coding 6, ci_wait 8, ci_fix 2).
- Cannot be taken back: merged, deployed (the default: the file has no "irreversible").
- The file treats as possible to take back: plan, draft_pr, ready_pr.
- The event merged of merging reaches "merged". Every path to it crosses a gate that guards it. On the shortest path the last one is merge_auth, whose judge is shown "the pull request". Steps between merge_auth and merging: 0; agents among them: 0.
- The event deployed of delivery reaches "deployed". Every path to it crosses a gate that guards it. On the shortest path the last one is merge_auth, whose judge is shown "the pull request". Steps between merge_auth and delivery: 1; agents among them: 0.
```

The other forms. No circle: "- No circle: no step can be entered twice." One cap in the group: "cap of ‹state› ‹n›"; several: "caps of ‹state› ‹n›, …"; `most_entries` 1: "1 time in all at most". The key written: '- Cannot be taken back: ‹names› (the file says so under "irreversible").'; an empty list: '- Cannot be taken back: nothing, the file says so ("irreversible": []): no write is checked for a gate.' The `taken_back` line is left out when the list is empty. For each irreversible name no transition reaches, before the lines of `guards`: '- No transition of this file reaches "‹name›": if a step of yours does that write under another name, flow check does not know it; write that name under "irreversible".' A state that is itself the gate: '- The event ‹event› of ‹state› reaches "‹stop point›". ‹state› is a gate: its judge, shown "‹shows›", decides it.' A `human` state: '… ‹state› is a person's step (type "human"): no gate is asked.' A write after a person's: '- The event ‹event› of ‹state› reaches "‹stop point›". Every path to it crosses a gate that guards it or a write a person makes. On the shortest path the last one is ‹step›, a person's step (type "human") whose write is that person's decision. Steps between …' A line that names a gate ends with one sentence more when that gate waits: " That gate still waits for its judge's answer.", or when its answer cannot be read: ' The file's answer for that gate cannot be read: write "can_judge": "yes" or "no".' A gate the file answers `"no"` is not said to guard: '- The event ‹event› of ‹state› reaches "‹stop point›". Every path to it crosses a gate flow check counts. On the shortest path the last one is ‹gate›, whose judge is shown "‹shows›", and the file says nobody can judge it ("can_judge": "no"): flow place refuses it. Steps between …', and for the state itself: '… ‹state› is a gate, shown "‹shows›", and the file says nobody can judge it ("can_judge": "no"): flow place refuses it.' The words "a person decides" are never printed: the program sees a gate, not a person, and the lines say how far that gate is from the write and what its judge reads, with no rule applied to it. And because `flow place` tells a team to remove a gate nobody can judge, `flow place` and `flow status` add a "Careful:" note when a refused gate is the `last_gate` of an entry of `guards`. Removing it is read with the refused gates offered for removal before it (`flow_paths.kept_writes`, below; `flow_paths.struck_with(definition, gates, gate)` gives that set). When the flow cannot lose that gate, for the entry's write or for any other (the gate is in `kept_writes`): 'Careful: ‹gate› is the last gate before "‹stop point›", which cannot be taken back. Do not remove it: flow check would refuse the file. Give ‹judge› something they can read and refuse.' when it keeps the entry's transition, and 'Careful: ‹gate› is the last gate before "‹stop point›". Do not remove it: flow check would refuse the file, for "‹a stop point it keeps›", which cannot be taken back. Give ‹judge› something they can read and refuse.' when it keeps another write only. When removing that gate alone opens no new way to a write, and only removing it with the gates offered before it does, "Do not remove it:" becomes "Do not remove it together with ‹those gates, in the order a run meets them›:" and "would refuse" becomes "would then refuse". Otherwise, the gate being offered: 'Careful: ‹gate› is the last gate before "‹stop point›". Removed, the last one would be ‹the next last_gate›, ‹n› step(s) and ‹k› agent(s) before the write.' (the removed gate is not counted); a gate the flow can lose for every write opens no new way to any, so this form never describes the removal of a gate kept for another write. A gate the flow cannot lose is never offered for removal on stdout either. `flow_paths.kept_writes(definition, gates) -> {gate: [the where of each write it keeps, in file order]}` reads the gates in the order a run meets them, by the length of the shortest path from `start` (breadth first, every transition followed), file order between equals, the gates no run reaches last; never in the order of the file alone. Each is struck (read as guarding nothing) together with the earlier ones offered for removal: a gate is kept when that opens a new way to a write, otherwise it joins the ones offered. A new way to the write (X, e) is a state a run reaches from `start`, crossing no gate that still guards, from which it can take (X, e) without entering the path the file as written already leaves open to it: the states a run reaches from `start` and can take (X, e) from, X left aside. When the file leaves no such path, this is `unguarded` refusing a transition it did not refuse on the file as written; when it does (a bypass `flow check` already refuses), the bypass is set apart, so that it never turns the gate nearest the write into one to remove. So following every offer together never leaves a write unguarded that was guarded, and the gate kept is the one nearest the write whatever the order of the states in the file; on branches it is not always the one the bounds name as the last gate before the write it keeps (`gate_keeps` below). It is read whenever the file is not `malformed`, its other problems left aside, so that an unrelated fault (a missing budget, a cap) never turns the only gate into one to remove; while a step type is unknown, `unguarded` says nothing and no gate is kept, the placement being provisional. While the file is `malformed` or a step type is unknown (`flow_paths.removal_unread`), no refused gate is offered for removal either: its line is 'A gate nobody can judge: ‹gate›. Give ‹judge› something they can read and refuse. Whether the flow can do without it is said once flow check finds no fault that hides its paths.' (`flow_paths.gate_marks(definition, gates)` gives, for `flow place` and `flow status`, `kept_gates` or every gate marked unread). `flow_paths.gate_keeps(definition, gates) -> {gate: {"stop", "last", "where", "with"}}` gives the same gates, each with a write it keeps (`where`, its stop point `stop`): the first, in file order, of which the bounds name it the last gate (`last` true), otherwise the first it keeps (`last` false); `with` lists the gates offered before it that must go with it for `flow check` to refuse the file, empty when removing it alone is refused. `flow_paths.kept_gates(definition, gates) -> {gate: stop}` gives the same gates and stop points. Such a gate's line in `flow place`, and so the `detail` of `steps_placed` and the `next_step` of `flow status`, is 'A gate nobody can judge: ‹gate›. It is the last gate before "‹stop point›", which cannot be taken back: do not remove it; give ‹judge› something they can read and refuse.' when `last` is true; otherwise 'A gate nobody can judge: ‹gate›. Without it, a run could reach "‹stop point›", which cannot be taken back, crossing no gate that guards it: do not remove it; give ‹judge› something they can read and refuse.'; with `with` not empty, "do not remove it" becomes "do not remove it together with ‹those gates›". So a program or a person who keeps stdout only is never told to make the edit `flow check` then refuses, nor told that a gate is the last before a write the bounds give to another, nor that a gate cannot go alone when it can.

**Examples**, all on `definitions/feature.json`; each is a case of 12.6. (1) `plan_review`, `human_review`, `rework` and `merge_auth` removed, their two incoming events pointed at `coding` and `merging`, `stop_at` `deployed`. Today: "This flow holds: 14 steps, it stops at deployed, …", exit 0, level 1. Now exit 1, level 0, two lines, the second at `states.delivery.on.deployed`, the first: '- The event merged of the step merging reaches "merged", which cannot be taken back, and the path ready → planning → plan_size → coding → checks → draft_pr → ci_wait → ci_check → review_checks → mark_ready → merging crosses no gate that guards it. Add a step of type "gate" on that path, with an answer that stops the run; or, if a person does this outside the flow and the step merging only waits for it, that step is a person's decision: give it the type "gate", with its judge and what they are shown; or, if your team can take "merged" back, write "irreversible": [<the stop points it cannot take back>] at the top of the file. (states.merging.on.merged)'

(2) The same with `stop_at` left at `ready_pr`, or with `plan_review` kept (`plan_small` goes around it): the same two problems. (3) Silence as consent: `stop_at` `deployed`, `"deadline_passed": {"to": "merge_auth"}` added to `human_review` and `{"to": "merging"}` to `merge_auth`: the same two problems, the path going through both gates and ending "… → mark_ready → human_review → merge_auth → merging crosses no gate that guards it (it leaves the gate human_review by deadline_passed, when nobody answered) (it leaves the gate merge_auth by deadline_passed, when nobody answered)". (4) A refusal that leads to the write: `human_review` and `rework` removed, `marked_ready` pointed at `merge_auth`, `merge_refused` pointed at a new program step whose one event goes to `merging`: the same two problems, with " (every answer of the gate merge_auth leads to this write)"; `plan_review` is struck too, since its refusal now leads to the merge through no gate that guards. (5) `"cap": 1000000` on `coding` and a budget of 1000000000 dollars: it holds, exit 0, as today; what changes is what the person reads: "past 1000000000 dollars or 240 minutes" and "can be entered 1000010 times in all at most (caps of coding 1000000, ci_wait 8, ci_fix 2)". (6) The whole `writes` list of `draft_pr` deleted, or `ci_wait` retyped `code` with its deadline and the premise check of `ci_check` dropped: both hold, exit 0, as today. Nothing general decides them: the type of a step and the list of its writes are what the file says, and no program can know a step writes more than it declares. They are in the list that ends this section, and `flow check`, when a flow holds, prints the note: "flow check reads the file, not the programs: it cannot see a write a step does not declare, nor a step given the wrong type. The full list is in the page flow-spec.md, section 12." **Replaces**: section 1, a row `irreversible` in the top-level table; section 2, a row and two `malformed` cases; section 4, the row of `flow check`; section 7, the keys of the `status` document and the map; "Twelve refusal codes" in "Choices made here".

### 12.3 `flow fit` prints a cost, from the pages

**Rule.** Every verdict carries cost entries copied from `cli/harnesslib/flow_costs.json`: `{"facts_date": "2026-11-21", "entries": {‹id›: {"about", "figure", "kind", "label", "where", "found"}}, "by_verdict": {…}}`. `kind` is `published` (a figure a source prints, with its evidence label [M], [V] or [S] in `label`), `arithmetic` (the notes' own sum: always printed with the words "not a measurement") or `none` (`figure` is null: the sources give no figure). `where` cites the place in `report.md` or `costs.md`. `found` maps each cited page to the strings a test must find in the cited section of that page (the text under the heading whose number `where` gives; an item number is not looked for), read with the bold marks (`**`) removed; every figure of `figure` is in it, as written. For `agent_pass`: `report.md`: "near one dollar", "$1.19", "131,246", "$1.00 flat", "$1.20"; `costs.md`: the last four. An entry of kind `none` has an empty `found`. The test also checks that `facts_date` is the "Date of the facts" of `costs.md`. The command adds, multiplies, rounds and converts nothing.

| `id` | `about` | `figure` | `kind`, `label` | `where` |
|---|---|---|---|---|
| `agent_pass` | One agent pass | near one dollar: Cloudflare's code review, mean $1.19 over 131,246 runs; Sentry's fix, $1.00 flat; GitHub's heavy runs, about $1.20 | `published`, [V] [V] [M] | report §5.4; costs.md §1 |
| `whole_ticket` | One ticket from start to end | null | `none` | report §5.4; report §9.1, item 2 |
| `ticket_estimate` | One ticket, estimated | $3 to $10 for a feature ticket, $1 to $3 for a simple bug fix | `arithmetic` | report §5.4; costs.md §2 |
| `ci_minute` | One CI minute | $0.006 on a GitHub Actions Linux runner with 2 cores | `published`, [V] | costs.md §1 |
| `engine_fee` | The fee of a managed engine | about $50 per million actions on Temporal Cloud, with no base fee | `published`, [V] | report §3.5; costs.md §3 |
| `engine_workflow` | Writing one workflow for an engine | "1-2 days" on average for a custom Temporal workflow at Duolingo | `published`, [V, self-reported] | report §5.2 |
| `engine_staffing` | The people to host an engine yourself | null | `none` | report §3.5; report §9.1, item 5 |
| `this_tool` | ‹the `choice` of the case› | null | `none` | report §8: the table gives no price |

Which entries, in this order: `by_hand` → `agent_pass`, `whole_ticket`, `ticket_estimate`; `ticket_state_and_ci` → the same three, then `ci_minute`; `symptom` → the same three, then `engine_fee`, `engine_workflow`, `engine_staffing` only when a symptom that fired has `engine` true; `tool` → `own_agent_app` and `many_repositories`: `this_tool`, `agent_pass`; `agent_product`: `engine_fee`, `engine_workflow`, `engine_staffing`; `long_lived_orchestrator`: `this_tool`.

**Output.** The `fit` document gains `"cost": {"facts_date", "entries": [{"id", "about", "figure", "kind", "label", "where"}]}`; a refusal has no `cost`. For a person, after the "Source: …" line and before the symptoms not measured, one heading line then one line per entry: published "- ‹about›: ‹figure›. Published ‹label› (‹where›)."; arithmetic "- ‹about›: ‹figure›. Arithmetic of the notes, not a measurement (‹where›)."; none "- ‹about›: no published figure (‹where›)." Example 1 of section 11 gains, between its "Source" and "Not measured" lines:

```
Cost, from the pages, facts of 2026-11-21 (nothing here is measured on your runs):
- One agent pass: near one dollar: Cloudflare's code review, mean $1.19 over 131,246 runs; Sentry's fix, $1.00 flat; GitHub's heavy runs, about $1.20. Published [V] [V] [M] (report §5.4; costs.md §1).
- One ticket from start to end: no published figure (report §5.4; report §9.1, item 2).
- One ticket, estimated: $3 to $10 for a feature ticket, $1 to $3 for a simple bug fix. Arithmetic of the notes, not a measurement (report §5.4; costs.md §2).
- One CI minute: $0.006 on a GitHub Actions Linux runner with 2 cores. Published [V] (costs.md §1).
```

Example 2 (`double_runs` fired, which an engine removes) gains the heading, the first three lines above, then the three engine lines, built the same way from the table, the last two being '- Writing one workflow for an engine: "1-2 days" on average for a custom Temporal workflow at Duolingo. Published [V, self-reported] (report §5.2).' and "- The people to host an engine yourself: no published figure (report §3.5; report §9.1, item 5)." Example 3, a refusal, is unchanged. Section 11 so grows by 12 lines (5 and 7), and the limit `test_the_contract_names_every_key_and_every_allowed_value` puts on it moves from 95 to 100. `fixtures/flow/fit/<name>/expected.json` gains `"cost"` in every folder, the refused one included: the list of entry ids in order, `[]` for a refusal. **Replaces**: section 11, the list of keys of the `fit` document, the lines printed for a person, examples 1 and 2, and the keys of `expected.json`.

### 12.4 Commands and pages a person can use from their own repository

**Rule.** Stdout stays the same bytes on every machine, help included. What depends on the machine is in the notes only. A note names a command in the short form `flow …` and a page by its file name ("the page flow-format.md", never a path from this repository). Every `flow` command that exits 0 or 1 with `--format md` prints the **closing note** after every other line of stderr, the refusal of `flow new` on an existing file included; never on exit 2:

> Here "flow" is typed: python3 ‹root›/cli/harness.py flow. The pages (flow-format.md, decide.md, costs.md, report.md, flow-spec.md) are in ‹root›/docs/workflow-harness.

‹root› is the folder that holds the `cli/` of the running copy: `os.path.dirname` three times of `os.path.abspath(__file__)` of `flow_notes.py`, links not resolved, never the current folder. Only the path of `harness.py` goes through `shlex.quote`; the folder of the pages is printed as it is. "python3" is fixed text, not the interpreter that runs. When that copy has no `docs/workflow-harness` folder, the second sentence is "The pages are not installed with this copy." `flow_notes.closing() -> str` returns the note. `--format json` still leaves stderr empty, and every command still answers with a document on stdout there: `flow new` on an existing file prints `{"file": ‹path›, "written": false, "reason": "exists"}` and exits 1 (with `--format md`, nothing on stdout and the sentence of section 4 on stderr). `flow --help` and the help of each subcommand are on stdout and carry no path: they name pages by file name, never `docs/workflow-harness/…`, and their last line is "With --format md, every flow command that exits 0 or 1 ends, on stderr, with the full command as this installation runs it and the folder of the pages." **Who prints, in which order.** `flow_place.main` prints stdout only (and the `flow: …` line of an exit 2), never a note: every note of every command is printed by `flow_cli`, with the sentences of `flow_notes`. For each command, in this order, each when it applies: (1) the note about the stop point (section 4); (2) the waiting note (12.1); (3) the "Careful:" notes (section 4, then 12.2); (4) the note of 12.2 on what `flow check` cannot see (`flow check` only); (5) the note of 12.5 (`flow place` and `flow status`); (6) the "Next:" notes, among them the two lines of `flow status` at level 0 without `--map` and its "To try this flow by hand…" at level 1; (7) the closing note.

**The "Next:" notes**, each safe to paste: it reads only, or says what it writes and where, and every path inside a command goes through `shlex.quote` (`flow_notes.q`), so that a file named "my flow.json" is one argument; a plain name is printed as it is, so the outputs of the fixtures do not move. `flow fit`, after `ticket_state_and_ci`, in place of "Next: flow new feature or flow new bug writes a starting definition.": "Next: flow new feature --out .harness/flow/feature.json writes a starting definition under the current folder, ‹absolute current folder›, and never replaces a file. For a bug flow: flow new bug --out .harness/flow/bug.json." `flow new`: "Next: edit ‹path› (every key is explained in the page flow-format.md), then flow check ‹path›, flow place ‹path›, flow status ‹path› --map." `flow check`, `flow place`, `flow status`, `flow next`: the sentences of section 4 and of 12.1, which only read, except `--save-run`, whose note already names the file written. `flow fit`, after a symptom verdict read from a file: 'Next: with a flow definition, flow place <file> --answers ‹answers file› reads these symptoms beside it; flow new feature --out .harness/flow/feature.json writes one.' (none when the answers came on the standard input, which `--answers` does not take). "Source: report §8, first row; …" stays on stdout as it is: the closing note says where `report.md` is. **Example**, `flow fit` on a symptom verdict, which printed nothing on stderr: it now prints that "Next:" note, then the closing note. **Replaces**: section 4, "Answers and notes"; section 5, `flow_place.main`; section 11, the note after `ticket_state_and_ci`.

### 12.5 `flow place` and `flow status` read the measured symptoms

**Option.** `flow place <file> [--answers FILE]` and `flow status <file> [--map] [--answers FILE]`, where FILE is the answers file of `flow fit` (section 11), read with `flow_fit.parse`, so that a key written twice is refused as `flow fit` refuses it. A file that is missing or is not JSON, or `-` (standard input is not taken here): exit 2. Answers that `flow fit` refuses: exit 2, nothing on stdout, "flow: ‹FILE›: flow fit refuses these answers (‹n› to fix). Run flow fit ‹FILE›." Answers whose verdict is `tool`: exit 2, nothing on stdout, "flow: ‹FILE›: these answers describe ‹the case's label›, not a ticket workflow, and ‹file› is a ticket workflow. Give the answers measured on the runs of this flow." A definition is a ticket workflow by being one, so numbers counted on something else are never read as if they were its own, and never dropped in silence. `flow_fit.measured(answers) -> dict`, on what `parse` returns, gives `{"fired": [‹the entries of fit's `fired`›], "sentence": ‹fit's `verdict.sentence` under `symptom`, otherwise null›, "not_deciding": [‹fit's entries›], "not_measured": [‹keys›], "symptoms": ‹how many symptoms the rules hold, 8 today›}`; it raises `ValueError` with the two messages above. `place(definition, measured=None)` and `status(definition, placement=None, measured=None)` take it; both documents gain `"measured"`, that value, or null when no answers were given: the last key of the `place` document, after `passed`; the `status` document ends with `waiting`, `bounds`, `measured`, in this order. `passed`, the exit code and the level do not change: a symptom is a fact about runs, the level is read from the file.

**What is said of the runs**, ‹M›, built by `flow_fit` from `measured`, in this order: (a) when `fired` is not empty, `sentence`; when it is empty and nothing is `not_measured`, "None of the ‹k› symptoms measured on your own runs is above its threshold."; when some are, "Measured on your own runs: ‹j› of the ‹k› symptoms, none above its threshold."; when all are, "Nothing was measured on your own runs, so nothing is known from them." (b) when any, " Not measured, so not counted as fine: ‹keys›." (c) when `not_deciding` is not empty, " Listed for you to judge, no threshold is written for it: ‹key› is ‹value›." (several joined by "; "). (d) when `fired` is not empty, " No command can tell which step a symptom comes from." **The verdict of `flow place`** when `measured` is not null. Where the verdict would be `no_engine` and a symptom fired, its code is `symptom`, a new code, and its sentence "No step is written as needing an engine. ‹M›". Where it would be `no_engine` and none fired, the code stays and the sentence is "No step needs an engine, as the file is written. ‹M›". Where it is `engine` or `open`, the code is kept and the sentence of section 6 is followed by " ‹M›". So "No step needs an engine." alone is printed only when no answers were given, and a file of answers that are all `"not measured"`, the one `flow fit --questions` gives to start from, never reads as reassurance. `flow status` prints one line more, "From your own runs: ‹M›", after the bounds block in the map and last without `--map`; nothing when `measured` is null. **Notes.** Without the option, `flow place` and `flow status` print: "Measured symptoms were not read: this answer comes from the file alone. To read them, add --answers <the answers file given to flow fit>." With it: "Symptoms read from ‹FILE›: ‹n› above threshold, ‹k› listed without a threshold, ‹m› not measured (never counted as fine).", followed by " flow fit ‹FILE› gives the smallest fix to try first for each." only when a symptom fired: otherwise `flow fit` gives no fix. With the option, the "Next: flow status …" note of `flow place`, and the note of `flow status` at level 0 without `--map` that names the command showing every reason, carry the same `--answers ‹FILE›`.

**Example**, `fixtures/flow/definitions/feature.json` and `fixtures/flow/fit/symptom-fired/answers.json`. `flow place`, today, with or without those answers, ends "Verdict: no step needs an engine." With `--answers`, exit 0: "Verdict: no step is written as needing an engine. 2 symptoms are measured above their threshold: double_runs is 2, above 0; agent_loops is 3, above 0. Not measured, so not counted as fine: order_breaks. No command can tell which step a symptom comes from." With `--format json`, `"verdict": {"code": "symptom", "sentence": "No step is written as needing an engine. 2 symptoms are […]"}`, `"passed": true`, `"measured": {"fired": [{"key": "double_runs", "value": 2, "above": 0, …}, {"key": "agent_loops", …}], "sentence": "2 symptoms are […]", "not_deciding": [], "not_measured": ["order_breaks"], "symptoms": 8}`. With `fit/ticket-state-and-ci/answers.json`: "Verdict: no step needs an engine, as the file is written. Measured on your own runs: 7 of the 8 symptoms, none above its threshold. Not measured, so not counted as fine: tickets_without_cost. Listed for you to judge, no threshold is written for it: steps_with_own_retry_rule is 4." With `fit/nothing-measured/answers.json`: "Verdict: no step needs an engine, as the file is written. Nothing was measured on your own runs, so nothing is known from them. Not measured, so not counted as fine: runs_paid_twice, double_runs, silent_events, agent_loops, waits_inside_computation, steps_with_own_retry_rule, order_breaks, tickets_without_cost." **Replaces**: section 4, the rows of `flow place` and `flow status`; section 5, the two signatures; section 6, the list of verdict codes.

### 12.6 The fixtures and the tests the change moves, and the new ones

**Expected answers that move**, each for the sentence named. `cases/feature-as-written` and `cases/bug-as-written` (12.1, "No template writes `can_judge`"): `place` becomes `open` `["plan_review", "human_review", "merge_auth"]` and `["human_review"]`, verdict `open`, `passed` false; `status` level 0, `steps_placed` false. The six folders of `fit/` (12.3) gain `cost`. **References that move, answers unchanged** (12.1, "a team's answered files"): `place/feature` and `place/bug` take `definitions/feature.json` and `definitions/bug.json`; so do the fourteen cases that need answered gates: `answers-missing`, `circle-closed-by-moving-the-stop-point`, `circle-through-the-stop-point`, `engine-alone`, `gate-cannot-refuse`, `gate-nobody-can-judge-alone`, `gate-shown-a-late-write`, `gate-shows-nothing`, `loop-without-cap`, `order-of-the-questions`, `premise-check-missing`, `several-problems-in-order`, `stop-point-is-a-step-name`, `unknown-type`. `template:<kind>` keeps its meaning, what `flow new` writes; in the format tests, which run without the code, it resolves to `definitions/<kind>.json` with `can_judge` removed from every gate (`flow_fixture_files.reference_template` does it), and `definitions/<kind>.json` stays the answered file. Nothing moves in `sequences/` (`next_state` reads no `can_judge`), in `definitions/`, or in `place/trapped`: the refusal as worded here was tried by a prototype on every definition and case of the family and fires on none. `place/trapped` passes it thanks to `plan_approval`: its `merge_wait` is a wait that watches the team merge, three steps and two agents after that gate, which is what its bounds line will say.

**The case format gains** four optional keys: `waiting` (what `flow_place.waiting` returns), `bounds` (any of `circles`, as a list of `{"steps", "most_entries"}`, `irreversible`, `taken_back`, and `guards`, as a list of `{"state", "event", "last_gate", "steps_between", "agents_between"}`), `answers` (an answers file, a path from `fixtures/flow/`, given to `place` and `status`), and under `place`, `fired` (the keys of `measured.fired`, allowed only with `answers`); `place.verdict` may be `symptom`. A case holds no exit code: what exits 2 is a unit test. **New cases** (definition; what it shows); those on `definitions/…` give `check` and `bounds` only, unless said:

- `feature-answered`, `bug-answered` (`definitions/feature.json`, `definitions/bug.json`): nothing waits, level 1; their bounds: two circles of 3 and 16 entries and the two `guards` of 12.2; no circle, and `human_review` its own gate.
- `one-approval-answered` (`template:feature`, `plan_review` answered `yes`): two gates still wait, in file order; level 0.
- `merge-without-a-person`, `merge-behind-the-stop-point`, `gate-on-one-branch-only`, `silence-is-consent`, `refusal-leads-to-the-write` (examples 1 to 4 of 12.2): two problems each, at `states.merging.on.merged` and `states.delivery.on.deployed`. `silence-on-the-last-gate-only` (`definitions/feature.json`, `deadline_passed` to `merging` on `merge_auth` alone): it holds, since the path that leaves `merge_auth` in silence has crossed `human_review`.
- `reaches-on-a-stop` (the definition of `merge-behind-the-stop-point`, `delivery` and `closing` removed, `merged` of `merging` pointed at `stopped` with a reason, its `reaches` kept): one problem, at `states.merging.on.merged`. `gate-with-a-mistyped-type` (`definitions/bug.json`, `human_review` typed `gat`): one problem, `unknown_step_type`.
- `wait-watches-a-person-merge` (`definitions/bug.json`, `stop_at` `ready_pr`, `human_review` retyped `wait`, deadline 168, no judge): refused at `states.human_review.on.merged_by_human`; the sentence's second way out fits it. `person-merges-by-hand` (`definitions/bug.json`, `human_review` retyped `human`): it holds. `gate-far-before-the-write` (`definitions/feature.json`, `plan_small` pointed at `plan_review`, `human_review`, `rework` and `merge_auth` removed, `marked_ready` pointed at `merging`, `stop_at` `deployed`): it holds, and `guards` says `plan_review`, 7 steps between for `merged`, 2 of them agents.
- `irreversible-own-name` (`definitions/feature.json`, `"irreversible": ["ready_pr"]`): refused at `states.mark_ready.on.marked_ready`. `irreversible-empty` (the definition of `merge-without-a-person`, `"irreversible": []`): it holds, `guards` empty. `irreversible-not-a-list` (`"irreversible": "merged"`) and `irreversible-typo` (`["mergd", "deploied"]`): `malformed` at `irreversible`, alone. `stop-point-renamed` (example 1 with `merged` and `deployed` renamed `landed` and `shipped`, `stop_at` `shipped`, no key): it holds, `guards` empty, `taken_back` holds both names with the others, and the line "No transition of this file reaches …" is printed for `merged` and for `deployed`.
- `huge-cap-and-budget` (example 5): it holds; `most_entries` 1000010. `writes-deleted`, `wait-retyped-as-program` (example 6): both hold, recorded as what `flow check` cannot see.
- `symptom-on-a-placed-flow` (`definitions/feature.json`, answers `fit/symptom-fired/answers.json`; `place` and `status`): verdict `symptom`, `fired` `["double_runs", "agent_loops"]`, `passed` true, level 1. `symptom-beside-an-engine` (the definition of `engine-alone`, the same answers): verdict `engine`. `answers-nothing-above`, `answers-nothing-measured` (`definitions/feature.json`, answers of `fit/ticket-state-and-ci` and `fit/nothing-measured`): `no_engine`, `fired` `[]`. Answers of `fit/own-agent-app`: exit 2, a unit test. One folder joins `fit/`, which then has seven: `symptom-no-engine` (only `agent_loops` above zero), whose `cost` has no engine entry.
- After the critics: `every-answer-merges` (`definitions/feature.json`, `human_review` and `rework` removed, `marked_ready` pointed at `merge_auth`, `stop_at` `deployed`, `merge_refused` pointed at `merging_b`, a copy of `merging` that goes to `delivery_b`, a copy of `delivery`): refused at `states.merging.on.merged`, `states.delivery.on.deployed`, `states.merging_b.on.merged`, `states.delivery_b.on.deployed`; level 0. `bug-every-answer-merges` (`definitions/bug.json`, `stop_at` `merged`, `closed_with_reason` going to `closure_check` with `"reaches": "merged"`): refused at both answers of `human_review`. `refusal-reaches-the-write` (`human_review`, `rework` and `merging` removed, `marked_ready` pointed at `merge_auth`, both of its answers reaching `merged`, the refusal to `stopped`): refused at both answers. `refusal-deploys-directly` (as `every-answer-merges`, `merge_refused` pointed at a program `deploy_direct` whose event reaches `deployed`): refused at `states.delivery.on.deployed` and `states.deploy_direct.on.deployed_anyway`, the merge guarded. `person-merges-then-pipeline-deploys` (`definitions/feature.json`, `human_review`, `rework` and `merge_auth` removed, `marked_ready` pointed at `merging`, retyped `human` with `deadline_hours` 1 and its program keys removed, `stop_at` `deployed`): it holds; `guards` gives `merging` for the deploy, 0 steps between. `person-merges-on-silence-then-pipeline-deploys` (the same, plus `"deadline_passed": {"to": "delivery", "reaches": "merged"}` on `merging`): refused at `states.merging.on.deadline_passed` and `states.delivery.on.deployed`. `person-merges-on-silence` (`definitions/bug.json`, `human_review` retyped `human` without `judge`, `shows` and `can_judge`, its `deadline_passed` going to `closure_wait` with `"reaches": "merged"`, `stop_at` `merged`): refused at `states.human_review.on.deadline_passed`; level 0. `person-merges-what-can-be-taken-back` (as `person-merges-then-pipeline-deploys`, with `"irreversible": ["deployed"]`): it holds; `guards` gives `merging` for the deploy, 0 steps between, and `taken_back` ends with `merged`.

- After the fuzzing of the fix: `triage-before-the-merge-authorisation` (`definitions/feature.json`, `rework` removed, `human_review` answering `approved` to `merge_auth` or `redeploy_only` to `delivery`, both gates answered `"no"`, `stop_at` `deployed`): it holds; `merge_auth` is the last gate before the merge and kept for the deploy, `human_review` the last gate before the deploy; the "Careful:" note about `merge_auth` says not to remove it, for "deployed". `bypass-and-two-gates-nobody-can-judge` (`definitions/feature.json`, both pull request approvals answered `"no"`, `review_checks` sending `trivial` to `merging`): refused at `states.merging.on.merged` and `states.delivery.on.deployed`; `human_review` is offered, `merge_auth` kept for "merged".

**Tests whose assertions move.** No test is deleted or renamed; a test named after the old contract keeps its name and gets a first line saying what it asserts now. By owner. *Core* (`test_flow.py`, `test_flow_slice.py`, `test_flow_review.py`): `test_each_template_answers_the_placement_questions_as_the_contract_says` (no gate has `can_judge`); `test_check_says_a_flow_holds`, `test_check_prints_one_line_per_problem_and_exits_1`, `test_a_flow_that_holds_and_is_placed_is_mapped`, `test_the_map_of_a_mapped_flow` (the bounds, the three new keys); `test_a_new_flow_is_checked_placed_mapped_and_played_from_its_file` (a fresh template is at level 0 until answered), `test_the_map_names_the_judge_of_a_gate_nobody_can_judge_as_flow_place_does`, `test_place_on_a_flow_that_holds_says_what_comes_next`, `test_place_says_when_flow_check_refuses_the_file`, `test_place_with_json_prints_the_document_alone`, `test_status_at_level_one_says_how_to_try_the_flow_by_hand` (answered files, the new notes), `test_the_help_of_flow_gives_the_order_of_work` (pages by file name), and every comparison of stderr with `""` or with exact sentences under `--format md`, which gains the closing note (among them `test_flow_slice.py` on `flow next`). *Placement* (`test_flow_place.py`): the list of keys of the `place` document gains `measured`; `test_a_person_reads_one_line_per_step_then_the_verdict` stays as it is, since `flow_place.main` prints no note. *Fixtures* (`test_flow_fixtures.py`, `test_flow_cases.py`, `test_flow_guide.py`): `test_each_template_is_the_flow_the_contract_fixes` (`can_judge` leaves `FIXED_STATE_KEYS`; a new test asserts that no template gate has the key and every gate of `definitions/feature.json` and `bug.json` has it); `test_every_step_lands_where_the_answer_key_says`; `CODES` (thirteen), `CASE_KEYS`, `PLACE_KEYS` and `one_place` (the verdict `symptom`); `test_the_two_templates_are_placed_in_the_guide_as_flow_place_places_them` (the answered files). *Fit* (`test_flow_fit.py`): `DOCUMENT_KEYS` and `LISTED` (the cost), `test_six_fixtures_one_per_verdict_one_unmeasured_one_refused` (seven folders, the key `cost`), `test_a_note_says_what_comes_next` and `test_the_questions_list_every_key_and_allowed_value` (the closing note, the new "Next:"), `test_the_contract_names_every_key_and_every_allowed_value` (100 lines).

### What `flow check` still cannot see

- Whether a step has the type the file gives it: a wait written `code`, an agent written `code`, a person's decision written `human`. A `human` step that makes a write that cannot be taken back, or a write named `merged` or `deployed`, by any event but `deadline_passed`, is read as a person deciding it, for the writes after it too: that a person really does it is the file's word. A person's merge under another name the file lists as possible to take back decides nothing: list that name under `irreversible`.
- A write the file does not declare, and whether a declared write is the only one the program makes.
- Something that cannot be taken back under a name the file does not list: the answer prints which stop points the file treats as possible to take back. And a write on a transition with no `reaches`.
- Whether the gate on the path is the right one: a gate on the plan, or at the very start, counts though everything after it is written by agents. `flow check` prints the last gate before each such write, what its judge is shown and how many agent steps come after, and applies no rule to it. Nor does it decide whether the judge can judge: `flow place` asks, a person answers. A gate the file answers `"no"` still counts for `flow check`; its line says so and does not call it a gate that guards, `flow place` refuses it, and the flow stays under level 1. Nor does it know who really approved on the forge.
- Whether an answer of a gate is a refusal in more than name: it asks that one answer cannot lead to the write, not what that answer is called nor that the judge knows it.
- Whether a cap or a budget is reasonable: the figures are printed, no threshold is applied. And what one step costs: a run can pass its budget by one step.
- Whether a step that says `checks_premise: true` checks anything, and a premise check that is missing two steps after a wait.
- That what a gate `shows` is written before the gate on every path, and that the events of the file are the ones the programs send.
- Which step a measured symptom comes from: no command can tell.

### Settled after the critics

- **Silence is not a decision**: a gate left by `deadline_passed` is read as absent (12.2, rule 2).
- **A gate guards only if it can refuse the write**; found by striking, so two empty gates cannot vouch for each other (rule 3). A critic's own attack file is accepted: its first gate has an answer that stops the run, so a person could refuse; the case kept is one where no gate can.
- **One gate far before the write is still accepted**, and said: a stricter rule refuses `place/trapped`. The answer prints the last gate, what its judge reads and the agent steps after it; "a person decides" is never printed.
- **A name under `irreversible` that nothing reaches is `malformed`**; the stop points the file treats as possible to take back are printed, and so is "no transition reaches them".
- **`reaches` on a transition to `stopped` is read** like any other; a gate with a mistyped type gives one line, `unknown_step_type`, and the new refusal waits.
- **A wait that watches a person merge is refused**, and the sentence gives three ways out; a `human` step counts only when it holds the transition.
- **A gate nobody can judge, last before such a write, is not to be removed**: a "Careful:" note, stdout of `flow place` unchanged.
- **`most_turns` became `most_entries`**, and a state alone is a circle only with a transition to itself.
- **A waiting gate behind the stop point is said to be there**, and the level is read on the whole file.
- **Answers that describe another tool are refused, exit 2**, against the second critic, who kept them silent: a number is never dropped without a word. So `measured` is null only when no answers were given.
- **Nothing measured is never reassurance**: the verdict counts what was measured, lists what was not and the number with no threshold. The answers are read with `flow_fit.parse`, `-` is refused, and the new keys come last in both documents.
- **`found` is per page**, in the cited section, bold marks removed; the figure of `agent_pass` leads with the report's words, "near one dollar". Section 11 may reach 100 lines; the six folders of `fit/` all gain `cost`, and become seven.
- **Help is on stdout and carries no path**; the closing note is on stderr only, `python3` fixed text, links not resolved, never on exit 2. `flow_cli` prints every note, in one fixed order; `flow_place.main` prints none.
- **`template:<kind>` in the format tests** is the answered file without its answers; the guide's two tables are those of the answered files. The tests whose assertions move are listed in 12.6, by owner; none is renamed.

Three more reviews then attacked the change as built. What they changed:

- **A gate guards a stop point, not one transition** (rule 3). The contract read a gate as guarding one transition, so a gate whose every answer merges, each to its own copy of the merge step, or whose refusal itself reaches `merged`, still guarded, and `flow status` read level 1. The contract was the wrong one: rule 3 now strikes a gate that cannot keep the run from every write of the stop point. On every definition and case of the family, no answer moved. Cases `every-answer-merges`, `bug-every-answer-merges`, `refusal-reaches-the-write`, `refusal-deploys-directly`.
- **A person's own merge guards what follows it** (rule 1). A person merging by hand, then the pipeline deploying, was refused, and none of the three ways out fitted: writing `"irreversible": ["merged"]` would have said, falsely, that the deploy can be taken back. Case `person-merges-then-pipeline-deploys`.
- **A key written twice in a definition, an event or a run is exit 2** (section 2), as `flow fit` refuses it in the answers: the file that governs the merge gets the care the answers file gets.
- **A gate answered `"no"` still counts for `flow check`**, and its line says the file says nobody can judge it, never that it guards. A reviewer offered to strike it from the gates that guard; kept as it was, because `flow place` refuses that gate and the level stays 0, so no merge is certified, and `flow check` keeps to paths while `flow place` keeps to judges.
- **Removing a refused gate is offered only when the flow can lose it.** The "Careful:" note says what the last gate would become when another gate still guards the write, and stdout of `flow place`, and the `next_step` of `flow status`, never tell a team to remove the only gate before a write that cannot be taken back. Section 6 is changed for that line.
- **A person's step left by its deadline decides nothing** (rule 1, after the review of the change). Rule 1 read every transition of a `human` step as a person's write, its `deadline_passed` included, so a file that merged when nobody acted held and reached level 1. That transition is now read like any other step's, and guards nothing after it. Cases `person-merges-on-silence`, `person-merges-on-silence-then-pipeline-deploys`; no other answer moved.
- **The gates kept are read on the file as it is and together** (after the review of the change). `kept_gates` was empty while `flow check` refused the file for any reason, so a missing budget turned the only gate before the merge into one to remove; and it struck one gate at a time, so two gates nobody can judge on one path were both offered. It is now read whenever the file is not `malformed`, and each gate is struck with the ones offered before it. No answer of the family moved.
- **What the attacks on the fix changed** (issue 165). A person's merge counted only when `merged` was listed as irreversible, so writing `"irreversible": ["deployed"]` turned a flow that held into one refused, with no way out that fitted: the default names now count for rule 1 whatever the list says, and the bounds line no longer says that person's write cannot be taken back. `kept_writes` read the gates in file order, so stdout could call an early gate "the last gate before" a write and offer the real last one for removal: they are now read in the order a run meets them. The "Careful:" note struck the gate alone and could name, as the next last gate, one already offered for removal: it now strikes those offered before it. A malformed file or an unknown step type no longer turns the only gate into one to remove. Case `person-merges-what-can-be-taken-back`; the answers that moved are the bounds line of `person-merges-then-pipeline-deploys` and the gate line of a malformed flow in `test_flow_place.py`.
- **What the fuzzing of the fix changed** (issue 165). The "Careful:" note asked whether a gate kept the write of its own entry only, so a gate kept for the deploy but last before the merge was offered for removal on stderr while stdout said to keep it, and removing it broke the deploy: a kept gate is now never offered for removal, and its note names the write it keeps. The stdout line said a kept gate was the last gate before a write the bounds gave to another gate: it now says so only when the bounds agree, and says what removing it opens otherwise. "Do not remove it" was said of a gate that could go alone, another gate still guarding: it now names the gates it must not go with. And a bypass `flow check` already refuses turned every gate on the guarded path into one to remove: the path the file already leaves open is now set apart when a gate is read. Cases `triage-before-the-merge-authorisation`, `bypass-and-two-gates-nobody-can-judge`.
- **One line per irreversible name no transition reaches**, a name written twice under `irreversible` read once, and `can_judge` `"unreadable"` in the bounds for a value the grid cannot read, which is a fault, never a wait.
- **The notes**: every path inside a command is quoted for a shell; "flow fit ‹FILE› gives the smallest fix" only when a symptom fired; the waiting note says "Nothing is wrong with these steps"; the level-0 note of `flow status` keeps `--answers`; `flow fit` says, after a symptom verdict, which commands read the answers beside a flow; the last line of every help says the closing note comes with `--format md`, on exit 0 or 1; `flow new --format json` on an existing file answers with a document; and `flow fit` says "Nothing was measured on your own runs" when nothing was, as `flow place` does.

## Choices made here

- **A state is a step**, and there are five step types: a person who decides (`gate`) is told apart from a person who works (`human`), because only the first needs a judge and something to read.
- **The stop point sits on a transition** (`reaches`), not on a state: a state can be left by a failure, and that must not count as reaching the stop point. It is checked on one path only: `check` asks that some reachable transition reaches it, not that every path to a later write crosses it. The reviewers asked for more; a branch that goes around the stop point is a design a person must read, and `flow status` shows where the flow stops. Section 12.2 adds the one path rule a program can decide in general: a gate that can refuse, crossed by an answer and not by silence, before a write that cannot be taken back.
- **The event type carries the outcome.** No condition on payload values. So every step that can fail, refuse or find its facts changed has an event for it: `flow check` asks two ways out of a gate and of a premise check, and `step_failed` and `deadline_passed` exist everywhere without being declared.
- **Three built-in events, one reason each.** A passed deadline gives the reason `deadline_passed` in every state, gate or not.
- **A cap counts entries into a state over the whole run**, never reset, and the templates put it on the step that costs.
- **Twelve refusal codes**, thirteen since section 12.2. The proposal's seven, with "no judge or no deadline" split in two, plus `malformed`, a deadline on waits, a gate that cannot refuse and a gate that shows nothing.
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
- **The guide has two sections more than section 9 lists**, before its closing one: the two templates placed step by step, and what the guide does not decide. `test_flow_guide.py` also compares those two tables with what `flow place` answers on the templates (since section 12.1, on the answered files `definitions/feature.json` and `bug.json`).
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
