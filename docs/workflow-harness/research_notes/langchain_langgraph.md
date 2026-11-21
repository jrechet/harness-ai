# LangChain and LangGraph, explained from scratch

Research note, written 2026-11-21. All versions, stars and download counts were read on that day.

## Summary

1. **LangChain** (October 2022) began as glue code to chain prompts and parse model output, at a time when models could not call tools by themselves. That first job is mostly obsolete. In version 1.x (October 2025) it is a thin "agent loop + middleware + model adapters" library; the old chains live in a separate `langchain-classic` package. Current versions: `langchain` 1.5.2, `langgraph` 1.2.24, `deepagents` 0.7.41.
2. **LangGraph** (January 2024) is a different thing: a small runtime that runs a workflow as a graph of steps with saved state. It gives pause/resume, human approval, crash recovery and replay. This part did not age; it is the reason large teams (Uber, GitLab, LinkedIn, Klarna) still use the stack.
3. The company now earns its money on **LangSmith** (tracing, evals, hosting), which it sells as framework-agnostic. It raised $300M at a $3B valuation on 2026-11-13. The open-source libraries are the entry door, not the product.
4. The criticism is real and partly admitted by LangChain itself: early abstractions "got in the way", churn is high (Deep Agents went from 0.7.0 to 0.7.41 in 16 weeks), and big users wrap LangGraph in their own layer anyway. Several teams removed LangChain for a direct SDK loop; none of the public removals found concern LangGraph.
5. Honest verdict for end of 2026: you do not need LangChain to call a model or run a tool loop. You may want LangGraph, or an equivalent (Temporal, a job queue plus a state table), the day a workflow must survive a crash, wait hours for a human, or be replayed. There is no official Rust version of either.

## How to read this note

Each fact carries a label:

- **[M] measured**: read directly from a registry, a repository, or an official documentation page on 2026-11-21.
- **[V] vendor**: self-reported by LangChain Inc. or by another vendor about its own product. Plausible, not independently checked.
- **[S] secondary**: reported by a third party (press, blog, survey summary).
- **Judgment**: my own reading. Marked as such.

"Not found" means I looked and did not find it. The list is at the end.

## 1. Vocabulary, in plain words

- **LLM (large language model)**: the model you send text to and get text back from.
- **Prompt template**: a text with holes, filled in before the call. Example: "Summarise {document} in {n} lines".
- **Chain**: a fixed sequence of steps where the output of one is the input of the next. Prompt, then model call, then parsing.
- **Output parser**: code that turns the model's free text into a structure (JSON, a list). Needed when models only returned text.
- **Tool calling** (also "function calling"): the model returns a structured request "call function X with arguments Y" instead of prose. The program runs X and sends the result back. Models do this natively today.
- **Agent**: a model that calls tools in a loop until the task is done. The model decides the next step.
- **Workflow**: steps and their order are written in code. The model fills in individual steps but does not choose the path.
- **State graph**: a workflow drawn as nodes (steps) and edges (what comes next), sharing one state object. Unlike a chain, it can loop back.
- **Checkpoint**: a saved snapshot of the state after a step. A **checkpointer** is the component that writes snapshots to a database.
- **Thread**: one run of a workflow, identified by a `thread_id`. All its checkpoints belong to it.
- **Durable execution**: a run that survives a process crash or a long pause and continues where it stopped.
- **Interrupt / human-in-the-loop (HITL)**: the run stops at a chosen point, waits for a person, and resumes with the person's answer.
- **Time travel**: go back to an earlier checkpoint, replay from there, or fork with a modified state.
- **Harness**: everything around the model loop: system prompt, tools, file access, sub-agents, context trimming. Claude Code is a harness. So is LangChain's Deep Agents.
- **Middleware**: a hook that runs before or after each model call or tool call, to trim context, ask approval, redact data.
- **Trace**: the recorded tree of every model call and tool call in one run. The raw material of observability.
- **Eval**: an automated test for model behaviour, scored on a set of examples.

LangChain's own three-layer vocabulary, which the rest of the industry has partly adopted [V]:

| Layer | LangChain product | What it adds | Others it names in the same slot |
|---|---|---|---|
| Runtime | LangGraph | durable execution, streaming, HITL, persistence | Temporal, Inngest |
| Framework | LangChain | model adapters, agent loop, middleware | Vercel AI SDK, CrewAI, OpenAI Agents SDK, Google ADK, LlamaIndex |
| Harness | Deep Agents | default tools, file system, sub-agents, context management | Claude Agent SDK, Manus, coding CLIs |

Source: https://docs.langchain.com/oss/python/concepts/products.md and https://www.langchain.com/blog/agent-frameworks-runtimes-and-harnesses-oh-my (2025-10-25). The author himself writes that the lines are "blurry". Note the drift: the 1.x overview page now also calls LangChain's `create_agent` "a minimal, highly configurable agent harness" [M: https://docs.langchain.com/oss/python/langchain/overview.md].

## 2. Why each one was created

### LangChain (2022): glue for models that could only return text

Timeline, from LangChain's own documentation [V: https://docs.langchain.com/oss/python/langchain/philosophy.md] and repository data [M]:

| Date | Event |
|---|---|
| 2022-10-17 | GitHub repository created [M]. v0.0.1 on 2022-10-24: "LLM abstractions" and "Chains". A side project of Harrison Chase. |
| 2022-11-30 | ChatGPT launches one month later; the project takes off [V: https://www.langchain.com/blog/three-years-langchain]. |
| 2022-12 | First general agents, based on the ReAct paper. The model writes JSON as text; LangChain parses it to find the tool call. |
| 2023-02 | LangChain Inc. founded. |
| 2023 | OpenAI adds function calling to its API. LangChain's timeline files this under 2023-03; the commonly cited date is June 2023 (not re-verified here). LangChain switches from parsing JSON to native tool calls. |
| 2023-06 | LangSmith released as a closed-source platform for observability and evals. |
| 2023 Q3 | LCEL (LangChain Expression Language) introduced: a pipe syntax, `prompt | model | parser`, to compose steps [S: https://en.wikipedia.org/wiki/LangChain]. |
| 2024-01 | v0.1.0, first release aimed at stability. |
| 2024-06 | "Over 700 integrations", split into separate packages. |
| 2024-10 | "Most chains and agents were marked as deprecated", with guides to migrate to LangGraph. |
| 2025-10 | v1.0.0 (tag 2025-10-17 [M], announced 2025-10-20/22). All chains and agents replaced by one agent abstraction built on LangGraph. |

The problem it solved in 2022-2023, in one sentence: models were text-in, text-out, each provider had a different API, and every team rewrote the same prompt formatting, retry, parsing and "pretend to call a tool" code. LangChain packaged that code.

### LangGraph (2024): control and state, after the first design failed

The launch post is dated 2024-01-17 [V: https://www.langchain.com/blog/langgraph]. Its stated reasons:

- Chains built with LCEL were "directed acyclic graphs": no easy way to loop. Agents are loops.
- The existing `AgentExecutor` handed nearly every decision to the model. "Often times more control is needed": force a tool first, change the prompt depending on state.

Six months later (2024-06-27), LangGraph v0.1 and the hosted "LangGraph Cloud" beta were announced with this admission: "the higher level abstraction hides too many details from the developer" [V: https://www.langchain.com/blog/langgraph-cloud].

So LangGraph is LangChain Inc.'s correction of LangChain. It is lower level, it does not write prompts for you, and it does not require LangChain: "LangGraph does not require LangChain" [M: https://docs.langchain.com/oss/python/langgraph/overview.md].

## 3. What they contain today

### 3.1 Versions and activity, measured 2026-11-21

| Package | Latest | Released | Stars | Downloads, last 30 days |
|---|---|---|---|---|
| `langchain` (Python) | 1.5.2 | 2026-11-18 | 150,004 (repo created 2022-10-17) | 157.0M (PyPI) |
| `langchain-core` (Python) | 1.8.4 | 2026-11-19 | same repo | 160.7M |
| `langchain-classic` (old chains) | 1.0.8 | 2026-06-10 | same repo | 17.3M |
| `langgraph` (Python) | 1.2.24 | 2026-11-20 | 45,231 (repo created 2023-08-09) | 61.3M |
| `langgraph-checkpoint-postgres` | 3.2.1 | 2026-11-14 | same repo | 13.8M |
| `deepagents` (Python) | 0.7.41 | 2026-11-20 | 31,497 (repo created 2025-07-27) | 9.5M |
| `langsmith` (Python SDK) | 0.16.0 | 2026-11-21 | repo moved 2026-10-16 | 96.0M |
| `langchain` (npm) | 1.6.7 | n/a | 18,355 (langchainjs) | 17.9M |
| `@langchain/langgraph` (npm) | 1.7.5 | n/a | 3,422 (langgraphjs) | 21.7M |
| `deepagents` (npm) | 1.17.0 | n/a | n/a | 2.7M |

Sources [M]: GitHub API (`repos/langchain-ai/{langchain,langgraph,deepagents,langchainjs,langgraphjs}`), https://pypi.org/pypi/langchain/json and siblings, https://pypistats.org/api/packages/langgraph/recent and siblings, https://api.npmjs.org/downloads/point/last-month/@langchain/langgraph and siblings. Download counts include CI and mirrors; read them as "very widely installed", not as a count of users. All repositories are MIT licensed.

Minor-version dates [M, GitHub releases]:

- `langchain`: 1.0.0 2025-10-17, 1.1.0 2025-11-24, 1.2.0 2025-12-15, 1.3.0 2026-05-12, 1.4.0 2026-09-03, 1.5.0 2026-11-11.
- `langgraph`: 1.0.0 2025-10-17, 1.1.0 2026-03-10, 1.2.0 2026-05-12. No 1.3 and no 2.0 exist.
- `deepagents`: 0.3.0 2025-12-08, 0.4.0 2026-02-10, 0.5.0 2026-04-07, 0.6.0 2026-05-12, 0.7.0 2026-07-29.

### 3.2 LangChain 1.x

What is in the `langchain` package now [M: https://docs.langchain.com/oss/python/migrate/langchain-v1.md, V: https://www.langchain.com/blog/langchain-langgraph-1dot0]:

- **`create_agent`**: one function that builds a "model calls tools in a loop" agent. It runs on the LangGraph runtime, so it inherits checkpoints and interrupts. It replaces `create_react_agent` from `langgraph.prebuilt`.
- **Middleware**: hooks around the loop. Built-in ones: human approval, summarising history near the context limit, PII redaction, model retry with backoff, content moderation. Since 1.5.0 (beta): model routing and blocking of tool calls judged risky.
- **Model adapters**: one interface over OpenAI, Anthropic, Google and others. "Standard content blocks" normalise reasoning traces, citations and tool calls across providers.
- **Structured output** via the provider's native feature (`ProviderStrategy`) or via a tool call (`ToolStrategy`). "Prompted output" was removed.
- **MCP support** (Model Context Protocol, the standard way to plug external tools into an agent) moved into `langchain.mcp` in 1.4.0, in beta; the separate `langchain-mcp-adapters` repository is archived [M].

What left the package: "Legacy chains (`LLMChain`, `ConversationChain`, etc.)", retrievers, indexes and the prompt hub moved to `langchain-classic` [M, same migration guide].

**LCEL today.** The pipe syntax still works: the `runnables` module is still in `langchain-core` and was last changed on 2026-11-11 [M: GitHub API, `libs/core/langchain_core/runnables`]. But it is no longer taught: the 240-page Python documentation index contains zero occurrences of "LCEL" or "expression language" [M: https://docs.langchain.com/_llms/agent-development-lifecycle/build/python.txt, grep on 2026-11-21]. Judgment: LCEL is in maintenance, not a thing to learn in 2026.

**Stability promise.** "No breaking changes until 2.0" [V, 1.0 announcement]. In practice the Python floor moved inside 1.x: 3.10+ at 1.0, 3.11+ at 1.5.0 [M: changelog, https://docs.langchain.com/oss/python/releases/changelog.md].

### 3.3 LangGraph 1.x

The core model [M: https://docs.langchain.com/oss/python/langgraph/overview.md]: "You define workflows as graphs of shared state, nodes, and edges, and can mix deterministic steps with LLM-driven steps in the same graph." It "does not prescribe prompts or agent architecture."

Minimal shape, from the official overview:

```python
from langgraph.graph import StateGraph, MessagesState, START, END

graph = StateGraph(MessagesState)
graph.add_node(mock_llm)            # a node is a plain Python function: state in, update out
graph.add_edge(START, "mock_llm")
graph.add_edge("mock_llm", END)
graph = graph.compile()             # pass checkpointer=... here to get persistence
```

There is also a "functional API" (`@entrypoint` / `@task` decorators) for people who prefer ordinary functions to a drawn graph.

**Checkpointers** [M: https://docs.langchain.com/oss/python/langgraph/checkpointers.md]

- "A checkpointer saves a snapshot of graph state at each super-step, organized into threads." A super-step is one tick of the graph: all nodes scheduled for that tick run, possibly in parallel.
- Outputs of each finished node inside a tick are also saved ("pending writes"). If one node of a parallel tick fails, the successful ones are not re-run.
- Backends: in-memory (lost at restart, not for production), SQLite (development), Postgres (production), MongoDB, Azure Cosmos DB; a Redis one exists as a separate package. A custom backend means implementing about five methods; a conformance test suite is provided.
- State can be encrypted at rest (`EncryptedSerializer`, AES key in `LANGGRAPH_AES_KEY`).
- Checkpoints pile up. By default the full value of every state field is written at each tick. `DeltaChannel` (beta, needs `langgraph>=1.2`) stores only the increments.

**Durable execution** [M: same page]

Three durability modes, chosen per call:

- `"exit"`: write only when the run ends or is interrupted. Fast. A crash mid-run loses everything.
- `"async"`: write in the background while the next step runs. Small risk of a lost checkpoint on crash.
- `"sync"`: write before the next step starts. Safest, slower.

Read the fine print: "Replay re-executes nodes; it doesn't just read from cache", and on resume after an interrupt "the runtime restarts the entire node from the beginning" [M: https://docs.langchain.com/oss/python/langgraph/use-time-travel.md and https://docs.langchain.com/oss/python/langgraph/interrupts.md]. Consequence: any side effect inside a node (create a ticket, push a branch, send a message) must be idempotent, meaning safe to run twice. The docs say so: prefer upserts to inserts, put side effects after the interrupt.

Second fine print: the library saves state; it does not watch your process. If the process dies, something else must notice and call the graph again with the same `thread_id`. That supervisor is the commercial "Agent Server" (section 3.6), or your own code.

**Interrupts (human approval)** [M: https://docs.langchain.com/oss/python/langgraph/interrupts.md]

- `interrupt(payload)` inside a node pauses the run and saves state. The caller gets the payload, shows it to a person, and resumes with `Command(resume=value)` on the same `thread_id`. The value becomes the return value of `interrupt()`.
- Needs a checkpointer and a thread id. The pause can last minutes or weeks.
- Patterns documented: approve/reject before a critical action, review-and-edit, approval inside a tool, several parallel interrupts.
- Pitfalls documented: do not wrap `interrupt()` in a bare try/except; several interrupts in one node are matched by position; after a long pause, re-read external state before acting.
- In LangChain's `create_agent`, the same mechanism is packaged as `HumanInTheLoopMiddleware` with four decisions: approve, edit, reject, respond [M: https://docs.langchain.com/oss/python/langchain/human-in-the-loop.md].

**Time travel** [M: https://docs.langchain.com/oss/python/langgraph/use-time-travel.md]

- `get_state_history` lists the checkpoints of a thread. Invoke with an old checkpoint to **replay** from there. `update_state` on an old checkpoint creates a **fork**: "The original execution history remains intact."
- Limits: nodes after the chosen point really run again (new model calls, possibly different results); interrupts fire again; a sub-graph counts as one step unless it has its own checkpointer.

**Added in 2026** [M: https://docs.langchain.com/oss/python/releases/changelog.md]

- 1.1 (March): typed streaming and typed results (`version="v2"`), fixes to time travel with interrupts and sub-graphs.
- 1.2 (May): per-node timeouts, node-level error handlers that can reroute (useful for compensation, "undo what the failed step started"), graceful drain (`RunControl.request_drain()` stops after the current tick and leaves a resumable checkpoint), `DeltaChannel` (beta), event streaming v3 (beta). Timeouts and error handlers are Python-only and apply to async nodes only.
- 1.2.12: `interrupt()` accepts a `response_schema` to validate the human's answer.

### 3.4 Deep Agents (the harness)

- What it is: "the agent harness for complex, multi-step work. It adds planning, a virtual filesystem for context, subagent spawning, and long-term memory on top of LangChain and LangGraph" [M: https://docs.langchain.com/oss/python/deepagents/overview.md]. Also: skills, sandboxed code execution, human approval, an ACP adapter for editors.
- Position: LangChain's answer to Claude Code and the Claude Agent SDK, with the claim of being model-agnostic [V: https://www.langchain.com/blog/on-agent-frameworks-and-agent-observability, 2026-02-12].
- Status: version 0.7.41, still 0.x. An independent review calls out its "beta status and rapid release cadence" as upgrade risk and says it is a poor fit for "short tool calls, deterministic workflows" [S: https://wavect.io/blog/langchain-deep-agents-review/, 2026-08-23, reviewed 2026-11-11].
- A telling release: v0.7 (2026-07-29) **removed** the default system prompt, cut tool descriptions by 43%, and made the todo-list planner opt-in, because LangChain's own evals showed the planning prompt "did not significantly improve performance". Base input tokens per turn fell about 65%, from about 6k to about 2k [V: https://www.langchain.com/blog/deep-agents-v0-7]. Judgment: this is the vendor measuring that scaffolding built for 2025 models is dead weight for 2026 models.
- **Open SWE**, renamed "Robin" (11,246 stars [M]): LangChain's own "open-source software factory built on Deep Agents". It takes work from GitHub issues, Slack or Linear, runs in a per-thread sandbox, opens a pull request, reviews PRs and watches CI. "LangGraph provides durable execution and thread state." The README warns: "Under active development. Expect breaking changes", no external contributions, and deploying it as is "requires Managed Deep Agents", the paid hosted runtime [M: https://github.com/langchain-ai/open-swe]. The launch post (2026-03-17) says it captures patterns seen in Stripe's, Ramp's and Coinbase's internal coding agents [V: https://www.langchain.com/blog/open-swe-an-open-source-framework-for-internal-coding-agents].

### 3.5 LangSmith (the commercial platform)

- What it is: tracing, evals, prompt management, and since 2025 hosting. Closed source.
- Sold as framework-agnostic: integrations with Claude Agent SDK, OpenAI Agents, CrewAI, Mastra, PydanticAI, Vercel AI SDK, plus OpenTelemetry ingestion. Clay, Harvey and Vanta are cited as customers that use LangSmith **without** LangChain's open-source frameworks [V: https://www.langchain.com/blog/on-agent-frameworks-and-agent-observability].
- 2026 additions [V: https://www.langchain.com/blog/interrupt-2026-overview, 2026-05-14; https://www.langchain.com/blog/october-2026-langchain-newsletter, 2026-10-15]: Engine (clusters failing traces, proposes fixes, can open a PR; public beta in May), Sandboxes (microVMs for agent-written code; GA), Managed Deep Agents (hosted harness), Context Hub (versioned prompts, skills, memory files), LLM Gateway (spend caps, redaction, audit; beta), Fleet (no-code agent builder), Trajectories, Fine-Tuning. SmithDB, the new trace store, is written in Rust.
- Pricing [M: https://www.langchain.com/pricing]: Developer $0 (1 seat, 5k traces/month); Plus $39 per seat per month (10k traces, one small hosted Agent Server); Enterprise custom. Usage is metered in "LangChain Standard Units" at $1.00 each. Self-hosted and hybrid are Enterprise only.
- Money: $125M Series B at $1.25B (October 2025), then $300M Series C at $3B on 2026-11-13, led by CapitalG. "7,000+ organizations rely on LangSmith". The post positions LangSmith as "the framework-agnostic platform to run, improve, and govern agents" and says nothing about the roadmap of the open-source libraries [V: https://www.langchain.com/blog/series-c]. Revenue: not disclosed.

### 3.6 Deployment: "LangGraph Platform", now "LangSmith Deployment" / "Agent Server"

Names changed four times; you will meet all of them in articles:

| Period | Name | Source |
|---|---|---|
| 2024-06 | LangGraph Cloud (beta) | [V] https://www.langchain.com/blog/langgraph-cloud |
| 2025-05-14 | LangGraph Platform (general availability) | [S] https://en.wikipedia.org/wiki/LangChain |
| 2025-10 | LangSmith Deployment (rename; Studio becomes LangSmith Studio) | [V] https://docs.langchain.com/langsmith/changelog |
| 2026 | "Agent Server" on the pricing and docs pages | [M] https://www.langchain.com/pricing |

What it is: a server that runs LangGraph graphs with a task queue, Postgres checkpoints, streaming, scheduled runs and horizontal scaling. This is the piece that restarts a crashed run.

Options [M: https://docs.langchain.com/langsmith/deploy-overview.md]: Cloud (needs Plus or Enterprise), Hybrid, Self-hosted with control plane (Enterprise), and "Standalone server": "Bring your own PostgreSQL, Redis, and LangSmith license; no control plane."

Judgment: the open-source library gives you checkpoints for free. The component that makes a fleet of runs reliable is licensed. Teams that want to stay fully open source write that supervisor themselves or put Temporal underneath (section 5.5).

### 3.7 Things that were retired

- **LangServe** (expose a chain as a REST API): repository archived [M: GitHub API, `langchain-ai/langserve`].
- **`langgraph.prebuilt`**: deprecated at 1.0, moved to `langchain.agents`.
- **`langgraph-supervisor`** (multi-agent helper): a migration guide away from it is in the docs index [M].
- **`langchain-mcp-adapters`**: archived, folded into `langchain.mcp` [M].
- **`langsmith-sdk`** repository: archived 2026-10-16, split into `langsmith-python` and `langsmith-javascript` [M].

## 4. Who uses them in production, and for what

Most named users come from LangChain's own pages. I separate those from statements made by the companies themselves.

**Stated by the company itself**

| Company | What | Source |
|---|---|---|
| GitLab | Duo Agent Platform. GitLab "researched available AI frameworks and selected LangGraph" for model adapters, durable execution and traceability. It then built a "Flow Registry" that compiles YAML into LangGraph flows, because raw graphs gave "no reusability, no composability". Python per flow fell 45%. | [V, GitLab] https://about.gitlab.com/blog/how-gitlab-reduced-code-per-agentic-flow-ratio/ (2026-09-22) |
| Uber | Developer platform: Validator (flags issues in the IDE) and AutoCover (test generation), plus "Lang Effect", Uber's own opinionated wrapper around LangGraph. About 21,000 developer hours saved, coverage up 10%, about 5,000 developers served. | [S, summary of Uber's 2025 talk] https://www.zenml.io/llmops-database/building-ai-developer-tools-using-langgraph-for-large-scale-software-development ; talk: https://youtu.be/Bugs0dVcNI8 (not watched) |
| LinkedIn | Text-to-SQL assistant and GenAI application stack. | [V, LinkedIn] https://www.linkedin.com/blog/engineering/ai/practical-text-to-sql-for-data-analytics (listed in LangGraph case studies, not re-read) |
| Qodo | Coding agent. | [V, Qodo] https://www.qodo.ai/blog/why-we-chose-langgraph-to-build-our-coding-agent/ (not re-read) |
| Temporal | Ships a LangGraph plugin; evidence that enough of its customers run LangGraph to justify it. | [V, Temporal] https://temporal.io/blog/temporal-langgraph-plugin-durable-execution (2026-07-16) |

**Stated by LangChain** [V]

- Klarna: customer-support assistant on LangGraph and LangSmith. 2.5 million conversations, "work equivalent of 700 full-time staff", resolution time down 80% (https://www.langchain.com/blog/customers-klarna, 2025-02-12).
- LinkedIn (AI recruiter, hierarchical agents), Uber (code migrations, unit-test generation), Replit (coding agent with human-in-the-loop), Elastic (threat detection), AppFolio (property-manager copilot, "over 10 hours a week" saved) (https://www.langchain.com/blog/is-langgraph-used-in-production, 2025-02-04).
- 1.0 announcement: Uber, LinkedIn, Klarna, JP Morgan, BlackRock, Cisco; a quote from Rippling's head of AI (https://www.langchain.com/blog/langchain-langgraph-1dot0).
- Series C post: Harvey, Rippling, NVIDIA, Toyota, Salesforce, Clay ("hundreds of millions of agent runs per month" monitored), Workday (new agent deploy time "from five months to under a day") (https://www.langchain.com/blog/series-c).
- The official case-study list has 41 entries, among them BlackRock, Cisco (three teams), C.H. Robinson, Infor, Komodo Health, Morningstar, Rakuten, Vodafone, the Abu Dhabi Government (https://docs.langchain.com/oss/python/langgraph/case-studies). Most entries date from 2024-2025.

**Independent usage numbers**

- Stack Overflow Developer Survey 2025, among respondents who build or use agents (n = 3,758): LangChain 32.9%, LangGraph 16.2% [M: https://survey.stackoverflow.co/2025/ai].
- Stack Overflow pulse survey, late April 2026, 1,100 respondents: LangChain 26% used / 34% want to use; OpenAI Agents SDK 27% / 29%; LangGraph 19% / 28%. The article's text gives different figures (LangChain 22%, LangGraph 14%) from its own chart. Same survey: 69% run a single agent, 63% rarely or never let agents run fully unattended [S: https://stackoverflow.blog/2026/05/27/agents-on-a-leash-agentic-ai-remains-mostly-monitored-at-work/].
- LangChain's own survey (1,340 respondents, fielded Nov-Dec 2025, published 2026-06-12): 57.3% have agents in production; 89% have some observability; quality is the top barrier [V: https://www.langchain.com/state-of-agent-engineering]. The audience is LangChain's own, so the numbers lean favourable.

Judgment: within one year a lab SDK (OpenAI's) caught up with LangChain in reported usage. LangChain is no longer the default; it is one option among several.

**A pattern worth noticing.** The two best-documented engineering users, Uber and GitLab, both put their own layer on top of LangGraph (Lang Effect; Flow Registry). GitLab says low-level graphs are "not a good match for a platform implementation". LangGraph was the engine, not the product.

## 5. The criticism, and LangChain's answers

### 5.1 "The abstractions hide the prompt and cost more than they save"

- **Max Woolf, "The Problem With LangChain"** (July 2023): advises newcomers not to start with LangChain [S: https://minimaxir.com/2023/07/langchain-problem/, known through coverage, not re-read].
- **Hamel Husain, "Fuck You, Show Me The Prompt"** (2024-02-14): frameworks build prompts for you and hide them; intercept the HTTP calls and read what is actually sent before deciding to keep a framework [S: https://hamel.dev/blog/posts/prompt/].
- **Octomind, "Why we no longer use LangChain for building our AI agents"** (2024-06-20; 480 points and 297 comments on Hacker News [M: https://news.ycombinator.com/item?id=40739982]). The team used LangChain in production for about a year, then removed it: "rigid high-level abstractions", as much time spent "understanding and debugging LangChain" as building features, and "LangChain became our biggest obstacle" when moving from one sequential agent to something more complex. Replacement: "modular building blocks with minimal abstractions" [S, quotes via search summaries; the original at octomind.dev did not resolve on 2026-11-21].
- **Microsoft ISE, "Earning agentic complexity"** (2024-09-09): "large, breaking changes roll through LangChain that required significant rework"; security reports mean "most of our first-party teams eschew its use"; the weight "still needs to pay for itself" [S: https://devblogs.microsoft.com/frontier-engineering/earning-agentic-complexity/].
- **Vettio, "Why we replaced LangChain with the raw Anthropic SDK in production"** (April 2026): 14 stack frames of LangChain internals per agent call; CI pinned to one commit for six months; after the rewrite, p50 latency 2.1s to 1.4s, error rate 0.9% to 0.2%, integration code 812 to 187 lines. Key line: "Abstractions pay for themselves when the underlying APIs are bad." The author still names "LangGraph workflows" and LangSmith as valid reasons to stay [S, single team, self-reported: https://dev.to/tufailkhan457/why-we-replaced-langchain-with-the-raw-anthropic-sdk-in-production-3611].

### 5.2 "You do not need a framework"

- **Anthropic, "Building effective agents"** (2024-12-19): frameworks "often create extra layers of abstraction that can obscure the underlying prompts and responses, making them harder to debug." "We suggest that developers start by using LLM APIs directly: many patterns can be implemented in a few lines of code." "If you do use a framework, ensure you understand the underlying code." [M: https://www.anthropic.com/engineering/building-effective-agents]. Note: the page as served today lists the Claude Agent SDK and AWS Strands as example frameworks; from memory the original 2024 list began with LangGraph (not re-verified).
- **12-factor agents** (Dex Horthy, HumanLayer, 2025; 27,358 stars [M]): "I don't see a lot of frameworks in production customer-facing agents." "Most of them are rolling the stack themselves." Good agents "are comprised of mostly just software." Factors include "Own your prompts", "Own your control flow", "Launch/Pause/Resume with simple APIs", "Make your agent a stateless reducer" [M: https://github.com/humanlayer/12-factor-agents]. Note that several of these factors describe what LangGraph provides (pause/resume, state as a reducer); the disagreement is about owning the code, not about the needs.
- **The "big model" camp** (April 2025): OpenAI's agent guide and researchers argue that hand-built structure loses value as models scale; examples cited are Deep Research products, Bolt and Manus, which rely on a strong model with little workflow engineering [S: https://www.latent.space/p/oai-v-langgraph, 2025-04-20].

### 5.3 Churn

Measured, not opinion:

- Release cadence: `langgraph` 1.2.21 to 1.2.24 in eight days (2026-11-12 to 11-20); `deepagents` 0.7.0 to 0.7.41 in sixteen weeks [M: GitHub releases].
- Four names for the deployment product in two years (section 3.6); Open SWE renamed Robin; SDK repository split.
- Module moves: chains to `langchain-classic`; `langgraph.prebuilt` to `langchain.agents`; MCP adapters into `langchain.mcp`; `langgraph-supervisor` to a new pattern.
- Several headline features are still beta: MCP namespace, `DeltaChannel`, v3 streaming; "Python usually gets features before JavaScript"; "upgrades and rollbacks are operational events" for checkpoint formats [S: https://www.developersdigest.tech/blog/langchain-langgraph-whats-new-2026, updated 2026-11-17].

### 5.4 Security record

A library that deserialises saved state and model output is an attack surface.

- **CVE-2025-68664 ("LangGrinch")**: serialization injection in `langchain-core`, CVSS 9.3; a crafted model response could be treated as a serialized object. Fixed in `langchain-core` 0.3.81 and later [S: https://labs.cloudsecurityalliance.org/research/csa-research-note-langchain-langgraph-vulnerabilities-202603/].
- **CVE-2025-64439**: remote code execution in `langgraph-checkpoint` JSON deserialization, fixed in 3.0.0 [S: https://advisories.gitlab.com/pypi/langgraph-checkpoint/CVE-2025-64439/].
- **CVE-2025-67644 + CVE-2026-28277** (SQLite checkpointer SQL injection chained with unsafe msgpack deserialization, reaching code execution) and **CVE-2026-27022** (Redis checkpointer). Preconditions: self-hosted, SQLite or Redis checkpointer, and an application that passes a user-controlled `filter` to `get_state_history()`. "PostgreSQL-backed deployments" and the managed service were not affected. Fixed in `langgraph-checkpoint-sqlite` 3.0.1, `langgraph` 1.0.10, `langgraph-checkpoint-redis` 1.0.2 [S: Check Point Research, 2026-06-11, http://research.checkpoint.com/2026/from-sqli-to-rce-exploiting-langgraphs-checkpointer/].

Judgment: all were fixed, and the Postgres path was spared. The lesson is general: checkpoint stores hold executable-adjacent data; never expose their query filters to users, and pin and patch.

### 5.5 "Checkpoints are not durable execution"

Temporal's argument (2026-07-16): a LangGraph checkpoint "preserves data, not execution". A run lives in one process; if it dies, something else must detect it and resume. Temporal's plugin runs the graph as a Temporal Workflow and each node as a retried Activity; Public Preview, Python only [V, competitor: https://temporal.io/blog/temporal-langgraph-plugin-durable-execution].

LangChain's side (2026-06-06): Temporal is better for "deterministic distributed workflows", saga-style compensation and non-AI workloads; LangGraph is better for agent work because memory, streaming, human-in-the-loop and tracing are built in. Combining both is possible "but the tradeoffs are real". Same page: agent authoring is Python and TypeScript only, and "a Go rewrite of the core data plane is also underway" [V: https://www.langchain.com/resources/langgraph-vs-temporal].

### 5.6 What LangChain answered

1. **It conceded the original design.** "We learned this the hard way": the first chains and agents "provided abstractions that got in the way"; the early agent class "didn't provide enough control back then, and it doesn't now" [V: https://www.langchain.com/blog/how-to-think-about-agent-frameworks, 2025-04-20]. Users complained about "breaking changes, hidden prompts, package bloat, dependency conflicts, and outdated docs"; the team "traded power for ease of use" [V: https://www.langchain.com/blog/three-years-langchain, 2025-10-20].
2. **It rebuilt lower.** LangGraph "is an orchestration framework with agent abstractions built on top", where nodes are ordinary code and nothing writes prompts for you. The useful things a framework brings, per Chase: short- and long-term memory, human-in-the-loop, "human-on-the-loop" (inspect and rerun), streaming, observability, fault tolerance [V, same April 2025 post].
3. **It froze the API.** 1.0 with "no breaking changes until 2.0"; old code parked in `langchain-classic`.
4. **It reframed.** Runtime / framework / harness (October 2025). Then: "Agent frameworks are still useful, but only if they evolve as fast as the models do", and "If it's a simple LLM request, adding a framework may be too heavy handed" [V: https://www.langchain.com/blog/on-agent-frameworks-and-agent-observability, 2026-02-12].
5. **It deleted its own scaffolding** when evals said so (Deep Agents 0.7).
6. **It moved the business** to a platform that does not require its libraries (LangSmith).

## 6. The honest question: still useful at the end of 2026?

Context that changed since 2022:

- Models call tools natively and return structured output natively.
- Labs ship their own agent SDKs. LangChain's own docs list the OpenAI Agents SDK and Google ADK as frameworks and the Claude Agent SDK as a harness.
- Coding agents run long tasks alone, with their own loop, sandbox, sub-agents and permission system.

Everything below is judgment, built on the evidence above.

### What aged

| Piece | Why it aged | Evidence |
|---|---|---|
| Prompt templates and `LLMChain` | A prompt is a string; a chain of two calls is two function calls. | Moved to `langchain-classic` [M]. |
| Output parsers, ReAct-style JSON parsing | Native tool calling and structured output. | "Prompted output" removed in 1.0 [M]. |
| LCEL pipe syntax | Solved composition of steps that no longer need a library. | Gone from the 1.x Python docs [M]. |
| `AgentExecutor`, memory classes | Too opaque; replaced by the LangGraph-backed loop. | Deprecated October 2024 [V]. |
| LangServe | Superseded by Agent Server. | Archived [M]. |
| Planner prompts, long default system prompts | Recent models plan without them. | Deep Agents 0.7 removed them [V]. |
| "One abstraction over all models" as a reason by itself | Still real if you truly switch providers; weak if you are committed to one. | Vettio; Anthropic's advice. |

### What did not age

| Need | Why it stays | Who provides it |
|---|---|---|
| Saved state and resume after a crash | A ticket-to-production run lasts hours and crosses CI, reviews, deploys. No model improvement removes this. | LangGraph checkpointers; Temporal; a job queue plus a state table you own. |
| Waiting for a human | Approval before merge or deploy can take a day. The run must sleep without holding a process. | LangGraph `interrupt`; Temporal signals; your own "pending approval" row. |
| Mixing fixed steps and model steps | Lint, tests and deploys are deterministic; only some steps need judgment. Uber's lesson: pair model agents with deterministic sub-steps. | LangGraph graphs; plain code. |
| Replay and fork | Debugging a non-deterministic run needs "start again from step 4 with this change". | LangGraph time travel; event-sourced designs. |
| Traces and evals | "You have no idea what inputs or outputs to expect until you ship it" [V, Chase]. 89% of surveyed teams have observability [V]. | LangSmith, or any OpenTelemetry-based tool; independent of framework choice. |

### Verdict per product

- **LangChain (the `langchain` package)**: optional. Useful as a multi-provider adapter with a ready agent loop and approval middleware. Not needed to call one provider or to drive an existing coding agent.
- **LangGraph**: still useful for exactly one class of problem: long, stateful, interruptible workflows that mix code steps and model steps, in Python or TypeScript. It is a library choice, not an architecture you cannot build yourself; the concepts (thread, checkpoint, interrupt, replay) are worth copying even if the library is not used.
- **Deep Agents**: a moving target (0.x, from 0.7.0 to 0.7.41 in 16 weeks). Interesting if you need a model-agnostic harness. If the team already drives Claude Code or a similar coding agent, it duplicates what that agent ships.
- **LangSmith**: judged separately from the libraries. It is the piece LangChain bets the company on, and it works without them.

## 7. When to use it, when not to

### LangChain

Use it when:

- You call several model providers and want one interface for messages, tools and structured output.
- You want a ready tool loop with approval, summarisation and retry middleware, in Python or TypeScript.
- You plan to grow into LangGraph or LangSmith and want the shortest path.

Do not use it when:

- You call one provider. Use its SDK; the loop is a few dozen lines.
- You orchestrate an existing coding agent (Claude Code, Codex and the like). The agent is already the loop.
- You need a small dependency tree, strict reproducibility, or a language other than Python or TypeScript.
- You are tempted by old tutorials using `LLMChain`, LCEL pipes or `AgentExecutor`. That is the retired API.

### LangGraph

Use it when:

- A run must survive a crash, a redeploy or a wait of hours for a human.
- The process is a real graph: branches, loops ("tests failed, go back to implement"), parallel steps.
- You want replay and fork for debugging, and per-step traces.
- The team writes Python or TypeScript and Postgres is available.

Do not use it when:

- The workflow is a straight line that finishes in minutes. A script is enough.
- You already run a durable execution engine (Temporal, Inngest) or a CI system that can hold state between jobs. Add model calls to that.
- Side effects cannot be made idempotent. Replay will run them again.
- You need the supervisor (queue, restart, scaling) but refuse both the LangSmith licence and writing it yourself.
- You want Rust or Go on the authoring side. There is no official port.

## 8. Notes for a ticket-to-production workflow harness

Judgment, for the architect who will synthesise the study.

1. **The questions LangGraph answers are the right questions.** Where is the state of a ticket run stored? What happens if the machine dies during CI? How does a human approve the merge and how long may that take? How do we replay a failed run? Any harness for feature or bug tickets must answer them, with or without LangGraph.
2. **Big users wrapped it.** Uber and GitLab both built a declarative layer above the graph (GitLab: YAML compiled to LangGraph). A team-level harness will need its own vocabulary of steps and gates in any case.
3. **LangChain's own software factory is the closest reference design.** Open SWE / Robin does issue to PR to review to CI follow-up with sandboxes, Slack/Linear/GitHub triggers, sub-agents, `AGENTS.md` injection, and approval prompts on pushes. Worth reading as a design even if not adopted; it is unstable and tied to a paid runtime.
4. **Idempotency is the hidden cost.** Every step that touches the outside world (open PR, comment on ticket, deploy) must tolerate being run twice. This is true of LangGraph, of Temporal, and of hand-written resume logic.
5. **Decision rule the evidence supports**: a skill or prompt when the step is judgment inside one agent session; deterministic code when the step must be guaranteed; a durable workflow engine only when the run outlives a session and needs gates. LangGraph is one candidate for the third case.
6. **Rust.** No official LangChain or LangGraph in Rust. LangChain Inc. itself uses Rust for SmithDB and is rewriting a data plane in Go, but agent authoring stays Python/TypeScript [V]. Community crates, measured 2026-11-21:

| Project | Stars | Crate | Total downloads | Note |
|---|---|---|---|---|
| `0xPlaygrounds/rig` | 9,212 | `rig-core` 0.47.0 (2026-11-20) | 4.63M | LLM application library, the most used; not a LangChain port. |
| `Abraxas-365/langchain-rust` | 1,364 | `langchain-rust` 8.0.0 (2026-11-03) | 164k | Community port of the chain-era LangChain. |
| `a-agmon/rs-graph-llm` | 390 | `graph-flow` 0.8.1 (2026-10-21) | 24k | Graph workflow with state, LangGraph-like. |
| `Onelevenvy/langgraph-rust` | 11 | n/a | n/a | "Not the official LangGraph Rust implementation." |

Sources [M]: GitHub API and https://crates.io/api/v1/crates/rig-core and siblings. None has the maturity of the Python original. A Rust harness would implement the concepts (state table, checkpoints, interrupts) directly, or sit on a durable engine with a Rust SDK. Whether such an SDK is mature is outside this note.

## 9. Not found, or not verified

- The original Octomind article: the domain did not resolve on 2026-11-21. Date and reception confirmed through Hacker News; quotes come from search summaries.
- Whether Replit still runs its agent on LangGraph in 2026. Only 2024 material found.
- A public post from a named large company about removing **LangGraph** (as opposed to LangChain). None found.
- LangChain Inc. revenue or ARR. Not disclosed.
- An independent benchmark of LangGraph durability or overhead against Temporal. Only vendor and competitor material found.
- The default durability mode of `langgraph` 1.2. The docs list the three modes; I did not confirm which is the default.
- The per-trace overage price of LangSmith. The pricing page says "pay as you go" in LSUs without a per-trace rate.
- A date or roadmap for LangGraph 2.0 or LangChain 2.0. None published.
- Uber's 21,000-hour figure in Uber's own words: known through a summary of the talk, the video was not watched.
- Max Woolf's 2023 post and the Towards AI "LangGraph in November 2026" article (HTTP 403) were not read directly.
- Detailed feature comparison with the Claude Agent SDK, OpenAI Agents SDK and Google ADK (sessions, approvals, durability): out of scope here, and the web-search budget for this session ran out before a cross-check.
- Rust SDK maturity of durable execution engines: not researched here.

## Sources

Official LangChain documentation (read 2026-11-21)

- https://docs.langchain.com/oss/python/langgraph/overview.md
- https://docs.langchain.com/oss/python/langchain/overview.md
- https://docs.langchain.com/oss/python/langchain/philosophy.md
- https://docs.langchain.com/oss/python/concepts/products.md
- https://docs.langchain.com/oss/python/langgraph/persistence.md
- https://docs.langchain.com/oss/python/langgraph/checkpointers.md
- https://docs.langchain.com/oss/python/langgraph/interrupts.md
- https://docs.langchain.com/oss/python/langgraph/use-time-travel.md
- https://docs.langchain.com/oss/python/langchain/human-in-the-loop.md
- https://docs.langchain.com/oss/python/migrate/langchain-v1.md
- https://docs.langchain.com/oss/python/releases/changelog.md
- https://docs.langchain.com/oss/python/deepagents/overview.md
- https://docs.langchain.com/oss/python/langgraph/case-studies
- https://docs.langchain.com/langsmith/deploy-overview.md
- https://docs.langchain.com/langsmith/changelog
- https://docs.langchain.com/_llms/agent-development-lifecycle/build/python.txt
- https://www.langchain.com/pricing

LangChain blog (vendor)

- https://www.langchain.com/blog/langgraph (2024-01-17)
- https://www.langchain.com/blog/langgraph-cloud (2024-06-27)
- https://www.langchain.com/blog/is-langgraph-used-in-production (2025-02-04)
- https://www.langchain.com/blog/customers-klarna (2025-02-12)
- https://www.langchain.com/blog/how-to-think-about-agent-frameworks (2025-04-20)
- https://www.langchain.com/blog/three-years-langchain (2025-10-20)
- https://www.langchain.com/blog/langchain-langgraph-1dot0 (2025-10-22)
- https://www.langchain.com/blog/agent-frameworks-runtimes-and-harnesses-oh-my (2025-10-25)
- https://www.langchain.com/blog/on-agent-frameworks-and-agent-observability (2026-02-12)
- https://www.langchain.com/blog/open-swe-an-open-source-framework-for-internal-coding-agents (2026-03-17)
- https://www.langchain.com/blog/interrupt-2026-overview (2026-05-14)
- https://www.langchain.com/resources/langgraph-vs-temporal (2026-06-06)
- https://www.langchain.com/state-of-agent-engineering (2026-06-12)
- https://www.langchain.com/blog/deep-agents-v0-7 (2026-07-29)
- https://www.langchain.com/blog/deep-agents-vs-langchain-vs-langgraph (2026-08-06)
- https://www.langchain.com/blog/october-2026-langchain-newsletter (2026-10-15)
- https://www.langchain.com/blog/series-c (2026-11-13)

Repositories and registries (measured 2026-11-21)

- https://github.com/langchain-ai/langchain
- https://github.com/langchain-ai/langgraph
- https://github.com/langchain-ai/langgraph/releases
- https://github.com/langchain-ai/deepagents
- https://github.com/langchain-ai/open-swe
- https://github.com/langchain-ai/langchainjs
- https://github.com/langchain-ai/langgraphjs
- https://github.com/langchain-ai/langserve
- https://github.com/langchain-ai/langsmith-sdk
- https://github.com/langchain-ai/langchain-mcp-adapters
- https://github.com/humanlayer/12-factor-agents
- https://github.com/0xPlaygrounds/rig
- https://github.com/Abraxas-365/langchain-rust
- https://github.com/a-agmon/rs-graph-llm
- https://github.com/Onelevenvy/langgraph-rust
- https://pypi.org/project/langchain/ , https://pypi.org/project/langgraph/ , https://pypi.org/project/deepagents/ , https://pypi.org/project/langsmith/ , https://pypi.org/project/langchain-classic/
- https://pypistats.org/api/packages/langgraph/recent (and the same path for the other packages)
- https://www.npmjs.com/package/@langchain/langgraph , https://api.npmjs.org/downloads/point/last-month/@langchain/langgraph
- https://crates.io/crates/rig-core , https://crates.io/crates/langchain-rust , https://crates.io/crates/graph-flow

Users speaking for themselves

- https://about.gitlab.com/blog/how-gitlab-reduced-code-per-agentic-flow-ratio/ (2026-09-22)
- https://handbook.gitlab.com/handbook/engineering/architecture/design-documents/duo_workflow/
- https://www.zenml.io/llmops-database/building-ai-developer-tools-using-langgraph-for-large-scale-software-development (summary of Uber's 2025 talk, https://youtu.be/Bugs0dVcNI8)
- https://www.linkedin.com/blog/engineering/ai/practical-text-to-sql-for-data-analytics
- https://www.qodo.ai/blog/why-we-chose-langgraph-to-build-our-coding-agent/

Criticism and debate

- https://minimaxir.com/2023/07/langchain-problem/ (2023-07)
- https://hamel.dev/blog/posts/prompt/ (2024-02-14)
- https://www.octomind.dev/blog/why-we-no-longer-use-langchain-for-building-our-ai-agents (2024-06; unreachable on 2026-11-21)
- https://news.ycombinator.com/item?id=40739982 (2024-06-20)
- https://devblogs.microsoft.com/frontier-engineering/earning-agentic-complexity/ (2024-09-09)
- https://www.anthropic.com/engineering/building-effective-agents (2024-12-19)
- https://www.latent.space/p/oai-v-langgraph (2025-04-20)
- https://dev.to/tufailkhan457/why-we-replaced-langchain-with-the-raw-anthropic-sdk-in-production-3611 (2026-04)
- https://temporal.io/blog/temporal-langgraph-plugin-durable-execution (2026-07-16)
- https://wavect.io/blog/langchain-deep-agents-review/ (2026-08-23)
- https://www.developersdigest.tech/blog/langchain-langgraph-whats-new-2026 (2026-10-17, updated 2026-11-17)

Surveys

- https://survey.stackoverflow.co/2025/ai
- https://stackoverflow.blog/2026/05/27/agents-on-a-leash-agentic-ai-remains-mostly-monitored-at-work/

Security

- http://research.checkpoint.com/2026/from-sqli-to-rce-exploiting-langgraphs-checkpointer/ (2026-06-11)
- https://labs.cloudsecurityalliance.org/research/csa-research-note-langchain-langgraph-vulnerabilities-202603/
- https://advisories.gitlab.com/pypi/langgraph-checkpoint/CVE-2025-64439/

Other

- https://en.wikipedia.org/wiki/LangChain
