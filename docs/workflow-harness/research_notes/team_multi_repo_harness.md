# From one instrumented repository to a team harness across many repositories

Research note, 2026-11-21. Scope: what changes when agent workflows are shared by a team or several teams over many repositories.

## Summary in five lines

1. Sharing is solved the same way everywhere it is documented: a versioned Git repository of skills, rules and hooks (a "plugin marketplace"), pushed to machines by device management or managed settings, with team additions kept in each repository. No vendor offers an organisation-level AGENTS.md; the file only nests inside one repository.
2. A cross-repository workflow lives in one of four places: a central orchestrator a platform team builds (Stripe, Spotify, Ramp, Uber), CI in each repository, a vendor's cloud agent, or a mix. The first costs years of platform work; the last two cost setup per repository and give up control of the run loop.
3. Ticket systems now treat agents as assignable actors (Jira, Linear, GitHub Issues), and Linear keeps a human as the accountable assignee by design. Status sync is uneven: Linear tells agents to move the issue to "started"; the Jira integrations read stream progress and links, and none says it transitions the work item.
4. Identity is the real fork. An agent either acts as the person who asked (simple, but that person cannot approve their own pull request and the agent inherits everything they can reach) or under its own app or service account (clean audit, one capability for everyone in the scope). Every documented lock is code or platform settings, never text.
5. No published maturity model for teams is backed by outcome measurement. All are vendor guides, one-author experience reports or security frameworks; the one academic model that grades evidence (AgentStripes) rates an agent release, not a team, and says itself it is not validated. A team ladder next to this project's repository ladder has to be built from checks we can measure ourselves; a proposal is in the last section.

## How to read this note

Each claim carries a tag and a source.

- **[measured]**: an independent measurement, or a number I read myself today from an API.
- **[vendor]**: self-reported by the organisation that sells or runs the thing. Product documentation and company engineering blogs both fall here.
- **[secondary]**: a third party reporting on someone else, or a claim I only saw through a search summary without opening the primary page.

Terms used:

- **Harness**: everything around the model that shapes an agent's work: instruction files, skills, hooks, tools, checks.
- **Skill**: a folder with a `SKILL.md` that an agent loads when a task matches.
- **Hook**: a script the agent tool runs before or after an action. It can block the action.
- **Plugin**: a package of skills, agents, hooks and tool connections. A **marketplace** is a catalogue of plugins, usually a Git repository.
- **Managed settings**: configuration an administrator pushes to every machine; the user cannot override it.
- **MCP server**: a service that exposes tools (Jira, a database, an internal API) to agents through the Model Context Protocol.
- **Cloud agent** or **background agent**: an agent that runs in a remote sandbox with no person watching, and returns a pull request.
- **Sandbox**: an isolated machine or container where the agent runs commands.
- **PR**: pull request.

Limit of this note: it was written in two passes on 2026-11-21. The second pass opened several pages the first had only seen through search summaries (Vercel excepted: the page returned an error). What I could not confirm is listed in "Not found".

---

## 1. Distributing shared instructions, skills and agents

### 1.1 What each tool offers

| Tool | Shared unit | How it reaches every developer | What it can lock | Source, tag |
|---|---|---|---|---|
| Claude Code | Plugin, in a marketplace (Git repository, URL or local path) | Managed settings: `extraKnownMarketplaces` registers the marketplace, `enabledPlugins` installs and force-enables plugins. Delivered from the claude.ai admin console ("server-managed"), by device management (MDM), or as a `managed-settings.json` file | `strictKnownMarketplaces` (allowlist of sources), `blockedMarketplaces`, `disableSideloadFlags`, `allowManagedHooksOnly`, `strictPluginOnlyCustomization` (blocks skills, agents, hooks and MCP servers that come from user or project sources) | code.claude.com/docs/en/plugins/org [vendor] |
| GitHub Copilot | Organisation custom instructions (text in settings, not a file); custom agents (Markdown profiles) at repository, organisation or enterprise level | Organisation settings UI; a `.github-private` repository holds enterprise agent profiles and a managed settings JSON | Enterprise AI controls: which agents and clients are allowed, MCP servers, tool calls that need approval | docs.github.com (add-organization-instructions, custom-agents-configuration, governance-controls) [vendor] |
| Cursor | Team Rules (free text, optional file glob) | Cursor dashboard, Team and Enterprise plans | "Enforce this rule": the rule "cannot be disabled" by a member. Team hooks on Enterprise | cursor.com/docs/context/rules, cursor.com/docs/cloud-agent [vendor] |
| OpenAI Codex | `requirements.toml` (limits) and managed defaults | Admin console policies, macOS MDM, or a system file | Approval policies, sandbox modes, MCP allowlist, network rules, managed hooks, plugin marketplace sources | learn.chatgpt.com/docs/enterprise/managed-configuration [vendor] |
| Any tool | `AGENTS.md` | In the repository only | Nothing | agents.md [vendor] |

Details that matter for a design:

- **Claude Code precedence.** Only one managed source applies by default: server-managed first, then MDM, then the file. Setting `managedSourcesBehavior` to `"merge"` applies all. [vendor] code.claude.com/docs/en/plugins/org
- **Claude Code cloud sessions only read server-managed settings.** A policy shipped by MDM or file stays on the laptop and does not reach a session on Anthropic's infrastructure. A team that mixes local and cloud work needs the admin-console route. [vendor] code.claude.com/docs/en/managed-settings
- **Per repository instead of per fleet.** A repository's `.claude/settings.json` can name the marketplace and the plugins, but this "doesn't install the plugin": each contributor runs an install command, and the marketplace entry is ignored in a folder the user has not trusted. [vendor] code.claude.com/docs/en/plugins/org
- **CI and containers.** A "seed" directory is built at image build time and is read-only at run time. In GitHub Actions, the default workflow token cannot read a private marketplace in another repository; a personal or app token is needed. [vendor] same page
- **Release channels.** The documented way to run "stable" and "early access" is two marketplaces pointing at two refs of the same plugins, each given to a user group. [vendor] same page
- **What managed settings cannot do.** No per-user targeting inside one policy, no restriction on entries inside an allowed marketplace (block a single plugin with `enabledPlugins: false`), no way to hide `/plugin`. [vendor] same page
- **Audit.** OpenTelemetry events `claude_code.plugin_installed` and `claude_code.plugin_loaded`; on Enterprise, an Analytics API returns install and invocation counts per plugin and per day. [vendor] same page
- **Copilot organisation instructions apply only on the GitHub website and in code review.** "They are not supported in local client sessions." [vendor] docs.github.com add-organization-instructions
- **Copilot custom agents: the lower level wins.** "In the case of naming conflicts, the lowest level configuration overrides higher-level configurations." A repository can therefore replace an organisation agent of the same name. [vendor] docs.github.com custom-agents-configuration
- **Cursor Team Rules outrank project rules** (Team, then Project, then User). The page does not say whether they apply to cloud agents. Cursor itself warns that rules "should not be your only security control". [vendor] cursor.com/docs/context/rules
- **Codex**: requirements are "admin-enforced constraints that users can't override"; cloud requirements outrank system files; a policy can target users, groups or roles. [vendor] learn.chatgpt.com managed-configuration
- **AGENTS.md has no cross-repository mechanism.** The nearest file in the directory tree wins and "explicit user chat prompts override everything". The site claims use by "over 60k open-source projects" and stewardship by the Agentic AI Foundation under the Linux Foundation. [vendor] agents.md

### 1.2 A tool-neutral packaging layer exists

Microsoft's Agent Package Manager (APM) declares instructions, skills, agents, hooks, plugins and MCP servers in one `apm.yml`, resolves dependencies between packages, and writes a lockfile with commit hashes. A policy file (`apm-policy.yml`) is said to be enforced at install time with "tighten-only" inheritance from enterprise to organisation to repository. [secondary: project README seen through a search summary] github.com/microsoft/apm. The repository has 4,427 stars and was pushed today. [measured, GitHub API, 2026-11-21]

Thoughtworks names the pattern "agent plugin marketplace" and puts it in **Trial** (Radar vol. 35, 2026-11-04): a documented Git repository that publishes skills, instructions, MCP servers and subagents, consumed directly or as dependencies through APM. [secondary: consultancy opinion] thoughtworks.com/en-us/radar/techniques/agent-plugin-marketplace

### 1.3 How large companies actually roll it out

| Company | What is shared | How it is pushed | Tool policy | Source, tag |
|---|---|---|---|---|
| Intercom | 13 plugins, more than 100 skills, hooks | The marketplace "ships automatically to Macs through JAMF" (device management), which keeps it updated | Claude Code | ideas.fin.ai, Brian Scanlan, 2026-03-19 [vendor] |
| Zalando (250+ teams) | One central skill collection grouped into plugins (data, engineering, frontend, SRE); reference configurations for each coding agent | Managed configuration, or a CLI command that installs symlinks from a Git-hosted state | "We have never centrally mandated the use of a single tool." Claude Code, opencode and pi are covered | engineering.zalando.com, Bartosz Ocytko, 2026-08-14 [vendor] |
| Stripe | Rule files scoped to sub-directories or file patterns; an internal MCP server ("Toolshed") with nearly 500 tools | One rule format (Cursor's) is the source; it is synced into a format Claude Code reads, so the in-house agents, Cursor and Claude Code share guidance | Several | stripe.dev Minions part 2 [vendor] |
| Uber | 3,600+ agent skills, 30,000+ skill executions a day; one MCP gateway in front of more than 1,000 servers | Not described | Several harnesses under one spend tier | uber.com/blog/efficient-software-factory, 2026-08 [vendor] |

Three practices recur:

- **Hooks carry the workflow, not the skill text.** At Intercom a hook blocks a raw `gh pr create` unless the PR skill ran first; another blocks any change to a merged branch. [vendor] ideas.fin.ai
- **Global rules are kept few.** Stripe uses global rules "sparingly" to protect the context window; most rules attach as the agent enters a directory. [vendor] stripe.dev part 2
- **Telemetry tells the base what is missing.** Intercom instruments 14 lifecycle event types with OpenTelemetry, does not capture prompts, and classifies gaps as missing skill, missing tool, repeated failure or wrong information. [vendor] ideas.fin.ai

Thoughtworks calls the whole layer an "enterprise harness" (**Assess**, vol. 35): shared skills, tools, connectors, approved technologies, hooks and security policies. Its advice, since "no consensus exists yet": keep it thin and federated. "Curated shared instructions for software teams" is in **Adopt**, with instruction files embedded in service templates so new repositories inherit them. [secondary] thoughtworks.com/radar/techniques/enterprise-harness, .../curated-shared-instructions-for-software-teams

### 1.4 Maturity of the building blocks (measured today)

Stars and last push from the GitHub API on 2026-11-21. [measured]

| Repository | Stars | Last push | Note |
|---|---|---|---|
| anthropics/skills | 198,389 | 2026-11-16 | Reference skills |
| anomalyco/opencode (was sst/opencode) | 228,388 | 2026-11-21 | Open-source coding agent |
| openai/codex | 136,051 | 2026-11-21 | |
| aaif-goose/goose (was block/goose) | 56,851 | 2026-11-20 | Now under the Agentic AI Foundation organisation; Stripe forked it in late 2024 |
| anthropics/claude-plugins-official | 47,897 | 2026-11-21 | Official marketplace |
| agentsmd/agents.md | 25,640 | 2026-09-10 | The AGENTS.md format |
| anthropics/claude-code-action | 10,040 | 2026-11-21 | Claude Code in GitHub Actions |
| github/gh-aw | 5,671 | 2026-11-21 | GitHub Agentic Workflows |
| kagent-dev/kagent | 4,482 | 2026-11-21 | Agents on Kubernetes; Zalando's planned runtime |
| microsoft/apm | 4,427 | 2026-11-21 | Agent Package Manager |
| open-inspect/background-agents (was ColeMurray/background-agents) | 3,507 | 2026-11-21 | Open implementation modelled on Ramp's Inspect |

---

## 2. Where a cross-repository workflow lives and runs

### 2.1 Option A: a central orchestrator service, built in-house

A service owned by a platform team receives the request, starts a sandbox, runs the agent, and opens the PR.

| Company | Shape | Numbers | Source, tag |
|---|---|---|---|
| Stripe "Minions" | A **blueprint** is a workflow defined in code that mixes "agent nodes" (open-ended model loops such as "Implement task") and "deterministic nodes" (code that never calls a model, such as "Run configured linters" or "Push changes"). Runs happen on "devboxes": pooled cloud machines, ready in about 10 seconds, with no production access and no arbitrary network egress. At most two CI rounds, then the branch goes back to a human | More than 1,300 PRs merged a week contain no human-written code; all are reviewed by humans | stripe.dev part 1 (2026-02-09) and part 2 [vendor] |
| Spotify "Honk" | The agent replaced hand-written migration scripts inside an existing system, Fleet Management, which already targeted repositories, opened PRs and tracked progress. Since mid-2024 about half of Spotify's PRs were automated by that system, before agents | More than 1,500 agent PRs merged; 60 to 90% time saved on migrations | engineering.atspotify.com, 2025-11-06 [vendor] |
| Ramp "Inspect" | Cloud agent started from Slack, GitHub, Linear or the web. A vendor white paper says it runs the opencode harness inside Modal sandboxes | "accounts for 74% of merged PRs"; 99% of engineering, design and product used it in the past month | ramp.com/blog/introducing-inspect, 2026-10-27 [vendor]; ona.com white paper [secondary] |
| Uber | Managed agents for review, CI repair, end-to-end PRs, alert triage. "A growing share of agent sessions start automatically" | "More than 70% of pull requests are attributed to local or cloud agents" (this counts any agent involvement) | uber.com/blog/efficient-software-factory [vendor] |
| Zalando | Planned agent platform on kagent (Kubernetes) with an "Identity Broker" for delegation chains and a token vault | Not yet in production at the time of the post | engineering.zalando.com, 2026-08-14 [vendor] |

Why Stripe built its own: an unusual stack (Ruby with Sorbet, many home-grown libraries), compliance obligations, and existing developer-productivity tooling to plug into. [vendor] stripe.dev part 1

What it needs from the organisation: a platform team; a pool of pre-warmed sandboxes; an MCP gateway; an identity for the agent; a place to see runs. A vendor white paper (Ona, March 2026) lists five "primitives": sandboxed execution, governance, context and connectivity, triggers, fleet coordination. It also names the "false summit": several agents in parallel on a laptop has "no governance, no event triggering, no fleet coordination". [vendor, sells sandboxes] ona.com/files/background_agents_white_paper.pdf

### 2.2 Option B: CI in each repository

The workflow is a pipeline file in every repository. The agent runs on the CI runner.

- **GitHub Agentic Workflows** (`gh aw`): Markdown files in `.github/workflows/` are compiled to ordinary GitHub Actions workflows. They run read-only by default; writes go through pre-approved "safe outputs". Technical preview 2026-02-13, public preview 2026-06-11, generally available on 2026-10-28 for Free, Team and Enterprise plans. Because they run as Actions they "reuse your existing runner groups and policy constraints"; a "threat detection job scans all proposed changes before they are applied"; `gh aw forecast` estimates monthly AI credit spend; "enclaves" are listed to "prevent data leaks in cross-repository workflows". The entry does not say under which identity a workflow writes. [vendor: GitHub changelog, read]
- **Claude Code in CI**: GitHub Actions or GitLab CI, on your own runners, with an API key or cloud-provider credentials. Plugins come from a seed directory. [vendor] code.claude.com/docs/en/code-review, .../plugins/org
- **Copilot cloud agent** can run its sessions on GitHub Actions: 59 minutes at most, limited to the repository named when the task starts. [vendor] docs.github.com about-coding-agent

What it needs from the team: a workflow file and secrets in every repository, a token that can read the shared marketplace, and someone to keep the copies in step. The strength is that the gate sits where branch protection already is.

### 2.3 Option C: a platform team's "paved road"

A paved road is the supported default path: templates, pipelines and guardrails a team gets without building them. DORA's AI Capabilities Model (2025-09-23) lists "Quality internal platforms" as one of seven capabilities that amplify the benefit of AI: platforms "provide the capabilities and guardrails needed to scale AI benefits across the organization". The model comes from 78 interviews and a survey of almost 5,000 respondents. [measured: survey research, published by Google Cloud] cloud.google.com/blog (introducing-doras-inaugural-ai-capabilities-model)

In practice this is Option A or B delivered as a product to teams. The evidence in section 1.3 is the same evidence.

### 2.4 Option D: vendor cloud agents

| Product | Where it runs | What the team must set up | Triggers | Identity of the result | Repositories per run |
|---|---|---|---|---|---|
| Claude Code cloud sessions | Anthropic-managed VM by default; or runners inside your network ("self-hosted environments", public beta on Team and Enterprise) | Claude GitHub App or a `gh` token; a "cloud environment" (network level, environment variables, setup script) | Browser, mobile, desktop, `claude --cloud`, scheduled tasks | The person's GitHub account | `--cloud` "works with a single repository at a time" |
| Claude scheduled tasks (formerly "routines", research preview) | Same | Same, plus connectors | Schedule, HTTP call with a token, GitHub events | "Scheduled tasks belong to your individual claude.ai account. They are not shared with teammates"; commits and PRs "carry your GitHub user" | "one or more repositories" |
| Claude Tag (public beta) | Cloud sandbox, one per Slack thread | An organisation Owner provisions service accounts and applies connectors per channel, workspace or organisation | `@Claude` in a Slack channel, scheduled tasks | The Claude GitHub App authors the PR, which links back to the Slack thread | Those an admin attached to the scope |
| GitHub Copilot cloud agent | Cloud sandbox or GitHub Actions | Policies, firewall allowlist, optional custom agents | Issue assignment, agents panel, chat; Slack and Teams by a separate integration; Jira by a Marketplace app | Commits "authored by Copilot", requester as co-author, signed | Sandbox sessions "can span across repositories in one organization"; "one pull request per task" |
| OpenAI Codex cloud | Container: a setup script runs with network, then "the agent phase runs offline by default" | GitHub connection, one environment per repository, optional domain allowlist | Web, Linear (assign or `@Codex`), Slack | Runs under the requester's linked account | First repository of the environment's repo map |
| Cursor cloud agents | Cursor-managed VMs, or "Self-Hosted Machines" | An admin connects source control; environment from a snapshot or a Dockerfile in `.cursor/environment.json`; secrets in the dashboard | Web, desktop, Slack, GitHub or Bitbucket comment, Linear, API; "automations" on schedule, source-control events, Slack, Linear, PagerDuty, Sentry, webhook | On GitHub, commits are by `Cursor Agent <cursoragent@cursor.com>`, "not as the person who started the agent", who is added as a `Co-authored-by` trailer when known; on GitLab, the project access token's bot user | Not stated |
| Devin | Cognition cloud, or a customer-dedicated deployment | Organisations mapped to teams, repositories and identity-provider groups; a Jira service account | Jira (assign, label, mention, automation on Jira events), Linear, Slack, API | In Jira, a service account. On GitHub, an admin setting "Open PRs as" chooses Devin, the user when their Git account is linked, or the user only; automations and service users fall back to Devin. Commit authoring has its own setting (Devin only, co-authored, or user as author) | Not stated |

Sources, all [vendor]: code.claude.com/docs/en/claude-code-on-the-web, .../routines, .../self-hosted-environments; claude.com/docs/claude-tag/concepts/agent-identity; docs.github.com (about-coding-agent, risks-and-mitigations); learn.chatgpt.com/docs/environments/cloud-environment (where developers.openai.com/codex/cloud/environments now redirects) and learn.chatgpt.com/docs/third-party/linear; cursor.com/docs/cloud-agent, cursor.com/docs/integrations/linear, cursor.com/docs/cloud-agent/automations, cursor.com/docs/cloud-agent/security-network; docs.devin.ai/integrations/jira, docs.devin.ai/integrations/gh.

What every vendor agent needs from the team, whatever the product:

1. **A reproducible environment per repository**: a setup script or image that installs dependencies. Claude caches a setup script only if it finishes in about five minutes. [vendor] code.claude.com
2. **A network decision**: Claude defaults to "Limited" access with an allowlist; Codex: "Agent internet access is off by default"; Copilot has a firewall; Cursor has three modes (allow all, default plus allowlist, allowlist only), settable per user, environment or team, and on Enterprise the team setting "applies to every member".
3. **Secrets kept away from the model**: Claude keeps Git credentials outside the sandbox and attaches them in a proxy; Codex: "secrets are removed before the agent phase starts" (plain environment variables stay); Cursor separates build secrets (never in the running agent's environment) from runtime secrets, which are redacted from tool results, transcripts and commits but "still visible to users" in the terminal.
4. **A repository that can verify itself**: the agent is only as good as the checks it can run. Stripe runs linters locally in under five seconds before pushing. [vendor] stripe.dev
5. **A policy route that reaches the cloud**: see the Claude Code point in 1.1.

A caveat on vendor cloud agents for cross-repository work: most are scoped to one repository or one PR per run. A change that spans repositories is a fan-out of runs, which is what Spotify's and Stripe's orchestrators do. The Ona paper calls this "fleet coordination". [vendor]

### 2.5 Reading the four options together

| Question | A. Central orchestrator | B. CI per repository | D. Vendor cloud agent |
|---|---|---|---|
| Who owns the run loop | You | You, in each repository | The vendor |
| Cost to start | Years of platform work (Spotify, Stripe) | A workflow file per repository | An admin setup and an environment per repository |
| Deterministic steps between agent steps | Yes (Stripe blueprints) | Yes (pipeline steps) | Only through hooks and CI after the push |
| Cross-repository change | Native | Fan-out by script | Fan-out by script or scheduled task |
| Fits a team of a few people | No | Yes | Yes |

I found no study that compares these options on the same task. [not found]

---

## 3. Integration with ticket systems

### 3.1 Jira

- "Agents in Jira" lets a user assign a work item to an agent, mention it in a comment, or trigger it from a workflow transition. Announced in open beta on 2026-02-25; generally available by 2026-05-06 on Jira Cloud Standard, Premium and Enterprise. [vendor: Atlassian Team '26 post read; beta date and plan list from TechCrunch and an Atlassian Community post, through a search summary]
- A workflow rule "Trigger agent action" runs the agent "when any team member moves a work item to the allocated status". Setting it up needs the space-admin role. [vendor] support.atlassian.com (collaborate-on-work-items-with-ai-agents)
- "Only the person who adds the agent as an assignee" can interact with it; the output is "only visible to you" until shared as a comment. [vendor] same page
- Third-party agents come through MCP servers added in Atlassian Administration. GitHub Copilot was the first partner. Atlassian's product page lists Claude, Cursor, Codex, Copilot and a native Jira coding agent. [vendor; last sentence through a search summary]
- Each invocation uses Rovo credits; allowances apply from 2026-12-03, with admin alerts at 80% and 100%. [vendor] same page
- **Whose permissions.** A Rovo agent is built with one of two accounts. *User's account*: "The agent will adopt the identity of the person who's using it, inheriting all of their existing permissions and access", and what it changes "will appear as being performed by the user". *Agent's account*: "its own account with permissions managed by admins at the organization, space or app level", and changes are "credited to the agent". In an automation, the user's-account option runs with the permissions "of the person who creates the automation flow"; Atlassian suggests the agent's account there "to minimize security risks". [vendor] support.atlassian.com/studio/docs/understand-rovo-agent-accounts
- **Audit.** Atlassian's Team '26 post (2026-05-06) says Agents in Jira are "now generally available", that "Every agent action is logged in Jira with a full audit trail" and that "Admins control which agents run and where". [vendor] atlassian.com/blog/company-news/teamwork-collection-team-26. An open request in Atlassian's public tracker (AUTO-2432) reports that an agent's edit shows the invoking user in the change history, which is the user's-account behaviour above. [secondary: search summary of the tracker]
- **GitHub Copilot for Jira** (generally available 2026-06-24): assign the work item to GitHub Copilot, mention it in a comment, or use the automation action "Use GitHub Copilot". Installing needs a Jira site administrator and a GitHub organisation owner; each user connects their own GitHub account; "Only users with write access to the repository can trigger" the agent. Back in Jira: a comment when work starts, then "its activity streams live into the chat panel", with a link to the session. The pages describe no status transition. Jira content is copied into the PR, "visible to everyone if the repository is public". [vendor] docs.github.com (integrate-coding-agent-with-jira), github.blog/changelog/2026-06-24
- Devin in Jira: assign to a service account, add a `devin` label, mention, or define an automation on Jira events. It posts a start comment, a session link, and PR URLs as remote links. Without a service account, comments post under the admin who connected Jira. [vendor] docs.devin.ai/integrations/jira

### 3.2 Linear

- Linear's **Agent Interaction Guidelines** have six principles. The last one: "An agent cannot be held accountable"; a human remains responsible for the outcome. [vendor] linear.app/developers/aig
- The product follows it. "Delegate an issue to an agent while keeping a human teammate as the assignee." "The assignee remains responsible for the work, while the agent contributes on their behalf." [vendor] linear.app/docs/assigning-issues
- **Status.** Linear's developer guidance tells agent builders: when delegated and the issue is not already started, completed or cancelled, "move the issue to the first status in `started` when your agent begins work"; if no delegate is set, the agent "should set itself as the delegate"; when an automation delegated the issue, "leave assignment up to a human". This is a guideline for integrations, not something Linear enforces. [vendor] linear.app/developers/agent-best-practices
- Admins install agents and choose the teams each can access. Agents "are not billable seats". [vendor] linear.app/docs/agents-in-linear
- **Guidance at two levels**: workspace instructions for agents, and team instructions that take priority. How an agent applies them "depends on the specific integration". [vendor] same page
- Triage rules can assign a person and delegate to an agent in one flow. The agent session then uses "the automatically assigned teammate's identity". [vendor] linear.app/docs/assigning-issues
- Measurement: Insights can be segmented by agent (Business and Enterprise plans); the activity feed records delegation history. [vendor] same page
- Codex in Linear: assign or mention `@Codex`. It chooses the environment from the repository Linear suggests; when unclear it uses the one used most recently. A triage-rule run uses the issue creator's account. At the end it posts a summary and a link where a person can create the PR. [vendor] learn.chatgpt.com/docs/third-party/linear
- Cursor in Linear: repository chosen from `[repo=owner/repository]` in the issue, then a label in a group named "repo", then a project label, then a dashboard default. "Linear requires a human assignee for rules to fire." [vendor] cursor.com/docs/integrations/linear

### 3.3 GitHub Issues

- An issue is assigned to Copilot like to a person. The agent adds a reaction, starts a session, opens a PR and requests review. [vendor: GitHub docs through a search summary]
- "Only users with write access to the repository can trigger" the agent; comments from others never reach it. Hidden characters and HTML comments are filtered from the input. [vendor] docs.github.com risks-and-mitigations
- Claude scheduled tasks can start on GitHub events such as a PR opening; each event starts an independent session, and events over the hourly cap are dropped. [vendor] code.claude.com/docs/en/routines

### 3.4 What the evidence says about the four sub-questions

| Sub-question | What is documented |
|---|---|
| Triggers | Assignment, mention, label, workflow transition, triage rule, automation on events, webhook. Stripe also starts runs from a button on tickets its CI files for flaky tests |
| Status sync | Linear: by guideline, the agent moves the issue to the first "started" status; closing follows Linear's usual PR automation (not checked here). Jira: comments, a live activity stream and links (Copilot, Devin); no page read says the agent transitions the work item. Moving a Jira item is left to Jira's own automation rules |
| Who is the assignee | Linear: the human stays assignee, the agent is a delegate. Jira and GitHub Issues: the agent or its service account can be the assignee |
| Audit | Linear: activity feed and insights. Jira: "full audit trail" per Atlassian; whether an edit shows the agent or the person depends on the agent's account type. Devin: an audit-log API on Enterprise. GitHub: session logs and audit-log events for administrators, kept 180 days in the interface, with streaming for longer retention [vendor: GitHub docs through a search summary] |

A design consequence: the ticket key has to travel with the work by convention (branch name, PR title, remote link), because status sync differs per tracker and per agent and cannot be assumed.

---

## 4. Identity, permissions, secrets, sandboxes, accountability

### 4.1 Two identity models, and one hybrid

| Model | Examples | Effect on review | Effect on reach and audit |
|---|---|---|---|
| The agent acts **as the person who asked** | Claude Code cloud sessions and scheduled tasks; Claude Code in Slack; Codex from Linear; a Devin session | On GitHub the person is the PR author and cannot approve their own PR. Claude's auto-fix replies "are posted using your GitHub account", labelled as coming from the agent | The agent can reach what the person can reach. The audit trail shows the person |
| The agent has **its own app or service account** | Claude Tag in a channel; Cursor cloud agents on GitHub (`Cursor Agent`, requester as co-author trailer); Devin with "Open PRs as: Devin"; a Rovo agent on an agent's account; Devin's Jira service account; Stripe and Spotify orchestrators (identity not described in their posts) | A human can approve. Branch rules must stop the bot from being the only approver | "What Claude can do never changes based on who asked"; "Anyone in the channel gets the same capability". The audit trail shows the service account |
| **Hybrid** | GitHub Copilot cloud agent | Commits are authored by Copilot with the requester as co-author. "GitHub prevents the user who asked" from approving. When the agent opens a PR under its own app identity, one more approval is required | Signed commits; each commit links to its session log |

Sources [vendor]: code.claude.com/docs/en/routines and .../claude-code-on-the-web; claude.com/docs/claude-tag/concepts/agent-identity; docs.github.com risks-and-mitigations; docs.devin.ai/integrations/jira and /gh; cursor.com/docs/cloud-agent/security-network; support.atlassian.com (understand-rovo-agent-accounts); learn.chatgpt.com linear.

Two products make the model a setting rather than a fact: Devin ("Open PRs as") and Rovo (user's account or agent's account). A team harness should record which was chosen, per scope, because the review rule that follows is different. Devin's GitHub App asks for write access to contents, pull requests, actions and workflows, and its docs recommend branch protection "to ensure all required checks pass before Devin can merge changes": the app can merge unless a rule stops it. [vendor] docs.devin.ai/integrations/gh

My reading, not a sourced fact: a shared service identity moves the access decision from the person to the scope (channel, team, repository group). The scope then has to be drawn as carefully as a role.

A vendor-written maturity model for agent identities (Akto, published by the Cloud Security Alliance, 2026-08-20) gives five stages: Untracked, Discovered, Contextualized, Right-sized, Governed. Its requirement: each agent has an identity "never shared with another agent or a human administrator", and credentials live shorter than the time needed to detect misuse. [vendor] cloudsecurityalliance.org

### 4.2 Secrets and sandboxes

- Claude cloud sessions: "git credentials and signing keys stay outside the sandbox, and a proxy authenticates on the session's behalf with scoped credentials". With network access disabled, the session can still reach the Anthropic API, "which may allow data to exit the VM". [vendor] code.claude.com/docs/en/claude-code-on-the-web
- Claude Tag: the sandbox holds "no stored credentials"; an "Agent Proxy" attaches the credential at the network boundary, so "the model and the sandbox itself are not given the key". Only HTTP and HTTPS cross it. [vendor] claude.com/docs/claude-tag
- Self-hosted Claude runners: checkouts, build artefacts and secrets stay on your machines; the conversation still goes to Anthropic's API. A runner serves one owner at a time so checked-out code never mixes. [vendor] code.claude.com/docs/en/self-hosted-environments
- Codex cloud: secrets are available only to setup scripts and "are removed before the agent phase starts"; the setup script runs "in a separate Bash session from the agent". [vendor] learn.chatgpt.com/docs/environments/cloud-environment
- Stripe: devboxes have no real user data, no production services and no arbitrary egress, which is why agents run there "with full permissions and no confirmation prompts". [vendor] stripe.dev part 2
- Anthropic's own engineering: developers and agents work on remote VMs whose traffic is "egress-allowlisted"; all agent actions go to the security log system; agents are treated "as a new type of insider threat". [vendor] claude.com/blog (how-anthropic-secures..., Jason Clinton, 2026-07-21)
- A warning from the Claude documentation: when an agent replies on a PR under a person's account, it can trigger comment-driven automation (Atlantis, Terraform Cloud, custom Actions on `issue_comment`). [vendor] code.claude.com/docs/en/claude-code-on-the-web

### 4.3 Who is accountable for a merge

- Linear: "An agent cannot be held accountable." [vendor] linear.app/developers/aig
- Intercom: "The human who ships the code remains accountable for the outcome." Engineers who ship a change monitor it in production. [vendor] intercom.com/blog, 2026-04-21
- Anthropic: "Human accountability is still central to our process." [vendor] claude.com/blog, 2026-07-21
- GitHub Copilot: the agent "cannot approve or merge a pull request"; workflows triggered by its PRs wait for a person with write access. [vendor] docs.github.com
- Claude Code Review: "A review never approves or blocks the pull request." [vendor] code.claude.com/docs/en/code-review
- Compliance: Intercom labels and logs every AI-approved PR (comments, decision, tests, merge) and engaged an auditor before scaling, citing SOC 2, HIPAA, ISO 27001 and ISO 42001. "The 'who' may change, but the 'what' doesn't." [vendor] intercom.com/blog

### 4.4 Separating the agent that writes from the one that reviews

| Company or product | Writer | Reviewer | Reported result | Tag |
|---|---|---|---|---|
| Stripe | Minion | A human engineer other than the one who started the run; two CI rounds at most | 1,300+ PRs a week | [vendor] |
| Spotify | Honk | Deterministic verifiers (format, build, test), then a model acting as judge on the diff | The judge is reported to veto about 25% of sessions | [secondary: summary of Spotify's part 3] |
| Intercom | Claude | A review agent split into independent sub-agents (problem description, diff against intent, safety, logic, practices). It refuses large or broad changes | 93% of PRs agent-driven; 19.2% auto-approved; revert rate 0.53% for AI-authored backend PRs against 5.39% for human-authored; downtime from breaking changes down 35% while deployments doubled | [vendor] |
| Anthropic | Claude (about 80% of merged code) | Several narrow review agents plus static analysis; humans for "regulated or truly critical code"; new reviewers run in "shadow mode" first; a risk-weighted sample of approvals is checked by humans | PRs with substantive review comments went from 16% to 54% | [vendor] |
| Vercel | Agents and humans | A classifier marks each PR LOW or HIGH risk (authentication, payments, data integrity, security, infrastructure are HIGH). The agent's approval of a LOW PR satisfies branch protection; HIGH still needs a human. Two hard rules were reported in the first pass (100 or more changed files, CODEOWNERS paths) and not re-confirmed | 58% of PRs in the largest monorepo merge without human review; merge time 29 h to 10.9 h; 671 low-risk PRs skipped review with zero reverts, against 2 of 513 (0.39%) for reviewed low-risk PRs; about $0.054 per assessment (first pass) | [vendor: Vercel post of 2026-04-06; the page returned 404 to my fetch twice, so all of this is through search summaries] |
| Cursor "PR Routing & Approval" | Any | An agent that "can approve low-risk changes" from a risk score, policy files and the findings of review agents. If the PR changes a policy or routing file, the agent "does not use the changed content to relax review requirements for that same PR". On Enterprise only team admins edit the configuration. The page does not say which identity submits the approval | Not published | [vendor] cursor.com/docs/approval-agents |
| Zalando | Agents and humans | A bot scores each PR low, medium or high from rules drawn from past incidents | About 33% auto-approved; lead time down 20 to 40% for those. Side effects: teams split PRs to isolate low-risk parts; PR size and cyclomatic complexity rose | [vendor] |
| Claude Code Review | Any | Several agents, a verification step; reads `REVIEW.md` "from the base or default branch and never from the pull request's own changes" | Not published | [vendor] |

One incident shows why the separation must be enforced by access, not by instructions. At Anthropic, after a model upgrade, an incident-response agent with three narrow permissions asked a code-writing agent over Slack to push a fix. "This was caught at a human review gate as designed." Anthropic's conclusion: draw boundaries "around access and actions, not around a model's instructions". [vendor] claude.com/blog, 2026-07-21

---

## 5. Governance and measurement at team level

### 5.1 What gets worse first: review

Faros (a vendor of engineering analytics; telemetry from 22,000 developers in 4,000 teams over two years; comparison between low and high AI adoption; correlation, not cause): PR size +51%, median review time about 5 times longer, incidents per PR about 3 times higher (+242.7%), code churn about 10 times higher, deployments per week -11.7%, while epics completed rose 66.2%. A later Faros release on 12 months of data gives a much smaller rise in incidents per PR (+14.5%) and reports PRs merged with no review up 76.3%. [vendor telemetry; the second set only through a search summary] faros.ai/research/ai-acceleration-whiplash

The two Faros releases disagree by an order of magnitude on incidents per PR. Treat the direction (review is the bottleneck) as supported and the sizes as unsettled.

### 5.2 What the companies that publish actually track

- **Uber**, five layers, weekly and monthly: total cost and users; unit economics per tool; model economics; drivers (adoption, engagement, workload); and for managed agents, outcomes such as "cost per merged PR, revert rate, MTTR". [vendor] uber.com/blog/efficient-software-factory
- **Intercom**: revert rate split by author type; downtime from breaking changes; time to approval. [vendor]
- **Zalando**: monthly and weekly active users, model and client from the proxy; PR size and code complexity over time. No cost figure published. [vendor]
- **Anthropic**: share of PRs with substantive review comments; share of past incidents current checks would have caught (about a third). [vendor]
- **Claude Code analytics** (Team and Enterprise): PRs and lines "with Claude Code", accept rate, a leaderboard of top contributors. Attribution matches session activity against the merged diff within a window of 21 days before to 2 days after merge; code rewritten by more than 20% is not counted; merged PRs get a `claude-code-assisted` label. The documentation calls these numbers "deliberately conservative". [vendor] code.claude.com/docs/en/analytics
- **DX** (vendor of developer-experience analytics): three dimensions: utilisation, impact, cost. [secondary: search summary] getdx.com

The project's own proposal already rejects usage counts and leaderboards as targets. The products ship them by default; the published practice of Uber and Intercom is closer to the proposal's list (time in review, after-the-fact fixes, revert rate, cost per merged PR).

### 5.3 Cost budgets

- **Uber** (February to August 2026): weekly agent users up 7 times, weekly agent requests up 9.4 times, total spend "relatively stable since April". Controls: one shared spend tier for interactive tools and separate tiers for managed agents; Slack alerts at 50%, 80% and 100% of expected spend; "tier upgrades need manager sign-off"; automatic compaction at 400,000 tokens; medium reasoning effort by default; sub-agents on a cheaper model; a dashboard that flags 16 session anti-patterns with their cost. [vendor] uber.com/blog
- An earlier secondary report said Uber's AI costs had risen 6 times since 2024. [secondary: Pragmatic Engineer, through a search summary]
- **Claude Enterprise**: spend limits at organisation, group and user level, optional pooled budgets, alerts at 75% and 90%. [vendor, through a search summary] claude.com/blog (giving-admins-more-visibility...)
- **Claude Code Review**: three depths (Quick, Standard, Deep) set per organisation or repository; a monthly spend limit. [vendor] code.claude.com/docs/en/code-review
- **Devin**: budgets cap usage with one account limit, shared pools per team or project, and per-user limits; a session stops when the budget runs out; limit changes go to the audit log. [vendor, through a search summary] docs.devin.ai
- **GitHub Copilot**: budgets, cost centres and overage policies across all Copilot surfaces. [vendor] docs.github.com governance-controls
- **Jira agents**: Rovo credits per invocation from 2026-12-03. [vendor]
- Scheduled and event-triggered runs have their own caps: Claude scheduled tasks allow 100 scheduled runs an hour per account, and they "count against your account's usage". [vendor] code.claude.com/docs/en/routines

I found no company that publishes its cost per merged PR. [not found]

### 5.4 Governance controls that exist as product features

- GitHub: "Enterprise AI Controls" and an "agent control plane", generally available since late February 2026: which agents are allowed, MCP servers, agent session list, audit events. Rulesets apply "to both agents and humans" and can target repositories by naming convention or custom property. [vendor: changelog and docs; part through a search summary]
- Claude Code: managed settings locks (permission rules, hooks, MCP allowlist, sandbox domains), group-specific configurations on Enterprise, owner-controlled toggles for cloud sessions and scheduled tasks. [vendor] code.claude.com/docs/en/managed-settings
- Uber and Stripe route all tool access through one MCP gateway or server (more than 1,000 servers; nearly 500 tools), which gives one place for authentication and policy. [vendor]
- Zalando: an AI section in its internal technology radar, legal assessment per early-stage use case, and scanning of deployed images to detect model usage. [vendor]

---

## 6. Maturity models published for teams or organisations

| Model | Author, date | Unit | Levels | Evidence behind it | Tag |
|---|---|---|---|---|---|
| Agentic Engineering Maturity Model | Augment Code (vendor), 2026-06-12 | Engineering organisation | 1 Ad-Hoc; 2 Standardized (shared, version-controlled guidance such as a root AGENTS.md, layered global, project, sub-directory); 3 Orchestrated (coordinated multi-agent workflows in CI, traceable agent identities, event triggers, clear ownership); 4 Systematic (shared memory across sessions and people, a learning loop); 5 Autonomous (tiered approval by risk, humans "on the loop") | None of its own; five dimensions: agent configuration, knowledge sharing, governance, measurement, organisational design | [vendor] |
| AI Codebase Maturity Model | A. Anderson, arXiv 2604.09388, April 2026 | A codebase and its maintainers | 1 Assisted (prompt and review); 2 Instructed (preferences in files); 3 Measured (feedback becomes visible); 4 Adaptive (the system acts on its own metrics); 5 Semi-Automated (the system proposes, humans approve); 6 Fully Autonomous. "Each level subsumes the previous. You cannot skip levels." | One author's 100-day report on one open-source project | [measured on one case, self-reported] |
| AI Engineering Maturity Model, "5 Stages for Teams" | Augment Code (vendor), 2026-07-20 | Team | 1 Ad Hoc Assistance; 2 Supervised Agents; 3 Standardized Team Practice (sanctioned tools, shared standards, measured rollout); 4 Autonomous Delegation (headless agents in remote environments return PRs); 5 Orchestration. Each stage names the constraint that blocks the next: trust, review bandwidth, platform quality and the review pipeline, risk-tiered governance, observability and model routing. Suggested metrics change by stage: acceptance and usage (1 to 2), PR cycle and review time (3), rework rate, bug rate and cost per shipped feature (4 to 5) | Cites surveys (Stack Overflow, DORA, Faros); no distribution of teams across stages | [vendor] |
| Agentic AI adoption maturity model | Microsoft Learn, 2026-03-31, updated 2026-09-30 | Enterprise, all agents, not only coding | 100 Initial; 200 Repeatable; 300 Defined; 400 Capable; 500 Efficient. Five pillars: AI strategy and experience; business strategy; AI governance and security; technology and data; organisation and culture. Each pillar is scored separately; Microsoft's guidance warns against reducing it to one number (that warning through a search summary) | "based on the Capability Maturity Model"; no data | [vendor] |
| AgentStripes | Naik et al., arXiv 2610.18603, 2026-10-13 | One agent release, not a team | 0 to 7 stripes from 40 capabilities in 12 process areas, each rated 0 to 3 **and** given an evidence grade E0 to E5 that caps how much the rating counts; three gates (basic, safety, proof) hold the level down | 30 public repositories, static evidence only: 26 at one stripe, 4 at two. The authors: "the stripes have not been shown to predict reliability or safety" | [measured, exploratory] |
| The Five Levels | Dan Shapiro, 2026-01-23 | A developer or a small team | 0 fully manual; 1 discrete tasks handed off; 2 pairing; 3 the human reviews; 4 specs in, unattended runs; 5 "dark factory": "a black box that turns specs into software" | Opinion | [secondary] |
| Identity Maturity Model for AI Agents | Akto, on the Cloud Security Alliance blog, 2026-08-20 | Organisation, identity only | Untracked; Discovered; Contextualized; Right-sized; Governed | Opinion | [vendor] |
| OWASP agentic AI adoption and governance model | OWASP GenAI Security Project, June 2026 | Organisation, security | Two axes kept apart: nine adoption tiers AT0 to AT8, ordered by trust boundary and autonomy (AT0 is unmanaged "shadow AI"), and a governance scale from 0 (unaware, ad hoc) upward, with level 3 described as integrated, continuous oversight: kill switches that work, policy in machine-readable form. Secondary sources give the scale as 0 to 4 or stop at 3, and date the report 2026-06-01 or 06-03 | Not read in the original | [secondary: CSA research note and press, through a search summary] |
| DORA AI Capabilities Model | DORA / Google Cloud, 2025-09-23 | Organisation | Not levels. Seven capabilities: clear AI stance; healthy data ecosystems; AI-accessible internal data; strong version control; small batches; user-centric focus; quality internal platforms | 78 interviews, survey of almost 5,000 | [measured] |
| Technology Radar | Thoughtworks, vol. 35, 2026-11-04 | Techniques, not organisations | Rings, not levels: shared instructions Adopt; plugin marketplace Trial; enterprise harness Assess | Consultancy experience | [secondary] |

What they agree on, in order: shared files first; then identities, triggers and CI integration; then measurement that feeds back; then approval tiered by risk. What none of the team models has: a check you can run.

Three ideas worth taking from the newer entries:

- **Separate the claim from its evidence** (AgentStripes; also the critique of OWASP's model, that it records what an organisation says and not who verified it). This project already does it: levels are measured, never declared.
- **Separate how far agents are let loose from how well they are governed** (OWASP's two axes). A team can run unattended agents with weak controls; one number would hide that.
- **Name the constraint that blocks the next stage** (Augment's stages). It matches "each failing check carries the next action". Augment's own page cites no distribution of organisations across its levels. A figure of "7%" of organisations at the top stage of an Anthropic framework appeared in one search result and I could not confirm it. [not found]

---

## 7. What a team-level ladder could look like next to this project's

### 7.1 Starting points taken from the two project documents

- The repository ladder has five levels: 0 None, 1 Framed, 2 Looped, 3 Verified, 4 Delegated. Levels are **measured**, never declared; "a level is a place where you can stay"; each failing check carries the next action.
- The `ai-sdlc` plugin has seven phases (`/ticket`, `/dev`, `/review`, `/qa`, `/secu`, `/ship`, `/run`), three layers (platform, base, team), extension points read on the base branch, and locks that are never text.

The ladder below keeps those rules. Its unit is a **scope**: a named set of repositories that share one base (one plugin marketplace at one version) and one owner. A team is one scope; a company can have several.

### 7.2 Proposed ladder

| Level | Name | What it means | Checks a CLI can measure | Evidence it rests on |
|---|---|---|---|---|
| T0 | Scattered | Each repository, or each person, has its own setup | none | Thoughtworks: copying assets between repositories is the problem the marketplace solves |
| T1 | Shared | One versioned base reaches every repository of the scope | A marketplace repository exists with an owner · every repository of the scope names it and a version · no repository carries a diverging copy of a base skill (hash compare) · every repository is at repository level 1 or more | Claude Code managed keys; Intercom via JAMF; Zalando central collection |
| T2 | Fed | What repositories learn goes back into the base | The base has had a release in the last N days · at least one base change cites an override or a `rule:` comment from a repository of the scope · a base release has a recorded bench run · every repository is at level 2 or more | Proposal's "harvest of the pilots' overrides"; Intercom's gap classification; release channels in the Claude Code docs |
| T3 | Guarded | Identity, gates and secrets are held by the platform, not by text | Agent PRs in the scope are authored by an app or service identity, or the requester is barred from approving · branch rules require an approval by someone other than the author on every repository · gate files are read on the base branch · no agent PR was merged by its own author in the window · a spend limit exists · every repository where agents open PRs is at level 3 | Copilot's mitigations; Claude Tag identity; Claude Code Review and `REVIEW.md`; Anthropic's cross-agent incident; Stripe devboxes |
| T4 | Orchestrated | A ticket becomes a reviewed PR with no human session, across the scope, inside a budget | At least one workflow is triggered by the ticket system or a schedule · its runs carry the ticket key through to the PR · after-the-fact fixes on agent PRs (signal S2) are zero over the window, per repository · time in review per PR is not rising over the window · cost per merged agent PR is recorded and under the budget · the repositories it runs on are at level 4 | Stripe, Spotify, Ramp, Uber; Linear's delegate model; Uber's cost layers |

Notes on the design:

- **A scope's level is capped by its repositories.** T3 without repositories at "Verified" would be a gate with nothing behind it. The proposal already says the framework opens phases according to the repository level; the team ladder states the same dependency the other way round.
- **T3 before T4, always.** Every company that runs unattended agents at scale had the sandbox, the identity and the review gate first. Stripe's agents have "full permissions" only because the devbox has no production access.
- **Risk-tiered auto-approval is not a level.** Intercom (19.2%), Zalando (33%) and Vercel (58%) do it, but each on top of T4-like controls, and Zalando reports the side effects. It fits better as an option a T4 scope may turn on, with its own measured conditions (revert rate by author type, a sampled human check), than as a rung everyone should aim at.
- **Where each phase of `ai-sdlc` runs at team level.** `/ticket` at the ticket system's trigger; `/dev` in a cloud agent or orchestrator run; `/review`, `/qa` and `/secu` as CI checks reading the base branch; `/ship` and `/run` centrally, proposing only. This is Option B for the gates and Option D or A for the writing, which is also what Stripe and Spotify do: the agent writes in one runtime, the verification runs in another.
- **What the CLI can and cannot see.** Authorship, approvals, branch rules, ticket keys, review time and S2 come from the Git host's API, as `harness harvest github` already does for one repository. Cost comes from vendor exports (Claude analytics API, Copilot billing, Devin budgets) and cannot be read from a repository; the check can only verify that a number is recorded.
- **Reach and guard are two things** (OWASP's two axes). A scope that already runs ticket-triggered agents while its T3 checks fail is not "almost T4": it is T2 with unguarded reach. The state should say so in plain words, the way the repository state reports "references without a target".
- **Identity is a recorded setting, not an assumption.** Devin and Rovo let an admin choose between acting as the user and acting as a service account. The T3 check has to read the actual author and approver of merged PRs from the Git host, not the configuration someone declared.
- **Next to the levels, a view by dimension**, as the repository ladder has its layer view. Five columns cover what this note found: distribution, where workflows run, ticket link, identity and gates, measurement and cost. A scope can be strong on one and absent on another; the level is the weakest link, the view says where.

### 7.3 What this ladder does not claim

- That a higher level means better delivery. The repository ladder says the same of itself. The proof is the trend of S2, review time and revert rate per scope.
- That the order is validated. It follows the order the published models and company accounts share, and the dependencies between controls. Nobody has measured it.

---

## Not found

- An organisation-level or cross-repository mechanism for AGENTS.md. The format only nests inside a repository.
- Whether Cursor Team Rules apply to cloud agents (the identity question is answered in 2.4), and which identity submits a Cursor approval agent's approval.
- Any Jira-side page stating that a coding agent transitions the work item (Atlassian, Copilot for Jira and Devin pages read). Linear's guideline is the only explicit statement found.
- Where exactly the Jira agent audit trail is read, and its retention. Atlassian asserts it exists; the page describing it was not found.
- Which identity a third-party agent (Copilot, Claude, Codex) holds inside Jira when assigned a work item.
- Whether Devin can approve a PR; its documentation implies it can merge.
- The full text of Vercel's post (HTTP 404 on two attempts): the two hard rules and the cost per assessment rest on the first pass's search summary.
- An org-level convention for AGENTS.md on GitHub (for example through the `.github` repository). Blog posts describe a "meta-repository" with sync scripts or symlinks; no vendor documents one.
- The body of GitHub's "Governing agents" Well-Architected page; the page did not render.
- A study comparing a central orchestrator, CI per repository and vendor cloud agents on the same work.
- A team or organisation maturity model backed by measurement.
- A published cost per merged PR from any company. Uber tracks it and does not publish it.
- Confirmation that Intercom gates skills on evaluations before distribution. Its post says the most-used skills "have high-quality evals"; it does not describe a gate.
- The "7%" of organisations at the top stage attributed to an Anthropic framework.
- The identity used by Stripe's and Spotify's agents when opening PRs.
- OWASP's original report: the level names for governance levels 1 and 2, and whether the scale ends at 3 or 4.
- Which Thoughtworks Radar volume moved "curated shared instructions" to Adopt: a secondary guide says vol. 34 (April 2026); section 1.3 lists it next to the vol. 35 items.

## Sources

Product documentation and vendor pages
- https://code.claude.com/docs/en/plugins/org
- https://code.claude.com/docs/en/managed-settings
- https://code.claude.com/docs/en/claude-code-on-the-web
- https://code.claude.com/docs/en/routines
- https://code.claude.com/docs/en/self-hosted-environments
- https://code.claude.com/docs/en/code-review
- https://code.claude.com/docs/en/analytics
- https://claude.com/docs/claude-tag/concepts/agent-identity
- https://claude.com/blog/giving-admins-more-visibility-and-control-over-claude-usage-and-spend
- https://docs.github.com/en/copilot/concepts/agents/coding-agent/about-coding-agent
- https://docs.github.com/en/copilot/concepts/agents/cloud-agent/risks-and-mitigations
- https://docs.github.com/en/copilot/how-tos/copilot-on-github/customize-copilot/add-custom-instructions/add-organization-instructions
- https://docs.github.com/en/copilot/reference/custom-agents-configuration
- https://docs.github.com/en/copilot/concepts/enterprise/governance-controls
- https://github.blog/changelog/2026-02-26-enterprise-ai-controls-agent-control-plane-now-generally-available/
- https://github.blog/changelog/2026-04-02-copilot-organization-custom-instructions-are-generally-available/
- https://github.blog/changelog/2026-02-13-github-agentic-workflows-are-now-in-technical-preview/
- https://github.blog/changelog/2026-10-28-github-agentic-workflows-generally-available
- https://cursor.com/docs/context/rules
- https://cursor.com/docs/cloud-agent
- https://cursor.com/docs/cloud-agent/automations
- https://cursor.com/docs/integrations/linear
- https://developers.openai.com/codex/cloud/environments
- https://learn.chatgpt.com/docs/enterprise/managed-configuration
- https://learn.chatgpt.com/docs/third-party/linear.md
- https://docs.devin.ai/integrations/jira
- https://docs.devin.ai/integrations/gh
- https://cursor.com/docs/cloud-agent/security-network
- https://cursor.com/docs/approval-agents
- https://learn.chatgpt.com/docs/environments/cloud-environment
- https://linear.app/developers/agent-best-practices
- https://docs.github.com/en/copilot/how-tos/use-copilot-agents/coding-agent/integrate-coding-agent-with-jira
- https://github.blog/changelog/2026-06-24-github-copilot-for-jira-is-now-generally-available/
- https://support.atlassian.com/studio/docs/understand-rovo-agent-accounts/
- https://www.atlassian.com/blog/company-news/teamwork-collection-team-26 (2026-05-06)
- https://jira.atlassian.com/browse/AUTO-2432 (not opened)
- https://techcrunch.com/2026/02/25/jiras-latest-update-allows-ai-agents-and-humans-to-work-side-by-side (not opened)
- https://docs.devin.ai/llms.txt
- https://linear.app/developers/aig
- https://linear.app/docs/agents-in-linear
- https://linear.app/docs/assigning-issues
- https://support.atlassian.com/jira-software-cloud/docs/collaborate-on-work-items-with-ai-agents/
- https://www.atlassian.com/blog/announcements/ai-agents-in-jira
- https://agents.md/
- https://github.com/microsoft/apm

Company engineering accounts
- https://stripe.dev/blog/minions-stripes-one-shot-end-to-end-coding-agents (2026-02-09)
- https://stripe.dev/blog/minions-stripes-one-shot-end-to-end-coding-agents-part-2
- https://engineering.atspotify.com/2025/11/spotifys-background-coding-agent-part-1 (2025-11-06)
- https://engineering.atspotify.com/2025/12/feedback-loops-background-coding-agents-part-3
- https://ramp.com/blog/introducing-inspect (2026-10-27)
- https://www.uber.com/blog/efficient-software-factory/ (2026-08)
- https://engineering.zalando.com/posts/2026/08/agentic-engineering-at-zalando-a-snapshot.html (2026-08-14)
- https://ideas.fin.ai/p/how-we-use-claude-code-today-at-intercom (2026-03-19)
- https://intercom.com/blog/ai-is-approving-our-pull-requests-heres-how-we-made-it-safe (2026-04-21)
- https://claude.com/blog/how-anthropic-secures-its-ai-native-software-development-lifecycle (2026-07-21)
- https://vercel.com/blog/58-percent-of-prs-in-our-largest-monorepo-merge-without-human-review (2026-04-06, read through a search summary)

Research, surveys, models and commentary
- https://cloud.google.com/blog/products/ai-machine-learning/introducing-doras-inaugural-ai-capabilities-model (2025-09-23)
- https://dora.dev/research/2025/ai-capabilities-model
- https://www.faros.ai/research/ai-acceleration-whiplash
- https://www.thoughtworks.com/radar/techniques/enterprise-harness (2026-11-04)
- https://www.thoughtworks.com/en-us/radar/techniques/agent-plugin-marketplace (2026-11-04)
- https://www.thoughtworks.com/radar/techniques/curated-shared-instructions-for-software-teams
- https://www.augmentcode.com/guides/agentic-engineering-maturity-model (2026-06-12)
- https://arxiv.org/abs/2604.09388 (2026-04)
- https://arxiv.org/abs/2610.18603 (2026-10-13, AgentStripes)
- https://www.augmentcode.com/guides/ai-engineering-maturity-model (2026-07-20)
- https://learn.microsoft.com/en-us/agents/adoption-maturity-model (2026-03-31)
- https://infosecurity-magazine.com/news/owasp-agentic-ai-security-maturity (not opened)
- https://www.danshapiro.com/blog/2026/01/the-five-levels-from-spicy-autocomplete-to-the-software-factory/ (2026-01-23)
- https://cloudsecurityalliance.org/blog/2026/08/20/governing-ai-agent-identities-an-identity-maturity-model-for-ai-agents
- https://labs.cloudsecurityalliance.org/research/csa-research-note-owasp-agentic-ai-governance-maturity-v2-20/ (not opened)
- https://ona.com/files/background_agents_white_paper.pdf (2026-03)
- https://getdx.com/ai-measurement-framework/ (not opened)
- https://newsletter.pragmaticengineer.com/p/how-uber-uses-ai-for-development (not opened)

Repository statistics: GitHub API, read on 2026-11-21 for the eleven repositories in section 1.4.

Project documents read
- docs/maturity.md
- docs/ai-sdlc/proposal.md
