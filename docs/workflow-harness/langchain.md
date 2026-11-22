# LangChain: what it was for, and what is left of it

Date of the facts: 2026-11-21, from [report.md](report.md).

Should a team use LangChain for its ticket workflow? No, not when it drives an existing coding agent.
LangChain was glue code for models that could only return text; models now do that work themselves, and the old parts were moved to a legacy package.
What is left is useful in one case: you write your own agent application and you call several model providers.

You are a tech lead. Somebody on the team says "we should use LangChain for our ticket workflow". This page gives you what the library is, why it existed, what happened to it, and the facts to answer with. Its sibling [langgraph.md](langgraph.md) covers LangGraph, a different product from the same company.

**Words used, defined once.**

- **Model**: the large language model you send text to and get text back from. **Provider**: the company whose API serves it (OpenAI, Anthropic, Google).
- **Prompt template**: a text with holes, filled in before the call.
- **Chain**: a fixed sequence of steps where the output of one is the input of the next: prompt, then model call, then parsing.
- **Output parser**: code that turns the model's free text into a structure such as JSON.
- **Tool calling**: the model returns a structured request "call function X with arguments Y" instead of prose. The program runs X and sends the result back.
- **Agent**: a model that calls tools in a loop until a task is done. **Coding agent**: an agent that edits a repository (Claude Code, Codex).
- **Middleware**: a piece of code that runs before or after each model call or tool call, for example to ask a person for approval.
- **SDK**: the library a provider publishes to call its own API.
- **Harness**: everything around the model that makes its work reliable: instructions, tools, checks, the loop.
- **CI**: the pipelines of the forge, the server that hosts the repositories (GitHub Actions, GitLab CI, Forgejo Actions).
- **Flow**: one team workflow for one kind of ticket.
- **Evidence labels**, kept from the report: [M] read from a registry, a repository or a specification; [V] said by a company about itself; [S] said by a third party.

The definitions of model, prompt template, chain, output parser, tool calling, agent and middleware are from the note langchain_langgraph.md, section 1. Coding agent, harness and CI are from the report's word list. Provider, SDK and flow are this page's.

## 1. What it is, in one paragraph

LangChain is an open-source library, in Python and TypeScript, started in October 2022. In its first form it formatted prompts, called a model and parsed the answer. In its current form (version 1.x, since October 2025) it is one interface over many model providers plus a ready agent loop with middleware (report §2.1; note langchain_langgraph.md, summary). The company behind it, LangChain Inc., also publishes three other things, which people often mix up with it:

| Product | Since | In one sentence | State in November 2026 |
|---|---|---|---|
| **LangChain** | Oct 2022 | Formats prompts, calls a model, parses the answer; later, one interface over many providers plus a ready agent loop | 1.5.2. Old chains moved to `langchain-classic` [M] |
| **LangGraph** | Jan 2024 | Runs a workflow as a graph of steps sharing one saved state | 1.2.24, MIT licence, Python and TypeScript [M]. See [langgraph.md](langgraph.md) |
| **Deep Agents** | Jul 2025 | LangChain's own harness (planning, files, sub-agents), its answer to Claude Code | 0.7.41, still 0.x; 41 releases in 16 weeks [M] |
| **LangSmith** | Jun 2023 | The paid platform: traces, evaluations, hosting. Works without the libraries | Where the company earns money; $300M raised on 2026-11-13 [V] |

(report §2.1). Two cautions on this table. The version numbers other than LangGraph's latest release, and the funding amount, were not re-checked by the report's fact-checkers (report §11, "Not checked in this pass"). And LangGraph does not need LangChain: its own documentation says so [M] (report §2.1).

## 2. The 2022 problem it solved

In 2022 a model was text in, text out. Each provider had a different API. A model could not call a tool: you asked it to write JSON in its answer, then you parsed that text and hoped it was valid. So every team wrote the same code again:

```
 your code, 2022                                   the model
 ───────────────                                   ─────────
 fill the prompt template      ───── text ────►
                               ◄──── text ─────    free text, maybe JSON, maybe not
 parse the text
 if it does not parse: retry
 if it "asks for a tool": run the tool,
 paste the result into a new prompt  ── text ──►
                               ◄──── text ─────
 parse again …
```

LangChain packaged that code: templates, the call, the retry, the parsing, and the "pretend to call a tool" trick [V] (report §2.2; note langchain_langgraph.md §2). It appeared one month before ChatGPT, and took off with it [V] (note langchain_langgraph.md §2).

What changed since: models call tools natively and return structured output natively; the labs publish their own agent SDKs; coding agents run long tasks alone, with their own loop, sandbox and permission system (note langchain_langgraph.md §6). The right-hand column of the picture now does most of what the left-hand column did.

## 3. The timeline to 1.0

From LangChain's own documentation [V] and its repository [M], as the note read them (note langchain_langgraph.md §2).

| Date | Event |
|---|---|
| 2022-10-17 | GitHub repository created [M]. Version 0.0.1 on 2022-10-24: "LLM abstractions" and "Chains". A side project of Harrison Chase |
| 2022-11-30 | ChatGPT launches; the project takes off [V] |
| 2022-12 | First general agents. The model writes JSON as text; LangChain parses it to find the tool call |
| 2023-02 | LangChain Inc. founded |
| 2023 | OpenAI adds function calling to its API. LangChain's timeline says March 2023; the commonly cited date is June 2023. The note did not re-verify either. LangChain switches from parsing JSON to native tool calls |
| 2023-06 | LangSmith released, closed source |
| 2023 Q3 | The pipe syntax arrives (LCEL, "LangChain Expression Language"): `prompt \| model \| parser` [S] |
| 2024-01 | Version 0.1.0, the first release aimed at stability. LangGraph is launched the same month |
| 2024-06 | "Over 700 integrations", split into separate packages |
| 2024-10 | "Most chains and agents were marked as deprecated", with guides to migrate to LangGraph |
| 2025-10 | Version 1.0.0 (tag of 2025-10-17 [M]). All chains and agents replaced by one agent abstraction built on LangGraph |

Read the last two lines together: two years after its start the library marked most of what had made it known as deprecated, and a year later it rebuilt its agent on top of its own second product.

LangChain says so itself. Its first chains and agents "provided abstractions that got in the way"; users complained about "breaking changes, hidden prompts, package bloat, dependency conflicts, and outdated docs" [V] (note langchain_langgraph.md §5.6). Since 1.0 it promises "no breaking changes until 2.0" [V]. In practice the minimum Python version moved inside 1.x: 3.10 at 1.0, 3.11 at 1.5.0 [M] (note langchain_langgraph.md §3.2). No date for a 2.0 is published (note langchain_langgraph.md §9).

## 4. What aged, and the proof

| Piece | Why it aged | Proof |
|---|---|---|
| Prompt templates, chains | A prompt is a string; two calls are two function calls | Moved to `langchain-classic` [M] |
| Output parsers | Models return structured output natively | "Prompted output" removed in 1.0 [M] |
| The pipe syntax (LCEL) | It composed steps that no longer need a library | Zero mention in the index of the 1.x Python documentation [M]. The code still works and is still maintained; it is no longer taught (note langchain_langgraph.md §3.2) |
| The first agent class (`AgentExecutor`) | Too opaque: it gave nearly every decision to the model | LangChain: its early abstractions "got in the way" [V] |
| Planner prompts, long default prompts | Recent models plan without them | Deep Agents 0.7 removed its default prompt; input per turn fell about 65% [V] |

(report §2.3). The last line is the vendor measuring its own product: help written for the models of 2025 was dead weight for the models of 2026 (note langchain_langgraph.md §3.4, marked there as a judgement).

**What teams that removed it say.** The report sums it up in one sentence: time spent understanding the framework instead of building (report §2.3). The accounts behind it, each with its limit (note langchain_langgraph.md §5.1):

| Who | What they report | Label and limit |
|---|---|---|
| Octomind (2024) | Used it in production for about a year, then removed it: as much time "understanding and debugging LangChain" as building features | [S]. The original article did not resolve on 2026-11-21; the quotes come from search summaries. The Hacker News thread (480 points) was read [M] |
| Microsoft ISE (2024) | "Large, breaking changes roll through LangChain that required significant rework"; after security reports, "most of our first-party teams eschew its use" | [S] |
| Vettio (2026) | After a rewrite on the provider's SDK: median latency 2.1 s to 1.4 s, error rate 0.9% to 0.2%, integration code 812 to 187 lines. "Abstractions pay for themselves when the underlying APIs are bad" | [S], one team, self-reported. The same author still names LangGraph workflows and LangSmith as valid reasons to stay |

None of these is a controlled comparison. The report says the same of nearly every "we removed it and nothing broke" number: self-reported, often on a handful of cases (report §9.1, point 11).

**Security.** A library that reads back saved state and model output is a target. One vulnerability of 2025 in `langchain-core` (CVE-2025-68664, score 9.3) let a crafted model response be treated as a saved object; it is fixed [S] (note langchain_langgraph.md §5.4).

## 5. What the 1.x package still gives

What is in the `langchain` package now [M][V] (note langchain_langgraph.md §3.2):

| Piece | What it does | Still in beta |
|---|---|---|
| `create_agent` | One function that builds a "model calls tools in a loop" agent. It runs on LangGraph, so it inherits saved state and the pause for a human | |
| Middleware | Code around the loop. Built in: human approval, summarising history near the context limit, redaction of personal data, retry with backoff, content moderation | Model routing and the blocking of risky tool calls, since 1.5.0 |
| Model adapters | One interface over OpenAI, Anthropic, Google and others, with one shape for reasoning traces, citations and tool calls | |
| Structured output | Through the provider's native feature, or through a tool call | |
| MCP support | MCP (Model Context Protocol) is the standard way to plug external tools into an agent | Yes, since 1.4.0 |

What left the package: the old chains (`LLMChain`, `ConversationChain`), retrievers, indexes and the prompt hub, all moved to `langchain-classic` [M] (note langchain_langgraph.md §3.2).

So the 1.x library is small: an agent loop, hooks around it, and adapters. The report's wording: "useful only if you call several model providers and want one interface" (report §1).

One thing it does not give: a Rust version. LangChain's organisation has one Rust repository of its own, an unrelated and archived example, plus eight forks of third-party data libraries [M]. The community port is small and published four major versions in two weeks [M] (report §1). The crate by crate detail is in note rust_ecosystem.md, section 1; the verdict for the other Rust building blocks is in [rust.md](rust.md).

## 6. When to use it, when not

| Use it when | Do not use it when |
|---|---|
| You call several providers and want one interface | You call one provider. Use its SDK; the loop is a few dozen lines |
| You want a ready loop with approval and retry, in Python or TypeScript | You drive an existing coding agent. The agent is already the loop |
| You plan to grow into LangGraph or LangSmith and want the shortest path | You need a small dependency tree, strict reproducibility, or a language other than Python or TypeScript |
| | You follow an old tutorial: `LLMChain`, pipes and `AgentExecutor` are the retired API |

(report §2.7; note langchain_langgraph.md §7). The right-hand column of the last row matters when you search the web: much of what is written about LangChain describes the library of 2023.

How widely is it used? Among respondents who build or use agents, 32.9% named LangChain in the Stack Overflow survey of 2025 [M]. A smaller Stack Overflow survey of April 2026 gives 26% in its chart and 22% in its own text, against 27% for the OpenAI Agents SDK [S] (note langchain_langgraph.md §4). The note reads this as: no longer the default, one option among several. Download counts are very high (157 million in 30 days for the Python package [M]) but include CI and mirrors, so they say "very widely installed", not a number of users (note langchain_langgraph.md §3.1).

## 7. You do not need it to drive a coding agent

This is the case of this project and of the flows on [decide.md](decide.md): a ticket goes through steps, and a coding agent such as Claude Code or Codex does the work inside some of them.

- **The loop is already written.** LangChain's remaining value is a ready agent loop and adapters over providers. A coding agent is that loop, with its tools, its sandbox and its permissions. "A team that drives an existing coding agent has no use for it" (report §1).
- **The chaining is not a model problem.** What goes from one step to the next is decided by code: the ticket or the pull request holds the state, a short CI job runs each step (report §1; [decide.md](decide.md), "The default"). No part of that needs a prompt library.
- **The labs do not use it for their own workflows.** They use a plain loop in ordinary code, with checks written as code around it (report §1). Anthropic's advice, in its reference text on agents: "We suggest that developers start by using LLM APIs directly: many patterns can be implemented in a few lines of code", and "if you do use a framework, ensure you understand the underlying code" [M] (note langchain_langgraph.md §5.2).
- **Traces do not require it.** You still need to see what a model did. LangSmith, or any tool based on OpenTelemetry (an open standard for traces), does that without LangChain's libraries (report §2.4, last row). LangSmith is closed source: its Developer plan is free for one seat and 5,000 traces a month, its Plus plan is $39 per seat per month, and self-hosting is on the Enterprise plan only [M] (note langchain_langgraph.md §3.5).

What a ticket workflow does need is elsewhere: state that survives a crash, a wait for a person, replay. Those are the subject of [langgraph.md](langgraph.md), of [engines.md](engines.md) and of [ci-as-engine.md](ci-as-engine.md).

How sure is this? It follows from what the library contains, read in its documentation and repository. It is not a measured comparison, and the sources record none for LangChain on a ticket workflow. The nearest they have: no controlled comparison of CI against an engine on the same workflow exists, and nearly every "we removed it" number is self-reported (report §9.1, items 3 and 11).

## The symptom that would make you need it

You can count each of these in your own code.

- **Two or more model providers called from the same application, in production.** Count the places where your code branches on the provider to format messages, tools or structured output. If there are none, or one provider, you have no use for the adapters.
- **You are writing the agent loop yourself**, in Python or TypeScript, instead of driving a coding agent, and you have written approval, retry with backoff or history summarising a second time. One hand-written loop of a few dozen lines is not the symptom; maintaining the same three hooks in several applications is.
- **You have already decided on LangGraph or LangSmith** for a reason given in [langgraph.md](langgraph.md), and you want the agent that plugs into them without extra code.

If none of the three is true, and above all if the work is done by a coding agent inside the steps of a flow, the answer stays no.
