# What a ticket costs when an agent works on it

Date of the facts: 2026-11-21, from [report.md](report.md).

One agent pass costs about one dollar: three unrelated sources land there.
Nobody publishes the cost of a whole ticket; "$3 to $10 for a feature" is arithmetic, not a measurement.
The bill grows by multiplication (triggers, restarts, re-sent context, loops), so a flow definition must carry a budget, and today it does.

You are a tech lead and someone asks "what will this cost us per ticket?". This page gives the prices that are published, says honestly what is not known, names what multiplies a bill, and shows what this repository's `flow` commands already count and what they do not.

**Words used, defined once.**

- **Agent**: a model that calls tools in a loop until a task is done.
- **Run** (in the price tables of sections 1 to 3): one agent pass over one task: one review, one fix attempt, one implementation attempt.
- **Flow**: one team workflow for one kind of ticket. A **flow run** (section 4) is one ticket going through it, which is several agent passes.
- **Token**: the unit a model reads and writes, and the unit it is billed in.
- **Prompt cache**: text the model provider has already read and bills at a lower price when it is sent again.
- **CI**: the pipelines of the forge, the server that hosts the repositories (GitHub Actions, GitLab CI, Forgejo Actions). A CI minute is one minute of a machine running a job.
- **Trigger**: the event that starts a job (a push, a comment, a label).
- **Engine** (durable engine): a product that records each finished step so a run continues where it stopped. See [engines.md](engines.md).
- **Budget**: what one flow run may spend, in dollars and in minutes. **Cap**: the most times one flow run may enter a step.
- **Run record**: the small JSON document `flow next` returns and takes back with the next event: the state, the visits, what was spent.
- **Evidence labels**, kept from the report: [M] read from a registry, a repository or a specification; [V] said by a company about itself; [S] said by a third party.

Every price was read on 2026-11-21. Pricing pages change.

## 1. Published prices per run

| What | Price | Unit and sample | Label |
|---|---|---|---|
| Cloudflare, AI code review in GitLab CI | mean **$1.19**, median $0.98 | per review, 131,246 runs | [V] |
| Sentry, automatic fix (root cause, plan, code) | **$1.00** flat; a restart is billed as a new run | per run | [V] |
| GitHub's own agentic workflows, heavy runs | about **$1.20** | per run, one day; the tool's own estimate | [M] |
| GitHub's own agentic workflows, average | $0.086 and 9.6 CI minutes | per run, 100 runs, one day | [M] |
| One GitHub agentic workflow in detail | $1.00, 3,728,969 tokens, 110 model calls, 16 CI minutes | one run | [M] |
| Codex, "a typical task" | $0.08 to $0.60 | per task; the dollar figure is the note's arithmetic from credits | [V] |
| GitLab, code review flow | $0.25 | per execution | [V] |
| GitLab, security fix flow | $4 | per execution | [V] |
| Anthropic, managed code review with several agents | "generally average $15-25", about 20 minutes (March 2026). Today: "no flat per-review price" | per review | [V] |
| One agent against a set-up of three agents, same brief | $9 and 20 minutes, against $200 and 6 hours | one brief | [V] |
| GitHub Actions runner, Linux, 2 cores | $0.006 | per minute | [V] |

(Report §5.4 for the three figures in bold; note gap_small_team_engine_threshold_and_cost.md, section 4.1, for the others.)

The note sorts them into four bands (same note, section 4.2):

| Band | Price of one run | What lands there |
|---|---|---|
| Low | $0.05 to $0.60 | Small models, short tasks |
| Typical | about $1 | Cloudflare, Sentry, GitHub's heavy runs |
| High | $4 to $25 | Deep or multi-agent passes |
| Runaway | $100 to $200 | GitHub's hard cap ($100; its default cap per run is $10); the set-up of three agents ($200) |

**CI minutes.** One run takes 5 to 20 billed minutes, that is $0.03 to $0.12 at list price on a standard Linux runner. This is the note's arithmetic. It leaves out your own test suite, which usually dominates CI time. Machine time weighs when runs are short and many: on the day measured in GitHub's repository it would be about $5.78 against $8.58 of model spend. It becomes negligible on runs of one dollar and more (same note, section 4.2).

**Not found.** The credits one Jira agent run consumes. The current usage units of Devin: its pricing page no longer mentions them (same note, section 4.1 and section 6).

## 2. The estimate per ticket, and why it is only arithmetic

The notes' estimate (report §5.4):

| Ticket | Model spend | CI | How it is built |
|---|---|---|---|
| Feature ticket | **$3 to $10** | 30 to 120 minutes ($0.20 to $0.70) | Five to eight runs (readiness check, implementation, one or two CI-fix rounds, review, security pass) at about $1 each |
| Feature ticket with a deep review on each push | up to $30 to $60 | | The same, with a high-band review |
| Simple bug fix | **$1 to $3** | | One implementation pass and one review |

(Note gap_small_team_engine_threshold_and_cost.md, section 4.2.)

For comparison, the default caps of GitHub's agentic workflows are $10 per run and $50 per workflow per day [V] (note gap_small_team_engine_threshold_and_cost.md, section 4.1).

Why this is not a measurement:

- It multiplies a per-run price by a guessed number of runs. No source measures a ticket end to end (report §5.4; §9.1, item 2).
- The share of runs that end in a merged pull request is not published. Without it, a cost per run cannot become a cost per merged pull request (note, section 6, item 4).
- The per-run prices come from other teams, other models and other tasks than yours. The largest sample is code review, not implementation.
- The failure rate that would tell you how many runs are paid twice is not known. The one figure read, 25 failures in a sample of 100 runs in GitHub's own repository, is one day, a sample very likely capped at 100, with test workflows that may fail on purpose. It is not a failure rate of the product (report §5.3; §9.1, item 4).

So use the table to choose a first budget, not to promise a number. The only cost per ticket you can trust is the one your own runs write down (section 4).

## 3. What multiplies the bill

A bill grows by multiplication, rarely by the price of one pass.

| Multiplier | The case that shows it | The cheap protection |
|---|---|---|
| **Triggers** | A review on every push multiplies cost by the number of pushes [V]. Push and check triggers "can produce hundreds of runs per day" [V]. 9 review sessions on one pull request in a day [M] | One flow run at a time per ticket; start on a ticket state, not on every push |
| **Late failures** | A CI job that fails starts again from its beginning | Short jobs, so a failure repeats one job, not the ticket |
| **Context re-sent at each model call** | About 99% of one run's 3.7 million tokens were context sent again [M]. Cloudflare reports 85.7% of input tokens served from the prompt cache [V] | Prompt caching; less always-loaded text |
| **Loops with no budget** | "This bug cost me 15M tokens" [M]. One issue started 16 sessions in 45 minutes [M] | A budget per flow run; a cap on every loop |
| **Several agents instead of one** | 3 to 10 times the tokens of one agent for the same task [V]. $9 against $200 on one brief [V] | One agent, until a measured reason |
| **Long instruction files** | One study: context files raise inference cost by over 20% with no average gain in task success [M] | Short files, details in skills |

(Rows 1 to 4: note gap_small_team_engine_threshold_and_cost.md, section 4.2, and report §5.3. Rows 5 and 6: report §7; the $9 and $200 pair, the same note, section 4.1.)

Four things that do not multiply the bill as much as one would think:

- **The engine's fee.** Temporal Cloud lists about $50 per million actions with no base fee [V]. A ticket of 100 actions, 1,000 tickets a month: about $5, by the notes' arithmetic. The fee is not the cost. The cost is one more system, a programming model with rules, and people who know it. No source gives the staffing needed to host one yourself (report §3.5; §9.1, item 5).
- **The language of your program.** Rust buys nothing on the duration or the model cost of a ticket [S] (report §4.5; [rust.md](rust.md)).
- **A hosted sandbox.** About 10 US cents for a 30-minute run, one or two orders of magnitude under the model spend. This is the note's arithmetic from three vendors' pricing pages [V] (note gap_rust_orchestrator_agent_interfaces.md, section 4).
- **Waste from failures, at small volume.** At $1 a run and a 25% failure rate, 1,000 runs a month waste about $250. This is the note's arithmetic, on a failure rate that is itself one day's sample (note, section 5).

One warning that belongs here: **an engine does not stop a looping agent. It retries it faithfully.** The fix for a loop is a budget and a failure rule in code, on any runtime (report §7, engine table; [ci-as-engine.md](ci-as-engine.md)).

And one limit: where the agent runs as a CI action, the cost may not be readable at all. There is no supported way to read the cost of a run from Anthropic's GitHub action [M] (report §5.3).

## 4. How `flow report` counts (planned, not built)

The commands of this section are sub-commands of this repository's command line: `python3 cli/harness.py flow new bug` writes the bug template used below, `python3 cli/harness.py flow check <file>` reads it, and `python3 cli/harness.py flow next <file> --event <event.json> --run <run.json>` tries one event on it.

**`flow report` is planned, not built.** The plan: a last step of every job, always run, that writes the status, the attempt count, tokens, dollars and minutes on the ticket and on the pull request, by code and never by the agent. A cost per ticket over a window comes later still (proposal.md, sections 3 and 8.2).

What exists today is the rule that makes such a report possible. The flow definition holds a budget, `flow check` requires it, and `flow next` enforces it. Nothing here measures a cost: the caller says what each step cost, and the command adds, compares and stops ([flow-spec.md](flow-spec.md), sections 1 to 3; [flow-format.md](flow-format.md)).

**In the definition.** One key at the top of the file, both numbers above zero:

```json
"budget": {"dollars": 10, "minutes": 120}
```

That is the budget of the bug template; the feature template has 20 dollars and 240 minutes. Minutes are minutes of running steps. Waiting costs nothing. A step that loops also takes a `cap`, put on the step that costs (the agent), not on the cheap check after it.

**`flow check` requires it.** A definition with no budget, or with a number missing or at zero, is refused: "The flow has no budget in dollars and minutes for one ticket." A flow that holds is told its ceiling: "one ticket may cost up to 10 dollars and 120 minutes."

**`flow next` enforces it.** `flow next` takes one event and answers what the flow run does. It runs nothing and reads no clock. An event that ends a step done by a program or by an agent must carry what the step cost:

```json
{"id": "T-7:root_cause:1:cause_written", "type": "cause_written",
 "payload": {"dollars": 1.25, "minutes": 14}}
```

One ticket through the bug template, tried by hand. Each line is one event; the numbers are the ones the command printed:

```
event            cost reported     answer of flow next              spent          left
ticket_ready     $0     1 min      triage → premise                 $0     1 min   $10    119 min
still_fails      $0.75  9 min      premise → root_cause             $0.75  10 min  $9.25  110 min
cause_written    (none)            REFUSED: does not say its cost   $0.75  10 min  $9.25  110 min
cause_written    $1.25  14 min     root_cause → notify              $2     24 min  $8      96 min
cause_written    same event again  already taken into account       $2     24 min  $8      96 min
confident        $0     1 min      done: reached its stop point     $2     25 min  $8      95 min

the same ticket with a budget of 1 dollar, after the same ticket_ready:
still_fails      $0.75  9 min      premise → root_cause             $0.75  10 min  $0.25  110 min
cause_written    $1.25  14 min     STOPPED: more than its budget    $2     24 min  $0      96 min
```

The rules behind that picture ([flow-spec.md](flow-spec.md), section 3):

| Rule | What it means for the bill |
|---|---|
| An event that ends a program or agent step without both costs is refused | Nothing is spent without being counted. 0 is a cost; a missing cost is not. One exception: a deadline that ends the flow run carries no cost, since it comes from outside the step |
| A failed step reports its cost too (`step_failed`) | A failure is paid, and counted |
| A retry after a deadline says what the round cost | Six silent rounds cannot add up to nothing |
| The same event delivered twice changes nothing | A cost is counted once |
| A refused event costs nothing | It can be delivered again later without being counted twice |
| Above the budget, in dollars or in minutes, the flow run is stopped and the next step is not entered. Exactly on the budget is within it | The budget can be passed by one step at most |
| The answer gives what is left | The caller can cap the next step with it |
| A cap is reached: the flow run stops before paying one more round | A loop has a last round |
| The last event of a flow run may pass the budget: the run still ends as finished, and the answer says it went over | The record does not call "stopped" work that finished |
| Each cost, in dollars or in minutes, is rounded up to 4 decimals (for dollars, a hundredth of a cent) before it is added | A hundred tiny costs never add up to zero |
| A person's stop wins over the budget and the caps | |

**What this does not do yet.**

- It does not measure. The dollars and minutes are the ones the caller writes in the event. Reading them from the agent is the work of `flow run-step` (planned, not built). The agent tools document a dollar cap of their own, such as `--max-budget-usd` on Claude Code [V] (report §4.3). The figure the agent reports is itself an estimate: Claude Code calls its `total_cost_usd` a "client-side estimate" that "can differ from your actual bill", and its dollar cap is checked against that estimate [V] (note gap_rust_orchestrator_agent_interfaces.md, section 1.1).
- It does not write anything on a ticket or a pull request. That is `flow report` (planned, not built).
- It does not keep one queue per ticket. The guarantees hold for one run record passed from each call to the next, one event at a time. Holding that is `flow claim` (planned, not built).
- It does not stop a step in progress. Stopping ends the run record; cancelling the job belongs to the pipeline.
- It does not count tokens, and it gives no cost per ticket over a month.

## The symptom that would make you need it

You need a budget in the definition from the first day: `flow check` refuses a flow without one, and the cases of section 3 are why.

You need more than the budget, that is a cost line written by code on every ticket, when one of these is true:

- You cannot say what one named ticket cost. This is a row of the report's symptom table, and its fix needs no engine: the step writes tokens and dollars on the pull request (report §7).
- The provider's monthly bill and the sum of what your runs reported differ, and you cannot say by how much.
- More than one review session starts for one push, or two flow runs are alive on one ticket at the same time.
- A run ends with `budget_exceeded` more than once in a week, or the same step reaches its cap on several tickets.
- Runs fail late and pay their tokens twice, more than about one run in ten. This one is also an engine symptom: see [decide.md](decide.md), section 3.

None of these is an opinion about price. Each is a count you can read from run records, once something writes them.
