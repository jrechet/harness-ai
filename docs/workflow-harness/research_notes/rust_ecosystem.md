# The Rust ecosystem for agent workflows, November 2026

Research note. Data collected on 2026-11-21.

## Summary in five lines

1. There is no official LangChain or LangGraph for Rust. The `langchain-ai` GitHub organisation holds one Rust repository, an unrelated example with zero stars. The Rust "LangChain" crates are community ports, the main one with a single owner.
2. There is no official Anthropic or OpenAI client SDK for Rust, and the Claude Agent SDK and the OpenAI Agents SDK exist only in Python and TypeScript. The official Rust pieces are elsewhere: the MCP SDK (`rmcp`, Tier 1), the GitHub Copilot SDK, the AWS and Google Cloud SDKs.
3. The largest coding agents are nonetheless written in Rust: OpenAI Codex CLI, Block's goose, and, since September 2026, the GitHub Copilot runtime (832,378 lines of Rust). None of them uses a Rust agent framework; they build on Tokio, `rmcp`, OpenTelemetry and their own loop.
4. Durable execution became first-class in Rust in 2026: Temporal's Rust SDK went 1.0 in September, AWS Lambda's durable SDK went 1.0 on 19 November. Restate is usable (0.13). DBOS is officially pre-production. Inngest is alpha.
5. Verdict: Rust is a reasonable choice for the deterministic part of a harness (orchestrator, state machine, tools, MCP servers, CLI). It is a poor choice if you want a ready-made agent framework, a vendor agent loop as a library, or an evaluation toolkit: those are thin or missing.

## How to read this note

Every fact carries a tag:

- **[measured]**: I read it myself on 2026-11-21 from the GitHub API, the crates.io API, or the file in the repository.
- **[vendor]**: stated by the organisation that ships the product (docs, blog, README). True as a statement, not independently checked.
- **[secondary]**: reported by a third party (press, blog, survey).

Terms used:

- **Crate**: a Rust package. **crates.io** is the public registry. "Recent downloads" means the last 90 days on crates.io. Download counts include automated builds, so they show use by other software more than use by people.
- **Agent loop**: the code that calls a model, runs the tools the model asked for, feeds results back, and repeats until done.
- **MCP** (Model Context Protocol): the open protocol by which an agent discovers and calls external tools.
- **Durable execution**: a runtime that records each step of a long workflow so that a crash or a restart resumes at the last finished step instead of starting over.
- **Tracing**: recording each model call and tool call as a timed span, to see what an agent did and what it cost.
- **Evals**: automated tests that grade the output of an agent on a fixed set of cases.
- **GA** (general availability): the vendor supports it for production. **Pre-1.0**: the API can break between releases.

Limit of this research: the web-search budget of the session ran out partway. Every number below was read directly from an API or a primary page; the gaps are listed in the section "Not found".

---

## 1. LangChain and LangGraph in Rust

### 1.1 Official: none

- The `langchain-ai` organisation has exactly one repository whose main language is Rust: `langchain-ai/datafusion-example`, 0 stars, last push June 2025. A search for "rust" in repository names and descriptions of the organisation returns nothing. [measured, `gh api search/repositories q=org:langchain-ai language:Rust`]
- The official LangChain and LangGraph packages are Python and JavaScript. `langchain-ai/langchain`: 150,004 stars, Python. `langchain-ai/langgraph`: 45,231 stars, Python. [measured]
- LangSmith, LangChain's tracing and evaluation product, has no Rust SDK either: the `langchain-ai/langsmith-sdk` repository contains `python/` and `js/` only. [measured]
- A public statement from LangChain Inc. about a Rust plan: not found.

### 1.2 Community ports

| Crate | Repository | Stars | Latest release | Downloads (total / 90 days) | State |
|---|---|---|---|---|---|
| `langchain-rust` | Abraxas-365/langchain-rust | 1,364 | 8.0.0, 2026-11-03 | 164,048 / 11,776 | Maintained, one crates.io owner, 39 contributors, 73 commits in the last six months |
| `langchain-ai-rust` | fanjia1024/langchain-rust (now Colin4k1024) | 7 | 5.0.1, 2026-01-28 | 372 / 155 | Repository archived. Despite the name, not from LangChain Inc. |
| `langgraph` | Onelevenvy/langgraph-rust | 11 | 0.2.5, 2026-07-01 | 1,501 / 354 | Its own description: "Not the official LangGraph Rust implementation" |

All [measured].

What to know about `langchain-rust`:

- It is a port of the classic LangChain building blocks: model wrappers (OpenAI, Azure, Ollama, Claude), embeddings, a dozen vector stores, chains, memory, a tool-calling agent, a ReAct agent, tracing spans. [vendor, README]
- It has no graph or state-machine module: the word "graph" does not appear in its README. So it ports LangChain, not LangGraph. [measured]
- Its version numbers are unstable: v5.0.0, v5.1.0, v5.2.0, v6.0.0 and v7.0.0 were published within about a day on 21-22 October 2026, then v8.0.0 on 3 November. Four major versions in two weeks means the API is still moving. [measured, GitHub releases]
- 11,776 downloads in 90 days is small. For scale, `rig-core` had 2,300,767 in the same period. [measured]

The crate named `langchain-ai-rust` deserves a warning. Its name suggests an official origin. Its owner on crates.io is an individual, the repository is archived, and its docs build failed for the last version. [measured, docs.rs and GitHub]

### 1.3 LangGraph-like libraries written for Rust

These do not port LangGraph. They rebuild the same idea, a graph of steps sharing a state, with pause and resume.

| Crate | What it is | Stars | Latest | Downloads (total / 90 days) |
|---|---|---|---|---|
| `graph-flow` (repo `a-agmon/rs-graph-llm`) | "LangGraph-inspired" graph engine: tasks, conditional routing, session storage in Postgres, human-in-the-loop pause. Uses Rig for model calls. | 390 | 0.8.1, 2026-10-21 | 23,819 / 14,366 |
| `swiftide` tasks | "Typed task graphs": each node has an input type, an output type, an error type; pause and resume for human approval. | 805 | 0.34.0, 2026-11-06 | 86,441 / 2,728 |
| `adk-graph` (part of `adk-rust`) | Graph orchestration inside a community agent kit. | 765 (whole repo) | 2.3.0, 2026-10-09 | 25,902 / 19,589 |

All [measured] for numbers, [vendor] for descriptions. `graph-flow` has 6 contributors and no GitHub release; it is a small project.

**Answer to the owner's question.** LangChain and LangGraph do not exist in Rust in any official form. The community port of LangChain is alive but small and unstable; nothing ports LangGraph seriously. If the graph model is what you want, the Rust options are small libraries, or a hand-written state machine (see section 7).

---

## 2. Rust-native agent and LLM libraries

Numbers are [measured] on 2026-11-21. "Who uses it" is [vendor] unless stated.

| Library | What it does | Stars | Latest release | Downloads (total / 90 days) | Contributors |
|---|---|---|---|---|---|
| **rig** (0xPlaygrounds) | Model clients for 20+ providers, agents with tools, streaming, vector stores, MCP tools; since 2026 also ships a terminal coding agent | 9,212 | 0.47.0, 2026-11-20 | `rig-core` 4,628,452 / 2,300,767 | 231 |
| **async-openai** (64bit) | Client for the OpenAI API | 2,037 | 0.43.0, 2026-11-01 | 11,188,385 / 3,720,012 | 112 |
| **genai** (jeremychone) | One client for many providers, each through its native protocol | 948 | 0.7.5, 2026-11-14 | 645,004 / 322,583 | 81 |
| **swiftide** (bosun-ai) | Agent harness, typed task graphs, indexing and retrieval pipelines | 805 | 0.34.0, 2026-11-06 | 86,441 / 2,728 | 28 |
| **AutoAgents** (liquidos-ai) | Multi-agent framework, tools in a WASM sandbox, guardrails, Python bindings | 791 | 0.4.0, 2026-07-08 | 25,085 / 11,250 | 27 |
| **adk-rust** (zavora-ai) | Community "Agent Development Kit" in 43 crates. Not Google's. | 765 | 2.3.0, 2026-10-09 | 46,367 / 20,784 | 24 |
| **graph-flow** | See 1.3 | 390 | 0.8.1, 2026-10-21 | 23,819 / 14,366 | 6 |
| **kalosm** (floneum) | Runs local models (text, audio, image) in-process | 2,236 | 0.4.0, 2025-02-09 | 26,143 / 2,229 | 19 |
| **llm-chain** (sobelio) | Early chain library | 1,601 | 0.13.0, 2023-11-15 | 103,135 / 8,305 | 41 |
| **llm** (graniet) | Unified client and CLI for several backends | 368 | 1.3.8, 2026-04-19 | 136,017 / 20,898 | - |

### 2.1 rig

- The reference Rust library for LLM applications by adoption: about 2.3 million downloads in 90 days and 231 contributors. [measured]
- It is pre-1.0 and says so: "Rig is pre-1.0, so releases break APIs." It reached version 0.47.0 on 20 November 2026, about 30 months after its first release; the cadence is fast. [vendor, README; measured]
- It follows the OpenTelemetry GenAI conventions for tracing and has a `rig-rmcp` crate for MCP tools. `rig-core` and `rig-agent` build for browser WASM. [vendor]
- In 2026 the project widened: `cargo install rig` now installs a terminal coding agent whose tools and commands are plugins. The agent runtime moved to a separate crate, `rig-agent`, created 2026-07-19. [measured, crates.io; vendor, README]
- Rig has no built-in orchestrator for several agents; patterns are composed by hand. [secondary, Zylos survey, 2026-04-01]
- Named users, as listed by the project: St. Jude (chatbot in the proteinpaint genomics tool), Coral Protocol, Dria, Nethermind (NINE), Neon (app.build agent), ilert (agentic LLM proxy), Archestra, Cairnify, Syncable, Refresh Agent, nitpik. [vendor, `0xPlaygrounds/awesome-rig`] None of these is a large technology company; several are from the crypto world, where Rig started.
- Microsoft's Agent Governance Toolkit ships a Rust integration for Rig tools. [vendor, awesome-rig list]

### 2.2 swiftide

- Built by bosun.ai for its own product; started as an indexing pipeline, now "composable LLM agents and harness, typed task graphs, and streaming RAG pipelines". [vendor]
- Useful ideas for a harness: typed graph nodes, pause and resume for human approval, a Docker executor for running tools in isolation, Langfuse support. [vendor]
- Pre-1.0: "APIs can change while the agent harness and task graph APIs settle". [vendor]
- Small: 2,728 downloads in 90 days. [measured] Its demo coding agent `bosun-ai/kwaak` (338 stars) had its last push in January 2026. [measured]

### 2.3 async-openai and genai: the client layer

- `async-openai` is the de facto OpenAI client for Rust. OpenAI's own libraries page lists it under community libraries. [vendor, developers.openai.com]
- `genai` talks to Anthropic, OpenAI, Gemini, Bedrock, Ollama and others through each provider's native protocol and lets you pick the provider by model name. It is a client, not an agent framework. [vendor]
- Both are single-maintainer-led projects with many contributors (112 and 81). [measured]

### 2.4 The rest

- **AutoAgents** calls itself "production-grade". Evidence for production use by named companies: not found. Its last crates.io release is from July 2026. [measured]
- **adk-rust** borrows the name of Google's Agent Development Kit. Google's official kits are `google/adk-python` (22,296 stars), `adk-go` (8,992), `adk-java` (1,778) and `adk-js` (1,488); `google/adk-rust` does not exist. [measured] The project advertises a 3.0 with durable runs, approvals, budgets and an audit log, still unpublished. [vendor]
- **kalosm** is for local models. Its last crates.io release is from February 2025, though the repository is active. [measured]
- **llm-chain** is abandoned: last crate release November 2023, last commit October 2024. [measured] Do not start on it.
- **Local inference** is a strong Rust area but outside this study: `huggingface/candle` (21,371 stars), `tracel-ai/burn` (16,320), `EricLBuehler/mistral.rs` (7,853). [measured]
- **BAML** (`BoundaryML/baml`, 9,530 stars) is a language for typed prompts whose compiler and runtime are written in Rust; it generates clients for other languages. [measured for numbers]

### 2.5 A wider sign: new agent runtimes are written in Rust

A survey by OSS Insight (3 April 2026) found that seven notable agent repositories launched in the first quarter of 2026 were all in Rust, among them `zeroclaw-labs/zeroclaw` (33,556 stars today), `RightNow-AI/openfang` (18,273) and `vercel-labs/agent-browser`. [secondary; star counts measured today] The survey itself says its sample is seven repositories without a stated selection rule, and that Python still holds training and most agent frameworks. Read it as: Rust is winning the runtime and command-line layer, not the framework layer.

Stars are a weak signal here. `openfang` had its last push in July 2026. [measured]

---

## 3. Official SDKs in Rust

### 3.1 Model providers

| Provider | Official Rust client? | Evidence |
|---|---|---|
| **Anthropic** | **No.** Official client SDKs: Python, TypeScript, C#, Go, Java, PHP, Ruby, plus the `ant` CLI. | [vendor] platform.claude.com SDK overview, read 2026-11-21 |
| **OpenAI** | **No.** Official: TypeScript, Python, .NET, Java, Go, Ruby. Rust appears only under community libraries (`async-openai`). | [vendor] developers.openai.com libraries page |
| **AWS Bedrock** | **Yes.** `aws-sdk-bedrockruntime` 1.157.0, updated 2026-11-20, 7.1 million downloads. Gives an official Rust path to Claude and other models hosted on Bedrock. | [measured] |
| **Google Cloud (Vertex AI)** | **Yes.** `google-cloud-aiplatform-v1` 1.19.0, updated 2026-11-11, from `googleapis/google-cloud-rust`. | [measured] |

Details on Anthropic:

- The `anthropics` organisation has three Rust repositories: a C compiler written by Claude, `buffa` (a protobuf library, 946 stars, active), and a Nix plugin. No SDK. [measured] Anthropic writes Rust internally but does not ship a Rust client.
- An open request, issue #1559 on `anthropic-sdk-python` (17 May 2026), asks for an official Rust SDK. It quotes Anthropic's 2024 answer to an earlier request: no Rust SDK yet, other languages first. Those languages have since shipped. The issue has no staff reply. [measured on the issue page]
- Community Anthropic crates are small and single-maintainer: `anthropic-ai-sdk` (0.2.27, January 2026, 18 stars), `misanthropic` (1.0.0-alpha.26, November 2026, 8 stars), `async-anthropic` (0.6.0, May 2025), `clust` (last release June 2024), `anthropic` (0.0.8, September 2024). [measured]
- In practice a Rust program reaches Claude through `rig` or `genai` (which implement the Messages API themselves), through Bedrock or Vertex with the official cloud SDKs, or with a hand-written HTTP client. The cost: new API features (prompt caching options, new tool types, beta headers) reach Rust later than Python and TypeScript, and you depend on a volunteer for it.

### 3.2 Agent SDKs (the agent loop as a library)

| SDK | Languages | Rust? |
|---|---|---|
| **Claude Agent SDK** (Anthropic) | Python, TypeScript | No. The docs say: to drive the same loop from another language, run the CLI as a subprocess with `-p` and `--output-format json`. [vendor] |
| **OpenAI Agents SDK** | Python (30,800 stars), TypeScript (4,030 stars) | No. `openai/openai-agents-rust` does not exist. [measured] |
| **OpenAI Codex SDK** | TypeScript, Python (`sdk/typescript`, `sdk/python` in the repo) | No Rust SDK, although Codex itself is Rust. The crate `codex-core` is not on crates.io. [measured] |
| **GitHub Copilot SDK** | Python, TypeScript, Go, .NET, Java, **Rust** | **Yes, official.** Crate `github-copilot-sdk` 1.0.35 (2026-11-19), 275,167 downloads, owned by GitHub and Microsoft staff. [measured] |
| **Google ADK** | Python, Go, Java, TypeScript | No official Rust. [measured] |

Notes:

- The Claude Agent SDK is "a library that runs the Claude Code binary". [vendor] A Rust harness can do the same thing itself: start `claude -p` as a child process and parse its JSON output. This is the supported route for unsupported languages, and it keeps skills, hooks, permissions and MCP servers working.
- Community Rust wrappers do exactly that: `claude-agent-sdk-rs` (tyrchen, 0.6.4, February 2026, 78 stars), `anthropic-agent-sdk` (0.2.75, December 2025, 10 stars), `cc-sdk` (0.8.1, April 2026). All are one-person projects. [measured]
- **Warning.** The crate named `claude-agent-sdk` on crates.io (0.1.1, September 2025) declares `github.com/anthropics/claude-agent-sdk-rust` as its repository. That repository does not exist (HTTP 404), and the crate's owner is an individual. It is not an Anthropic product. [measured] Check owners before adding any crate with a vendor's name in it.
- The Copilot SDK is the one case where a large vendor ships its agent loop to Rust. It loads the Copilot runtime, itself written in Rust, into the application. It is tied to GitHub Copilot as the model service. [vendor, README]

### 3.3 Protocols

| Protocol | Rust SDK | State |
|---|---|---|
| **MCP** | `rmcp`, in `modelcontextprotocol/rust-sdk` | **Official, Tier 1** (the top tier, with TypeScript, Python, C#, Go, Ruby). 3.11.0 on 2026-11-17. 4,134 stars, 235 contributors, 53.1 million downloads, 31.4 million in 90 days. Implements the 2026-07-28 specification. [measured; vendor for the tier] |
| **ACP** (Agent Client Protocol, editor to agent) | `agent-client-protocol` | 5.5.1 on 2026-11-21, 6.5 million downloads. [measured] |
| **A2A** (agent to agent) | `a2aproject/a2a-rs` | Official repository, created April 2026, 116 stars. Young next to a2a-python (2,252 stars). [measured] |

`rmcp` is the strongest official building block in Rust. It went 1.0 on 2026-03-03, 2.0 on 2026-06-29 and 3.0 on 2026-07-28: three major versions in five months, so expect migration work. [measured, crates.io] Both Codex (pinned to 3.6.0) and goose (3.9.0) depend on it. [measured, their `Cargo.toml`]

### 3.4 OpenAI Codex CLI is written in Rust: what it shows

Facts:

- `openai/codex`: 136,051 stars, 746 contributors, latest release `rust-v0.171.0` on 2026-11-20. Rust is 89.5 MB of the 91.9 MB of source, about 97%. The `codex-rs` workspace has 131 directories. [measured]
- The move was announced on 30 May 2025 ("Codex CLI is Going Native"), with four reasons. In OpenAI's words: "Zero-dependency Install" (Node 22+ was required), "Native Security Bindings" (the Linux sandbox was already Rust), "Optimized Performance — no runtime garbage collection", and an "Extensible Protocol" so other languages can drive the agent. [vendor, discussion #1174]
- What Codex depends on: `tokio` (async runtime), `reqwest` (HTTP), `rmcp` (MCP), `landlock` and `seccompiler` (Linux sandbox), `opentelemetry` 0.31 with `tracing` (tracing), `sqlx` with SQLite (state), `ratatui` (terminal UI), `schemars` (JSON Schema). [measured, `codex-rs/Cargo.toml`]
- What it does not depend on: `async-openai`, `rig`, `genai`, any LangChain port, any durable-execution SDK. OpenAI wrote its own model client and agent loop. [measured]

What it shows:

1. Rust is a proven language for a production agent at very large scale. The doubt "can a serious agent be built in Rust" is settled.
2. The proof is for the **runtime**, not for frameworks. OpenAI used Rust's general ecosystem (async, HTTP, sandboxing, telemetry) and wrote the agent parts itself. The same holds for goose, whose dependencies show `rmcp`, `agent-client-protocol` and `opentelemetry` 0.33 but no agent framework. [measured]
3. The pattern is **Rust core, thin SDKs in other languages over a protocol**. Codex ships TypeScript and Python SDKs on top of its Rust binary. Copilot does the same in six languages. Temporal has done it since 2021: its TypeScript, Python, .NET and Ruby SDKs sit on a Rust core. [measured, repository layouts; vendor, Temporal README]
4. OS-level sandboxing is where Rust has a real edge, and it mattered to OpenAI's decision.
5. It does not show that Rust is the cheap route. OpenAI has 746 contributors on that repository.

---

## 4. Durable execution from Rust

Why it matters for a ticket-to-production workflow: such a run lasts hours or days, waits for a human approval, and must not redo a merged pull request after a restart. A durable execution engine gives this.

| Engine | Rust SDK | Version, date | Vendor's own status | Downloads (total / 90 days) | Verdict |
|---|---|---|---|---|---|
| **Temporal** | `temporalio-sdk`, official | 1.2.0, 2026-11-09 | **GA.** Works with Temporal Cloud and self-hosted. | 4,462,253 / 3,638,058 | Production-ready |
| **AWS Lambda durable functions** | `aws-durable-execution-sdk`, official | 1.0.0, 2026-11-19 | 1.0, not a pre-release | 12,046 / 12,046 | Production-ready on paper; two days old; AWS Lambda only |
| **Restate** | `restate-sdk`, official | 0.13.0, 2026-10-28 | No maturity statement found; pre-1.0 | 1,579,335 / 1,057,393 | Usable |
| **DBOS** | `dbos`, official | 0.6.0, 2026-11-10 | **"pre-production release, and isn't yet supported for production use"** | 35,999 / 35,971 | Not yet |
| **Inngest** | `inngest`, official | 0.1.1, 2024-11-01 | **"Alpha"**; axum only; no middleware | 112,650 / 27,517 | Not yet |
| **Golem** | `golem-rust` | 3.0.3, 2026-11-06 | Runtime of durable WASM components | 35,648 / 3,793 | Niche |
| **Obelisk** | runtime written in Rust | 0.42.0-rc.4, 2026-09-26 | Release candidates | - | Niche (768 stars) |
| **Resonate** | `resonate-sdk` | 0.6.0, 2026-07-22 | Young (repo created March 2026, 8 stars) | 2,562 / 1,251 | Not yet |
| **Hatchet** | community `hatchet-sdk` | 0.2.8, 2026-04-05 | Declares itself "unofficial" | 10,908 / 1,636 | Not official |

All numbers [measured]. Status quotes [vendor].

### 4.1 Temporal

- Public preview on 7 May 2026, 1.0.0 on crates.io on 4 September 2026, GA blog post on 23 September 2026. [measured for the crate date; vendor for the rest]
- Workflows and activities are plain async Rust functions with macros (`#[workflow]`, `#[activity]`), running on Tokio. Covered: durable timers, signals, queries, updates, retries, heartbeats, child workflows, continue-as-new, patching, interceptors, tracing, a replay tester. [vendor]
- Stated limits: workflow code must be deterministic (same decisions on replay), so all side effects go into activities. A detector for non-deterministic code is on by default but "cannot catch every change in polling order" and does not see calls like `SystemTime::now()`. Activities can run more than once, so they must be idempotent. [vendor]
- The Rust core is not new: it has run under Temporal's TypeScript, Python, .NET and Ruby SDKs for years. What is new in 2026 is the Rust-facing API. [vendor]
- The GA post names no customer. Named production users of the Rust SDK: not found.
- Cost to know: Temporal needs a server (Temporal Cloud, or self-hosted with a database). It is a real piece of infrastructure, not a library.
- Temporal's integrations with agent SDKs (for example the OpenAI Agents SDK) are for Python. An equivalent for Rust: not found.

### 4.2 Restate

- The Restate server is itself written in Rust (4,729 stars) and ships as a single binary. [measured; secondary for the single binary]
- The Rust SDK supports the three service types (services, virtual objects, workflows), journaled steps, state, timers, awakeables (wait for an outside event, such as a human approval), and typed clients. [vendor, docs.rs]
- It is at 0.13 after 19 releases since July 2024, with 11 contributors and 96 stars. The Python SDK has a 1.0 line; Rust does not. [measured; secondary for Python]
- Restate's documented agent integrations (Vercel AI SDK, OpenAI Agents SDK, Google ADK, Pydantic AI, LangChain) are Python and TypeScript products. Its AI examples repository is Python. [vendor; measured]

### 4.3 DBOS

- A library, not a server: it checkpoints each step into your Postgres database. Announced for Rust in September 2026 ("Growing demand from Rust developers inspired us"). [vendor]
- The README and the docs say in so many words that 0.6 is pre-production and its API may break. [vendor] Take them at their word.
- The repository has 50 stars and was created in August 2026. [measured]
- The model is attractive for a small team (no extra service, only Postgres). Worth re-checking in mid-2027.

### 4.4 Which to pick today

- Need durability now, in Rust, with vendor support: **Temporal**.
- Want a lighter server and accept pre-1.0: **Restate**.
- Already on AWS Lambda: the new AWS SDK, after it has aged a few months.
- A run that fits in one process and one day: none of them. A table in SQLite or Postgres with one row per step is enough. This is what Codex does with `sqlx` and SQLite for its own state. [measured for the dependency; the inference is mine]

---

## 5. What teams that chose Rust report

### 5.1 GitHub: the Copilot runtime (September 2026)

The strongest case study found. Source: Stephen Toub, "Migrating the GitHub Copilot runtime to Rust, using Copilot", GitHub Blog, 16 September 2026. All [vendor].

- What moved: the agent runtime behind the Copilot CLI, the Copilot app and the Copilot SDK, from TypeScript on Node.js to Rust.
- Size: about 430,000 lines of TypeScript ported; result 832,378 lines of production Rust and 468,689 lines of Rust unit tests; done in about 14.5 weeks through 128 pull requests, mostly written by agents with humans directing and reviewing.
- Why Rust: a runtime that can be loaded inside another program through a C interface, low start-up and steady overhead, predictable resource use. Before, each SDK client started a Node process, "on the order of 100 MB of working set minimum", and "a crash in Node took the session with it".
- The author also names soft reasons, team experience and industry direction, and adds: "The right target language legitimately varies from application to application."
- Results: performance "improved by orders of magnitude"; the post gives no latency or memory figure. About 60 npm dependencies removed. 158 `unsafe` blocks, all at outside boundaries.
- Costs reported: dozens of correctness and performance regressions, all fixed. Causes included type ambiguities (an integer serialised as `42.0`), behaviour that Node provided silently, and lifetime and shared-state bugs, which Rust forces you to handle explicitly. One 30,000-line file was the hardest. Fifteen parallel agent sessions overloaded a laptop with builds.

### 5.2 OpenAI: Codex CLI (May 2025)

See 3.4. Reasons given: install without Node, native sandbox, no garbage collector, a protocol for other languages. [vendor] No measured before-and-after numbers were published in that announcement.

### 5.3 Temporal: the core SDK (2021, still the base in 2026)

Reasons given in April 2021: safe concurrency, performance, a better alternative to C for one core shared by several language SDKs, direct linking instead of a separate process, WASM as a future target. [vendor] Five years later that core is still the base of four SDKs and now of the Rust SDK. This is the longest-running evidence that the "Rust core, thin SDKs" pattern holds.

### 5.4 Block: goose

- `aaif-goose/goose` (formerly `block/goose`): 56,851 stars, 700 contributors, release 1.60.2 on 2026-11-20. About 11.1 MB of Rust for the core and 3.5 MB of TypeScript for the desktop app. [measured]
- Block gave goose to the Agentic AI Foundation in November 2025. [secondary]
- A post by Block explaining why it chose Rust: not found. A maintainer talk names performance and stability of the core loop as a priority, without tying it to the language. [secondary]

### 5.5 A small team: Refresh Agent

A marketing-analytics agent rewritten from Python (Django, Pydantic AI) to Rust (Axum, SQLite, Rig). Author: Duncan Trevithick, who says he is not a developer. All [vendor], self-measured.

- Benefits: one 34 MB binary plus a SQLite file; about 45 MB of memory, flat over days; start in about 12 ms; the compiler caught several token-handling bugs that "would likely have been silent runtime failures in Python".
- Costs: in 2024, "I spent more time debugging AI-generated Rust than I would have spent writing Python by hand." Waiting for compiles slows prompt tuning (full rebuild 2 min 17 s, incremental 2 to 5 s). Fewer ready-made integrations than LangChain or LlamaIndex, "so he built more from scratch". The async learning curve was hard.
- His summary: "Python is easier to write. Rust is better to run." And, with 2026 coding agents, he "would go straight to Rust from day one".

### 5.6 Framework authors and surveys

- A Zylos survey (1 April 2026) lists what the Rust agent ecosystem lacks: no shared standard for messages between agents, no first-class deterministic replay or testing of async agent systems in any framework, uneven tracing with no standard for parent-child spans, and the fact that CPU-heavy work stalls the Tokio scheduler unless moved aside. [secondary]
- The same survey repeats benchmark figures (five times less memory than Python frameworks, cold start in 180 ms against several seconds). Its sources are the frameworks' own benchmarks. Treat these as [vendor] claims, not measurements.
- A caution on ecosystem risk: TensorZero, a Rust LLM gateway with built-in observability and evals (11,700 stars), was archived on 12 June 2026 when its company wound down. [measured for the archive; secondary for the reason] A tool being written in Rust and popular does not make it durable.

### 5.7 The pattern in these reports

Benefits that recur, in order of how well they are supported:

1. **Single binary, no runtime to install.** Named by OpenAI, GitHub and the small team. Well supported.
2. **Low and flat memory, fast start, no garbage-collector pauses.** Named by all; numbers only from small teams and framework authors.
3. **Embedding.** A Rust core can be loaded into programs in other languages. Named by GitHub and Temporal.
4. **Sandboxing and safety.** Named by OpenAI. Matters when the agent runs shell commands.
5. **Compile-time checks.** "If it compiles it is mostly correct" suits code written by agents. Named by the small team; OpenAI's president is quoted there saying the same. Plausible, weakly evidenced.

Costs that recur:

1. **You write more yourself.** No vendor SDK, no agent framework at the level of LangGraph. Every large team wrote its own loop.
2. **Slower iteration on prompts**, because of compile time. Mitigation used in practice: keep prompts and skills in text files loaded at run time, not in Rust code.
3. **Lifetimes and shared state** cause bugs during ports, and async Rust has a learning curve.
4. **API churn** in the libraries: `rig` 0.x, `rmcp` three majors in five months, `langchain-rust` four majors in two weeks.
5. **Speed of model calls does not change.** An agent spends its time waiting for the model. Rust improves cost of hosting, start-up and reliability, not the duration of a ticket.

---

## 6. Verdict table

Scale:

- **First-class**: official or de facto standard, 1.0 or later, actively released, used by large products.
- **Usable**: works and is maintained, but community-run or pre-1.0 or thin; expect to read source code and absorb breaking changes.
- **Missing**: nothing credible; build it or use another language.

| Building block | Rust in November 2026 | Best option | Why this grade |
|---|---|---|---|
| Model client, OpenAI | Usable | `async-openai` 0.43 | Not official; 11.2 M downloads; listed by OpenAI as a community library |
| Model client, Anthropic direct | Usable, weak | `rig` or `genai` | No official SDK; dedicated crates are tiny; features arrive late |
| Model client, via Bedrock or Vertex | First-class | `aws-sdk-bedrockruntime`, `google-cloud-aiplatform-v1` | Official cloud SDKs at 1.x |
| Model client, many providers | Usable | `rig-core` 0.47, `genai` 0.7 | Active, widely downloaded, pre-1.0 |
| Tool calling | Usable | `rig` or `swiftide` tool macros, `schemars` for JSON Schema | Works; each library has its own tool trait |
| MCP (client and server) | **First-class** | `rmcp` 3.11 | Official Tier 1; used by Codex and goose; fast major-version churn |
| Vendor agent loop as a library | Missing, one exception | `github-copilot-sdk` 1.0; otherwise run `claude -p` or `codex` as a subprocess | Claude Agent SDK and OpenAI Agents SDK are Python and TypeScript only |
| Graph or state machine for agents | Usable, thin | `graph-flow` 0.8, `swiftide` tasks, or plain Rust enums | No LangGraph; small projects; the language itself fits state machines |
| Durable execution | **First-class** | `temporalio-sdk` 1.2 (GA) | Also AWS 1.0 (new), Restate 0.13 (usable); DBOS and Inngest not ready |
| Tracing | Usable | `tracing` + `opentelemetry` 0.33 + OTLP export | Used by Codex and goose; OpenTelemetry Rust marks traces as Beta; no LangSmith SDK |
| Evals | **Missing** | Run evals from outside the binary | `mira-eval` (8 stars), `adk-eval`: too young; mainstream tools are Python or TypeScript |
| Sandboxing of tools | First-class | `landlock`, `seccompiler`, WASM runtimes | Shipped in Codex |
| Agent-to-editor and agent-to-agent protocols | Usable | `agent-client-protocol` 5.5, `a2a-rs` | ACP widely downloaded; A2A Rust is young |
| Local model inference | First-class | `candle`, `mistral.rs`, `burn` | Outside this study |
| LangChain, LangGraph | **Missing** | none official | Section 1 |

Notes on two grades:

- **Tracing.** The OpenTelemetry Rust project lists logs and metrics as Stable and the traces API, SDK and OTLP exporter as Beta. [measured, project README] The version is 0.33.1; there is no 1.0. The conventions for naming model-call attributes ("GenAI semantic conventions") are still marked "Development" for every language. [secondary] In practice Rust tracing is what Codex and goose ship with, so "usable" is conservative. What is missing is the LLM-specific layer: LangSmith has no Rust SDK; Langfuse is reached through OTLP or through small community crates (`langfuse-ergonomic` 0.17, 19,042 downloads). [measured]
- **Evals.** I found no Rust equivalent of the Python and TypeScript eval toolkits with real adoption. This matters less than it seems: an eval harness sends inputs to the agent and grades outputs, so it can sit outside the binary and be written in any language. The inference is mine.

---

## 7. Is Rust a reasonable choice? A reading for a team harness

Reasonable, with a precise scope.

**Where Rust fits well**

- The **orchestrator** of a ticket workflow: a state machine with explicit states (ticket checked, plan approved, code written, review passed, shipped) and typed transitions. A Rust `enum` with `match` makes a missing case a compile error. No framework is needed for this.
- **Guarantees**: gates, budgets, permission checks, the audit trail. Things that must hold every time belong in compiled, tested code.
- **MCP servers and command-line tools** handed to agents: `rmcp` is official and the result is one binary to distribute to every team.
- **Long runs**: Temporal's Rust SDK is GA.

**Where Rust costs more than it gives**

- The **agent loop itself**, if you want Claude Code's behaviour (skills, hooks, subagents, permissions). The official SDK is Python and TypeScript. From Rust, start the CLI as a child process. Rewriting the loop in Rust means giving those features up or rebuilding them.
- **Anything LangChain or LangGraph**: integrations, checkpointers, LangSmith. They do not exist in Rust.
- **Prompt and skill iteration**: keep those as files outside the binary.
- **Evals**: use outside tooling.

**The shape the large players converged on**

A Rust core that owns state, tools, sandbox and protocol; agents and SDKs in other languages talk to it over JSON-RPC or MCP. Codex, the Copilot runtime, goose and Temporal all have this shape. For a team harness the same split gives: a Rust binary for the deterministic workflow, and the vendor's agent (Claude Code or Codex, as a subprocess) for the judgement steps.

**Risks to accept knowingly**

1. No vendor will fix your model client. Anthropic's API features reach Rust through volunteers.
2. Pre-1.0 churn. Pin versions, and budget time for upgrades of `rig` and `rmcp`.
3. A smaller hiring pool and a slower start for people new to async Rust. Coding agents reduce this cost in 2026 but do not remove review effort: GitHub reported dozens of regressions in an agent-written port.
4. Community projects in this space appear and stall quickly (llm-chain abandoned, kwaak quiet, TensorZero archived). Prefer libraries backed by a product that depends on them.

---

## 8. Not found

Stated plainly rather than filled in:

- An official statement from LangChain Inc. about Rust support, for or against.
- Any Anthropic statement on a Rust client SDK later than the 2024 answer quoted in issue #1559.
- Named production users of the Temporal Rust SDK, of the Restate Rust SDK, of swiftide outside bosun.ai, or of AutoAgents.
- An explicit maturity statement (preview, beta, GA) for the Restate Rust SDK.
- A post by Block explaining the choice of Rust for goose.
- First-hand engineering reports from Zed, Warp or the Kiro and Amazon Q command-line teams on building agents in Rust. Warp (66,077 stars) and Zed (95,474 stars) are Rust code bases with agents [measured]; `aws/amazon-q-developer-cli` is Rust with its last push in August 2026 [measured]. Their reasons were not researched: the search budget ran out.
- Measured before-and-after latency or memory figures from OpenAI or GitHub. Both describe gains in words only.
- An independent benchmark of Rust agent frameworks against Python ones. All figures found come from the frameworks themselves.
- Whether a Temporal or Restate integration with an agent SDK exists for Rust.

---

## Sources

Primary, vendor pages:

- Anthropic, SDKs, CLI, and libraries: https://platform.claude.com/docs/en/cli-sdks-libraries/overview
- Anthropic, Claude Agent SDK overview: https://code.claude.com/docs/en/agent-sdk/overview
- Request for an official Anthropic Rust SDK (2026-05-17): https://github.com/anthropics/anthropic-sdk-python/issues/1559
- OpenAI, libraries: https://developers.openai.com/api/docs/libraries
- OpenAI, "Codex CLI is Going Native" (2025-05-30): https://github.com/openai/codex/discussions/1174
- OpenAI Codex repository and `codex-rs/Cargo.toml`: https://github.com/openai/codex
- GitHub Blog, "Migrating the GitHub Copilot runtime to Rust, using Copilot" (2026-09-16): https://github.blog/ai-and-ml/generative-ai/migrating-the-github-copilot-runtime-to-rust-using-copilot/
- GitHub Copilot SDK: https://github.com/github/copilot-sdk
- MCP, SDK list and tiers: https://modelcontextprotocol.io/docs/sdk
- MCP Rust SDK: https://github.com/modelcontextprotocol/rust-sdk
- Temporal, Rust SDK generally available (2026-09-23): https://temporal.io/blog/build-durable-applications-rust-temporal-rust-sdk-now-generally-available
- Temporal, "Why Rust powers Temporal's new Core SDK" (2021-04-20): https://temporal.io/blog/why-rust-powers-core-sdk
- Temporal Rust SDK repository: https://github.com/temporalio/sdk-rust
- Restate Rust SDK: https://github.com/restatedev/sdk-rust and https://docs.rs/restate-sdk/latest/restate_sdk/
- Restate documentation index: https://docs.restate.dev/llms.txt
- DBOS Transact for Rust: https://github.com/dbos-inc/dbos-transact-rust and https://docs.dbos.dev/rust/programming-guide
- DBOS, "What's New in DBOS - September 2026": https://www.dbos.dev/blog/whats-new-in-dbos-september-2026
- Inngest Rust SDK: https://github.com/inngest/inngest-rs
- AWS Durable Execution SDK for Rust: https://github.com/aws/aws-durable-execution-sdk-rust
- OpenTelemetry Rust, project status table: https://github.com/open-telemetry/opentelemetry-rust
- goose: https://github.com/aaif-goose/goose
- A2A Rust SDK: https://github.com/a2aproject/a2a-rs
- ACP Rust SDK: https://github.com/agentclientprotocol/rust-sdk

Libraries:

- rig: https://github.com/0xPlaygrounds/rig
- Rig users list: https://github.com/0xPlaygrounds/awesome-rig
- swiftide: https://github.com/bosun-ai/swiftide
- langchain-rust: https://github.com/Abraxas-365/langchain-rust
- langchain-ai-rust (not official): https://docs.rs/crate/langchain-ai-rust/latest
- langgraph-rust (not official): https://github.com/Onelevenvy/langgraph-rust
- graph-flow: https://github.com/a-agmon/rs-graph-llm
- AutoAgents: https://github.com/liquidos-ai/AutoAgents
- adk-rust (community): https://github.com/zavora-ai/adk-rust
- genai: https://github.com/jeremychone/rust-genai
- async-openai: https://github.com/64bit/async-openai
- llm-chain: https://github.com/sobelio/llm-chain
- kalosm: https://github.com/floneum/floneum
- claude-agent-sdk-rs (community): https://github.com/tyrchen/claude-agent-sdk-rs
- TensorZero (archived): https://github.com/tensorzero/tensorzero

Registries and APIs used for measurements (2026-11-21):

- crates.io API, per crate: https://crates.io/api/v1/crates/{name} (for example https://crates.io/crates/rmcp, https://crates.io/crates/temporalio-sdk, https://crates.io/crates/rig-core, https://crates.io/crates/claude-agent-sdk)
- GitHub REST API, per repository: https://api.github.com/repos/{owner}/{name}
- GitHub search for an organisation's Rust repositories: https://api.github.com/search/repositories?q=org:langchain-ai+language:Rust

Secondary:

- OSS Insight, "The Rust Shift" (2026-04-03): https://ossinsight.io/blog/rust-ai-agent-infrastructure-2026
- Zylos Research, Rust-native agent frameworks (2026-04-01): https://zylos.ai/research/2026-04-01-rust-native-ai-agent-frameworks-ecosystem-2026/
- Refresh Agent, "Why I Built My AI Agent in Rust (And What I'd Do Differently)": https://refreshagent.com/engineering/building-ai-agents-in-rust
- Dipankar Sarkar, "Rust for AI Agent Infrastructure" (2026-06-29): https://www.dipankar.name/writings/rust-for-ai-agent-infrastructure-field-guide/
- Techzine, "OpenAI rewrites AI coding tool in Rust": https://www.techzine.eu/news/devops/131954/openai-rewrites-ai-coding-tool-in-rust/
- DevClass, on the Codex rewrite (2025-06-02): https://www.devclass.com/ai-ml/2025/06/02/nodejs-frustrating-and-inefficient-openai-rewrites-ai-coding-tool-in-rust/1619589
- Temporal changelog: https://temporal.io/changelog
- On the state of the OpenTelemetry GenAI conventions (July 2026): https://john-hodge.com/blog/opentelemetry-genai-semantic-conventions/
- On the TensorZero archive (2026-06-14): https://the-context.pages.dev/en/news/2026-06-14-tensorzero-archived/
