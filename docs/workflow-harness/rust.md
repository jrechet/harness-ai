# Rust for a team workflow: where it is a real option, and where nothing exists

Date of the facts: 2026-11-21, from [report.md](report.md).

Rust is a real option for the part of a workflow that is a compiled program: the state machine, a command-line tool, a tool server, a worker on a durable engine.
Nothing exists in Rust for the agent itself: no LangChain, no LangGraph, no agent SDK from Anthropic or OpenAI, no evaluation tooling.
In every language the coding agent sits on the other side of a process boundary, so the language of your program changes less than it seems.

You are a tech lead and someone on the team asks "could we write this in Rust?". This page answers building block by building block, then shows the one part every Rust program has to write by hand, then says what the large Rust agents prove and do not prove.

**Words used, defined once.**

- **Agent**: a model that calls tools in a loop until a task is done. **Coding agent**: an agent that edits a repository (Claude Code, Codex, goose).
- **Agent loop**: the code that sends the conversation to the model, runs the tools it asks for, and starts again. An **agent SDK** is that loop offered as a library.
- **Child process**: a program started by another program, which reads what it prints.
- **Crate**: a Rust library, published on the registry crates.io.
- **MCP** (Model Context Protocol): the protocol through which an agent calls tools served by another program.
- **Durable execution**: a runtime records each finished step, so a run that crashes or waits for days continues where it stopped. A **durable engine** is a product that gives it (Temporal, Restate, DBOS). See [engines.md](engines.md).
- **Worker**: your program, connected to an engine, that runs the steps the engine hands it.
- **Idempotent**: safe to run twice.
- **CI**: the pipelines of the forge, the server that hosts the repositories. A **runner** is the machine that executes one job.
- **Skill**: a Markdown procedure an agent loads when a task matches. **Hook**: a script the agent's runtime runs at a fixed point.
- **Sandbox**: what stops a command the agent runs from reading secrets, reaching the network or damaging the host.
- **1.0**: the first version whose authors promise not to break their interface without warning. "Pre-1.0" means no such promise.
- **Evidence labels**, kept from the report: [M] read from a registry, a repository or a specification; [V] said by a company about itself; [S] said by a third party.

## 1. The verdict, building block by building block

The scale is the report's: **first-class** (official or standard, 1.0 or later, used by large products), **usable** (works, but run by volunteers or pre-1.0), **missing** (report §4.4). Two rows use other words, also the report's: "well suited" (the language does the job with no framework) and "supported, young" (explained below).

| Building block | Rust today | Best option | What to know |
|---|---|---|---|
| State machine of a workflow | **Well suited** | plain `enum` and `match` | A missing case is a compile error. No framework needed |
| Command-line tool, one binary | **First-class** | the general ecosystem | No runtime to install on the runner. The reason OpenAI and GitHub give |
| MCP server or client | **First-class** | `rmcp` 3.11, official | Three major versions in five months [M]: pin the version |
| Sandboxing of commands | **First-class** | `landlock`, `seccompiler` | Shipped in Codex |
| Durable execution | **Supported, young** | `temporalio-sdk` 1.2 on any host; `aws-durable-execution-sdk` 1.0 if your code runs on AWS Lambda | Section 4 |
| Vendor agent loop as a library | **Missing**, one exception | start `claude -p` or `codex exec` as a child process | The exception is the GitHub Copilot SDK, tied to Copilot as the model service |
| Model client, Anthropic or OpenAI direct | Usable, weak | `rig`, `genai`, `async-openai` | All pre-1.0, kept by volunteers; new API features arrive late |
| Model client through a cloud | First-class | the official AWS Bedrock and Google Vertex crates | Official, 1.x |
| Graph of agent steps | Usable, thin | plain enums; `graph-flow` is small | No LangGraph |
| Tracing | Usable | `tracing` with OpenTelemetry | The Rust OpenTelemetry project marks traces as Beta [M]; no LangSmith client |
| Evaluations | **Missing** | run them from outside the binary | A grader sends inputs and reads outputs: any language does it |
| LangChain, LangGraph | **Missing** | none | Nothing official; small community crates that break often [M] |

(All rows: report §4.4 and §4.2; note rust_ecosystem.md, section 6.)

Three rows deserve one more sentence each.

- **The agent SDKs.** The Claude Agent SDK and the OpenAI Agents SDK exist in Python and TypeScript only [V][M]. A crate named `claude-agent-sdk` exists on crates.io; it points to a repository that does not exist and belongs to an individual. It is not an Anthropic product [M]. Check the owner of any crate with a vendor's name in it (note rust_ecosystem.md, section 3.2).
- **Durable execution.** The source note grades Temporal "first-class". The report lowers it to "supported, young", because the scale asks for "used by large products" and no production user of the Rust SDK is named (report §4.4).
- **Evaluations.** Nothing with real adoption was found. It matters less than it looks, since the grader can sit outside the binary; that conclusion is the note's own reading, not a measured fact (note rust_ecosystem.md, section 6).

Why not take the one exception? The Copilot SDK loads the Copilot runtime into your own process by default. Its README says this "provides neither crash isolation nor a sandbox", and a Copilot subscription is required unless you bring your own model key [V] (note gap_rust_orchestrator_agent_interfaces.md, section 1.4).

What "the choice of Rust" costs and buys, as the teams that made it report:

| Recurring benefit | Who names it | Recurring cost | Who shows it |
|---|---|---|---|
| One binary, nothing to install | OpenAI, GitHub, one small team [V] | You write more yourself: no vendor SDK, no framework | Every large team wrote its own loop |
| Low, flat memory; fast start | All; figures only from small teams and framework authors | Prompt tuning waits for the compiler | One small team: full rebuild 2 min 17 s [V] |
| A core other languages can load | GitHub, Temporal [V] | Libraries change fast | `rmcp`: three majors in five months [M] |
| Native sandboxing | OpenAI [V] | Bugs of lifetimes and shared state during a port | GitHub: dozens of regressions, all fixed [V] |

(Note rust_ecosystem.md, section 5.7; report §4.1.)

One thing Rust does not buy: the duration or the model cost of a ticket. An agent spends its time waiting for the model [S] (report §4.5).

## 2. How a Rust program drives a coding agent

It starts the vendor's command-line tool as a child process and reads JSON from it. This is the route Anthropic documents for languages without an SDK [V]. It is also what the Claude Agent SDK does itself: "The Agent SDK spawns and supervises a `claude` CLI subprocess" [V]. This is shown for Claude only: the OpenAI Agents SDK is a library that calls the API in its own process, and nothing read says it wraps `codex` (report §4.3).

```
 your program (Rust, Go, anything)                the vendor's tool
 ┌──────────────────────────────┐   starts   ┌───────────────────────────┐
 │ state machine: which step?   │ ─────────► │ claude -p                 │
 │ adapter: builds the command, │            │   --output-format json    │
 │   sets turn cap, dollar cap, │            │ the agent loop, skills,   │
 │   deny-instead-of-ask,       │            │ hooks, tools, the model   │
 │   a timeout                  │ ◄───────── │ calls                     │
 │ reads ONE JSON result,       │   JSON on  └───────────────────────────┘
 │   checks it against a schema │   stdout        exits
 │ keeps the session ID         │
 │   to resume later            │   the process boundary is here, in every language
 └──────────────────────────────┘
```

What the two main tools document for this use (report §4.3):

| | Claude Code | Codex |
|---|---|---|
| The command | `claude -p --output-format json` | `codex exec --json --output-schema` |
| A result checked against a JSON schema | yes | yes |
| Resume a session later | by session ID | `codex exec resume` (note gap_rust_orchestrator_agent_interfaces.md, section 5) |
| Caps | turns and dollars (`--max-turns`, `--max-budget-usd`) | not read in the report |
| Unattended: deny instead of asking | `--permission-prompts none`, from Claude Code 2.1.259 | sandbox read-only by default |
| Pause for a human approval, resume later | yes, a documented `defer` decision | not read in the report |
| Release rhythm | about one release per working day | about every five days |
| Stability promise | none formal | none formal |

All [V], from vendor documentation.

**What a hand-written wrapper gets, and what it does not.** Python and TypeScript get a typed wrapper for free. Rust and Go write one by hand, a few hundred lines per agent, and own its upkeep. The wrapper gets the same agent, not the same interface. The documented route is one call that returns one result. The SDK holds a two-way stream that also carries hooks in the caller's process, permission callbacks and custom tools. A wrapper has those only if it implements that stream, and that stream has no stated stability promise (report §4.3; §9.1, item 9).

**Four things that bite, whatever the language** (report §4.3):

- **No stability promise.** Flags have been removed and defaults changed: `--enable-auto-mode` was removed, and since v2.1.302 a `-p` run with no mode set denies what needs approval [V] (note gap_rust_orchestrator_agent_interfaces.md, section 1.1). One change is announced: `--bare` will become the default for `-p`, which stops loading skills and hooks unless asked [V].
- **Hooks of the repository run.** Without `--bare`, a `-p` run executes the hooks configured in the repository it runs in, with no trust prompt [V].
- **Billing.** A change to how subscriptions cover programmatic use was announced in spring 2026, then paused on 2026-06-15. `claude -p` on a subscription still draws from the plan's limits [V]. Both vendors say: for unattended automation, use an API key [V]. `--bare` needs one: it does not read subscription credentials [V] (note gap_rust_orchestrator_agent_interfaces.md, section 1.1).
- **The neutral protocol is not settled.** ACP (Agent Client Protocol) is the only protocol that drives several agents the same way. Claude and Codex are reached through Node adapters, and its Rust crate had four major versions in five months [M].

The discipline the notes draw from this (note gap_rust_orchestrator_agent_interfaces.md, section 5): one small interface of your own with one adapter per agent; documented flags only; the agent's version pinned and written with each run; a contract test per adapter (start, read the result, resume, refuse) run before every version bump; API keys, not subscription tokens. No independent report was found of a team running these commands under a Rust program in production, with failure rates: the evidence is two code bases that were read (same note, section 6).

What stops the agent your program starts from reading secrets? The same note gives a ladder, marked as its own inference: first a dedicated runner user, one working copy per ticket and the agent's own sandbox; then a wrapper or a rootless container with a list of allowed network addresses; separate virtual machines only for untrusted code (same note, section 4).

Kiro, Amazon's coding agent (note labs_internal_stacks.md, section 5), reached the same process boundary after maintaining three engines, one of them in Rust [V] (report §4.3).

## 3. What the large Rust agents show, and what they do not

| Product | What is measured or said | Label |
|---|---|---|
| OpenAI Codex | About 97% Rust. Depends on the general ecosystem (async runtime, HTTP, `rmcp`, sandboxing, OpenTelemetry, SQLite) and on no agent framework, no model-client crate, no durable SDK | [M] |
| GitHub Copilot runtime | Moved from TypeScript to Rust in 2026: 832,378 lines, with dozens of regressions fixed on the way. The post gives no latency or memory figure | [V] |
| goose (Block) | A Rust core, same kind of dependencies, no agent framework. No post by Block explaining the choice was found | [M] |
| Temporal | Its Rust core has sat under its other SDKs for years; the Rust-facing interface is what is new in 2026 | [V] |

(Report §4.1; note rust_ecosystem.md, sections 3.4 and 5.)

**What they show.**

- A serious agent can be built in Rust. That doubt is settled (note rust_ecosystem.md, section 3.4).
- The shape they share: a Rust core that owns state, tools, sandbox and protocol, with thin SDKs in other languages talking to it. Codex ships TypeScript and Python SDKs over its Rust binary (same note, section 7).
- Their stated reasons: one binary with no runtime to install, native sandboxing, flat memory, a core other languages can embed [V] (report §4.1).

**What they do not show.**

- That a framework exists. Each of them wrote its own loop; Codex also wrote its own model client (note rust_ecosystem.md, sections 3.4 and 5.7).
- That Rust is the cheap route. Codex has 746 contributors on its repository [M]. Every team that chose Rust wrote more itself (report §4.5).
- That your case is theirs. Their reasons apply to a program that lives long or is embedded in others. A set of short commands started by a pipeline gains little from flat memory over days (proposal.md, section 7).
- That Rust makes an orchestrator reliable. Every failure report found is in TypeScript or Elixir, because that is where the deployed orchestrators are, and each is a design failure: no idempotency key, no clean-up of child processes, no lock, no sweep (report §4.5).
- Measured gains. Neither OpenAI nor GitHub published before-and-after latency or memory figures; no independent benchmark of Rust agent frameworks against Python ones was found (note rust_ecosystem.md, section 8).
- That the labs are "all Rust". Claude Code is TypeScript; GitHub's CI workflow compiler is Go (report §4.5; note labs_internal_stacks.md, pattern P13).

**Is there a Rust orchestrator to adopt?** No. They are worth reading, not depending on (report §4.5).

| Project | What it is | Why not to depend on it |
|---|---|---|
| vibe-kanban | The largest Rust code base that drives many agents; a board where a person launches each task | Its company shut down in April 2026; it is not a ticket workflow [M][V] |
| symphony-rust (the most active Rust port of OpenAI's Symphony specification) | The closest thing to a ticket workflow in Rust | 14 stars, two authors, Linear and macOS only [M] |
| A Rust orchestrator with GitLab, Forgejo or Gitea built in | | Not found; the search was cut short |

(Note gap_rust_orchestrator_agent_interfaces.md, sections 3 and 6.)

## 4. The shape of the engine exit in Rust

The **engine exit** is the day a team leaves "the ticket holds the state, CI runs each step" for a durable engine, because a measured symptom asks for it ([decide.md](decide.md), section 3). It is planned, not built: the proposal lists it as an optional last epic, and says the engine is chosen again at that date (proposal.md, sections 2.2 and 8.2).

Its planned shape: a managed engine; one engine workflow per ticket, with the ticket key as its identifier; agent steps left in CI jobs; the same definition file read by the worker. The worker is the part that can be Rust.

What a Rust worker can stand on today (report §4.1, §4.5; note rust_ecosystem.md, section 4):

| Engine | Rust SDK | State | Fits |
|---|---|---|---|
| Temporal | `temporalio-sdk` 1.2.0; 1.0 on 2026-09-04 | Vendor-supported 1.0. No named production user; no agent integration for Rust [V] | Any host: a server to run, or a service to buy |
| AWS Lambda durable functions | `aws-durable-execution-sdk` 1.0.0, 2026-11-19 | "The first stable release" per its release notes; two days old on the date of the facts; some AWS documentation pages do not list Rust yet [M] | Only a team whose code runs on AWS Lambda |
| Restate | `restate-sdk` 0.13 | Usable, pre-1.0; no maturity statement found [M] | A lighter server, if you accept pre-1.0 |
| DBOS | `dbos` 0.6 | "Pre-production" in its own words [V] | Not yet. A library on Postgres, no extra service |
| Inngest | `inngest` 0.1.1 | "Alpha" [V]; no release since 2024 [M] | Not yet |

**A corrected claim, in its corrected form.** The first version of the report said Temporal was the only durable engine supported for production in Rust. The fact-check found this wrong: there are two with a vendor-supported 1.0, Temporal on any host and AWS Lambda durable functions for a team on Lambda. The checkers found the AWS release notes but not AWS's own announcement page (report §11, claim C6 and "Not checked in this pass").

What the Temporal SDK asks of your code, in its vendor's words [V] (note rust_ecosystem.md, section 4.1):

- Workflow code must be deterministic: it must take the same decisions when replayed. Every side effect goes into an "activity".
- A detector of non-deterministic code is on by default, but it "cannot catch every change in polling order" and does not see a call such as reading the system clock.
- Activities can run more than once, so they must be idempotent.

And below all of them: if a run fits in one process and one day, none is needed. A table with one row per step is enough; Codex keeps its own state in SQLite [M] (the conclusion is the note's reading; note rust_ecosystem.md, section 4.4).

A Go or Python worker can replace a Rust one without touching the rest (proposal.md, section 7).

## 5. Where this leaves this project

Planned, not built, and a decision of the owner (proposal.md, section 7):

- The first version stays Python, standard library only. In the recommended design nothing lives long, and standard-library Python is the cheapest to change where Python is on the runner.
- Rust is the candidate second implementation of the four run commands (`claim`, `run-step`, `report`, `sweep`; all planned, not built). It pays the day runners have no Python, or many repositories pin one tool. Forgejo's default job image ships only Node [V]; that claim was not re-checked by the fact-checkers (report §4.5, §11).
- Rust is the proposed language of the engine exit's worker.
- The known price of choosing Rust for its own sake: a release pipeline to build and own, two languages in one repository, and people able to review it.

## 6. What to re-check in mid-2027

| Check | Why | Source |
|---|---|---|
| Has Anthropic or OpenAI shipped an official Rust agent SDK? | The verdict "missing" for the agent loop would change | report §9.2 |
| Has DBOS for Rust left pre-production, or Restate's Rust SDK reached 1.0? | A lighter engine exit than Temporal would exist | report §9.2 |
| Are there named production users of Temporal's Rust SDK, or of AWS's? | None was found; how either behaves under real load is not known | report §9.1, item 6 |
| Has the AWS SDK aged a few months, and do AWS's pages list Rust? | It was two days old | report §4.1 |
| Is there a stability promise for `claude -p`, its event format, or the SDK's two-way stream? Did `--bare` become the default? | Every adapter depends on it, in any language | report §9.1, item 9; §4.3 |
| Did the paused billing change for subscriptions come back? | It decides what an unattended run draws from | report §4.3 |
| Has the ACP Rust crate settled? | It is the only neutral way to drive several agents | report §4.3 |
| Is there evaluation tooling in Rust with real adoption? | "Missing" today | report §4.2 |

## The symptom that would make you need it

Rust for the command-line part, when one of these is true and counted:

- At least one runner you must use has no Python and you cannot add it.
- The same tool is pinned by several repositories, and you count version drift or install failures between them.

Rust for a long-lived program, only when one of the six conditions that justify such a program is **observed** on your own flow (report §5.3): a ticket joined across several repositories; a global money cap or fairness rule; an approval answered while the agent waits with its context; expensive warm state between steps; reaction under about a minute; late failures that cost more than running a service. One exception: if the reason is live interaction inside a run, the vendor's SDK in TypeScript or Python fits better (proposal.md, section 7).

A Rust worker on an engine, only after an engine symptom is measured on real runs and its cheap fix did not remove it ([decide.md](decide.md), section 3).

Never for these, because nothing measured supports it: a shorter ticket, a lower model bill, or a more reliable orchestrator by the language alone (report §4.5).
