# Alternatives to LangGraph for orchestrating agent workflows (state on 2026-11-21)

## Summary

1. By late 2026 every large lab and cloud ships its own agent SDK, and all of them converged on the same shape: an agent loop, tools through MCP, a way to pause for a human, and a graph or script layer for multi-step work. LangGraph is one option among about ten, no longer the default.
2. The SDKs differ most on one point: what happens when the process dies. Most save a session or a checkpoint that you must reload yourself. Only a durable workflow engine (Temporal, Restate, DBOS, Inngest, Cloudflare Workflows, Lambda durable functions) resumes on its own.
3. The pattern that production teams describe is two layers: a deterministic workflow that owns the steps, the waits and the retries, and an agent that runs inside one step. Temporal says OpenAI's Codex web agent and Replit Agent run this way (vendor claim; no OpenAI source found).
4. CI is a real orchestrator for repository work. GitHub Agentic Workflows went GA on 2026-10-28 and GitLab Custom Flows on 2026-07-16. CI gives triggers, isolation, permissions and approval gates, but no state between runs and hard time limits.
5. The protocols have settled under one roof: MCP, AGENTS.md and Agent Skills are all in the Linux Foundation's Agentic AI Foundation; A2A is at 1.0. Consolidation is also visible in what died: AutoGen is archived, OpenAI's visual Agent Builder shuts down on 2026-11-30, Prefect's ControlFlow is archived.

## How to read this note

- Every claim carries a tag. **[measured]**: I read it myself today from a registry, an API or the primary document. **[vendor]**: stated by the company that sells or owns the thing. **[secondary]**: a third party, or a search summary of a page I did not open.
- Numbers in brackets like [14] point to the Sources list at the end.
- GitHub stars, release dates, npm and PyPI download counts were read on 2026-11-21 [61]. Download counts include CI and transitive installs; treat them as an order of magnitude, not as a user count.
- Section 8 is my own analysis, marked as such. The rest is reporting.

## 0. Vocabulary

- **Agent loop**: the cycle "call the model, run the tool it asked for, feed the result back, repeat until done".
- **Harness**: everything around the model that makes the loop usable: tools, permissions, context management, memory, limits.
- **Orchestration**: deciding which agent or function runs next. It is *agentic* when the model decides, *deterministic* when your code decides.
- **Handoff**: one agent passes the conversation to another agent, which takes over.
- **Human-in-the-loop (HITL)**: the run stops and waits for a person to approve or answer.
- **Checkpoint**: a saved copy of the run's state at a given step.
- **Durable execution**: a runtime records the result of every step. After a crash it re-runs the code, skips the steps already recorded, and continues. A wait of three weeks costs nothing and survives a redeploy.
- **Replay**: the mechanism behind durable execution. It forces the code between steps to be deterministic (no clock, no random, no direct network call outside a recorded step).

## 1. The baseline: LangGraph in one paragraph

LangGraph models a workflow as a graph of nodes that share a state object; a "checkpointer" saves the state after each node, which gives resume and human interrupts. It is at 1.2.24 (2026-11-20), 45,231 stars, 15.3 M PyPI downloads last week and 5.2 M weekly npm downloads [measured, 61]. It remains the most downloaded graph framework. Everything below is compared against that reference: a graph you write, a state you persist, in Python or TypeScript.

## 2. Agent SDKs from labs and cloud vendors

### 2.1 Claude Agent SDK (Anthropic)

- **What it gives.** The Claude Code agent as a library: "the same tools, agent loop, and context management that power Claude Code" [vendor, 1]. Built-in file, shell and web tools; hooks (your code runs at lifecycle points); subagents; MCP; permissions; sessions; skills, memory and plugins loaded from `.claude/` [measured, 1].
- **Languages.** Python and TypeScript. For any other language the docs say to run the CLI as a subprocess with `-p --output-format json` [measured, 1]. No Rust SDK.
- **Multi-step workflows.** There is no graph API. Multi-step work is done by the agent itself, by subagents, or by your own code calling `query()` several times. In Claude Code, "dynamic workflows" (2026-06-02) let Claude write a JavaScript script that calls `agent()`, `parallel()` and `pipeline()`: the script holds loops and routing, each agent call holds judgement [vendor, 5]. The post warns they "often use more tokens and are best suited for complex, high value tasks" [5]. Whether the SDK exposes this as an API: not found; the SDK overview only links to the post.
- **Handoffs.** None in the OpenAI sense. The model is delegation: a parent spawns a subagent with its own context and gets a result back [measured, 1].
- **Human approval.** A `canUseTool` callback fires when a tool needs permission or when Claude asks a question (`AskUserQuestion`). "The callback can stay pending indefinitely." For long waits, a `PreToolUse` hook can return `defer` so the process exits and resumes later from the saved session [measured, 3]. `AskUserQuestion` is not available inside subagents [3].
- **State.** Sessions are JSONL transcript files on local disk (`~/.claude/projects/...`). Resume by ID, continue the latest, or fork. They hold the conversation, not the file system. "Session files are local to the machine that created them"; a `SessionStore` adapter mirrors them to your storage for other hosts [measured, 2]. The docs themselves suggest a third way: do not rely on resume, pass results as application state into a fresh session [2].
- **Hosted variant.** Claude Managed Agents: Anthropic runs the loop and the sandbox; sessions are stateful and "resume cleanly after pauses"; cron-scheduled runs exist; status is **beta** (header `managed-agents-2026-04-01`) [measured, 4].
- **Maturity.** Python 0.2.187 (2026-11-20), TypeScript 0.3.330 (2026-11-20): still 0.x, released almost daily. 8,610 stars (Python repo). 10.0 M PyPI downloads last week, 20.7 M weekly npm downloads [measured, 61].
- **Lock-in.** Claude models only (direct, Bedrock, Google Cloud, Foundry). Commercial terms, not an open-source licence, govern the SDK [measured, 1].

### 2.2 OpenAI Agents SDK and AgentKit

- **What it gives.** Three primitives: agents, handoffs (or agents-as-tools), guardrails; plus sessions, tracing, MCP, realtime and voice agents [measured, 6]. Since 2026-04-15 it also ships a harness with file tools, AGENTS.md and skills support, and "sandbox agents" that run in an isolated workspace (providers: Cloudflare, Daytona, E2B, Modal, Vercel and others) [vendor, 8].
- **Languages.** Python (0.25.0, 2026-11-18) and TypeScript (`@openai/agents` 0.22.0). The April harness shipped "Python first" [8]. No Rust SDK.
- **Multi-step workflows.** Orchestration is code: you call `Runner.run` and chain results, or you let agents hand off. No graph engine in the SDK.
- **Handoffs.** First-class: an agent transfers control to another agent [6]. This is the SDK that popularised the term.
- **Human approval.** A tool marked `needs_approval` pauses the run; `result.interruptions` lists pending calls; you approve or reject and call `Runner.run` again. The paused state (`RunState`) serialises to JSON and can be reloaded in another process [measured, 7]. The docs warn: "Approval permits a tool call to execute; it does not guarantee exactly-once execution" [7].
- **State.** Sessions store conversation history in a backend you pick. Sandbox state can be snapshotted and "rehydrated" in a fresh container [vendor, 8]. Crash recovery of the run itself is your job, or a durable engine's: Temporal's integration went GA on 2026-03-23 [vendor, 33]; Restate and DBOS publish their own [40][42].
- **AgentKit.** Announced October 2025 as Agent Builder (visual canvas), ChatKit (chat UI) and evals. **Agent Builder is deprecated and "scheduled to shut down on November 30, 2026"**; ChatKit remains [measured, 9]. Migration paths: export to Agents SDK code, or recreate as a ChatGPT workspace agent; the export "does not convert your workflow graph" [measured, 10]. Lesson: the visual builder lasted about thirteen months.
- **Maturity.** 30,800 stars (Python), 4,030 (JS). 4.7 M PyPI downloads last week, 2.5 M weekly npm [measured, 61]. MIT licence.
- **Lock-in.** The SDK accepts other model providers, but tracing, sandboxes and hosted tools point at OpenAI's platform.

### 2.3 Google Agent Development Kit (ADK)

- **What it gives.** An open-source (Apache-2.0) framework for agents and multi-agent systems, with a local dev UI, evaluation, sessions and memory services, and A2A built in [vendor, 11].
- **Languages.** Five: Python (reference), Go, TypeScript, Java, Kotlin (2026-10-13) [vendor, 11]. Versions today: Python 2.15.0, Go 2.8.0, `@google/adk` 2.5.0, Java 1.15.0, Kotlin 1.6.0 [measured, 61]. No Rust.
- **Multi-step workflows.** ADK 2.0 added a graph engine: "describe the shape of your application as a graph of nodes connected by edges", mixing agents and plain functions, with conditional routes and parallel steps. "A graph is an agent" [vendor, 12]. Four kinds exist: graph, dynamic (orchestration written as ordinary code), collaborative (a coordinator agent over sub-agents), and the older templates (sequential, loop, parallel) [measured, 13]. Kotlin's graph support is experimental [11]. ADK 2.0 GA date of 2026-05-19: [secondary].
- **Handoffs.** Agent transfer to sub-agents inside a process; A2A for remote agents in any language [11].
- **Human approval.** "Any node can pause the graph and ask a human a question"; the workflow waits durably [vendor, 12].
- **State.** "The run state lives in the session"; ADK rebuilds a paused workflow from session history, so it can resume after a restart, even in another language runtime [vendor, 12]. Durability therefore depends on the session service you configure.
- **Deployment.** Cloud Run, GKE, or Google's managed "Gemini Enterprise Agent Runtime" [11]. Temporal and Restate both list ADK integrations [35][40].
- **Maturity.** 22,296 stars (Python), 8,992 (Go). 2.8 M PyPI downloads last week [measured, 61].
- **Lock-in.** Model-agnostic on paper, Gemini-first in defaults and managed runtime.

### 2.4 Microsoft Agent Framework (successor of AutoGen and Semantic Kernel)

- **What it gives.** Agents, a "harness agent" (planning, compaction, file access, tool approval), workflows, and integrations [measured, 15]. 1.0 shipped 2026-04-03 for .NET and Python with "stable APIs, and a commitment to long-term support" [vendor, 14].
- **Languages.** .NET and Python (stable), Go (public preview since 2026-07-10, several features missing) [measured, 15][secondary, 18]. No Rust, no Java found.
- **Multi-step workflows.** "Functional and graph-based workflows that connect agents and functions through explicit execution paths" [15]. Ready-made orchestration patterns: sequential, concurrent, handoff, group chat, Magentic-One. Workflows can also be declared in YAML [vendor, 14].
- **Handoffs.** One of the built-in patterns [14].
- **Human approval.** "All patterns support streaming, checkpointing, human-in-the-loop approvals, and pause/resume" [vendor, 14].
- **State.** Checkpoints to a store you provide (local file, Cosmos DB). Microsoft's own comparison table is frank: for Agent Framework workflows, state storage is "Bring your own (checkpoint manager)" and failure recovery is "Manual"; for the Durable Task stack it is "Automatic" [measured, 16]. A Durable Task extension for Agent Framework closes the gap [16].
- **Relation to its ancestors.** "Agent Framework is the direct successor, created by the same teams" [measured, 15]. **AutoGen is archived**: the README says "no longer actively maintained", and the GitHub API reports `archived: true` [measured, 17][61]. Semantic Kernel still releases (dotnet-1.82.0, 2026-11-07) [measured, 61].
- **Maturity.** PyPI `agent-framework` 1.26.0 (2026-11-12), 38,724 downloads last week: small next to the others; .NET usage through NuGet not measured. The repository URL given by Microsoft, `github.com/microsoft/agent-framework`, **returned 404 on 2026-11-21** from both the API and the web [measured, 61]; reason not found.
- **Lock-in.** Connectors for OpenAI, Anthropic, Bedrock, Gemini, Ollama [14]; hosting and durable features lean on Azure (Foundry, Durable Task Scheduler).

### 2.5 AWS: Strands Agents and Bedrock AgentCore

Two separate things: Strands is the open-source SDK, AgentCore is the managed platform that runs agents built with any SDK.

- **Strands, what it gives.** "Choose Strands when you would otherwise write your own agent loop: it runs in your process with no hosted control plane" [vendor, 19]. Lifecycle limits, tools, MCP, multi-agent patterns, sessions, guardrails, tracing, evals. A packaged "Strands harness" gives a fully assembled agent in one call [19]. Apache-2.0.
- **Languages.** Python (1.65.0) and TypeScript (`@strands-agents/sdk` 1.26.0) [measured, 61]. The repository was renamed `strands-agents/harness-sdk` and is now a monorepo; the old TypeScript repo is archived [measured, 61]. A `strands-agents` crate exists on crates.io but is an unofficial community port with 77 downloads [measured, 61].
- **Multi-step workflows and handoffs.** The docs list multi-agent patterns (graph, swarm, workflow, agents-as-tools) and A2A [secondary: the pattern page returned 404 at the URL tried; names from search results and the README link]. A swarm hands control between agents; a graph fixes the order.
- **Human approval.** "Interrupts" pause the loop from a hook or a tool; a session manager persists the interrupt so it can be answered later by a new process; supported in multi-agent runs too [secondary, 20].
- **State.** Session managers (file, S3, AgentCore Memory) [secondary, 20].
- **AgentCore, what it gives.** Modular services: Harness (managed agent loop in an isolated microVM), Runtime (serverless hosting with session isolation), Memory, Gateway (turns APIs and Lambdas into MCP tools), Identity, Code Interpreter, Browser, Observability (OpenTelemetry), Evaluations, Optimization, Policy (rules checked before every tool call), Registry, Payments [measured, 21]. It "works with custom frameworks and any open-source framework, including CrewAI, LangGraph, LlamaIndex, Google ADK, OpenAI Agents SDK, and Strands Agents" and supports MCP and A2A [vendor, 21].
- **Workflows on AWS.** Step Functions can call AgentCore runtimes with retries and run agents in parallel (March 2026) [vendor, 22], and has an "agentic reasoning step" backed by the managed harness, in preview (June 2026) [vendor, 23]. See also Lambda durable functions in section 4.
- **Maturity.** 9,265 stars; 9.1 M PyPI downloads last week (heavily CI-driven, to be read with care); 0.84 M weekly npm [measured, 61].
- **Lock-in.** Strands is portable. AgentCore is AWS-only by nature, but consumption-priced and usable piece by piece [21].

### 2.6 The five at a glance

| SDK | Languages | Multi-step layer | Handoff | Human approval | State after a crash |
|---|---|---|---|---|---|
| Claude Agent SDK | Python, TS (CLI for others) | none built in; subagents, your code, workflow scripts in Claude Code | delegation to subagents | `canUseTool` callback, `defer` hook | session file on local disk; adapter for shared storage |
| OpenAI Agents SDK | Python, TS | your code | first-class | `needs_approval` + serialisable `RunState` | you reload `RunState`; or Temporal/Restate/DBOS |
| Google ADK 2.x | Python, Go, TS, Java, Kotlin | graph, dynamic, templates | agent transfer, A2A | any node can pause | rebuilt from the session store |
| Microsoft Agent Framework | .NET, Python, Go (preview) | graph and functional workflows, YAML | built-in pattern | built in all patterns | checkpoints you store; automatic only with Durable Task |
| Strands (+ AgentCore) | Python, TS | graph, swarm, workflow | swarm | interrupts | session manager |

## 3. Other frameworks, one paragraph each

**CrewAI.** Niche: "crews" of role-playing agents, and since 2024 "Flows", an event-driven layer that chains code and crews. Flows have typed state, `@router` branches, `@persist` (SQLite by default) so that "failed or restarted flows can automatically reload their previous state", and `@human_feedback` gates (version 1.8.0+) [measured, 25]. Python only. Version 1.15.44 (2026-11-19), 61,145 stars but 0.59 M PyPI downloads last week: many stars, comparatively modest installs [measured, 61]. The company claims 450 M agentic workflows a month and wide Fortune 500 use [vendor, 26]. A paid control plane (AMP) sits on top.

**LlamaIndex Workflows.** Niche: event-driven, async steps, born for document and RAG pipelines. Now a standalone package (`llama-index-workflows` 2.26.1), and the repository is renamed `run-llama/llama-agents`; a server package wraps a workflow as an API "with streaming, persistence, and human-in-the-loop support" [secondary, 27]. 1.2 M PyPI downloads last week; the TypeScript package was last published 2026-03-09 [measured, 61]. How durability works inside: not found.

**Pydantic AI.** Niche: type-safe Python agents from the Pydantic team, deliberately small. Its distinctive move is to delegate durability instead of building it: an agent gets a durability "capability" for Temporal, DBOS, Prefect, Restate, AWS Lambda, Azure Durable Task, Airflow and others; the engine "journals the agent's model requests and the tool calls it wraps" [measured, 28]. Human approval uses deferred tools: the run ends, a later run picks it up [secondary]. Version 2.71.0 (2026-11-19), 21,325 stars, 1.6 M PyPI downloads last week [measured, 61]. Airflow's own agent decorator is built on it [44].

**Mastra.** Niche: the TypeScript-native full stack (agents, workflows, memory, evals, dev studio) from the Gatsby founders. 1.0 on 2026-01-20 with locked APIs [vendor, 29]. Workflow steps can suspend and resume; Temporal can be the execution backend [secondary, 29]. Thoughtworks Radar listed it in April 2026 [secondary, 29]. `@mastra/core` 1.85.0, 29,723 stars, 4.1 M weekly npm downloads [measured, 61]. Open core: GitHub does not detect a standard licence [measured, 61]. No Python.

**Vercel AI SDK.** Niche: the default TypeScript library for calling models and streaming to a UI; by far the most installed item in this note (`ai` 7.0.179, 48.5 M weekly npm downloads, 28,118 stars) [measured, 61]. Version 6 (December 2025) added an agent class (`ToolLoopAgent`) and `needsApproval` on tools [secondary, 30]. Durability comes from a separate project, Workflow DevKit (`workflow` 5.7.1, 2,526 stars): functions marked `"use workflow"` and `"use step"` are checkpointed, and `WorkflowAgent` runs the same loop with each tool call as a durable step [secondary, 30][measured versions, 61].

**DSPy.** Not an orchestrator. Niche: you declare what a model call must do (a "signature"), give examples and a metric, and an optimizer (MIPROv2, GEPA) writes the prompts. Use it to make one step of a workflow reliably good, inside any of the other frameworks. Version 3.5.0 (2026-11-10), 39,166 stars, 1.6 M PyPI downloads last week [measured, 61]. Production users are self-reported (Shopify, Databricks, Dropbox and others) [vendor, 31]; Dropbox published its own write-up [secondary]. Python only.

**smolagents (Hugging Face).** Niche: minimal "code agents" that write Python to call tools, good for teaching and for open-weight models. 30,467 stars, but the last release is 1.26.0 from 2026-05-29, almost six months ago, with 0.16 M PyPI downloads last week [measured, 61]. No checkpoint, approval or durable layer documented [secondary]. Read it as a library to learn from, not a base for a team workflow.

## 4. Durable workflow engines used for agents

### 4.1 Why teams put an agent inside a durable workflow

- **The arithmetic of long chains.** Five steps at 99 % reliability give about 95 % for the chain; ten steps about 90 % [vendor, 41]. Agents make many steps.
- **Tokens already paid.** Without checkpoints, a crash at step 14 repeats and re-bills steps 1 to 13. Microsoft lists "expensive token consumption" as a production reason [measured, 16].
- **Waiting for people.** An approval can take days. A durable wait holds no process and costs no compute [measured, 24][46].
- **Deploys and restarts.** Long runs must survive a redeploy of the worker.
- **The split that makes it work.** The workflow code is deterministic and replayable; every model call and tool call is a recorded step. "The Workflow handles orchestration and must be deterministic. LLM calls and tool calls run in Activities" [vendor, 34]. The agent stays free to choose its next action; the engine only guarantees that a choice already made is not made twice.

What durable execution does **not** give (Thoughtworks, 2026-11-10 [secondary, 46]):
- Steps are at-least-once: a retry can repeat a side effect, so the receiving side needs idempotency keys.
- Changing the code while runs are suspended can break replay; versioning is a discipline of its own, and engines behave differently.
- Replay cost grows with the length of the history; long agents need snapshots.
- Facts go stale during a three-week wait; the harness must re-check them.

### 4.2 The engines

| Engine | Model | Languages | Agent integrations | Maturity [measured, 61] |
|---|---|---|---|---|
| **Temporal** | separate server (self-host or Cloud); workflows + activities; replay | Go, Java, Python, TS, .NET, Ruby, PHP, **Rust (GA Sept 2026)** [38] | OpenAI Agents SDK (GA 2026-03-23), Pydantic AI, Vercel AI SDK, Google ADK, Mastra, Strands, Spring AI [33][35] | server 1.32.2; 24,531 stars; 11.6 M PyPI downloads/week; Rust SDK 1.2.0 |
| **Restate** | one binary (written in Rust) in front of your services; journals each step | TS, Python, Java/Kotlin, Go, **Rust (0.13, pre-1.0)** | Vercel AI SDK, OpenAI Agents SDK, Google ADK, Pydantic AI, LangChain [40] | 1.8.1; 4,729 stars; licence not a standard open-source one |
| **DBOS** | a library, state in your own Postgres, no extra server | Python, TS, Go, Java | Pydantic AI, OpenAI Agents SDK, Vercel AI [42] | Python 3.6.0; 1.2 M PyPI downloads/week |
| **Inngest** | event-driven functions made of steps; cloud or self-host | TS, Python, Go | `step.ai`, AgentKit (TS) | 1.53.0; 6,066 stars; 4.1 M npm downloads/week; AgentKit last published 2025-11-13 |
| **Hatchet** | task queue and durable tasks on Postgres, MIT | Python, TS, Go, Ruby | generic | 0.114.2; 8,327 stars |
| **Prefect** | Python data orchestrator; tasks and flows | Python | Pydantic AI capability [28] | 3.9.4; 24,204 stars; ControlFlow (its agent framework) archived since 2025 |
| **Airflow** | scheduled DAGs; batch and data | Python (TS tasks in 3.4) | AI provider 1.0: `@task.agent`, sandboxes, human review [44] | 3.4.0 (2026-11-06); 47,584 stars |
| **AWS Step Functions** | managed state machine in a JSON DSL, visual designer | DSL | AgentCore integrations, agent step in preview [22][23] | managed service |
| **AWS Lambda durable functions** | checkpoint and replay inside Lambda, up to one year | JS/TS, Python, Java, Go, **Rust**, C# [24] | "agentic AI applications" named use case [24] | launched Dec 2025 |
| **Cloudflare Workflows** | steps on Workers; GA April 2025 | TS/JS, Python | Agents SDK `AgentWorkflow`, `waitForApproval`, events awaited up to a year [45] | `agents` 0.34.0; 6,021 stars |
| **Azure Durable Task** | Durable Functions lineage, managed scheduler | .NET, Python, Java, TS/JS | extension for Microsoft Agent Framework [16] | managed service |
| **Vercel Workflow DevKit** | directives in TS code | TS | AI SDK `WorkflowAgent` [30] | 5.7.1; 2,526 stars |

Notes per engine:
- **Temporal** is the reference and the heaviest: a cluster and a database to run, or Temporal Cloud at about $50 per million actions on pay-as-you-go [vendor, 39, via search summary]. Replay 2026 added serverless workers on AWS Lambda (pre-release) and standalone activities [vendor, 37]. The Rust SDK lists AI agents as a use case but ships no agent integration [measured, 38].
- **Restate** aims at the same guarantees with far less to operate; its agent docs state that "every LLM call and tool execution is durably persisted" and that approvals resume "even across restarts" [vendor, 40].
- **DBOS** is the smallest step from "a Python or TypeScript service with Postgres": decorate functions, get recovery.
- **Inngest** is strong where work starts from events and ends in a web UI. Its own agent framework looks dormant; its durable primitives are current [measured, 61].
- **Prefect and Airflow** are data orchestrators that added agent steps. They fit when the agent is one task in a scheduled pipeline, less when a human converses with it. Airflow 3.1 added human-in-the-loop tasks; the AI provider 1.0 adds agents, sandboxes and review loops with a mandatory iteration cap [vendor, 44].
- **Step Functions** fits when the workflow mostly glues AWS services and a visual state machine helps audits; Lambda durable functions fit when the workflow is application code [measured, 24].

### 4.3 Named examples

- **OpenAI Codex (web agent) on Temporal.** "Heck, OpenAI's Codex web agent is built on Temporal" (Temporal blog, 2025-11-12) [vendor, 34]. OpenAI appears as a customer logo on Temporal's AI page [vendor, 35], and an OpenAI VP spoke at Temporal's Replay 2026 [secondary, 37]. **No OpenAI-authored source found.** OpenAI's own April 2026 post speaks of snapshot and rehydration, and does not name Temporal [measured, 8].
- **Replit Agent on Temporal.** Replit "migrated their popular coding agent to Temporal"; quote from Replit's Connor Brewster: "Temporal gives us a lot more confidence to build the product" [vendor, 35]. Temporal's blog also names "Replit's new long-running Agent 3" [vendor, 34].
- **Retool Agents on Temporal.** Shipped "in a matter of months"; "just wouldn't have been possible without Temporal" (Lizzie Siegrist, Retool) [vendor, 35].
- **Gorgias.** "All LLM use cases are workflows" (Romain Niveau) [vendor, 35].
- **Lovable, Abridge, Hebbia**: logos only on Temporal's AI page, no claim attached [vendor, 35]. **Cursor**: a Replay 2026 session title mentions Temporal [secondary]; no primary source found.
- Named production users of Restate, DBOS, Inngest or Hatchet for agents: not searched in depth; not found.

## 5. CI as an orchestrator

### 5.1 What exists

- **Agent actions on GitHub Actions.** `anthropics/claude-code-action` (v1; 10,040 stars) runs Claude Code in a workflow: on an `@claude` mention, or with a `prompt` on any event including cron; the prompt can invoke a skill from the repository [measured, 51][61]. Equivalent actions exist for Codex (`openai/codex-action`, 1,310 stars) and Gemini CLI (`google-github-actions/run-gemini-cli`, 2,129 stars) [measured, 61].
- **GitHub Agentic Workflows (gh-aw).** You write a Markdown file with YAML front matter; `gh aw compile` generates a normal Actions workflow (`.lock.yml`). **GA on 2026-10-28** on Free, Team and Enterprise [measured, 48]. Version 1.2.2, 5,671 stars [measured, 61]. Engines: Copilot (default, needs a licence), Claude Code, Codex, Gemini, Pi [measured, 49]. Security model: the agent job is read-only and sandboxed behind a firewall; writes go through "safe outputs" that are "sanitized and applied in separate jobs"; a threat-detection job scans proposed changes [measured, 48][49]. Each safe output has a cap (create-issue defaults to one). Cost: AI credits at $0.01 each with a cap of 1,000 per run [secondary, 50]. Adoption figures: not found.
- **GitHub Agent HQ.** A control plane to assign tasks to Copilot, Claude or Codex agents from GitHub itself. Announced October 2025; Claude and Codex in public preview from February 2026 for Pro+ and Enterprise [vendor, 52]. Status after February 2026: not found.
- **GitLab Duo Agent Platform.** GA on 2026-01-15; **Custom Flows GA in GitLab 19.2 (2026-07-16)**: "AI-powered workflows you define once, trigger from native GitLab events, and run in CI/CD pipeline", with human checkpoints at sensitive steps, billed in GitLab Credits [vendor, 53]. Triggers: mentions, assignments, pipelines, merge request events, work item status. A flow cannot call a custom agent from the catalog; it defines its own [secondary, GitLab docs via mirror].

### 5.2 What CI can do as a workflow engine

- React to the events a software team already produces: issue opened, label added, PR updated, comment, schedule.
- Give each step a clean, isolated machine with scoped permissions and secrets.
- Gate a step on a named reviewer: GitHub environment protection rules, "the job pauses until a designated reviewer approves" [measured, 49].
- Fan out (a matrix of up to 256 jobs) and chain (`needs:`, `workflow_call`, dispatching another workflow) [measured, 47][49].
- Leave an audit trail (logs, PR comments, check runs) where the team already looks.

### 5.3 What CI cannot do

Limits read from GitHub's documentation [measured, 47]:

| Limit | Value |
|---|---|
| One job on a GitHub-hosted runner | 6 hours |
| One job on a self-hosted runner | 5 days |
| One workflow run, waits and approvals included | 35 days |
| Waiting for an environment approval | 30 days |
| Matrix | 256 jobs per run |
| Re-runs of one run | 50 |

Consequences (the first three are my reading of these limits and of the gh-aw FAQ):
- **No memory between runs.** A run that ends leaves only what it wrote: a comment, a label, a commit, an artifact. The next run rebuilds context from the issue or PR. The workflow state lives in GitHub objects, not in the engine.
- **No resume inside a job.** A failed job is re-run from its start; the agent's tokens are spent again. gh-aw "has no automatic retries" [measured, 49].
- **Waiting for a human reply is a new event, not a pause.** Only environment approvals pause a run. A question asked in a comment is answered by a new run.
- **Not for the deterministic part.** GitHub's own FAQ: deterministic Actions "remain the right choice for builds, tests, linting, deployments, and reproducible scripts"; agentic workflows suit "interpretation, investigation, or generation" [measured, 49].
- **Plumbing traps.** A PR created with the default token does not trigger CI; safe-output protections do not cover custom jobs or direct write permissions; no macOS runners for gh-aw [measured, 49][51].
- **Cost is double**: runner minutes plus model tokens on every event [measured, 51].

## 6. Protocols

| Protocol | What it standardises | Status (Nov 2026) | Adoption |
|---|---|---|---|
| **MCP** (Model Context Protocol) | how an agent reaches tools and data | Spec revision **2026-07-28**: stateless core, long-running "tasks" extension, OAuth 2.1 alignment; Roots, Sampling, Logging and HTTP+SSE proposed for deprecation, earliest removal July 2027 [secondary, 54; release tag measured, 61]. Governed by the Agentic AI Foundation (AAIF, Linux Foundation) since 2025-12-09 [vendor, 60] | Supported by every SDK in section 2. Rust SDK `rmcp` 3.11.0: 53 M crate downloads [measured, 61]. Registry size (about 65,000 servers) [secondary, single blog] |
| **A2A** (Agent2Agent) | how one agent calls another across teams or vendors | **1.0 in March 2026**, 1.0.1 in May; "more than 150 organizations"; SDKs in Python, JS, Java, Go, .NET [vendor, 55][measured, 61]. Reported move into the AAIF in August 2026 [secondary, 56, page not readable] | In Azure AI Foundry, Copilot Studio, AgentCore Runtime, ADK [vendor, 55]. 26,622 stars. No named production user in the press release |
| **AG-UI** | how an agent streams messages, tool calls and state to a front end | Event-based protocol from CopilotKit (a startup, not a foundation); `@ag-ui/core` 1.0.5 [measured, 61]; Thoughtworks Radar "Trial", April 2026 [secondary, 57] | Integrations in Microsoft Agent Framework (preview) [14], AgentCore, ADK, Strands, Mastra, Pydantic AI [secondary, 57]. 20,983 stars |
| **AGENTS.md** | where a coding agent reads a repository's instructions | Plain Markdown, no schema; stewarded by the AAIF [measured, 58] | "over 60k open-source projects"; read by Codex, Copilot coding agent, Cursor, Gemini CLI, Jules, Zed, Devin, goose and others [vendor, 58]. Claude Code reads `CLAUDE.md` by default [secondary] |
| **Agent Skills** (`SKILL.md`) | a folder of instructions, scripts and resources an agent loads on demand | Open standard since December 2025; **donated to the AAIF on 2026-10-22** [vendor, 59] | "70+ agent platforms", 1 million skills published, nearly 280 million installs [vendor, 59]; ChatGPT, Cursor, GitHub Copilot, VS Code named. Malicious skills are a documented supply-chain risk [secondary] |

Two remarks:
- A second protocol also abbreviated ACP, the Agent Client Protocol (editor to coding agent, from Zed, 4,706 stars, written in Rust) [measured, 61], is not IBM's Agent Communication Protocol, which is reported merged into A2A [secondary].
- For a team harness, MCP, AGENTS.md and Skills are the three that matter today. A2A matters when agents owned by different teams must call each other. AG-UI matters only if you build your own front end.

## 7. Comparison table

Cells mix sourced facts (sections above) and my judgement where a cell says "low", "medium" or "high". "Determinism" means: can the order of steps be fixed in code rather than left to the model.

| Option | Determinism of the flow | Survives a crash | Human-in-the-loop | Observability | Languages | Lock-in | Operating cost |
|---|---|---|---|---|---|---|---|
| LangGraph (baseline) | graph in code | yes, with a checkpointer you configure | interrupts | LangSmith (paid) or OpenTelemetry | Python, TS | low for the library, medium for the platform | a database; or the hosted platform |
| Claude Agent SDK | none built in; your code or a workflow script | session file to reload; not automatic | callback, deferrable | hooks, OpenTelemetry, transcripts | Python, TS | Claude models | tokens; your process. Managed Agents (beta) removes the hosting |
| OpenAI Agents SDK | your code | `RunState` to reload; automatic with Temporal | built in, serialisable | built-in tracing on OpenAI's platform | Python, TS | medium | tokens; sandboxes billed by their provider |
| Google ADK 2.x | graph and templates | resumes from the session store | any node | dev UI, OpenTelemetry | Python, Go, TS, Java, Kotlin | low to medium | a session database, or Google's runtime |
| Microsoft Agent Framework | graph, functional, YAML | manual from checkpoints; automatic with Durable Task | built in | DevUI (preview), OpenTelemetry | .NET, Python, Go (preview) | medium (Azure for durability) | a checkpoint store, or Azure services |
| Strands + AgentCore | graph or swarm | session manager; AgentCore keeps sessions | interrupts | traces by default; CloudWatch | Python, TS | low for Strands, high for AgentCore | consumption-priced on AWS |
| Pydantic AI + an engine | your code | yes, automatic (engine) | deferred tools | Logfire or OpenTelemetry | Python | low | that of the engine chosen |
| Mastra | workflow steps | suspend/resume snapshots; Temporal backend | built in | studio, OpenTelemetry | TS | low to medium (open core) | a storage backend |
| Vercel AI SDK + Workflow | code with directives | yes with `WorkflowAgent` | `needsApproval` | Vercel dashboard or own | TS | medium (best on Vercel) | pay per step on Vercel, or self-host |
| CrewAI Flows | event-driven code | `@persist` reload | `@human_feedback` | AMP (paid) | Python | medium | SQLite or your store; AMP for teams |
| Temporal | full, enforced by replay | yes, automatic | signals, waits of any length | web UI with full history | 8 including Rust | low (MIT server) | high if self-hosted (cluster + database); about $50 per million actions on Cloud |
| Restate | full | yes, automatic | durable promises | UI, journals | 5 including Rust | low to medium (licence) | one binary, or cloud |
| DBOS | full | yes, automatic | wait for events | Postgres tables, console | Python, TS, Go, Java | low (MIT) | your Postgres |
| Inngest | full, step based | yes, automatic | wait for event | dashboard | TS, Python, Go | medium | cloud per run, or self-host |
| Step Functions / Lambda durable | full (DSL or code) | yes, automatic | callback tokens, waits to one year | console, CloudWatch | DSL; 7 languages for Lambda incl. Rust | high (AWS) | per transition / per invocation, zero when idle |
| Cloudflare Workflows | full | yes, automatic | `waitForEvent`, one year | dashboard | TS, Python | high (Cloudflare) | per request, zero when idle |
| GitHub Actions + agent action / gh-aw | the YAML is fixed, the agent step is not | no; re-run the job | environment approvals (30 days); otherwise a new event | run logs, PR comments | any (it runs a CLI) | high (GitHub) | runner minutes + tokens per event |
| GitLab Custom Flows | flow definition fixed | not found | checkpoints in the flow | pipeline logs | n/a | high (GitLab) | GitLab Credits |

## 8. What this suggests for a team building an AI SDLC workflow (analysis, not reporting)

1. **Four layers, four choices.** (a) the trigger: an event in the forge or the ticket tool; (b) the skeleton: the fixed stages of a ticket (refine, develop, review, test, ship) and the gates between them; (c) the agent that works inside a stage; (d) the runtime that keeps the skeleton alive across days. A framework that claims all four deserves suspicion on at least one.
2. **The agent layer is settled for coding work**: a coding agent harness (Claude Agent SDK or the CLI it wraps, Codex, Copilot) plus AGENTS.md, skills and MCP. None of the general frameworks in section 3 does better at editing a repository.
3. **The skeleton is where the "skill or code?" question lives.** A stage order that never changes is code, not a prompt. The vendors now say so themselves: Microsoft ("If you can write a function to handle the task, do that instead of using an AI agent" [15]), GitHub (deterministic Actions for builds and deploys [49]), Anthropic (the script holds the loop, the agent holds the judgement [5]).
4. **Three sizes of runtime.**
   - *Small, one repository*: CI is the runtime. State lives in the issue and the PR. Good until a stage needs to wait for something that is not a forge event, or until re-running a failed job costs too much.
   - *Medium, several repositories or a ticket tool outside the forge*: a small service with a durable library and a database already owned (DBOS on Postgres, or Restate as one binary). The workflow is ordinary code; each stage calls the coding agent as one recorded step.
   - *Large, many teams*: Temporal, or the cloud's native engine. Justified by volume and by an operations team, not by the first workflow.
5. **Rust, since it was asked.** No lab ships a Rust agent SDK: Claude Agent SDK (Python, TS, else CLI subprocess), OpenAI Agents SDK (Python, TS), ADK (five languages, not Rust), Microsoft (.NET, Python, Go). Rust is well served one layer down: Temporal's Rust SDK is GA (1.2.0), Restate's server is written in Rust and has a pre-1.0 Rust SDK (0.13), Lambda durable functions has a Rust SDK, MCP has an official Rust SDK (`rmcp` 3.11.0), A2A has `a2a-rs` (116 stars) [measured, 61]. A Rust skeleton that drives a coding agent as a subprocess is therefore a supported shape; a Rust agent loop is do-it-yourself.
6. **Signals of what not to bet on**: visual builders (Agent Builder, gone in 13 months), research-born multi-agent chat frameworks (AutoGen archived, ControlFlow archived), and any framework whose last release is more than a few months old in a field that releases weekly.

## 9. Not found, or not verified

- An OpenAI-authored statement that Codex runs on Temporal. Only Temporal says so.
- Why `github.com/microsoft/agent-framework` returns 404 today, and its star count.
- The Strands multi-agent pattern page (404 at the URL tried): which patterns are deterministic, from the primary docs.
- Maximum session duration of AgentCore Runtime.
- Status of GitHub Agent HQ and of the Copilot coding agent after February 2026.
- Adoption numbers for gh-aw and for GitLab Custom Flows.
- Whether GitLab Custom Flows resume after a runner failure.
- Unit prices for Inngest, Restate Cloud, DBOS and Step Functions; the Temporal price comes from a search summary of its pricing page.
- Primary confirmation that A2A moved into the AAIF (Axios page blocked) and that IBM's ACP merged into A2A.
- MCP registry size from the registry itself.
- How LlamaIndex Workflows persist state; a primary date for ADK 2.0 GA; the ADK human-input docs page (404).
- Whether the Claude Agent SDK exposes dynamic workflows as an API; the reported June 2026 billing change for subscription use of the SDK.
- Named production users of Restate, DBOS, Inngest or Hatchet for agent workloads.

## Sources

Primary documents opened on 2026-11-21 unless marked "(search summary)".

- [1] Claude Agent SDK overview: https://code.claude.com/docs/en/agent-sdk/overview.md
- [2] Claude Agent SDK, sessions: https://code.claude.com/docs/en/agent-sdk/sessions.md
- [3] Claude Agent SDK, approvals and user input: https://code.claude.com/docs/en/agent-sdk/user-input.md
- [4] Claude Managed Agents overview: https://platform.claude.com/docs/en/managed-agents/overview
- [5] "A harness for every task: dynamic workflows in Claude Code", 2026-06-02: https://claude.dev/blog/a-harness-for-every-task-dynamic-workflows-in-claude-code/ (redirect from https://claude.com/blog/a-harness-for-every-task-dynamic-workflows-in-claude-code)
- [6] OpenAI Agents SDK docs: https://openai.github.io/openai-agents-python/
- [7] OpenAI Agents SDK, human in the loop: https://openai.github.io/openai-agents-python/human_in_the_loop/
- [8] OpenAI, "The next evolution of the Agents SDK", 2026-04-15: https://openai.com/index/the-next-evolution-of-the-agents-sdk/
- [9] OpenAI Agent Builder guide, deprecation notice: https://developers.openai.com/api/docs/guides/agent-builder
- [10] OpenAI, migrate from Agent Builder: https://developers.openai.com/api/docs/guides/agent-builder/migrate-from-agent-builder
- [11] Google Cloud, "One Agent Development Kit, five languages", 2026-10-13: https://cloud.google.com/blog/topics/developers-practitioners/one-agent-development-kit-five-languages
- [12] Google, "Announcing ADK Go 2.0", 2026-06-30: https://developers.googleblog.com/en/announcing-adk-go-20/
- [13] ADK docs, workflows: https://adk.dev/workflows/
- [14] Microsoft Agent Framework 1.0, 2026-04-03: https://devblogs.microsoft.com/agent-framework/microsoft-agent-framework-version-1-0/
- [15] Microsoft Agent Framework overview (updated 2026-10-28): https://learn.microsoft.com/en-us/agent-framework/overview/
- [16] Durable Task for AI agents: https://learn.microsoft.com/en-us/azure/durable-task/sdks/durable-task-for-ai-agents
- [17] AutoGen README, archive notice: https://raw.githubusercontent.com/microsoft/autogen/main/README.md
- [18] Microsoft Agent Framework for Go, public preview, 2026-07-10 (search summary): https://devblogs.microsoft.com/go/microsoft-agent-framework-for-go-public-preview/
- [19] Strands Agents README: https://raw.githubusercontent.com/strands-agents/harness-sdk/main/README.md
- [20] Strands, interrupts (search summary): https://strandsagents.com/docs/user-guide/concepts/interrupts/
- [21] Amazon Bedrock AgentCore overview: https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/what-is-bedrock-agentcore.html
- [22] Step Functions adds AgentCore integrations, March 2026 (search summary): https://aws.amazon.com/about-aws/whats-new/2026/03/aws-step-functions-sdk-integrations
- [23] Step Functions agentic reasoning step, June 2026 (search summary): https://aws.amazon.com/about-aws/whats-new/2026/06/aws-step-functions-agentcore
- [24] AWS Lambda durable functions: https://docs.aws.amazon.com/lambda/latest/dg/durable-functions.html
- [25] CrewAI Flows: https://docs.crewai.com/en/concepts/flows
- [26] CrewAI press release, 2026-02-11 (search summary): https://www.businesswire.com/news/home/20260211693427/en ; AMP: https://blog.crewai.com/crewai-amp-the-agent-management-platform/
- [27] LlamaIndex Workflows (search summary): https://developers.llamaindex.ai/python/llamaagents/workflows/ ; https://raw.githubusercontent.com/run-llama/llama-agents/main/README.md
- [28] Pydantic AI, durable execution: https://pydantic.dev/docs/ai/capabilities/durable_execution/overview/
- [29] Mastra 1.0 (search summary): https://mastra.ai/blog/announcing-mastra-1 ; suspend and resume: https://mastra.ai/docs/workflows/suspend-and-resume.md ; Thoughtworks Radar: https://www.thoughtworks.com/radar/languages-and-frameworks/mastra
- [30] Vercel AI SDK 6 (search summary): https://vercel.com/blog/ai-sdk-6 ; WorkflowAgent: https://ai-sdk.dev/docs/agents/workflow-agent
- [31] DSPy in production (search summary): https://dspy.ai/community/use-cases/ ; Dropbox: https://dropbox.tech/machine-learning/optimizing-dropbox-dash-relevance-judge-with-dspy
- [32] smolagents: https://github.com/huggingface/smolagents
- [33] Temporal, OpenAI Agents SDK integration (2025-07-30, GA note 2026-03-23): https://temporal.io/blog/announcing-openai-agents-sdk-integration
- [34] Temporal, "Of course you can build dynamic AI agents with Temporal", 2025-11-12: https://temporal.io/blog/of-course-you-can-build-dynamic-ai-agents-with-temporal
- [35] Temporal AI solutions page: https://temporal.io/solutions/ai
- [36] Temporal and agentic sandboxes, 2026-04-16: https://temporal.io/blog/introducing-temporal-and-agentic-sandboxes-openai-agents-sdk
- [37] Temporal Replay 2026 announcements (search summary): https://temporal.io/blog/replay-2026-product-announcements
- [38] Temporal Rust SDK GA, 2026-09-23: https://temporal.io/blog/build-durable-applications-rust-temporal-rust-sdk-now-generally-available
- [39] Temporal pricing (search summary): https://temporal.io/pricing
- [40] Restate AI docs: https://docs.restate.dev/ai
- [41] Inngest, "Durable execution: the key to harnessing AI agents", 2026-02-19: https://www.inngest.com/blog/durable-execution-key-to-harnessing-ai-agents ; durable agents: https://www.inngest.com/docs/learn/durable-agents
- [42] DBOS integrations (search summary): https://docs.dbos.dev/integrations/pydantic-ai ; https://docs.dbos.dev/integrations/openai-agents ; https://dbos.dev/blog/dbos-new-features-march-2026
- [43] Hatchet: https://github.com/hatchet-dev/hatchet
- [44] Airflow (search summary): https://airflow.apache.org/blog/airflow-3.1.0/ ; https://airflow.apache.org/blog/common-ai-provider-1.0/ ; https://airflow.apache.org/blog/airflow-3.4.0/
- [45] Cloudflare Agents and Workflows: https://developers.cloudflare.com/agents/concepts/workflows ; GA post: https://blog.cloudflare.com/workflows-ga-production-ready-durable-execution/
- [46] Kiran Prakash, "Long-horizon agents and durable execution", martinfowler.com, 2026-11-10: https://martinfowler.com/articles/durable-execution-agents.html
- [47] GitHub Actions limits: https://docs.github.com/en/actions/reference/limits
- [48] GitHub changelog, Agentic Workflows GA, 2026-10-28: https://github.blog/changelog/2026-10-28-github-agentic-workflows-generally-available/
- [49] GitHub Agentic Workflows FAQ: https://github.github.com/gh-aw/reference/faq/
- [50] InfoQ on gh-aw GA (search summary): https://www.infoq.com/news/2026/11/github-agentic-workflows-ga/
- [51] Claude Code GitHub Actions: https://code.claude.com/docs/en/github-actions.md
- [52] GitHub Agent HQ (search summary): https://github.blog/news-insights/company-news/welcome-home-agents/ ; https://github.blog/news-insights/company-news/pick-your-agent-use-claude-and-codex-on-agent-hq/
- [53] GitLab, Custom Flows GA, 2026-07-16: https://about.gitlab.com/blog/multi-step-software-delivery-with-agentic-flows/ ; platform GA, 2026-01-15 (search summary): https://about.gitlab.com/blog/gitlab-duo-agent-platform-is-generally-available/
- [54] AAIF, "MCP 2026-07-28: what's changing", 2026-07-21: https://aaif.io/blog/mcp-2026-07-28-whats-changing-and-how-to-migrate
- [55] Linux Foundation, A2A at one year, 2026-04-09: https://www.linuxfoundation.org/press/a2a-protocol-surpasses-150-organizations-lands-in-major-cloud-platforms-and-sees-enterprise-production-use-in-first-year
- [56] Axios, A2A and the Agentic AI Foundation, 2026-08-17 (HTTP 403, title only): https://axios.com/2026/08/17/a2a-agentic-ai-foundation-open-ai-standards
- [57] AG-UI: https://github.com/ag-ui-protocol/ag-ui ; Thoughtworks Radar (search summary): https://www.thoughtworks.com/radar/platforms/ag-ui-protocol
- [58] AGENTS.md: https://agents.md/
- [59] Anthropic, donating Agent Skills to the AAIF, 2026-10-22: https://www.anthropic.com/news/donating-agent-skills-to-the-agentic-ai-foundation
- [60] OpenAI, Agentic AI Foundation (search summary): https://openai.com/index/agentic-ai-foundation/
- [61] Measurements taken 2026-11-21: GitHub REST API (`repos/OWNER/NAME`, `releases/latest`) for every repository named; npm registry and `api.npmjs.org/downloads/point/last-week` (week 2026-11-14 to 2026-11-20); `pypistats.org/api/packages/NAME/recent` and `pypi.org/pypi/NAME/json`; `crates.io/api/v1/crates/NAME`.
