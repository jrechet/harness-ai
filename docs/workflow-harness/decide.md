# Where does this step go? A guide for placing one step of a team workflow

Date of the facts: 2026-11-21, from [report.md](report.md). The grid is the one of [flow-spec.md](flow-spec.md), section 6.

You are a tech lead. Your team wants a ticket to go from "ready" to a pull request, or further, with a coding agent doing part of the work. For each step you must decide where it lives. This page gives the questions to ask, in order, and the places a step can land.

**Where this page sits in the work.** All commands are `python3 cli/harness.py flow …`, in this order:

1. `flow new feature` or `flow new bug` writes a starting definition.
2. You edit it. Every key, and one step of each type ready to paste, are in [flow-format.md](flow-format.md).
3. `flow check <file>` refuses a flow that could loop, wait or spend without end.
4. `flow place <file>` says where each step belongs. This page explains its answers: read it before or after.
5. `flow status <file> --map` gives the level reached on paper, and the next step.
6. `flow next <file> --event <event.json> --new` tries the flow by hand, one event at a time. Nothing is run.

A template describes more than it runs. As written, a run of the bug template stops on purpose once the root cause is written on the ticket: the steps after it, up to the pull request and the closure check, are described but not run until you move the stop point (section 6).

**The default, said once.** The ticket (or the pull request) holds the state. A short CI job runs each step. The coding agent works inside one step. You add an engine only when you have measured a symptom that nothing cheaper removes (section 3).

**Words used, defined once.**

- **Flow**: one team workflow for one kind of ticket. **Step**: what happens in one state of the flow. **Definition**: the JSON file that describes the flow. **Run**: one ticket going through it.
- **Agent**: a model that calls tools in a loop until a task is done. Here, a coding agent such as Claude Code or Codex.
- **Skill**: a Markdown procedure the agent loads when a task matches. **Sub-agent**: a second agent with its own context, started by the first.
- **Hook**: a script the agent's runtime runs at a fixed point. The model does not choose whether it runs.
- **Forge**: where the repositories live and where merges are decided (GitHub, GitLab, Forgejo). **CI**: the forge's pipelines.
- **Gate**: a step where a person decides yes or no. **Judge**: that person.
- **Stop point**: a milestone a transition reaches, such as "the draft pull request is open". The definition picks one with `stop_at`: a run ends there on purpose. It is a name on a transition, not a step.
- **Cap**: the most times one run may enter a step. Every circle of steps needs one.
- **Premise check**: a step that first checks the facts it starts from still hold (the branch has not moved, the bug still reproduces). Needed after a wait or a person's work.
- **Engine** (workflow engine, durable engine): a product that records each finished step, so a run that crashes or waits for days continues where it stopped (Temporal, Restate, DBOS).
- **Graph framework**: a library where you declare steps as nodes and transitions as edges (LangGraph).
- **Idempotent**: safe to run twice.
- **Evidence labels**, kept from the report: [M] read from a registry, a repository or a specification; [V] said by a company about itself; [S] said by a third party.

## 1. The seven questions for one step

Ask them in this order. The first answer that names a place ends the walk. `flow place` does not ask you anything: it reads each answer from a key of the step in the definition. If the key is missing, the step stays open and the command tells you which key to add.

### Who performs this step?

`who`, read from the key `type`.

- `code` (a program, no model call) or `agent` (a coding agent) → go on to "How long does it live".
- `human` (a person does work) or `wait` (nobody; the run waits for something outside) → **the ticket holds this**. Nothing runs meanwhile.
- `gate` (a person decides) → go on to "Can the person who approves really judge".

Why it matters: a step with two owners has none. Example: Stripe's flow alternates code steps ("run linters", "push") and agent steps ("implement", "fix CI"), each with one owner [V] (report §5.1, pattern 2; §6 types every step the same way).

### Can the person who approves really judge what they approve?

`judge`, read from the key `can_judge`, which a person fills in.

- `yes` → **a human gate**: they are shown something they can read and refuse.
- `no` → **no gate**: nobody could tell a good one from a bad one.

Why it matters: an approval nobody can judge is a click. It slows the flow and protects nothing. Example: the reference flows ask for a plan approval "only for large or sensitive changes", and the report's grid says of gates "do not add one for comfort" (report §6.1, step 7; §7, question 4). The gates that hold are on things a person can read: Bitrise added "merge only on explicit instruction" after its agent merged its own pull request [V] (report §5.1, pattern 6).

### How long does it live, and what must survive?

`survive`, read from the key `survives`.

- `restart`: minutes to a few hours, and starting again from its beginning is acceptable → go on.
- `midway`: days inside one computation, or it must not run twice, or every run must be replayable step by step → **an engine**.

Why it matters: this is the only question that leads to an engine. A long wait is not a long step: in both reference flows every wait sits between two ticket states, and nothing needs to stay alive during it (report §6.3). Example: Dropbox moved CI handling out of the agent after sessions waited for hours [V] (report §5.1, pattern 2). The wait became a state; the step stayed short.

### Does the work split into many independent units?

`spread`, read from the key `units`.

- `one` → go on.
- `many` → **a fan-out by script**, one writer per unit.

Why it matters: several agents on one task cost 3 to 10 times the tokens of one agent [V] (report §7, "three numbers"). Example: the same change across hundreds of repositories is a script and a CI matrix, one pull request per repository (report §8).

### How many repositories need this step?

`repos`, read from the key `repositories`.

- `one` → go on.
- `several` → **a shared CI workflow**, versioned, with an owner.

Why it matters: a copied step drifts, and nobody owns the copies. Example: on Forgejo a workflow cannot be shared from a private repository, so sharing means a thin file per repository with all the logic in one versioned command-line tool [V, read from documentation, not tested] (report §3.3).

### Is the right output determined by the inputs?

`determined`, read from the key `type` again.

- yes (the step is `code`) → **code**: a tested command. Never a prompt.
- no (the step is `agent`) → go on to the last question.

Why it matters: a skill is a request, not a guarantee. In Vercel's evaluations the agent never invoked the available skill in 56% of cases [V, own evaluations] (report §7). So lint, build, push and "is this ticket eligible" are programs.

### Is this step here because today's model is weak?

`weakness`, read from the key `weak_model`.

- `yes` → **a skill with its date**: write the model and the date in the skill file itself, at its top, test again at each model release, delete it when it changes nothing. The definition has no key for the model or the date, and this version does not check that they are written: `flow place` only reminds you.
- `no` → **a skill**.

Why it matters: help written for a weak model becomes dead weight. Example: Anthropic removed context resets, then sprint decomposition, as models improved; Vercel removed about 80% of an agent's tools and got better results on 5 test queries [V] (report §5.1, pattern 8).

### How these seven come from the report's eight

The report's grid (§7) has eight questions for a piece of any kind. Here they are adapted to a step of a flow. "Does a human decide in the middle" became two questions, `who` and `judge`. "Must it happen every time" stays with `python3 cli/harness.py place`, the grid for pieces inside one repository. "What shape is the control flow" is not asked per step: it is answered once for the whole flow, which is a small table of states in code.

## 2. The nine places

| Place | `flow place` says | What it means | Right when | Wrong when |
|---|---|---|---|---|
| `code` | "this is code" | A tested command, started by a short CI job | The same inputs must give the same output | The step needs to read intent or write prose |
| `skill` | "a skill is enough" | The agent, inside one step, guided by a skill | The work needs interpretation, and a check in code follows it | You need it to happen every time: a skill can be ignored |
| `dated_skill` | "a skill is enough, with its date" | The same, with the model and the date written in the skill file | The step only makes up for a weakness of today's model | It is a guarantee, a right or a fact: those do not age, put them in code |
| `ticket_state` | "the ticket holds this" | A state on the ticket or the pull request; nothing runs while it lasts; the next event starts a short job | A person works, or the run waits for CI, a review or a deploy | Something must stay alive in memory through the wait |
| `human_gate` | "this is a human gate" | A ticket or pull request state only a human account may set | The judge is shown something they can read and refuse | The judge is the requester, or approves what they cannot read |
| `no_gate` | "no gate here" | A refusal: nobody can judge this | Never a goal. It tells you to remove the gate or give the judge something to judge | You keep the gate "for comfort" |
| `reusable_workflow` | "this is a shared CI workflow" | A versioned plugin and a reusable CI workflow, with an owner | Several repositories need the same step | One repository needs it: a file there is enough |
| `campaign` | "this is a fan-out by script" | A script fans out, one writer per unit, never a swarm | Tens or hundreds of independent units | The units depend on each other, or there are only a few |
| `durable_engine` | "this would need an engine" | The exit: a workflow engine holds the step | The step answered `midway`, and section 3 agrees | The wait could be a ticket state, or the trouble is an agent that loops |

`flow place` has no place for a graph framework. Section 3 says why.

**Four places you will hear about that `flow place` does not hand out.** They are for pieces inside one repository or inside one step. `harness place` and the report's grid (§7) decide them.

| Place | Right when | Wrong when |
|---|---|---|
| A line of instructions (AGENTS.md) | A fact every task needs and the agent cannot find by itself | It is a procedure, or it must be enforced. Long always-loaded files raise cost by over 20% with no average gain [M] (report §7) |
| A sub-agent | A check that must be independent, or a few parts that read a lot; one writer | Splitting by role for its own sake: 3 to 10 times the tokens [V] (report §7) |
| A hook | Something must happen every time the agent acts, on the agent's machine | It must hold for people too: then it is a required CI check |
| A CI job | A few hours, unattended, a restart is acceptable. It is how every `code` step of a flow runs | The step must resume in its middle: a failed job restarts from zero and pays its tokens again (report §3.3) |

## 3. When a step really needs an engine

**When do I need an engine, LangGraph or Temporal?** By default, neither. The default is the ticket's state plus CI. "You need an engine" should be a symptom you measured, not a taste (report §7, last table):

| Symptom you can measure | Smallest fix, staying on CI and ticket state | What removes it by design |
|---|---|---|
| Runs die far in and pay their tokens twice, more than about one run in ten | Shorter jobs; progress written on the pull request between jobs | An engine |
| Two runs on one ticket | One run at a time per ticket; keys derived from the ticket, never random | An engine with one workflow per ticket |
| An event accepted, nothing happened, nobody told | A job timeout; a scheduled sweep; a final status written by code | Polling, or an engine timer |
| An agent loops and burns tokens | A budget cap per run; empty turns count as failure | **Nothing. An engine retries it faithfully** |
| A wait that must resume inside an expensive multi-step computation | Model the wait as a ticket state | An engine |
| Many steps, each with its own retry and timeout rule | Reusable CI workflows | An engine; count one to two days per workflow |
| Strict order across events from several systems | One queue per ticket | An engine, or a database constraint |
| You cannot say what a ticket cost | The step writes tokens and dollars on the pull request | Any runtime with a run record |

Try the middle column first. Move to the right column only when the symptom is still there.

- **Temporal, or another engine** (Restate, DBOS): right when a symptom above stays after its cheap fix, or when compliance asks for a step-by-step replay of every run (report §9.2). The fee is small: about $50 per million actions on Temporal Cloud [V]. The cost is one more system and people who know it (report §3.5). Duolingo counts "1-2 days" for a custom workflow [V, self-reported] (report §5.2). An engine still runs steps at least once, so writes must be idempotent, and facts go stale during a wait (report §3.2).
- **LangGraph**: right for one case, which is not a ticket flow: you write your own agent application in Python or TypeScript, the graph is known, and a run must pause and resume inside the process (report §2.7). Around an existing coding agent it has no place. The free library has no queue, no detection of a dead run and no "one run per ticket" lock [M] (report §2.5).
- **How sure is the default?** It rests on converging accounts and on issue trackers, not on a controlled comparison. No first-hand account exists of a team of 5 to 50 running such a flow on any runtime [M: searched and not found] (report §9.1). On paper, neither reference flow needs an engine; the report calls that "a hypothesis to test" (§6.3).

In this version, `flow place` reads one answer only for the engine: `survives: midway`. The other symptoms can be read only from real runs, which this version does not do yet.

## 4. Reading what `flow place` prints

One line per step, then the verdict, then the gates nobody can judge.

```
- coding (an agent): a skill is enough. Decided by "Is this step here because today's model is weak?": no.
- approval (a person decides): this is a human gate. Decided by "Can the person who approves really judge what they approve?": yes. Shown to a maintainer of the repository: the branch.

Verdict: no step needs an engine.
```

- `coding` is the step's name in your definition. "(an agent)" is who performs it.
- "a skill is enough" is the place, in the words of section 2.
- "Decided by" gives the question that ended the walk and the answer read from your file. If you disagree with the place, that answer is the one to look at.
- A gate's line ends with who judges and what they are shown.
- **The verdict** is one of three. "No step needs an engine." Or "One step would need an engine", with the step and the reason: this is an answer, not a failure. Or "1 step(s) cannot be placed yet", with the question that has no answer and the key to add to that step, for example `can_judge` on a gate.
- **A step that cannot be placed** has a second line under it, which says what to write: the key, its allowed values, and every other key the step still lacks. A value the grid does not know (`"can_judge": true`, `"survives": "hours"`) is told as such, not as a missing answer.
- **A gate nobody can judge** gets its own line: "A gate nobody can judge: ‹step›. Remove it, or give ‹judge› something they can read and refuse." The command then exits with 1, as it does for a step that cannot be placed.
- **Two commands, two questions.** `flow check` looks at the shape of the flow: a gate must name a judge, a deadline, two ways out, and show something a step wrote. `flow place` looks at where each step lives and at `can_judge`, the answer a person gives. Each can pass while the other fails, and each says so in a note when it sees the other would refuse the file. `flow status` needs both.

## 5. Three examples

**`coding`, an agent step** ("Implements the ticket and its tests"). Who performs it: an agent. It lives minutes to hours and may start again (`restart`). One unit, one repository. The right code is not determined by the ticket: it needs interpretation. It is not there to make up for a weak model. Place: `skill`, "a skill is enough". Note what makes this safe: the next step, `checks`, is code, and the loop between them has a cap.

**`approval`, a gate** ("A maintainer reads the branch and says whether a PR may be opened"). Who performs it: a person who decides. Can they judge? They are shown the branch, which an earlier step pushed, and they can refuse. Place: `human_gate`, "this is a human gate". Change one thing: show the maintainer nothing, or something only the agent can read. The honest answer becomes `can_judge: no`, the place becomes `no_gate`: `flow place` exits with 1 and `flow status` stays at level 0 until you remove the gate or give the judge something to read. `flow check` still passes: it checks that the gate shows something a step wrote, not that a person can judge it.

**`settle`, a step that needs an engine.** Imagine a program step: "Sends the refunds of the ticket to the payment provider, one by one, over two days". It lasts days inside one computation and no refund may be sent twice: `survives: midway`. The walk stops at the third question. Place: `durable_engine`, "this would need an engine". Before you accept it, try the cheap fix of section 3: can each refund be its own short job with a key derived from the ticket, and the wait a ticket state? If yes, the answer was `restart` after all.

## 6. The two reference flows, placed step by step

These are the two templates `flow new` writes, built from the reference flows of report §6. Every step lands on the default: no step needs an engine.

**Feature ticket** (report §6.1). The flow starts at "ready for agent": writing the ticket and checking it is ready (steps 1 to 3) happen before. As written, a run stops on purpose when the pull request is marked ready: `stop_at` is the stop point `ready_pr`, reached by the transition out of `mark_ready`. The six steps after it, from `human_review` to `closing`, are described but not run until you set `stop_at` to `merged` or `deployed`.

| Step | Report step | Who | `flow place` says | Why |
|---|---|---|---|---|
| `ready` | 4, 5 | a program | this is code | Eligible or not is determined; it refuses a second run on the ticket |
| `planning` | 6 | an agent | a skill is enough | A plan needs interpretation |
| `plan_size` | 7 | a program | this is code | Code decides whether the plan is reviewed, never the agent that wrote it |
| `plan_review` | 7 | a person decides | this is a human gate | Shown the plan; only for large changes |
| `coding` | 8 | an agent | a skill is enough | Capped |
| `checks` | 9 | a program | this is code | Format, lint, build, tests |
| `draft_pr` | 10 | a program | this is code | A write to the outside, keyed by the ticket |
| `ci_wait` | 11 | waits | the ticket holds this | Nothing runs while CI runs |
| `ci_check` | 11 | a program | this is code | First checks the result is for the current commit |
| `ci_fix` | 12 | an agent | a skill is enough | Cap: two rounds, then hand back |
| `review_checks` | 13 | an agent | a skill is enough | Independent review, in a separate context |
| `mark_ready` | 14 | a program | this is code | By default a run stops after this step |
| `human_review` | 15 | a person decides | this is a human gate | Shown the pull request |
| `rework` | 15 | a program | this is code | Passes the review comments back; capped |
| `merge_auth` | 16 | a person decides | this is a human gate | The requester cannot be the approver |
| `merging` | 17 | a program | this is code | First checks the branch has not moved |
| `delivery` | 18 | waits | the ticket holds this | The team's normal pipeline; no agent holds a deploy right |
| `closing` | 20 | a program | this is code | Records outcome and cost |

**Bug ticket** (report §6.2). A bug starts from a machine signal, so code filters before any agent runs. As written, a run stops on purpose once the root cause is on the ticket: `stop_at` is the stop point `root_cause`, reached by the transition out of `notify` (not by the step named `root_cause`, which comes before). Bug flows stop earlier than feature flows (report §5.1, pattern 9). The ten steps after `notify` are described but not run until you set `stop_at` to `plan`, `draft_pr`, `ready_pr` or `merged`.

| Step | Report step | Who | `flow place` says | Why |
|---|---|---|---|---|
| `triage` | 1 to 3 | a program | this is code | Removes duplicates, checks eligibility |
| `premise` | 4 | an agent | a skill is enough | Does it still fail? Is it already fixed? |
| `root_cause` | 5 | an agent | a skill is enough | Cap: five attempts |
| `notify` | 6 | a program | this is code | Forced stop when confidence is low; by default a run stops after this step |
| `repro` | 7 | an agent | a skill is enough | A failing test first |
| `fix` | 8 | an agent | a skill is enough | The smallest fix that makes the test pass |
| `verify` | 9 | a program | this is code | Runs the test, then the suite |
| `draft_pr` | 10 | a program | this is code | Cause, evidence, test, what was tried |
| `ci_wait` | 11 | waits | the ticket holds this | |
| `ci_check` | 11 | a program | this is code | |
| `ci_fix` | 11 | an agent | a skill is enough | Cap: two rounds |
| `human_review` | 12 | a person decides | this is a human gate | The tool never merges a bug fix |
| `closure_wait` | 14 | waits | the ticket holds this | Days, and still not an engine: nothing is alive |
| `closure_check` | 14, 15 | a program | this is code | Has the signal stopped? |

What to notice: the waits of several days (`delivery`, `closure_wait`) and the gates with long deadlines land on the ticket, not on an engine. Length alone never sends a step to an engine.

## 7. What this guide does not decide

- **Whether your team should build a flow at all.** Chaining the steps by hand may be enough.
- **Whether a judge can judge.** A person answers that, in `can_judge`. The grid only refuses a gate once the answer is no.
- **Whether the flow works on real tickets.** Everything here is on paper. Nothing in this version runs an agent, calls a forge or reads a clock.
- **Pieces inside one repository**: an instruction line, a hook, a required check. Use `harness place`.
- **Which agent, which model, which forge, which engine product.** The report compares them (§3, §4).
- **Caps, budget and stop point.** You set them, with the keys `cap` on a step, and `budget` and `stop_at` at the top of the file ([flow-format.md](flow-format.md)); `flow check` only refuses a flow that has none.
- **The symptoms of section 3.** They are measured on real runs, later.

## The symptom that would make you need it

You need this guide when two people on the team answer "where does this step go" differently, or when a step keeps moving between a prompt and a script. You need more than its default when a symptom of section 3 is measured on your own runs and its cheap fix did not remove it. Until then: the ticket's state, a short CI job per step, and a cap on every loop.
