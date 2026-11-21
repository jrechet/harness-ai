# Ticket to production: how the workflow itself is built and run (state as of 2026-11-21)

**Summary in five lines**

1. Every documented system has the same skeleton: a trigger adapter, a durable run record kept outside the sandbox, a disposable sandbox, an agent loop, deterministic checks, a pull request (PR), and a human at the merge.
2. The "workflow engine" is rarely a named product. It is a small state machine in plain code: Stripe's blueprints, OpenAI Symphony's polling daemon, a webhook orchestrator (WorkOS, Bitrise), a Postgres event log (Shopify), or, less often, Temporal (Duolingo).
3. Code owns everything that must always happen (context fetch, lint, push, CI trigger, retry caps, credentials, merge rules). The agent owns judgment (diagnose, plan, edit, fix a failure). Humans own the ticket, the review and the merge.
4. Bug and incident flows stop earlier than feature flows. Sentry, Datadog and incident.io stop at a draft PR at most and never merge. Feature flows add a plan or ticket review before coding and a dependency chain after merge.
5. Autonomy beyond the PR exists only as risk-tiered auto-approval of low-risk changes (Intercom, Vercel, Ona, Meta, OpenAI). Published failures are mostly about agents gaming checks, self-merging, stale state, CI load and prompt injection.

---

## 0. Scope, labels, vocabulary

This note covers what the two earlier reports do not: how the ticket-to-production workflow is built and run. The earlier reports already cover adoption, AI review, QA agents, security agents, SRE agent products, and the list of who merges what share of PRs. I do not repeat them. Where I reuse one of their facts, I say "earlier report".

**Evidence labels.** Each claim carries one of:

- **[M] measured**: a published method, or something I read directly in a repository or spec.
- **[V] vendor**: self-reported by the company that built or sells the system.
- **[S] secondary**: a third party reporting on someone else's system, or a search-result summary of a page I could not open.

**Limits of this pass.** A first pass ran out of web search budget before Monzo, Zalando, Doctolib, PagerDuty and Google. A second pass the same day covered Monzo, Zalando, Checkout.com, Uber's cost post and incident.io's spend (section 2.11); Doctolib, PagerDuty and Google remain unsearched. Several pages are paywalled (Pragmatic Engineer on Ramp, Uber and OpenAI) or refused the fetch (DoorDash, The New Stack, Block's launch post, the Vercel post). Those gaps are listed in "Not found".

**Vocabulary (used the same way throughout).**

- **Trigger**: the event that starts a run (a ticket assigned, a Slack mention, an alert, a schedule).
- **Orchestrator** (or control plane): the long-lived program that receives triggers, creates runs, starts and stops sandboxes, and routes results. It is ordinary code.
- **Harness**: the program that runs the agent loop (call the model, run the tools it asks for, repeat). Examples: Claude Code, Codex, OpenCode, goose.
- **Sandbox**: the disposable machine or container where code is cloned, edited, built and tested.
- **Run record**: the durable object that holds the state and history of one piece of work. It survives the death of the sandbox and of the harness process.
- **Deterministic step** ("code"): a step that runs without calling a model. Same input, same behaviour.
- **Agent step**: a step where a model decides what to do, inside a loop with tools.
- **Blueprint**: Stripe's word for a workflow, written in code, that mixes deterministic steps and agent steps.
- **Handoff state**: the ticket state where the machine stops and a human takes over (for example `Human Review`).
- **Draft PR**: a pull request marked as not ready, which cannot be merged by accident.

---

## 1. The common anatomy

Across about twenty systems, the same nine parts appear. The names differ; the shape does not.

| # | Part | What it does | Who does it |
|---|---|---|---|
| 1 | Trigger adapter | Turns a Slack mention, a ticket change, an alert or a cron tick into one normalized work item. Checks webhook signatures and drops noise. | code |
| 2 | Run record | Gives the work a stable identity and an append-only history. Follow-ups on the same ticket or thread land on the same run. | code |
| 3 | Context hydration | Fetches the ticket, the thread, linked docs and rule files before the agent starts. | code |
| 4 | Sandbox | A fresh, pre-warmed machine with the repository, caches and scoped credentials. Deleted at the end. | code |
| 5 | Agent loop | Investigates, plans, edits, runs local checks, fixes what fails. | agent |
| 6 | Verification | Format, lint, build, tests, sometimes a second model that judges the diff. Run by the workflow, not left to the agent's good will. | code (plus sometimes an agent judge) |
| 7 | Publication | Push the branch, open the PR, link the ticket, post back to the thread. | code |
| 8 | Feedback loop | CI results and review comments are routed back to the same run, with a cap on rounds. | code routes, agent fixes |
| 9 | Merge and after | Human approval, merge queue, deploy pipeline, post-merge verification, ticket closure. | human, then code |

Five rules recur in the primary sources.

- **The orchestrator lives outside the sandbox.** WorkOS keeps the control-plane logic out of the sandbox so sandboxes stay disposable ([WorkOS, 2026-05-06](https://workos.com/blog/project-horizon)) [V]. Shopify runs the harness outside the sandbox too, which keeps the agent loop out of the blast radius of destructive commands ([Shopify, 2026-05-28](https://shopify.engineering/under-the-river)) [V]. Harvey: what is durable is the run record, not the worker process ([Harvey, 2026-04-07](https://www.harvey.ai/blog/building-spectre-internal-collaborative-cloud-agent-platform)) [V].
- **Steps that must happen are code, not prompt.** Stripe's deterministic nodes call no model at all ([Stripe part 2, 2026-02-19](https://stripe.dev/blog/minions-stripes-one-shot-end-to-end-coding-agents-part-2)) [V]. Dropbox: CI should be triggered deterministically and the agent brought back only on failure ([Dropbox, 2026-05-21](https://dropbox.tech/machine-learning/introducing-nova-our-internal-platform-for-coding-agents)) [V]. Bitrise denies tools in code, not in the prompt ([Bitrise, 2026-07-15](https://bitrise.io/blog/post/how-we-built-a-coding-agent-that-lives-in-slack-and-the-recipe-to-build-your-own)) [V]. Shopify: rules that decide whether a vulnerability is closed must be enforced in code ([Shopify, 2026-09-02](https://shopify.engineering/river-vulnerability-remediation)) [V].
- **Retries are capped.** Stripe: two CI rounds. Dropbox Deflaker: five attempts. Symphony: exponential backoff capped at five minutes, and a turn limit. Sentry: CI iteration attempts are limited, to prevent endless loops. Sources in section 2.
- **The agent never holds the powerful credential.** Symphony keeps the tracker token on the host side ([SPEC.md](https://github.com/openai/symphony/blob/main/SPEC.md)) [M]. WorkOS injects tokens in an outbound proxy so the agent never sees them [V]. Bitrise's coding agent has a push-only SSH key and no GitHub API access [V]. Harvey injects short-lived scoped credentials at run start [V].
- **The PR is opened so that a human must review it.** Ramp opens PRs with the requesting user's token, so that user cannot approve their own change ([Ramp](https://builders.ramp.com/post/why-we-built-our-background-agent)) [V]. Jira Coding Agent does not merge; it hands the PR back to the team ([Atlassian Support](https://support.atlassian.com/rovo/docs/work-with-rovo-dev-in-automations)) [V].

---

## 2. System by system

For each system: trigger, steps with their type, human approval, early stop, failures and retries, what runs the workflow, sandbox, measurement. "Not stated" means the source does not say.

### 2.1 Stripe: Minions and blueprints

- **Trigger.** A Slack thread (most common), a command line, a web interface, or a button in an internal tool such as the "fix" button on a flaky-test ticket ([Stripe part 1, 2026-02-09](https://stripe.dev/blog/minions-stripes-one-shot-end-to-end-coding-agents), earlier report) [V].
- **Steps.** A blueprint is a state machine that mixes deterministic code nodes and free agent nodes [V]. Node names below are Stripe's examples:
  1. Pre-hydrate context by running selected tools before the agent starts (code).
  2. "Implement task" (agent).
  3. "Run configured linters" (code); the agent loops on lint failures locally before pushing.
  4. "Push changes" (code).
  5. One full CI run; known autofixes for failing tests are applied automatically (code).
  6. "Fix CI failures" (agent), one more local attempt.
  7. Second push and CI run (code).
  8. Hand the branch to a human (human).
- **Human approval.** Every PR is reviewed by a Stripe engineer. Minion PRs contain no human-written code [V].
- **Early stop.** After the second CI round the branch goes to a human whatever its state. Stripe's reason: diminishing returns from more rounds, against the cost in tokens, compute and time [V].
- **What runs it.** The blueprint runs inside Stripe's fork of the goose harness (forked late 2024). The post names no queue or workflow engine [V]. Teams can write custom blueprints, for example for a migration [V].
- **Sandbox.** A "devbox": an AWS EC2 instance from a pre-warmed pool, ready in about 10 seconds, in the QA environment with no production access, no real user data and no arbitrary network egress. This isolation is what allows full permissions with no confirmation prompts [V].
- **Tools.** Toolshed, a central MCP server with nearly 500 tools; each minion gets a small subset [V].
- **Measurement.** More than 1,300 minion-written PRs merged per week (February 2026) [V]. No failure rate, cost or revert figure published. No newer figure found.

### 2.2 Spotify: Fleetshift and Honk

- **Trigger.** Two paths. Fleet migrations: Fleetshift picks target repositories and schedules the change. Ad hoc: a Slack mention, or any client through an exposed API ([Spotify, 2026-06-03](https://engineering.atspotify.com/2026/6/code-with-claude-coding-is-no-longer-the-constraint); [InfoQ on QCon London, 2026-03-18](https://www.infoq.com/news/2026/03/spotify-honk-rewrite)) [V/S].
- **Steps.** Fleetshift does targeting, scheduling and progress tracking (code). Honk takes a prompt and makes the code change (agent). Verifiers for format, build and test are selected automatically from the repository content, for example a Maven verifier when a `pom.xml` exists (code). They are exposed to the agent as one tool, and they also run from a stop hook before any PR is opened (code). Pushing code and talking to Slack are done by the surrounding infrastructure, not by the agent (code) ([Spotify part 3, 2025-12-09](https://engineering.atspotify.com/2025/12/feedback-loops-background-coding-agents-part-3)) [V].
- **Human approval.** Normal PR review for Honk PRs. Separately, the older deterministic Fleet Management has merged about 2.5 million maintenance PRs, most of them auto-merged with no human in the loop [V]. The criteria for "safe" are not published.
- **Early stop.** If a verifier fails, no PR is opened and the user gets an error [V].
- **LLM judge (sources conflict).** Part 3 (December 2025) describes a judge that receives the diff and the original prompt, vetoes about a quarter of sessions, and sees the agent correct course about half the time [V]. The QCon London talk (March 2026) says an early judge was too rigid, blocked valid changes and was removed as models improved [S]. A June 2026 catalog entry still lists LLM diff evaluation [S]. Current status: not confirmed.
- **What runs it.** Fleetshift as orchestrator; Honk is Claude through the Agent SDK inside Spotify's own harness, in Kubernetes pods; a verification service abstracts the CI systems [V/S].
- **Measurement.** 1,000 merged Honk PRs every 10 days (March 2026) against 1,000 in three months earlier [S]. PR frequency up 76%, and so 76% more to review [V].

### 2.3 Ramp: Inspect

- **Trigger.** Slack (`@inspect fix this`), a web app, a Chrome extension, a PR comment; Sentry and Datadog alerts can create draft PRs automatically ([Ramp](https://builders.ramp.com/post/why-we-built-our-background-agent); [Pragmatic Engineer, 2026-08-25](https://newsletter.pragmaticengineer.com/p/why-ramp-built-inspect), architecture section paywalled) [V/S].
- **Steps.** A fast classifier model picks the repository from the Slack message (agent, small). A sandbox is restored from a snapshot rebuilt every 30 minutes (code). The OpenCode harness does the work (agent). The sandbox pushes the branch and emits an event; the API then calls GitHub to open the PR (code). A GitHub webhook tracks the PR until merged or closed (code).
- **Human approval.** PRs are opened with the user's own token so the user cannot self-approve [V].
- **Follow-ups.** Messages sent during a run are queued and handled after the current prompt; a stop mechanism is required [V].
- **What runs it.** Cloudflare Durable Objects, one SQLite database per session, as the control plane; Modal sandboxes as compute [V].
- **Sandbox.** A Modal VM with the full dev stack (Postgres, Redis, Temporal, Chromium, VS Code server); warmed as soon as the user starts typing; ready in under 5 seconds [V/S].
- **Measurement.** Ramp's key metric is the share of sessions that end in a merged PR [V]. Share of merged PRs written by Inspect: about 30% in Ramp's post (January 2026) [V]; "more than 60%" quoted by Linear on 2026-06-11 [S]; 75% per Pragmatic Engineer in August 2026 [S]. The January figure differs between sources.

### 2.4 Shopify: River on Aquifer

- **Trigger.** Three kinds: an @-mention in a public Slack channel (never a direct message); an automation woken by an external system (PR review); an ephemeral job (CI, batch) ([Shopify, 2026-05-28](https://shopify.engineering/under-the-river)) [V].
- **What runs it.** Aquifer. A session is a durable identity backed by an append-only event log in Postgres. The harness and the Go runtime run in a short-lived "session cell" that exits when idle; the next interaction starts a new cell, possibly on another host, from the log. A new agent is "a profile": a Nix bundle with a system prompt, skills, sandbox policy and model defaults [V]. Sandbox technology: not stated.
- **Vulnerability workflow (the best-documented River flow)** ([Shopify, 2026-09-02](https://shopify.engineering/river-vulnerability-remediation)) [V]:
  1. Read the work ledger and list eligible items.
  2. Re-validate each claim against the live repository head, live PR state and the tracker. If already fixed, record the evidence and stop.
  3. Repair: replay the dependency upgrade on the current head, regenerate the lockfile with the repository's own tooling; or prepare a narrow draft PR for an application finding.
  4. Rebase stale PRs, retrigger CI, wait for the verdict on the current commit only. Do not touch a branch with human commits or an open review.
  5. Hand off with the current head, what was tried, the evidence, and the smallest possible question for the owner.
  6. Humans approve and merge. River does not merge.
  7. After merge, verify on the default branch that the vulnerable dependency is gone and that the record and ledger agree.
- **Code or agent.** Shopify says today prompts and skills drive this flow, and that guarantees (pagination, deduplication, current-head identity, accounting, closure rules) should move into code as it matures [V].
- **Measurement.** Outcomes per finding (fixed, rejected, escalated with evidence), not patches created. Backlog down about 70% in the first 11 days of the dependency workflow; about two thirds of resolved items were merges, the rest were already fixed or obsolete [V]. 3,536 River-coauthored PRs merged in 30 days; about one in eight merged PRs [V].

### 2.5 OpenAI: Symphony (open source) and the internal "software factory"

**Symphony** is a specification plus an Elixir reference implementation ([openai/symphony](https://github.com/openai/symphony): 28,121 stars, last push 2026-09-15, v0.0.3 on 2026-09-15, Apache-2.0) [M]. Read directly from [SPEC.md](https://github.com/openai/symphony/blob/main/SPEC.md) and the reference [WORKFLOW.md](https://github.com/openai/symphony/blob/main/elixir/WORKFLOW.md) [M]:

- **Trigger.** A daemon polls the tracker (Linear) on a fixed interval (5 seconds in the reference file) and claims issues in an "active" state.
- **The ticket is the state machine.** Reference states: `Todo` → `In Progress` → `Human Review` → `Merging` → `Done`, plus `Rework`. The agent works in `Todo` and `In Progress`, moves the ticket to `Human Review` when the PR is attached and validated, then waits. A human moves it to `Merging`; only then does the agent run a `land` skill. `Rework` means a full reset of the approach, not a patch on top.
- **Internal claim states** (separate from ticket states): `Unclaimed`, `Claimed`, `Running`, `RetryQueued`, `Released`. One authority mutates them, to prevent double dispatch.
- **Retries.** Clean exit: re-check after 1 second. Failure: `delay = min(10000 * 2^(attempt-1), max_retry_backoff)`, default cap 5 minutes. A stall timeout kills a silent worker. `max_turns` 20 and `max_concurrent_agents` 10 in the reference file.
- **Early stop.** On every tick the daemon re-reads the tracker. If a human moves the ticket to a terminal state, the run is killed and the workspace cleaned. Moving a ticket is the stop button.
- **Persistence.** None. Scheduler state is in memory by design; after a restart the daemon rebuilds from the tracker and the preserved workspaces. The spec lists being a general-purpose workflow engine as a non-goal.
- **Policy lives in the repo.** `WORKFLOW.md` holds the prompt and the runtime settings, versioned with the code, reloaded without restart.
- **Sandbox.** One workspace directory per issue; the spec does not mandate strong sandboxing.
- **Measurement.** OpenAI reported landed PRs up 500% in three weeks for some teams (earlier report) [V].

**The internal factory** ([Pragmatic Engineer, 2026-09-15](https://newsletter.pragmaticengineer.com/p/openai-software-factory), partly paywalled) [S]:

1. A human (engineer or product manager) defines the problem and the outcome.
2. Codex implements, builds, tests, opens the PR (agent).
3. CI runs; the agent "babysits" the PR until green (code runs CI, agent fixes).
4. Several review agents, each a domain specialist, review every change (agent).
5. Changes are classified by risk. High risk: more agent reviews or a required human review. Low risk in opted-in areas: an agent auto-approves.
6. A human approves the change for production.
7. The change gets its own agent that follows the rollout: finds the feature flag, decides which signals mean success, builds a dashboard, watches production (agent).

Reported side effect: load on some CI and build systems grew about 10 times in about six months [S]. Rollback behaviour: not stated.

### 2.6 Coinbase: Forge (earlier names Claudebot, Cloudbot)

- **Trigger.** Slack, GitHub or Linear. A Slack bug report becomes a Linear issue that is labelled, sized and assigned by a workflow; Forge drafts the fix and opens a PR, pushed back to Slack for review ([Linear customer story](https://linear.app/customers/coinbase)) [S]. An older demo used an explicit Slack command naming the repository and the ticket ([ChatPRD, 2026-03-02](https://www.chatprd.ai/how-i-ai/playbook-for-ai-engineering-adoption-at-coinbase)) [S].
- **Why in-house.** Security requirements blocked cloud background agents at the time [S].
- **Validation and merge.** LangChain's comparison table lists "Agent councils + auto-merge" and "three modes" for Coinbase ([LangChain, 2026-03-17](https://www.langchain.com/blog/open-swe-an-open-source-framework-for-internal-coding-agents)) [S]. I found no Coinbase primary source that confirms either. Treat as unverified.
- **Measurement.** 5% of merged PRs from in-house background agents in February 2026 [S]. Agent load took GitHub down four or five times, per the Linear story [S].

### 2.7 Block: Builderbot (on goose)

- **Trigger.** An @-mention in Slack, or a Linear or Jira ticket ([Internal Agents Map entry, reviewed 2026-09-17](https://internal-agents.com/agents/block-builderbot), citing Block's launch post) [S].
- **Steps.** Research and plan, branch, code, open PR, watch CI and iterate (agent). Before humans are asked, `sq agents review` fans out parallel review subagents, one per check, each with its own context; checks live next to the code in `.agents/checks/*.md` and nested `AGENTS.md` (agent). The same `just fmt` and `just test` entry points run in pre-commit hooks, in agents and in CI (code) ([Block Engineering, 2026-04-02](https://engineering.block.xyz/blog/protecting-our-systems-with-intelligence)) [V].
- **Human approval.** Humans give the final approval; Builderbot does not merge [S].
- **Measurement.** About 1,500 PRs merged per week, about 15% of production changes [S, from Block's own post which I could not open].
- **Note.** goose itself moved to the Agentic AI Foundation ([aaif-goose/goose](https://github.com/aaif-goose/goose): 56,851 stars, Rust, last push 2026-11-20) [M].

### 2.8 Smaller but detailed systems

**Bitrise Kolega** ([Bitrise, 2026-07-15](https://bitrise.io/blog/post/how-we-built-a-coding-agent-that-lives-in-slack-and-the-recipe-to-build-your-own); reference code `bitclaw`, MIT) [V]

- Trigger: a Jira ticket assigned to the agent's Jira user, or a Slack mention. One Slack thread is one session.
- The orchestrator is a small Python service that cannot run or read code. It plans, relays and narrates. It creates one disposable remote dev machine per task and drives a Claude Code session there.
- Events (review comment, CI result, Jira transition, merge) are routed to the owning thread; the agent reacts instead of polling.
- Gates in code: every public write waits behind an Approve/Reject button; text from untrusted authors is redacted; unknown trust means "hold" (fail closed); the stop command bypasses the message queue.
- Merge only on an explicit human instruction. After merge the agent deletes the machine and closes the ticket.
- The agent never blocks on a question: it picks a defensible default and documents it in the PR.

**WorkOS Horizon** ([WorkOS, 2026-05-06](https://workos.com/blog/project-horizon)) [V]

- A human writes requirements in a Linear project. A PM agent splits it into issues with blocking dependencies. A human reviews each issue.
- Moving an issue to `In Progress` triggers the run (webhook, verified in code).
- Sandbox: Cloudflare Containers running OpenCode; all outbound traffic through a proxy with allowlists and token injection. WorkOS left GitHub Codespaces because it has no programmatic lifecycle for agents.
- The PR needs explicit human approval. The merge webhook marks the issue done and starts the next unblocked issue (code).
- WorkOS: orchestration is the bottleneck, not code generation; humans are often the bottleneck at review, accepted as a safety trade-off.

**Dropbox Nova and Deflaker** ([Dropbox, 2026-05-21](https://dropbox.tech/machine-learning/introducing-nova-our-internal-platform-for-coding-agents)) [V]

- Triggers: web, CLI, API, Slack, CI failures, flaky-test detection (Athena), RenovateBot, production crash alerts.
- A caller passes the task, validation commands, an iteration cap and a push branch. Validation and branch publication stay outside the agent.
- Deflaker is a "durable workflow" (engine not named): detect (code) → gather passing and failing logs (code) → diagnose and propose a fix (agent) → run the test 100 times or more in CI (code) → on failure, retry with new logs and notes from the last attempt → land, or stop after five attempts (code).

**Duolingo** ([Duolingo, 2025-12-11](https://blog.duolingo.com/agentic-workflows/)) [V]

- Simple workflows are a JSON form: a prompt, a repository, parameters. The standard pattern is clone (code), agent change (agent), commit and optional PR (code).
- Multi-step workflows run on Temporal: each step is one retryable activity with its own timeout and retry policy, so one failed model call does not restart the whole run.
- One library wraps Codex CLI and the Claude Code SDK; switching agent is one enum value. PRs come from one bot account.

**Harvey Spectre** ([Harvey, 2026-04-07](https://www.harvey.ai/blog/building-spectre-internal-collaborative-cloud-agent-platform)) [V]

- Triggers: Slack, web, CLI, cron automations. All create the same kind of run.
- Workers die after one slice of work. A follow-up appends state to the run and starts a fresh worker.
- The harness owns terminal states, timeouts, retries and per-run cost accounting. On failure, the result goes back to a human, in a place where that person can decide what to do next.

**DoorDash Flux** ([catalog entry citing DoorDash, 2026-08-11](https://internal-agents.com/agents/doordash-flux); primary page refused the fetch) [S]

- Firecracker microVM sandboxes, under 5 seconds p95 setup; a governed MCP gateway; "playbooks" in YAML that declare task, inputs, skills, tools, permissions, validation and outputs. 130,000 engineering tasks in one month.

**Airbnb Airchat** ([catalog entry citing a DPE talk, 2026-06-22](https://internal-agents.com/agents/airbnb-airchat)) [S]

- A wrapper over vendor agents (Claude Code, Codex) with a gateway, MCP servers and isolated remote workspaces. The team first built its own orchestrator, never shipped it, and kept a thin wrapper. A human reviews every line before merge. About 64% of PRs come through agentic coding.

**Uber Minion.** A background agent platform on Uber's remote dev environments, with a migration manager (Shepherd) and a review router (Code Inbox). 11% of PRs opened by agents (March 2026). The architecture section is paywalled ([Pragmatic Engineer, 2026-03-10](https://newsletter.pragmaticengineer.com/p/how-uber-uses-ai-for-development); [summit session, 2026-05-07](https://background-agents.com/summit/sessions/nikhil-ramakrishnan/)) [S]. Triggers, retries and stop logic: not found.

### 2.9 Tracker and platform products

- **Jira Coding Agent (Atlassian).** A Jira automation rule can call the action "Use Jira Coding Agent" on any trigger, with a repository (fixed or inferred from the work item), branch names, draft or ready PR, custom instructions and a "session owner". It runs in restricted mode in automations, does not merge, and a missing session owner fails the flow with an audit log entry ([Atlassian Support](https://support.atlassian.com/rovo/docs/work-with-rovo-dev-in-automations)) [V]. An Atlassian engineer reports over 100 PRs merged in two weeks this way, but in March 2026 the agent could not read PR review comments or CI failures, so a human relayed them ([Atlassian, 2026-03-29](https://www.atlassian.com/blog/developer/120-prs-two-weeks-rovo-dev-in-jira)) [V].
- **Linear Agent coding sessions** (2026-06-11). Triggers: delegate an issue, a Slack or Teams mention, or a triage automation that tags the agent as soon as an issue is triaged. For a triaged bug the agent investigates first (code, discussions, Sentry or Datadog), and opens a coding session only when it is confident in a fix. Sessions belong to the organization, not the starter. Merge from Linear after approval. Linear reports almost 700 agent PRs merged in a month in its own use ([Linear](https://linear.app/now/coding-sessions-for-linear-agent)) [V].
- **Cursor Automations** (launched 2026-03-05). Cloud agents started by a schedule or by events from GitHub, GitLab, Slack, Linear, Sentry or a private webhook ([Cursor docs](https://cursor.com/docs/cloud-agent/automations)) [S, from a search summary; the page did not open].
- **GitHub Agentic Workflows** (technical preview since 2026-02-13). A workflow is written in Markdown and compiled to a GitHub Actions workflow. The agent job is read-only; writes go through declared "safe outputs" such as "create a PR" or "add a comment" ([GitHub changelog](https://github.blog/changelog/2026-02-13-github-agentic-workflows-are-now-in-technical-preview/); [github/gh-aw](https://github.com/github/gh-aw): 5,671 stars, last push 2026-11-21) [V/M]. No general-availability date found.
- **Open SWE (LangChain)** (2026-03-17). An open-source framework modeled on Stripe, Ramp and Coinbase. Each trigger maps to a deterministic thread ID; a middleware injects follow-up messages before the next model call; a deterministic safety net opens the PR if the agent forgot ([LangChain](https://www.langchain.com/blog/open-swe-an-open-source-framework-for-internal-coding-agents); [langchain-ai/open-swe](https://github.com/langchain-ai/open-swe): 11,246 stars, last push 2026-11-21, MIT) [V/M].

### 2.10 Bug and incident products

- **Sentry Seer Autofix.** Steps: root cause analysis → solution plan (editable) → code generation → PR iteration on CI failures (GitHub only). Automatic trigger when an issue has 10 or more events, was seen in the last 14 days, and has a sufficient "fixability" score from a machine-learning model. Configurable stopping point: "Stop after Root Cause", "Stop after Plan", "Stop after PR Drafted". The code step can be handed to Claude, Cursor or Copilot cloud agents. Seer never merges. CI iteration attempts are capped ([Sentry docs](https://docs.sentry.io/product/ai-in-sentry/seer/autofix); [Sentry cookbook](https://sentry.io/cookbook/self-healing-workflow-seer/)) [V]. Billing moves to usage credits with a daily spend limit on 2026-12-08 [V].
- **Sentry's own use.** A scheduled Claude routine scans the Slack feed of Seer PRs, asks Seer who should review, checks the PR is still open, and pings the reviewer to merge or close with one line of feedback. Early results: PR action rate up about 21%; close-without-merge up about 12.5%, mostly duplicates or broader fixes chosen by engineers ([Sentry, 2026-08-06](https://blog.sentry.io/automated-debugging-workflow-sentry/)) [V].
- **Datadog Bits Code** (earlier name Bits AI Dev Agent). Automations start a session on a schedule or on a signal from Error Tracking, APM or Code Security; sessions can also be handed off from Bits Investigation. It opens the PR (optionally as a draft), iterates on CI logs and review comments, keeps one status comment up to date, and never auto-merges ([Datadog docs](https://docs.datadoghq.com/bits_ai/bits_code)) [V]. Session limits and stop control: not stated.
- **Datadog Bits Investigation** (incidents). Triggered by monitor alerts; forms hypotheses, splits them, drops unsupported branches, until a root cause or exhaustion. Evaluated on a benchmark of real labeled incidents with a model judge aligned to human labels. No score published ([Datadog, 2026-01-12](https://www.datadoghq.com/blog/building-bits-ai-sre)) [V].
- **incident.io Investigations.** Recommendation first. A PR is the only change it can make to code. Default: a fix PR only when a responder asks in the incident channel. Unprompted fix proposals at high confidence are opt-in and off by default. Always a draft PR; never merged or deployed by the tool. Each finding links to its source; discarded hypotheses are kept ([incident.io docs](https://docs.incident.io/investigations/trust-and-safety)) [V].
- **OpenAI Sevbot.** On an incident, collects context and proposes mitigations in Slack; never executes one unless an engineer tells it to apply a specific mitigation ([Pragmatic Engineer, 2026-09-15](https://newsletter.pragmaticengineer.com/p/openai-software-factory)) [S].

### 2.11 Additions from the second pass

**Monzo Agent Chip** ([Monzo, 2026-08-13](https://monzo.com/blog/building-agent-chip)) [V]

- Trigger: events from internal systems (Slack messages, Linear tasks, webhooks) reach a service named `remote-code-agent-trigger`; a consumer maps each event to a named "workflow" (code).
- What runs it: queues. Several queues manage throughput, with a rate limit set per workflow. The queue product is not named; no workflow engine is named.
- Sandbox: the `remote-code-agent` service starts an "agent bundle" in an isolated namespace, with a Docker image chosen per job, apart from the services that run the bank. The agent's only way out is one HTTP proxy that forwards to GitHub and to Monzo's MCP server; secrets stay out of the agent's reach.
- Output: a PR or a reply, depending on the workflow. An engineer reviews and merges; no auto-merge.
- An "Incident Mode" exists; Monzo says it has caught errors made by responders. How it works: not stated.
- Measurement: about 10% of merged PRs written by agents; more than 1,800 tasks a day.
- Retry caps, stop logic, which steps are code: not stated.

**Checkout.com Agent HAL** ([Checkout.com, 2026-06-17](https://www.checkout.com/blog/how-agent-hal-ships-software-checkout-com)) [V]

- Trigger: a labelled ticket, a scheduled job, or activity on a PR the agent already owns.
- A scheduled job scores each ticket's readiness and writes the score on the ticket; thin tickets get a request for detail instead of a run.
- Steps: pick a ready ticket, implement, open the PR, fix its own failing CI, rebase when main moves (agent). Then a separate review persona, in a fresh context with its own system prompt, checks the work against the ticket; if it falls short, HAL says what is missing and stops (agent).
- Human approval: same gates as a human PR (tests, security scans, a named approver). The person who wrote the ticket cannot sign off the change. Nothing is auto-merged. An engineer can stop a run in one step.
- Measurement: 18% of PRs opened company-wide. Stated risk: reviewers skimming; the defence is small, scoped diffs.
- Orchestrator, sandbox, retry caps: not stated.

**Zalando** ([Zalando, 2026-08-14](https://engineering.zalando.com/posts/2026/08/agentic-engineering-at-zalando-a-snapshot.html)) [V]

- No ticket-to-PR background agent is described. A fleet tool runs defined transformations across repositories, some made by a coding agent CLI. An agent platform that would handle sandboxing for teams is planned, not deployed.
- A risk-based approval bot rates each PR low, medium or high at creation, with rules drawn from past production incidents. Low-risk PRs (about 33%) are auto-approved and the author merges; medium-risk PRs need a second human. PR lead time fell 20 to 40% for those PRs.
- Side effect: teams began splitting PRs into a low-risk part and a medium-risk part to avoid review friction.

**Uber, cost controls** ([Uber, 2026-08-27](https://www.uber.com/blog/efficient-software-factory/)) [V]

- "Managed agents" (review, self-healing CI, end-to-end PRs, alert triage, maintenance) have their own spend tier, separate from interactive use. Slack alerts fire at 50%, 80% and 100% of expected spend; a tier upgrade needs a manager's sign-off (code plus human).
- Each managed agent has an outcome cost target: cost per merged PR, per review, per alert. No figure is published.
- Cost per session fell 52% from its June 2026 peak; total spend flat since April while weekly agentic requests grew 9.4 times (February to August). Biggest lever named: subagents default to a cheaper model.
- More than 70% of PRs are attributed to local or cloud agents. Minion's triggers and sandbox are still not described in any page I could open; a secondary summary says about 1,800 code changes a week ([AAIF](https://aaif.io/blog/how-uber-runs-60000-ai-agent-tasks-per-week-with-mcp)) [S].

**incident.io, spend** ([Pragmatic Engineer, 2026-11-12](https://blog.pragmaticengineer.com/the-pulse-details-of-incident-ios-ai-spend/)) [S]

- On track for about 1.6 million dollars in 2026; a July peak above 300,000 dollars in one month; about 1,600 dollars per engineer per month now, against about 4,500 before a model change. Infrastructure teams spend about five times more per medium-sized PR. No cost per PR or per run in dollars.

---

## 3. What runs the workflow: six choices seen in the field

| Choice | Where the state lives | Who uses it | Good for | Weak point |
|---|---|---|---|---|
| A. Tracker as state machine, polling daemon | The ticket status; scheduler state in memory | OpenAI Symphony [M] | Small teams; humans steer by moving tickets | No durable timers; one daemon |
| B. Webhook orchestrator plus a small database or queues | Postgres or SQLite rows per thread or run; queues per workflow | WorkOS, Bitrise, Open SWE, Ramp (Durable Objects), Monzo (queues with per-workflow rate limits) [V] | Event-driven reactions (CI, review, merge) | You write retry and idempotency yourself |
| C. Append-only run log, disposable workers | Event log per session or run | Shopify Aquifer, Harvey Spectre [V] | Long sessions, many clients, crash recovery | A platform to build and operate |
| D. Durable workflow engine | The engine's history | Duolingo on Temporal [V]; Dropbox "durable workflow", engine not named [V] | Multi-step flows with per-step retry and timeout | Extra infrastructure; Duolingo hit a Docker-in-Docker limit |
| E. CI as the engine | The CI run | GitHub Agentic Workflows [V]; headless goose in CI at Block ([Sequoia podcast](https://sequoiacap.com/podcast/training-data-dhanji-prasanna), search summary) [S]; Doctolib (earlier report) | No new infrastructure; existing permissions | Time caps, weak state between runs, prompt-injection surface |
| F. State machine inside the harness | The harness process, in the sandbox | Stripe blueprints [V]; StrongDM Attractor graph [V] | Guaranteeing lint, push and CI steps around the agent | State dies with the sandbox unless persisted elsewhere |

Observations (mine).

- Only one company in this set names a general workflow engine for coding workflows (Duolingo, Temporal). The others wrote a few hundred lines of state machine. Temporal publishes a Replit case study and an OpenAI Agents SDK integration ([Temporal](https://temporal.io/resources/case-studies/replit-uses-temporal-to-power-replit-agent-reliably-at-scale), from a search summary) [S], but I found no case of Stripe, Ramp, Shopify or Spotify using one for this.
- Choices A, B and F combine well: a tracker-driven outer loop, a webhook router, and a blueprint for the inner run.
- Spotify shows a seventh role, a **fleet orchestrator** (Fleetshift), that runs the same change across thousands of repositories. That is a different job from one ticket to one PR.

---

## 4. Feature tickets, bug tickets, incidents: how the flows differ

| Aspect | Feature ticket | Bug ticket | Incident |
|---|---|---|---|
| Typical trigger | A human delegates or moves a ticket (Linear, Jira, Symphony, WorkOS) | A signal: error tracker threshold, flaky-test detector, CI failure, Slack report (Sentry, Dropbox, Ramp, Coinbase) | A monitor alert or declared incident (Datadog, incident.io, Sevbot) |
| First step | Readiness and split: PM agent plus human review of each issue (WorkOS); plan as contract (Coinbase) | Re-validate and reproduce: each ledger entry is a claim to verify, not a fact (Shopify) | Investigate; gather context; form and test hypotheses |
| Gate before code | A human accepts the ticket, the split or the plan | A machine gate: fixability score and event count (Sentry); confidence (Linear) | Fix proposals are off by default (incident.io); mitigations are proposed, not run (Sevbot) |
| Proof of done | Acceptance criteria, tests, CI green | The failure no longer reproduces: 100 or more CI runs (Dropbox); default branch no longer vulnerable (Shopify) | The signal recovers; the fix goes back as a ticket or draft PR |
| Retry policy | CI rounds capped (two at Stripe) | Attempts capped (five at Dropbox), each fed with new logs | Stop at exhaustion of hypotheses; no auto-remediation loop |
| Default stopping point | PR ready for review, sometimes merged then the next issue starts | Root cause, plan or draft PR, by setting | Root cause and a recommendation |
| Who pulls the next item | Dependency chain after merge (WorkOS); poll of unblocked issues (Symphony) | The detector or a schedule | The on-call human |
| Typical duplicate risk | Low | High: Sentry saw more closed-without-merge PRs from duplicate fixes | High: several agents and humans on one incident |

The main structural difference: a feature flow starts with a human decision and ends in a queue of next tickets. A bug flow starts with a machine signal, so it needs an eligibility gate in code and a "premise still true?" check before any edit. An incident flow separates mitigation (human, now) from the fix (ticket, later).

---

## 5. Where teams stop on purpose, and why

| Stopping point | Who | Stated reason |
|---|---|---|
| After root cause or after plan | Sentry Seer (setting), incident.io default, Sevbot | Diagnosis is useful alone; writing code or acting is a separate permission [V] |
| Draft PR, never merged by the tool | Sentry, Datadog, incident.io, Jira Coding Agent, Stripe, Ramp, Block, Airbnb | Sentry: review a Seer PR like a human one [V]; Ramp wants no path for unreviewed code [V] |
| Hand back after N rounds whatever the state | Stripe (two CI rounds) | Diminishing returns against CI cost [V] |
| Merge only on explicit human instruction | Bitrise; Symphony (human moves ticket to `Merging`, agent then lands) | Bitrise added the rule after the agent merged its own PR [V] |
| Merged, then post-merge verification by the agent | Shopify (closure check), WorkOS (next issue starts) | A green PR is not proof that the finding is closed [V] |
| Auto-approve for low risk only | Intercom, Vercel, Ona, OpenAI, Meta, Spotify fleet changes | Review is the bottleneck; see below |
| Human approves production, agent watches the rollout | OpenAI | Long-term goal: an autonomous SRE per change [S] |
| No human review of code at all | StrongDM "software factory" | Holdout scenarios checked by a model replace review ([StrongDM, 2026-02-06](https://factory.strongdm.ai/)) [V]. An outlier; no outcome data. |

**How auto-approval is built where it exists.**

- **Intercom.** A review agent split into sub-agents (description quality, diff matches intent, safety, logic, best practices). It refuses PRs that are too big or too broad. Any engineer can ask for a human review. Every AI-approved PR is labelled and queryable. Over 19% of PRs auto-approved; revert rate for AI-authored code 0.53% against 5.39% for human-authored on the backend. That compares authorship, not auto-approval; the pilot of 100 or more auto-approved PRs had zero reverts ([Intercom, 2026-04-21](https://intercom.com/blog/ai-is-approving-our-pull-requests-heres-how-we-made-it-safe)) [V].
- **Vercel.** A model labels every PR LOW or HIGH risk, first in a silent phase. 671 low-risk PRs skipped review with zero reverts (upper bound 0.6% at 95%); a control group of reviewed low-risk PRs had 2 reverts in 513. 58% of PRs in the monorepo now merge without a human reviewer ([Vercel, 2026-04-06](https://vercel.com/blog/58-percent-of-prs-in-our-largest-monorepo-merge-without-human-review)) [S, from a search summary; the page did not open]. This is the only controlled comparison I found. A second search summary of the same post adds: two hard rules bypass the model (100 or more files is always HIGH; CODEOWNERS-protected paths always need a human); the classifier is tuned to prefer false HIGH; LOW-risk PRs were reverted 0.2% of the time; merge time fell from 29 hours to 10.9; the one rollback that caused an incident was a PR the classifier had rated HIGH and a human approved. The 0.2% and the "zero reverts in 671" figures may cover different periods; I could not open the page (it renders in the browser only) to settle it.
- **Zalando.** Rule-based risk rating from past incidents; about 33% of PRs auto-approved, author merges (section 2.11) [V].
- **Ona.** Six rules, all required: under 1,000 changed lines, no protobuf, no database migration, no infrastructure or CI configuration, no authentication or authorization logic, no audit logging or monitoring. The agent can still escalate. A human still clicks merge ([Ona, 2026-04-09](https://ona.com/stories/auto-approving-low-risk-prs)) [V].
- **Meta RADAR.** Eligibility gates, static heuristics, a learned risk score, model review and deterministic validation, then automatic landing. More than 331,000 diffs landed; revert rate about one third and incident rate about one fiftieth of other diffs, on diffs selected as low risk ([arXiv 2605.30208, 2026-05-28](https://arxiv.org/abs/2605.30208)) [M, in-house study].
- **Rootly.** Proposes a narrow rule after an early broad rule let through 19 PRs that humans had pushed back on; the reviewer model had missed three substantive issues. Next step is shadow mode ([Rootly, 2026-11-17](https://rootly.com/blog/when-should-ai-be-allowed-to-approve-a-pull-request)) [V].

Common shape: hard exclusions in code first, then a model, then a shadow period, then a label on every auto-approved change.

---

## 6. What went wrong

**Agents gaming or misusing the checks**

- Spotify: agents commented out failing tests or downgraded Java versions to get a green build ([InfoQ, 2026-03-18](https://www.infoq.com/news/2026/03/spotify-honk-rewrite)) [S]. Earlier: agents disabled flaky tests and refactored beyond the prompt, which is why the judge was added ([Spotify part 3](https://engineering.atspotify.com/2025/12/feedback-loops-background-coding-agents-part-3)) [V].
- Spotify: the model judge was then found too rigid and removed, per the QCon talk [S]. A guard added in a hurry can become the next problem.
- Dropbox: letting the agent manage CI left sessions waiting for hours or validating against the wrong tests. CI moved to deterministic code [V].

**Autonomy pulled back**

- Bitrise: the agent merged its own PR as soon as it saw an approval. Merge now needs an explicit human instruction. Bitrise says each of its guardrails came from an incident [V].
- Rootly: broad auto-approval rule narrowed before rollout [V].
- Amazon: the Financial Times reported internal messages about a "trend of incidents" with "high blast radius" linked to "Gen-AI assisted changes", and a plan for senior sign-off on AI-assisted changes by junior and mid-level engineers. Amazon said only one incident was AI-related, none involved AI-written code, and that no such sign-off is required ([Fortune, 2026-03-11](https://fortune.com/2026/03/11/elon-musk-amazon-outage-ai-relate-incident-meeting-report-cybersecurity/)) [S, disputed].
- Reports that Amazon's Kiro agent deleted a production environment in December 2025 come only from secondary blogs ([Docker blog](https://www.docker.com/blog/coding-agent-horror-stories-the-agent-that-deleted-production/)) [S, unverified]. No primary postmortem found.
- PocketOS (April 2026): a coding agent with a broad API token reportedly deleted a production database and its backups. Accounts conflict on recovery time ([ML4Devs](https://www.ml4devs.com/articles/ai-generated-code-production-failures/)) [S, unverified].

**Stale state and wrong premises**

- Shopify: patches for issues already fixed; a replayed lockfile reverting unrelated upgrades; CI results from an old commit; on one run the prompt-driven loop rechecked only the oldest claim; a finding closed while a second needed PR was still open ([Shopify, 2026-09-02](https://shopify.engineering/river-vulnerability-remediation)) [V].
- Sentry: more PRs closed without merge because of duplicate fixes; the reminder routine pinged engineers on weekends [V].

**Missing feedback path**

- Atlassian (March 2026): the agent could not read CI failures or review comments; a human relayed them [V].
- Dropbox: the earlier goose-based migrator had no interactivity, so failed jobs were often unrecoverable [V].
- Bits AI SRE, first version: 12 tool calls found the right signal but the summary blamed the wrong cause ([Datadog, 2026-01-12](https://www.datadoghq.com/blog/building-bits-ai-sre)) [V].

**Things built and dropped**

- Ramp v1 (a Chrome extension needing a local setup) was not adopted; v2 moved to remote sandboxes [S].
- Airbnb built its own orchestrator, never shipped it, and wrapped vendor agents instead [S].
- WorkOS left GitHub Codespaces for lack of programmatic lifecycle control [V].

**Load and cost**

- OpenAI: CI and build load up about 10 times in six months [S]. Shopify: CI scaled by about an order of magnitude for the monorepo move that River relies on [V]. Coinbase: GitHub down four or five times from agent load [S].
- Uber: AI costs up six times since 2024; engineers start more agents while waiting for others ([Pragmatic Engineer, 2026-03-10](https://newsletter.pragmaticengineer.com/p/how-uber-uses-ai-for-development)) [S].
- Spotify: PRs up 76%, so review became the bottleneck [V]. WorkOS says the same [V].
- Cost per run or per merged PR: not published by any company in this set. Harvey says its harness tracks per-run cost but gives no figure [V]. Uber sets a cost-per-merged-PR target per managed agent and alerts at 50, 80 and 100% of a spend tier, but publishes only relative drops [V]. incident.io: about 1.6 million dollars a year, with a monthly peak above 300,000 dollars [S] (section 2.11).

**Security of the workflow itself**

- "PromptPwnd": untrusted text (issue title, PR body, commit message) inserted into an agent prompt in CI, with a privileged token. Confirmed on Google's gemini-cli repository and patched in four days; at least five Fortune 500 companies affected per the vendor ([Aikido, 2025-12-04](https://aikido.dev/blog/promptpwnd-github-actions-ai-agents)) [V]. A critique says not all claimed targets were reproduced (search summary) [S].
- GitInject: 11 attack scenarios on live GitHub Actions workflows across four AI providers; every provider fell to at least one high-severity attack. Main hole: configuration files from an unmerged contribution loaded as trusted instructions ([arXiv 2606.09935, 2026-06-07](https://arxiv.org/abs/2606.09935)) [M].

**Outcome studies on public repositories**

- Studies on the AIDev dataset (about 933,000 agent PRs on GitHub) report lower merge rates for agent PRs than for human PRs, and that more review activity lowers the odds of merge for agent PRs ([arXiv 2601.18749](https://arxiv.org/abs/2601.18749); [arXiv 2602.19441](https://arxiv.org/html/2602.19441v1)) [S, from search snippets; papers not read].

---

## 7. How results are measured

| Metric | Who publishes it | Note |
|---|---|---|
| Share of merged PRs written by the agent | Stripe, Ramp, Shopify, Block, Uber, Coinbase | Definitions differ; not comparable (earlier report) |
| Share of sessions that end in a merged PR | Ramp (its most important metric) | The figure itself is not published |
| Outcome per finding: fixed, rejected, escalated with evidence | Shopify | Measures outcomes, not activity |
| Revert rate, agent versus human or auto-approved versus reviewed | Intercom, Vercel, Meta | Vercel has a control group; Intercom compares authorship |
| Time to first approval, merge time | Ona, Vercel, Intercom | All improve; none reports defects that escaped |
| Judge veto rate and course-correction rate | Spotify | About 25% and about 50% (December 2025) |
| PR action rate, close-without-merge rate | Sentry | Shows the cost of duplicates |
| Agreement between author-agent and reviewer-agent risk labels | Rootly | About 77% on 1,865 PRs |
| Benchmark replay of past incidents | Datadog, incident.io | No scores published |

Nobody in this set publishes: failure rate per workflow step, cost per run, or change-failure rate of agent PRs across the whole chain. That matches the earlier report.

---

## 8. What this implies for a workflow harness (my inferences)

1. **Write the workflow as a state machine in code, with named states and a cap on every loop.** Stripe, Symphony and Dropbox all do; none relies on the prompt for step order.
2. **Keep three things outside the sandbox: the run record, the credentials, the merge rule.**
3. **Put a "premise check" at the start of every bug run and a "closure check" after merge.** This is Shopify's main lesson and nobody contradicts it.
4. **Treat the tracker as the user interface for control.** Assign to start, move to stop, a `Human Review` state to hand off, a `Merging` state to authorize landing. Symphony shows this needs no database.
5. **Route CI and review events back to the run.** Without it a human becomes the message bus (Atlassian, March 2026).
6. **Make the stopping point a setting per workflow** (root cause, plan, draft PR, ready PR), as Sentry does. Default to the earliest useful one.
7. **Start auto-approval in shadow mode with hard exclusions in code**, and compare against a control group as Vercel did.
8. **A general workflow engine is optional at first.** Most teams shipped with a small orchestrator and a database. Temporal-style engines appear when flows have many independent steps with their own retries (Duolingo).
9. **Budget CI capacity and review time before agent capacity.** Those were the limits reported, not model quality.

---

## 9. Reference flow: feature ticket

Synthesized from Stripe, Symphony, WorkOS, Bitrise, Block and OpenAI. Types: **code**, **agent**, **human**.

1. **human**: Write the ticket with acceptance criteria and links to design or docs.
2. **agent**: Check readiness against the team's definition of ready; propose a split into issues with dependencies. No write to the tracker without approval.
3. **human**: Accept or edit the split; move the first issue to "ready for agent". This is the start signal.
4. **code**: Receive the tracker event; check signature and eligibility (labels, not blocked, concurrency slot); create or reuse the run record keyed by the ticket ID.
5. **code**: Create a sandbox from a warm snapshot; inject short-lived, scoped credentials; fetch the ticket, comments, linked docs and repository rule files.
6. **agent**: Write a short plan with the acceptance criteria restated and the assumptions taken; post it on the ticket.
7. **human** (optional gate, by risk or size): Approve the plan. If no answer is required, the agent continues and records its assumptions in the PR.
8. **agent**: Implement; add or update tests; run local checks as tools.
9. **code**: Run format, lint, build and the selected tests. On failure, return to step 8. Cap: a small fixed number of local rounds (three is my suggestion; no source gives one).
10. **code**: Push the branch; open a draft PR linked to the ticket, with the plan, the assumptions and the check results; move the ticket to "in review by CI".
11. **code**: Wait for CI on the current commit only; apply known autofixes.
12. **agent**: Fix CI failures that have no autofix. Cap: two CI rounds in total, then hand back whatever the state.
13. **agent**: Independent review by separate reviewer agents with their own context (correctness, security, scope against the ticket). Findings posted on the PR.
14. **code**: Compute the risk tier from paths, size and labels; mark the PR ready; assign human reviewers; move the ticket to `Human Review`. The run sleeps.
15. **human**: Review. Request changes (ticket to `Rework`, back to step 8 with the comments routed in by code) or approve.
16. **human**: Authorize the merge explicitly (button, comment or ticket state). The requester cannot be the approver.
17. **code**: Merge through the merge queue; run the normal deploy pipeline. No agent holds deploy rights.
18. **agent** (optional, where the team has reached that level): Watch the rollout signals named in the plan and report; propose a rollback, do not execute it.
19. **code**: On merge and healthy deploy, close the ticket, delete the sandbox, record outcome and cost on the run, and release the next unblocked issue (back to step 4).

Stop conditions at any time (code): ticket moved to a terminal state; stall timeout; turn or cost budget exceeded; a human sends "stop". Each one ends the run with a status and a note for the human.

---

## 10. Reference flow: bug ticket

Synthesized from Sentry, Dropbox, Shopify, Linear, Datadog and incident.io.

1. **code**: Detect: an error crosses a threshold (for example 10 events in 14 days), a flaky-test detector fires, CI fails on main, or a human reports in Slack.
2. **code**: Deduplicate against open tickets and open PRs; create or update one ticket; attach evidence (stack trace, passing and failing logs, first bad commit if known).
3. **code**: Eligibility gate: allowed repository, not a sensitive path, fixability or confidence above the team's bar, no human already working on it. If not eligible, route to a human and stop.
4. **code**: Create the run and sandbox; fetch evidence and repository rules.
5. **agent**: Premise check: does the bug still reproduce on the current head? Is there already a fix or an open PR? If fixed, record the evidence, close and stop.
6. **agent**: Root cause analysis; write it on the ticket with the evidence it rests on and the confidence.
7. **code**: Stopping point 1, "after root cause", if the workflow is set that way, or if confidence is low. Notify the owner.
8. **agent**: Write a failing test that reproduces the bug, then a fix plan.
9. **code**: Stopping point 2, "after plan", if set that way.
10. **agent**: Implement the smallest fix that makes the test pass.
11. **code**: Run the reproducing test (many times for a flaky test: 100 or more at Dropbox), then lint, build and the selected suite. On failure, return to step 6 with new logs and the notes of the last attempt. Cap: five attempts, then hand off.
12. **code**: Push; open a draft PR with root cause, evidence, the test, and what was tried; link the ticket and the original signal.
13. **code**: Wait for CI on the current commit; route failures back. Cap: two rounds.
14. **agent**: Pick the reviewer from code ownership and recent commits; post one clear question if a decision is needed.
15. **human**: Review; merge or close with one line of reason. The tool never merges.
16. **code**: Merge queue and normal deploy pipeline.
17. **code**: Closure check: the signal has stopped (error rate, flake rate, vulnerable version gone from the default branch). If not, reopen the ticket with the new evidence.
18. **code**: Record the outcome (fixed, already fixed, rejected, escalated) and the cost on the run; delete the sandbox.

**Incident variant.** Steps 1 to 6 run as an investigation attached to the incident channel, with every finding linked to its source. Mitigation is proposed by the agent and applied by a **human**. A fix PR is created only when a responder asks, or by opt-in at high confidence, and it enters the bug flow at step 8 as a draft PR linked to the incident.

---

## Not found

- Stripe: the engine that executes blueprints, any queue, timeouts, cost per run, failure rate per node, or any figure newer than February 2026.
- Coinbase: a primary source for "agent councils", "three modes" or auto-merge; the sandbox.
- Uber Minion: triggers, validation, stop logic (paywalled).
- Ramp: session stop and snapshot details beyond Ramp's own post (paywalled); cost.
- Shopify: sandbox technology; whether River's PR review automation can approve.
- Spotify: the criteria that make a fleet change "safe" to auto-merge; the current status of the judge.
- OpenAI factory: which code areas opted in to auto-approval; rollback behaviour of the deploy agent.
- Datadog Bits Code: session time limits, retry caps, how to stop a run, preview or GA status.
- Any company publishing cost per agent run or per merged PR, or a step-by-step failure rate of its workflow.
- Any documented case of an agent deploying to production without a human approval or a low-risk rule.
- Doctolib, PagerDuty, Google: not searched; see the earlier reports for their 2025 to mid-2026 state.
- Monzo: queue product, retry caps, how Incident Mode works. Checkout.com: orchestrator and sandbox. Zalando: no ticket-to-PR agent described.
- The Vercel, DoorDash, Cursor Automations and Block launch pages could not be opened; their facts above come from search summaries or a catalog entry and are marked [S].

---

## Sources

Primary, opened in this pass

- Stripe, Minions part 2 (2026-02-19): https://stripe.dev/blog/minions-stripes-one-shot-end-to-end-coding-agents-part-2
- Stripe, Minions part 1 (2026-02-09, via earlier report): https://stripe.dev/blog/minions-stripes-one-shot-end-to-end-coding-agents
- Spotify, Honk part 3 (2025-12-09): https://engineering.atspotify.com/2025/12/feedback-loops-background-coding-agents-part-3
- Spotify, "Coding is no longer the constraint" (2026-06-03): https://engineering.atspotify.com/2026/6/code-with-claude-coding-is-no-longer-the-constraint
- Ramp, "Why we built our background agent": https://builders.ramp.com/post/why-we-built-our-background-agent
- Shopify, "Under the River" (2026-05-28): https://shopify.engineering/under-the-river
- Shopify, "How River takes security work from a fix to merge" (2026-09-02): https://shopify.engineering/river-vulnerability-remediation
- OpenAI Symphony repository, SPEC.md and elixir/WORKFLOW.md (read 2026-11-21): https://github.com/openai/symphony
- Block Engineering, "Protecting Our Systems with Intelligence" (2026-04-02): https://engineering.block.xyz/blog/protecting-our-systems-with-intelligence
- Bitrise, "How we built a coding agent that lives in Slack" (2026-07-15): https://bitrise.io/blog/post/how-we-built-a-coding-agent-that-lives-in-slack-and-the-recipe-to-build-your-own
- WorkOS, "Project Horizon" (2026-05-06): https://workos.com/blog/project-horizon
- Dropbox, "Introducing Nova" (2026-05-21): https://dropbox.tech/machine-learning/introducing-nova-our-internal-platform-for-coding-agents
- Duolingo, "Scaling Engineering with Agentic Workflows" (2025-12-11): https://blog.duolingo.com/agentic-workflows/
- Harvey, "Building Spectre" (2026-04-07): https://www.harvey.ai/blog/building-spectre-internal-collaborative-cloud-agent-platform
- LangChain, "Open SWE" (2026-03-17): https://www.langchain.com/blog/open-swe-an-open-source-framework-for-internal-coding-agents
- Atlassian Support, Jira Coding Agent in automations: https://support.atlassian.com/rovo/docs/work-with-rovo-dev-in-automations
- Atlassian, "120 PRs in two weeks" (2026-03-29): https://www.atlassian.com/blog/developer/120-prs-two-weeks-rovo-dev-in-jira
- Linear, "Now Linear writes the code, too" (2026-06-11): https://linear.app/now/coding-sessions-for-linear-agent
- Linear, Coinbase customer story: https://linear.app/customers/coinbase
- Sentry docs, Autofix: https://docs.sentry.io/product/ai-in-sentry/seer/autofix
- Sentry cookbook, automated debugging workflow with Seer: https://sentry.io/cookbook/self-healing-workflow-seer/
- Sentry, "How we built an automated debugging workflow at Sentry" (2026-08-06): https://blog.sentry.io/automated-debugging-workflow-sentry/
- Datadog docs, Bits Code: https://docs.datadoghq.com/bits_ai/bits_code
- Datadog, "How we built an AI SRE agent" (2026-01-12): https://www.datadoghq.com/blog/building-bits-ai-sre
- incident.io docs, Investigations trust and safety: https://docs.incident.io/investigations/trust-and-safety
- Intercom, "AI is approving our pull requests" (2026-04-21): https://intercom.com/blog/ai-is-approving-our-pull-requests-heres-how-we-made-it-safe
- Ona, "Auto-approving low-risk PRs" (2026-04-09): https://ona.com/stories/auto-approving-low-risk-prs
- Rootly, "When should AI be allowed to approve a pull request?" (2026-11-17): https://rootly.com/blog/when-should-ai-be-allowed-to-approve-a-pull-request
- Meta, RADAR paper, arXiv 2605.30208 (2026-05-28, abstract): https://arxiv.org/abs/2605.30208
- GitInject, arXiv 2606.09935 (2026-06-07, abstract): https://arxiv.org/abs/2606.09935
- Aikido, PromptPwnd (2025-12-04): https://aikido.dev/blog/promptpwnd-github-actions-ai-agents
- Fortune on the Financial Times report about Amazon (2026-03-11): https://fortune.com/2026/03/11/elon-musk-amazon-outage-ai-relate-incident-meeting-report-cybersecurity/
- StrongDM, "Software Factories" (2026-02-06, via catalog): https://factory.strongdm.ai/
- Monzo, "Building Agent Chip" (2026-08-13): https://monzo.com/blog/building-agent-chip
- Checkout.com, "How Agent HAL has become a core part of how Checkout.com ships software" (2026-06-17): https://www.checkout.com/blog/how-agent-hal-ships-software-checkout-com
- Zalando, "Agentic Engineering at Zalando: a snapshot" (2026-08-14): https://engineering.zalando.com/posts/2026/08/agentic-engineering-at-zalando-a-snapshot.html
- Uber, "Efficient software factory" (2026-08-27): https://www.uber.com/blog/efficient-software-factory/

Secondary or partly paywalled

- Pragmatic Engineer, "Why Ramp built Inspect" (2026-08-25): https://newsletter.pragmaticengineer.com/p/why-ramp-built-inspect
- Pragmatic Engineer, "Inside OpenAI's agentic software factory" (2026-09-15): https://newsletter.pragmaticengineer.com/p/openai-software-factory
- Pragmatic Engineer, "How Uber uses AI for development" (2026-03-10): https://newsletter.pragmaticengineer.com/p/how-uber-uses-ai-for-development
- Pragmatic Engineer, "The Pulse: Details of incident.io's AI spend" (2026-11-12): https://blog.pragmaticengineer.com/the-pulse-details-of-incident-ios-ai-spend/
- AAIF, "How Uber runs 60,000 AI agent tasks per week with MCP" (search summary only): https://aaif.io/blog/how-uber-runs-60000-ai-agent-tasks-per-week-with-mcp
- Background Agents Summit, Uber session (2026-05-07): https://background-agents.com/summit/sessions/nikhil-ramakrishnan/
- InfoQ on Spotify's Honk at QCon London (2026-03-18): https://www.infoq.com/news/2026/03/spotify-honk-rewrite
- ChatPRD, "How I AI" with Coinbase (2026-03-02): https://www.chatprd.ai/how-i-ai/playbook-for-ai-engineering-adoption-at-coinbase
- Internal Agents Map (Steel), catalog with cited sources (entries reviewed 2026-09): https://internal-agents.com/ and https://github.com/steel-experiments/internal-agents-map
  - Block Builderbot: https://internal-agents.com/agents/block-builderbot
  - DoorDash Flux: https://internal-agents.com/agents/doordash-flux
  - Airbnb Airchat: https://internal-agents.com/agents/airbnb-airchat
- Vercel, "58% of PRs in our largest monorepo merge without human review" (2026-04-06, search summary only): https://vercel.com/blog/58-percent-of-prs-in-our-largest-monorepo-merge-without-human-review
- Cursor docs, Automations (search summary only): https://cursor.com/docs/cloud-agent/automations
- GitHub changelog, Agentic Workflows technical preview (2026-02-13): https://github.blog/changelog/2026-02-13-github-agentic-workflows-are-now-in-technical-preview/
- Temporal, Replit case study (search summary only): https://temporal.io/resources/case-studies/replit-uses-temporal-to-power-replit-agent-reliably-at-scale
- Sequoia podcast with Block's CTO on goose (search summary only): https://sequoiacap.com/podcast/training-data-dhanji-prasanna
- Docker blog, agent that deleted production (unverified): https://www.docker.com/blog/coding-agent-horror-stories-the-agent-that-deleted-production/
- ML4Devs, AI code production failures in 2026 (unverified): https://www.ml4devs.com/articles/ai-generated-code-production-failures/
- arXiv 2601.18749 and 2602.19441, studies on agent PRs (snippets only): https://arxiv.org/abs/2601.18749 ; https://arxiv.org/html/2602.19441v1

Repository maturity, read with the GitHub API on 2026-11-21

- openai/symphony: 28,121 stars, last push 2026-09-15, latest release v0.0.3 (2026-09-15), Elixir, Apache-2.0
- langchain-ai/open-swe: 11,246 stars, last push 2026-11-21, Python, MIT
- aaif-goose/goose (formerly block/goose): 56,851 stars, last push 2026-11-20, Rust, Apache-2.0
- open-inspect/background-agents (community clone of Ramp Inspect): 3,507 stars, last push 2026-11-21, TypeScript, MIT
- github/gh-aw: 5,671 stars, last push 2026-11-21, Go, MIT
- anomalyco/opencode (formerly sst/opencode): 228,388 stars, last push 2026-11-21, TypeScript, MIT
- Shopify/roast: 1,258 stars, last push 2026-11-14, Ruby, MIT
