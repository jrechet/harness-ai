# Gap note: does "ticket holds the state, CI runs the steps" hold for a small team, and what does a run cost?

Research note, written 2026-11-21. It adds to the seven notes in this folder; it does not repeat them.

## Summary in five lines

1. The recommendation survives the test, but as a default with named exit conditions, not as a proven result. No first-hand account was found of a team of 5 to 50 engineers running an internal ticket-to-PR flow on a durable engine. The small-scale evidence that exists is issue trackers of open-source orchestrators, and it shows that the home-made daemon and the webhook orchestrator fail in exactly the ways CI does not (lost sessions, duplicate sessions, memory leaks, a single maintainer leaving).
2. The two notes that disagree on "who uses a workflow engine" are both right; they talk about different things. Cursor, OpenAI Codex and Replit use Temporal for the control plane of an agent **product** sold to users. In the set of **internal** ticket or engineering workflows, Duolingo is still the only company that names an engine. One correction: `orchestration_alternatives.md` says no primary source exists for Cursor; there is one (Cursor's own blog, 2026-06-02).
3. Symptoms that justify leaving CI are now backed by cases: runs that die far in and re-spend their tokens (Cursor, Replit, cubic), one-run-per-entity guarantees (Replit), many steps with their own retry rules (Duolingo). Symptoms that do **not** need an engine, only an idempotency key, a concurrency group, a budget cap or a reconciliation sweep: duplicates, silent losses and token-burn loops.
4. Published per-run prices cluster around one dollar: Cloudflare $1.19 per review (mean, 131,246 runs), Sentry Seer $1.00 per issue fix, GitHub's own agentic workflows about $0.09 per run on average and about $1.20 for the heaviest, Codex $0.08 to $0.60 per "typical task". The outlier is Anthropic's managed Code Review at $15 to $25. CI minutes are cents. Nobody publishes cost per feature ticket or per merged agent PR.
5. Limit of this pass: the shared web-search budget was exhausted before this note started. Everything here was read directly from known URLs, GitHub repositories and their issue trackers. Independent practitioner reports on LangGraph (adoption or removal) could therefore not be searched and stay **not found**.

## How to read this note

Labels on every fact:

- **[M] measured**: I read it in a primary artefact on 2026-11-21 (a repository, an issue with logs or counts, a specification, a metric published with its sample size). A user's bug report with reproduction counts as measured **on that user's install only**.
- **[V] vendor**: said by a company about its own product or its own internal system, including pricing pages and case studies.
- **[S] secondary**: a third party reporting or judging.

Vocabulary used below:

- **Runtime**: the thing that decides which step runs next and remembers where a run is.
- **Tracker-as-state daemon**: a long-lived process that polls the ticket tracker and starts agents; the ticket status is the state (OpenAI Symphony, Cyrus).
- **CI-as-engine**: each step is a CI job started by a repository event; the state is whatever the job wrote on the issue or pull request (claude-code-action, GitHub Agentic Workflows, GitLab flows).
- **Webhook orchestrator plus database**: a small service that receives events from GitHub, Slack or Linear, stores sessions in a database and starts sandboxes (Open-Inspect, WorkOS Horizon, Bitrise).
- **Durable engine**: a runtime that records every step so a crashed run resumes where it stopped (Temporal, Restate, DBOS, Inngest).
- **Idempotency key**: an identifier attached to an action so that doing it twice has the effect of doing it once.
- **AIC**: "AI Credit", GitHub's unit for agentic-workflow spend. One AIC is $0.01 [V, gh-aw cost page].

What "small team" evidence means here. The reporters of the issues cited below do not state their team size. They are self-hosters of open-source tools, which is the profile of the likely user, but the size is an inference, not a fact.

## 1. First-hand accounts per runtime

### 1.1 Tracker-as-state daemon: OpenAI Symphony

Repository state [M]: `openai/symphony`, 28,121 stars, 2,900 forks, last push 2026-09-15. **Issues are disabled.** Outside contributors cannot open pull requests either: three reporters say the create-PR call is refused and post their fixes as Discussions (#126, #121, #133). There are 51 discussions and 81 pull requests, the pull requests almost all from OpenAI staff.

What the specification says about state [M, SPEC.md]:

- Line 57-58: restart recovery is driven by the tracker and the filesystem "without requiring a persistent database; exact in-memory scheduler state is not restored".
- Line 1692: "Current design is intentionally in-memory for scheduler state."
- Line 2239, in the TODO list: "Persist retry queue and session metadata across process restarts."
- Line 727: one authority serializes state changes "to avoid duplicate dispatch".

What adopters reported [M, each is one user's report on their own install]:

| Symptom | Report | Date |
|---|---|---|
| A failed turn is treated as completed; the runner loops at about one tracker request per second until the Linear rate limit runs out, then retries after backoff | Discussion #133 | 2026-10-16 |
| Every turn rejected by the model, run "silently consumes its entire turn budget" (about 20 empty turns); the cause was only in debug logs; "a multi-hour investigation" | Discussion #92 | 2026-07-01 |
| A sub-agent finishing is taken for the end of the parent run; the issue is redispatched. A commenter: "This bug cost me 15M tokens while the agent loops" | Discussion #121 | 2026-08-16 |
| Workspace setup fails, the agent starts anyway, stalls on a question from a tool, and Symphony restarts the same issue about every 5 minutes; the ticket stays "In Progress", no PR | Discussion #64 | 2026-05-04 |
| Cancelling a run leaves the agent process alive; one orphan survived Symphony's shutdown | Discussion #126 | 2026-09-15 |
| A final ticket transition made by the agent races with the daemon's reconciliation: two valid but different outcomes | Discussion #123 | 2026-08-24 |
| Two Symphony processes can serve the same project at once | PR #8 (OpenAI staff), **closed without merge** 2026-02-27 | |
| A retry could stay claimed forever, or dispatch stale work | PR #110, merged 2026-07-20 | |
| Stale claims after a worker dies: a lease with heartbeat was proposed | PR #82 (OpenAI staff), **closed without merge** 2026-10-21 | |
| Token totals per ticket are lost when the run exits or the process restarts | PR #60, **closed without merge** 2026-10-21 | |

Reading [my analysis]:

- No report of a duplicate pull request was found. The dominant failure is the opposite: a run that looks alive, or looks finished, and spends tokens or tracker quota without producing anything.
- "Lost state on restart" is not a bug report; it is the documented design. The daemon recovers by re-reading the tracker. What is lost is the retry queue, the backoff timers and the per-ticket token totals.
- The fixes that would make the daemon safer (startup lock, claim lease, token ledger) were written and not merged. The reference implementation moves slowly: no push between 2026-09-15 and today, while the Codex CLI it drives changed its event format twice (#131, #134). A team that adopts Symphony adopts a fork.

### 1.2 Tracker-driven daemon: Cyrus

`cyrusagents/cyrus` (Linear to Claude Code and other agents; 909 stars, pushed 2026-11-21, 119 open issues) [M].

- **Runaway duplication** (#1328, 2026-06-16, open): one delegated Linear issue "can self-replicate into many agent sessions", a new one every 20 to 30 seconds, until Linear's 5,000 requests per hour are exhausted. "Observed 3 times over 3 days; worst case 16 sessions on one issue in ~45 min." Causes named by the reporter: no cycle guard, no filter on the bot's own events, "no agent-session webhook idempotency" [M].
- **Memory leak hidden by auto-restart** (#1381, 2026-07-21, open): the main process was killed for lack of memory "15 times over ~4 weeks", at up to 6.9 GB against 250 MB in steady state. With `Restart=always` it came back in 10 seconds, "so the failures went unnoticed for a month" [M].
- A parked message stream pins the daemon "busy forever" and orphans the agent process (#1479, 2026-09-14, open) [M].

### 1.3 CI-as-engine: claude-code-action, GitHub Agentic Workflows, GitLab

**`anthropics/claude-code-action`** (10,040 stars, 972 open issues) [M]:

- **Runs that never end.** #674 (2025-11-12, closed, 20 comments): "About 20% of the time Claude will never respond - so the github action times out after 6 hours." Outdated by date (2025), kept because it is the only quantified rate. #865 (2026-01-27, open): the job posts its review, then hangs until cancelled because tool servers are not terminated.
- **Double or missing trigger.** #591 (2025-09-26, open, 19 comments): a bot comment mentioning the agent is acknowledged but starts nothing; the human's follow-up comment "kicks off the workflow twice".
- **Instant crashes.** #853 (2026-01-22, open, 17 comments): the action exits in about 150 ms with `total_cost_usd: 0`, intermittently, same configuration. #892, #1013: same family.
- **Run cut short.** #1499 (2026-07-13, open): the action stops at the first result message, which ends the run while background sub-agents are still working.
- **No cost output.** #1482 (2026-07-08, open): there is no supported way to get per-run cost or token counts from the action. A team cannot meter its CI agent without parsing logs.

**GitHub Agentic Workflows (`github/gh-aw`)** (5,671 stars, 323 open issues, generally available since 2026-10-28) [M]. The repository runs about 55 agentic workflows on itself and files their problems as issues, so it is the best public telemetry of CI-as-engine:

- 24 hours ending 2026-11-20: 100 runs, **75 success, 25 failure**, 857.56 AIC, 963 Actions minutes (#79510). The collector may cap at 100 runs; the issue says "the log collection returned 100 runs".
- One workflow: "43% success rate, high-cost failures", failures happen late in the run so tokens are spent anyway (#54542, 2026-08-21). The dollar figure in that issue ($274.02 per day for 965,732 tokens) does not fit the token count and the issue itself carries a data caveat; do not reuse it.
- An outside user (#72900, 2026-10-29): one HTTP 502 during the daily budget scan "failed the activation job closed with a 54-minute cooldown"; agent, detection and output jobs were all skipped; "Nothing was reviewed." Fixed since, per the same issue.
- Five reviewer workflows failed at once on a gateway start-up timeout (#70975, 2026-10-21).
- By design: "gh-aw has no automatic retries, so each trigger produces one run" [V, FAQ]. A failed run is not resumed.
- A typical run is a pre-activation job (10 to 30 seconds), an agent job (1 to 15 minutes), a threat-detection job (10-minute default timeout), and about 1.5 minutes of runner set-up per job [V, cost page].

**GitLab Custom Flows**: no first-hand user account read in this pass. **Not found.**

**Cloudflare** runs its AI code review as "a fully contained GitLab CI component" that starts an open-source coding agent as a child process: 131,246 review runs on 48,095 merge requests in 5,169 repositories in 30 days (2026-03-10 to 2026-04-09), median 3 min 39 s, 99th percentile 10 min 21 s [V, self-reported with sample sizes]. This is the strongest evidence that CI carries the load. It is a large company and a review step, not a ticket-to-PR flow.

### 1.4 Webhook orchestrator plus database

**Open-Inspect** (`open-inspect/background-agents`, an open-source build of Ramp's background-agent design on Cloudflare Durable Objects, D1 and Modal; 3,507 stars, created 2026-01-25) [M]:

- **Silent loss.** #1363 (2026-08-10): when a sandbox takes more than 120 s to connect, the session stays `active` with zero messages forever and the review is never posted. "In one production install this accounts for 20 of 135 github-bot sessions (~15%)." From the pull request, "it is indistinguishable from the bot never having been triggered."
- **Pile-up.** #1371 (2026-08-12, open): a new review session for every push event, no cancellation of the previous one. "One PR accumulated 9 review sessions; at one point 3 ran concurrently". A check stays "pending" forever when a session dies. The reporter notes the fix must survive concurrent webhook deliveries, because a naive "query, cancel, create" double-creates.
- **Duplicate output.** #2552 (2026-10-26): a completion message posted twice, because delivery is at-least-once and each retry gets a fresh random identifier. Suggested fix: derive the identifier from the session and message.
- **Database timeouts** of unclear origin on session creation and in the recovery sweep (#561, 2026-04-26).
- **Bus factor.** #2493 (2026-10-23): the single maintainer stepped back on 2026-11-01 for a new job; the hosted documentation ran on his personal account. He asked for "two or three maintainers", ideally from "teams running Open-Inspect in production".

**Open SWE (LangChain)**: `langchain-ai/open-swe` has issues and discussions disabled (0 of each) [M]. No user account can be read there. **Not found.**

**bitclaw (Bitrise)**: the repository was not located under `bitrise-io/bitclaw` (404) [M]. **Not found.**

**WorkOS Horizon** (re-read at the source, 2026-05-06) [V]: webhook-driven, signatures verified, one work queue. The post does not name its database or queue, gives no engineering head count, no run counts, no cost, does not discuss missed webhooks or duplicates, and does not mention a workflow engine. The failures it lists are environmental: flaky checks, slow sandbox boot, missing scripts.

### 1.5 Durable engines used for coding agents

| Who | Size | Engine | What runs on it | Stated trigger | Label |
|---|---|---|---|---|---|
| Cursor | large | Temporal | The agent loop of the cloud-agent product | Worker nodes that "looped agents to completion" gave about "one 9" of reliability; the team was "on the verge" of rebuilding retries, cross-machine scheduling and durability | [V] Cursor blog, 2026-06-02 |
| Replit | large | Temporal Cloud | The Replit Agent control plane (one workflow per agent, the workflow identifier guarantees one active agent per user session), plus deployments and domain lifecycle | Hand-rolled queues hard to manage; out-of-memory crashes, model outages, failed tool calls; "pretty bad user experience to have the agent get super far into something and then hit a catastrophic error" | [V] Temporal case study, 2025-09-15, unnamed Replit engineer |
| OpenAI Codex | large | Temporal | "our core control flows" | Not stated | [V] quote of Will Wang, engineer on Codex, hosted on Temporal's blog, 2025-05-17 |
| Duolingo | large | Temporal | Internal multi-step agent workflows | JSON workflows "too simplistic" for several agent passes; each step gets its own retry settings | [V] Duolingo blog, 2025-12-11 |
| cubic (AI code review) | **2 to 20 employees** | Inngest | A four-agent review pipeline | "The AI review would sometimes fail without explanation"; needed a queue with timeouts, retries and tracing on serverless; proof of concept in "a few hours" | [V] Inngest customer page |

Other figures read at the source:

- Cursor after migration: "past two 9s", more than 50 million Temporal actions per day across more than 7 million workflows. Cost and staffing: none stated. Design changes made afterwards: workflows that exit after one task instead of living forever, which "makes version upgrades easier"; activities split to handle timeouts and retries [V].
- Replit: migration of most of the system took "a couple of weeks"; evaluation started November 2024, two months after the product launched. No reliability, scale or cost figure [V].
- Duolingo: a JSON workflow takes under 5 minutes to create; a custom Temporal workflow "about 1-2 days on average". Docker-in-Docker on Temporal blocked "a large set of planned features" at the time [V].
- Temporal's case-study index lists no coding-agent company besides Replit; the Inngest customer list has cubic only; the DBOS case-study page returned 404; Restate was not read. Named users of Restate or DBOS for coding-agent workflows: **not found** [M for the two index pages].

Every case in this table is a product or a large internal platform. cubic is the only small company, and it runs its product on the engine, not an internal ticket workflow.

## 2. Migration stories and the "who uses an engine" contradiction

### 2.1 Reconciling the notes

`ticket_to_prod_orchestration.md` says only Duolingo names a general engine. `labs_internal_stacks.md` says Temporal runs at OpenAI Codex, Cursor and Replit. Both statements are correct for their scope:

| Company | Primary source | What is on the engine | Product control plane or internal ticket workflow? |
|---|---|---|---|
| Cursor | Cursor's own blog, "What we've learned building cloud agents", Josh Ma, 2026-06-02 [V] | The agent loop of cloud agents | **Product control plane.** Cursor adds that "more than 40% of our PRs come from cloud agents", so its internal use rides on the product |
| OpenAI Codex | No OpenAI-hosted statement found. The only attributable sentence is an OpenAI engineer's quote on Temporal's blog (2025-05-17) [V, hosted by the engine vendor] | "core control flows" of Codex | **Product control plane**, as far as one sentence can tell. OpenAI's own ticket runner, Symphony, is a polling daemon with in-memory state and no engine [M] |
| Replit | No Replit-hosted post found in this pass. Temporal's case study quotes "an engineer on Replit's Platform Team", unnamed [V, hosted by the engine vendor] | Replit Agent control plane, deployments, domains | **Product control plane** and platform operations |
| Duolingo | Duolingo's own blog, 2025-12-11 [V] | Agent workflows shared among employees | **Internal engineering workflow** |

Corrections to carry into the other notes:

- `orchestration_alternatives.md` section 4.3 says "Cursor: ... no primary source found". The primary source exists and is quoted above.
- The sentence "only Duolingo names an engine" should read "only Duolingo names an engine **for an internal workflow**".
- The Replit quote attributed to "Connor Brewster" in `orchestration_alternatives.md` comes from Temporal's AI page; the case study itself names nobody.

### 2.2 Moves toward an engine

- Cursor: from a home-made work-stealing loop to Temporal. Trigger: reliability near 90% and the prospect of rebuilding durable-execution primitives. Result: above 99%. The only before-and-after figure found [V].
- Replit: from custom orchestration and hand-rolled queues to Temporal Cloud, two months after launch. Trigger: tech debt and agent failures far into a run [V].
- cubic: from manual log tracing to Inngest. Trigger: unexplained failures [V].
- A move from CI to an engine for an internal coding workflow: **not found**.

### 2.3 Moves away from an orchestrator or engine

- Airbnb, re-read at the catalog entry [S]: the Dev AI team built its own orchestrator from scratch, "it never shipped", and the team wrapped vendor coding agents with a thin shim. The entry rates this "medium confidence", says the engineer described it as "the team's choice, not a measured comparison", and gives no reason, cost or team size. It rests on a newsletter article that quotes Airbnb engineers.
- Open-Inspect: not a removal, but the sole maintainer left on 2026-11-01 and asked production users to take over [M]. For a small team this is the realistic way an orchestrator "gets dropped".
- A team that removed Temporal, Restate, DBOS or Inngest from a coding-agent workflow: **not found**.

## 3. LangGraph: independent reports and the Radar move

### 3.1 The Thoughtworks Radar, read at the blip page [S]

- April 2025: Trial.
- November 2025: Adopt, with "strong results" from Thoughtworks teams building multi-agent systems.
- **April 2026: Trial.** Reasons given, in the Radar's terms: the graph-with-global-shared-state architecture is "not always the best approach for building agentic systems"; an alternative style, for which the Radar cites Pydantic AI, uses simple agents that communicate through code and adds a graph only when needed; this often gives leaner systems; because each agent sees only the state it needs, reasoning, testing and debugging are easier. LangGraph "remains a powerful tool" but is no longer the default.

So the downgrade is about **architecture fit** (one large shared state), not about reliability, churn or licensing. `decision_criteria.md` summarises it as "start with the simplest thing"; that is close, but the specific criticism is the shared state.

Related blip, same source: Temporal is in **Trial since November 2026**, up from Assess (March 2022). The use case the Radar names is control planes that reconcile several long-running tasks, such as internal developer platforms and AI cloud infrastructure. The blip says nothing on operating cost or staffing [S].

### 3.2 Independent 2026 practitioner reports

**Not found, and not searched**: the search budget was gone. This gap from `langchain_langgraph.md` stays open. What can be said from sources read:

- The only independent judgement read at its source is the Radar's, above.
- LangChain's own ticket-to-PR reference design (Open SWE) accepts no public issues, so its failure modes cannot be audited from outside [M].
- None of the adopters' reports in section 1 mentions LangGraph, in either direction.

## 4. Cost per run

### 4.1 Published prices and measurements

| What | Figure | Unit | Label | Source |
|---|---|---|---|---|
| Cloudflare AI code review in GitLab CI | mean **$1.19**, median **$0.98**; 85.7% of input tokens served from cache; about 120 billion tokens in 30 days, so roughly 914,000 tokens per run (my division) | per review run, n = 131,246 | [V], with sample size | Cloudflare blog, 2026-04-20 |
| Sentry Seer "Issue Fix" (root cause, plan, code) | **$1.00**; a restart is billed as a new run | per run, pay-as-you-go | [V] | Sentry pricing docs |
| Sentry Seer issue scan | $0.003 falling to $0.0022 | per scan | [V] | same |
| Sentry Seer subscription | $40 per active contributor per month until 2026-12-08, then usage-based credits with a daily spend limit | | [V] | same |
| GitHub's own agentic workflows | 857.56 AIC and 963 Actions minutes for 100 runs: **$0.086 and 9.6 minutes per run on average**; heaviest single runs 121 to 127 AIC (**about $1.20**) | per run, one day | [M], estimates by the tool | gh-aw #79510 |
| One gh-aw workflow in detail | 99.57 AIC (**$1.00**), 3,728,969 tokens, 110 model calls, 16 Actions minutes; about 99% of tokens were context re-sent on each call | per run, n = 1 | [M] | gh-aw #72130 |
| gh-aw default caps | 1,000 AIC per run ($10), 5,000 AIC per workflow per day ($50), hard cap 10,000 AIC ($100), detection job 400 AIC ($4) | | [V] | gh-aw cost page |
| Codex | "A typical GPT-5.6 Sol task may use 2-15 credits"; 50 credits and $2 are both listed per million input tokens, so one credit is about $0.04 (my arithmetic): **$0.08 to $0.60** | per task | [V] + arithmetic | Codex pricing page |
| Anthropic Code Review (managed, several agents plus verification) | "generally average **$15-25**", about 20 minutes | per review | [V] | Anthropic blog, 2026-03-09 |
| Anthropic Code Review today | "no flat per-review price"; cost depends on review level, change size and pushes; reviews are skipped when the spend limit is reached | | [V] | Claude Code docs |
| GitLab Duo Agent Platform | $1 per credit on demand; Code Review Flow 0.25 credit ($0.25); SAST Vulnerability Resolution Flow 4 credits ($4); one model call 0.125 to 0.91 credit by model | per execution or call | [V] | GitLab docs |
| Copilot cloud agent, legacy billing | one premium request per session times the model multiplier; extra requests $0.04; plus Actions compute | per session | [V] | GitHub docs (applies only to annual Pro and Pro+ plans kept on legacy billing after 2026-06-01) |
| GitHub Actions runner | $0.006 per minute (Linux x64, 2 cores), $0.005 (arm64); free on public repositories | per minute | [V] | GitHub docs |
| Claude Code, interactive use | about $13 per developer per active day, $150 to $250 per month, under $30 per day for 90% of users | per developer, enterprise deployments | [V] | Claude Code docs |
| A loop bug | "15M tokens" lost by one user | one incident | [M], user report | Symphony discussion #121 |
| Devin | the pricing page read on 2026-11-21 no longer mentions ACUs: plans at $20, $200 and $80 (Teams) per month, extra usage "at API pricing" | | [V] | devin.ai/pricing |
| Jira Rovo credits per agent run | **not found** (the pricing and licensing pages did not return their tables) | | | |

Already in `decision_criteria.md` and still the only figures of their kind: a solo agent run at $9 and 20 minutes against a three-agent harness at $200 and 6 hours on the same brief (Anthropic, 2026-03-24) [V]; Temporal Cloud at about $50 per million actions [V].

### 4.2 A range for one run, and for one ticket

Run (one agent pass over one task: a review, a fix attempt, an implementation attempt):

- **Low: $0.05 to $0.60.** Small models or short tasks. Sources: gh-aw reviewers at 4 to 5 AIC, GitLab code review flow, Codex typical task.
- **Typical: about $1.** Three unrelated sources land here: Cloudflare (mean $1.19), Sentry ($1.00 flat), gh-aw heavy runs ($1.00 to $1.27).
- **High: $4 to $25.** Deep or multi-agent passes: GitLab SAST resolution ($4), gh-aw default per-run cap ($10), Anthropic Code Review ($15 to $25).
- **Runaway: $100 to $200.** gh-aw hard cap ($100); Anthropic's three-agent harness ($200).

CI compute for the same run: 5 to 20 billed minutes, that is **$0.03 to $0.12** at list price on a standard Linux runner (my arithmetic from the gh-aw job sizes and the Actions price). In the gh-aw day measured above, compute would be about $5.78 against $8.58 of model spend, so runner minutes are not negligible when runs are short and many; they become negligible on the $1-and-up runs. This excludes the project's own test suite, which usually dominates CI time.

Ticket (my estimate, not a source): a feature ticket handled as "check readiness, implement, one or two CI-fix rounds, review, security pass" is five to eight runs. At the typical price that is **$3 to $10 of model spend and 30 to 120 CI minutes ($0.20 to $0.70)**; with a deep review on each push it can reach $30 to $60. A bug fix with one implementation pass and one review is $1 to $3. These are bounds built from per-run prices; no source measures a ticket end to end.

What multiplies the bill, with the case that shows it:

- **Triggers.** A review on every push instead of once per pull request multiplies cost by the number of pushes (Claude Code docs [V]); `push` and `check_run` triggers "can produce hundreds of runs per day" (gh-aw [V]); 9 review sessions on one pull request in a day (Open-Inspect #1371 [M]).
- **Failures late in the run.** A CI job that fails is re-run from the start; 25% of gh-aw's own runs failed on the day measured [M].
- **Context re-sent on each model call.** 99% of one run's tokens (gh-aw #72130 [M]). Prompt caching is the main lever: Cloudflare reports 85.7% cache hits [V].
- **Loops without a budget.** 15 million tokens (Symphony #121 [M]); 16 sessions in 45 minutes (Cyrus #1328 [M]).

### 4.3 Engine fee and staffing

- Engine fee: unchanged from `decision_criteria.md`. At 100 actions per ticket and 1,000 tickets a month, Temporal Cloud is about $5 a month. Negligible.
- Staffing to operate a self-hosted engine: **not found**. Cursor, Replit and Duolingo give none. The Radar's Temporal blip is silent on it.
- Indirect staffing signals read at the source:
  - Maintaining an open-source webhook orchestrator: "A few hours a week, shared across a group" of two or three maintainers, across five areas (control plane, sandbox providers, web app, chat and tracker bots, deployment) (Open-Inspect #2493) [M, one maintainer's estimate].
  - Writing one custom workflow on Temporal once the platform exists: 1 to 2 days (Duolingo) [V].
  - Migrating an existing agent control plane to Temporal Cloud: "a couple of weeks" (Replit) [V].
  - Proof of concept on Inngest: "a few hours" (cubic) [V].
  - Diagnosing one silent loop in a tracker daemon: "a multi-hour investigation" (Symphony #92) [M, user report].

## 5. Threshold table: symptom observed, runtime change that fixes it

Read each row as "do not move until you see this". The third column is the smallest change that removes the symptom; the fourth is the heavier one.

| # | Symptom you can measure | Named case | Smallest fix (stay on CI or tracker state) | Runtime that removes it by design |
|---|---|---|---|---|
| 1 | Runs die far in and restart from zero; more than about 1 run in 10 is lost; tokens are paid twice | Cursor: "one 9" before, "two 9s" after [V]. Replit: "catastrophic error" far into a run [V]. cubic: reviews "fail without explanation" [V]. gh-aw: 25 failures in 100 runs, no automatic retry [M] | Split the flow into short jobs so that a failure repeats one job, not the ticket; write progress to the pull request between jobs | **Durable engine** (Temporal, Restate, DBOS, Inngest): each model or tool call is a recorded step |
| 2 | Two runs work on the same ticket or pull request at once; duplicate comments or sessions | Open-Inspect #1371: 9 sessions on one PR, 3 at once [M]. Open-Inspect #2552: message posted twice [M]. Cyrus #1328: 16 sessions in 45 minutes [M]. claude-code-action #591: workflow started twice [M] | In CI, a concurrency group keyed on the issue or PR number, with cancel-in-progress; an idempotency key derived from the entity, never a random one | **Durable engine** with one workflow identifier per entity (Replit uses exactly this for "one agent per session" [V]) |
| 3 | An event was accepted and nothing happened; nobody is told | Open-Inspect #1363: 20 of 135 bot sessions (about 15%) on one install [M]. claude-code-action #674: about 20% of reviews never answered, job held 6 hours (2025) [M]. gh-aw #72900: one 502 skipped every job for 54 minutes [M] | A job timeout far below the platform limit; a scheduled sweep that lists tickets in an active state with no recent run; a final status written by code, not by the agent | **Polling the tracker** instead of trusting webhooks (Symphony's reconciliation loop is this [M]); or an engine whose timers fire the sweep |
| 4 | An agent loops or idles and burns tokens or API quota while looking healthy | Symphony #133, #92, #121 (15M tokens) [M]. Symphony #64: restart every 5 minutes with no output [M] | A hard cap per run in dollars or tokens (gh-aw defaults: 1,000 AIC per run, 5,000 per day [V]); count empty turns as failure; cap retries | None. An engine does not fix this; it retries faithfully. The fix is a budget and a failure rule in code |
| 5 | The orchestrator process itself is the incident: memory growth, orphan processes, restart hides the fault | Cyrus #1381: 15 out-of-memory kills in 4 weeks, unnoticed [M]. Symphony #126: orphan agent after cancel [M]. Cyrus #1479: "busy forever" [M] | Alert on restarts; reap process groups | **CI-as-engine**: no long-lived process to leak; each step gets a fresh machine. Or a managed engine (Temporal Cloud at Replit [V]) |
| 6 | A step must wait for a human longer than one job, or resume exactly where it paused | CI limits: 6 hours per hosted job, 30 days for an environment approval, 35 days per run [M, GitHub docs, in `orchestration_alternatives.md`] | Model the wait as a ticket state; the reply is a new event that starts a new job | **Durable engine** when the wait is inside a multi-step computation whose intermediate results are expensive (Replit: user consent through workflow updates [V]) |
| 7 | Many steps, each with its own timeout and retry rule, and a form-style workflow no longer expresses them | Duolingo: JSON workflows "too simplistic"; Temporal gives per-step retry [V] | Reusable CI workflows with `needs:` chains | **Durable engine**; budget 1 to 2 days per workflow (Duolingo [V]) |
| 8 | You need "at most one agent per X" or strict ordering across events from several sources (GitHub, Slack, tracker) | Open-Inspect #1371 notes that concurrent webhook deliveries defeat "query, cancel, create" [M] | One queue per entity | **Durable engine**, or a database with a uniqueness constraint in your own orchestrator |
| 9 | The orchestrator depends on one person, or on an upstream that does not take fixes | Open-Inspect #2493: sole maintainer leaves [M]. Symphony: issues off, outside PRs refused, safety fixes unmerged [M]. Airbnb: own orchestrator "never shipped" [S] | Keep the home-made part to a few hundred lines you can rewrite | **Vendor-run runtime**: CI plus a vendor agent action, or a vendor cloud agent |
| 10 | You cannot say what a ticket cost | claude-code-action #1482: no cost output [M]. Symphony PR #60 unmerged: totals lost at exit [M] | Have the step write tokens and dollars to the PR; gh-aw does this in a footer on each output [M] | Any runtime with a run record; gh-aw's `logs` and `audit` commands [V] |
| 11 | The graph's single shared state has become hard to reason about and test | Thoughtworks Radar, April 2026, on LangGraph [S] | Plain code calling small agents that each see only what they need | Not a runtime question; a framework question |

What the table says about the central recommendation [my analysis]:

- Rows 2, 3, 4, 9 and 10 are the failures a small team will meet first, and none of them requires an engine. They require an idempotency key, a concurrency group, a sweep, a budget and a cost line. These are cheap in CI and were each missing in at least one open-source daemon or orchestrator.
- Rows 1, 6, 7 and 8 are the real exits toward an engine. Every named case for them is a product control plane or a large platform. At 5 to 50 engineers the volume that makes row 1 hurt (a failure rate you can feel on runs that cost dollars each) may never arrive: at $1 a run and a 25% failure rate, 1,000 runs a month waste about $250.
- Row 5 is an argument **against** the middle options for a small team. The tracker daemon and the webhook orchestrator both add a long-lived process to operate; the evidence here shows that process failing silently. CI-as-engine and a managed engine both remove it.
- So the order "CI and ticket state first, managed engine second, home-made daemon last" is better supported than the original wording, which presented the daemon and the webhook orchestrator as lighter alternatives of equal standing.

## 6. What remains unmeasured

Not found in any source, after this pass and the seven earlier notes:

1. A first-hand account from a team of 5 to 50 engineers running an internal ticket-to-PR workflow on any durable engine.
2. A first-hand account of GitLab Custom Flows, of Open SWE (issues disabled) or of Bitrise's reference code in someone else's hands.
3. Cost per feature ticket, per bug fix, or per merged agent pull request, end to end. Only per-run prices exist.
4. The share of runs that end in a merged pull request, which is needed to turn cost per run into cost per merged PR. Sentry's and Cloudflare's posts do not give it.
5. Staffing to operate a self-hosted Temporal or Restate, and the head count of any platform team behind an agent orchestrator.
6. A controlled comparison of CI-as-engine against a durable engine on the same workflow: failure rate, cost, time to recover.
7. A rate of missed or duplicated webhooks for GitHub or Linear as experienced by agent orchestrators. The Open-Inspect 15% is a timeout inside the orchestrator, not a missed delivery.
8. A duplicate pull request caused by a runtime. Duplicates found were sessions, comments and reviews.
9. An OpenAI-hosted statement on Codex and Temporal, and a Replit-hosted one.
10. Independent 2026 reports of LangGraph adoption or removal by named teams. Not searched.
11. Rovo credits consumed per Jira agent run; current Devin usage units; Copilot AI Credits included per seat on Business and Enterprise (the page for the current billing model was not located).
12. Whether the 25% failure rate in GitHub's own agentic workflows is typical. It is one day, one repository, experimental workflows, and possibly a capped sample.
13. Team size of every issue reporter cited in section 1.

Limits of this note:

- No web search was available. Sources are the URLs already known to the study, vendor documentation reached directly, and GitHub repositories read through the API. Conference talks and community forums were not covered.
- Issue trackers over-represent failures and say nothing about installs that work.
- Pricing pages change; every price above was read on 2026-11-21.

## Sources

Read on 2026-11-21 unless a date is given.

Tracker daemons
- https://github.com/openai/symphony (28,121 stars, pushed 2026-09-15, issues disabled)
- https://raw.githubusercontent.com/openai/symphony/main/SPEC.md (lines 57-58, 727, 1692, 2239)
- https://github.com/openai/symphony/discussions/133 (2026-10-16)
- https://github.com/openai/symphony/discussions/126 (2026-09-15)
- https://github.com/openai/symphony/discussions/123 (2026-08-24)
- https://github.com/openai/symphony/discussions/121 (2026-08-16)
- https://github.com/openai/symphony/discussions/107 (2026-07-19)
- https://github.com/openai/symphony/discussions/92 (2026-07-01)
- https://github.com/openai/symphony/discussions/64 (2026-05-04)
- https://github.com/openai/symphony/pull/8 , /pull/60 , /pull/82 , /pull/110
- https://github.com/cyrusagents/cyrus (909 stars, pushed 2026-11-21)
- https://github.com/cyrusagents/cyrus/issues/1328 (2026-06-16)
- https://github.com/cyrusagents/cyrus/issues/1381 (2026-07-21)
- https://github.com/cyrusagents/cyrus/issues/1479 (2026-09-14)

CI as engine
- https://github.com/anthropics/claude-code-action (10,040 stars, 972 open issues)
- https://github.com/anthropics/claude-code-action/issues/591 (2025-09-26)
- https://github.com/anthropics/claude-code-action/issues/674 (2025-11-12)
- https://github.com/anthropics/claude-code-action/issues/853 (2026-01-22)
- https://github.com/anthropics/claude-code-action/issues/865 (2026-01-27)
- https://github.com/anthropics/claude-code-action/issues/1482 (2026-07-08)
- https://github.com/anthropics/claude-code-action/issues/1499 (2026-07-13)
- https://github.com/github/gh-aw (5,671 stars, 323 open issues)
- https://github.com/github/gh-aw/issues/79510 (daily AIC audit, 2026-11-20)
- https://github.com/github/gh-aw/issues/72130 (2026-10-26)
- https://github.com/github/gh-aw/issues/72900 (2026-10-29)
- https://github.com/github/gh-aw/issues/70975 (2026-10-21)
- https://github.com/github/gh-aw/issues/54542 (2026-08-21; figure not reused)
- https://github.github.com/gh-aw/reference/faq/
- https://github.github.com/gh-aw/reference/cost-management/
- https://blog.cloudflare.com/ai-code-review/ (2026-04-20)

Webhook orchestrators
- https://github.com/open-inspect/background-agents (3,507 stars, created 2026-01-25)
- https://github.com/open-inspect/background-agents/issues/561 (2026-04-26)
- https://github.com/open-inspect/background-agents/issues/1363 (2026-08-10)
- https://github.com/open-inspect/background-agents/issues/1371 (2026-08-12)
- https://github.com/open-inspect/background-agents/issues/2552 (2026-10-26)
- https://github.com/open-inspect/background-agents/issues/2493 (2026-10-23)
- https://github.com/langchain-ai/open-swe (issues and discussions disabled)
- https://workos.com/blog/project-horizon (2026-05-06)

Durable engines and migrations
- https://cursor.com/blog/cloud-agent-lessons (2026-06-02)
- https://temporal.io/resources/case-studies/replit-uses-temporal-to-power-replit-agent-reliably-at-scale (2025-09-15)
- https://temporal.io/blog/improving-java-sdk-codex-openai (2025-05-17)
- https://temporal.io/resources/case-studies (index)
- https://blog.duolingo.com/agentic-workflows/ (2025-12-11)
- https://www.inngest.com/customers and https://www.inngest.com/customers/cubic
- https://internal-agents.com/agents/airbnb-airchat

Radar
- https://www.thoughtworks.com/radar/languages-and-frameworks/langgraph (entries of April 2025, November 2025, April 2026)
- https://www.thoughtworks.com/radar/platforms/temporal (entries of March 2022, November 2026)

Prices
- https://docs.sentry.io/pricing/
- https://learn.chatgpt.com/docs/pricing (redirect target of developers.openai.com/codex/pricing)
- https://claude.com/blog/code-review (2026-03-09)
- https://code.claude.com/docs/en/code-review-costs
- https://code.claude.com/docs/en/costs
- https://docs.gitlab.com/subscriptions/gitlab_credits/
- https://docs.github.com/en/billing/concepts/product-billing/github-copilot-premium-requests
- https://docs.github.com/en/copilot/concepts/billing/copilot-requests
- https://docs.github.com/en/billing/reference/actions-runner-pricing
- https://devin.ai/pricing

Pages that did not return usable content
- https://www.atlassian.com/software/rovo/pricing and https://www.atlassian.com/licensing/rovo (tables truncated)
- https://docs.devin.ai/billing/usage , https://www.dbos.dev/case-studies , https://docs.github.com/en/copilot/concepts/billing/ai-credits (404)
- https://github.com/bitrise-io/bitclaw (404)
