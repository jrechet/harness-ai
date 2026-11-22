# LangGraph: four ideas worth keeping, and a library you probably do not need

Date of the facts: 2026-11-21, from [report.md](report.md); the code example of section 2 was checked against the official documentation on 2026-11-22.

Do you need LangGraph? Not for a ticket workflow that drives a coding agent, and not by default for a team.
LangGraph fits one case: you write your own agent application in Python or TypeScript, the graph is known, and a run must pause and resume inside the process.
Its four ideas (run identity, checkpoint, interrupt, replay) are the right ones, and you will apply them on whatever runs your flow.

You are a tech lead. Somebody on the team says "we need LangGraph so the workflow can wait for an approval and survive a crash". This page gives you what the library does, what it leaves to you, who uses it and how, and where the same four ideas live when you do not use it. For LangChain, a different product of the same company, see [langchain.md](langchain.md).

**Words used, defined once.**

- **Agent**: a model that calls tools in a loop until a task is done. **Coding agent**: an agent that edits a repository (Claude Code, Codex).
- **Workflow**: a sequence where code chooses the next step, and a model fills in some steps.
- **Graph framework**: a library where you declare steps as **nodes** and transitions as **edges**. Unlike a plain sequence, a graph can loop back.
- **Durable execution**: a run that crashes or waits for days continues where it stopped. **Engine**: a product that gives it (Temporal, Restate, DBOS). See [engines.md](engines.md).
- **Flow**: one team workflow for one kind of ticket.
- **Idempotent**: safe to run twice. Doing it twice has the effect of doing it once.
- **CI**: the pipelines of the forge. A **forge** hosts repositories and decides what may be merged (GitHub, GitLab, Forgejo). A **sweep** is a scheduled job that lists the tickets whose run is missing or dead.
- **Evidence labels**, kept from the report: [M] read from a registry, a repository or a specification; [V] said by a company about itself; [S] said by a third party. A user's bug report counts as [M] on that user's install only.

## 1. The idea: a graph, one saved state

LangGraph is a small runtime, published in January 2024, under the MIT licence, in Python and TypeScript (version 1.2.24 [M], report §2.1). Its documentation describes it in one sentence: "You define workflows as graphs of shared state, nodes, and edges, and can mix deterministic steps with LLM-driven steps in the same graph" [M] (note langchain_langgraph.md §3.3).

- A **node** is a plain function: it receives the state and returns an update to it.
- An **edge** says which node comes next. It can go back, so a graph can loop ("tests failed, go back to implement").
- There is **one state object** for the whole graph. A component called a checkpointer saves a copy of it to a database after each step.

Why it exists: LangChain's first agent class gave nearly every decision to the model and could not loop under the developer's control. LangChain wrote that "the higher level abstraction hides too many details from the developer" [V]. LangGraph is the correction: lower level, nothing writes prompts for you, and it does not need LangChain (report §2.1, §2.2).

## 2. The four words to keep

| Word | LangGraph's name | What it means |
|---|---|---|
| **Run identity** | a thread, named by a `thread_id` | One name for one run. Every saved state of the run belongs to it. Resuming, approving and replaying all start from that name |
| **Checkpoint** | a checkpoint, written by a checkpointer | A saved copy of the state after a step. Stores: memory (lost at restart, not for production), SQLite (development), Postgres (production) [M] |
| **Interrupt** | `interrupt(payload)` | The run stops at a chosen point and saves its state. A person is shown the payload. A later call resumes the run with the person's answer. The pause can last minutes or weeks; no process stays alive [M] |
| **Replay** | time travel | List the checkpoints of a run, start again from an earlier one, or fork from it with a changed state. The original history stays intact [M] |

(note langchain_langgraph.md §1 and §3.3).

**The example.** A plan is written, a person approves it, and the run is replayed. It is about twenty lines with its imports.

```python
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command, interrupt

class State(TypedDict):
    ticket: str
    plan: str
    answer: str

def write_plan(state: State):            # a node: state in, update out
    return {"plan": "plan for " + state["ticket"]}

def approve(state: State):               # pauses here; on resume this node starts again from its first line
    return {"answer": interrupt(state["plan"])}

builder = StateGraph(State)
builder.add_node(write_plan)
builder.add_node(approve)
builder.add_edge(START, "write_plan")
builder.add_edge("write_plan", "approve")
builder.add_edge("approve", END)
graph = builder.compile(checkpointer=InMemorySaver())      # checkpoints, in memory only

run = {"configurable": {"thread_id": "TICKET-42"}}         # the run identity
graph.invoke({"ticket": "TICKET-42"}, run, durability="sync")   # runs until the interrupt, then stops
graph.invoke(Command(resume="yes"), run)                   # a person answered: resume the same run
history = list(graph.get_state_history(run))               # the checkpoints, newest first
graph.invoke(None, history[1].config)                      # replay from an earlier one
```

**This example was not executed here.** It is assembled from names, not copied from one page. `StateGraph`, `START`, `END`, `add_node`, `add_edge`, `compile(checkpointer=...)`, `interrupt`, `Command(resume=...)`, `thread_id`, `get_state_history` and `durability="sync"` are in the notes (langchain_langgraph.md §3.3; gap_langgraph_independent_evidence_2026.md §5.1). The import paths, `InMemorySaver`, the `{"configurable": {"thread_id": ...}}` shape and the replay call `invoke(None, <checkpoint>.config)` were checked on 2026-11-22 in the official documentation:

- https://docs.langchain.com/oss/python/langgraph/interrupts.md
- https://docs.langchain.com/oss/python/langgraph/use-time-travel.md

Three details of the example carry the rest of this page.

- `durability="sync"` is not the default. The default is `"async"`: the checkpoint is written in the background while the next step already runs, so a hard crash can lose the newest one. Read in the source at tags 1.0.0, 1.2.0 and main [M] (report §2.5, point 2). Even with `sync`, a user's open bug report says the order of two writes is not enforced; the note did not run its reproduction, and found no maintainer answer in the comments it read (note gap_langgraph_independent_evidence_2026.md §1.2 and §4.2). There are three modes: `exit` (write only when the run ends or is interrupted), `async` and `sync` [M] (note langchain_langgraph.md §3.3). The mode is chosen on each call, so the resume and the replay lines above would need `durability="sync"` too (note gap_langgraph_independent_evidence_2026.md §5.1).
- A resume passes `Command(resume=...)` or `None`, never a fresh input. In the one crash test found, passing a fresh input ran the whole graph again [S, single author] (note gap_langgraph_independent_evidence_2026.md §4.1).
- The comment on `approve` is the first line of the fine print.

## 3. The fine print

### Replay runs the step again

"Replay re-executes nodes; it doesn't just read from cache", and after a pause "the runtime restarts the entire node from the beginning" [M]. A maintainer calls it "a natural consequence of the fact that all code pre-interrupts re-runs" [M] (report §2.5, point 1).

```
 one node: open_ticket_then_ask

 first call      create the ticket ──► interrupt("send the email?") ──► state saved, run stops
                 (ticket #1 exists)                                      … a person answers, hours later …

 resume          create the ticket ──► interrupt() returns "yes" ──► send the email
                 (ticket #2 exists)
```

A demo by an engineer shows exactly this: "The ticket ran twice before the user saw anything." His rule: "any tool with side effects or irreversible consequences gets its own node" [M, a demo, not a production system] (note gap_langgraph_independent_evidence_2026.md §1.1). The same holds after a crash: "Put four tool calls in one node, and the restart runs all four again" [S] (same note, §4.1).

So every side effect in a node (open a pull request, comment on a ticket, push a branch) must be idempotent, and that work is yours. A replay from an old checkpoint also makes new model calls, possibly with different results, and its interrupts fire again [M] (note langchain_langgraph.md §3.3).

### Nothing watches your process

The library saves state. It does not watch the process that runs the graph. The MIT library alone has no queue, no worker pool, no detection of a dead run, no automatic restart, no lock against two workers on one thread, and no record that a run was accepted [M] (report §2.5, point 3). On the last point, a request to record accepted runs was closed "not planned": "tracking admission belongs in the caller" [M] (note gap_langgraph_independent_evidence_2026.md §1.2).

Those parts are in LangChain's Agent Server, the server that wraps the library with a queue, workers and an HTTP API. It was earlier called "LangGraph Platform" and is now sold as "LangSmith Deployment" (note gap_langgraph_independent_evidence_2026.md, word list). What is known about it:

| Fact | Label |
|---|---|
| Its package, `langgraph-api`, is under the Elastic 2.0 licence, not an open-source one | [M] |
| Its standalone-server page lists `LANGGRAPH_CLOUD_LICENSE_KEY` among the variables needed, and asks for network access to LangChain "for license verification" | [V] |
| Which paid plan a standalone server needs is **not stated on a page the report can cite**. The docs call the self-hosted LangSmith platform an add-on to the Enterprise plan; a forum answer from a community member, not staff, says self-hosting is not possible without an enterprise key | not settled |
| The old free tier is no longer mentioned; no page announces its removal | not found |
| The server has its own open bug: tool calls longer than about 180 seconds are dispatched a second time. Open since April 2026, 89 comments | [M, on users' installs] |

(report §2.5, point 3; report §11, claim C3). So you write the supervisor yourself, or you take a licensed server.

### The store is an attack surface

A checkpoint store holds data that is read back and turned into objects. Several vulnerabilities in 2025 and 2026 reached code execution through saved state. All are fixed, and the Postgres path was spared [S] (report §2.5, point 4). The note's lesson: never expose the store's query filters to users, pin versions, and patch (note langchain_langgraph.md §5.4).

**Two of these three are not LangGraph's fault.** Making side effects safe to repeat, and noticing a dead run, are the cost of durability on every option, a home-made one included (report §2.5). No independent, repeatable benchmark compares LangGraph's recovery with Temporal, Restate or DBOS; one single-author test with a stubbed model exists (report §2.5).

## 4. Who uses it, and how they wrapped it

| Who | What they run on it | What they built around it | Label |
|---|---|---|---|
| **GitLab** (agent platform) | Chose LangGraph, then built a layer above it that compiles YAML into LangGraph flows, because raw graphs gave "no reusability, no composability" | Its own checkpointer, a lock, and a 15-second heartbeat, because a workflow could run in two places and overwrite its own checkpoints | [V] |
| **LinkedIn** (hiring agent) | A planner loop on LangGraph | Does **not** use the interrupt for human review: each turn runs the graph end to end, and a small "pending suggestion" is saved between turns | [S], summary of a 2026 talk; the video was not watched |
| **Uber** (legal agent) | A parallel step runner inside one request | Nothing reported on checkpoints or approval | [V] |
| **Replit** | Documented on LangGraph in a 2024 case study on LangChain's site | Its durable layer went elsewhere: Temporal in 2025, then Restate. Whether LangGraph is still inside Replit Agent is **not known** | [V] |

(report §2.6; note gap_langgraph_independent_evidence_2026.md §1.1 and §3). Klarna, the fifth name LangChain uses: nothing found since February 2025, for or against (same note, §3).

Three more facts complete the picture.

- **Removals exist, and they are small.** Three were found: an anonymous team (to Pydantic AI plus Temporal), a consultancy (to Temporal, published on Temporal's blog) and a Swiss product (to plain Python classes). None gives numbers. No large named company has published one [S][V] (report §2.3).
- **LangChain's own ticket-to-PR system depends on the paid stack.** Open SWE, renamed Robin, takes work from issues, opens a pull request and watches CI. Its README warns of breaking changes, and deploying it as is requires the paid hosted runtime [M] (note langchain_langgraph.md §3.4).
- **Nobody was found doing what you may be planning.** No named team was found that drives Claude Code or Codex from a LangGraph graph in production (report §2.6). This is a search that found nothing, not a proof that none exists.

The report's reading: the three users confirmed in 2026 use LangGraph as a library inside their own service, and the two that need recovery or approval built those parts themselves (report §2.6, marked "My reading").

## 5. Why the Radar moved it to Trial

The Thoughtworks Technology Radar is a list that a consultancy publishes in editions; it places each tool in a ring, such as Adopt or Trial. In April 2026 it moved LangGraph from Adopt to Trial [S] (report §2.6; confirmed by the fact-checkers, report §11, claim C14).

The reason is about design, not reliability. One large shared state for the whole graph is "not always the best approach"; simple agents that talk through code, with a graph added later if needed, are often leaner and easier to test [S] (report §2.6). The note reads the three removals above as the same pattern: plain code calling small agents was leaner than one graph with a shared state (note gap_langgraph_independent_evidence_2026.md §2). That is the note's reading. The teams' own words differ: one calls a graph "the wrong abstraction for long-running tasks" and its checkpointing "bolted on", one blames a brittle design of its own with Redis and Kafka, one says the graph made debugging harder.

One limit. The page was last updated on 2026-04-15, and the entry is absent from the November 2026 edition, so there is no newer judgement in either direction (report §2.6, §11).

A neighbouring fact, often misread: Anthropic's reference text on agents listed "LangGraph from LangChain" among example frameworks until October 2025, and lists "The Claude Agent SDK" since November 2025. No reason is given. It shows what Anthropic recommends, not a criticism [M, web archive] (report §2.6).

## 6. When to use it, when not

| Use it when | Do not use it when |
|---|---|
| You write your own agent application | The step already runs inside a coding agent: use skills and hooks |
| The graph has real branches and loops | The flow is a straight line: use a script |
| A run must pause for a human inside the process | You already have an engine, or a CI that holds state |
| The team writes Python or TypeScript and has Postgres | Side effects cannot be made idempotent |
| | You want Rust: nothing serious ports it (report §1; [rust.md](rust.md)) |

(report §2.7). For a ticket workflow that drives a coding agent, the coding agent already owns the loop LangGraph was built to control. What is left for LangGraph is the outer workflow: remember the step, wait for a human, survive a crash, never run twice. On those four jobs the 2026 evidence is unfavourable or absent (note gap_langgraph_independent_evidence_2026.md §7). That note states its own limit: the verdict rests on an absence of positive independent evidence and on a handful of small or vendor-coloured negative reports, not on a measured comparison.

If you already have LangGraph graphs and need an engine under them, Temporal publishes a plugin that runs the graph as a workflow and each node as a retried activity. It is in Public Preview and for Python only [V, said by a competitor] (note langchain_langgraph.md §5.5).

This is why `flow place`, the command that says where each step of a flow belongs, has no place for a graph framework ([decide.md](decide.md), sections 2 and 3).

## 7. The same four words on CI and on an engine

The four words are needs, not products (report §2.4). You answer them on any runtime.

| Word | LangGraph | Ticket state plus CI (the default) | An engine |
|---|---|---|---|
| **Run identity** | `thread_id` | The ticket. One run at a time per ticket; keys derived from the ticket, never random | One workflow ID per ticket |
| **Checkpoint** | A checkpointer writes the state after each step | What each job writes on the ticket or the pull request: a status, a label, progress between jobs. A failed job restarts from zero and pays its tokens again | Each call to the outside is a recorded step. After a crash the code runs again and skips the recorded steps |
| **Interrupt** | `interrupt()`, then a resume call | A ticket or pull request state whose change starts a new job. It is the only human gate that exists on all four forges compared | A signal. A wait of three weeks holds no process |
| **Replay** | Time travel; nodes run again | Run the job again from its start. Labels and a comment are not an audit trail | The engine's history. Steps still run at least once |
| Who notices a dead run | Nobody: your code, or the licensed server | A job timeout and a scheduled sweep | An engine timer |
| Who makes writes safe to repeat | You | You | You |

(report §2.4; §3.2; §3.3; §6.3; §7, last table; §9.2). Details of the middle column in [ci-as-engine.md](ci-as-engine.md), of the right one in [engines.md](engines.md).

The last row is the one to remember. No runtime removes idempotency. And the first two rows explain the report's choice of default: a ticket status, a label and a pull request are durable state the team already owns (report §2.4).

How sure is the default? No first-hand account exists of a team of 5 to 50 running a ticket-to-PR flow on any runtime, CI included [M: searched and not found] (report §1, §9.1).

## The symptom that would make you need it

All of these, on your own project, not one of them:

- **You are writing the agent application itself**, in Python or TypeScript. The loop is your code, not a coding agent you start. Measure: no step of the run is "start Claude Code or Codex".
- **The run has at least one loop or branch you can draw before it runs**, and you have already written the "which step is next" code by hand more than once.
- **A person must answer while the run holds something that cannot be written to a ticket and read back**: a wait inside one expensive multi-step computation. Measure: you tried to model the wait as a ticket state ([decide.md](decide.md), section 3) and the step had to redo paid work each time.
- **Every write to the outside in your nodes has a key** that makes a second run harmless. Count the writes that have none: it must be zero before you rely on resume.
- **You have Postgres**, and somebody owns the part that notices a dead run and starts it again.

For a ticket flow that drives a coding agent, no symptom was found that points to LangGraph and not to the ticket's state or to an engine (note gap_langgraph_independent_evidence_2026.md §7). If your symptom is "runs die far in" or "two runs on one ticket", read the symptom table of [decide.md](decide.md), section 3, first.
