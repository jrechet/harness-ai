# Building a workflow harness for a team: state of the art

Date: 2026-11-21. State: a study. Nothing described here is built.

This report answers one question from the owner: we know how to instrument one repository; how do teams build a whole workflow, for example "a feature ticket or a bug ticket, end to end, up to production or stopping earlier", and which tools do they need for it (LangChain, LangGraph, a workflow engine, Rust)?

**What it rests on.** Eleven research notes in [research_notes/](research_notes/), written the same day. Each fact in them carries a label: *measured* (read from a registry, a repository or a specification), *vendor* (said by a company about itself) or *secondary* (a third party). I keep those labels as [M], [V], [S]. When I wrote it I did not open the URLs again: a source cited here is the one the note read. Afterwards, fact-checkers opened the sources of the fourteen claims the recommendation rests on; section 11 lists each claim with its status, and the text below carries their corrections. Keys in brackets such as `[radar-lg]` point to the Sources section, where each key has its URL. Sentences marked **My reading** are my conclusions, not facts.

**How much I read, said plainly.** Six notes in full: the decision criteria, the Rust ecosystem, the Rust orchestrator interfaces, the small-team threshold, the self-hosted forge and language note, and the LangGraph evidence note. The ticket-to-production note up to the start of its bug flow. The four others (the labs, LangChain and LangGraph, the alternatives, the team note) by their summary, their outline and their ladder section; for their details this report keeps what its first version drew from them. Where two notes disagree, the text says which one I follow and why.

**Words used, defined once.**

- **Agent**: a model that calls tools in a loop until a task is done. The model chooses the next step.
- **Coding agent**: an agent that edits a repository (Claude Code, Codex, goose).
- **Workflow**: a sequence where code chooses the next step, and a model fills in some steps.
- **Harness**: everything around the model that makes its work reliable: instructions, tools, checks, sandboxes, the loop.
- **Skill**: a Markdown procedure an agent loads when a task matches.
- **Hook**: a script the agent's runtime runs at a fixed point. The model does not choose whether it runs.
- **CI**: the pipelines of the forge (GitHub Actions, GitLab CI, Forgejo Actions). A **forge** hosts repositories and decides what may be merged.
- **Durable execution**: a runtime records each finished step, so a run that crashes or waits for days continues where it stopped.
- **Workflow engine** (or durable engine): a product that gives durable execution (Temporal, Restate, DBOS, Inngest).
- **Graph framework**: a library where you declare steps as nodes and transitions as edges (LangGraph).
- **Idempotent**: safe to run twice. Doing it twice has the effect of doing it once.
- **PR**: pull request.

---

## 1. In one page

**Should we use LangChain?** No. LangChain was glue code for models that could only return text (2022). Models now call tools and return structured data by themselves, and the old parts were moved to a legacy package `[lc-migrate]`. It is useful only if you call several model providers and want one interface. A team that drives an existing coding agent has no use for it.

**Should we use LangGraph?** Not for this project, and not by default for a team. LangGraph is a small runtime: a workflow as a graph with saved state, pause and resume `[lg-overview]`. It fits one case: you write your own agent application in Python or TypeScript, the graph is known, and you need pause and resume inside the process. A ticket workflow that drives a coding agent is not that case, and for it the 2026 evidence is unfavourable: checkpoints are written in the background by default [M] `[lg-source]`; the free library has no queue, no detection of a dead run and no "one run per ticket" lock; the server that adds them is under a non-open licence and its documentation lists a licence key among the variables needed to run it standalone [M][V] `[lg-api-pypi]` `[lg-standalone]`. The ideas of LangGraph (one run identity, saved state, a pause for a human, replay) are the right ideas and are worth teaching.

**Do they exist in Rust?** No. LangChain's organisation has one Rust repository of its own, an unrelated and archived example, plus eight forks of third-party data libraries [M] `[lc-rust-search]`. The community port of LangChain is small and published four major versions in two weeks [M] `[langchain-rust]`. Nothing serious ports LangGraph. The Claude Agent SDK and the OpenAI Agents SDK are Python and TypeScript only [V] `[claude-sdk]` `[openai-libs]`.

**Is Rust a reasonable choice, and for which parts?** Yes for the deterministic part of a harness: a state machine, a command-line tool, a tool server, a long-lived orchestrator, and durable execution (Temporal's Rust SDK is generally available since September 2026 [V] `[temporal-rust-ga]`; AWS published a 1.0 Rust SDK for Lambda durable functions on 2026-11-19 [M] `[aws-durable-rust]`). No for the agent loop itself, for anything LangChain, and for evaluation tooling: those are missing in Rust. The large coding agents written in Rust (Codex, goose, the Copilot runtime) use no Rust agent framework; they wrote their own loop [M] `[codex-repo]` `[goose]`. Rust does not make a ticket faster: the time is spent waiting for the model.

**How do the labs build their own workflows?** With a plain loop in ordinary code, not a graph. Around it: checks written as code, state kept in files, git and a run log stored outside the sandbox, credentials the agent never sees, and a human who approves the plan and the pull request. Companies that run ticket-to-PR flows wrote a small state machine in plain code with a cap on every loop (Stripe, OpenAI Symphony, Dropbox). A durable engine appears under agent *products* sold to users (Cursor, Replit, Codex). For an *internal* engineering workflow, Duolingo is the only company found that names one `[duolingo]`; a search cannot prove there is no other.

**What should this project build?** A third plugin, on the same model as the two existing ones. Skills help a team draw its workflow, place each step (skill, code, hook, CI job, ticket state, human gate, engine) and build it one step at a time. Code guarantees: the workflow definition, the transition function, the caps, the budget, and four short commands that CI jobs call (claim a ticket, run one step, report, sweep). The default runtime is the one teams already own: the ticket or the PR holds the state, CI runs each step, a coding agent works inside a step. An engine is a measured exit, offered only when a named symptom is seen. The code stays Python, standard library only, for the first version; the four commands are specified so that one Rust binary can replace them later, and Rust is the natural language of the engine exit. Details in [proposal.md](proposal.md).

**How sure is this?** The default rests on converging accounts and on issue trackers, not on a controlled comparison. No first-hand account exists of a team of 5 to 50 engineers running a ticket-to-PR flow on *any* runtime, CI included [M: searched and not found] `[gap-small]`. Section 9 says what would change the recommendation.

---

## 2. LangChain and LangGraph explained

### 2.1 What they are

| Product | Since | In one sentence | State in November 2026 |
|---|---|---|---|
| **LangChain** | Oct 2022 | A library that formats prompts, calls a model, and parses the answer; later, one interface over many model providers plus a ready agent loop | 1.5.2. Old chains moved to `langchain-classic` [M] `[lc-migrate]` |
| **LangGraph** | Jan 2024 | A runtime that runs a workflow as a graph of steps sharing one saved state | 1.2.24, MIT, Python and TypeScript [M] `[lg-repo]` |
| **Deep Agents** | Jul 2025 | LangChain's own harness (planning, files, sub-agents), its answer to Claude Code | 0.7.41, still 0.x; 41 releases in 16 weeks [M] `[lg-repo]` |
| **LangSmith** | Jun 2023 | The paid platform: traces, evaluations, hosting. Works without the libraries | Where the company earns money; $300M raised on 2026-11-13 [V] `[lc-series-c]` |

LangGraph does not need LangChain: its documentation says so `[lg-overview]`.

### 2.2 Why they were created

- **LangChain, 2022.** Models were text in, text out. Each provider had a different API. Every team rewrote the same code: fill a prompt template, call, retry, parse the text, and pretend to "call a tool" by asking the model for JSON and parsing it. LangChain packaged that code [V] `[lc-philosophy]`.
- **LangGraph, 2024.** LangChain's first agent class gave nearly every decision to the model and could not loop under the developer's control. LangChain wrote that "the higher level abstraction hides too many details from the developer" [V] `[lg-cloud]`. LangGraph is the correction: lower level, nodes are plain functions, nothing writes prompts for you `[lg-launch]`.

### 2.3 What aged

| Piece | Why it aged | Evidence |
|---|---|---|
| Prompt templates, chains | A prompt is a string; two calls are two function calls | Moved to `langchain-classic` [M] `[lc-migrate]` |
| Output parsers | Models return structured output natively | "Prompted output" removed in 1.0 [M] `[lc-migrate]` |
| The pipe syntax (LCEL) | It composed steps that no longer need a library | Zero mention in the 1.x Python docs index [M] `[lc-docs-index]` |
| The first agent class | Too opaque | LangChain: its early abstractions "got in the way" [V] `[lc-how-to-think]` |
| Planner prompts, long default prompts | Recent models plan without them | Deep Agents 0.7 removed its default prompt; input per turn fell about 65% [V] `[deepagents-07]` |

Teams that removed LangChain for a direct loop report the same thing: time spent understanding the framework instead of building `[octomind-hn]` `[vettio]`. For LangGraph, three small removals were found: an anonymous team (to Pydantic AI plus Temporal), a consultancy (to Temporal, published on Temporal's blog) and a Swiss product (to plain Python classes). None gives numbers, and no large named company has published one [S][V] `[jim-removal]` `[griddynamics]` `[yeos]`. An earlier note of this study said "none found"; the later, searched note corrects it.

### 2.4 What did not age

These are needs, not products. A ticket-to-production workflow has all of them.

| Need | Why no better model removes it | Who provides it |
|---|---|---|
| The state of a run survives a crash | A run lasts hours and crosses CI, reviews and deploys | A LangGraph checkpointer; an engine; **or the ticket and the PR themselves** |
| Waiting for a human | An approval can take days; no process should stay alive for it | A LangGraph interrupt `[lg-interrupts]`; an engine signal; or a ticket state |
| Mixing fixed steps and model steps | Lint, tests and deploys are deterministic | A graph; or plain code |
| Replay | A run that depends on a model must be debugged from step N | LangGraph time travel `[lg-timetravel]`; an engine history |
| Traces and evaluations | You cannot know what a model does until you look | LangSmith, or any OpenTelemetry tool |

**A point the notes left open, settled here.** One note says saved state is a need "no model improvement removes"; two others say most ticket workflows need no engine. Both are true. *The state must be durable somewhere.* It does not follow that an engine is required: a ticket status, a label and a PR are durable state that the team already owns. An engine is needed when the state to keep is inside one long computation, not between ticket states (section 7).

### 2.5 Four things in the fine print of LangGraph

1. **Replay runs the node again.** "Replay re-executes nodes; it doesn't just read from cache", and after a pause the node restarts from its beginning [M] `[lg-timetravel]` `[lg-interrupts]`. A maintainer calls it "a natural consequence of the fact that all code pre-interrupts re-runs" [M] `[lg-7780]`. So any side effect in a node (open a PR, comment on a ticket) must be idempotent.
2. **The default save is not "before the next step".** The run methods default to `durability="async"`: the checkpoint is written in the background while the next step runs. A hard crash can lose the newest one. Read in the source at tags 1.0.0, 1.2.0 and main [M] `[lg-source]`.
3. **The library saves state; it does not watch your process.** No queue, no worker pool, no detection of a dead run, no automatic restart, no lock against two workers on one thread, no record that a run was accepted [M] `[lg-8764]`. Those are in LangChain's Agent Server: package `langgraph-api`, licence Elastic 2.0 [M] `[lg-api-pypi]`. Its standalone-server page lists `LANGGRAPH_CLOUD_LICENSE_KEY` among the variables needed and asks for network access to LangChain "for license verification" [V] `[lg-standalone]`. Which paid plan a standalone server needs is not stated on a page I can cite: the docs call the self-hosted LangSmith *platform* an add-on to the Enterprise plan, and a forum answer (a community member, not staff) says self-hosting is not possible without an enterprise key. The old free tier is no longer mentioned; no page announces its removal. That server has its own open bug: tool calls longer than about 180 seconds are dispatched a second time (open since April 2026, 89 comments) [M, on users' installs] `[lg-7417]`.
4. **Checkpoint stores are an attack surface.** Several vulnerabilities in 2025 and 2026 reached code execution through saved state; all fixed, the Postgres path spared [S] `[checkpoint-rce]`.

Points 1 and 3 are true of every option, including a home-made one: something must make side effects safe to repeat, and something must notice a dead run. They are the real cost of durability, with or without LangGraph. No independent, repeatable benchmark compares LangGraph's recovery with Temporal, Restate or DBOS; one single-author test with a stubbed model exists `[crash-test]`.

### 2.6 Who uses it, and how

- GitLab chose LangGraph for its agent platform, then built a layer above it that compiles YAML into LangGraph flows, because raw graphs gave "no reusability, no composability" [V] `[gitlab-flows]`. It also wrote its own checkpointer, a lock and a 15-second heartbeat, because a workflow could run in two places and overwrite its own checkpoints [V] `[gitlab-548686]`.
- LinkedIn's hiring agent runs on LangGraph but does **not** use its pause for human review: each turn runs the graph end to end [S, summary of a 2026 talk] `[linkedin-zenml]`. Uber uses it in a legal agent as a parallel step runner inside one request [V] `[uber-redline]`.
- The Thoughtworks Radar moved LangGraph from Adopt to Trial in April 2026. Its reason is about design, not reliability: one large shared state for the whole graph is "not always the best approach"; simple agents that talk through code, with a graph added later if needed, are often leaner and easier to test [S] `[radar-lg]`. (One note sums this up as "start with the simplest thing". The blip page is more specific, and I follow it.) The blip is absent from the November 2026 edition, so there is no newer judgement.
- Anthropic's reference text on agents listed "LangGraph from LangChain" among example frameworks until October 2025; since November 2025 it lists "The Claude Agent SDK" instead. No reason is given: it shows what Anthropic recommends, not a criticism [M, web archive] `[bea]` `[bea-archive]`.
- Replit is the one coding-agent company documented on LangGraph, in a 2024 case study on LangChain's site. Its durable layer went elsewhere: to Temporal in 2025, then to Restate, which "now handles all durable orchestration at Replit" per Restate's page [V] `[replit-lc]` `[replit-temporal]` `[restate-replit]`. Whether LangGraph is still inside Replit Agent is not known.

**My reading.** The three users confirmed in 2026 (GitLab, LinkedIn, Uber) use LangGraph as a library inside their own service, and the two that need recovery or approval built those parts themselves. A team harness will need its own vocabulary of steps and gates in any case. No named team was found that drives Claude Code or Codex from a LangGraph graph in production `[gap-lg]`.

### 2.7 When to use them, when not

| | Use it when | Do not use it when |
|---|---|---|
| **LangChain** | You call several providers and want one interface; you want a ready loop with approval and retry in Python or TypeScript | You call one provider; you drive an existing coding agent; you follow an old tutorial (`LLMChain`, pipes, `AgentExecutor` are the retired API) |
| **LangGraph** | You write your own agent application; the graph has real branches and loops; a run must pause for a human inside the process; the team writes Python or TypeScript and has Postgres | The step already runs inside a coding agent (use skills and hooks); the flow is a straight line (use a script); you already have an engine or a CI that holds state; side effects cannot be made idempotent; you want Rust |

---

## 3. The landscape

Four families of tools answer "who decides the next step, and who remembers where we are".

### 3.1 Agent SDKs: the loop as a library

Every lab and cloud now ships one, and they converged: a loop, tools through MCP, a pause for a human, and a script or graph layer for multi-step work `[n-alternatives]`. They differ on one point: what happens when the process dies. Most save a session you must reload yourself.

- **Claude Agent SDK** (Python, TypeScript): the Claude Code loop as a library. No graph. For other languages the documentation says to run the command-line tool as a child process [V] `[claude-sdk]`.
- **OpenAI Agents SDK** (Python, TypeScript): agents, handoffs, a paused state you can save as JSON. Its documentation warns that an approval "does not guarantee exactly-once execution" [M] `[openai-hitl]`.
- **Google ADK 2** and **Microsoft Agent Framework 1.0**: both ship a graph engine with pause and resume, as products for customers [V] `[adk-go2]` `[ms-af]`. Neither company describes its own coding agent as built on it `[n-labs]`.
- What died: AutoGen is archived [M] `[autogen]`; OpenAI's visual Agent Builder shuts down on 2026-11-30, a little over a year after launch [M] `[agent-builder]`.

### 3.2 Durable workflow engines

The workflow is ordinary code. Each call to the outside is a recorded step. After a crash the code runs again and skips recorded steps. A wait of three weeks holds no process.

What an engine does **not** give [S] `[fowler-durable]`:

- Steps run *at least once*: a retry can repeat a side effect. You still need idempotency.
- Changing the code while runs are suspended can break replay. Versioning is a discipline.
- Facts go stale during a long wait. The workflow must check them again.
- It does not stop an agent that loops; it retries it faithfully (**my reading**, from `[gap-small]`).

### 3.3 CI as the orchestrator

A forge event (label, comment, check finished, schedule) starts a job. The job runs a coding agent once. The state is what the job writes on the ticket or the PR.

- GitHub Agentic Workflows: a Markdown file compiled to a normal Actions workflow. The agent job is read-only; writes pass through checked "safe outputs". **Generally available since 2026-10-28** [V] `[ghaw-ga]`. (One note still says "technical preview"; the changelog entry settles it.) By design it has "no automatic retries" [V] `[ghaw-faq]`.
- GitLab Custom Flows: generally available since 2026-07-16 [V] `[gitlab-custom-flows]`. No user account was read.
- Time limits, with their scope. GitHub Actions: 6 hours per job on a hosted runner, 5 days self-hosted, 35 days per run, 30 days for an environment approval [M] `[gha-limits]`. The "59 minutes" quoted in two notes is a different thing: the cap of one Copilot cloud-agent session `[n-labs]`. No memory between runs. A failed job restarts from zero and pays its tokens again.

**On a self-hosted forge.** Read from documentation and API files, not tested on a running instance `[gap-forge]`.

| Need | GitHub | Forgejo 17 | Gitea 28 | GitLab CE (free) |
|---|---|---|---|---|
| One run at a time per ticket (concurrency group) | yes | yes since 14.0; **cancels the running job by default on push and PR events**, default not stated for the others, so write it explicitly; "best-effort", queue order not guaranteed `[forgejo-ref]` | yes since 1.26 | `resource_group` |
| Start a run from outside with inputs | yes | yes, typed inputs (string, number, boolean, choice); no free-form event | yes | yes, trigger token |
| Approval gate inside a pipeline | environment reviewers | **none** (the `environment` key is named once in the reference, with no approval feature) | **none** (key ignored) `[gitea-compare]` | paid tiers; free: a manual job `[gitlab-approvals]` |
| Shared workflow from a private repository | yes | **no**; a contributor's branch of 2026-11-19 is not merged `[forgejo-12343]` | yes | yes |
| Narrow the job's automatic token | yes | **no**, except that it is already read-only on PRs from forks; a read-only token is "on the roadmap" `[forgejo-13183]` | yes `[gitea-perms]` | not re-read |
| Official coding-agent action | yes | **no**; one small fork `[cca-1601]` | no | not checked |

Two consequences. The only human gate that exists on all four is a ticket or PR state whose change starts a new job. And on Forgejo, sharing across private repositories means a thin workflow file per repository with all logic in one versioned command-line tool.

**From a tracker outside the forge.** A Jira automation rule can call the forge's dispatch API itself: zero lines of code, but no documented retry [V][S] `[jira-automation]`. This works only if the forge is reachable from Atlassian's addresses on one of a dozen allowed ports (80, 443, 8080, 8443 and a few others): a self-hosted forge on port 3000 or on a private network needs a reverse proxy or a relay after all. Secret values of a rule are lost when the rule is copied or exported. Linear sends a fixed, signed payload and wants an answer within 5 seconds, so it needs a small relay; a failed delivery is retried at most three times (after 1 minute, 1 hour, 6 hours), and a webhook whose URL stays unresponsive "might be disabled" [V] `[linear-webhooks]`. A scheduled **sweep** job (list "ready" tickets with no run, and "in progress" tickets with no live run) makes either path safe, and can be the whole bridge if a few minutes of delay is acceptable. Nobody was found who documents exactly "stateless relay plus sweep" with failure counts; the nearest are Viam's shared workflows and an archived OpenAI recipe `[viam]` `[openai-jira]`. GitHub's own draft specification for such a bridge demands durable receipts, for a shared and hostile setting `[ghaw-gateway]`.

### 3.4 Protocols

Three matter for a team harness: **MCP** (how an agent reaches tools), **AGENTS.md** (where a coding agent reads a repository's instructions) and **Agent Skills** (`SKILL.md`). All three are now under the Linux Foundation's Agentic AI Foundation [V] `[skills-aaif]` `[agents-md]`. A2A (agent calls agent) matters when agents of different teams must call each other. ACP (editor or orchestrator drives a coding agent) is the only neutral way to drive several agents, but its Rust crate had four major versions in five months [M] `[acp-crate]`.

### 3.5 Comparison

| Option | Who fixes the order of steps | Survives a crash | Waits for a human | Languages | What you operate |
|---|---|---|---|---|---|
| Coding agent + skills, in a session | The model, guided by text | No | Yes, a person is there | any | nothing |
| Claude Agent SDK / OpenAI Agents SDK | Your code | A session to reload yourself | Callback or saved state | Python, TS | your process |
| LangGraph | A graph in code | Yes, if you set a checkpointer and something restarts the process | Interrupt | Python, TS | a database, or the paid server |
| Google ADK 2, Microsoft Agent Framework | A graph or code | From a session store or checkpoints you store | Any node | Python, Go, TS, Java, .NET | a store |
| **CI + ticket state** | The pipeline file and your code | No resume inside a job; the ticket keeps the state between jobs | A new event; or an environment approval (30 days) | any (it runs a command) | nothing new |
| Home-made daemon or webhook service + database | Your code | What you wrote | What you wrote | any | a long-lived process |
| Temporal | Code, enforced by replay | Yes, automatic | Signals, any length | 8, **Rust included** | a cluster, or Temporal Cloud |
| AWS Lambda durable functions | Code | Yes, automatic | Not read for this study | several, **Rust 1.0 since 2026-11-19** | nothing, but the code must run on Lambda |
| Restate | Code | Yes, automatic | Durable promises | 5, Rust pre-1.0 | one binary |
| DBOS | Code | Yes, automatic | Wait for events | Python, TS, Go, Java; Rust pre-production | your Postgres |

Sources: `[n-alternatives]`, `[n-rust]`. One correction between notes: the engine table of one note lists DBOS and Inngest without Rust; both have an official Rust SDK, DBOS "pre-production" and Inngest "alpha" [V] `[dbos-rust]` `[inngest-rs]`. Inngest's crate is 0.1.1, last published on 2024-11-01: do not count it as a live option [M].

**Cost of an engine.** Temporal Cloud lists about $50 per million actions with no base fee [V] `[temporal-pricing]`. A ticket of 100 actions, 1,000 tickets a month: about $5 (arithmetic of the notes). The fee is not the cost. The cost is one more system, a programming model with rules, and people who know it. No source gives the staffing needed to self-host one `[n-decision]`.

---

## 4. Rust

### 4.1 What exists

- **MCP**: `rmcp`, official, top tier, used by Codex and goose. Three major versions in five months [M] `[rmcp]`.
- **Durable execution**: Temporal's Rust SDK, 1.0 on 2026-09-04 (its release notes already say "Generally Available"), blog announcement on 2026-09-23, now 1.2.0. No named production user; no agent integration for Rust [V] `[temporal-rust-ga]` `[temporal-crate]`. AWS's durable execution SDK for Rust reached 1.0 on 2026-11-19, "the first stable release" per its release notes, for Lambda durable functions only; two days old, and some AWS documentation pages do not list Rust yet [M] `[aws-durable-rust]`. Restate 0.13 is usable [M] `[restate-rust]`.
- **Large products**: Codex is about 97% Rust [M] `[codex-repo]`. GitHub moved the Copilot runtime to Rust in 2026: 832,378 lines, with dozens of regressions fixed on the way [V] `[copilot-rust]`. Their reasons: one binary with no runtime to install, native sandboxing, flat memory, a core that other languages can embed `[codex-native]`.
- **One vendor agent loop you can link into Rust**: the GitHub Copilot SDK [M] `[copilot-sdk]`.
- **Model clients**: community crates (`rig`, `genai`, `async-openai`), all pre-1.0 `[rig]`. Official only through Bedrock and Vertex.

### 4.2 What is missing

- LangChain and LangGraph: nothing official; small unstable community crates [M] `[langchain-rust]` `[graph-flow]`.
- An official Anthropic or OpenAI client, and their agent SDKs [V] `[anthropic-sdks]` `[openai-libs]`.
- Evaluation tooling: nothing with real adoption `[n-rust]`.
- A LangSmith client; OpenTelemetry Rust marks traces as Beta [M] `[otel-rust]`.

### 4.3 How a Rust program drives a coding agent today

It starts the vendor's tool as a child process and reads JSON. This is the route Anthropic documents for unsupported languages [V] `[claude-sdk]`. And it is what the Claude Agent SDK does itself: "The Agent SDK spawns and supervises a `claude` CLI subprocess" [V] `[sdk-hosting]`. (Earlier notes called the SDK "in-process"; the hosting page settles it. This is shown for Claude only: the OpenAI Agents SDK is a library that calls the API in its own process, and nothing read says it wraps `codex`.) So Python and TypeScript get a typed wrapper for free; Rust and Go write a wrapper by hand, a few hundred lines per agent, and own its upkeep `[gap-forge]`. The hand-written wrapper gets the same agent, not the same interface: the documented route for other languages is one call, `claude -p --output-format json`, while the SDK holds a two-way stream that also carries hooks in the caller's process, permission callbacks and custom tools. A wrapper has those only if it implements that stream, which has no stated stability promise.

- Claude Code: `claude -p --output-format json`, a result checked against a JSON schema, resume by session ID, a turn cap and a dollar cap (`--max-turns`, `--max-budget-usd`, documented in the CLI reference), a flag that denies instead of asking (`--permission-prompts none`, from Claude Code 2.1.259), and a documented way to stop the process for a human approval and resume later (`defer`) [V] `[claude-headless]` `[claude-hooks]`.
- Codex: `codex exec --json --output-schema`, sandbox read-only by default [V] `[codex-exec]`.
- Both tools release often (Claude Code about one release per working day, Codex every five days) and give no formal stability promise. Announced change: `--bare` will become the default for `-p`, which stops loading skills and hooks unless asked. Security note: without `--bare`, a `-p` run executes the hooks configured in the repository it runs in, with no trust prompt [V] `[claude-headless]`.
- Billing. A change to how subscriptions cover programmatic use was announced in spring 2026, then **paused on 2026-06-15**: `claude -p` on a subscription still draws from the plan's limits [V] `[claude-plan]`. Both vendors say: for unattended automation, use an API key [V] `[claude-legal]` `[codex-auth]`.
- ACP is the only neutral protocol to drive several agents, but Claude and Codex are reached through Node adapters, and its Rust crate had four major versions in five months [M] `[acp-crate]`.

**Language matters less than it seems** for this part: in every language the agent is on the other side of a process boundary. Kiro reached the same boundary after maintaining three engines, one of them in Rust [V] `[kiro]`.

### 4.4 Verdict by building block

Scale: **first-class** (official or standard, 1.0+, used by large products), **usable** (works, but community-run or pre-1.0), **missing**. Source: `[n-rust]` section 6.

| Building block | Rust today | Best option | Note |
|---|---|---|---|
| State machine of a workflow | **Well suited** | plain `enum` and `match` | A missing case is a compile error. No framework needed |
| Command-line tool, single binary | **First-class** | the general ecosystem | The reason OpenAI and GitHub give |
| MCP server or client | **First-class** | `rmcp` 3.11 | Pin it: fast major versions |
| Durable execution | **Supported, young** | `temporalio-sdk` 1.2 on any host; `aws-durable-execution-sdk` 1.0 if the code runs on AWS Lambda | The source note grades Temporal "first-class", but its own scale asks for "used by large products" and no production user is named. Two and a half months since Temporal's 1.0; two days since AWS's |
| Sandboxing of commands | **First-class** | `landlock`, `seccompiler` | Shipped in Codex |
| Vendor agent loop | **Missing** (one exception) | run `claude -p` or `codex exec` as a child process | The Copilot SDK is the exception |
| Model client, Anthropic or OpenAI direct | Usable, weak | `rig`, `genai`, `async-openai` | Volunteer-maintained; features arrive late |
| Graph of agent steps | Usable, thin | plain enums; `graph-flow` is small | No LangGraph |
| Tracing | Usable | `tracing` + OpenTelemetry | Traces in Beta |
| Evaluations | **Missing** | run them from outside the binary | Any language can grade outputs |
| LangChain, LangGraph | **Missing** | none | |

### 4.5 The honest answer

- Rust is a **reasonable** choice for the code part of a harness when that part is a program worth compiling: a binary handed to many repositories, an orchestrator that lives long, a tool server, a worker on a durable engine.
- Rust is a **poor** choice for the agent loop, for prompt iteration (compile time; keep prompts in files), and for evaluations.
- Rust **buys nothing** on the duration or the model cost of a ticket [S] `[refresh-agent]`.
- Every team that chose Rust wrote more itself `[n-rust]`. The labs' own cores are Rust or TypeScript: Codex and, since September 2026, the Copilot runtime are Rust; GitHub's CI workflow compiler (`gh-aw`) is Go. Both facts are true of GitHub; one note lists only the second.
- Rust does not make an orchestrator reliable by itself. Every failure report found is in TypeScript or Elixir, because that is where the deployed orchestrators are, and each is a design failure: no idempotency key, no reaper for child processes, no lease, no sweep `[gap-forge]`.
- For a command-line tool called from CI jobs, the choice is about distribution and review, not about the agent. Rust or Go give one static binary with no runtime on the runner. Standard-library Python gives zero build, and is the cheapest to change, **where Python is on the runner**; Forgejo's default job image ships only Node [V] `[forgejo-ref]`.
- If durability is needed today in Rust there are two options with a vendor-supported 1.0: Temporal on any host (a server to run or a service to buy), and AWS Lambda durable functions for a team whose code runs on Lambda [M] `[temporal-crate]` `[aws-durable-rust]`. (An earlier version of this report said Temporal was the only one; its own section 4.1 already recorded the AWS release.) The lighter "library on Postgres" (DBOS) is pre-production in Rust; Restate's Rust SDK is 0.13 [V][M] `[dbos-rust]` `[restate-rust]`.
- The existing Rust orchestrators are not something to adopt: the closest one to a ticket workflow has 14 stars and two authors; the largest lost its company in April 2026 [M] `[symphony-rust]` `[vibe-kanban-shutdown]`. They are worth reading, not depending on.

---

## 5. How the labs and leading companies build their workflows

### 5.1 Recurring patterns

| # | Pattern | Named examples |
|---|---|---|
| 1 | **A plain loop in ordinary code for their own agent, not a graph** | Claude Code (TypeScript), Codex (Rust), Cursor, Cognition, Factory, Manus `[n-labs]`. Google and Microsoft sell graph engines to customers, not to themselves |
| 2 | **Steps that must happen are code, not prompt** | Stripe "blueprints": a state machine that alternates code nodes ("run linters", "push") and agent nodes ("implement", "fix CI") [V] `[stripe-2]`. Dropbox moved CI handling out of the agent after sessions waited for hours [V] `[dropbox-nova]` |
| 3 | **A cap on every loop** | Stripe: two CI rounds, then a human whatever the state `[stripe-2]`. Dropbox: five attempts `[dropbox-nova]`. Symphony: turn limit and backoff `[symphony-spec]` |
| 4 | **The run record, the credentials and the merge rule live outside the sandbox** | Anthropic splits loop, sandbox and an append-only session log [V] `[anthropic-managed]`. GitHub's agent job holds no secret; writes are checked after it exits [V] `[ghaw-security]` |
| 5 | **Files, git and the ticket are the memory** | OpenAI ran a 5-month project on an `AGENTS.md` of about 100 lines pointing into `docs/` [V] `[openai-harness]`. Symphony keeps no database: the ticket status is the state `[symphony-spec]` |
| 6 | **Humans approve the plan and the result, not each step** | A PR everywhere. Symphony: a human moves the ticket to `Merging` before the agent may land it `[symphony-spec]`. Bitrise added "merge only on explicit instruction" after its agent merged its own PR [V] `[bitrise]` |
| 7 | **Durable execution under the loop, for agent products** | Cursor moved the loop of its cloud agents to Temporal: "one 9 of reliability" often before, "past two 9s" after [V] `[cursor-cloud]`. Self-reported, with no measurement method, and the post does not separate Temporal from the other changes of the same period. It is the only before-and-after figure found for a coding agent, which a search cannot prove to be the only one. Replit (Temporal, then Restate) and Codex, per the engine vendors' sites [V] `[replit-temporal]` `[restate-replit]` `[temporal-codex]` |
| 8 | **Delete harness parts as models improve** | Anthropic removed context resets, then sprint decomposition `[anthropic-harness-design]`. Vercel removed about 80% of an agent's tools and got better results on 5 test queries [V] `[vercel-tools]` |
| 9 | **Bug flows stop earlier than feature flows** | Sentry: stop after root cause, after plan, or after a draft PR, by setting; never merges [V] `[sentry-autofix]`. incident.io: a fix PR only when a responder asks [V] `[incidentio]` |
| 10 | **Review and CI capacity are the limit, not writing** | Spotify: PRs up 76%, so 76% more to review [V] `[spotify-cwc]`. OpenAI: CI load about ten times higher in six months [S] `[pragmatic-openai]` |

### 5.2 Who uses a workflow engine: the notes disagreed, here is the reconciled reading

| Company | What runs on the engine | Kind | Source |
|---|---|---|---|
| Cursor | The loop of its cloud agents | Product sold to users | Cursor's own post, 2026-06-02 [V] `[cursor-cloud]` |
| Replit | The control of Replit Agent | Product | Temporal's case study, unnamed engineer; Restate's page says it has since moved there. No Replit-hosted statement found [V] `[replit-temporal]` `[restate-replit]` |
| OpenAI Codex | "core control flows" | Product, as far as one sentence tells | A quote on Temporal's blog; no OpenAI page found [V] `[temporal-codex]` |
| Duolingo | Multi-step agent workflows for employees (2025); since then its whole agent platform: a workflow wrapper per agent, tool calls as engine activities, evaluations | **Internal workflow** | Duolingo's own posts, 2025-12-11 and 2026-08-04 [V] `[duolingo]` `[duolingo-platform]` |
| Stripe, Spotify, Shopify, Ramp, WorkOS, Bitrise, OpenAI Symphony | Nothing named: a state machine, a daemon, a webhook service, an event log | Internal workflow | `[n-ticket]` section 3 |

So "the labs use Temporal" and "only one company was found that names an engine for an internal workflow" are both true. The second is an absence of evidence: the fact-check found no second company (the Razorpay and Ramp posts name none; one page could not be opened), and a primary source cannot prove a negative. They describe different populations. A team that builds an internal ticket workflow belongs to the second one.

Duolingo's own figures show the price: a simple declarative workflow takes under 5 minutes to create; a custom Temporal workflow "1-2 days" on average [V, self-reported] `[duolingo]`. Duolingo then went further on the engine, not back: the price did not stop it. Airbnb built its own orchestrator, never shipped it, and kept a thin wrapper over vendor agents [S, medium confidence] `[airbnb]`.

### 5.3 What goes wrong at small scale

The only evidence at small scale is the issue trackers of open-source orchestrators. It over-represents failures, and the reporters' team size is not stated `[gap-small]`.

| Runtime | What broke | Source |
|---|---|---|
| Home-made daemon polling the tracker | A run that looks alive and burns tokens: "This bug cost me 15M tokens"; an orphan agent after cancel | Symphony discussions [M] `[symphony-121]` |
| Tracker daemon | One issue spawned 16 sessions in 45 minutes; 15 out-of-memory kills in about 4 weeks, unnoticed because the service manager restarted the process each time (one user, one install, a memory leak; issue still open) | Cyrus issues [M] `[cyrus-1328]` `[cyrus-1381]` |
| Webhook service + database | 20 of 135 review sessions (about 15%) silently lost on one install, one reporter's count; the issue was closed as fixed on 2026-10-04. 9 review sessions on one PR. The main author stepped back on 2026-11-01 and asked for two or three maintainers; the repository moved to an organisation and is still active | Open-Inspect issues [M] `[oi-1363]` `[oi-1371]` `[oi-2493]` |
| CI as engine | 25 failures in a sample of 100 runs over one day in GitHub's own repository (55 workflows, smoke tests and experiments included; 100 is very likely the collector's cap), no automatic retry; no supported way to read the cost of a run from Anthropic's action | gh-aw and claude-code-action issues [M] `[ghaw-79510]` `[cca-1482]` |

**My reading.** The first failures a small team meets are duplicates, silent losses, loops that burn tokens, one person holding the orchestrator, and an unknown cost. None needs an engine. They need a key derived from the ticket, one run at a time per ticket, a budget cap, a scheduled sweep, and a cost line. CI gives most of these cheaply and removes the long-lived process that fails silently. CI is also fragile, by how much is not known: the 25% figure is one day, one repository, a sample very likely capped at 100 runs, with test workflows that may fail on purpose. It is not a failure rate of the product.

**One default, and when the other applies.** Three notes give three pieces of advice: "CI and ticket state first, managed engine second, home-made daemon last"; "a new, small Rust daemon with a SQLite table"; and "a tracker-polling daemon is good for small teams". I follow the first. The second answers a different question (if the orchestrator is in Rust, what can it stand on) and nothing in it shows the process must live long; the third is a description, written before the issue trackers were read. A long-lived process is justified only when one of these is **observed**: a ticket joined across several repositories; a global money cap or fairness rule; an approval answered while the agent waits with its context; expensive warm state between steps; reaction under about a minute; or late failures that cost more than running a service `[gap-forge]`. Likewise "a small service on DBOS or Restate as soon as the tracker is outside the forge" is too strong: an outside tracker needs a bridge, not a stateful service.

### 5.4 Figures to handle with care

- **Share of PRs written by agents.** Not comparable between companies, and sometimes not between two sources about one company. Ramp: about 30% (January 2026), "more than 60%" (June), 74% or 75% (August to October), from different posts `[ramp-inspect]` `[n-ticket]`. Uber: 11% of PRs *opened by* background agents (March) against "more than 70%" *attributed to* any agent (August): two definitions `[n-team]`. Nothing in the recommendation depends on these.
- **Spotify's model-as-judge.** A December 2025 post says it vetoes about a quarter of sessions; a March 2026 talk says an early judge was too rigid and was removed; a June catalog still lists one. Current status: not confirmed `[spotify-3]` `[infoq-honk]`.
- **Coinbase "agent councils and auto-merge".** Stated by LangChain about Coinbase; no Coinbase source found. Unverified `[n-ticket]`.
- **Cost of a run.** Three unrelated sources land near one dollar per agent pass: Cloudflare's code review (mean $1.19 over 131,246 runs) [V] `[cloudflare-review]`, Sentry's fix ($1.00 flat) [V] `[sentry-pricing]`, GitHub's heavy runs (about $1.20) [M] `[ghaw-79510]`. Nobody publishes the cost of a ticket end to end. The notes' estimate, $3 to $10 for a feature ticket and $1 to $3 for a simple bug fix, is arithmetic, not a measurement.
- **Vercel's auto-approval post**, the only controlled comparison found (671 low-risk PRs merged without review and zero reverts, against 2 reverts in 513 reviewed ones). Neither note could open the page; one got a browser-only page, the other an HTTP 404. A second summary gives a 0.2% revert rate that may cover another period. Treat it as [S], unverified `[vercel-58]`. Nothing in the recommendation depends on it.

---

## 6. From a ticket to production: two reference flows

Built from Stripe, Symphony, WorkOS, Bitrise, Sentry, Dropbox and Shopify `[n-ticket]` sections 9 and 10. Each step has one owner: **code** (no model call), **agent** (a model decides inside a loop), **human**. **Stop** marks a place where a team can choose to end the flow. The cap of three local rounds is the notes' suggestion; two CI rounds and five bug attempts come from Stripe and Dropbox.

### 6.1 Feature ticket

| # | Who | Step | Stop |
|---|---|---|---|
| 1 | human | Writes the ticket with acceptance criteria | |
| 2 | agent | Checks the ticket is ready; proposes criteria and a split. Writes nothing without agreement | `readiness` |
| 3 | human | Accepts, moves the ticket to "ready for agent". **Start gate** | |
| 4 | code | Checks the event and eligibility; refuses a second run on the same ticket; opens the run record, keyed by the ticket | |
| 5 | code | Prepares a clean workspace with a short-lived, narrow credential; fetches ticket, comments, rules | |
| 6 | agent | Writes a short plan with the criteria restated and its assumptions | `plan` |
| 7 | human | Approves the plan. **Only for large or sensitive changes**; otherwise the assumptions go in the PR | |
| 8 | agent | Implements and tests | |
| 9 | code | Format, lint, build, selected tests. On failure, back to 8. Cap: three rounds | |
| 10 | code | Pushes; opens a **draft** PR linked to the ticket, with plan, assumptions, results, cost | `draft_pr` |
| 11 | code | Waits for CI on the current commit only | |
| 12 | agent | Fixes CI failures. Cap: two CI rounds, then hand back whatever the state | |
| 13 | agent | Independent review, tests and security pass, in a separate context, run as CI checks | |
| 14 | code | Computes the risk from paths and size; marks the PR ready; assigns reviewers. Nothing runs while it waits | `ready_pr` |
| 15 | human | Reviews. "Changes requested" returns to 8 with the comments passed in by code | |
| 16 | human | Authorises the merge explicitly. The requester cannot be the approver | |
| 17 | code | Merge queue | `merged` |
| 18 | human + code | The team's normal delivery pipeline, behind a protected environment. No agent holds a deploy right | `deployed` |
| 19 | agent | Optional: watches the rollout signals named in the plan; proposes a rollback, never runs it | |
| 20 | code | Closes the ticket; records outcome and cost; releases the next unblocked ticket | |

### 6.2 Bug ticket

A bug starts from a machine signal. So it needs a gate in code before any agent runs, and a check that the bug is still real.

| # | Who | Step | Stop |
|---|---|---|---|
| 1 | code | A signal arrives: error threshold, flaky-test detector, CI red on main, or a human report | |
| 2 | code | Removes duplicates against open tickets and PRs; creates or updates **one** ticket with the evidence | |
| 3 | code | Eligibility: allowed repository, not a sensitive path, nobody already on it. Otherwise, to a human, end | |
| 4 | agent | **Premise check**: does it still reproduce on the current head? Is there already a fix? If fixed: record, close, end | |
| 5 | agent | Root cause on the ticket, with evidence and a confidence | |
| 6 | code | Notifies the owner. Forced stop when confidence is low | `root_cause` (default) |
| 7 | agent | A failing test that reproduces the bug, then a fix plan | `plan` |
| 8 | agent | The smallest fix that makes the test pass | |
| 9 | code | Runs the test (many times if flaky), then lint, build, suite. On failure, back to 5 with the new logs. Cap: five attempts | |
| 10 | code | Draft PR with cause, evidence, test, what was tried | `draft_pr` |
| 11 | code + agent | CI on the current commit. Cap: two rounds | |
| 12 | human | Reviews; merges, or closes with one line of reason. **The tool never merges a bug fix** | |
| 13 | code | Merge queue and normal pipeline | `merged` |
| 14 | code | **Closure check**, days later: has the signal stopped? If not, reopen with the new evidence | |
| 15 | code | Records the outcome (fixed, already fixed, rejected, escalated) and the cost | |

**Incident variant.** Steps 1 to 5 run as an investigation attached to the incident. The agent proposes a mitigation; a human applies it. A fix enters at step 7 only when a responder asks.

### 6.3 What these flows say about the runtime

- Every wait is *between* two ticket states: plan review, CI, human review, merge, the closure check. During each, nothing needs to stay alive. A ticket state and a later event are enough.
- No step holds an expensive computation that must resume in the middle.
- So, on paper, neither flow needs an engine or a graph framework. The note that first drew this conclusion calls it "a hypothesis to test on real team workflows, not a result" `[n-decision]`. It still is.

**Which mechanism holds a human gate.** The notes offer three, and they are not interchangeable. (1) A ticket or PR state whose change starts a new job: used for every gate of the two flows, because it is the only one that exists on all forges and nothing stays alive. (2) An environment approval in the delivery pipeline: used for the production gate where the forge has it. (3) Claude Code's `defer` (the run stops, a later process resumes it with its context): documented, but the session file is on local disk, which a fresh CI job does not have, so it belongs to a long-lived orchestrator only `[gap-rust]`. The labs design mid-run questions out: approve the plan before, the PR after `[n-labs]`.

---

## 7. The decision grid for one step

Ask in this order. The first three questions settle most steps. Source: `[n-decision]` sections 3, 4 and 8, checked against the cases of `[gap-small]`.

| # | Question | If the answer is… | The step goes to |
|---|---|---|---|
| 1 | Is the right output determined by the inputs? | Yes | **Plain code**: a tested command. Never a prompt |
| | | Partly | Code computes the facts and options; a **skill** tells the agent how to choose |
| | | No, it needs interpretation | The **agent**, through a **skill** |
| | | It is a fact, not a step | An **instruction line** if every task needs it and the agent cannot find it; otherwise a document |
| 2 | Must it happen every time? | No, it is advice | Instruction line or skill |
| | | Yes, for the agent | A **hook** that calls the code of question 1 |
| | | Yes, for everyone on the repository | A required **CI check** |
| | | Yes, for every repository | An organisation rule and managed settings |
| 3 | How long does it live, and what must survive? | Minutes, in one session | The session |
| | | A few hours, unattended, a restart is acceptable | A **CI job** or a vendor's hosted agent |
| | | Hours to days, with waits, each step safe to redo | **State on the ticket or the PR**; each event starts a short job |
| | | Days to weeks inside one computation, steps that must not run twice, or full replay required | A **workflow engine** |
| 4 | Does a human decide in the middle? | No | No gate. Do not add one for comfort |
| | | Yes, on a change they can judge | PR review |
| | | Yes, before something irreversible | A protected environment in the pipeline; the agent only prepares |
| | | Yes, several people, with deadlines and escalation across systems | An engine signal; or a graph framework's pause, **if** the wait is inside your own agent application |
| 5 | Does the work split? | A check that must be independent, or a few parts that read a lot | A **sub-agent** with its own context; one writer |
| | | Tens or hundreds of independent units | A script fans out (CI matrix); one writer per unit. Never a swarm |
| 6 | What shape is the control flow? | Fixed sequence | A script or CI steps |
| | | Branches and loops known in advance, around a coding agent | **A small state machine in code** |
| | | The same, inside your own agent application, with pause and resume in the process | A state machine in code, or a **graph framework** |
| | | Unknown until it runs | An agent loop on an existing coding agent |
| 7 | How many repositories need it? | One | A file in that repository |
| | | Several | A versioned plugin and a reusable CI workflow, with an owner |
| 8 | Is this piece here because today's model is weak? | Yes | The cheapest layer; write the model and the date; test again at each model release; delete when it changes nothing |
| | | No: a guarantee, a right, a state, or a fact the model cannot know | Code, CI, the sandbox or the ticket. It does not age |

Three numbers behind the grid:

- A skill is a request, not a guarantee. In Vercel's evaluations the agent never invoked the available skill in 56% of cases [V, own evals] `[vercel-agentsmd]`.
- Splitting by role costs. Several agents use 3 to 10 times the tokens of one agent for the same task; teams "spent months" on designs a single agent matched [V] `[anthropic-multiagent]`.
- Long always-loaded context costs. One study found context files raise inference cost by over 20% with no average gain in task success [M] `[arxiv-agentsmd]`.

**The engine row, made measurable.** "You need an engine" should be a symptom, not a taste `[gap-small]` section 5:

| Symptom you can measure | Smallest fix, staying on CI and ticket state | What removes it by design |
|---|---|---|
| Runs die far in and pay their tokens twice, more than about one run in ten | Shorter jobs; progress written on the PR between jobs | An engine |
| Two runs on one ticket | One run at a time per ticket; keys derived from the ticket, never random | An engine with one workflow ID per ticket |
| An event accepted, nothing happened, nobody told | A job timeout; a scheduled sweep; a final status written by code | Polling, or an engine timer |
| An agent loops and burns tokens | A budget cap per run; empty turns count as failure | **Nothing. An engine retries it faithfully** |
| A wait that must resume inside an expensive multi-step computation | Model the wait as a ticket state | An engine |
| Many steps, each with its own retry and timeout rule | Reusable CI workflows | An engine; count one to two days per workflow |
| Strict order across events from several systems | One queue per ticket | An engine, or a database constraint |
| You cannot say what a ticket cost | The step writes tokens and dollars on the PR | Any runtime with a run record |

---

## 8. Where each tool fits, in one table

| You are building… | Reasonable choice | Why |
|---|---|---|
| A ticket workflow for a team, driving a coding agent | Ticket and PR as state, CI jobs as steps, a state machine in code | Section 5.3; nothing new to operate |
| The same, and a symptom of section 7 is measured | A managed engine (Temporal Cloud), one workflow per ticket; the worker can be Rust | Sections 3.5 and 4 |
| An agent product for users, sessions that resume mid-run | A durable engine under a plain loop | Cursor, Replit `[cursor-cloud]` |
| Your own agent application in Python or TypeScript, with a known graph and pauses in the process | LangGraph, or an agent SDK plus an engine | Section 2.7 |
| The same change across hundreds of repositories | A script and a CI matrix, one PR per repository | A different job from one ticket to one PR `[n-ticket]` |
| A long-lived orchestrator, a tool server, a binary for many teams | Rust is reasonable | Section 4.5 |

---

## 9. What is not known, and what would change the recommendation

### 9.1 Not known

1. Whether "CI plus ticket state" holds for a team of 5 to 50 on a real ticket workflow. No first-hand account on any runtime; no team documents "stateless relay plus sweep" with failure counts `[gap-small]` `[gap-forge]`.
2. The cost of a ticket end to end, and the share of runs that end in a merged PR. Only per-run prices exist.
3. A controlled comparison of CI against an engine on the same workflow: failure rate, cost, time to recover. Nor an independent benchmark of LangGraph's recovery against an engine.
4. The real failure rate of agentic workflows in CI. The 25% read in GitHub's own repository is a one-day sample with test workflows in it.
5. The staffing to self-host Temporal or Restate.
6. Named production users of Temporal's Rust SDK or of AWS's, and how either behaves under real load.
7. Everything about Forgejo, Gitea and GitLab CE above comes from documentation. To test on the exact version: label events after an issue is created, the queue of a concurrency group, whether a dispatch made from inside a job starts a run, behaviour under two runners `[gap-forge]`.
8. Whether agents on a self-hosted runner can be made as safe as GitHub's "safe outputs". Forgejo cannot make the job token read-only today, except on PRs from forks where it already is; a maintainer says it is on the roadmap `[forgejo-13183]`.
9. A stability promise for `claude -p` flags, its event format, or the two-way stream the SDK uses. None was found `[gap-rust]`.
10. Whether a Jira rule can reach the team's forge directly (allowed ports, Atlassian's address ranges). It depends on how the forge is exposed.
11. Almost every "we removed it and nothing broke" number is self-reported, often on a handful of cases. Vercel's controlled comparison could not be opened.

### 9.2 What would change the recommendation

| If this becomes true | Then |
|---|---|
| A team's measured runs show a symptom of section 7 that only an engine removes | Build the engine exit for that team: a managed engine, one workflow per ticket |
| The team is building an agent product, not an internal workflow | Start on a durable engine; section 5.2 |
| Compliance requires step-by-step replay of every run | An engine's history; labels and a comment are not an audit trail |
| Anthropic or OpenAI ships an official Rust agent SDK | The Rust verdict for the agent loop changes; revisit section 4 |
| DBOS for Rust leaves pre-production, or Restate's Rust SDK reaches 1.0 | A lighter engine exit than Temporal becomes available; re-check in mid-2027 |
| The team already runs its code on AWS Lambda | The engine exit can be Lambda durable functions in Rust instead of Temporal; read its limits first, the SDK is days old |
| The headless contract of `claude -p` changes materially | The adapter must change, in any language; pin versions and test before each bump |
| First real runs on CI show failure or loss rates like the worst issues of section 5.3, despite the cheap fixes | The default is wrong for that team; move earlier to a managed engine or a vendor's hosted agent |
| A vendor's hosted agent covers the whole flow on the team's forge | The skills and the grid still help; the generated CI does not |
| A team's runners have no Python, or the owner wants one binary for many repositories | Reimplement the four run commands as one Rust (or Go) binary against the same recorded contract |
| Forgejo adds approval gates, private reusable workflows or a read-only token (the last two have work in progress) | Simplify the generated files; the design does not change |

---

## 10. Sources

Research notes of this study (each has its own source list and its "not found" list):

- `[n-langgraph]` [research_notes/langchain_langgraph.md](research_notes/langchain_langgraph.md)
- `[n-alternatives]` [research_notes/orchestration_alternatives.md](research_notes/orchestration_alternatives.md)
- `[n-rust]` [research_notes/rust_ecosystem.md](research_notes/rust_ecosystem.md)
- `[n-labs]` [research_notes/labs_internal_stacks.md](research_notes/labs_internal_stacks.md)
- `[n-ticket]` [research_notes/ticket_to_prod_orchestration.md](research_notes/ticket_to_prod_orchestration.md)
- `[n-decision]` [research_notes/decision_criteria.md](research_notes/decision_criteria.md)
- `[n-team]` [research_notes/team_multi_repo_harness.md](research_notes/team_multi_repo_harness.md)
- `[gap-small]` [research_notes/gap_small_team_engine_threshold_and_cost.md](research_notes/gap_small_team_engine_threshold_and_cost.md)
- `[gap-rust]` [research_notes/gap_rust_orchestrator_agent_interfaces.md](research_notes/gap_rust_orchestrator_agent_interfaces.md)
- `[gap-forge]` [research_notes/gap_runtime_on_self_hosted_forge_and_language_choice.md](research_notes/gap_runtime_on_self_hosted_forge_and_language_choice.md)
- `[gap-lg]` [research_notes/gap_langgraph_independent_evidence_2026.md](research_notes/gap_langgraph_independent_evidence_2026.md)

LangChain and LangGraph

- `[lc-philosophy]` https://docs.langchain.com/oss/python/langchain/philosophy.md
- `[lc-migrate]` https://docs.langchain.com/oss/python/migrate/langchain-v1.md
- `[lc-docs-index]` https://docs.langchain.com/_llms/agent-development-lifecycle/build/python.txt
- `[lc-how-to-think]` https://www.langchain.com/blog/how-to-think-about-agent-frameworks (2025-04-20)
- `[lc-series-c]` https://www.langchain.com/blog/series-c (2026-11-13)
- `[lg-launch]` https://www.langchain.com/blog/langgraph (2024-01-17)
- `[lg-cloud]` https://www.langchain.com/blog/langgraph-cloud (2024-06-27)
- `[lg-overview]` https://docs.langchain.com/oss/python/langgraph/overview.md
- `[lg-interrupts]` https://docs.langchain.com/oss/python/langgraph/interrupts.md
- `[lg-timetravel]` https://docs.langchain.com/oss/python/langgraph/use-time-travel.md
- `[lg-repo]` https://github.com/langchain-ai/langgraph and https://github.com/langchain-ai/deepagents (read 2026-11-21)
- `[langsmith-deploy]` https://docs.langchain.com/langsmith/deploy-overview.md
- `[deepagents-07]` https://www.langchain.com/blog/deep-agents-v0-7 (2026-07-29)
- `[temporal-lg]` https://temporal.io/blog/temporal-langgraph-plugin-durable-execution (2026-07-16)
- `[checkpoint-rce]` http://research.checkpoint.com/2026/from-sqli-to-rce-exploiting-langgraphs-checkpointer/ (2026-06-11)
- `[gitlab-flows]` https://about.gitlab.com/blog/how-gitlab-reduced-code-per-agentic-flow-ratio/ (2026-09-22)
- `[uber-langgraph]` https://www.zenml.io/llmops-database/building-ai-developer-tools-using-langgraph-for-large-scale-software-development
- `[radar-lg]` https://www.thoughtworks.com/radar/languages-and-frameworks/langgraph
- `[bea]` https://www.anthropic.com/engineering/building-effective-agents (2024-12-19)
- `[bea-archive]` http://web.archive.org/web/20250305014737/https://www.anthropic.com/engineering/building-effective-agents
- `[replit-lc]` https://www.langchain.com/breakoutagents/replit
- `[octomind-hn]` https://news.ycombinator.com/item?id=40739982 (2024-06-20)
- `[vettio]` https://dev.to/tufailkhan457/why-we-replaced-langchain-with-the-raw-anthropic-sdk-in-production-3611
- `[lg-source]` https://github.com/langchain-ai/langgraph/blob/main/libs/langgraph/langgraph/pregel/main.py
- `[lg-api-pypi]` https://pypi.org/pypi/langgraph-api/json
- `[lg-standalone]` https://docs.langchain.com/langsmith/deploy-standalone-server and https://docs.langchain.com/langsmith/agent-server
- `[lg-7417]` https://github.com/langchain-ai/langgraph/issues/7417
- `[lg-7780]` https://github.com/langchain-ai/langgraph/issues/7780
- `[lg-8764]` https://github.com/langchain-ai/langgraph/issues/8764
- `[crash-test]` https://github.com/paolo-perrone/agent-crash-recovery
- `[gitlab-548686]` https://gitlab.com/gitlab-org/gitlab/-/issues/548686 and https://runbooks.gitlab.com/duo-workflow-svc/
- `[linkedin-zenml]` https://www.zenml.io/llmops-database/agentic-hiring-system-reduces-time-to-interview-by-60-for-small-businesses
- `[uber-redline]` https://www.uber.com/us/en/blog/building-ubers-redlining-agent/ (2026-10-08)
- `[restate-replit]` https://restate.dev/use-cases/replit
- `[jim-removal]` https://jiminsf.com/langchain-to-pydantic-ai/ (2025-11-11)
- `[griddynamics]` https://temporal.io/blog/prototype-to-prod-ready-agentic-ai-grid-dynamics (2025-09-29)
- `[yeos]` https://dev.to/nicolaric/why-we-removed-langgraph-from-our-ai-platform-i9o (2026)

Agent SDKs, engines, CI, protocols

- `[claude-sdk]` https://code.claude.com/docs/en/agent-sdk/overview
- `[anthropic-sdks]` https://platform.claude.com/docs/en/cli-sdks-libraries/overview
- `[openai-libs]` https://developers.openai.com/api/docs/libraries
- `[openai-hitl]` https://openai.github.io/openai-agents-python/human_in_the_loop/
- `[adk-go2]` https://developers.googleblog.com/en/announcing-adk-go-20/ (2026-06-30)
- `[ms-af]` https://devblogs.microsoft.com/agent-framework/microsoft-agent-framework-version-1-0/ (2026-04-03)
- `[autogen]` https://raw.githubusercontent.com/microsoft/autogen/main/README.md
- `[agent-builder]` https://developers.openai.com/api/docs/guides/agent-builder
- `[fowler-durable]` https://martinfowler.com/articles/durable-execution-agents.html (2026-11-10)
- `[temporal-pricing]` https://temporal.io/pricing
- `[ghaw-ga]` https://github.blog/changelog/2026-10-28-github-agentic-workflows-generally-available/
- `[ghaw-security]` https://github.blog/ai-and-ml/generative-ai/under-the-hood-security-architecture-of-github-agentic-workflows/ (2026-03-09)
- `[gitlab-custom-flows]` https://about.gitlab.com/blog/multi-step-software-delivery-with-agentic-flows/ (2026-07-16)
- `[gha-limits]` https://docs.github.com/en/actions/reference/limits
- `[skills-aaif]` https://www.anthropic.com/news/donating-agent-skills-to-the-agentic-ai-foundation (2026-10-22)
- `[agents-md]` https://agents.md/
- `[acp-crate]` https://crates.io/crates/agent-client-protocol
- `[ghaw-faq]` https://github.github.com/gh-aw/reference/faq/
- `[ghaw-gateway]` https://github.github.com/gh-aw/specs/webhook-gateway-specification/
- `[forgejo-ref]` https://forgejo.org/docs/latest/user/actions/reference/ and https://forgejo.org/docs/latest/user/actions/basic-concepts/
- `[forgejo-12343]` https://codeberg.org/forgejo/forgejo/issues/12343
- `[forgejo-13183]` https://codeberg.org/forgejo/forgejo/issues/13183
- `[gitea-compare]` https://docs.gitea.com/usage/actions/comparison
- `[gitea-perms]` https://docs.gitea.com/usage/actions/token-permissions
- `[gitlab-approvals]` https://docs.gitlab.com/ci/environments/deployment_approvals/
- `[cca-1601]` https://github.com/anthropics/claude-code-action/issues/1601
- `[jira-automation]` https://support.atlassian.com/cloud-automation/docs/jira-automation-actions/ and https://developer.atlassian.com/cloud/jira/platform/webhooks/
- `[linear-webhooks]` https://linear.app/developers/webhooks
- `[viam]` https://github.com/viamrobotics/claude-ci-workflows
- `[openai-jira]` https://developers.openai.com/cookbook/examples/codex/jira-github

Rust

- `[lc-rust-search]` https://api.github.com/search/repositories?q=org:langchain-ai+language:Rust (add `fork:true` to see the forks)
- `[langchain-rust]` https://github.com/Abraxas-365/langchain-rust
- `[graph-flow]` https://github.com/a-agmon/rs-graph-llm
- `[rig]` https://github.com/0xPlaygrounds/rig
- `[rmcp]` https://github.com/modelcontextprotocol/rust-sdk and https://modelcontextprotocol.io/docs/sdk
- `[temporal-rust-ga]` https://temporal.io/blog/build-durable-applications-rust-temporal-rust-sdk-now-generally-available (2026-09-23)
- `[temporal-crate]` https://crates.io/crates/temporalio-sdk and https://github.com/temporalio/sdk-rust/releases (1.0.0 on 2026-09-04)
- `[aws-durable-rust]` https://github.com/aws/aws-durable-execution-sdk-rust/releases/tag/v1.0.0 (2026-11-19)
- `[restate-rust]` https://github.com/restatedev/sdk-rust
- `[dbos-rust]` https://github.com/dbos-inc/dbos-transact-rust
- `[inngest-rs]` https://github.com/inngest/inngest-rs
- `[otel-rust]` https://github.com/open-telemetry/opentelemetry-rust
- `[codex-repo]` https://github.com/openai/codex
- `[codex-native]` https://github.com/openai/codex/discussions/1174 (2025-05-30)
- `[copilot-rust]` https://github.blog/ai-and-ml/generative-ai/migrating-the-github-copilot-runtime-to-rust-using-copilot/ (2026-09-16)
- `[copilot-sdk]` https://github.com/github/copilot-sdk
- `[goose]` https://github.com/aaif-goose/goose
- `[refresh-agent]` https://refreshagent.com/engineering/building-ai-agents-in-rust
- `[claude-headless]` https://code.claude.com/docs/en/headless and https://code.claude.com/docs/en/cli-reference
- `[claude-hooks]` https://code.claude.com/docs/en/hooks
- `[claude-legal]` https://code.claude.com/docs/en/legal-and-compliance
- `[codex-exec]` https://developers.openai.com/codex/noninteractive
- `[codex-auth]` https://developers.openai.com/codex/auth
- `[symphony-rust]` https://github.com/anantjain-xyz/symphony-rust
- `[vibe-kanban-shutdown]` https://www.vibekanban.com/blog/shutdown (2026-04-10)
- `[sdk-hosting]` https://code.claude.com/docs/en/agent-sdk/hosting
- `[claude-plan]` https://support.claude.com/en/articles/15036540-use-the-claude-agent-sdk-with-your-claude-plan
- `[kiro]` https://kiro.dev/blog/one-agent (2026-08-03)

Companies and labs

- `[stripe-2]` https://stripe.dev/blog/minions-stripes-one-shot-end-to-end-coding-agents-part-2 (2026-02-19 as read on the page through a summariser, medium confidence; one note gave 2026-02-09)
- `[symphony-spec]` https://github.com/openai/symphony/blob/main/SPEC.md
- `[openai-harness]` https://openai.com/index/harness-engineering/ (2026-02-11)
- `[pragmatic-openai]` https://newsletter.pragmaticengineer.com/p/openai-software-factory (2026-09-15)
- `[anthropic-managed]` https://www.anthropic.com/engineering/managed-agents (2026-04-08)
- `[anthropic-harness-design]` https://www.anthropic.com/engineering/harness-design-long-running-apps (2026-03-24)
- `[anthropic-multiagent]` https://claude.com/blog/building-multi-agent-systems-when-and-how-to-use-them (2026-01-23)
- `[cursor-cloud]` https://cursor.com/blog/cloud-agent-lessons (2026-06-02)
- `[replit-temporal]` https://temporal.io/resources/case-studies/replit-uses-temporal-to-power-replit-agent-reliably-at-scale
- `[temporal-codex]` https://temporal.io/blog/improving-java-sdk-codex-openai (2025-05-17)
- `[duolingo]` https://blog.duolingo.com/agentic-workflows/ (2025-12-11)
- `[duolingo-platform]` https://blog.duolingo.com/production-ready-ai-agent-platform/ (2026-08-04; found by the fact-check, not read by any note)
- `[dropbox-nova]` https://dropbox.tech/machine-learning/introducing-nova-our-internal-platform-for-coding-agents (2026-05-21)
- `[bitrise]` https://bitrise.io/blog/post/how-we-built-a-coding-agent-that-lives-in-slack-and-the-recipe-to-build-your-own (2026-07-15)
- `[sentry-autofix]` https://docs.sentry.io/product/ai-in-sentry/seer/autofix
- `[sentry-pricing]` https://docs.sentry.io/pricing/
- `[incidentio]` https://docs.incident.io/investigations/trust-and-safety
- `[spotify-3]` https://engineering.atspotify.com/2025/12/feedback-loops-background-coding-agents-part-3
- `[spotify-cwc]` https://engineering.atspotify.com/2026/6/code-with-claude-coding-is-no-longer-the-constraint
- `[infoq-honk]` https://www.infoq.com/news/2026/03/spotify-honk-rewrite
- `[ramp-inspect]` https://builders.ramp.com/post/why-we-built-our-background-agent and https://ramp.com/blog/introducing-inspect
- `[airbnb]` https://internal-agents.com/agents/airbnb-airchat
- `[vercel-tools]` https://vercel.com/blog/we-removed-80-percent-of-our-agents-tools (2025-12-22)
- `[vercel-agentsmd]` https://vercel.com/blog/agents-md-outperforms-skills-in-our-agent-evals (2026-01-27)
- `[arxiv-agentsmd]` https://arxiv.org/abs/2602.11988
- `[cloudflare-review]` https://blog.cloudflare.com/ai-code-review/ (2026-04-20)
- `[vercel-58]` https://vercel.com/blog/58-percent-of-prs-in-our-largest-monorepo-merge-without-human-review (2026-04-06; page not opened by any note)

Issue trackers read for small-scale evidence

- `[symphony-121]` https://github.com/openai/symphony/discussions/121
- `[cyrus-1328]` https://github.com/cyrusagents/cyrus/issues/1328
- `[cyrus-1381]` https://github.com/cyrusagents/cyrus/issues/1381
- `[oi-1363]` https://github.com/open-inspect/background-agents/issues/1363
- `[oi-1371]` https://github.com/open-inspect/background-agents/issues/1371
- `[oi-2493]` https://github.com/open-inspect/background-agents/issues/2493
- `[ghaw-79510]` https://github.com/github/gh-aw/issues/79510
- `[cca-1482]` https://github.com/anthropics/claude-code-action/issues/1482

---

## 11. How this report was checked

After the first version, fact-checkers tried to refute the fourteen claims the recommendation rests on, by opening the sources on 2026-11-21. Eleven held, one was wrong, two cannot be proven. The corrections are in the text above. **The recommendation did not change**: the wrong claim concerned which engines a Rust worker can stand on, which touches only the optional engine exit.

| # | Claim | Status |
|---|---|---|
| C1 | LangChain's organisation has no Rust port: one Rust repository of its own, unrelated | Confirmed. Detail added: eight forks of data libraries also exist |
| C2 | LangGraph's run methods default to a checkpoint written in the background | Confirmed, in the source at 1.0.0, 1.2.0 and main |
| C3 | The server that adds queue and recovery is under Elastic 2.0 and needs a licence key | Confirmed for the licence and the key. The exact paid plan is not stated on a citable page: softened in 2.5 |
| C4 | For other languages, Anthropic documents running the command-line tool as a child process | Confirmed. Limit added in 4.3: a hand-written wrapper does not get the SDK's callbacks |
| C5 | `claude -p` has JSON output, a schema, resume, caps and a deny-instead-of-ask flag | Confirmed, from vendor documentation with no stability promise |
| C6 | Temporal is the only durable engine supported for production in Rust | **Wrong.** AWS published a 1.0 Rust SDK for Lambda durable functions on 2026-11-19. Corrected in 1, 3.5, 4.1, 4.4, 4.5 and 9 |
| C7 | Forgejo has no approval gate, no private shared workflow, no narrowing of the job token | Confirmed from documentation of v17.0.2, not tested. Two of the three have work in progress |
| C8 | Cursor's "one nine to two nines" is the only before-and-after figure, on a product's control plane | Unverifiable as "the only". The figure is confirmed, self-reported, no method; it is the agent loop that moved. Reworded in 5.1 |
| C9 | Duolingo is the only company naming an engine for an internal workflow; 5 minutes against 1 to 2 days | Unverifiable as "the only"; now "the only one found". Both figures confirmed. A second Duolingo post added in 5.2 |
| C10 | A tracker daemon had 15 out-of-memory kills in about four weeks, unnoticed | Confirmed. One user, one install |
| C11 | 25 failures in 100 runs in GitHub's own repository; no automatic retry | Confirmed, as a capped one-day sample with test workflows. Caveat strengthened in 5.3 |
| C12 | Stripe's blueprints alternate code steps and agent steps, with two CI rounds at most | Confirmed |
| C13 | A Jira rule can call a forge directly; Linear needs a relay | Confirmed. Limit added in 3.3: allowed ports and addresses for Jira; Linear's exact retry wording |
| C14 | The Thoughtworks Radar moved LangGraph from Adopt to Trial, for a design reason | Confirmed. The page was last updated on 2026-04-15 |

Also corrected from the checkers' side remarks: Forgejo dispatch inputs are typed, not strings only; the Forgejo concurrency default is stated per event; the Open-Inspect loss issue was fixed and its author handed over, he did not just leave; "the official SDKs spawn the process" is shown for the Claude Agent SDK only; Inngest's Rust crate has had no release since 2024; the Stripe post date; a duplicated source key.

**Not checked in this pass.** The LangChain and LangGraph version numbers other than LangGraph's latest release, the funding amount, the Gitea and GitLab columns of the forge table, the claim that Forgejo's default job image ships only Node, and every company figure of section 5 other than Cursor's, Duolingo's and Stripe's. The checkers found the AWS release notes but not AWS's own announcement page. Nothing was prototyped or run on a forge.
