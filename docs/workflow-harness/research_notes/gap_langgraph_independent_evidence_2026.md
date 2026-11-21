# Gap note: independent 2026 evidence on LangGraph (adoption, removal, crash recovery, licence)

Research note, written 2026-11-21. It fills the gap listed as "not searched" in `langchain_langgraph.md` (section 9) and `gap_small_team_engine_threshold_and_cost.md` (section 3.2). It adds to those notes and does not repeat them. Web search was available for this pass.

## Summary in five lines

1. Independent first-hand reports exist but are thin. No named team was found that runs a ticket-to-PR or software-delivery workflow with human approval on LangGraph and writes about it, apart from LangChain's own Open SWE and GitLab (whose product is built on it). The best first-hand material is the LangGraph issue tracker, GitLab's own issues, and a LinkedIn talk from 2026.
2. Removals of LangGraph do exist, contrary to the earlier notes: three were found (an anonymous team to Pydantic AI plus Temporal, Grid Dynamics to Temporal, yeos.ai to plain Python classes). All three are small, two are published by or for a vendor, none gives numbers. No large named company has published a LangGraph removal.
3. The five reference customers in 2026: Uber yes (its own blog, October 2026, one legal agent), LinkedIn yes (2026 talk), GitLab yes (runbooks and issues, 2026). Klarna: nothing since February 2025. Replit: its durable orchestration moved to Temporal (2025) and then to Restate (2026); no 2026 source says LangGraph is still inside Replit Agent.
4. No rigorous independent crash-recovery benchmark against Temporal, Restate or DBOS exists. One single-author test (September 2026, stubbed model) and one open bug report with a reproduction (a race in `durability="sync"`) are the only measured items. The recurring measured problem is the same everywhere: code before a pause or inside a crashed step runs again, so side effects are duplicated unless you make them idempotent yourself.
5. The three unverified points are now settled: the default durability mode is `"async"` (read in the source at tags 1.0.0, 1.2.0 and main); the server that queues, leases and restarts runs is under the Elastic License 2.0 and needs a licence key in production; Anthropic's page did replace "LangGraph from LangChain" with "The Claude Agent SDK" between 2025-10-02 and 2025-11-30 (web archive).

## How to read this note

Labels, same as the other notes:

- **[M] measured**: read by me on 2026-11-21 in a primary artefact (source code, package registry, issue with reproduction, archived page). A user's bug report counts as measured on that user's install only.
- **[V] vendor**: said by a company about its own product or its own internal system, including case studies and conference talks.
- **[S] secondary**: a third party reporting or judging; also summaries of talks I did not watch.

Terms used:

- **Checkpoint**: a saved copy of the workflow state, written after a step. **Checkpointer**: the component that writes it (to Postgres, SQLite, Redis, memory).
- **Interrupt**: LangGraph's pause for a human. The run stops, the state is saved, and a later call resumes it.
- **Durable execution**: the guarantee that a run finishes even if the process dies, without redoing finished steps. Temporal, Restate and DBOS sell this.
- **Idempotent**: safe to run twice (the second run changes nothing).
- **Agent Server** (earlier "LangGraph Platform", now sold as "LangSmith Deployment"): LangChain's server that wraps the library with a queue, workers, an HTTP API and scheduled jobs.

## 1. First-hand accounts of teams running LangGraph (2025-2026)

### 1.1 What was found, by source quality

| Who | What they run | What they report | Label and source |
|---|---|---|---|
| GitLab (Duo Agent Platform) | A Python service that "manages and executes Duo Agent Platform sessions using LangGraph". State is kept in memory and saved through "periodic checkpoints saved to GitLab" (their own checkpointer, which posts to the Rails application). | They had to build the supervision themselves: a lock taken from Rails at start, a heartbeat every 15 s, Rails marks the run failed after 30 s without one. The reason given: a workflow could run in two places and "both be checkpointing and overwriting each others checkpoints". Issue opened 2025-06-11, closed 2026-02-16. A September 2026 bug: a failed checkpoint POST was not checked, so later incremental checkpoints were built on one that was never saved (opened 2026-09-03, closed 2026-09-08). | [V, GitLab on its own system; issue dates M] https://runbooks.gitlab.com/duo-workflow-svc/ ; https://gitlab.com/gitlab-org/gitlab/-/issues/548686 ; https://gitlab.com/gitlab-org/gitlab/-/issues/627533 |
| LinkedIn (hiring agent for small businesses) | A central planner in a plan, execute, replan loop on LangGraph. Third rebuild: static branches, then two LangChain chains, then LangGraph. Chosen after looking at 89 frameworks, mainly because their code already used LangChain building blocks. | Two details matter. They chose **not** to use LangGraph's interrupt for human review; each turn runs the graph end to end and they save only a small "pending suggestion" between turns. And they keep checkpoints minimal on purpose to control their size. They could not send production data to LangSmith, so they "built something similar internally". No mention of the paid server. | [S, ZenML summary of a 2026 LinkedIn talk; video not watched] https://www.zenml.io/llmops-database/agentic-hiring-system-reduces-time-to-interview-by-60-for-small-businesses ; [V] https://www.langchain.com/blog/previewing-interrupt-2026-agents-at-enterprise-scale (2026-04-09) |
| Uber (legal contract redlining agent) | "the back end runs a LangGraph workflow that parallelizes intent detection, risk assessment, and policy lookup". Lawyers accept, reject or modify each suggestion. | Nothing on checkpoints, durability or approval primitives. LangGraph is used here as a parallel step runner inside one request. | [V, Uber] https://www.uber.com/us/en/blog/building-ubers-redlining-agent/ (2026-10-08) |
| A LangGraph Cloud customer (Plus tier, EU), user MarioAlessandroNapoli | Deep Agents sub-agents that run 3 to 10 minutes each, on LangChain's hosted server. | Tool calls longer than about 180 s are "silently re-dispatched from the last checkpoint while the original is still running", giving "2-3x redundant work and cost". Seen on langgraph 1.1.3 to 1.1.6. They traced it to a hardcoded 120 s heartbeat and a sweep in `langgraph-api`. Open since 2026-04-05, 89 comments, no reply from an account marked member, collaborator or contributor. Several other users report the same; one reports it on self-hosted `langgraph-api` 0.8.7. Much of the thread is people promoting their own deduplication tools. | [M on that install] https://github.com/langchain-ai/langgraph/issues/7417 |
| Raed Chammam, staff engineer at Algolia (personal blog, demo, not a named production system) | An agent that creates a support ticket (automatic) and sends an email (needs approval) in one model turn. | "The ticket ran twice before the user saw anything." On resume the whole node runs again, so the tool that ran before the pause runs again. His rule: "any tool with side effects or irreversible consequences gets its own node." | [M, demo] https://raed.dev/blog/posts/langgraph-hitl/ (2026-03-15) |
| One Hacker News commenter (dragonmage65535) | "we use langgraph in production" | Considering the Claude Agent SDK instead because the coding agent needs "little guidance"; notes the SDK is heavier (a subprocess plus MCP). One sentence, no detail. | [S] https://news.ycombinator.com/item?id=46740737 (2026-01-24) |

### 1.2 What the issue tracker shows on the five points asked

The LangGraph repository had 481 open issues and 45,231 stars on 2026-11-21 [M: GitHub API]. Issues read at the source:

- **Replay re-runs side effects, by design.** A maintainer (sydney-runkle, collaborator) on 2026-06-10: this is "a natural consequence of the fact that all code pre-interrupts re-runs". Another answer on 2026-10-16 (eliornl, contributor), closing a question on recovery after a tool timeout: "a node that failed reruns from its last checkpoint on resume, so side effects need to be idempotent". [M] https://github.com/langchain-ai/langgraph/issues/7780 ; https://github.com/langchain-ai/langgraph/issues/9006
- **Checkpointer durability under `sync`.** An open bug (2026-06-10, reproduction on langgraph 1.2.4) says the order of two writes (a finished task's results, and the next checkpoint) is not enforced, so after a crash "whether resume replays them (exactly-once) or re-executes the node (duplicating its side effects) is decided by the OS thread scheduler". Still open; a fix PR (#8234) was closed. I did not run the reproduction. [M that the report and script exist; the claim itself is the reporter's] https://github.com/langchain-ai/langgraph/issues/8039
- **A crash before the first checkpoint loses the run with no trace.** Closed "not planned" on 2026-10-19 with the answer that "tracking admission belongs in the caller". In plain words: the library does not record that it accepted a run; your code or the server must. [M] https://github.com/langchain-ai/langgraph/issues/8764
- **Parallel approvals.** Resuming one of two parallel interrupts inside a subgraph re-ran a sibling step that had already finished. Reported 2026-09-29, fixed by PR #9315, closed 2026-10-15. The report lists five earlier issues with the same root cause, one fix that was reverted, and the same bug in the JavaScript version. [M] https://github.com/langchain-ai/langgraph/issues/9106
- **Maintainer capacity.** Same maintainer, 2026-06-11, on adding a guard against the interrupt trap: "we don't have a ton of resources on LG development right now". This fits the release history in `langchain_langgraph.md`: no minor release after 1.2.0 (2026-05-12), only patches up to 1.2.24. [M] https://github.com/langchain-ai/langgraph/issues/7780

### 1.3 Upgrade churn 0.x to 1.x

**Not found**: no first-hand account of a painful 0.x to 1.x upgrade. LangChain says 1.0 "maintains full backward compatibility" [V: https://www.langchain.com/blog/langchain-langgraph-1dot0]. The documented breaks are small: Python 3.9 dropped, `create_react_agent` moved to `langchain.agents` [V: https://docs.langchain.com/oss/python/migrate/langgraph-v1]. The churn that users do report in 2026 is in the layers above and beside the library (Deep Agents, `langgraph-api` versions 0.7.28 to 0.18.4 in about a year, as seen in issue 7417 and on PyPI [M]).

### 1.4 Sources I looked at and discarded

- Six near-identical dev.to posts by one author ("Three LangGraph rewrites...") give three different root causes for the same incident and two different final databases. I treat them as generated content, not evidence [S: e.g. https://dev.to/elenarevicheva/three-langgraph-rewrites-checkpointing-production-agents-3872, read through search summaries only].
- "LangGraph Checkpointing Is Not Free: A Production Postmortem" (Towards AI): the page returned HTTP 403; not read. Its claims are **not verified**.
- "Why teams migrate from LangGraph" (bswen, 2026-03-18): HTTP 403; not read; it is a summary of others in any case.
- "One missing checkpoint can break every approval gate" (dev.to, Creeta): no real incident, general advice only.
- Vendor posts that argue from documentation, not from a run: Diagrid (sells Dapr Workflows) 2026-02-25, AgentField 2026-07-02 [V, competitors].

## 2. Teams that removed or replaced LangGraph

The earlier notes said none was found. Three were found. Read them with their limits.

| Who | From | To | Reasons given | Limits | Label and source |
|---|---|---|---|---|---|
| "Jim" (personal blog, team and company not named) | LangChain and LangGraph, about eight months, in production | Pydantic AI for the agents, Temporal for durability. Rewrite took about three weeks. | A graph of nodes and edges is "the wrong abstraction for long-running tasks". Durability: "LangGraph bolted it on with 'checkpointing.' It's not native." Result claimed: "fewer lines of code, better type coverage, easier testing", fewer on-call incidents. | Anonymous; no figures; no detail on which checkpointer or which failure. | [S, unverifiable first-hand] https://jiminsf.com/langchain-to-pydantic-ai/ (2025-11-11) |
| Grid Dynamics (consultancy), three named authors | LangGraph with Redis for state and Kafka for delivery; a research agent for a manufacturer with 100+ plants | Temporal: each graph node became an activity, state is a Python dataclass kept in Temporal's history | First design "incredibly brittle in practice". Human-approval waits needed custom retry code; Redis state expired or was overwritten. After: they could "delete thousands of lines of custom retry and error handling code". | Published on Temporal's blog. Several of the problems came from their own Redis and Kafka design, not from LangGraph's Postgres checkpointer, which the post does not discuss. | [V, on the replacing vendor's blog] https://temporal.io/blog/prototype-to-prod-ready-agentic-ai-grid-dynamics (2025-09-29) |
| yeos.ai (Swiss enterprise-search product), author Nicola Richli | LangGraph pipeline: planner, retrieval, tools, answer, persistence. No human approval mentioned. | Small Python classes called in order, with their own telemetry | Debugging: "The graph made those questions harder instead of easier." Engineers spent time on state, edges and reducers. Most flows were sequential anyway. | Promotional post ending in a product pitch; no numbers; the year (2026) is inferred from the author's account date. | [V, about own system] https://dev.to/nicolaric/why-we-removed-langgraph-from-our-ai-platform-i9o (posted 27 July, 2026) |

Replacement by a lab SDK (Claude Agent SDK, OpenAI Agents SDK), by DBOS or by Restate, told first-hand by a named team: **not found**. Comparison articles on the subject are many; none is a migration report. A Hacker News search for the phrases "replaced LangGraph", "moved off LangGraph", "away from LangGraph", "dropped LangGraph", "ripped out LangGraph" in comments since July 2025 returned zero hits [M: hn.algolia.com API, 2026-11-21].

The pattern in the three cases matches the Thoughtworks reason for moving LangGraph from Adopt to Trial in April 2026 (shared state hard to reason about, plain code calling small agents is leaner). One addition on that source: the LangGraph page now says the blip is not on the current edition of the Radar (volume 35, November 2026). So there is no newer judgement, in either direction [S: https://www.thoughtworks.com/radar/languages-and-frameworks/langgraph].

## 3. Do the reference customers still run LangGraph in 2026?

| Company | 2026 evidence | Verdict |
|---|---|---|
| Uber | Uber's own blog, 2026-10-08: the legal redlining agent runs "a LangGraph workflow" [V: https://www.uber.com/us/en/blog/building-ubers-redlining-agent/]. For the developer platform, the public part of the Pragmatic Engineer piece (2026-03-10, interviews with Ty Smith and Anshu Chada) names Minion (background agents, about 11% of pull requests opened by agents), uReview and AutoCover, and does not mention LangGraph; the Minion section is behind a paywall [S: https://newsletter.pragmaticengineer.com/p/how-uber-uses-ai-for-development]. A third-party page says LangGraph is documented for Validator and AutoCover only, not for Minion [S: https://rywalker.com/research/uber-coding-agents]. | **Yes, in at least one product, October 2026.** Whether Uber's background coding-agent platform (the closest thing to a ticket-to-PR flow) uses it: **not found**. |
| GitLab | Runbook: the Duo Workflow Service runs sessions "using LangGraph"; issues and fixes on its LangGraph checkpointer dated September 2026 (section 1.1); blog of 2026-09-22 already in `langchain_langgraph.md`. | **Yes.** With its own checkpointer, lock, heartbeat and a YAML layer on top. |
| LinkedIn | 2026 talk at LangChain's conference: hiring agent on LangGraph (section 1.1). LangChain's preview: built "with LangSmith and LangGraph" [V]. | **Yes**, as of May 2026, without the interrupt primitive. No 2026 post on LinkedIn's own engineering blog was found. |
| Klarna | Only LangChain's case study of 2025-02-12 and reprints. Klarna is not on the 2026 conference speaker lists read [V: https://www.langchain.com/blog/previewing-interrupt-2026-agents-at-enterprise-scale]. | **Not found.** No 2026 source, for or against. |
| Replit | Restate's customer page (undated, footer 2026) quotes Michele Catasta, President and Head of AI at Replit: Restate "now handles all durable orchestration at Replit". It says Replit used Temporal first and moved for lower latency (an agent turn runs "thousands of inline durable steps"), for building blocks suited to concurrent agents, and to run in its own cloud account. About six weeks of development, then a two to three week rollout. LangGraph is not mentioned [V, Restate: https://restate.dev/use-cases/replit]. Replit's own post of 2026-07-16 describes "our agent harness, microVMs, and remote filesystem infrastructure" and names no framework [V: https://replit.com/blog/self-driving-company]. Replit was a 2025 conference speaker, not a 2026 one. | **Not found.** The only 2026 facts are about the durable layer, and it is not LangGraph's checkpointer. This also updates `labs_internal_stacks.md` and `gap_small_team_engine_threshold_and_cost.md`, which list Replit under Temporal: per Restate, Replit has since moved to Restate. |

What this table says, read plainly: of the five names LangChain uses, three are confirmed in 2026, and the three confirmed users use LangGraph as a library inside their own service. None of the three is shown to rely on LangChain's paid server for queueing and restart; GitLab and LinkedIn explicitly built those parts.

## 4. Crash recovery compared with Temporal, Restate, DBOS

### 4.1 The one test that ran

Paolo Perrone, "agent-crash-recovery" repository and a HackerNoon article (2026-09-24). The same small research agent (search, summarise 11 pages, outline, publish) on LangGraph, Inngest, DBOS and Temporal; the process is killed mid-run; the probe counts which finished steps run again [M by a single author; S for us]:

- Model calls were stubbed, so the test measures recovery, not cost.
- LangGraph with `durability="sync"` and Postgres: 0 finished steps paid twice (the kill landed between steps). Temporal: 0. Inngest: 0. DBOS: one summary repeated.
- Two LangGraph traps were hit on the way. First, resuming by passing a fresh input re-ran the whole graph ("bought 4 summaries and a search twice"); the resume call must pass `None`. Second, the author had to set `sync` by hand because the default writes in the background.
- Granularity: "Put four tool calls in one node, and the restart runs all four again."
- The README contradicts itself (a status line says nothing was executed end to end; a later section reports runs dated 2026-09-08) and names no SDK versions. Treat it as an anecdote that can be re-run, not as a benchmark.

Sources: https://github.com/paolo-perrone/agent-crash-recovery ; https://hackernoon.com/durable-execution-for-ai-agents-langgraph-dbos-inngest-and-temporal-compared

### 4.2 Other material

- The open race report on `sync` mode (section 1.2) is the only item with a reproduction script that targets LangGraph's own crash guarantee. It was not answered by a maintainer in the comments I filtered [M].
- Diagrid's "Checkpoints are not durable execution" (2026-02-25): "If your process crashes, no one knows"; no "supervisor, no watchdog, no heartbeat mechanism"; two processes resuming the same thread are not prevented. Argument from the API, nothing run, by a competitor [V: https://www.diagrid.io/blog/checkpoints-are-not-durable-execution-why-langgraph-crewai-google-adk-and-others-fall-short-for-production-agent-workflows]. GitLab's lock-and-heartbeat issue (section 1.1) is first-hand confirmation of exactly these two points.
- LangChain's own "LangGraph vs Temporal" page ticks "Durable execution" for both and does not discuss failure detection or queueing in the open-source library [V: https://www.langchain.com/resources/langgraph-vs-temporal].
- An academic paper (DART, arXiv 2605.23311, 2026-05-22) validates a recovery method on a LangGraph-based runtime; it does not compare engines.

**Not found**: an independent, versioned, repeatable benchmark or a post-mortem that compares LangGraph checkpoints with Temporal, Restate or DBOS on crash recovery.

## 5. The three unverified points

### 5.1 Default durability mode: `"async"` [M]

In `libs/langgraph/langgraph/pregel/main.py`, the run methods take `durability: Durability | None = None` and then do `config.get(CONF, {}).get(CONFIG_KEY_DURABILITY, "async")`. The docstring reads "defaults to `"async"`". I read this at tag 1.0.0, tag 1.2.0 and on the main branch (1.2.24) [M: https://github.com/langchain-ai/langgraph/blob/main/libs/langgraph/langgraph/pregel/main.py].

Meaning for a tech lead: by default the checkpoint is written in the background while the next step already runs. A hard crash can lose the newest checkpoint, and the step is then run again on resume. To get "written before the next step starts" you must pass `durability="sync"` on each call, and even then see the open race report in section 1.2. The official durable-execution documentation page could not be re-read in this pass (the fetch returned a different page); the source code is the stronger evidence.

### 5.2 What the open-source library lacks without the licensed server [M, V]

Licences read on PyPI on 2026-11-21 [M]:

| Package | Version | Licence |
|---|---|---|
| `langgraph` (the library) | 1.2.24 | MIT |
| `langgraph-checkpoint-postgres` | 3.2.1 | MIT |
| `langgraph-sdk` (client) | 0.4.14 | MIT |
| `langgraph-cli` | 0.4.43 | MIT |
| `langgraph-api` (the Agent Server) | 0.18.4 | Elastic-2.0 |
| `langgraph-runtime-inmem` (the local dev server runtime) | 0.38.4 | Elastic-2.0 |

Sources: https://pypi.org/pypi/langgraph-api/json and siblings.

What the server adds, in LangChain's words [V: https://docs.langchain.com/langsmith/agent-server]: a task queue ("the API server enqueues it and a queue worker picks it up"), a lease per run, "at most 1 run can be executed for a given thread at one time", scheduled jobs, webhooks when runs finish, authentication, separate scaling of API servers and queue workers, and "if a worker is interrupted, the run can resume from the last checkpoint".

So the MIT library alone does **not** give you: a queue, a worker pool, detection of a dead run, automatic restart, one-run-per-thread locking, scheduled runs, an HTTP API, or a record that a run was accepted (section 1.2). You write those, or you take the server.

Conditions for the server [V]: the standalone server needs Postgres, Redis and `LANGGRAPH_CLOUD_LICENSE_KEY`, "used to authenticate ONCE at server start up", plus outbound access for "license verification and usage reporting" unless air-gapped (https://docs.langchain.com/langsmith/deploy-standalone-server). "Self-hosted LangSmith is an add-on to the Enterprise plan" (https://docs.langchain.com/langsmith/self-hosted). A free self-hosted production tier: **not found** on the pages read. An independent write-up reaches the same reading: without the key you "build a custom FastAPI wrapper to handle the persistence, API layer, and streaming yourself" [S: http://rvernica.github.io/2026/03/langchain-license, Rares Vernica, March 2026]. Community replacements for the server exist (for example `langhost`, `mwaeckerlin/langgraph-agent`); I did not evaluate them.

Two caveats from the field: the paid server has its own recovery bug open for seven months (issue 7417, section 1.1), and LangChain's own ticket-to-PR system depends on the paid stack: Open SWE pins `deepagents==0.7.41`, requires `managed-deepagents`, ships a `langgraph.json` for Agent Server API 0.18.2, and has its issue tracker switched off [M: https://github.com/langchain-ai/open-swe, read 2026-11-21, 11,246 stars, last push the same day].

### 5.3 Did Anthropic drop LangGraph from its framework list? Yes [M]

Archived copies of "Building effective agents" (https://www.anthropic.com/engineering/building-effective-agents), read through the Wayback Machine:

| Snapshot | Framework list |
|---|---|
| 2025-03-05 | "LangGraph from LangChain; Amazon Bedrock's AI Agent framework; Rivet...; and Vellum..." |
| 2025-10-02 | same as above |
| 2025-11-30 | "The Claude Agent SDK; Amazon Bedrock's AI Agent framework; Rivet...; and Vellum..." |
| 2026-02-02 | "The Claude Agent SDK; Strands Agents SDK by AWS; Rivet...; and Vellum..." |
| 2026-05-28 | same; no note at the top |
| 2026-09-02 and live page | same list, plus a note: "Much of the tooling landscape described in this post has changed since December 2024", pointing to Claude Managed Agents |

So the claim in `labs_internal_stacks.md` holds, with a date: the swap happened between 2025-10-02 and 2025-11-30. One caution on reading it: Anthropic replaced a third-party name with its own SDK and gave no reason. It is evidence of what Anthropic recommends, not a published criticism of LangGraph. Archive URLs: http://web.archive.org/web/20250305014737/https://www.anthropic.com/engineering/building-effective-agents ; .../20251002000748/... ; .../20251130000615/... ; .../20260202124918/... ; .../20260902212628/...

## 6. What this changes in the other notes

- `langchain_langgraph.md`, summary line 4 ("none of the public removals found concern LangGraph"): three small removals exist (section 2). The statement stays true for large named companies.
- `langchain_langgraph.md`, section 9: default durability is `"async"`; Replit 2026 is still not found, but its durable layer is Restate, not a LangGraph checkpointer.
- `labs_internal_stacks.md` and `gap_small_team_engine_threshold_and_cost.md`: Replit is listed as a Temporal user; a vendor page says it has moved to Restate [V]. The Anthropic claim is confirmed and dated.
- The "big users wrap it" pattern is stronger than stated: GitLab wrote its own checkpointer, lock and heartbeat; LinkedIn avoids the interrupt primitive and rebuilt LangSmith-like tracing in house.

## 7. Verdict

For a team that drives an existing coding agent (Claude Code, Codex) through a ticket workflow, I found **no independent evidence that LangGraph adds something a state table plus CI, or a durable engine, does not**. The coding agent already owns the loop that LangGraph was built to control, so what is left for LangGraph is the outer workflow: remember the step, wait for a human, survive a crash, never run twice. On exactly those four jobs the 2026 evidence is unfavourable or absent. The library's default writes checkpoints in the background; a paused or crashed step runs again by design, so duplicate tickets, comments or pushes are the team's problem to prevent; the library does not notice a dead run, does not queue, and does not stop two workers on the same ticket; the component that does is under a non-open licence, needs an Enterprise key in production, and has an open duplicate-execution bug of its own. The users best placed to judge (GitLab, LinkedIn) built locks, heartbeats and their own approval logic around it, and the teams that left went to plain code or to Temporal. What LangGraph does offer and a state table does not is rewind to an earlier checkpoint and a ready-made state viewer; no source showed a ticket workflow that needed them. The honest limit of this verdict: it rests on an absence of positive independent evidence and on a handful of small or vendor-coloured negative reports, not on a measured comparison.

## 8. Not found

1. A named team, outside LangChain and GitLab, that runs a ticket-to-PR or software-delivery workflow with human approval on LangGraph and reports on it first-hand.
2. Any team that drives Claude Code or Codex from a LangGraph graph in production and reports results (only proof-of-concept repositories and tutorials).
3. A first-hand removal of LangGraph by a large named company; a removal in favour of a lab SDK, DBOS or Restate.
4. Whether Replit Agent still contains LangGraph in 2026; whether Uber's Minion platform uses it; any 2026 statement on Klarna.
5. An independent, versioned benchmark of LangGraph checkpoints against Temporal, Restate or DBOS; a public post-mortem of a LangGraph crash-recovery incident with numbers.
6. A first-hand account of the 0.x to 1.x upgrade, good or bad; whether old checkpoints stay readable across versions.
7. A LangChain staff answer to issue 7417 (duplicate execution on the hosted server) and to issue 8039 (race in `sync` mode).
8. Whether a free production tier of the self-hosted Agent Server exists; the price of the Enterprise self-hosted add-on.
9. Reddit threads: Reddit refused automated reads and search engines returned none; r/LangChain was **not searched** in effect.
10. The full text of the Towards AI post-mortem, of the bswen article and of GitLab's ADR 005 (blocked or truncated pages); the paywalled part of the Pragmatic Engineer article; the conference videos (not watched).

## Sources

Primary artefacts read (measured):

- https://github.com/langchain-ai/langgraph/blob/main/libs/langgraph/langgraph/pregel/main.py (also at tags 1.0.0 and 1.2.0)
- https://github.com/langchain-ai/langgraph/issues/7417 (2026-04-05, open)
- https://github.com/langchain-ai/langgraph/issues/7780 (2026-05-13, open)
- https://github.com/langchain-ai/langgraph/issues/8039 (2026-06-10, open)
- https://github.com/langchain-ai/langgraph/issues/8764 (2026-08-30, closed not planned)
- https://github.com/langchain-ai/langgraph/issues/9006 (2026-09-19, closed not planned)
- https://github.com/langchain-ai/langgraph/issues/9106 (2026-09-29, closed, fixed)
- https://github.com/langchain-ai/langgraph/issues/7714 (2026-05-05, closed not planned; storage-size claim rejected by a contributor)
- https://github.com/langchain-ai/open-swe (pyproject.toml, langgraph.json)
- https://pypi.org/pypi/langgraph-api/json ; https://pypi.org/pypi/langgraph-runtime-inmem/json ; https://pypi.org/pypi/langgraph-cli/json ; https://pypi.org/pypi/langgraph-checkpoint-postgres/json ; https://pypi.org/pypi/langgraph-sdk/json ; https://pypi.org/pypi/langgraph/json
- http://web.archive.org/web/20250305014737/https://www.anthropic.com/engineering/building-effective-agents (and snapshots 20251002000748, 20251130000615, 20260202124918, 20260528022315, 20260902212628)
- https://www.anthropic.com/engineering/building-effective-agents (live)
- https://hn.algolia.com/api/v1/search (queries listed in section 2)
- https://gitlab.com/gitlab-org/gitlab/-/issues/548686 (2025-06-11 to 2026-02-16)
- https://gitlab.com/gitlab-org/gitlab/-/issues/627533 (2026-09-03 to 2026-09-08)

Companies on their own systems or products (vendor):

- https://runbooks.gitlab.com/duo-workflow-svc/
- https://www.uber.com/us/en/blog/building-ubers-redlining-agent/ (2026-10-08)
- https://replit.com/blog/self-driving-company (2026-07-16)
- https://restate.dev/use-cases/replit (undated, 2026)
- https://temporal.io/blog/prototype-to-prod-ready-agentic-ai-grid-dynamics (2025-09-29)
- https://dev.to/nicolaric/why-we-removed-langgraph-from-our-ai-platform-i9o (27 July 2026)
- https://docs.langchain.com/langsmith/agent-server
- https://docs.langchain.com/langsmith/deploy-standalone-server
- https://docs.langchain.com/langsmith/self-hosted
- https://docs.langchain.com/oss/python/migrate/langgraph-v1
- https://www.langchain.com/blog/langchain-langgraph-1dot0
- https://www.langchain.com/blog/previewing-interrupt-2026-agents-at-enterprise-scale (2026-04-09)
- https://www.langchain.com/resources/langgraph-vs-temporal
- https://interrupt.langchain.com/recordings (8 of 23 talks visible)
- https://www.diagrid.io/blog/checkpoints-are-not-durable-execution-why-langgraph-crewai-google-adk-and-others-fall-short-for-production-agent-workflows (2026-02-25, competitor)
- https://agentfield.ai/blog/langgraph-to-production (2026-07-02, competitor)

Third parties (secondary):

- https://jiminsf.com/langchain-to-pydantic-ai/ (2025-11-11)
- https://raed.dev/blog/posts/langgraph-hitl/ (2026-03-15)
- https://github.com/paolo-perrone/agent-crash-recovery
- https://hackernoon.com/durable-execution-for-ai-agents-langgraph-dbos-inngest-and-temporal-compared (2026-09-24)
- https://www.zenml.io/llmops-database/agentic-hiring-system-reduces-time-to-interview-by-60-for-small-businesses (talk: https://www.youtube.com/watch?v=LUemJGG2k4c, not watched)
- https://newsletter.pragmaticengineer.com/p/how-uber-uses-ai-for-development (2026-03-10, partly paywalled)
- https://rywalker.com/research/uber-coding-agents
- https://www.thoughtworks.com/radar/languages-and-frameworks/langgraph
- http://rvernica.github.io/2026/03/langchain-license (March 2026)
- https://forum.langchain.com/t/self-hosted-deployment-question/1092 (2025-08-12)
- https://8thlight.com/insights/production-is-the-new-prototype-notes-from-langchain-interrupt-2026 (attendee notes; does not mention LangGraph)
- https://news.ycombinator.com/item?id=46740737 (2026-01-24)
- https://arxiv.org/abs/2605.23311 (2026-05-22)
- https://dev.to/creeta/one-missing-checkpoint-can-break-every-approval-gate-127k (discarded)
- https://dev.to/elenarevicheva/three-langgraph-rewrites-checkpointing-production-agents-3872 (discarded)

Pages that could not be read (claims not used): https://pub.towardsai.net/langgraph-checkpointing-is-not-free-a-production-postmortem-398bc86861f4 (403) ; https://docs.bswen.com/blog/2026-03-18-why-teams-migrate-from-langgraph (403) ; https://particula.tech/blog/langgraph-vs-temporal-agents (429) ; https://handbook.gitlab.com/handbook/engineering/architecture/design-documents/duo_workflow/decisions/005_deprecate_checkpoint_field (body truncated).
