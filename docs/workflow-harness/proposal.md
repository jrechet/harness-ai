# harness-flow: helping a team build its workflow harness

Date: 2026-11-21. State: a proposal. Nothing described here is built or prototyped. Sizes and orders are estimates.

It rests on [report.md](report.md) (the state of the art) and on the eleven notes of [research_notes/](research_notes/). The fourteen claims it leans on most were fact-checked on 2026-11-21 (report §11): one was wrong, two cannot be proven, and the recommendation holds. A sentence that cites "report §N" takes its sources from that section. This version replaces the first one: it compares the three designs the architects proposed, and takes in the two later notes (self-hosted forges and language; independent evidence on LangGraph).

Words used here, beyond those of the report:

- **Flow**: one team workflow for one kind of ticket, for example "feature ticket to a reviewed PR".
- **Definition**: the data file that describes a flow: its states, who performs each step, the caps, the budget, the gates, the stop point.
- **Run**: one ticket going through a flow.
- **Run record**: what code writes about a run: state, attempts, cost, last transition.
- **Stop point**: the place where a flow ends on purpose (root cause, plan, draft PR, ready PR, merged, deployed).
- **Exit**: leaving the default runtime for a workflow engine, because a measured symptom asks for it.

---

## 1. The idea in five lines

1. A third plugin, `harness-flow`, on the same model as the two others: skills explain and ask, a tested program guarantees, the pipeline executes.
2. It helps a team **draw** one flow (feature or bug), **place** each step (skill, code, hook, CI job, ticket state, human gate, engine), and **build** it one step at a time, with a stop point the team chooses.
3. The default runtime is what the team already owns: the ticket or the PR holds the state, CI runs each step, a coding agent works inside one step and calls the existing `ai-sdlc` skills.
4. A workflow engine or LangGraph is never a rung of the ladder. It is an **exit**, named only when a program measures one of a few symptoms on real runs; docs explain both tools even when the answer is "not yet".
5. The code stays Python, standard library only, for the first version. The commands that CI calls are specified so that one Rust binary can replace them, and Rust is the language of the engine exit.

### How it sits next to what exists

| | Subject | Question it answers | State |
|---|---|---|---|
| `harness-ai` | One repository | "Is this repository ready for agents, and what is the next step?" | built, five measured levels |
| `ai-sdlc` | One change, in seven phases | "Is this ticket ready, this PR reviewed, this delivery prepared?" | built, about forty gates as code |
| `harness-team` ([team-assessment.md](team-assessment.md)) | A workflow a team **already has**, across repositories | "What do we really have, and how is each piece held?" | proposed, not built |
| **`harness-flow`** (this document) | A workflow a team **wants to build**, across repositories | "What chains the phases, where does each step go, what runs it, where does it stop?" | proposed |

`harness-flow` writes no phase logic. It chains what `ai-sdlc` already does and reuses three things: the placement grid (`cli/harnesslib/placement.json`), the four "holds" of `harness-team` (asked, runs-ignored, checked, enforced), and the repository level of `harness-ai` as a condition to open unattended steps, as `docs/ai-sdlc/proposal.md` already states.

---

## 2. Three designs, and the one I recommend

Three architects each proposed a design from one angle. All three agree on more than they differ: a third plugin, a workflow written as a data file, an extended placement grid, the vendor's coding agent run as a child process, gates that the agent cannot pass, no LangGraph.

| | A. Flow on CI | B. Durable spine | C. Rust core on CI |
|---|---|---|---|
| What runs a flow | The forge's CI, one short job per event | One Temporal workflow per ticket, a worker process (`flowd`); agent steps still run as CI jobs | The forge's CI, as A |
| Where the state lives | The ticket status and markers on the ticket and PR | Temporal's history, mirrored on the ticket | As A |
| Language of the guaranteed code | Python, standard library, in the existing `cli/` | Rust for the worker, relay and step runner; Python for the checks | One Rust binary, `flow`; the existing Python gates called as subprocesses |
| New things to operate | None | An engine (Temporal Cloud or self-hosted), a worker, a relay | A release pipeline for binaries; cargo builds in CI |
| A job that dies late | Runs again from its start and pays again; short jobs limit it | Resumes at the last recorded step | As A |
| A human who takes days | A ticket state; the reply is a new event; reminders come from the sweep | A durable wait with timers for reminder, escalation, park | As A |
| On Forgejo and Gitea (no approval gate, report §3.3) | Works: gates are ticket states | Works: gates are signals | Works; a versioned binary plus a thin file is the documented work-around for private sharing |
| Fit with this repository's rules | Full: no dependency, same CLI, same fixtures | A second toolchain and a service | A second toolchain; "nothing to install" is lost for the new plugin |
| Evidence for it | The first failures of small teams need a key, one run per ticket, a sweep and a budget, not an engine (report §5.3) | The only before-and-after figure found is on an engine: Cursor's agent loop, one nine to two nines, self-reported with no method (report §5.1). Duolingo extended Temporal to its whole agent platform in 2026 (report §5.2) | The large coding agents are Rust cores with the agent behind a process boundary (report §4.1) |
| Evidence against it | CI is fragile, by how much is not known: 25 failures in a capped one-day sample of 100 runs in GitHub's own repository, test workflows included, no retry (report §5.3). No team documents this exact shape | No team of 5 to 50 found on an engine for an internal flow; 1 to 2 days per custom workflow at Duolingo; Temporal's Rust SDK is under three months into general availability with no named user (report §5.2, §4) | For a tool called from CI, standard-library Python is the cheapest to change; every Rust team wrote more itself; one human can review it (report §4.5) |
| The owner's taste for Rust | Not served at first | Served where Rust has a supported building block | Served everywhere code is written |
| First measurable slice | One week, no account, no key | After an engine namespace, a worker and a relay exist | After a workspace, its CI and a release job exist |

### 2.1 The recommendation

**Design A as the base**, built so that C and B stay reachable without a rewrite.

Why A:

- It is the default the research supports for an internal ticket workflow: "CI and ticket state first, managed engine second, home-made daemon last" (report §5.3). On paper, every wait of the two reference flows sits between two ticket states (report §6.3).
- It adds nothing to operate. The long-lived process is what failed silently in the open-source daemons and webhook services.
- It keeps the repository's own rule: what must be guaranteed goes into `cli/`, standard library only.
- It can be measured within a week.
- Going from commands called by CI to a long-lived process or an engine is an addition. The other way is a rewrite (report §5.3, self-hosted forge note).

Its weaknesses, which the design must say and limit, not hide: a job that fails late is paid twice; state spread over a ticket status, labels and a PR marker is harder to read than a run table; every write to the outside must be made safe to repeat by hand; agents in CI are a known injection surface (GitInject: every provider tested fell to at least one attack, https://arxiv.org/abs/2606.09935); one ticket maps to one repository; and nobody has published this exact shape with failure counts.

### 2.2 What I take from B

- **Durability is measured, not declared.** B's `flow-drill` becomes a command of A: deliver the same event twice, kill a job in the middle, let a gate time out, then count which finished steps ran again and which writes were duplicated.
- **Every gate has a deadline.** Remind, escalate to a named person, then park the ticket with a plain status. On CI the sweep does it; no timer service is needed.
- **A run keeps the definition it started with.** The hash of the definition and the agent's version are written in the run record at claim time.
- **The approver is checked on the forge**, by code, not read from a sentence: the requester is not the approver.
- **The shape of the exit**: a managed engine, one workflow per ticket with the ticket key as its identifier, agent steps left in CI jobs, the `ai-sdlc` gates left as required CI checks, the same definition file interpreted by the worker.
- **A coded "do you need this at all" test** before anything is installed.

### 2.3 What I take from C

- **The run side is four commands with a written contract**: `claim`, `run-step`, `report`, `sweep`. JSON in, JSON out, and a set of recorded event sequences with expected results. A Rust binary can replace the Python ones and be graded by the same sequences.
- **One adapter per coding agent, behind one interface**, using only documented flags, the version pinned, and a contract test (start, read the result, resume, refuse) run before any version bump.
- **Prompts and skills stay text files** read at run time, never compiled in.
- **A thin workflow file per repository, all logic in the versioned tool.** This is what makes sharing work on a private Forgejo.
- **The agent holds no tracker or forge token**; code reads and writes for it.
- **Rungs that are places to stay**, and a pruning routine at each model change.

### 2.4 Under which facts I would be wrong

| If this is true | Then the better design is |
|---|---|
| The teams' runners have no Python (Forgejo's default job image ships only Node), or cannot run this repository's CLI | C for the run side: one static binary. Question 2 |
| The owner wants a Rust code base for its own sake, to learn or to ship one binary to many teams | C. A would only delay it. Question 2 |
| Runs cost dollars each and more than about one in ten dies far in, at a volume where paying twice costs more than a service | B |
| A ticket must be joined across several repositories, or events from several systems must be strictly ordered | B, or a small service with a database constraint |
| A human must answer while the agent waits with its context | Neither A nor C. A service in TypeScript or Python on the vendor's SDK |
| Compliance requires a step-by-step replay of every run | B. Markers and CI logs are not a replayable history |
| The team builds an agent **product** for its users | B. That is where Cursor and Replit use an engine |
| First real runs on CI lose or duplicate work at the rates of the worst issues read, despite the cheap fixes | The default is wrong; go to a managed engine earlier |
| The scope cannot hold identity and review gates on the forge (level T3 of the team note) | None. Wire nothing unattended yet |
| The team writes its own agent application in Python or TypeScript, with a known graph and pauses in the process | None of the three. That is LangGraph's ground; the suite explains it and stops there |
| A vendor's hosted agent already covers the flow on the team's forge | Ship the skills and the grid; skip the generated CI |

---

## 3. What the code guarantees

All of it under `python3 cli/harness.py flow`, standard library only, in `cli/harnesslib/flow*.py`. The definition is JSON (the CLI supports Python 3.10, which has no TOML reader), in `.harness/flow/<name>.json` of the repository that owns the flow. It is always read **on the base branch**, never from the change it judges.

Design side, run by a person or a skill:

| Command | What it does | What it guarantees |
|---|---|---|
| `flow fit` | Reads the answers the skill recorded about the team's path | Prints one of: "by hand with `ai-sdlc` is enough", "ticket state and CI are enough", or the step and the symptom that would need an engine |
| `flow new <feature\|bug>` | Writes a definition from one of two templates (report §6) | The file passes `flow check` |
| `flow check` | Validates a definition | Refuses: a loop without a cap; a write to the outside without a key derived from the ticket; no stop point; no budget in dollars and minutes; a wait without a following premise check; a gate with no named judge or no deadline; an unknown step type |
| `flow place` | Takes each step through the grid, extended (below) | A destination per step, with the question that decided; the verdict "no step needs an engine" or the step that does |
| `flow next --event <file>` | The transition function: data in, data out, no network, no clock | One legal transition or a refusal; caps enforced; an unknown or contradictory state becomes `stopped: inconsistent`, never a guess |
| `flow render` | Generates the thin CI files; nobody writes them by hand | In every job: one run at a time per ticket with cancel written explicitly, a timeout far under the platform limit, the budget, the agent version pinned, a separate job for writes, agent configuration taken from the base branch |
| `flow status [--map]` | The level of the flow (section 5), each check with its origin | A level rises only on what a program read |
| `flow exits` | Reads the run records over a window | "stay", or the symptom that fired, with its numbers (report §7, last table) |
| `flow drill` | With agreement: replays one event twice, kills one job, lets one gate pass its deadline | Counts steps that ran again and writes that were duplicated |
| `flow scope` | Reads a list of repositories | Which use the flow, at which pinned version, where a copy diverges |

Run side, started by CI jobs. These four are the contract a Rust binary could take over:

| Command | What it does | What it guarantees |
|---|---|---|
| `flow claim` | Reads the ticket; if it is not ready, ends green; otherwise marks it in progress and writes the run identifier, the definition's hash and the agent's version | A second event on the same ticket finds the marker and ends. The ticket is the deduplication store; the concurrency group is the lock |
| `flow run-step <name>` | Runs one code step, or one agent step through the adapter, with a turn cap and a dollar cap | Refuses a result that does not match the step's schema; counts an empty turn as a failure |
| `flow report` | Last step of every job, always run | Status, attempt count, tokens, dollars and minutes written on the ticket and the PR by code, never by the agent |
| `flow sweep` | Scheduled; lists "ready" tickets with no run, "in progress" tickets with no live run, gates past their deadline | Dispatches the first, flags the second with a visible `stopped` and its reason, reminds or escalates the third. A lost event is never silent |

**The grid, extended in a separate data file.** `placement.json` stays as it is, so the existing design fixtures do not move. A new file adds the questions the one-repository grid lacks (report §7): how long the step lives and what must survive; whether a human decides and can really judge; how many repositories need it; whether the piece compensates for a model weakness. New destinations: `ticket_state`, `human_gate`, `no_gate` (a refusal: the person could not judge what they approve), `reusable_workflow`, `campaign` (a fan-out by script, one writer per unit), `durable_engine`. There is **no** destination "graph framework" for a step that runs around a coding agent; the explainer says where LangGraph fits instead.

**Where the state lives.** One label per state on the ticket or the PR (`flow:ready`, `flow:planning`, `flow:plan-review`, `flow:coding`, `flow:ci`, `flow:human-review`, `flow:rework`, `flow:merging`, `flow:done`, `flow:stopped`) and one machine-written comment, the run record. A person steers with the same objects: add `flow:ready` to start, add `flow:stopped` to stop, add `flow:merging` to authorise a merge.

**Where a human approves.** Five places: the start; the plan (only for changes computed as large or sensitive); the PR review, where the requester cannot approve; the explicit merge authorisation; the production gate of the delivery pipeline. Each is a ticket or PR state that only a human account may set, and whose change is the event that starts the next job. That is the one form that exists on GitHub, Forgejo, Gitea and GitLab CE (report §3.3). Where the forge has environment approvals, the production gate uses them too. The pause-and-resume of the agent itself (`defer`) is not used: it needs a session file on local disk, which a fresh CI job does not have (report §6.3). The agent never holds the merge or the deploy right.

**The agent inside a step.** A vendor coding agent, run once, without a terminal, behind one small adapter interface (workspace, rendered prompt, permission settings, timeout in; outcome, session identifier, error class, cost out). First adapter: `claude -p --output-format json --json-schema …`, with the permission mode, `--permission-prompts none` and `--bare` or not always passed explicitly. Second: `codex exec --json --output-schema …` (report §4.3). Only documented flags. The agent is told to run one `ai-sdlc` skill. Its version is pinned and written in the run record; a contract test runs before any bump. It authenticates with an API key held as a CI secret, and gets no tracker or forge token.

**What is not solved by this design, said plainly.**

- A job that fails late is paid twice. Short jobs limit it; nothing removes it short of an engine.
- A self-hosted runner isolates nothing by itself. On Forgejo there is no "safe outputs" product; the read-only agent job, the base-branch configuration and a dedicated runner user are ours to write and to test.
- A tracker outside the forge (Jira, Linear) must call the forge's dispatch endpoint, or wait for the scheduled sweep. The ticket may show a stale status. A Jira rule reaches the forge only on a few allowed ports and from Atlassian's addresses: a forge on a private network needs a relay or the sweep (report §3.3).
- State lives in three places (ticket status, labels, a PR marker). "What happened to ticket X" is answered by `flow status`, not by one table.
- One ticket maps to one repository. A feature across repositories is split by a human at the ticket step.
- On Forgejo the job's own token cannot be made read-only today (work is announced, not shipped), and a change made with it starts no workflow, so chaining needs a bot account. Both must be tested on the exact version (report §9.1).

---

## 4. The suite of skills

Seven skills in `plugins/harness-flow/skills/`. Each one shows a map before any question, measures nothing itself, and calls the CLI for every figure. Each also triggers on the French phrasing of the same requests, as the existing skills do.

### `flow-why`

- **Triggers when** the user asks "do I need LangChain, LangGraph, Temporal, a workflow engine, Rust for this?", "what is LangGraph for?", "is LangChain still useful?".
- **Shows first** the decision table of the report §8, with the date of the facts.
- **Asks** one thing: what are you building (a ticket workflow around a coding agent, your own agent application, an agent product for users, a change across many repositories)?
- **Produces** a plain answer for that case: use it or not, why, what it would cost, and the measurable symptom that would change the answer. It changes nothing.
- **Code behind it**: `flow fit`; the docs of section 6.

### `flow-map`

- **Triggers when** the user says "we want a workflow for feature tickets", "handle a bug ticket end to end", "draw our path from ticket to production".
- **Shows first** the reference flow for that ticket type (report §6), each step typed code, agent or human, with the stop points, and the level of each repository named (`harness status`).
- **Asks**, once: which ticket type; where tickets live; which forge; where the flow must stop. Default stop: `ready_pr` for a feature, `root_cause` for a bug.
- **Produces** `.harness/flow/<name>.json`, and the same map redrawn with the team's own names.
- **Code behind it**: `flow new`, `flow check`.

### `flow-place`

- **Triggers when** the user asks "is a skill enough here, or do I need code?", "where does this step go?", "do we need an engine for this?".
- **Shows first** the output of `flow place` on the definition: one line per step with its destination.
- **Asks**, only for steps the definition leaves open: is the right output determined by the inputs; must it happen every time; how long does it live and what must survive; can the person who approves really judge it.
- **Produces** for each step one sentence: "a skill is enough", "this is code", "this is a hook", "this is a CI job", "the ticket holds this", "this is a human gate", "no gate here", or "this would need an engine", with the question that decided and the source behind it. It ends with the verdict for the whole flow.
- **Code behind it**: `flow place`, `harness place` for pieces inside one repository.

### `flow-step`

- **Triggers when** the user says "next step of our flow", "wire the plan step", "continue the workflow".
- **Shows first** `flow status --map`: the ladder, "you are here", the target, the next step.
- **Asks** for agreement on one step, with what it costs and changes; and, at the first agent step, which agent runs it and the name of the secret that holds its key.
- **Produces** the smallest next piece and only one: a step's pipeline file from `flow render`, its cap, its schema, its prompt file. It shows before and after, runs `flow check` and the recorded sequences, then stops. Same contract as `harness-step`.
- **Code behind it**: `flow render`, `flow check`, `flow next`, `flow report`.

### `flow-gate`

- **Triggers when** the user asks "who approves what?", "where should it stop?", "can the agent merge?".
- **Shows first** the five approval places and, for each, how it is held today on the forge: asked, checked, enforced, or could not read.
- **Asks**: who may start a run; above which size a plan needs approval; who may authorise a merge; whether delivery is in scope; the stop point.
- **Produces** the gate settings in the definition and the exact forge changes to make (branch rule, environment reviewers, who may set a label). It applies a forge change only when asked. It refuses a gate nobody can judge.
- **Code behind it**: `flow check`, and the forge reader shared with `harness team forge`.

### `flow-watch`

- **Triggers when** the user asks "where is ticket 123?", "what did it cost?", "why did it stop?", "is CI still enough?", "the model changed, what should we remove?".
- **Shows first** the run record of the ticket, or the table of `flow exits` over the window.
- **Asks** nothing by default.
- **Produces** the smallest fix for each symptom seen (a shorter job, a cap, a sweep). Only when an exit symptom is measured does it say so, explain what an engine would change and cost, and say that this is where a Rust worker on Temporal becomes a sensible choice (or on AWS Lambda durable functions, for a team already on Lambda). At a model change, it lists the instruction and skill pieces of the flow with the model and date they were last tested against, and proposes to remove one at a time.
- **Code behind it**: `flow status`, `flow exits`, `flow sweep`, `flow drill`.

### `flow-share`

- **Triggers when** the user says "use this flow in our other repositories", "several teams want it".
- **Shows first** `flow scope`: which repositories use the flow, at which version, where a copy diverges.
- **Asks** the list of repositories and who owns the base.
- **Produces** a pinned plugin version per repository, copied pipeline files replaced by calls to the reusable ones, a proposal of what belongs in an organisation rule, and for a change across repositories a fan-out with one PR per repository.
- **Code behind it**: `flow scope`, `flow render`.

---

## 5. A ladder for a team flow

Same rules as `docs/maturity.md`: a level is **measured**, never declared; each failing check carries the next action; a level is a place where you can stay; the team states its target and nothing is proposed beyond it. The unit is one flow.

| Level | Name | What it means | Checks a program reads |
|---|---|---|---|
| 0 | None | The phases are chained by hand | no definition |
| 1 | **Mapped** | The flow is written down and every step has a place | The definition passes `flow check` · every step has a destination from `flow place` · a stop point and a budget are set |
| 2 | **Shadow** | The flow runs on real tickets and only comments (readiness, plan, root cause) | At least 10 runs ended · every run ended with a status written by code · zero tickets with two runs at once · a cost on every run record · the sweep ran in the window · one `flow drill` passed with no duplicated write |
| 3 | **Drafting** | Runs end with a draft PR; CI and review results come back to the run | Runs reached `draft_pr` · no run exceeded a cap or the budget · each gate of the flow is "enforced" on the forge, not only "asked" · the repositories it writes in are at repository level 3 |
| 4 | **Delivering** | Runs reach a reviewed PR and merge only on a human's word | Every merge of the window was authorised by someone other than the requester · no silent loss found by the sweep in 30 days · cost per merged PR recorded and under the budget · no agent PR fixed after the fact in the last harvest |

Beside the ladder, as options and not as levels:

- **Beyond merge**: watching a rollout, the closure check of a bug flow.
- **Several repositories**: the view of `flow scope`.
- **The exit**: an engine, when `flow exits` says so.
- **Automatic approval of low-risk changes**: not offered. The companies that do it started in shadow with hard exclusions and a control group (report §5.1); it is out of scope until a team asks.

What the level does not say: that the flow delivers better. That proof is the trend of review time, fixes after the fact and cost per merged PR. The thresholds (10 runs, 30 days) are my proposal; nothing in the notes validates them or the order of the levels.

---

## 6. The docs to write

In `docs/workflow-harness/`. Each ends with "the symptom that would make you need it" and carries the date of its facts. The content comes from the report and the notes, with their evidence labels.

| File | Outline |
|---|---|
| `decide.md` | The eight questions for one step · the destinations · the symptom table for the engine · how to read a `flow place` output · three worked examples |
| `langchain.md` | What it is in one paragraph · the 2022 problem it solved · the timeline to 1.0 · what aged and the proof · what the 1.x package still gives · when to use it, when not · "you do not need it to drive a coding agent" |
| `langgraph.md` | The idea: a graph, one saved state · the four words to keep (run identity, checkpoint, interrupt, replay) with a ten-line example · the fine print (replay runs the step again, nothing watches your process, the store is an attack surface) · who uses it and how they wrapped it · why the Radar moved it to Trial · when to use it, when not · the same four words on CI and on an engine |
| `engines.md` | What durable execution is, with a picture of one run · what it does not give (at least once, versioning, stale facts, it retries a looping agent) · Temporal, AWS Lambda durable functions, Restate, DBOS side by side with versions and dates (Inngest's Rust crate is stale) · who uses one, products against internal flows · price and what it really costs |
| `ci-as-engine.md` | How a ticket state and short jobs make a flow · the limits table · the five cheap protections and the failure each one prevents · what stays fragile · GitHub, GitLab, Forgejo differences |
| `rust.md` | The verdict table by building block · how a program drives a coding agent as a child process · what the large Rust agents show and do not show · the shape of the engine exit in Rust · what to re-check in mid-2027 |
| `flows.md` | The feature and bug reference flows, each step typed, with stop points and the incident variant · where each `ai-sdlc` skill plugs in |
| `costs.md` | Published prices per run · the estimate per ticket and why it is only arithmetic · what multiplies the bill · how `flow report` counts |

| `forges.md` | What GitHub, Forgejo, Gitea and GitLab CE give and lack as a workflow runtime · the bridge from Jira or Linear (rule and its port and address limits, relay, sweep) · what to test on your own version |


## 7. The language question

**Short answer.** Keep Python, standard library only, for the first version. Do not start in Rust. Design the run side so that Rust can take it over, and say exactly when that pays.

Why Python first:

- In the recommended design the code is a set of short commands started by a pipeline. Nothing lives long. What teams report gaining from Rust (flat memory over days, a core other programs embed, native sandboxing) applies to a long-lived program (report §4.5).
- For a command-line tool called from CI, the choice is about distribution and review. Standard-library Python is the cheapest to change where Python is on the runner, and it is on this repository's runner.
- The rule of `AGENTS.md` forbids a dependency outside the standard library in the CLI, and the README promises "nothing to install". A Rust binary needs a build, per-platform artefacts with checksums and an installer; no workflow of this repository releases anything today.
- The gates, the grid, the fixtures and the grader are Python. A Rust binary would call them through a shell, so runners would need Python anyway.
- The language is not what makes orchestrators fail: every failure read is a design failure (report §4.5).

What Rust would really buy, and where:

| Part | Language | Why |
|---|---|---|
| Skills, prompts, docs | Markdown, loaded at run time | Iteration speed |
| Definition, grid, checks, transition, render, status, exits, drill | Python, standard library | Above |
| The four run commands (`claim`, `run-step`, `report`, `sweep`) | Python first. **Rust is the candidate second implementation** | One static binary, no runtime on the runner, a state machine where a missing case is a compile error. It pays the day runners have no Python (Forgejo's default image), or many repositories pin one tool |
| Generated pipeline files | The forge's YAML | It is the runtime |
| The coding agent | The vendor's own program, as a child process | No vendor agent loop exists in Rust, and the Claude Agent SDK spawns the same process. A hand-written adapter gets the same agent, not the SDK's in-process hooks and permission callbacks (report §4.3) |
| Evaluation of the suite | Python (the existing grader) | Missing in Rust |
| A relay for Linear, if needed | One file, any language | Stateless, about a page |
| **The engine exit: a worker on Temporal** | **Rust** | One of two durable SDKs at 1.0 in Rust, and the one that runs on any host; young, no named production user. The other, AWS Lambda durable functions (1.0 on 2026-11-19), fits only a team on Lambda. A Go or Python worker can replace it without touching the rest |
| A long-lived orchestrator, if one of the six conditions is observed (report §5.3) | Rust is reasonable | Unless the reason is live interaction inside a run: then TypeScript or Python with the vendor's SDK |

**The honest answer to "ideally, in Rust".** LangChain and LangGraph do not exist in Rust. No lab ships a Rust agent SDK. Rust is good at exactly the part of this suite that must hold (a typed state machine, one binary), and that part is a few hundred lines started by CI. So Rust is a real option for it, not a need. If the owner wants it for its own sake, the cost is known: a release pipeline to build and own, cargo builds on a runner with slow disks, two languages in one repository, and one human able to review it. Question 2 is where to say so; the first slice is the same either way, because the contract comes first.

---

## 8. First slice, then the epics

### 8.1 A first slice, one week

No pipeline, no agent call, no account, no key.

**Built**

- The definition format and two templates, `feature` and `bug`, from the reference flows.
- `flow new`, `flow check`, `flow next`, `flow place`, `flow status --map`.
- The grid extension as a separate data file.
- `docs/workflow-harness/decide.md`.
- A new fixture family `fixtures/flow/`:
  - about twelve recorded event sequences with the expected states: an event delivered twice, events out of order, a cap reached, a budget exceeded, a human stop, an unknown label, a rework loop, a bug already fixed, a low-confidence root cause;
  - three flows to place: the feature flow, the bug flow, and a trapped one where exactly one step truly needs an engine and one gate cannot be judged by anyone.

**Measured, by program**

- For every state and every event, `flow next` gives one transition or a refusal: checked over the whole table.
- No sequence of events, however long, passes a cap: checked on generated sequences.
- `flow place` answers "no step needs an engine" on the two reference flows, and names exactly the planted step and the planted gate on the trapped one.
- Both existing suites still pass.

**What it proves and what it does not.** It proves the definition, the transition function and the grid hold on paper cases written by us. It does not prove that a flow runs, nor that the skills help anyone: those are epics 3 and 7.

### 8.2 The epics after it

| # | Epic | What it delivers | Depends on |
|---|---|---|---|
| 1 | **Map** (the slice above) | Level Mapped on paper | nothing |
| 2 | **Explain** | The seven other docs · the skill texts `flow-why`, `flow-map`, `flow-place` | 1 |
| 3 | **Run in shadow** | `flow render` for GitHub, then Forgejo · `flow claim`, `flow run-step`, `flow report`, `flow sweep`, `flow drill` · the Claude Code adapter with its contract test, and a fake agent for the fixtures · the skill `flow-step` · level Shadow · a first real flow on this repository: the bug flow, stopping at `root_cause`, comments only | 1; questions 5 and 6 |
| 4 | **Gate** | The forge checks of `flow check` · the skill `flow-gate` · level Drafting | 3; the forge reader shared with `harness team forge` (slice 3 of team-assessment.md): build it once |
| 5 | **Watch** | `flow exits` · cost per ticket · the skill `flow-watch`, pruning included · level Delivering | 3, and some weeks of run records |
| 6 | **Share** | `flow scope` · the thin file per repository · the skill `flow-share` · a tracker outside the forge (Jira rule where the forge is reachable, a relay otherwise, or the sweep alone) · the Codex adapter · `forges.md` | 4; tests on the owner's Forgejo version |
| 7 | **Measure the skills** | Blind runs on `fixtures/flow/`, graded by program; fixes to skill texts only | 2 to 4; only on the owner's request |
| 8 | **The Rust run binary** (optional) | The four run commands as one static binary, graded by the same recorded sequences; a release job with checksums | 3; opened by question 2, or when a team's runners have no Python |
| 9 | **The engine exit** (optional) | A reference worker in Rust on a managed Temporal, one workflow per ticket, reading the same definition. The engine is chosen again at that date, not now | 5; opened only if `flow exits` fires on a real flow, or by the owner's decision |

Each epic adds its rows to the progress plan of `docs/capabilities.md` in the same change, as `AGENTS.md` requires.

Assumptions taken without asking: the code lives in the existing CLI; the definition is JSON; the plugin is the third entry of the same marketplace; `harness-team` and this suite share one forge reader. Not assumed: that Forgejo behaves like GitHub. Its concurrency default differs and it has no approval gate (report §3.3).

Not verified in this study: nothing was prototyped; only the sources of the fourteen claims of report §11 were opened again, the others are as the notes read them; the Forgejo facts come from documentation, not from a running instance; the one-week estimate has no prototype behind it; the ladder thresholds and order are mine.

**What the fact-check changed here.** Not the recommendation. Design A, Python first and the engine as a measured exit do not rest on the claim that was wrong ("Temporal is the only durable engine supported in Rust"): that claim touches only epic 9, where a second option now exists for teams on AWS Lambda. Two arguments were weakened and are now worded as such: "the only" for Cursor's figure and for Duolingo is "the only one found", and the 25% CI failure figure is a capped sample, so it argues neither for nor against A with any force. One practical limit was added: a Jira rule cannot always reach a self-hosted forge directly.

---

## 9. Questions

1. **Language.** Keep `harness flow` in Python, standard library only, for the first version? Default: yes.
2. **Rust.** Do you want the four run commands rewritten as one Rust binary (epic 8) as soon as epic 3 works, whatever the measurements say, to learn and to ship one binary? Default: no; it opens when a team's runners have no Python or when you ask. Either way the contract and the first slice are the same.
3. **A third plugin.** `harness-flow`, beside `harness-ai` and `ai-sdlc`, sharing the CLI? Default: yes.
4. **Order with `harness-team`.** Build slice 1 of this proposal first, since it needs no forge, and build the forge reader once when the first of the two reaches it? Default: yes.
5. **First real flow.** This repository, the bug flow, stopping at `root_cause`, comments only, started only by a label you set? Default: yes.
6. **The runner.** The repository's runner is on your server and is not disposable. Accept an agent job there under these limits: a dedicated user, started only by your label, never on a PR from someone else, no production credential on the machine? Default: yes, for a private repository with one owner; to revisit before any publication.
7. **The key.** An API key as a CI secret for the agent, not a subscription token, as both vendors ask for unattended use? Default: yes. Only you can create it.
8. **Forges.** GitHub first, then your Forgejo (after the four behaviours of report §9.1 are tested on your version), GitLab later? Default: yes.
9. **How your Forgejo is exposed.** Is it reachable from the internet on port 443, so that an outside tracker could call it directly, or only on a private network? Default assumed: reachable on 443; if not, epic 6 plans a relay or the sweep alone. Only you know.
10. **Trackers.** Forge issues first; Jira or Linear only in epic 6? Default: yes.
11. **The ladder.** Mapped, Shadow, Drafting, Delivering, with the engine as an exit and not a level? Default: yes.
12. **The engine, if the exit ever fires.** Temporal Cloud rather than a self-hosted server, since no source gives the staffing to run one? Default: yes; to decide only then. If your teams run on AWS Lambda, say so: Lambda durable functions would then be compared first.
13. **Blind runs.** None until you ask, and not before epic 3 is done? Default: none.
14. **The research notes.** Keep the eleven notes in the repository beside the two documents? Default: yes.
