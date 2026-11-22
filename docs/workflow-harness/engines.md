# Workflow engines: what durable execution gives, and what it costs

Date of the facts: 2026-11-21, from [report.md](report.md).

A workflow engine records each finished step of a run, so a run that crashes or waits for days continues where it stopped.
It does not make a step run only once, it does not stop an agent that loops, and it is one more system with rules to learn.
For a team ticket flow the default stays the ticket's state plus CI ([ci-as-engine.md](ci-as-engine.md)); an engine is an exit, taken when a measured symptom asks for it.

**Words used, defined once.**

- **Flow**: one team workflow for one kind of ticket. **Run**: one ticket going through it. **Step**: one unit of work in a run.
- **Agent**: a model that calls tools in a loop until a task is done. Here, a coding agent such as Claude Code or Codex.
- **CI**: the pipelines of the forge. **Forge**: where the repositories live (GitHub, GitLab, Forgejo).
- **Durable execution**: a runtime records the result of every finished step. After a crash it runs the code again, skips the steps already recorded, and continues.
- **Workflow engine** (or engine): a product that gives durable execution (Temporal, Restate, DBOS).
- **Replay**: running the workflow code again from its start, reading recorded results instead of doing the work again.
- **At least once**: a step may run more than one time, never zero times. **Idempotent**: safe to run twice.
- **SDK**: the library you write the workflow with, in one language.
- **Worker**: your program, which the engine calls to run the steps. **Managed engine**: an engine its vendor runs for you and bills by use (Temporal Cloud), as opposed to one you host.
- **Tracker**: where the tickets live. A tracker daemon is a long-lived program that polls it.
- **Evidence labels**, kept from the report: [M] read from a registry, a repository or a specification; [V] said by a company about itself; [S] said by a third party.

## 1. What durable execution is

The workflow is ordinary code. Each call to the outside (a model call, a tool call, a push) is a recorded step. After a crash the code runs again and skips the recorded steps. A wait of three weeks holds no process (report §3.2).

Teams put an agent inside such a workflow for four reasons (note orchestration_alternatives.md, section 4.1):

- **Long chains fail often.** Five steps at 99% reliability give about 95% for the chain; ten steps about 90% [V].
- **Tokens already paid.** Without recorded steps, a crash at step 14 repeats steps 1 to 13 and pays for them again. Microsoft lists "expensive token consumption" as a production reason [M].
- **Waiting for people.** An approval can take days. A durable wait holds no process and costs no compute [M].
- **Deploys and restarts.** A long run must survive a redeploy of the program that runs it.

The price of this is a rule on your code. The workflow code must be deterministic, so that it can be replayed, and every model call and tool call is a recorded step. Temporal says it this way: "The Workflow handles orchestration and must be deterministic. LLM calls and tool calls run in Activities" [V] (note orchestration_alternatives.md, section 4.1). Activity is Temporal's word for a recorded step. The agent stays free to choose its next action. The engine only guarantees that a choice already recorded is not made a second time.

### One run that crashes and resumes

A run of three steps. The machine dies during the third.

```
First attempt
  workflow code   step 1: plan       step 2: write code   step 3: open the PR
                      |                    |                    |
  the engine's    [1 recorded]        [2 recorded]         (nothing recorded:
  record                                                    the machine died
                                                            during the step)
                                                                X  crash

Second attempt: the engine starts the same code again, from its first line
  workflow code   step 1: plan       step 2: write code   step 3: open the PR
                      |                    |                    |
                  read from the       read from the        runs for real,
                  record: no model    record: no model     a second time
                  call, no cost       call, no cost             |
                                                           [3 recorded]
                                                                |
                                                              done
```

Two things to read in this picture.

- Steps 1 and 2 are not paid twice. This is what the engine sells.
- Step 3 ran twice. If the first attempt had already opened the pull request before the crash, the second attempt opens another one, unless the step recognises its own earlier write. The engine cannot know how far an unrecorded step went. This is "at least once", and it is the first line of the next section.

The same crash on CI: the job starts again from its first line, steps 1 and 2 run for real and their tokens are paid again (report §3.3). That difference is the whole case for an engine. How often it matters is a number to measure on your own runs.

## 2. What it does not give

Five limits, the first four from a third-party review [S] (report §3.2; note orchestration_alternatives.md, section 4.1, for the third).

| Limit | What it means for you | What you still write |
|---|---|---|
| Steps run **at least once** | A retry can repeat a side effect: a second pull request, a second comment | Idempotent writes: a key derived from the ticket, so a step recognises its own earlier write |
| **Versioning** is a discipline | Changing the workflow code while runs are suspended can break replay: the new code no longer matches the record | A rule for changing a workflow that has runs alive. Engines behave differently here (note orchestration_alternatives.md, section 4.1) |
| **Replay cost grows** with the length of the history | A long agent run gets slower to resume | Snapshots of a long run, the review's word; the study gives no more detail |
| **Facts go stale** during a long wait | After three weeks the branch has moved, the bug may be fixed | A check, after every wait, that the facts the run started from still hold |
| It **retries a looping agent** faithfully | An agent that loops and burns tokens looks like a step that keeps failing | A budget cap per run and a rule that counts an empty turn as a failure, in your code |

The last line is the report author's reading, not a sourced fact (report §3.2, marked "my reading"). It rests on the issue trackers: one user of a tracker daemon reports "This bug cost me 15M tokens" [M] (report §5.3). The threshold table of the study says of this symptom: "None. An engine does not fix this; it retries faithfully" (note gap_small_team_engine_threshold_and_cost.md, section 5).

One company's account shows the versioning limit in practice. After moving to an engine, Cursor changed its design to workflows that exit after one task instead of living for ever, which "makes version upgrades easier" [V] (note gap_small_team_engine_threshold_and_cost.md, section 1.5).

Three of these five are also needed by a flow on CI: the key derived from the ticket, the check after a wait, and the budget cap. Versioning and replay cost are the engine's own problems. `python3 cli/harness.py flow check` already refuses a definition without a key derived from the ticket (`write_without_key`), without a check of the facts after a wait (`wait_without_premise_check`) or without a budget (`no_budget`). It has no rule for empty turns ([ci-as-engine.md](ci-as-engine.md), section 3). An engine does not remove that work.

## 3. Four engines side by side

Versions and dates as read on 2026-11-21. The Rust column is there because a Rust worker is the shape the study gives to the engine exit ([rust.md](rust.md)).

| | Temporal | AWS Lambda durable functions | Restate | DBOS |
|---|---|---|---|---|
| What it is | A separate server; your workflow code is replayed | Checkpoint and replay inside AWS Lambda, runs up to one year | One binary, written in Rust, in front of your services; it journals each step | A library; the state is in your own Postgres, no extra server |
| What you operate | A cluster and a database, or the paid Temporal Cloud | Nothing, but the code must run on Lambda | One binary | Your Postgres |
| Version read | Server 1.32.2 [M] | Launched December 2025 | 1.8.1 [M] | Python library 3.6.0 [M] |
| Languages | Go, Java, Python, TypeScript, .NET, Ruby, PHP, Rust | JavaScript and TypeScript, Python, Java, Go, Rust, C# | TypeScript, Python, Java and Kotlin, Go, Rust | Python, TypeScript, Go, Java, Rust |
| Rust SDK | 1.0 on 2026-09-04, announced as generally available on 2026-09-23, now 1.2.0 (2026-11-09) [V] | 1.0.0 on 2026-11-19, "the first stable release" [M] | 0.13.0 (2026-10-28), before 1.0; no maturity statement found [M] | 0.6.0 (2026-11-10), "pre-production release, and isn't yet supported for production use" [V] |
| Waits for a human | "Signals", its name for what wakes a waiting run; waits of any length | Not read for this study | "Durable promises", its name for a wait the engine keeps | Wait for events |
| To know | The heaviest to run. No named production user of the Rust SDK was found | The Rust SDK was two days old on the date of the facts; some AWS documentation pages do not list Rust yet | Its licence is not a standard open-source one | The smallest step from a service that already has Postgres |

Sources: report §3.5 and §4.1; note orchestration_alternatives.md, section 4.2; note rust_ecosystem.md for the Rust versions and dates.

Three remarks on this table.

- **Inngest is left out on purpose for Rust.** Inngest is a live engine in TypeScript, Python and Go (1.53.0) [M]. Its Rust crate is 0.1.1, last published on 2024-11-01 and marked "alpha": do not count it as a live option [M] (report §3.5).
- **One claim of the study was wrong here, and was corrected.** A first version said Temporal was the only engine supported for production in Rust. The fact-check found the AWS 1.0 release of 2026-11-19 (report §11, claim C6). Both are young: two and a half months since Temporal's 1.0, two days since AWS's (report §4.4).
- **What was not found.** A named production user of DBOS for a coding-agent workflow; for Restate, only Replit, on Restate's own page; for Inngest, only cubic (section 4 below). Unit prices for Restate Cloud, DBOS and Inngest (report §5.2; note orchestration_alternatives.md, section 9; note gap_small_team_engine_threshold_and_cost.md, section 1.5).

Other engines exist and were only listed by the study, not compared: Hatchet, Cloudflare Workflows, Azure Durable Task, AWS Step Functions, Prefect, Airflow (note orchestration_alternatives.md, section 4.2).

## 4. Who uses one: products against internal flows

Two sentences are both true: "the labs use Temporal", and "only one company was found that names an engine for an internal workflow". They describe two populations (report §5.2).

| Company | What runs on the engine | Kind | Source |
|---|---|---|---|
| Cursor | The loop of its cloud agents, on Temporal | A product sold to users | Cursor's own post, 2026-06-02 [V] |
| Replit | The control of Replit Agent, on Temporal, one workflow per agent | A product | Temporal's case study, unnamed engineer; Restate's page says Replit has since moved there. No statement hosted by Replit was found [V] |
| OpenAI Codex | "core control flows", on Temporal | A product, as far as one sentence tells | A quote on Temporal's blog; no OpenAI page found [V] |
| cubic (2 to 20 employees) | A four-agent code review pipeline, on Inngest | A product | Inngest's customer page [V] |
| Duolingo | Multi-step agent workflows for employees (2025); since then its whole agent platform | **An internal workflow** | Duolingo's own posts, 2025-12-11 and 2026-08-04 [V] |
| Stripe, Spotify, Shopify, Ramp, WorkOS, Bitrise, OpenAI Symphony | Nothing named: a state machine, a daemon, a webhook service, an event log | Internal workflows | report §5.2 |

Sources: report §5.2; note gap_small_team_engine_threshold_and_cost.md, section 1.5, for cubic and the Replit detail.

How to read it:

- **A team that builds an internal ticket flow belongs to the last two lines.** Duolingo is the only company found that names an engine there. "The only one found" is an absence of evidence: the fact-check found no second company, and a search cannot prove there is none (report §5.2, §11 claim C9). OpenAI shows both sides: Codex, the product, is said to run on Temporal; Symphony, its own ticket runner, is a polling daemon with in-memory state and no engine [M] (note gap_small_team_engine_threshold_and_cost.md, section 2.1).
- **The one before-and-after figure found is self-reported.** Cursor says "one 9 of reliability" often before the move and "past two 9s" after [V]. The post gives no measurement method and does not separate Temporal from the other changes of the same period (report §5.1, pattern 7). The fact-check could not confirm it is the only such figure (report §11, claim C8).
- **Why the product teams moved.** Replit: failures far into a run, "pretty bad user experience to have the agent get super far into something and then hit a catastrophic error" [V]. cubic: reviews that "would sometimes fail without explanation" [V] (note gap_small_team_engine_threshold_and_cost.md, section 1.5).
- **Nobody was found going either way for an internal flow.** A move from CI to an engine for an internal coding workflow: not found. A team that removed an engine from a coding-agent workflow: not found (note gap_small_team_engine_threshold_and_cost.md, sections 2.2 and 2.3).
- **No first-hand account exists of a team of 5 to 50** running a ticket flow on any runtime, an engine or CI [M: searched and not found] (report §9.1).

## 5. The price, and what it really costs

**The fee is small.** Temporal Cloud lists about $50 per million actions with no base fee [V]; the figure was read through a search summary of the pricing page (note orchestration_alternatives.md, section 4.2). A ticket of 100 actions, 1,000 tickets a month: about $5 a month. That is arithmetic of the notes, not a bill anyone published (report §3.5).

**The cost is elsewhere** (report §3.5): one more system, a programming model with rules, and people who know it.

| What it costs | The figure found | Label and source |
|---|---|---|
| Writing one custom workflow, once the platform exists | "1-2 days" on average, against under 5 minutes for a declarative one | [V, self-reported] Duolingo (report §5.2) |
| Moving an existing agent control to a managed engine | "a couple of weeks" | [V] Replit (note gap_small_team_engine_threshold_and_cost.md, section 4.3) |
| A proof of concept | "a few hours" | [V] cubic, on Inngest (same note) |
| A limit met on the way | Docker-in-Docker on Temporal blocked "a large set of planned features" at the time | [V] Duolingo (same note, section 1.5) |
| People to run a self-hosted engine | **Not found.** Cursor, Replit and Duolingo give none | report §3.5, §9.1; note gap_small_team_engine_threshold_and_cost.md, section 4.3 |

Duolingo then went further on the engine, not back: the price did not stop it (report §5.2).

**What the engine saves, in the same units.** The study's own arithmetic: at $1 a run and a failure rate of 25%, 1,000 runs a month waste about $250. It adds that, at 5 to 50 engineers, the volume that makes late failures hurt "may never arrive" (note gap_small_team_engine_threshold_and_cost.md, section 5). The 25% is not a product failure rate: it is one day in one repository, a sample very likely capped at 100 runs, with test workflows in it (report §5.3). Run prices are in [costs.md](costs.md).

**Managed or self-hosted.** The study's order is: CI and ticket state first, a managed engine second, a home-made long-lived service last (report §5.3). When a symptom is measured, its choice is a managed engine with one workflow per ticket (report §8). A team whose code already runs on AWS Lambda can look at Lambda durable functions instead, after reading its limits: the Rust SDK is days old (report §9.2).

**What about LangGraph?** It saves state too, but nothing in the free library restarts a dead process, queues runs or keeps one run per ticket [M] (report §1). See [langgraph.md](langgraph.md).

## The symptom that would make you need it

Measure these on your own runs. Each one counts only if it is still there after its cheap fix on CI (report §7, last table; [decide.md](decide.md), section 3).

| Symptom, as a number | Cheap fix to try first | If it stays |
|---|---|---|
| More than about one run in ten dies far in and pays its tokens twice | Shorter jobs; progress written on the pull request between jobs | An engine |
| A wait must resume inside a multi-step computation whose intermediate results are expensive to rebuild | Model the wait as a ticket state | An engine |
| Many steps, each with its own retry and timeout rule, that shared CI workflows no longer express | Reusable CI workflows | An engine; count one to two days per workflow |
| Events from several systems must be handled in strict order, or "at most one run per ticket" must hold under real contention | One queue per ticket | An engine with one workflow per ticket, or a database constraint |
| Compliance asks for a step-by-step replay of every run | None: labels and a comment are not an audit trail (report §9.2) | An engine's history |

Four symptoms that look like a need for an engine and are not one (note gap_small_team_engine_threshold_and_cost.md, section 5):

- two runs on one ticket, or a comment posted twice;
- an event accepted, then nothing, and nobody told;
- an agent that loops and burns tokens;
- no way to say what a ticket cost.

They ask for a key derived from the ticket, one run at a time per ticket, a scheduled sweep, a budget cap and a cost line. [ci-as-engine.md](ci-as-engine.md) covers them.

What this tool reads today: `python3 cli/harness.py flow place` names an engine for a step only when its definition says `survives: midway`. The symptoms above are counted on real runs; the command that would count them, `flow exits`, is planned, not built.
