# The two reference flows: a feature ticket and a bug ticket, step by step

Date of the facts: 2026-11-21, from [report.md](report.md).

Short answer: a feature ticket and a bug ticket each fit in a small table of steps, and every step has one owner: a program, a coding agent, a person, or nobody while the run waits.
The two templates `flow new` writes are those tables, cut where a team should start: the feature flow stops at a pull request ready for review, the bug flow stops once the root cause is on the ticket.
Both are on paper. No first-hand account was found of a team of 5 to 50 running such a flow, and this version runs nothing (report §9.1, §6.3).

**Where this page sits.** `python3 cli/harness.py flow new feature` and `flow new bug` write the two flows described here as a file you edit ([flow-format.md](flow-format.md)). Where each step should live is the subject of [decide.md](decide.md). This page explains what the steps are, where they come from, and where they differ from the report.

**Words used, defined once.**

- **Flow**: one team workflow for one kind of ticket. **Step**: what happens in one state of the flow. **Run**: one ticket going through it. **Template**: the starting flow `flow new` writes.
- **Agent**: a model that calls tools in a loop until a task is done. Here, a coding agent such as Claude Code or Codex. **Skill**: a Markdown procedure the agent loads when a task matches.
- **CI**: the pipelines of the forge, the place where repositories live and merges are decided. **PR**: pull request.
- **Step types**, as the templates write them in the key `type`: `code` (a program, no model call), `agent` (a coding agent), `human` (a person does work), `wait` (nobody; the run waits for something outside), `gate` (a person decides yes or no).
- **Signal**: what opened the bug ticket and can be looked at again later: an error count past a threshold, a flaky-test detector, CI red on the main branch, or a person's report (report §6.2, step 1).
- **Stop point**: a milestone a run can end on, on purpose, such as "the draft PR is open". The key `stop_at` picks one.
- **Cap**: the most times one run may enter a step.
- **Premise check**: a step that first checks the facts it starts from still hold, for example that the bug still reproduces.
- **Engine**: a product that records each finished step, so that a run continues where it stopped ([engines.md](engines.md)).
- **Evidence labels**, kept from the report: [M] read from a registry, a repository or a specification; [V] said by a company about itself; [S] said by a third party. A fact shown without a label has none in the report either.

## 1. Where the two flows come from

Nobody published them in this form. The report built them from what companies wrote about their own systems. It names seven sources: Stripe, OpenAI's Symphony, WorkOS, Bitrise, Sentry, Dropbox and Shopify (report §6). The note they come from also lists Block, Linear, Datadog and incident.io (note ticket_to_prod_orchestration.md §9 and §10). Four rules recur across the sources and shape both tables (report §5.1):

| Rule | Where it was seen |
|---|---|
| A step that must happen is a program, not a sentence in a prompt | Stripe alternates program steps ("run linters", "push") and agent steps ("implement", "fix CI") [V] (report §5.1, pattern 2) |
| Every loop has a cap | Stripe: two CI rounds, then a person, whatever the state. Dropbox: five attempts (report §5.1, pattern 3) |
| People approve the plan and the result, not each step | Bitrise added "merge only on explicit instruction" after its agent merged its own PR [V] (report §5.1, pattern 6) |
| A bug flow stops earlier than a feature flow | Sentry stops after the root cause, the plan or a draft PR, by setting, and never merges [V] (report §5.1, pattern 9) |

The numbers do not all have the same weight. Two CI rounds and five bug attempts are what Stripe and Dropbox do. Three local rounds is the notes' own suggestion: "no source gives one" (report §6; note ticket_to_prod_orchestration.md §9, step 9).

## 2. The feature flow

The report's flow has twenty steps and three owners: code, agent, human (report §6.1). The template has eighteen steps and uses four of the format's five types (none is typed `human`). It starts at "ready for agent", so the report's steps 1 to 3 happen before it.

**Before the flow** (report §6.1, steps 1 to 3; not in the template): a person writes the ticket with acceptance criteria; an agent checks the ticket is ready and proposes criteria and a split, writing nothing without agreement; a person accepts and moves the ticket to "ready for agent". That move is the start gate.

| Template step | Type | Report step | What it does | Cap or deadline | Stop point reached on leaving |
|---|---|---|---|---|---|
| `ready` | code | 4 | Checks the ticket is eligible, refuses a second run on it, opens the run record | | |
| `planning` | agent | 6 | Writes a short plan: the criteria restated, the assumptions listed | cap 3 | |
| `plan_size` | code | 7 | Decides from size and paths whether a person must review the plan; posts the plan on the ticket | | `plan` |
| `plan_review` | gate | 7 | A maintainer approves the plan or sends it back. Entered for large plans only | 72 hours | |
| `coding` | agent | 8 | Implements the ticket and its tests | cap 6 | |
| `checks` | code | 9 | Format, lint, build, selected tests. On failure, back to `coding` | | |
| `draft_pr` | code | 10 | Pushes; opens a draft PR linked to the ticket, with plan, assumptions, results, cost | | `draft_pr` |
| `ci_wait` | wait | 11 | Waits for CI on the pushed commit | cap 8, 6 hours | |
| `ci_check` | code | 11 | Checks the result is for the current commit, then reads it | | |
| `ci_fix` | agent | 12 | Fixes the CI failures and pushes | cap 2 | |
| `review_checks` | agent | 13 | Reviews code, tests and security in a separate context. On failure, back to `coding` | | |
| `mark_ready` | code | 14 | Computes the risk from paths and size, marks the PR ready, assigns reviewers | | `ready_pr` (default) |
| `human_review` | gate | 15 | A reviewer who did not request the change approves or asks for changes | 72 hours | |
| `rework` | code | 15 | Collects the review comments and hands them to the next coding round | cap 2 | |
| `merge_auth` | gate | 16 | A maintainer who is not the requester says whether the PR may be merged | 72 hours | |
| `merging` | code | 17 | Checks the PR is still the one approved, then puts it in the merge queue | | `merged` |
| `delivery` | wait | 18 | Waits for the team's normal delivery pipeline, behind its protected environment | 168 hours | `deployed` |
| `closing` | code | 20 | Checks what was deployed is this ticket's change; closes the ticket; records outcome and cost | | |

The template allows up to 20 dollars and 240 minutes for one ticket. That budget is the template's starting value, not a measured cost: nobody publishes the cost of a ticket end to end (report §5.4; [costs.md](costs.md)).

One run, as the template is written. It ends on purpose when the PR is marked ready:

```
 ticket moved to "ready for agent"
      |
   [ready] --not eligible--> stopped
      |
  (planning) <-------- sent back --------+
      |                                  |
  [plan_size] --large--> <plan_review> --+
      |small                  |approved
      v                       |
  (coding) <------------------+
      |        ^
      |        +--- failed checks, or failed review
  [checks]
      |passed
  [draft_pr]
      |
  ~ci_wait~ <--- stale result, or fix pushed ---+
      |                                         |
  [ci_check] --red--> (ci_fix) -----------------+
      |green
  (review_checks)
      |done
  [mark_ready]
      |
  == ready_pr: the run ends here on purpose ==

  described, not run until stop_at moves:
  <human_review>  [rework]  <merge_auth>  [merging]  ~delivery~  [closing]

  [code]   (agent)   <gate>   ~wait~
```

At any step a run also ends when a person stops it (the event `human_stop`), when a deadline passes, or when the budget or a cap is reached (note ticket_to_prod_orchestration.md §9, stop conditions; [flow-format.md](flow-format.md)).

**Where the template and the report differ.** The step types are the first difference: the report has three owners; the format has five types, of which the templates use four.

| Subject | Report §6.1 | Template |
|---|---|---|
| Steps 1 to 3, and the stop point `readiness` | In the flow | Before the flow. The template has no `readiness` stop point |
| Step 5: clean workspace, short-lived narrow credential, fetching ticket and rules | A code step | No step of its own. `ready` does not mention it |
| Who decides that a plan is reviewed | Step 7 is a human step, "only for large or sensitive changes" | A code step, `plan_size`, decides; the review is a `gate` |
| Who posts the plan | Step 6, the agent, per the note (§9) | `plan_size`, a program |
| Waiting for CI | Step 11, typed code | A `wait` step, then a code step that reads the result |
| Review by a person, merge authorisation | Steps 15 and 16, typed human | Typed `gate`. No template step is typed `human` |
| Passing review comments back | Inside step 15, "by code" | Its own code step, `rework` |
| The independent review finds a problem | Not said | `review_checks` sends the run back to `coding` |
| Local rounds | Cap of three, the notes' suggestion | `coding` may be entered 6 times in a run, all ways in counted: first pass, failed checks, failed review, rework |
| Delivery | Step 18, typed "human + code" | A `wait` step: the run waits for the team's pipeline |
| Step 19: an agent watches the rollout and proposes a rollback, never runs it | Optional | Absent |
| Step 20: releases the next unblocked ticket | Yes | Not in the step's description. `closing` adds a premise check instead |
| Deadlines of 6, 72 and 168 hours; caps on `planning`, `ci_wait`, `rework` | Not given | Template values, to edit |

## 3. The bug flow

A bug starts from a machine signal. So it needs a gate in code before any agent runs, and a check that the bug is still real (report §6.2). The report's flow has fifteen steps; the template has fourteen.

| Template step | Type | Report step | What it does | Cap or deadline | Stop point reached on leaving |
|---|---|---|---|---|---|
| `triage` | code | 1 to 3 | Removes duplicates against open tickets and PRs, checks the ticket is eligible, opens the run record | | |
| `premise` | agent | 4 | Premise check: does it still reproduce on the current head, is there already a fix? | | |
| `root_cause` | agent | 5 | Finds the root cause, with its evidence and a confidence | cap 5 | |
| `notify` | code | 6 | Writes the root cause on the ticket and notifies the owner; stops when the confidence is low | | `root_cause` (default) |
| `repro` | agent | 7 | A failing test that reproduces the bug, then a fix plan | | `plan` |
| `fix` | agent | 8 | The smallest fix that makes the test pass | | |
| `verify` | code | 9 | Runs the test, many times if it is flaky, then lint, build, suite. On failure, back to `root_cause` | | |
| `draft_pr` | code | 10 | Draft PR with the cause, the evidence, the test, what was tried | | `draft_pr` |
| `ci_wait` | wait | 11 | Waits for CI on the pushed commit | cap 4, 6 hours | |
| `ci_check` | code | 11 | Checks the result is for the current commit, then reads it | | `ready_pr` |
| `ci_fix` | agent | 11 | Fixes the CI failures and pushes | cap 2 | |
| `human_review` | gate | 12 | A maintainer merges, or closes with one line of reason | 72 hours | `merged` |
| `closure_wait` | wait | 14 | Waits some days after the merge | 168 hours | |
| `closure_check` | code | 14, 15 | Checks the fix is the one merged; has the signal stopped? Records outcome and cost | | |

The template allows up to 10 dollars and 120 minutes for one ticket, a starting value as above.

Before the default stop point, five ends are reached without a fix. Three are results, not failures: a duplicate (`triage`), a bug already fixed (`premise`), a root cause with low confidence handed to a person (`notify`). Two hand the ticket back: not eligible (`triage`) and cannot reproduce (`premise`). The report names the outcomes to record: fixed, already fixed, rejected, escalated (report §6.2, step 15).

**The tool never merges a bug fix** (report §6.2, step 12). In the template the only way to the stop point `merged` is the event `merged_by_human`, out of a gate.

**Where the template and the report differ.**

| Subject | Report §6.2 | Template |
|---|---|---|
| Signal, duplicates, eligibility | Three code steps (1 to 3) | One code step, `triage` |
| CI on the current commit | One step, typed "code + agent" | Three steps: `ci_wait` (wait), `ci_check` (code), `ci_fix` (agent) |
| A stop point when CI is green | None | `ready_pr` |
| Review | Step 12, typed human | Typed `gate` |
| Step 13: merge queue and normal pipeline | A code step | No step: the person merges, then the run waits |
| The signal continues after the fix | "Reopen with the new evidence" | The run stops with the reason `not_fixed`. Reopening is not written |
| Recording the outcome | Its own step (15) | Inside `closure_check` |

### The incident variant

The report gives it in three sentences (report §6.2): steps 1 to 5 run as an investigation attached to the incident. The agent proposes a mitigation; a human applies it. A fix enters at step 7 only when a responder asks.

Read against the template: `triage`, `premise` and `root_cause` are the investigation; nothing in production is touched by the agent; the fix, if asked for, starts at `repro`. The reason is that an incident separates the mitigation (a person, now) from the fix (a ticket, later) (note ticket_to_prod_orchestration.md §4). incident.io opens a fix PR only when a responder asks [V] (report §5.1, pattern 9).

The note is a little wider than the report on one point: it also lets a fix PR be created "by opt-in at high confidence", and asks that every finding link to its source (note ticket_to_prod_orchestration.md §10). The report kept only "when a responder asks".

`flow new` writes two kinds, feature and bug. There is no incident template. The nearest thing is the bug flow with `stop_at` left at `root_cause`; it has no step for the mitigation a person applies, and its `triage` expects a ticket. This reading is this page's, not the report's.

## 4. Stop points

A stop point is a choice, not a defect. "Diagnosis is useful alone; writing code or acting is a separate permission" is the reason given by the products that stop after the root cause or the plan [V] (note ticket_to_prod_orchestration.md §5).

| Stop point | The run ends when | Feature | Bug | Who stops there, and why |
|---|---|---|---|---|
| `readiness` | The ticket is judged ready or not | report only | | |
| `root_cause` | The cause is on the ticket, confidence not low | | default | Sentry by setting, incident.io by default [V] (note §5) |
| `plan` | The plan is posted (feature); the failing test and fix plan exist (bug) | yes | yes | Sentry by setting [V] (report §5.1, pattern 9) |
| `draft_pr` | A draft PR is open | yes | yes | Stripe and Ramp among others. Ramp wants no path for unreviewed code [V] (note §5) |
| `ready_pr` | The PR is marked ready (feature); CI is green (bug, template only) | default | yes | The usual stop of a feature flow: a PR ready for review (note §4) |
| `merged` | The merge is done, on a person's word | yes | yes | Bitrise: merge only on explicit instruction [V] (report §5.1, pattern 6) |
| `deployed` | The team's pipeline has delivered | yes | no | "No agent holds a deploy right" (report §6.1, step 18) |

To move a stop point, set `stop_at` to another name of this table that your file reaches. `flow check` and `flow status --map` then say which steps are run and which are only described. The note's advice is to make the stop point a setting per flow and to "default to the earliest useful one" (note ticket_to_prod_orchestration.md §8, point 6). That is the author's inference, not a measured result.

Not found: any documented case of an agent deploying to production without a human approval or a low-risk rule (note ticket_to_prod_orchestration.md, "Not found").

## 5. Where each `ai-sdlc` skill plugs in

`ai-sdlc` is this project's plugin for one change, in seven phases, each a skill backed by a tested command (proposal §1). The flow writes no phase logic: the agent inside a step calls the existing skill (proposal §1). This table is read from each skill's own file, not from the report. In this version nothing wires a skill to a step: the templates name no skill, and no command runs one.

| Skill | What it does, in its own words | Feature flow | Bug flow |
|---|---|---|---|
| `ticket` | Says whether a ticket is ready and what it lacks; never modifies it without agreement | Before the flow: report steps 1 to 3 | Reads the ticket an incident investigation returns |
| `dev` | Develops a ticket from the plan to the PR body, on the path its size imposes; never approves, never merges | `planning` and `coding`. Its `size` command is the kind of check `plan_size` needs; its PR body is what `draft_pr` posts | `repro` and `fix` |
| `qa` | Derives tests from the acceptance criteria; a program says whether they hold, the suite passing several times in a row | The tests part of `review_checks`; its gate is a command `checks` can call | `verify`, which runs a flaky test many times |
| `review` | Reviews a PR and returns few comments, each with its evidence; only comments | `review_checks`, in a separate context | Before `human_review`, if you add the step: the bug template has none |
| `secu` | Runs the declared scanners; a program says whether there is a secret or a silenced scanner; never declares a change safe | The security part of `review_checks` | The same, if you add the step |
| `ship` | Prepares a delivery and proposes it; sets no tag, starts no deployment | Beside `delivery`: it helps the person who delivers. The run only waits | Not used: the flow ends at the closure check |
| `run` | Investigates a production incident and returns a ticket; never acts in production | Not used | The incident variant: the investigation that comes before `repro` |

Two things to notice. Every skill refuses the same acts the flows refuse: none approves, merges, deploys or acts in production. And the report asks that review, tests and security run "as CI checks" (report §6.1, step 13): the skill explains, the command behind it is what a CI job can require.

## 6. What the two flows say, and do not say

- **Every wait sits between two ticket states**: plan review, CI, human review, merge, the closure check. During each, nothing needs to stay alive (report §6.3). So, on paper, neither flow needs an engine. The note that first drew this conclusion calls it "a hypothesis to test on real team workflows, not a result", and the report adds: "It still is" (report §6.3). The default runtime, a ticket state plus short CI jobs, is described in [ci-as-engine.md](ci-as-engine.md).
- **They are a synthesis.** No company runs exactly these steps. The sources are accounts companies gave of themselves; the engine, the timeouts and the failure rate per step of Stripe's flow, for example, were not found (note ticket_to_prod_orchestration.md, "Not found").
- **Nothing was run.** `flow new`, `flow check`, `flow place`, `flow status --map` and `flow next` work on the definition file. Running a step on a real ticket (`run-step`) is planned, not built.

## The symptom that would make you need it

You need a written flow, starting from one of these two templates, when you can count one of these on your own tickets:

- Two people on the team list the steps of "a ticket handled by the agent" and the lists differ, or a step has two owners, or none.
- A PR opened by an agent was merged with no person saying so, even once.
- An agent went around the same failure more times than anyone decided: no cap is written anywhere.
- Fixes are opened for bugs that were already fixed, or two PRs fix the same bug. Count the agent PRs closed without merge for that reason.
- A bug ticket was closed on a green PR and the signal came back. Count the reopened ones.

You need to move a stop point later only when the runs that reach the current one are accepted by people nearly every time, on a count you keep. Until then keep the defaults: `ready_pr` for a feature, `root_cause` for a bug.
