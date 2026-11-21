# Decision criteria: where does one step of a team workflow go?

Research note, written 2026-11-21. Sources are dated; anything older than 2025 is flagged.

## Summary

1. Every serious source says the same first thing: start with the simplest thing, add a layer only when a measured failure demands it. Anthropic (2024, 2026), OpenAI (2025), HumanLayer, Cognition, Vercel and the Thoughtworks Radar (2026) all agree, and the Radar moved LangGraph from Adopt to Trial in April 2026 for this reason.
2. Six properties decide where a step goes: is the output determined by the inputs, must it happen every time, how long does it live and what must survive, does a human decide in the middle, how many repositories share it, and what does an error cost. Frequency, audit and fan-out refine the answer.
3. A durable workflow engine (Temporal, Restate) is justified by waits and crash recovery, not by "we use agents". A graph framework (LangGraph) is justified only when you build your own agent application with a known graph and need pause and resume inside it. Most team workflows fit in "ticket or pull request as the state, CI jobs as the steps, a coding agent inside each step".
4. Scaffolding that compensates for a model weakness ages fast: context resets, sprint decomposition, think tools, large rule prompts, many specialised tools were all removed between 2025 and 2026 with published numbers. Scaffolding that gives a guarantee, a right, a durable state or a fact the model cannot know did not age: deterministic checks, sandboxes, credentials kept out of reach, session logs, short instruction files, independent review.
5. The project's placement grid already covers one repository well. A team-level version needs eight more things: a time axis, a place for workflow state, human gates by risk tier, a distribution channel across repositories, an owner and a version per shared piece, external triggers, fan-out across repositories, and a budget and audit line per run.

## How to read this note

Each factual claim carries a label:

- **[M] measured**: a number from a study or benchmark with a stated method, by a party that does not sell the thing measured.
- **[V] vendor**: reported by a company about its own product or its own internal system. Often a real measurement, but not reproducible from outside.
- **[S] secondary**: a third party reporting or judging (a consultancy radar, a news site, a practitioner's advice).

"Not found" means I searched and did not find a source. I did not fill the gap.

## 1. Vocabulary

- **Harness**: everything around the model that makes its work reliable: instructions, tools, checks, sandboxes, the loop that calls the model. The Thoughtworks Radar (Vol. 35, 2026-11-04) uses the same definition [S].
- **Workflow** (Anthropic's sense): the code decides the path, the model fills in steps. **Agent**: the model decides the path and which tools to call (Anthropic, 2024-12-19) [V].
- **Instruction line**: one line in `AGENTS.md` or `CLAUDE.md`, loaded in every session.
- **Skill**: a Markdown procedure loaded on demand. Only its description is in context until it is used.
- **Sub-agent**: a second model loop with its own blank context and its own tools, which returns a summary.
- **Plain code**: a CLI or script. Same inputs, same output, with tests.
- **Hook**: a command the agent's runtime runs at a fixed point (before a tool, after an edit, at stop). The model does not choose whether it runs.
- **CI job**: a job on the forge (GitHub Actions or similar), triggered by an event, with its own rights and logs.
- **Durable workflow engine**: a service (Temporal, Restate, DBOS, Inngest) that records every step of a long process so that it resumes after a crash, and can sleep for days waiting for a timer or a signal.
- **Graph framework**: a library (LangGraph is the best known) where you declare nodes and edges; a "checkpointer" saves the graph state so a run can pause and resume.
- **Eval**: a repeatable test of an AI behaviour, graded by code or by a validated judge.

## 2. What the sources say

### 2.1 Anthropic, "Building effective agents" (2024-12-19, older than 2025 but still the reference)

- Start by calling the model API directly; many patterns are a few lines of code. Frameworks hide prompts and responses and tempt you to add complexity. If you use one, understand the code underneath [V].
- Five workflow patterns, each with a "when": prompt chaining (fixed subtasks), routing (distinct categories), parallelization (independent parts, or voting), orchestrator-workers (subtasks unknown in advance), evaluator-optimizer (clear criteria, iteration measurably helps) [V].
- Agents fit open-ended problems where steps cannot be hard-coded and you trust the model. They cost more and errors compound. Use the simplest solution that works [V].
- The page now carries a note that much of the tooling it describes has changed, and points to Managed Agents [V].
- Source: https://www.anthropic.com/engineering/building-effective-agents

### 2.2 OpenAI, "A practical guide to building agents" (PDF dated 2025-04-07)

- Build an agent only where rules fall short: nuanced judgment, rule sets too costly to maintain, heavy unstructured data. If the case does not clearly meet these, a deterministic solution may be enough [V].
- Maximise one agent first. Split into several only when instructions become a maze of branches or tools overlap. Some setups handle more than 15 distinct tools; others fail under 10 overlapping ones [V].
- It criticises declarative graphs (every branch and loop defined up front) as cumbersome when workflows get dynamic, and prefers code-first orchestration [V]. Note that OpenAI sells the code-first SDK.
- Two triggers for human intervention: a failure threshold exceeded, and a high-risk action (sensitive, irreversible, high stakes) [V].
- Source: https://cdn.openai.com/business-guides-and-resources/a-practical-guide-to-building-agents.pdf

### 2.3 LangChain's answer, "How to think about agent frameworks" (Harrison Chase, 2025-04-20)

- The hard part is giving the model the right context at each step. A framework that hides context works against you. Chase agrees that agent abstractions (a class around model, prompt, tools) obscure what reaches the model, including the original LangChain ones [V].
- LangGraph is presented as a lower layer: nodes and edges are ordinary code, plus persistence, pause for a human, streaming, retries [V].
- On "models will get better": simple tool-calling loops will suffice where a model is trained for the task (coding is his example); elsewhere workflows stay simpler, cheaper and faster [V].
- Source: https://www.langchain.com/blog/how-to-think-about-agent-frameworks

### 2.4 HumanLayer, "12-factor agents" (repository, 27,358 stars, last push 2025-09-21)

- Observation: most products sold as agents are mostly deterministic code with model steps at key points. Teams take a framework, reach 70 to 80% quality, then reverse-engineer it and start over [S, practitioner report, no dataset].
- The factors that matter here: own your prompts (2), own your context window (3), unify execution state and business state (5), launch, pause and resume with simple APIs (6), contact humans with tool calls (7), own your control flow (8), small focused agents (10), trigger from anywhere (11), make the agent a stateless reducer (12) [S].
- Factor 8 gives the clearest criterion: you need to pause between the model choosing a tool and the tool running. Three cases: a clarification request stops the loop and waits for a webhook; a fetch continues at once; a deploy stops until a human approves. Without that control you either hold the task in memory, restrict the agent to low-risk work, or accept the risk [S].
- Source: https://github.com/humanlayer/12-factor-agents

### 2.5 Cognition, twice

- "Don't build multi-agents" (Walden Yan, 2025-06-12): share full traces, not messages; every action carries implicit decisions; parallel writers produce conflicting decisions. Default to one single-threaded agent [V].
- "Multi-agents: what's actually working" (2026-04-22): a narrower class now works. Writes stay single-threaded; extra agents bring intelligence, not actions. In production: a reviewer with a clean context (it catches on average 2 bugs per pull request written by Devin, about 58% severe), a call to a stronger model as a tool, and a manager with child agents in a map-reduce shape. Swarms of parallel writers still do not work [V].
- Sources: https://cognition.com/blog/dont-build-multi-agents and https://cognition.com/blog/multi-agents-working

### 2.6 Manus, "Context engineering for AI agents" (2025-07-18)

- The team rebuilt its agent framework four times. The stated goal is to stay independent of model progress rather than be fixed to one model's limits [V].
- Cost lever: about 100 input tokens per output token; cached input costs $0.30 per million tokens against $3 uncached on Claude Sonnet at the time. So keep the prompt prefix stable and the context append-only [V].
- Use the file system as memory; keep errors in context; rewrite a todo file to keep the goal in view (average task: about 50 tool calls) [V].
- Source: https://manus.im/blog/Context-Engineering-for-AI-Agents-Lessons-from-Building-Manus

### 2.6 bis. "The bitter lesson" applied to scaffolding (Lance Martin, 2025-07-30)

The "bitter lesson" (Rich Sutton, 2019) says that general methods which use more computation end up beating hand-built structure. Applied to agents: structure you add to help today's model becomes the bottleneck for tomorrow's.

- One concrete account by a LangChain engineer. In 2024 he built a research tool as a fixed orchestrator-worker workflow and avoided tool calling, because tool calling was unreliable then. As models improved, the fixed structure blocked him: he could not use the growing set of MCP tools, and sections written in parallel gave disjoint reports. He rebuilt it twice, ending with flexible planning, several agents that only gather context, and one final writing pass [V, one person's account; the final system scored 43.5 on Deep Research Bench, his own run].
- His three lessons: know which assumptions about the model your structure encodes; re-test them as models improve; make structure easy to remove [V].
- The same idea, stated by a model vendor a year later with numbers, is in section 5.3.
- Source: https://rlancemartin.github.io/2025/07/30/bitter_lesson/

### 2.7 Anthropic on multi-agent cost and fit (2025-06-13 and 2026-01-23)

- Agents use about 4 times the tokens of a chat; multi-agent systems about 15 times. On one research eval, a lead with sub-agents beat a single agent by 90.2%; token use alone explained about 80% of the variance. Poor fit: shared context, many dependencies, most coding tasks [V].
- 2026: multi-agent uses 3 to 10 times the tokens of a single agent for the same task. Three cases where it wins: context pollution (a subtask that produces more than about 1,000 mostly irrelevant tokens), parallel search, specialisation. Split by context boundary, not by role: in one experiment with planner, implementer, tester and reviewer, the agents spent more tokens coordinating than working. Teams spent months on multi-agent designs that a better-prompted single agent matched [V].
- Sources: https://www.anthropic.com/engineering/multi-agent-research-system and https://claude.com/blog/building-multi-agent-systems-when-and-how-to-use-them

### 2.8 Thoughtworks Technology Radar, Vol. 34 (April 2026) and Vol. 35 (2026-11-04)

All [S]: the opinion of a consultancy, based on its own projects.

- **LangGraph moved out of Adopt to Trial** (Vol. 34). Reason given: treating every system as a stateful graph with a global shared state is not always best; simple agents communicating through code, with graph structure added later when needed, are often leaner and easier to test.
- **Durability** (Vol. 34): ignoring it is called an anti-pattern. Workflows that run for days or weeks need it. Start with the durable execution built into your agent framework; move to a standalone platform when the workflow becomes critical or complex.
- **Temporal and Restate both in Trial** (Vol. 35). Restate is recommended for long processes that wait for a person or retry many times against legacy systems; its server is under the Business Source License. Temporal is cited for internal platforms and infrastructure control planes, not for agent loops.
- **Coding harness for general-purpose agents, Trial** (Vol. 35): teams build non-coding agents on the runtime of a coding agent (Claude Agent SDK, Codex SDK, OpenCode, Pi) instead of assembling a loop with a framework. Less control, a runtime already tested.
- **Risk-tiered human oversight, Trial**; **human-in-the-loop theater, Caution**: reviewing everything with the same intensity ends in empty approvals. Triage: riskiest changes applied by humans, middle tier reviewed, low risk auto-merged through CI.
- **Agent instruction bloat, Caution**: convert every instruction you can into a deterministic hook or check; re-test the rest against each new model and delete what it no longer needs.
- **Agent skill cognitive surrender, Caution**: importing large community skill sets or heavy frameworks without reading them.
- **Enterprise harness, Assess**; **agent plugin marketplace, Trial**: the organisation-wide layer (skills, tools, hooks, policies). Advice: keep it thin and federated; no consensus yet.
- **Subagents for context management, Trial**: the Radar says the benefit rests on practitioners' accounts, without systematic measurement; guideline of two to four sub-agents at a time.
- **Managed agents runtime, Trial**; **unattended overnight agentic builds, Trial**; **harness quality evaluation, Assess**; **agent sandboxing, Adopt**.
- **MCP by default, Caution** (Vol. 34): MCP earns its place for structured tool contracts, OAuth boundaries and governed multi-tenant access; otherwise a well-designed CLI with good `--help` and JSON output often gives the agent everything it needs.
- **Coding agent swarms, Caution** (Vol. 34): dozens to hundreds of agents remain costly and immature; the two public successes (a C compiler, a browser) had detailed specifications and test suites that typical product work lacks.
- **Feedback sensors for coding agents, Trial** (Vol. 34): compilers, linters, structural tests and test suites wired into the agent's session, reporting clean before a commit rather than after.
- **Agent Package Manager, Trial** (Vol. 35): a manifest and lock file for plugins, skills, instructions and MCP servers, with content hashes and provenance; pre-1.0.
- **Context profiling, Assess** (Vol. 35): measure where tokens go before optimising; the biggest savings came from clearing sessions, cache settings and quieter build scripts, not from compression proxies.
- The blip texts were read from the published data set of all blips (https://github.com/setchy/thoughtworks-tech-radar-volumes), because the PDF returned an error on 2026-11-21.
- Sources: https://www.thoughtworks.com/content/dam/thoughtworks/documents/radar/2026/11/tr_technology_radar_vol_35_en.pdf and https://www.thoughtworks.com/content/dam/thoughtworks/documents/radar/2026/04/tr_technology_radar_vol_34_en.pdf

### 2.9 Hamel Husain and Shreya Shankar on evals (FAQ, first published 2025, revised 2026; exact date not confirmed)

All [S]: practitioner advice.

- Error analysis first: read traces yourself (at least 30 to start, about 100 before you stop finding new failure types), then write evaluators for failures you observed. Generic scores (helpfulness, coherence) give false confidence.
- Check with code whenever a rule can identify the failure. Use a model as judge only for what needs judgment, one judge per failure type, binary pass or fail, validated against human labels.
- For multi-step workflows: grade the end result first, then locate failures with a matrix (last step that succeeded against first step that failed).
- CI evals: small curated sets, about 100 examples, mostly deterministic assertions. Production: sample live traces.
- They report spending 60 to 80% of development time on error analysis and evaluation.
- Source: https://hamel.dev/blog/posts/evals-faq/

### 2.10 Teams that run agent workflows at scale

- **Stripe, "Minions"** (2026-02): more than 1,300 merged pull requests per week contain no human-written code; humans review all of them. A run follows a **blueprint**: a state machine in code that alternates deterministic nodes ("run configured linters", "push changes") and agent nodes ("implement task", "fix CI failures"). Stated reason: putting predictable decisions in code saves tokens and CI cost and leaves the model fewer chances to go wrong. At most two CI rounds per run. Disposable dev machines ready in about 10 seconds, no production access. One central MCP server ("Toolshed", nearly 500 tools), each agent gets a small subset. Rules scoped by directory, shared between three agent tools [V]. https://stripe.dev/blog/minions-stripes-one-shot-end-to-end-coding-agents-part-2
- **OpenAI, "Harness engineering"** (2026-02-11): about one million lines and 1,500 pull requests in five months with no hand-written code, three then seven engineers. `AGENTS.md` is about 100 lines and works as a table of contents; the big single file failed. Architecture is enforced by custom linters and structural tests whose error messages tell the agent how to fix. Recurring background agents open small clean-up pull requests. Merge gates are minimal, which the authors say would be irresponsible at low throughput [V]. https://openai.com/index/harness-engineering/
- **Spotify, "Honk"** (2025-11 to 2026-03): a background agent for fleet-wide migrations. The agent has very limited access; a separate verification service runs CI and opens the pull request only after validation. 1,000 merged pull requests now take 10 days. Review, not generation, is the bottleneck [V for the blog, S for the InfoQ report]. https://engineering.atspotify.com/2025/12/feedback-loops-background-coding-agents-part-3 and https://www.infoq.com/news/2026/03/spotify-honk-rewrite

### 2.11 Teams that over-built and removed layers

| Who, when | What they removed | Result | Label |
|---|---|---|---|
| Octomind, mid-2024 (older than 2025) | LangChain, after about a year in production; replaced by plain code and small building blocks | Could change tool availability and move to sub-agents without fighting the framework | V, no numbers |
| Vercel, 2025-12-22 | About 17 specialised tools, heavy prompt engineering, hand-coded retrieval; replaced by a sandbox with shell commands over well-documented files | 5 test queries: success 4/5 to 5/5, time 274.8 s to 77.4 s, tokens about 102k to 61k | V, sample of 5 |
| Anthropic Labs, 2026-03-24 | Context resets, then sprint decomposition and per-sprint evaluation | Kept planner and a final evaluator; see section 5 | V |
| Anthropic Claude Code, 2026-07-24 | Over 80% of the system prompt | The post reports no loss it could measure on in-house coding evals, which are not described. The team lead repeated the figure in a podcast of 2026-07-28 ("we deleted 80% of the system prompt"; "every time that a new model comes out, we delete a bunch") and the Radar Vol. 35 cites it. One secondary article disputes the figure | V, disputed |
| Cursor, 2026-01-14 | Locks shared between agents (20 agents slowed to the output of 2 or 3), a flat structure with no hierarchy, then an "integrator" role for quality control | Kept planners, workers that do not talk to each other, and a judge per cycle. Their words: many improvements came from removing complexity rather than adding it. Runs of about a week, over a million lines | V, no controlled numbers |
| Lance Martin, 2024 to 2025 | A fixed orchestrator-worker workflow without tool calling | Rebuilt twice as models improved (section 2.6 bis) | V |
| Spotify Honk, reported 2026-03-18 | A model-as-judge that proved too rigid, replaced by prompt-based verification as models improved | No number | S |
| Thoughtworks, 2026-04 | LangGraph as the default choice | Moved from Adopt to Trial | S |

Sources: https://octomind.dev/blog/why-we-no-longer-use-langchain-for-building-our-ai-agents, https://vercel.com/blog/we-removed-80-percent-of-our-agents-tools, https://www.anthropic.com/engineering/harness-design-long-running-apps, https://claude.dev/blog/the-new-rules-of-context-engineering-for-claude-5-generation-models/, https://cursor.com/blog/scaling-agents, https://spoken.md/episode/boris-cherny-building-claude-code-1000778651350

## 3. The properties that decide

Ask these in order. The first three settle most cases.

### 3.1 Is the right output determined by the inputs?

If yes, it is code. Stripe's stated reason is the best short argument: code for predictable decisions saves tokens and removes chances to go wrong [V]. The project README already says it: the prompt explains, the code checks, the pipeline executes. If only part is determined, code computes the options and the model chooses among them.

### 3.2 Must it happen every time?

A line or a skill is a request. Claude Code's own documentation says so: an instruction in `CLAUDE.md` or a skill is a request, a hook is enforcement, and a hook costs zero context unless it returns output [V]. Vercel measured the gap for skills: in 56% of eval cases the agent never invoked the available skill, and the default skill scored the same as no documentation (53%) [V, own evals, Next.js APIs only]. So: "should" goes in text, "must for the agent" in a hook, "must for everyone" in a required CI check, "must for every repository" in an organisation ruleset or managed settings.

### 3.3 How long does it live, and what must survive?

This is the axis the single-repository grid lacks.

| Lifetime | What must survive | Fits |
|---|---|---|
| Seconds to minutes, inside one session | Nothing | The session, a skill, a sub-agent |
| Minutes to hours, unattended, restart from zero is acceptable | The result | A CI job or a managed agent runtime (a hosted place that runs the agent loop in a sandbox) |
| Hours to days, with waits, each step can be redone safely | Which step we are at | State in the ticket or pull request; each event triggers a short job |
| Days to weeks, many waits, timers, retries against fragile systems, side effects that must not run twice | Every step and its result | A durable workflow engine |

Hard limits that make this concrete [V, GitHub docs]: a job on a GitHub-hosted runner stops at 6 hours (5 days self-hosted); a workflow run at 35 days; an environment approval can wait 30 days. So CI can hold a human approval for a month, but a single job cannot hold a week-long process in memory. The state must live somewhere else.

Model capability moves the first two rows. METR's report of 2026-05-19 measured, for the public frontier in February and March 2026, a 50% time horizon of about 12 hours (95% range 5 to 61 hours) and an 80% horizon of about 1.5 hours; its task suite cannot measure reliably above 16 hours, and METR states that benchmark results have consistently overstated real-world ability [M]. Read plainly: a model finishes half of the 12-hour tasks, and four out of five of the 1.5-hour tasks. Long unattended steps are possible; checkpoints and verification between steps are still needed.

### 3.4 Does a human decide in the middle?

- A human who can judge a diff: the pull request review is the gate. No new machinery.
- A human who approves an irreversible action: a protected environment in the delivery pipeline. The project grid already has this.
- Several approvals, timeouts, escalation, across systems (ticket tracker, chat, forge): this is where a durable engine or a framework's interrupt earns its place. LangGraph's interrupt saves the graph state through a checkpointer and waits until resumed; a durable saver such as Postgres is needed in production [V, LangChain docs].
- Do not add an approval the human cannot evaluate. The Radar names this "human-in-the-loop theater" and recommends tiers by risk [S].

### 3.5 How many repositories and teams?

One repository: a file in the repository. Several: the piece must be distributed, versioned and owned. Channels that exist today: plugin marketplaces (Radar, Trial [S]), a central MCP server (Stripe [V]), reusable or required CI workflows, managed settings. Claude Code's managed settings sit above every other level and include locks such as `allowManagedHooksOnly`, `allowManagedPermissionRulesOnly`, `allowManagedMcpServersOnly` and `strictKnownMarketplaces` [V, docs]. The Radar's advice for this layer: thin, federated, harvest what works [S].

### 3.6 What does an error cost?

OpenAI's two triggers (failure threshold, high-risk action) [V] and the Radar's three tiers [S] give the same table: cheap and reversible, the agent acts and is reviewed after; costly but reversible, a gate before merge; irreversible or regulated, the agent prepares and a pipeline with a human approval executes.

### 3.7 Refinements

- **Frequency.** Claude Code's documentation gives triggers by repetition: wrong twice, add an instruction line; the same playbook pasted a third time, make a skill; a second repository needs it, make a plugin [V]. At hundreds of runs a week, Stripe moved the fixed parts into code and capped CI rounds [V].
- **Audit trail.** Git, the pull request and CI logs answer "who changed what". They do not answer "which steps did the agent take, with which model and prompt version, at what cost". For that, the session log must be stored outside the sandbox; Anthropic made this the centre of its Managed Agents design (an append-only log, from which a crashed harness resumes) [V]. A workflow engine's history gives it for free.
- **Fan-out.** Inside a session: two to four sub-agents, one writer (Radar [S], Cognition [V]). Across tens or hundreds of units (repositories, files): a script decides, not the model. Claude Code now has "dynamic workflows", a script that runs many sub-agents and returns one result [V, docs]; a CI matrix or fleet tooling does the same across repositories.
- **An in-session workflow script is not a durable engine.** The Claude Code documentation is explicit about the limits of dynamic workflows [V, docs read 2026-11-21]: no user input in the middle of a run ("for sign-off between stages, run each stage as its own workflow"); a run is resumable in the same session, and does not continue on its own if the session exits; 16 agents at once by default, 1,000 agents per run at most; the script may not read the clock or random numbers, so that a relaunch repeats the same calls; a warning appears above 25 agents or 1.5 million projected tokens. So it covers fan-out and cross-checking inside hours, not waits of days or approvals between steps.
- **Is this step here because the model is weak today?** If yes, it is temporary. See section 5.

## 4. The eight destinations, one by one

| Destination | Right when | Wrong when | Cost | Ages? |
|---|---|---|---|---|
| **Instruction line** | Every task needs it and the agent cannot find it by reading the repository: a non-standard command, a trap | It is a procedure, a rule that must hold, or something the code already shows | Paid on every request. A study found context files raise inference cost by over 20% with no gain in task success on average [M] | Rules written for a weaker model age; facts about the repository do not |
| **Skill** | A procedure for one type of task, with judgment in it; team-specific knowledge | The step must always happen (56% not invoked in Vercel's evals [V]); or it is a computation | Description on every request, body when used | Generic skills age (Radar [S]); team-specific ones less |
| **Sub-agent** | Blank context is the point: independent review, reading a lot, narrower rights, parallel reading | Splitting by role (planner, coder, tester); two writers on the same thing | 3 to 10 times the tokens of one agent [V] | The need for a separate verifier shrinks as the orchestrating model improves (Anthropic, 2026 [V]); independence does not |
| **Plain code (CLI, script)** | The output is determined by the inputs; several callers need the same answer (agent, human, CI) | The step needs interpretation of free text | Writing and testing once; near zero per run | No |
| **Hook** | Must happen at a fixed point of the agent's loop, the agent alone is the risk | Humans must also be bound (they can skip it); long-running work | Zero context unless it returns output [V] | No, but hooks that nag about a model habit do |
| **CI job** | Must bind everyone on the repository; needs rights the agent must not have; triggered by an event with nobody present | State must persist between runs beyond a ticket or pull request; sub-minute feedback is needed | Runner minutes; 6 h job limit hosted [V] | No |
| **Durable workflow engine** | Days to weeks, waits on humans or events, retries against fragile systems, steps that must not run twice, full history required | The process fits in pull request events; a restart from zero is acceptable | Engine fee is small (section 6); the real cost is one more system to run and to know | No |
| **Graph framework (LangGraph)** | You build your own agent application; the graph (branches, loops) is known; you need checkpointing and pause-resume inside the process | The step already runs inside a coding agent (use skills and hooks); a plain sequence (use code); the process spans services and weeks (use an engine) | A dependency that moves fast (version 1.2.24 on 2026-11-20, 45,231 stars [M]); a team that knows it | The Radar moved it from Adopt to Trial in April 2026 [S] |

Two intermediate options appeared in 2026 and reduce the need for the last two rows:

- **Agentic workflows in CI.** GitHub Agentic Workflows became generally available on 2026-10-28: a Markdown file compiled to a standard Actions workflow, agent read-only by default, writes only through validated "safe outputs", a threat-detection job before changes apply [V]. https://github.blog/changelog/2026-10-28-github-agentic-workflows-generally-available
- **Managed agent runtimes.** A hosted loop with sandbox, triggers, credentials and session state (Claude Managed Agents, Codex cloud tasks, Copilot coding agent, Cursor cloud agents). Radar: Trial [S].

Engines and frameworks also converge: Temporal has integrations with the OpenAI Agents SDK (generally available 2026-03-23), Pydantic AI and LangGraph (preview, July 2026) [V, Temporal; the LangGraph preview date is from secondary sources]. Choosing an agent library no longer forces the choice of where durability lives.

## 5. The "scaffolding ages" problem

### 5.1 What became useless, with evidence

| Scaffolding | Why it existed | What happened | Label |
|---|---|---|---|
| Context resets (throw away the window, restart with a handoff note) | Claude Sonnet 4.5 wrapped up early near its context limit | On Opus 4.5 the behaviour was gone; the resets were dead weight and were dropped. Reported in two Anthropic posts (2026-03-24, 2026-04-08) | V |
| Sprint decomposition and an evaluator after every sprint | The model lost coherence on long builds | Removed for Opus 4.6; the builder ran coherently for over two hours. Full harness on Opus 4.5: 6 h, $200. Simplified on Opus 4.6: 3 h 50 min, $124.70. Different applications, so not a controlled comparison | V |
| "Think" tool (a no-op tool that gives room to reason) | Claude 3.7 needed a place to reason between tool calls; +54% relative on one benchmark domain (2025-03-20) | Note added 2025-12-15: use extended thinking instead in most cases | V |
| Many specialised tools and hand-coded retrieval | Constrain a weaker model's choices | Vercel removed about 80% of them; better on all four metrics on 5 queries | V, n=5 |
| Large rule-and-example system prompts | Guard against worst-case behaviour of older models | Claude Code cut over 80% for the Claude 5 generation; tool description for the todo tool went from about 9,100 characters to one line and an enum | V, disputed by one secondary source |
| Emphatic prompts ("CRITICAL", "MUST"), anti-laziness prompts, prefilled answers | Older models under-used tools and ignored instructions | Anthropic's prompting guide: these now cause over-triggering on Opus 4.5 and later; prefill returns an error from the 4.6 models | V, docs |
| Two-model edit (one describes, one rewrites the file) | 2024 models could not write reliable diffs | Single-model edits by mid-2025 | V, Cognition |
| Repository overviews in context files | Help the agent orient | No gain in task success, over 20% more inference cost, across agents and models. The authors keep one use: non-standard practices. arXiv 2602.11988, v3 2026-09-29 | M |
| Complex agent scaffolds for bug fixing | Structure the search | A roughly 100-line agent with only a shell scores above 74% on SWE-bench Verified with a frontier model (project's own README; the benchmark's "bash-only" board uses it to compare models) | V |
| "Never build multi-agents" | 2025 models could not hand over context | A narrow class works in 2026 (section 2.5) | V |
| "Keep each agent to 3 to 10 steps, 20 at most" (12-factor agents, factor 10, 2025) | Models lost focus as context grew | The factor itself said to widen scope as models improve. By February 2026 OpenAI reported single runs of over six hours on one task [V]; METR measured a 50% time horizon of about 12 hours [M]. The reason behind the rule (bounded scope, verifiable steps) holds; the number does not | S, then V and M |
| MCP as the default way to reach every external system | Give the model typed tools | Radar Vol. 34 puts "MCP by default" in Caution; Claude Code's cost page says CLI tools such as `gh` or `aws` are more context-efficient because they add no tool listing | S, V |
| Locks and an integrator agent to coordinate parallel agents | Prevent conflicts | Cursor removed both; workers resolved conflicts themselves (section 2.11) | V |

Two more are predictions, not evidence: LangChain expects its loop-detection guardrails to dissolve as models improve (2026-02-17) [V, opinion]; the Radar expects generic community skills to become obsolete [S, opinion].

### 5.2 What did not age, with evidence

| Piece | Evidence | Label |
|---|---|---|
| Deterministic checks, linters, tests, CI gates | OpenAI enforces architecture with custom linters over a million agent-written lines; Stripe keeps deterministic nodes and CI; the Radar says convert instructions to hooks and checks first | V, V, S |
| Sandboxes and credentials out of reach | Radar: agent sandboxing in Adopt. Anthropic moved tokens out of the sandbox because a prompt injection only had to make the model read its environment. OpenAI stated on 2025-12-22 that prompt injection remains an open problem it expects to work on for years | S, V, V |
| Durable state outside the process | Anthropic: session log outside the harness, a crashed harness resumes from the last event; p50 time to first token fell about 60%, p95 over 90% after the split. Radar: Temporal and Restate in Trial | V, S |
| The harness as a whole | LangChain moved its agent from 52.8% to 66.5% on Terminal-Bench 2.0 with the model fixed (gpt-5.2-codex), by changing only the harness. The pieces change; having a harness does not stop paying | V |
| A plan or specification up front, and an independent check at the end | Both survived Anthropic's simplification: without the planner the builder under-scoped; the final QA still caught real gaps. Cognition's clean-context reviewer: 2 bugs per pull request on average | V |
| A short file of facts the model cannot know | Vercel: an 8 KB index of documentation for APIs absent from training data gave 100% against 53% without. The arXiv study and Anthropic's 2026 post agree on the narrow use: non-standard practices and traps | V, M, V |
| Evals and reading traces | Anthropic's method for pruning is to remove one component at a time and re-measure; without evals there is no way to know what to delete | V |
| Human review of risky changes | Stripe and Spotify still review every agent pull request; review is now the bottleneck at Spotify | V, S |

### 5.3 The rule that follows

Anthropic states it directly (2026-03-24): every harness component encodes an assumption about what the model cannot do alone, and those assumptions go stale [V]. A usable test for each piece:

- It **compensates for a model weakness** (forgets, stops early, loops, picks the wrong tool): put it in the cheapest layer (a line, a skill, a small middleware), write the model and date next to it, and re-test at each model release. The Radar calls this "progression testing" [S].
- It gives a **guarantee** (a check), a **right** (a permission, a credential boundary), a **state** (where the process stands) or a **fact** the model cannot derive: it belongs in code, CI, the sandbox or the engine, and it is durable.

This matches the project's own layers: L1 and L2 age, L3 and L4 do not. The consequence for a team harness: invest in L3 and L4, keep L1 and L2 thin and dated.

A caution on the evidence: almost every "we removed it and nothing broke" number is self-reported, on in-house evals, often on a handful of cases. The only independent measurement in the table is the arXiv study.

## 6. Cost

### 6.1 Tokens

- Agent against chat: about 4 times. Multi-agent against chat: about 15 times (Anthropic, 2025) [V]. Multi-agent against single agent on the same task: 3 to 10 times (Anthropic, 2026) [V].
- A three-agent harness against a solo run on the same brief: $200 and 6 hours against $9 and 20 minutes; the solo result was judged much worse (Anthropic, 2026-03-24) [V].
- Always-loaded context: over 20% more inference cost for context files (arXiv 2602.11988) [M].
- Caching: a tenfold price gap between cached and uncached input on the model Manus used [V]. A harness that changes its prompt prefix on every call pays full price.
- More reasoning is not free: running at the highest reasoning level throughout scored 53.9% against 63.6% at the level below, because of timeouts (LangChain, 2026-02-17) [V].
- Order of magnitude per developer: Anthropic reports about $13 per developer per active day for Claude Code across enterprise deployments, $150 to $250 per month, under $30 per active day for 90% of users [V, docs read 2026-11-21]. "Agent teams" (several sessions with a lead) use about 7 times the tokens of a standard session when teammates run in plan mode [V, same page].
- List prices on 2026-11-21, per million tokens, input then output [V, pricing page]: Claude Haiku 5.5 $0.10 and $0.50 (prompts up to 100,000 tokens); Sonnet 5.5 $2 and $10; Opus 5.5 $4 and $20; Fable 5.2 $8 and $40. A cache read costs 0.025 to 0.1 times the input price depending on the model. The batch interface halves both prices. The gap between the cheapest and the dearest model is 80 times: which model runs a step matters more than most harness choices. A managed session adds $0.08 per running hour.
- A model used as judge is not a cheap check: Husain and Shankar say a judge needs over 100 labelled examples and weekly upkeep, against assertions that are cheap to build and keep [S].

### 6.2 Latency

- Each round trip through the model for a decision that code could make adds seconds. Vercel's simplification cut average time from 274.8 s to 77.4 s [V, n=5].
- Sub-agents in parallel shorten wall-clock time for searches, but total work often takes longer [V, Anthropic 2026].
- CI as a feedback loop is slow by nature. Stripe runs a lint subset locally in under 5 seconds before pushing, and caps CI at two rounds [V].

### 6.3 Operating a workflow engine

- Temporal Cloud list price on 2026-11-21: $50 per million actions for the first 5 million, falling to $25 at high volume; pay-as-you-go has no base fee; the Business plan starts at $500 per month. An action is each activity start or retry, timer, signal, query or workflow start [V, pricing page].
- My arithmetic, not a source: a ticket workflow of 10 steps at about 10 actions per step is 100 actions. At 1,000 tickets a month that is 100,000 actions, about $5. The engine fee is negligible next to tokens. The cost is elsewhere: one more system, a programming model with rules (workflow code must be deterministic and versioned for in-flight runs), and people who know it.
- LangSmith Deployment (the hosted LangGraph server): Plus plan $39 per seat per month, compute metered in units of $1 [V, pricing page].
- Restate: SDKs under MIT, server under the Business Source License [S, Radar; M for the repository: 4,729 stars, release 1.8.1 on 2026-10-21]. Temporal server: MIT, 24,531 stars, release 1.32.2 on 2026-11-02 [M].
- A lighter class exists: durable execution as a library on a database you already run. DBOS describes itself as Postgres-only, with no separate orchestration server, and claims to be 2 to 10 times cheaper to run than Temporal [V, a vendor comparing itself to a competitor; not independently measured]. Pydantic AI documents integrations with Temporal, DBOS, Prefect, Restate and others [V, docs], which matches the Radar's advice to start with the durability built into the agent library.
- Staffing needed to self-host Temporal or Restate: **not found** in a citable source.
- In-flight versions are a real operating cost with any long-running agent: Anthropic deploys by shifting traffic gradually while old and new versions run side by side, because agents may be mid-task [V].

### 6.4 People

- OpenAI's team first spent every Friday, about 20% of the week, cleaning up agent output by hand, then encoded the principles and let background agents do it [V].
- Hamel Husain and Shreya Shankar report 60 to 80% of development time on error analysis and evals in their projects [S].
- The Radar calls the harness a living asset that needs ongoing ownership, and expects an "enterprise harness" role similar to platform engineering [S].
- Size of the platform teams behind Stripe's and Spotify's agents: **not found**.
- A published total cost of ownership comparing "CI plus ticket state" with "durable engine" for a software delivery workflow: **not found**.

## 7. What a team-level, multi-repository grid needs in addition

The existing grid (`cli/harnesslib/placement.json`) asks what a piece does (acts, limits, requires, computes, judges, chains steps, informs), then who must not bypass it, when it runs, and whether it needs isolation. It has 20 destinations, from "nothing to write" to "organisation managed settings". It already contains two team-level answers: `managed` and `org_check`.

What it does not ask, and a team workflow needs:

1. **A time axis.** The `when` question offers on demand, a point in the agent loop, or a repository event. It has no answer for "this step waits three days for a product owner" or "this must resume after a crash at step 7 of 12". New question: how long does the step live and what must survive (section 3.3). New destinations: `ticket_state` (the ticket or pull request carries the state; events trigger short jobs) and `durable_workflow`.

2. **A place for workflow state.** The grid places pieces of behaviour, not the state of a ticket moving through phases. A team workflow needs one answer to "where do we read that this ticket is at QA, attempt 2". Options, cheapest first: labels and status on the ticket or pull request; a state file committed on the branch; an engine's history. HumanLayer's factor 5 (one state, not an execution state and a business state side by side) is the criterion [S].

3. **Human gates by risk tier.** The grid has one gate: the protected environment of the delivery pipeline. A ticket workflow has several (is the ticket ready, is the plan accepted, is the change approved, may it ship). New question: can the person genuinely judge what they approve, and how long may they take. Destinations: pull request review, required reviewers on an environment (up to 30 days wait [V]), a durable signal. And one destination that is a refusal: "no gate here" when the approval would be theater.

4. **A distribution channel across repositories.** Today a procedure goes to `.claude/skills/` in one repository. New question after every "skill", "CLI", "hook", "workflow" answer: who else needs this. Destinations: a versioned plugin in a marketplace, a reusable CI workflow called from each repository, a shared CLI package, a central MCP server with a per-agent subset. The project already ships its two plugins this way; the grid does not say when to do so.

5. **An owner, a version and a retirement date per shared piece.** A file in a repository is owned by the repository. A shared skill or required workflow needs a named owner, a version teams can pin, a way to roll out gradually, and, for L1 and L2 pieces, the model and date it was last tested against (section 5.3).

6. **Triggers that are not repository events.** A ticket moved in the tracker, a message in chat, an alert, a schedule across repositories. The grid's `workflow` destination assumes PR, push or schedule. New options: a webhook that dispatches a CI run, a managed agent runtime, or the engine.

7. **Fan-out across repositories.** The grid's `parallel` answer means sub-agents inside one session. A migration over 200 repositories is a different thing: a script enumerates the units, one writer per repository, one pull request each, a campaign view of progress. Destination: `campaign` (CI matrix, dynamic workflow script or fleet tooling), never a swarm.

8. **Budget and audit per run.** No question in the grid mentions cost or trace. A team needs, per workflow run: a ceiling (tokens, CI rounds, wall-clock), an identity for the agent (a bot account or app, not a developer's token), credentials the sandbox cannot read, and a log stored outside the sandbox that says which step ran with which model and harness version.

Three smaller additions:

- **Where it runs.** L4 today means CI or a pipeline. Add the developer machine against a managed runtime as an explicit choice for unattended steps, because rights and sandboxing differ.
- **Local override rules.** Three tiers (organisation, team, repository) with stated precedence. The ai-sdlc plugin's extension points read on the target branch are already a good repository-level pattern; the team level needs to say which organisation rules a team may tighten but not loosen.
- **A fleet view.** `harness status` measures one repository. A team needs the same measure across its repositories, and the drift between them.

What should not be added: a question that leads to "graph framework" as a destination for steps inside a coding agent. On the evidence above, a graph framework is a choice of implementation for a custom agent application, not a layer of a repository or team harness.

## 8. Draft decision table

Rows are questions, asked in this order. Each cell says where the step goes. The first row that gives a firm answer wins; later rows refine.

| # | Question | Answer A | Answer B | Answer C | Answer D |
|---|---|---|---|---|---|
| 1 | Is the right output determined by the inputs? | **Yes** → plain code: a tested CLI subcommand. Never a prompt | **Partly** → code computes the options and the facts; a skill tells the agent to choose among them | **No, it needs interpretation** → the agent, through a skill (row 9 says whether a sub-agent) | **It is a fact, not a step** → an instruction line if needed on every task and not discoverable; otherwise a document read on demand, or nothing |
| 2 | Must it happen every time? | **No, it is advice** → instruction line or skill | **Yes, for the agent** → a hook that calls the code from row 1 | **Yes, for everyone on the repository** → a required CI check | **Yes, for every repository** → organisation ruleset or required workflow, and managed settings for the agent |
| 3 | How long does it live, and what must survive? | **Minutes, in one session** → stays in the session | **Up to a few hours, unattended, restart is acceptable** → a CI job or a managed agent runtime | **Hours to days, with waits, steps are safe to redo** → state on the ticket or pull request; each event triggers a short CI job | **Days to weeks, many waits or timers, steps must not run twice, or full replay is required** → durable workflow engine |
| 4 | Does a human decide in the middle? | **No** → no gate; do not add one for comfort | **Yes, on a diff they can judge** → pull request review, depth set by risk tier | **Yes, before an irreversible action** → protected environment in the delivery pipeline; the agent only prepares | **Yes, several people, with timeouts and escalation across systems** → durable engine signal; or a graph framework interrupt if the wait is inside your own agent application |
| 5 | What does an error cost? | **Little, and reversible** → the agent acts; review after, or auto-merge through CI | **Much, but reversible** → gate before merge: CI check plus human review | **Irreversible or regulated** → pipeline with human approval and dry-run; agent has no rights to do it | **Unknown** → treat as C until measured |
| 6 | How many repositories and teams use it? | **One repository** → a file in that repository | **Several repositories, one team** → a versioned plugin plus a reusable CI workflow | **Several teams** → marketplace entry with an owner; shared MCP server for external systems; required workflow for what must hold | **Everyone, no exception** → managed settings and organisation rulesets |
| 7 | How often does it run? | **A few times a year** → a document or a hand-invoked skill; automate nothing | **Weekly** → skill plus CLI | **Daily, triggered by events** → CI job or agentic workflow in CI | **Hundreds a week** → a blueprint: code-driven sequence with agent steps, cost caps and a cap on CI rounds |
| 8 | What audit trail is required? | **None beyond git** → nothing more | **Who changed what, approved by whom** → pull request, CI logs, branch protection | **Which steps the agent took, with which model and version, at what cost** → session log stored outside the sandbox | **Step-by-step replay for compliance** → durable engine history |
| 9 | Does the work split into parts? | **No** → one agent, one context | **A few independent parts that read a lot, or a check that must be independent** → two to four sub-agents; one writer | **Tens or hundreds of independent units** → a script fans out (CI matrix, dynamic workflow, fleet tooling); one writer per unit | **Parts that must coordinate while running** → do not parallelise; redesign into a sequence |
| 10 | What shape is the control flow? | **A fixed sequence** → a script or CI steps calling the model at given points | **Branches and loops known in advance, inside a coding agent** → a skill for the order, hooks and CLI for the fixed points | **Branches and loops known in advance, in your own agent application, with pause and resume** → a small state machine in code, or a graph framework | **Unknown until run time** → an agent loop on an existing coding harness |
| 11 | Is this piece here because today's model is weak? | **Yes** → cheapest layer (line, skill); write model and date; re-test at each model release; delete when it no longer changes the result | **No, it is a guarantee** → code, hook or CI | **No, it is a right or a boundary** → permission, sandbox, credential scope, server-side protection | **No, it is state or a fact** → ticket, engine, or a short instruction line |

How to use it on a workflow such as "feature ticket to production":

1. List the steps (is the ticket ready, plan, code, tests, security, review, merge, delivery, watch).
2. Pass each step through rows 1, 2 and 3. Most land in "skill plus CLI", "hook" or "CI job".
3. Look at the whole workflow through rows 3 and 4. If no step lands in column D of either row, the workflow needs no engine and no graph framework: the ticket and the pull request hold the state.
4. Apply row 6 to every piece that more than one repository needs.
5. Apply row 11 to every piece in L1 and L2 and write the date.

A first reading of the project's own ai-sdlc flow through this table: every phase lands in columns A to C. The only candidates for column D of row 3 are a delivery that waits days between environments and an incident follow-up that waits for a fix. This is a hypothesis to test on real team workflows, not a result.

## 9. Not found, and limits of this note

- No independent, controlled comparison of "CI plus ticket state" against a durable engine for software delivery workflows.
- No sourced staffing figure for operating Temporal or Restate, nor for the platform teams behind Stripe's and Spotify's agents.
- No independent replication of the "we removed it and nothing broke" claims; the 80% system prompt claim is disputed by one secondary article.
- The exact publication date of the Husain and Shankar FAQ could not be confirmed (first published in 2025, revised in 2026).
- Sub-agents for context management: the Radar itself says the benefit has not been measured systematically.
- The Temporal LangGraph integration date (preview, July 2026) comes from secondary sources.
- Whether these frameworks and engines exist in Rust was not researched here; it is another note's topic.
- Most evidence comes from very large engineering organisations or from model vendors. Little is published by teams of five to fifty people with ten to a hundred repositories, which is the likely user of a team harness.

## Sources

Primary, read for this note (fetched 2026-11-21):

- Anthropic, "Building effective agents", 2024-12-19: https://www.anthropic.com/engineering/building-effective-agents
- Anthropic, "How we built our multi-agent research system", 2025-06-13: https://www.anthropic.com/engineering/multi-agent-research-system
- Anthropic, "Building multi-agent systems: when and how to use them", 2026-01-23: https://claude.com/blog/building-multi-agent-systems-when-and-how-to-use-them
- Anthropic, "Harness design for long-running application development", 2026-03-24: https://www.anthropic.com/engineering/harness-design-long-running-apps
- Anthropic, "Scaling Managed Agents: decoupling the brain from the hands", 2026-04-08: https://www.anthropic.com/engineering/managed-agents
- Anthropic, "The new rules of context engineering for Claude 5 generation models", 2026-07-24: https://claude.dev/blog/the-new-rules-of-context-engineering-for-claude-5-generation-models/
- Anthropic, "The think tool", 2025-03-20, note of 2025-12-15: https://www.anthropic.com/engineering/claude-think-tool
- Anthropic, prompting best practices (migration notes): https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices
- Claude Code docs, "Extend Claude Code" (feature comparison, context cost): https://code.claude.com/docs/en/features-overview
- Claude Code docs, hooks guide: https://code.claude.com/docs/en/hooks-guide
- Claude Code docs, settings and precedence: https://code.claude.com/docs/en/settings
- Claude Code docs, managed settings: https://code.claude.com/docs/en/managed-settings
- OpenAI, "A practical guide to building agents", PDF dated 2025-04-07: https://cdn.openai.com/business-guides-and-resources/a-practical-guide-to-building-agents.pdf
- OpenAI, "Harness engineering: leveraging Codex in an agent-first world", 2026-02-11: https://openai.com/index/harness-engineering/
- OpenAI, "Hardening Atlas against prompt injection", 2025-12-22 (read through press coverage): https://openai.com/index/hardening-atlas-against-prompt-injection and https://techcrunch.com/2025/12/22/openai-says-ai-browsers-may-always-be-vulnerable-to-prompt-injection-attacks/
- HumanLayer, "12-factor agents": https://github.com/humanlayer/12-factor-agents (factor 6: https://github.com/humanlayer/12-factor-agents/blob/main/content/factor-06-launch-pause-resume.md, factor 8: https://github.com/humanlayer/12-factor-agents/blob/main/content/factor-08-own-your-control-flow.md)
- Cognition, "Don't build multi-agents", 2025-06-12: https://cognition.com/blog/dont-build-multi-agents
- Cognition, "Multi-agents: what's actually working", 2026-04-22: https://cognition.com/blog/multi-agents-working
- Manus, "Context engineering for AI agents: lessons from building Manus", 2025-07-18: https://manus.im/blog/Context-Engineering-for-AI-Agents-Lessons-from-Building-Manus
- LangChain, "How to think about agent frameworks", 2025-04-20: https://www.langchain.com/blog/how-to-think-about-agent-frameworks
- LangChain, "Improving Deep Agents with harness engineering", 2026-02-17: https://www.langchain.com/blog/improving-deep-agents-with-harness-engineering
- LangChain docs, interrupts and persistence: https://docs.langchain.com/oss/python/langgraph/interrupts and https://docs.langchain.com/oss/python/langgraph/durable-execution
- LangChain pricing: https://www.langchain.com/pricing
- Vercel, "We removed 80% of our agent's tools", 2025-12-22: https://vercel.com/blog/we-removed-80-percent-of-our-agents-tools
- Vercel, "AGENTS.md outperforms skills in our agent evals", 2026-01-27: https://vercel.com/blog/agents-md-outperforms-skills-in-our-agent-evals
- Gloaguen et al., "Evaluating AGENTS.md: are repository-level context files helpful for coding agents?", arXiv 2602.11988, v1 2026-02-12, v3 2026-09-29: https://arxiv.org/abs/2602.11988
- Stripe, "Minions: Stripe's one-shot, end-to-end coding agents", 2026-02-09, and part 2: https://stripe.dev/blog/minions-stripes-one-shot-end-to-end-coding-agents and https://stripe.dev/blog/minions-stripes-one-shot-end-to-end-coding-agents-part-2
- Spotify, "Background coding agents: predictable results through strong feedback loops (Honk, part 3)", 2025-12-09: https://engineering.atspotify.com/2025/12/feedback-loops-background-coding-agents-part-3
- Thoughtworks Technology Radar Vol. 35, 2026-11-04: https://www.thoughtworks.com/content/dam/thoughtworks/documents/radar/2026/11/tr_technology_radar_vol_35_en.pdf
- Thoughtworks Technology Radar Vol. 34, April 2026: https://www.thoughtworks.com/content/dam/thoughtworks/documents/radar/2026/04/tr_technology_radar_vol_34_en.pdf
- Husain and Shankar, "AI evals: everything you need to know" (FAQ): https://hamel.dev/blog/posts/evals-faq/
- METR, "Frontier risk report (February to March 2026)", 2026-05-19: https://metr.org/blog/2026-05-19-frontier-risk-report/
- Temporal pricing: https://temporal.io/pricing
- Temporal, OpenAI Agents SDK integration: https://temporal.io/blog/announcing-openai-agents-sdk-integration
- GitHub, "GitHub Agentic Workflows generally available", 2026-10-28: https://github.blog/changelog/2026-10-28-github-agentic-workflows-generally-available
- Lance Martin, "Learning the bitter lesson", 2025-07-30: https://rlancemartin.github.io/2025/07/30/bitter_lesson/
- Cursor, "Scaling long-running autonomous coding", 2026-01-14: https://cursor.com/blog/scaling-agents
- Anthropic, "Effective harnesses for long-running agents", 2025-11-26 (feature list file, progress file and git as the state between sessions): https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents
- Claude Code docs, dynamic workflows (limits, resume, cost warning): https://code.claude.com/docs/en/workflows
- Claude Code docs, costs (per-developer averages, agent teams): https://code.claude.com/docs/en/costs
- Claude API pricing, read 2026-11-21: https://platform.claude.com/docs/en/about-claude/pricing
- Temporal Cloud pricing (docs page): https://docs.temporal.io/cloud/pricing
- HumanLayer, factor 10, small focused agents: https://github.com/humanlayer/12-factor-agents/blob/main/content/factor-10-small-focused-agents.md
- Y Combinator Startup Podcast, "Boris Cherny: Building Claude Code", 2026-07-28 (transcript excerpt; the rest is behind a paywall): https://spoken.md/episode/boris-cherny-building-claude-code-1000778651350
- Thoughtworks Radar blips as data (all volumes, CSV): https://github.com/setchy/thoughtworks-tech-radar-volumes
- DBOS, comparison with Temporal (vendor page): https://docs.dbos.dev/explanations/comparing-temporal
- Pydantic AI, durable execution overview: https://pydantic.dev/docs/ai/durable-execution/overview/
- GitHub Actions limits: https://docs.github.com/en/actions/reference/limits
- GitHub environments (reviewers, wait timer): https://docs.github.com/en/actions/reference/workflows-and-actions/deployments-and-environments
- mini-swe-agent repository (9,926 stars, pushed 2026-11-16): https://github.com/SWE-agent/mini-swe-agent

Secondary, used for facts I could not read at the source:

- InfoQ on Spotify Honk at QCon London, 2026-03-18: https://www.infoq.com/news/2026/03/spotify-honk-rewrite
- Octomind, "Why we no longer use LangChain for building our AI agents", mid-2024 (page not reachable on 2026-11-21; read through search excerpts): https://octomind.dev/blog/why-we-no-longer-use-langchain-for-building-our-ai-agents
- Dispute of the 80% system prompt figure: https://we0.ai/articles/claude-code-cut-80-of-its
- LangChain's own comparison with Temporal (vendor page): https://www.langchain.com/resources/langgraph-vs-temporal

Repository figures (stars, last push, last release) were read with the GitHub API on 2026-11-21: langchain-ai/langgraph 45,231 stars, release 1.2.24 (2026-11-20); temporalio/temporal 24,531 stars, release 1.32.2 (2026-11-02); restatedev/restate 4,729 stars, release 1.8.1 (2026-10-21); github/gh-aw 5,671 stars, release 1.2.2 (2026-11-10); humanlayer/12-factor-agents 27,358 stars, last push 2025-09-21; pydantic/pydantic-ai 21,325 stars; inngest/inngest 6,066 stars; dbos-inc/dbos-transact-py 1,695 stars.
