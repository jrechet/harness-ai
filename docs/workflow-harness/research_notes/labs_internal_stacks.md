# How the labs and coding-agent companies build their own harnesses

Research note, written 2026-11-21. Scope: what each company says about its own stack, in its own engineering posts, docs and repositories.

## Summary

1. None of the labs describes its own coding agent as built on a graph framework. Claude Code, Codex, Cursor, Devin, Droid, Amp and Manus are all described as one model-in-a-loop written in plain code (TypeScript or Rust), with orchestration added around the loop, not inside it.
2. The reliability layer that does recur is *durable execution* (a runtime that records each step so a crashed run resumes instead of restarting): Temporal at Cursor (its own account) and at OpenAI Codex and Replit (per Temporal's site only); an append-only event log at Anthropic; session replay in Google ADK; cached-result replay in Claude Code workflows.
3. Everyone who runs agents in the cloud has converged on the same split: the loop (brain), the sandbox (hands) and the run history (state) are three separate things, and credentials never enter the sandbox.
4. State that matters is kept in files and git (specs, plans, progress logs, feature lists, handoff notes), and humans approve at two points: the plan before the run and the pull request after it.
5. All of them report deleting harness parts as models improve, so the durable investment is in the environment, the checks and the written specs, not in elaborate orchestration.

## How to read this note

Terms, defined once:

- **Harness**: everything around the model that makes it an agent: the loop that calls the model, the tools, the prompts, the context management, the permission checks. Anthropic's docs define it this way for Claude Code, and Factory uses the same definition for Droid.
- **Workflow vs agent** (Anthropic's distinction): in a workflow, code decides the next step; in an agent, the model decides the next step.
- **Graph framework**: a library where you declare steps as nodes and transitions as edges, and a scheduler runs the graph (LangGraph, Google ADK 2.0, Microsoft Agent Framework).
- **Durable execution**: a runtime that persists every step of a long process so it survives crashes and can pause for days (Temporal, Vercel Workflow, and similar).
- **Sandbox**: the isolated machine or container where the agent's commands run. A **microVM** is a small virtual machine with its own kernel (Firecracker is the usual engine).
- **Compaction**: summarising an over-long conversation so the agent can continue in a fresh context window. A **context reset** or **handoff** starts a new agent from a written note instead.

Evidence labels used below:

- **[M] measured**: I checked it myself today (GitHub API, direct download of a page or file).
- **[V] vendor**: stated by the company about itself. Not independently verified.
- **[S] secondary**: reported by a third party (press, a partner's case study, a newsletter).

Caveat on wording: most pages were read through a fetch tool that returns a summary. Figures and dates were taken from those summaries; exact wording was verified directly only where marked [M]. Paraphrase is used throughout; there is one direct quotation in this note.

Second pass (same day): the primary pages for Anthropic, OpenAI, Cursor, Cognition, Manus, Vercel, Amp's handoff post, the Jules changelog, ADK Go 2.0 and the GitHub statistics were fetched again independently and agreed with the first pass. Lines added in that pass are marked "(2nd pass)". Sources cited only in the first pass (Symphony's spec, Cognition's cloud-agents and blockdiff posts, Factory's two news posts, Amp's Neo post, the Replit and Temporal case studies, the Microsoft post) were not re-fetched.

---

## 1. Anthropic

### 1.1 The founding text: workflows versus agents

"Building effective agents" (19 Dec 2024) [V]:

- Workflows are systems where predefined code paths orchestrate models and tools. Agents are systems where the model directs its own process and tool use.
- Named patterns, in rising order of autonomy: augmented LLM, prompt chaining, routing, parallelization (sectioning and voting), orchestrator-workers, evaluator-optimizer, autonomous agent.
- The central advice, in their words: "find the simplest solution possible, and only increasing complexity when needed". They add that this may mean building no agentic system at all.
- On frameworks: they make the first steps easy but hide the prompts and responses, which makes debugging harder, and they tempt teams to add complexity. The advice is to start with direct API calls, and if a framework is used, to understand the code under it.

A detail that matters for this study [M]: the framework list on that page has been edited. A March 2025 archive lists LangGraph, Amazon Bedrock's agent framework, Rivet and Vellum. The live page today lists the Claude Agent SDK, the Strands Agents SDK from AWS, Rivet and Vellum. LangGraph is no longer named. The page now opens with a note that the tooling has changed and points to Managed Agents as the current approach.

### 1.2 The research posts on long-running work

| Date | Post | Design | What they report |
|---|---|---|---|
| 13 Jun 2025 | Multi-agent research system | Orchestrator-worker: a lead agent plans and spawns parallel search subagents; a separate agent adds citations | 90.2% better than a single agent on an internal eval; agents use about 4x the tokens of chat and multi-agent about 15x; resumes from the point of error using deterministic retries and checkpoints; "rainbow" deployments keep old and new versions running side by side so in-flight agents are not broken [V] |
| 29 Sep 2025 | Effective context engineering | Compaction, structured notes outside the context window, subagents returning condensed summaries, just-in-time retrieval by file path | Context is a finite resource; recall degrades as the window fills (context rot) [V] |
| 26 Nov 2025 | Effective harnesses for long-running agents | An initializer session writes a feature list (JSON, 200+ entries, all failing), a progress file, an `init.sh` and a first commit; every later session does one feature, tests it in a browser, commits, updates the progress file | Same harness for both roles, only the first prompt differs; compaction alone was not enough; browser automation caught bugs that unit tests and curl missed [V] |
| 5 Feb 2026 | Building a C compiler with parallel Claudes | A bash loop restarts Claude Code forever; 16 agents, each in its own Docker container; a bare git repo as shared upstream; agents claim tasks by committing lock files; no orchestrator agent | About 2,000 sessions, about $20,000, a 100,000-line compiler written in Rust; the test suite is what steers the agents [V] |
| 24 Mar 2026 | Harness design for long-running application development | Planner, generator, evaluator. Before each sprint the generator and evaluator agree a written contract in files; the evaluator drives the running app through Playwright and applies hard thresholds | Solo run: 20 minutes, $9. Full harness: 6 hours, $200. With a newer model the sprint structure was removed and the evaluator moved to one pass at the end [V] |
| 8 Apr 2026 | Scaling Managed Agents | Brain (model plus loop), hands (sandboxes and tools), session (append-only event log) as three separate components | Time to first token down about 60% at the median and over 90% at the 95th percentile, because containers are created only when needed [V] |

State, retries, approval, evaluation, as Anthropic describes them:

- **State.** In the research harnesses: files and git. In Managed Agents: the session event log, stored outside both the loop and the sandbox, read back in slices so a new loop can resume from the last event [V].
- **Retries.** A dead container is returned to the model as a failed tool call, and the model can ask for a new one. A dead loop is replaced by a new one that reloads the log. The old single-container design is described as a pet; the new parts are cattle [V].
- **Credentials.** Never in the sandbox. Git tokens are used at clone time by the platform; tool tokens sit in a vault behind a proxy [V].
- **Evaluation.** "Demystifying evals for AI agents" (9 Jan 2026): start with 20 to 50 tasks drawn from real failures; prefer deterministic graders; grade the outcome, not the path; read the transcripts; distinguish capability evals (start low) from regression evals (stay near 100%) [V]. The Agent SDK post ranks feedback types: clear rules such as linters first, visual checks second, a judging model last and described as not very robust [V].

Lessons they state directly:

- Every harness component encodes an assumption about what the model cannot do, and those assumptions expire. Their own example: context resets added for one model became dead weight with the next (posts of 24 Mar, 2 Apr and 8 Apr 2026) [V].
- Multi-agent setups work mainly because they spend more tokens on the problem, and they fit parallel research better than tightly coupled coding work (13 Jun 2025) [V].
- (2nd pass) An agent grading its own work skews positive, and a model is a poor QA agent until its grading criteria are written down and given hard thresholds; hence a separate evaluator (24 Mar 2026) [V].
- (2nd pass) "Harnessing Claude's intelligence" (2 Apr 2026, Lance Martin) [V] gives three rules: lean on tools the model already handles well (Claude Code rests on a shell tool and a text-editor tool, and skills, memory and programmatic tool calling are composed from those); keep asking what the harness can stop doing; keep in the harness only the boundaries that are about user experience, cost and security, for example a stable prompt prefix for caching and dedicated tools for high-stakes actions so they can be gated by confirmation.

### 1.3 Claude Code as built today

Stack: public repository `anthropics/claude-code`, language TypeScript, 156,553 stars, pushed today [M]. The terminal interface is reported to use React with Ink [S, Pragmatic Engineer]. Local sandboxing uses Linux bubblewrap and macOS seatbelt, with a network proxy outside the sandbox; Anthropic reports 84% fewer permission prompts internally; the runtime is open source (`anthropic-experimental/sandbox-runtime`, 7,210 stars [M]).

Architecture as documented (docs read 2026-11-21) [V]:

- **One loop.** Gather context, take action, verify, repeat. The same loop runs in the terminal, the desktop app, IDE extensions, the browser, Slack and CI.
- **Sessions.** Each message and tool result is appended to a plain JSONL file on disk, which is what makes resume, fork and rewind possible. Files are snapshotted before edits (checkpoints).
- **Permissions.** Modes range from manual approval to an auto mode where a classifier reviews actions and blocks risky ones.
- **Extension layer, each with one job:**

| Mechanism | What it is | Deterministic? |
|---|---|---|
| CLAUDE.md | Instructions loaded into every session; guidance is to stay under 200 lines | No, it is a request |
| Skills | Markdown procedures loaded on demand; only the description is always in context | No, the model interprets |
| Subagents | Workers with their own context window that return a summary | No, the model decides when |
| Hooks | Scripts fired on lifecycle events | Yes. The docs say rules that must always hold belong in hooks, not prompts |
| MCP servers | Connections to external tools | Tool-level |
| Plugins | The packaging unit for all of the above | n/a |
| Dynamic workflows | A JavaScript script that runs many subagents; the script holds the plan | Yes for control flow |
| Agent teams | A lead session supervising peer sessions with a shared task list | No; experimental, off by default |

- **Where it runs.** Locally; in background sessions watched from one screen (research preview); in cloud sessions on Anthropic-managed VMs or on self-hosted runners; in "projects" that coordinate many cloud sessions (public beta). In the cloud, git credentials stay on the server side behind a proxy, and when a VM is reclaimed the conversation is restored but running background work is not.

Dynamic workflows deserve attention because they are Anthropic's own answer to "when does code hold the plan":

- The script is plain JavaScript with `agent()`, `pipeline()`, `parallel()` and `phase()`. Clocks and random numbers are forbidden inside it so a relaunch replays identically.
- Each agent's result is saved. On relaunch, completed agents return their saved result until the first one whose prompt changed; from there everything reruns.
- Limits: 16 concurrent agents by default, 1,000 agents per run, no user input mid-run. For a sign-off between stages, the docs say to run each stage as its own workflow.
- A stalled agent is restarted up to five times; a structured output that fails its schema is retried up to five times.
- The human approves the plan before the run; the prompt shows the phases and lets the user read the script.
- (2nd pass) More limits from the same page: at most 4,096 items in one `parallel()` or `pipeline()` call; an advisory "large workflow" warning past 25 agents or a projected 1.5 million tokens; no module imports and no file or shell access from the script itself, only from the agents it starts. A failed agent in the middle of a fan-out makes every agent started after it rerun on relaunch, even finished ones.
- (2nd pass) When a subscription usage limit is hit, the run pauses and continues after the reset, at most twice per run, only in interactive sessions.
- (2nd pass) The docs place the four options by who holds the plan: subagents, skills and agent teams leave it with the model turn by turn; a workflow moves it into the script, with intermediate results in script variables instead of the context window. Stated scale: dozens to hundreds of agents per run.

### 1.4 What Anthropic says about frameworks, in one paragraph

Three stages, described in "Building with Claude Managed Agents" (10 Jun 2026) [V]: write your own loop on the API if you need full control; use the Agent SDK if you want Claude Code's loop inside something you host; use Managed Agents if you want hosting, credential isolation and a harness that is retuned for each model. Their stated view is that for most organisations maintaining a harness does not differentiate the product. No third-party graph framework is recommended anywhere in their current material.

---

## 2. OpenAI

### 2.1 Codex: the harness

Stack [M]: `openai/codex`, Apache-2.0, 136,051 stars, about 98% Rust by bytes, latest release `rust-v0.171.0` on 20 Nov 2026.

"Unrolling the Codex agent loop" (23 Jan 2026, Michael Bolin) [V]:

- One loop: the model returns either a final message or a tool call; the harness runs the tool, appends the output, and asks again.
- Requests are stateless. The full history is sent every time, to support zero-data-retention customers. Cost stays linear because of prompt caching, which requires an identical prefix; so tools, model and sandbox settings are never changed mid-conversation, changes are appended as new messages.
- Compaction is a server endpoint that returns a shorter item list, called automatically past a token limit.
- AGENTS.md files are not put in the system prompt. They are collected from the home directory and from the repository root down to the working directory, into one user-role message, 32 KiB by default.
- The sandbox covers the built-in shell tool only. Tools from MCP servers are not sandboxed by Codex.

"Unlocking the Codex harness" (4 Feb 2026, Celia Chen) [V]:

- All surfaces (terminal, IDE, desktop, web) share the Rust core through the App Server, a long-lived process speaking a JSON-RPC variant over stdio.
- Three primitives: item (one unit of input or output), turn (one unit of agent work), thread (a durable conversation that can be resumed, forked, archived).
- Human approval is part of the protocol: the server sends the client a request and the turn pauses until allow or deny.
- They first tried exposing Codex as an MCP server and dropped it, because rich session events did not map onto MCP.
- On the web, the App Server runs in a container managed by a worker and state is kept server-side, so work continues when the tab closes.

Cloud tasks (legacy environment docs) [V]: one container per task from a default image; a setup script runs with network access; the agent phase starts offline by default behind a proxy; secrets are removed before the agent phase; container state is cached up to 12 hours. In September 2026 environments became reusable across devices [S, TechCrunch].

### 2.2 "Harness engineering"

Post of 11 Feb 2026 by Ryan Lopopolo [V]. An internal product built with no hand-written code: about one million lines, about 1,500 merged pull requests, five months, three engineers growing to seven, about 3.5 pull requests per engineer per day.

What the humans built instead of code:

- **AGENTS.md as a map.** About 100 lines pointing into a structured `docs/` tree (design docs, active and completed execution plans, product specs, quality and reliability scorecards). Linters check that the docs stay current and cross-linked.
- **Architecture enforced mechanically.** A fixed layer order per domain, custom linters and structural tests, and lint messages that include the fix so the agent can repair itself.
- **An environment the agent can see.** The app boots per git worktree; Chrome DevTools Protocol lets the agent reproduce and check UI bugs; a throwaway local logs/metrics/traces stack is queryable by the agent.
- **Review and merge.** Mostly agent-to-agent; human review optional; short-lived pull requests; flaky tests rerun rather than block.
- **Garbage collection.** Recurring background agents scan for drift from stated principles and open small refactoring pull requests; another keeps docs fresh.

Lessons stated: give the agent a map, not a manual; enforce invariants, not implementations; anything the agent cannot reach from the repository does not exist for it. They flag that this depends on heavy tooling investment and that long-term architectural coherence is an open question.

A companion developer post describes a single run of about 25 hours, 13 million tokens and 30,000 lines, held on course by four Markdown files: a frozen spec, a milestone plan with validation commands, a runbook, and a live status log [V; date not shown on page].

### 2.3 Symphony: tickets to runs

`openai/symphony` [M]: created 26 Feb 2026, 28,121 stars, reference implementation in Elixir, last push 15 Sep 2026, labelled an engineering preview for trusted environments. The repository ships a 2,312-line `SPEC.md` and invites teams to have an agent implement it in any language.

What the spec specifies [M, read directly]:

- A daemon polls an issue tracker (Linear in the demo), creates one isolated workspace per issue, and runs a coding-agent session in it.
- The policy lives in the repository in `WORKFLOW.md`: YAML front matter for tracker, polling, hooks and limits, and a Markdown body that is the per-issue prompt template. It is hot-reloaded.
- One authoritative in-memory orchestrator state; reconciliation against the tracker on every tick, before dispatch.
- Retries with exponential backoff: 10 seconds doubling per attempt, capped at 5 minutes by default. A stalled worker is killed and requeued.
- No database. After a restart, state is rebuilt from the tracker and the filesystem.
- A run may end in a workflow-defined handoff state such as *Human Review* instead of *Done*. Approval and sandbox posture are left to each implementation but must be documented, and an approval request must never stall a run forever.

This is the closest public artefact from a lab to a ticket-to-pull-request harness, and it is a plain state machine, not a graph framework.

### 2.4 Agents SDK and AgentKit

- **Agents SDK** [M]: `openai/openai-agents-python`, 30,800 stars, v0.25.0 on 18 Nov 2026. Release of 15 Apr 2026 [V]: a model-native harness with Codex-style file tools, native sandbox execution with seven named providers (Blaxel, Cloudflare, Daytona, E2B, Modal, Runloop, Vercel), a manifest describing the workspace, snapshot and rehydration so a lost container does not lose the run. Python first. Their framing: model-agnostic frameworks are flexible but do not fully use frontier models.
- **Human approval** in the SDK [V, docs]: a tool is marked as needing approval; the run stops with an interruption; the run state is serialised to JSON and resumed later after approve or reject. The docs warn that approval does not give exactly-once execution, so side effects need idempotency keys.
- **AgentKit** (6 Oct 2025) [V]: a visual canvas (Agent Builder), an embeddable chat kit, evals, a connector registry, guardrails. An update dated 3 Jun 2026 on the same page says Agent Builder and Evals are being wound down and leave the platform after 30 Nov 2026; code workflows are sent to the Agents SDK. The visual workflow builder lasted about fourteen months.

### 2.5 Infrastructure they name

- **Temporal.** A Codex engineer is quoted on Temporal's blog (17 May 2025) saying Temporal executes Codex's core control flows [V, via Temporal's site, not an OpenAI page]. Temporal also ships an integration that runs Agents SDK agents as durable workflows, generally available 23 Mar 2026, and a sandbox extension built with OpenAI (16 Apr 2026) [V, Temporal].
- (2nd pass) A second Temporal post (12 Nov 2025, Mason Egger and Steve Androulakis) states that the Codex web agent is built on Temporal, with no link to an OpenAI source [V, Temporal]. OpenAI's own Agents SDK announcement of 15 Apr 2026 does not mention Temporal; it describes durability as snapshot and rehydrate.
- (2nd pass) Local sandbox and approvals [V, Codex docs as surfaced in search]: the sandbox sets the technical boundary and a separate approval policy says when to stop and ask; macOS uses Seatbelt. OpenAI's alignment blog (April 2026) reports that an "auto-review" mode stops for a human about 200 times less often than manual mode [V, figure seen in a search summary only].
- A conference talk on how OpenAI uses Temporal is listed in search results but the page returned 404: **not found**.
- No OpenAI-authored description of the Codex cloud control plane was found.

---

## 3. Google

- **Jules** (asynchronous coding agent) [V unless marked]: each task clones the repository into a fresh cloud VM, shows a plan before editing, then opens a pull request. A changelog entry of 26 Jan 2026 adds a *Planning Critic*, a second agent that reviews plans that skip human approval, with a reported 9.5% drop in task failures. Jules is being shut down: the changelog carries an entry titled "Jules Turndown" dated 29 Oct 2026 [M, title seen]. (2nd pass) The entry itself gives the dates: sessions can be finished until 11 Nov 2026, read-only after that, wind-down on 31 Dec 2026; it calls Jules an experiment whose lessons feed other Google products including Antigravity [V, changelog]. Press adds that Antigravity has no announced hosted asynchronous tasks yet [S].
- **Antigravity** [V, docs overview]: one shared harness, described as co-trained with Gemini models, behind a desktop app for orchestrating agent teams, a CLI (`agy`), IDE extensions and a Python SDK. Subagents work in isolated git worktrees. Agents emit *artifacts* (plans, diffs, browser recordings) for review. Tool approval gates and directory scoping are configurable. A developer guide describes a Python control plane over a bundled Go harness that runs the loop [S].
- **Gemini CLI** [M]: `google-gemini/gemini-cli`, TypeScript, 108,970 stars, v0.70.0 on 19 Nov 2026. Split into a terminal front end and a core package that talks to the model and schedules tools [S; the official architecture page could not be fetched]. (2nd pass) Google announced on 19 May 2026 that Gemini CLI is being replaced by Antigravity CLI: consumer plans stopped being served on 18 Jun 2026, while paid API keys and enterprise licences keep access; skills, hooks, subagents and extensions carry over, without full parity at first [V, Google Developers Blog, via search summary]. The open-source repository is still released weekly [M]. Press reports the new CLI is written in Go and was not open source at launch [S, The Register].
- (2nd pass) **Antigravity SDK** (19 May 2026) [V]: a Python library in research preview, Apache 2.0, exposing the same runtime as the app and the CLI. Nine hook points in three kinds (inspect, decide, transform); child agents with their own tools and context; policies declared as deny, allow or ask-user, with shell execution denied by default; local only for now, remote deployment on Google Cloud planned.
- **ADK (Agent Development Kit)**, the framework Google gives customers [M]: `google/adk-python` 22,296 stars, v2.15.0 on 19 Nov 2026; Go 8,992 stars; Java 1,778. Version 2 moved to a graph engine. The ADK Go 2.0 announcement (30 Jun 2026) [V]: nodes and edges, routing, fan-out and fan-in, loops, per-node retries with backoff and timeouts; any node can pause for human input; run state lives in the session and a paused workflow is rebuilt by scanning session history, even after a restart. Their rationale: real applications branch, wait for approval, retry and loop, and writing that as ad-hoc control flow becomes brittle; the model makes the decision and the graph makes it resumable and observable.

Note the split: Google sells a graph engine to customers, while its own coding products are described as a loop-style harness. Whether Antigravity or Jules use ADK internally: **not found**.

---

## 4. Microsoft and GitHub

- **Copilot coding agent** [V, GitHub docs]: runs in a GitHub Actions environment or a cloud sandbox; one branch and one pull request per task; a hard limit of 59 minutes per Actions-based session; firewall allowlists; customised through instructions, custom agents, skills, MCP servers and hooks. It can be blocked by branch rules like any contributor.
- **Agent HQ** (28 Oct 2025) [V]: GitHub as the place where agents from several vendors are assigned and watched (*mission control*), with a control plane for policy, identity, audit and metrics, and AGENTS.md-based custom agents. Third-party agents from Anthropic and OpenAI reached preview in February 2026 [S].
- **GitHub Agentic Workflows** (`gh-aw`) [M]: Go, 5,671 stars, v1.2.2 on 10 Nov 2026; technical preview since 13 Feb 2026, public preview on 11 Jun 2026, generally available on 28 Oct 2026 for Free, Team and Enterprise (2nd pass) [V, GitHub changelog; the docs page still said public preview in one search result]. The GA note adds a dedicated threat-detection job that scans proposed changes before they are applied, and micro-VM isolation options. A workflow is a Markdown file with YAML front matter. `gh aw compile` turns it into a locked GitHub Actions file. Engines: Copilot, Claude Code, Codex, Gemini, Pi.
  - Security design (post of 9 Mar 2026) [V]: the agent is assumed untrustworthy. It runs read-only in its own container with no secrets; model traffic goes through a proxy that holds the keys; MCP servers run behind a separate gateway; network is firewalled.
  - Writes are staged: the agent can only *propose* outputs (an issue, a comment, a pull request). After the agent exits, deterministic checks filter, cap, sanitise and strip secrets before anything is applied. GitHub calls this *safe outputs*.
  - Every boundary logs, on the principle that any point where traffic can be observed is a point where it can be controlled.
- **Microsoft Agent Framework 1.0** (3 Apr 2026) [V, from the announcement as surfaced in search; page not read in full]: .NET and Python; a graph-based workflow engine with checkpointing, human approvals and pause/resume; checkpoints on local disk or Cosmos DB.

Same split as Google: a graph framework for customers, and for GitHub's own agent automation a compile step onto an existing CI runner with deterministic gates.

---

## 5. Amazon

- **Kiro specs** [V, Kiro docs]: a feature becomes three files, `requirements.md` (or `bugfix.md`, which records current, expected and unchanged behaviour), `design.md` and `tasks.md`. The user reviews each. Running all tasks builds a dependency graph and executes in waves: waves in sequence, tasks inside a wave in parallel. A "quick" mode skips the approval gates. Steering files hold project conventions and hooks fire on events such as file save [S].
- **Frontier agents** (2 Dec 2025) [V]: the Kiro autonomous agent keeps context across sessions, learns from review feedback, works across repositories and proposes pull requests that humans merge. Amazon's stated internal lessons: point agents at goals rather than steps, and longer autonomous stretches gave better results.
- Later launches: Kiro Crew (August 2026) and Kiro bots (November 2026) for scheduled, multi-agent work [S].
- **Q Developer**: its CLI was succeeded by Kiro CLI; new sign-ups blocked from 15 May 2026 and end of support on 30 Apr 2027 [S]. The repository `aws/amazon-q-developer-cli` is Rust, 1,985 stars, last pushed 24 Aug 2026 and not flagged archived on GitHub [M], which differs from one secondary source that calls it archived.
- (2nd pass) **Kiro autonomous agent** (Kiro blog, 2 Dec 2025, updated for Kiro Web preview) [V]: each task runs in its own isolated sandbox, set up from the repository's Dockerfile or DevFile, with configurable network access (integrations only, package registries, open, or a custom allowlist). Three sub-agents: research and planning, coding, verification. It asks questions when unsure, opens pull requests that people approve, and runs up to 10 tasks at once. A separate local sandbox for shell commands arrived in Kiro CLI 2.31, with a warning that it cannot guarantee full isolation [S, search summary of the changelog].
- Engine, sandbox technology (which hypervisor or container runtime) and orchestration behind Kiro's autonomous agent: **not found**.

---

## 6. Cursor

Three posts give the most concrete infrastructure account of any company here.

**Research harness** ("Scaling long-running autonomous coding", 14 Jan 2026, and "Towards self-driving codebases", 5 Feb 2026, both by Wilson Lin) [V]:

- The harness is written in Rust and first ran on one large Linux VM.
- What failed: equal agents coordinating through a shared file; locks (twenty agents fell to the throughput of two or three); optimistic concurrency. Agents became risk-averse and avoided hard work.
- What worked: recursive planners that own scope and write no code; workers that each take one task on their own copy of the repository and return a single written handoff; no cross-worker communication. An integrator role and a rigid judge stage were both removed as bottlenecks.
- Scale reported: hundreds of concurrent agents, about 1,000 commits per hour at peak, about 10 million tool calls in a week, a browser of over a million lines.
- Lessons stated: the right amount of structure is in the middle; prompts mattered more than harness or model; accept a small steady error rate and fix up at the end rather than demand a green build on every commit; hard constraints work better than reminders; pick the model per role.

**Production cloud agents** ("What we've learned building cloud agents", 2 Jun 2026, Josh Ma) [V]:

- First design: worker nodes picked up agents and looped them to completion. Reliability was about one nine.
- They moved to **Temporal** rather than rebuild retries, cross-machine scheduling and durability. Reported after: past two nines, more than 50 million actions per day across more than 7 million workflows, more than 40% of Cursor's own pull requests from cloud agents.
- **The agent loop runs in Temporal, not on the VM.** That lets VMs be hibernated, prewarmed or read-only independently.
- Workflows were changed from long-lived to short ones that exit after a task, which makes version upgrades easier.
- Conversation state is a separate append-only store that streams to clients; when a step is retried, clients rewind.
- The biggest factor in output quality is a full development environment. Failures show up as quiet quality drops, not errors.
- Early harness logic that forced a check, commit and push after every task was moved into tools the agent chooses to call.
- Isolation: Firecracker-based microVMs in an AWS account separate from the rest of production [V, security docs as surfaced in search].

Human approval inside cloud runs is not described in these posts.

---

## 7. Cognition (Devin)

- **Position in 2025** ("Don't Build Multi-Agents", 12 Jun 2025, Walden Yan) [V]: share full context and full traces between agents, and remember that every action carries implicit decisions, so parallel actors conflict. Recommended shape: one linear agent, with a dedicated model that compresses history when it grows. Frameworks that push multi-agent designs (OpenAI Swarm, Microsoft AutoGen) are named as pushing the wrong idea.
- **Position in 2026** ("Multi-Agents: What's Actually Working", 22 Apr 2026) [V]: narrowed, not reversed. What works keeps writes single-threaded and uses other agents for intelligence:
  - a reviewer with clean context (reported: about two bugs found per pull request, about 58% severe);
  - a smaller model that escalates to a stronger one;
  - a manager that splits work and coordinates child Devins through an internal MCP server.
  Parallel-writer swarms still see little real adoption. Their conclusion is that the open problems are communication problems.
- **Infrastructure** ("What We Learned Building Cloud Agents", 23 Apr 2026; blockdiff post) [V]: one microVM per session with its own kernel, on a hypervisor they built themselves over more than a year; snapshots capture memory, processes and disk; an orchestration layer that took more than three quarters manages warm pools, crash recovery and teardown; compute shuts down while the agent waits and resumes when a CI result or review comment arrives; sessions inherit the permissions of the engineer who dispatched them; all actions go to an audit trail. Their snapshot tool is open source and written in Rust (`CognitionAI/blockdiff`, 264 stars [M]).
- (2nd pass) Detail from the April 2026 post [V]: the reviewer deliberately starts without the coder's context and reads only the diff; the coder's knowledge of the user's instructions is then used to filter the findings and stop loops. Child agents often assume shared state they do not have, so cross-agent messages have to be designed. An AWS architecture post adds that macOS sessions each get a fresh VM on EC2 Mac hosts and that idle sessions are snapshotted and stopped [S, search summary; page body not readable].
- **Devin Bots** (November 2026): agents that manage teams of Devins over weeks; review effort and failure rates were not disclosed [S, Fortune].
- Lessons stated: containers that share a kernel are a security risk for agent workloads; building this in-house means owning orchestration, governance and integrations for good.
- Graph framework: none named. Workflow engine: **not found**.

---

## 8. Factory (Droid)

- **Missions** (26 Feb 2026) [V]: an orchestrator splits a project into milestones and features; each feature gets a fresh worker session; git is the source of truth; each milestone ends with a validation phase that runs tests and clicks through the app. The user scopes and approves the plan in conversation before the run, then watches from a control view. Reported: median mission about 2 hours, 14% over 24 hours, longest 16 days, about 12x the tokens of a normal session. Different model per role (planning, implementation, validation, research). Lesson stated: serial execution with targeted parallelism beat broad parallelism.
- **Droid 1.0** (29 Oct 2026) [V]: the harness is model-independent; an automation tracks more than 20 models and checks each against behavioural assertions before human QA. *Script mode* lets the model write JavaScript that makes many tool calls in one request inside a sandbox with no file or network access of its own. Upfront tool definitions went from 11 to 2, with the rest loaded on demand; the base prompt fell 37%. About 98% of production input is read from cache. Lesson stated: a change that helps one model can hurt another, so harness options are per model.
- (2nd pass) **Missions docs** [V]: the stated sweet spot is about 1 to 500 features per mission; the repository should first reach "Agent Readiness Level 4", because validation needs a scriptable way to use the app as a user would; missions are described as not fire-and-forget, and the user can pause the orchestrator to redirect it.
- (2nd pass) **Context work** [V]: a Factory-run evaluation of 16 Dec 2025 scored its structured summaries 3.70 out of 5 against 3.44 for Anthropic's and 3.35 for OpenAI's built-in compaction, and argues for counting tokens per finished task, not per request. A post of 20 May 2026 describes loading tool schemas and skills only when needed: 16.6% of sessions started MCP servers but only 5.4% called an MCP tool [figures from search summaries].
- Core language, workflow engine and sandbox for workers: **not found** (a TypeScript SDK and Bun are mentioned).

---

## 9. Sourcegraph Amp

- 23 Oct 2025 [V]: Amp removed compaction and replaced it with *handoff*: state a goal, and Amp drafts a prompt and file list for a new thread. Reason given: summaries are lossy and encourage long, wandering threads.
- 6 May 2026 [V]: the rebuilt CLI reversed this. It compacts automatically at 90% of the window, and handoff was removed as obsolete. The same release removed permission prompts by default (their argument: checking tool names and arguments gives weak protection once models write scripts), removed file rollback, and added a plugin API and remote control of threads from the web.
- September 2026: users can no longer pin a model for the oracle (a second-opinion reasoning tool) or for subagents [S, from a search summary of Amp's news feed].
- Lesson stated: build for what current models can do and delete features that tie users to last year's workflow.
- Language, engine, sandbox, and current corporate relationship to Sourcegraph: **not found**.

---

## 10. Replit

- **The one confirmed graph-framework user in this list.** A LangChain case study (around 2024) describes Replit Agent as built on LangGraph with LangSmith tracing, using a manager agent, editor agents and a verifier that can ask the user; changes are committed automatically at each major step so users can roll back [V, LangChain's site].
- **Temporal** published a case study (September 2025) saying Replit orchestrates its coding agents on Temporal [V, Temporal's site].
- **Decision-time guidance** (20 Jan 2026) [V]: instead of a longer system prompt, a cheap classifier inspects each iteration and injects short, temporary reminders at the end of the trace. The core prompt stays fixed, which preserves caching (reported 90% cost saving against editing the system prompt). On a detected loop, a different model writes a fresh plan.
- (2nd pass) **Self-testing** (15 Dec 2025) [V]: testing runs in a separate subagent so it does not pollute the main context (often 80,000 to 100,000 tokens). The subagent writes and runs Playwright code in a notebook-style session that keeps browser state between steps, and returns a summary of what works and what is broken. Reported: median $0.20 per testing session, autonomous run length up from about 20 to over 200 minutes. The target is features that look finished but are mocked underneath.
- **Agent 4** (March 2026) [V]: parallel tasks run in isolation; dependencies are ordered first; conflicts are resolved automatically about 90% of the time.
- Whether Agent 4 still runs on LangGraph: **not found**.

---

## 11. Vercel (v0)

- "How we made v0 an effective coding agent" (7 Jan 2026, Max Leiter) [V]: three additions around the model. A dynamic system prompt injects version-specific library knowledge. A streaming rewriter fixes known errors as text arrives (for example, replacing icon names that do not exist) in under 100 ms. Autofixers run after generation, combining deterministic fixes, syntax-tree parsing and a small fine-tuned model, in under 250 ms. Raw model output fails about 10% of the time by their account. Lesson stated: fix deterministically wherever possible; each stage targets one failure mode.
- Vercel sells its own durable-execution layer (the Workflow SDK, with a `"use workflow"` directive and a `WorkflowAgent` class that puts the AI SDK loop inside a durable workflow) and microVM sandboxes [V, docs as surfaced in search].
- Whether v0 itself runs on the Workflow SDK, and its GA status: **not found**.

---

## 12. Manus

"Context Engineering for AI Agents" (18 Jul 2025, Yichao "Peak" Ji) [V]. The site now carries a banner saying Manus is part of Meta. No dated 2026 revision of the essay was found.

- Bet on in-context learning with frontier models instead of training their own, so improvements ship in hours.
- The agent framework was rebuilt four times.
- Cache hit rate is the key production metric: input outweighs output about 100 to 1, and a typical task takes about 50 tool calls. So: stable prefix, append-only context, deterministic serialisation.
- Do not add or remove tools mid-task; constrain which may be chosen instead.
- Use the file system as memory; drop bulky content but keep the path or URL so it can be restored.
- Rewrite a `todo.md` as work proceeds so the goal stays at the end of the context.
- Keep failed actions in context so the model learns from them; vary formatting so the model does not imitate a rut.
- Sandbox: one cloud VM per task, on E2B's Firecracker microVMs [V, E2B's case study].

---

## 13. Side-by-side

| Company | Core language | Graph framework for own agent? | Durable execution / state | Sandbox | Human gate | Evidence |
|---|---|---|---|---|---|---|
| Anthropic (Claude Code, Managed Agents) | TypeScript | No. Plain loop; scripts for fan-out | JSONL session files locally; append-only event log in Managed Agents; saved results in workflows | bubblewrap / seatbelt locally; managed VMs in cloud | Permission modes; plan approval before a workflow; PR | [M] language, [V] rest |
| OpenAI (Codex) | Rust | No. Plain loop; Symphony is a state machine | Threads persisted by App Server; Temporal for control flows | OS sandbox for shell; container per cloud task | Approval requests pause the turn; PR; review optional in their own team | [M] language, [V] rest |
| Google (Antigravity, Gemini CLI) | TypeScript (CLI); Go harness reported | Not for own tools, as far as stated. ADK 2 is a graph engine for customers | ADK: state in session, replay from history | Terminal sandbox; cloud VM (Jules) | Plan approval; tool gates; artifacts | [M] CLI, [V]/[S] rest |
| GitHub (Copilot agent, gh-aw) | Go (gh-aw) | No. Markdown compiled to Actions YAML | GitHub Actions run; 59-minute cap | Actions container, firewall, zero secrets | Staged writes vetted after the run; PR review | [M] language, [V] rest |
| Microsoft (Agent Framework) | .NET, Python | Yes, as a product for customers | Checkpoints (disk or Cosmos DB) | n/a | Approvals inside workflows | [V] |
| Amazon (Kiro) | Not found | Not found | Specs as files; persistent context | Not found | Review of each spec phase; PR | [V]/[S] |
| Cursor | Rust (research harness) | No | Temporal; append-only conversation store | Firecracker microVMs | Not described | [V] |
| Cognition | Rust (snapshot tool) | No; critical of multi-agent frameworks | VM snapshots; sleep and wake on events | Own hypervisor, microVM per session | Reviewer agent, then human PR review; audit trail | [V] |
| Factory | Not found | Not stated | Git as source of truth | Script sandbox | Plan approval before a mission | [V] |
| Amp | Not found | Not stated | Server-side threads | Not found | Prompts removed by default | [V] |
| Replit | Not found | Yes, LangGraph (historically) | Temporal; automatic commits | Not found | Verifier asks the user | [V via partners] |
| Vercel v0 | TypeScript ecosystem | No (pipeline) | Workflow SDK exists; use by v0 not found | microVM sandbox product | n/a | [V] |
| Manus | Not found | Not stated; framework rebuilt four times | Files in the sandbox | E2B Firecracker microVM | n/a | [V] |

---

## 14. Patterns that recur in at least three companies

**P1. A plain loop in ordinary code, not a graph, for the company's own agent.**
Anthropic, OpenAI, Cursor, Cognition, Factory, Amp, Manus. The only confirmed exception is Replit's early use of LangGraph. Anthropic dropped LangGraph from its own list of frameworks. Google and Microsoft ship graph engines, but as products for customers who need explicit branching, approval and resume in business processes.

**P2. Durable execution under the loop.**
Temporal at OpenAI Codex, Cursor and Replit. An event log at Anthropic. Session replay in ADK. Saved-result replay in Claude Code workflows. Snapshot and rehydrate in OpenAI's Agents SDK. The loop itself stays simple; what is bought or built is the thing that survives a crash. Cursor's numbers (one nine to two nines) are the only quantified before-and-after found.

**P3. Brain, hands and history are separate.**
Anthropic (brain, hands, session), OpenAI Agents SDK (harness and compute), Cursor (loop in Temporal, VM apart, conversation store apart), GitHub (agent container, gateway, proxy). The gains reported are recovery, faster starts and the ability to swap any part.

**P4. Credentials never enter the sandbox.**
Anthropic (git proxy, vault), OpenAI (secrets removed before the agent phase; harness and compute split), GitHub (zero-secret agent, API proxy, MCP gateway), Cursor (secret redaction, separate account). Symphony's spec says the same of tracker credentials.

**P5. Files and git are the memory.**
Anthropic (feature list, progress file, commits), OpenAI (four Markdown files; `docs/` as system of record), Factory (git as source of truth), Manus (`todo.md`, files as context), Kiro (three spec files), Cursor (written handoffs), Symphony (`WORKFLOW.md`, recovery from the filesystem).

**P6. A short instruction file that points elsewhere.**
OpenAI (about 100 lines of AGENTS.md as a map), Anthropic (CLAUDE.md under 200 lines, details in skills), Kiro (steering files), GitHub (AGENTS.md and custom agents). Long instruction files are described as crowding out context and going stale.

**P7. Fresh context per unit of work, with a written handoff.**
Anthropic (one feature per session; sprint contracts), Cursor (one task per worker, one handoff), Factory (one feature per worker session), Cognition (clean-context reviewer). Amp tried handoff-only, then went back to compaction: the mechanism is model-dependent, the need is constant.

**P8. Split roles, but keep writes isolated or single-threaded.**
Planner, worker and checker roles appear at Anthropic, Cursor, Factory, Cognition, Google (Planning Critic) and Replit. Where several agents write, each gets its own copy (Cursor's repo copies, Claude Code and Antigravity worktrees, Replit's isolated tasks). Shared-file coordination and locks failed at Cursor; Cognition still advises against parallel writers; Factory found mostly-serial execution better.

**P9. Deterministic checks first, a model as judge last, and test by running the product.**
Anthropic (rules over judges; Playwright), OpenAI (custom linters with fix instructions; DevTools; observability), Vercel (deterministic autofix before any model call), GitHub (deterministic vetting of staged writes), Factory (validators click through the app), Kiro (property-based tests).

**P10. Humans approve the plan and the result, not each step.**
Plan approval: Jules, Kiro, Factory, Claude Code workflows, Copilot plan mode. Result approval: a pull request everywhere; a *Human Review* state in Symphony. Mid-run questions are designed out: Claude Code workflows forbid them, Cursor prompts cloud agents for autonomy because a blocked agent idles for hours, Symphony forbids indefinite stalls. Per-tool approval survives for local interactive use (Codex, Claude Code, OpenAI Agents SDK) and is being relaxed (Amp removed it by default; Claude Code defaults to a classifier).

**P11. Design around the prompt cache.**
OpenAI (never change tools or model mid-thread), Manus (stable prefix, append-only), Anthropic (same advice; shared cache across sibling agents), Replit (static core prompt, temporary reminders), Factory (98% of input from cache).

**P12. Delete harness parts as models improve.**
Anthropic (context resets, then sprints removed), Cursor (forced checks moved into tools; integrator and judge removed), Amp (handoff, rollback and prompts removed), Manus (four rebuilds), OpenAI (AgentKit's visual builder wound down in favour of code). The stated consequence at Anthropic and Cursor is the same: the harness does not disappear, its contents change.

**P13. Rust, or TypeScript, for the harness; no Python at the core.**
Rust: OpenAI Codex [M], Cursor's research harness [V], Cognition's snapshot tooling [M], Amazon's Q CLI [M]. TypeScript: Claude Code [M], Gemini CLI [M]. Go: gh-aw [M], Antigravity's harness [S]. Elixir: Symphony [M]. Python appears in the SDKs offered to customers (OpenAI Agents SDK, ADK, Microsoft Agent Framework), not in the labs' own agents.

**P14. Small evals from real failures, run per model.**
Anthropic (20 to 50 tasks; read transcripts), Factory (behavioural assertions across 20+ models), Vercel (autofix model trained on real generations), Cursor (empirical over assumed). No company describes a large upfront benchmark as the starting point.

---

## 15. Not found, or weakly sourced

- An OpenAI-authored account of the Codex cloud control plane. Temporal's role rests on a quotation hosted by Temporal.
- The conference talk on OpenAI's use of Temporal (page returned 404).
- Whether Antigravity or Jules are built on ADK.
- Kiro's engine, sandbox and orchestration.
- Whether Replit Agent 4 still uses LangGraph.
- Whether v0 runs on Vercel's Workflow SDK, and that SDK's GA status.
- The languages and engines behind Factory's, Amp's and Manus's harness cores.
- Gemini CLI's official architecture page (404 at the path tried); details here are secondary.
- Microsoft Agent Framework details come from search summaries of the announcement, not a full read.
- How any company handles human approval in the middle of a long cloud run, beyond "we avoid it".
- Independent verification of any vendor productivity figure (lines of code, pull-request shares, failure reductions). All are self-reported.

---

## Sources

Anthropic
- https://www.anthropic.com/engineering/building-effective-agents (19 Dec 2024; live page read 2026-11-21)
- http://web.archive.org/web/20250305014737/https://www.anthropic.com/engineering/building-effective-agents (archive, 5 Mar 2025)
- https://www.anthropic.com/engineering/multi-agent-research-system (13 Jun 2025)
- https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents (29 Sep 2025)
- https://claude.com/blog/building-agents-with-the-claude-agent-sdk (29 Sep 2025)
- https://www.anthropic.com/engineering/claude-code-sandboxing (20 Oct 2025)
- https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents (26 Nov 2025)
- https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents (9 Jan 2026)
- https://www.anthropic.com/engineering/building-c-compiler (5 Feb 2026)
- https://www.anthropic.com/engineering/harness-design-long-running-apps (24 Mar 2026)
- https://claude.com/blog/harnessing-claudes-intelligence (2 Apr 2026)
- https://claude.com/resources/articles/harnessing-claudes-intelligence (same article, URL fetched in the 2nd pass)
- https://www.anthropic.com/engineering/managed-agents (8 Apr 2026)
- https://claude.com/blog/building-with-claude-managed-agents (10 Jun 2026)
- https://code.claude.com/docs/en/how-claude-code-works.md
- https://code.claude.com/docs/en/features-overview
- https://code.claude.com/docs/en/agents
- https://code.claude.com/docs/en/workflows.md
- https://code.claude.com/docs/en/claude-code-on-the-web.md
- https://github.com/anthropics/claude-code
- https://github.com/anthropic-experimental/sandbox-runtime
- https://newsletter.pragmaticengineer.com/p/how-claude-code-is-built (secondary)

OpenAI
- https://openai.com/index/unrolling-the-codex-agent-loop/ (23 Jan 2026)
- https://openai.com/index/unlocking-the-codex-harness/ (4 Feb 2026)
- https://openai.com/index/harness-engineering/ (11 Feb 2026)
- https://developers.openai.com/blog/run-long-horizon-tasks-with-codex
- https://openai.com/index/the-next-evolution-of-the-agents-sdk/ (15 Apr 2026)
- https://openai.com/index/introducing-agentkit/ (6 Oct 2025; update note of 3 Jun 2026)
- https://openai.github.io/openai-agents-python/human_in_the_loop/
- https://learn.chatgpt.com/docs/environments/cloud-environment (legacy Codex cloud environment docs)
- https://github.com/openai/codex
- https://github.com/openai/symphony and https://raw.githubusercontent.com/openai/symphony/main/SPEC.md
- https://github.com/openai/openai-agents-python
- https://temporal.io/blog/improving-java-sdk-codex-openai (17 May 2025; Temporal's site)
- https://temporal.io/blog/introducing-temporal-and-agentic-sandboxes-openai-agents-sdk (16 Apr 2026; Temporal's site)
- https://techcrunch.com/2026/09/29/openai-gives-codex-reusable-cloud-environments-that-work-across-devices/ (secondary)
- https://temporal.io/blog/of-course-you-can-build-dynamic-ai-agents-with-temporal (12 Nov 2025; Temporal's site)
- https://developers.openai.com/codex/concepts/sandboxing
- https://alignment.openai.com/auto-review (April 2026; seen in search summary)

Google
- https://jules.google/docs/changelog/2026-01-26-1/
- https://jules.google/docs/changelog/ ("Jules Turndown", 29 Oct 2026)
- https://developers.googleblog.com/an-important-update-transitioning-gemini-cli-to-antigravity-cli/ (19 May 2026)
- https://antigravity.google/blog/introducing-google-antigravity-sdk/ (19 May 2026)
- https://www.theregister.com/ai-ml/2026/05/20/bye-bye-gemini-cli-google-nudges-devs-toward-antigravity/5243605 (secondary)
- https://www.timesofai.com/news/google-jules-antigravity/ (secondary, shutdown dates)
- https://antigravity.google/docs/overview/
- https://developers.googleblog.com/announcing-adk-go-20/ (30 Jun 2026)
- https://github.com/google/adk-python
- https://github.com/google/adk-go
- https://github.com/google-gemini/gemini-cli
- https://www.linkedin.com/pulse/google-antigravity-sdk-developer-guide-karl-weinmeister-nymsc (secondary)

Microsoft and GitHub
- https://docs.github.com/en/copilot/concepts/agents/coding-agent/about-coding-agent
- https://github.blog/news-insights/company-news/welcome-home-agents/ (28 Oct 2025)
- https://github.github.com/gh-aw/introduction/overview/
- https://github.blog/ai-and-ml/generative-ai/under-the-hood-security-architecture-of-github-agentic-workflows/ (9 Mar 2026)
- https://github.blog/ai-and-ml/github-copilot/automate-repository-tasks-with-github-agentic-workflows/ (Feb 2026)
- https://github.com/github/gh-aw
- https://github.blog/changelog/2026-02-13-github-agentic-workflows-are-now-in-technical-preview/
- https://github.blog/changelog/2026-06-11-github-agentic-workflows-is-now-in-public-preview
- https://github.blog/changelog/2026-10-28-github-agentic-workflows-generally-available
- https://devblogs.microsoft.com/agent-framework/microsoft-agent-framework-version-1-0/ (3 Apr 2026)

Amazon
- https://kiro.dev/docs/specs/
- https://kiro.dev/blog/introducing-kiro-autonomous-agent/ (2 Dec 2025)
- https://kiro.dev/changelog/cli/2-31/ (seen in search summary)
- https://www.aboutamazon.com/news/aws/amazon-ai-frontier-agents-autonomous-kiro (2 Dec 2025)
- https://siliconangle.com/2026/08/04/aws-launches-kiro-crew-autonomous-agentic-orchestrator-24-7-code-development/ (secondary)
- https://venturebeat.com/technology/aws-launches-agentic-ai-kiro-bots-with-memory-and-support-for-recurring-development-jobs (secondary)
- https://nhimg.org/amazon-q-developer-end-of-support-guide (secondary)
- https://github.com/aws/amazon-q-developer-cli

Cursor
- https://cursor.com/blog/scaling-agents (14 Jan 2026)
- https://cursor.com/blog/self-driving-codebases (5 Feb 2026)
- https://cursor.com/blog/cloud-agent-lessons (2 Jun 2026)
- https://cursor.com/docs/cloud-agent/security

Cognition
- https://cognition.com/blog/dont-build-multi-agents (12 Jun 2025)
- https://cognition.com/blog/multi-agents-working (22 Apr 2026)
- https://cognition.com/blog/what-we-learned-building-cloud-agents (23 Apr 2026)
- https://cognition.com/blog/blockdiff
- https://github.com/CognitionAI/blockdiff
- https://aws.amazon.com/blogs/architecture/ai-coding-agents-on-amazon-ec2-mac-how-cognition-scales-devin-for-macos/ (AWS's site; body not readable, search summary only)
- https://fortune.com/2026/11/17/exclusive-cognition-bets-on-devin-bots-coding-agents-in-challenge-to-anthropics-duet-and-openais-dots/ (secondary)

Factory
- https://factory.com/news/missions (26 Feb 2026)
- https://factory.com/news/frontier-harness (29 Oct 2026)
- https://docs.factory.com/features/missions/overview
- https://factory.ai/news/evaluating-compression (16 Dec 2025; seen in search summary)
- https://factory.ai/news/deferred-context-engine (20 May 2026; seen in search summary)

Amp
- https://ampcode.com/news/handoff (23 Oct 2025)
- https://ampcode.com/news/neo (6 May 2026)
- https://ampcode.com/chronicle

Replit
- https://www.langchain.com/breakoutagents/replit (LangChain's site)
- https://temporal.io/resources/case-studies/replit-uses-temporal-to-power-replit-agent-reliably-at-scale (Temporal's site)
- https://frontier.replit.com/decision-time-guidance/ (20 Jan 2026)
- https://frontier.replit.com/automated-self-testing/ (15 Dec 2025)
- https://replit.com/blog/whats-changed-agent3-to-agent4

Vercel
- https://vercel.com/blog/how-we-made-v0-an-effective-coding-agent (7 Jan 2026)
- https://vercel.com/kb/guide/durable-ai-agents
- https://vercel.com/blog/a-new-programming-model-for-durable-execution

Manus
- https://manus.im/blog/Context-Engineering-for-AI-Agents-Lessons-from-Building-Manus (18 Jul 2025)
- https://e2b.dev/blog/how-manus-uses-e2b-to-provide-agents-with-virtual-computers (E2B's site)
- https://manus.im/blog/manus-sandbox
