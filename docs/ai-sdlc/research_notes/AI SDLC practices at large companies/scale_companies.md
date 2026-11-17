# How large product/tech companies rolled out AI coding agents across many teams (2024 → Nov 2026)

Research date: 2026-11-14. Items before 2025 are flagged **[older]**. "Measured" = a number the company reports from its own telemetry or a paper with a method; "claimed" = estimate, vendor marketing, or no method given. Anthropic/OpenAI/Atlassian customer pages are vendor marketing even when they quote the customer.

---

## 1. Spotify: Honk, Fleet Management / Fleetshift, Backstage, context engineering, verification

### Takeaway
Spotify did not roll out "an agent" so much as plug an LLM into a fleet-change platform it already had (Fleet Management, since 2022; executed by Fleetshift) and a standardised catalog (Backstage). Honk is a central, narrow, heavily sandboxed agent (Claude via Claude Code / Agent SDK since July 2025) whose output is gated by deterministic verifiers plus an LLM judge; the hard lessons were context engineering and the absence of tests in target repos.

### Cited Findings
**Pre-agent platform (the base Honk sits on)**
- Fleet Management runs source-to-source transformations as containerised jobs across repos and opens PRs automatically; since mid-2024 roughly half of Spotify's PRs were automated by it **[older baseline]** — [Spotify Eng, Honk Part 1, 2025-11-06](https://engineering.atspotify.com/2025/11/spotifys-background-coding-agent-part-1)
- Its deterministic limit: the automated Maven dependency updater script grew past 20,000 lines to handle corner cases; only a few teams had the expertise to write fleet-wide changes — [Honk Part 1](https://engineering.atspotify.com/2025/11/spotifys-background-coding-agent-part-1)
- By June 2026: over 2.5 million automated maintenance PRs merged via Fleet Management, most auto-merged with no human in the loop; Fleetshift does orchestration (targets, scheduling, progress tracking), Honk does the code modification — [Spotify Eng, "Coding is no longer the constraint", 2026-06-03](https://engineering.atspotify.com/2026/6/code-with-claude-coding-is-no-longer-the-constraint)
- Fleet Management introduced in 2022; Spotify integrated the Claude Agent SDK into it in July 2025 — [Anthropic customer page (vendor)](https://claude.com/customers/spotify)

**Agent history (what they tried)**
- Investigation started in February (2025 implied); first tried open-source agents Goose and Aider, which did not reliably produce mergeable PRs across thousands of repos — [Spotify Eng, Honk Part 2 "Context Engineering", 2025-11-24](https://engineering.atspotify.com/2025/11/context-engineering-background-coding-agents-part-2)
- Then a homegrown loop on LLM APIs (prompt + file list, max 10 turns per session, 3 session retries). Failure modes: users had to write git-grep patterns to pick context files (too broad overflowed the window, too narrow starved it); multi-file cascading changes ran out of turns; agent forgot the task as context filled — [Honk Part 2](https://engineering.atspotify.com/2025/11/context-engineering-background-coding-agents-part-2)
- Moved to Claude Code: top-performing agent, used for about 50 migrations, source of most background-agent PRs merged — [Honk Part 2](https://engineering.atspotify.com/2025/11/context-engineering-background-coding-agents-part-2)
- They wrapped the agent in an internal CLI that delegates to an agent, runs format/lint via local MCP tools, evaluates the diff with an LLM judge, ships logs to GCP and traces to MLflow; this let them swap agents/LLMs "multiple times" — [Honk Part 1](https://engineering.atspotify.com/2025/11/spotifys-background-coding-agent-part-1)
- Honk runs Claude via the Agent SDK inside Spotify's own harness, in Kubernetes pods for concurrency; Honk v2 adds shared sessions, team projects, orchestration ("Chirp"); a "Goose Farm" dashboard lists active sessions — [Spotify Eng 2026-06-03](https://engineering.atspotify.com/2026/6/code-with-claude-coding-is-no-longer-the-constraint)
- Sonnet 4.5 chosen as default model (date not given) — [Anthropic customer page (vendor)](https://claude.com/customers/spotify)

**Volume and results**
- More than 1,500 agent-generated PRs merged to production; "hundreds" of developers interact with the agent; 60–90% time savings vs manual on these migrations (claimed, no method) — [Honk Part 1, 2025-11](https://engineering.atspotify.com/2025/11/spotifys-background-coding-agent-part-1)
- 650+ agent-generated PRs merged per month; up to 90% time saved on complex migrations — [Anthropic customer page (vendor, undated)](https://claude.com/customers/spotify)
- Migration types: Java value types → records (AutoValue), Scio upgrades with breaking changes, Backstage new frontend system migration, YAML/JSON config changes; also ADR capture from Slack threads and PM-authored small changes — [Honk Part 1](https://engineering.atspotify.com/2025/11/spotifys-background-coding-agent-part-1)
- A Java migration across backend services took three days; work that once took hundreds of teams weeks/months can be done by one engineer in days (claim) — [Spotify Eng 2026-06-03](https://engineering.atspotify.com/2026/6/code-with-claude-coding-is-no-longer-the-constraint)
- Org-wide (June 2026): >99% of engineers use AI coding tools weekly; 94% report feeling more productive (survey); PR frequency +76%; adoption accelerated after Opus 4.5 (late 2025) — [Spotify Eng 2026-06-03](https://engineering.atspotify.com/2026/6/code-with-claude-coding-is-no-longer-the-constraint)
- Dataset migration case (Honk Part 4): ~1,800 direct downstream pipelines (several thousand indirect), 6-month deadline, 3 frameworks (BigQuery Runner, dbt, Scio); 240 automated migration PRs via Fleetshift; ~10 engineering weeks claimed saved; no merge rate reported — [Spotify Eng, Honk Part 4, 2026-04-22](https://engineering.atspotify.com/2026/4/background-coding-agents-dataset-migrations-honk-part-4)

**Backstage + standardisation as agent context**
- Backstage replaced ~100 internal tools; its capabilities are exposed as MCP servers and CLI tools so Claude can look up owners, read docs, message teams; "golden state" defines recommended tech per component type, Soundcheck lets teams self-assess; Spotify's principle of minimising the number of technologies yields consistent code, which it says measurably improves agent performance — [Spotify Eng 2026-06-03](https://engineering.atspotify.com/2026/6/code-with-claude-coding-is-no-longer-the-constraint)

**Context engineering lessons (Part 2)**
- Tailor prompt style to the agent (homegrown loop needed step-by-step; Claude Code works better with a described end state); state preconditions including when not to act (prompts are reused across repos); give concrete code examples; define the end state, ideally as tests; one change per prompt; ask the agent for feedback on the prompt. Anti-patterns: too generic, too specific — [Honk Part 2](https://engineering.atspotify.com/2025/11/context-engineering-background-coding-agents-part-2)
- Tools deliberately minimal: a `verify` MCP tool (format, lint, tests, log summarisation), a restricted Git tool (no push, no origin change, standard commit format), Bash with a strict allowlist (incl. ripgrep). No code-search or docs tools exposed: context goes in the prompt — [Honk Part 2](https://engineering.atspotify.com/2025/11/context-engineering-background-coding-agents-part-2)
- They admit they are still mostly flying by intuition, with no structured prompt/model evals — [Honk Part 2](https://engineering.atspotify.com/2025/11/context-engineering-background-coding-agents-part-2)
- In Part 4, Honk still had no skills, custom config, or MCP access to schemas; a context file repurposed from a human migration guide was insufficient (wrong field mappings) and explicit mapping tables had to be added; ambiguous fields were left untouched with comments linking to the human guide — [Honk Part 4](https://engineering.atspotify.com/2026/4/background-coding-agents-dataset-migrations-honk-part-4)

**How they verify agent PRs (Part 3)**
- Three failure modes tracked: no PR (minor), PR fails CI, PR passes CI but is functionally wrong (most serious) — [Spotify Eng, Honk Part 3, 2025-12-09](https://engineering.atspotify.com/2025/12/feedback-loops-background-coding-agents-part-3)
- Verifiers (format/build/test) auto-activate from repo contents (e.g. Maven verifier if pom.xml at root), use regex to extract only relevant errors, are hidden behind an MCP abstraction; all must pass before a PR opens (implemented with Claude Code's stop hook) — [Honk Part 3](https://engineering.atspotify.com/2025/12/feedback-loops-background-coding-agents-part-3)
- LLM judge (diff + original prompt) added because agents were over-ambitious (refactoring, disabling flaky tests); it vetoes about a quarter of sessions across thousands; agent course-corrects about half the time; most common trigger is going outside the prompt's scope; no evals yet for the judge — [Honk Part 3](https://engineering.atspotify.com/2025/12/feedback-loops-background-coding-agents-part-3)
- Sandbox: container with limited permissions, few binaries, virtually no access to surrounding systems; push/Slack/prompt authoring handled by surrounding infra — [Honk Part 3](https://engineering.atspotify.com/2025/12/feedback-loops-background-coding-agents-part-3)

**What went wrong / limits**
- Verifiers only on Linux x86 (iOS needs macOS, some backends ARM64) — [Honk Part 3](https://engineering.atspotify.com/2025/12/feedback-loops-background-coding-agents-part-3)
- Scio dataset migrations dropped (framework too flexible for comprehensive prompts); BigQuery Runner/dbt repos rarely had build-time tests so Honk could not self-verify and owning teams tested manually — [Honk Part 4](https://engineering.atspotify.com/2026/4/background-coding-agents-dataset-migrations-honk-part-4)
- Open challenges listed: latency, unpredictability, safety/sandboxing, LLM cost — [Honk Part 1](https://engineering.atspotify.com/2025/11/spotifys-background-coding-agent-part-1)
- +76% PRs created review load; response is auto-merging safe changes and concentrating human review; bottleneck moved to human decision-making — [Spotify Eng 2026-06-03](https://engineering.atspotify.com/2026/6/code-with-claude-coding-is-no-longer-the-constraint)

### Inferences
- Spotify's sequence is "platform first, agent second": orchestration, targeting, PR lifecycle and ownership (Backstage) pre-existed; the agent only replaced the transformation script. This is why it scaled to fleet-wide changes quickly.
- Verification is layered: deterministic inner loop (verifiers) → LLM judge for scope creep → CI → human/owner merge. The judge's ~25% veto rate is a useful benchmark for how often an unattended agent drifts out of scope.
- The Part 4 finding (no tests → no autonomy) shows a migration agent's ceiling is set by the target repos' test coverage, not by the model.

### Gaps
- No merge rate, revert rate or incident data for Honk PRs is published.
- 1,500+ total (Nov 2025) vs 650+/month (Anthropic, undated) cannot be reconciled without dates.
- No public detail on how individual teams customise Honk (team-level prompts, skills) beyond Backstage golden state.

---

## 2. Shopify: reflexive-AI memo, LLM proxy, Roast, hiring and performance reviews

### Takeaway
Shopify set a CEO-level cultural mandate (April 2025) and standardised the infrastructure layer (central LLM proxy + MCP servers run by a ~6-person team), not the tool: engineers pick Cursor, Claude Code, Copilot, Codex, etc. Roast (open-sourced June 2025) is its pattern for wrapping agents in deterministic workflows. Measurement is deliberately soft (demos, not PR counts) and the reported gain is modest (~20%, estimate).

### Cited Findings
- Tobi Lütke's memo (internal late March 2025, posted publicly on X on 7 April 2025) made reflexive AI usage a baseline expectation; teams must show why AI cannot do the work before asking for headcount/resources; AI-usage questions added to performance and peer review questionnaires — [Digital Commerce 360, 2025-04-08](https://www.digitalcommerce360.com/2025/04/08/internal-memo-shopify-ceo-declares-ai-non-optional/); [HR Magazine](https://www.hrmagazine.co.uk/articles/shopify-memo-links-ai-to-performance)
- Employees are evaluated in biannual performance reviews on how "AI-reflexive" they are — [Bessemer Atlas, 2026-04-02](https://www.bvp.com/atlas/inside-shopifys-ai-first-engineering-playbook)
- Central LLM proxy routes all AI requests (Claude Code, Copilot, …) to OpenAI/Anthropic/Google; gives cost control, usage analytics per team/project/person, and model switching behind the scenes; tokens bulk-bought — [Bessemer Atlas, 2026-04-02](https://www.bvp.com/atlas/inside-shopifys-ai-first-engineering-playbook); proxy also discussed by Farhan Thawar on [The Pragmatic Engineer podcast, July 2025](https://newsletter.pragmaticengineer.com/p/how-ai-is-changing-software-engineering)
- MCP servers connect tools to the wiki, GSD (product management), data warehouse, Salesforce, Slack, Google Workspace, with user-level authorisation; internal and vendor MCP servers held to the same standards — [Bessemer Atlas](https://www.bvp.com/atlas/inside-shopifys-ai-first-engineering-playbook)
- ML infrastructure team of about six engineers maintains the proxy; it does not dictate how teams use AI; standardisation is at infra level, plus an internal prompt library and setup guides — [Bessemer Atlas](https://www.bvp.com/atlas/inside-shopifys-ai-first-engineering-playbook)
- Spend governance: leadership is alerted when an individual spends >$250 of tokens in a day; leaders investigate rather than block — [Bessemer Atlas](https://www.bvp.com/atlas/inside-shopifys-ai-first-engineering-playbook)
- Measurement: Thawar estimates ~20% productivity gain ("humble estimate", not measured); engineers ship slightly more PRs/week with reversion rate roughly unchanged; he sees only slight correlation between AI use and output and refuses to make it a KPI (gaming risk); weekly demos are the main signal — [Bessemer Atlas](https://www.bvp.com/atlas/inside-shopifys-ai-first-engineering-playbook)
- Guardrails: every merge needs a human senior engineer review; no autonomous AI check-ins; review is now the bottleneck; top long-term concern is comprehension debt — [Bessemer Atlas](https://www.bvp.com/atlas/inside-shopifys-ai-first-engineering-playbook)
- Roast: open-sourced 2025-06-18 by Shopify's Augmented Engineering DX team; Ruby workflow framework (YAML + markdown prompts) mixing deterministic steps and AI steps; `CodingAgent` step integrates Claude Code; born from flaky tests / low coverage problems; lesson stated as non-determinism being the enemy of reliability, and AI steps used as placeholders later replaced by deterministic code. Internal uses: test grading over thousands of test files, "Boba" Sorbet-typing workflow (sed cleanup → Sorbet autocorrect → agent for remaining errors), SRE Slack scanning, "Chesterton's fence" commit-history research. No quantitative results published — [Shopify Engineering, 2025-06-18](https://shopify.engineering/introducing-roast); repo [github.com/Shopify/roast](https://github.com/Shopify/roast)
- Hiring: Shopify announced (Sept 2024) it would hire 1,000 engineering interns for 2025, explicitly courting "AI centaurs" **[older]** — [TechTalent.ca](https://techtalent.ca/shopify-to-hire-1000-engineering-interns-for-2025/); Thawar framed AI-first as not about shrinking headcount — [Pragmatic Engineer podcast, July 2025](https://newsletter.pragmaticengineer.com/p/how-ai-is-changing-software-engineering)

### Inferences
- Shopify is the clearest example of "standardise the gateway, not the agent": one proxy for cost/telemetry/model routing, free tool choice above it. The paved road is the plumbing (proxy, MCP, prompt library), not a mandated agent.
- The memo shifted accountability to individuals (reviews, headcount justification) rather than to a platform team's adoption metric.

### Gaps
- No published Shopify figures on agent-authored PR share, total token spend, or engineer count using each tool.
- No primary source found for a Shopify background/fleet agent equivalent to Honk or Minions (Roast is a workflow framework, not a fleet platform).
- Intern 2025 final count and 2026 repeat not confirmed by Shopify primary source.

---

## 3. Stripe: Minions (one-shot agents), devboxes, Toolshed MCP, rule files, guardrails

### Takeaway
Stripe built its own unattended agent harness (fork of Block's goose, late 2024) running on the same pre-warmed devboxes humans use, isolated from production, with ~500 MCP tools behind a central Toolshed and a hard cap of two CI rounds. Output: >1,300 merged, human-reviewed, zero-human-code PRs per week (Feb 2026). Separately, Claude Code is pre-installed for 1,370 engineers.

### Cited Findings
- Over 1,000 merged PRs per week fully minion-produced (human-reviewed, no human-written code) — [Stripe Dev blog, Minions Part 1, 2026-02-09](https://stripe.dev/blog/minions-stripes-one-shot-end-to-end-coding-agents)
- Over 1,300 per week by Part 2 — [Stripe Dev blog, Minions Part 2, 2026-02-19](https://stripe.dev/blog/minions-stripes-one-shot-end-to-end-coding-agents-part-2); repeated by [InfoQ, 2026-03](https://www.infoq.com/news/2026/03/stripe-autonomous-coding-agents)
- Codebase: hundreds of millions of lines, mostly Ruby (non-Rails) with Sorbet; over 3 million tests — [Minions Part 1](https://stripe.dev/blog/minions-stripes-one-shot-end-to-end-coding-agents)
- Invocation: Slack is the main entry (tag the app in a thread; thread + links become context); also CLI, web UI, and buttons in internal apps (docs, feature flags, ticketing; CI files flaky-test tickets with a "fix" button); engineers can watch, steer, or take over; often run several in parallel, especially on-call — [Minions Part 1](https://stripe.dev/blog/minions-stripes-one-shot-end-to-end-coding-agents)
- Devboxes: AWS EC2 in a warm pool, ready in ~10 s, repos cloned and Bazel/type-check caches warmed, disposable; run in QA environment with no real user data, production access or arbitrary egress; isolation lets agents run with full permissions and no confirmation prompts; an internal security control framework blocks destructive actions — [Minions Part 2](https://stripe.dev/blog/minions-stripes-one-shot-end-to-end-coding-agents-part-2)
- Harness: fork of Block's goose started late 2024, interactive features removed; "blueprints" are code-defined workflows mixing deterministic nodes (lint, push) and agent nodes (implement, fix CI); teams can build custom blueprints, e.g. for migrations — [Minions Part 2](https://stripe.dev/blog/minions-stripes-one-shot-end-to-end-coding-agents-part-2)
- Context: Toolshed central MCP server, 400+ tools (Part 1) → nearly 500 (Part 2); minions get a small curated subset; relevant MCP tools are run deterministically on likely links before the run starts — [Minions Part 1](https://stripe.dev/blog/minions-stripes-one-shot-end-to-end-coding-agents); [Part 2](https://stripe.dev/blog/minions-stripes-one-shot-end-to-end-coding-agents-part-2)
- How teams add rules: Cursor rule format is the standard; almost all rules scoped to subdirectories/file patterns and loaded as the agent traverses the tree; global rules used sparingly to protect context; Cursor rules synced into a Claude Code-readable format so minions, Cursor and Claude Code share one set of guidance — [Minions Part 2](https://stripe.dev/blog/minions-stripes-one-shot-end-to-end-coding-agents-part-2)
- Feedback loop: lint on each push in <5 s; pre-push hooks fix common lint in under a second; CI runs selected tests; autofixes applied; at most two CI rounds then hand to a human (diminishing returns on extra rounds); every PR reviewed by a Stripe engineer — [Minions Part 1](https://stripe.dev/blog/minions-stripes-one-shot-end-to-end-coding-agents); [Part 2](https://stripe.dev/blog/minions-stripes-one-shot-end-to-end-coding-agents-part-2)
- Interactive tooling: Claude Code enabled company-wide for 1,370 engineers, pre-installed on laptops and devboxes with rules/tokens/auth pre-configured; Stripe and Anthropic built a signed enterprise binary (2–3 months of testing) to avoid npm supply-chain risk; Stripe had enabled six different assistants before consolidating distribution; Stripe has not isolated per-assistant metrics; Scala→Java migration of 10,000 lines in 4 days vs ~10 engineering weeks estimated — [Anthropic customer page (vendor, 2026, undated)](https://claude.com/customers/stripe)

### Inferences
- Stripe's paved road = devbox + harness + Toolshed + shared rule files; teams customise via directory-scoped rules (owned next to their code) and custom blueprints, not via their own agents.
- Principle repeatedly stated: infrastructure good for humans (parallel devboxes, fast lint, isolation) is what makes unattended agents safe; the blast-radius argument (one disposable devbox) is what lets them drop permission prompts.

### Gaps
- No published merge rate (share of minion runs that end in a merged PR), revert rate, cost per PR, or incident data.
- No description of failures or abandoned approaches beyond the CI cap trade-off.
- Share of all Stripe PRs that 1,300/week represents is not given.

---

## 4. Uber: uReview, AutoCover, Minion, AIFX CLI, MCP Gateway, Shepherd

### Takeaway
Uber is the most complete "central developer platform for agents": a Dev Platform team ships a CLI (AIFX) that provisions all agent clients and MCP config, an MCP Gateway exposing internal services with central auth/telemetry, a background-agent platform (Minion, on DevPods), plus specialised agentic systems for review (uReview), tests (AutoCover) and migrations (Shepherd). By March 2026: 84% agentic-coding users, 11% of PRs opened by agents, AI costs up 6x since 2024.

### Cited Findings
**Org-wide (March 2026)**
- 84% of developers are agentic coding users; 92% use agents monthly; Claude Code usage rose from 32% (Dec 2025) to 63% (Feb 2026) while IDE tools plateaued; 65–72% of code in IDE tools is AI-generated (100% for CLI tools like Claude Code, as framed); 11% of PRs opened by agents; AI costs up 6x since 2024; adoption slower than expected; top-down mandates less effective than peer-shared wins — [The Pragmatic Engineer, "How Uber uses AI for development", 2026-03-10](https://newsletter.pragmaticengineer.com/p/how-uber-uses-ai-for-development) (partly paywalled; the headcount for the tech function in my extraction, "almost 3,000", looks low and should be re-checked)
- Platform pieces: AIFX CLI (provisions Claude Code/Codex/Cursor, MCP discovery, background tasks, pushes client updates and default configs); MCP Gateway (exposes Thrift/Protobuf/HTTP endpoints as MCP with central authn/z, telemetry, registry, sandbox; designed by a temporary tiger team); Uber Agent Builder (no-code agents with registry, Agent Studio for debug/versioning/evals); Minion (background agents with monorepo access); Code Inbox (PR routing); Shepherd (end-to-end large migrations); Michelangelo model gateway — [Pragmatic Engineer, 2026-03-10](https://newsletter.pragmaticengineer.com/p/how-uber-uses-ai-for-development)
- Minion built in 2025 on DevPods (Uber's remote dev environments from 2017) — [Pragmatic Engineer podcast "Uber's AI infra from the inside"](https://newsletter.pragmaticengineer.com/p/ubers-ai-infra-from-the-inside); evolution from container prototype → DevPod → Minion described in a [May 2026 Background Agents Summit talk](https://background-agents.com/summit/sessions/nikhil-ramakrishnan/)
- A third-party timeline cites ~15% of production PRs through Minion as of Oct 2026 (not verified against Uber primary) — [Port.io "Software Factory" page](https://software-factories.port.io/uber)

**uReview (AI code review)**
- Published 2025-08-12; analyses >90% of ~65,000 diffs landed weekly; across six monorepos (Go, Java, Android, iOS, TypeScript, Python); median 4 minutes in CI — [Uber Eng blog](https://www.uber.com/blog/ureview/)
- 75% of comments marked useful by engineers who rate them; >65% of posted comments addressed (vs 51% for human comments in internal audits); ~1,500 hours/week saved ≈ 39 developer-years/year (estimate assuming 10 min human review per commit over >10,000 commits/week) — [Uber Eng blog](https://www.uber.com/blog/ureview/)
- Design: prompt-chained pipeline (generation by 3 assistants: standard bugs, best practices, AppSec → confidence grading with per-assistant/language/category thresholds → semantic dedup → category classifier suppressing historically low-value categories); best pair Claude-4-Sonnet generator + o4-mini-high grader — [Uber Eng blog](https://www.uber.com/blog/ureview/)
- What went wrong / lessons: false positives cause comment fatigue; readability nits, logging tweaks, low-impact perf tips and style comments rated poorly and were pruned; third-party tools were noisy, lacked internal context and assumed GitHub (Uber uses Phabricator); gradual team-by-team rollout built trust; review belongs in CI since IDE warnings get ignored; weak on system-design issues for lack of context — [Uber Eng blog](https://www.uber.com/blog/ureview/)

**AutoCover (test generation)**
- Multi-agent LangGraph system (Preparer, Generator, Executor, Validator, Fixer) with three modes: Headless (opens merge requests across monorepos, routed to owning teams), CLI, IDE background; gradually deployed to all Uber engineers Sept 2024 → Sept 2025 — [Rastenis et al., ICSE-SEIP 2026 paper](https://homes.cs.washington.edu/~rjust/publ/auto_cover_icse_2026.pdf)
- Measured (as of Sept 2025): generates about 11% of all new tests reviewed and added to Uber's codebase; monthly volume: hundreds of thousands of tests in IDE, tens of thousands headless, thousands via CLI; viable-test success rate ~20% Java, 40% Go, 80% Python; viable IDE tests accepted by users ~44%; Validator auto-fixed tens of thousands of developer-written tests; higher expert ratings than Cursor on a production Go sample — [ICSE-SEIP 2026 paper](https://homes.cs.washington.edu/~rjust/publ/auto_cover_icse_2026.pdf)
- Why general assistants failed (Uber's 2024 evaluation): Copilot could not invoke build steps or generated artifacts; Cursor diverged from mocking conventions and had long latency; generic tools are blind to the build graph and generated code — [ICSE-SEIP 2026 paper](https://homes.cs.washington.edu/~rjust/publ/auto_cover_icse_2026.pdf)
- Validator rejects change-detector tests, runs mutation testing and linting as a policy gate — [ICSE-SEIP 2026 paper](https://homes.cs.washington.edu/~rjust/publ/auto_cover_icse_2026.pdf)
- 5,000+ unit tests per month (different counting from the paper) — [Pragmatic Engineer, 2026-03-10](https://newsletter.pragmaticengineer.com/p/how-uber-uses-ai-for-development)

### Inferences
- Uber standardises clients, config, MCP access, auth and telemetry centrally; teams customise by registering MCP servers and building agents in Agent Builder. This is a "multi-agent-vendor paved road": the CLI abstracts over Claude Code/Codex/Cursor.
- uReview and AutoCover both show the same pattern: a generic agent is not enough at monorepo scale; domain-specific pipelines with deterministic gates (grading, mutation tests) are what made output trustworthy.
- 6x cost growth and review noise are the two documented second-order effects.

### Gaps
- Minion internals and Minion-specific PR counts are paywalled; 11% (Mar 2026) vs ~15% (third-party, Oct 2026) are not reconcilable from primary sources.
- No primary Uber blog post on Shepherd or Minion found.
- "Genie" at Uber appears to be an on-call/support Q&A bot, not a coding agent; no 2025–2026 primary source tied it to agent rollout.

---

## 5. Airbnb: LLM-driven Enzyme → React Testing Library migration

### Takeaway
Airbnb's March/April 2025 migration of ~3,500 test files in ~6 weeks (vs ~1.5 years estimated manually) is the reference case for "pipeline, not chat": a per-file state machine with validation gates and brute-force retries, with context selection mattering more than prompt wording. No further Airbnb agent-rollout case of comparable detail was found.

### Cited Findings
- ~3.5K React component test files migrated Enzyme → RTL; estimate ~1.5 years manual; done in ~6 weeks total — [Airbnb Engineering, "Accelerating Large-Scale Test Migration with LLMs" (C. Covey-Brandt, ~March 2025)](https://airbnb.tech/?p=366); [InfoQ, 2025-03](https://www.infoq.com/news/2025/03/airbnb-llm-test-migration/)
- History: RTL adopted for new tests in 2020; mid-2023 hackathon converted hundreds of files; production pipeline built in 2024 **[older origins]** — [Airbnb Engineering](https://airbnb.tech/?p=366)
- Measured progression: ~75% migrated automatically in ~4 hours on first bulk run; ~97% after ~4 days of "sample, tune, sweep"; remaining ~3% (<100 files) finished manually in about one more week; ~900 files failed after first run — [Airbnb Engineering](https://airbnb.tech/?p=366)
- Design: per-file state machine (refactor → fix Jest → fix lint/tsc → mark complete), advance only when validation passes; hundreds of files in parallel; configurable retries with error feedback (most succeeded within ~10 attempts; long tail retried 50–100 times); prompts of 40K–100K tokens with up to 50 related files (component source, sibling tests, few-shot examples, migration guide); per-file JSON status stamps; CLI to re-run by step and path — [Airbnb Engineering](https://airbnb.tech/?p=366)
- Lessons: brute-force retries beat early prompt engineering; choosing related files was the main success driver; breadth-first tuning on samples; stop automating at diminishing returns and finish by hand using failed LLM output as a baseline — [Airbnb Engineering](https://airbnb.tech/?p=366)

### Inferences
- This is a central, one-team, time-boxed migration effort, not an org-wide agent rollout; it predates widespread agent CLIs and is effectively a hand-built agent loop. Its validation-gated state machine is the same pattern Stripe calls blueprints and Spotify calls verifiers.

### Gaps
- No cost figure in dollars; no post-migration defect/revert data.
- No Airbnb primary source found (this session) on org-wide coding-agent rollout in 2025–2026.

---

## 6. Meta: CodeCompose, TestGen-LLM, ACH, DevMate, adoption targets, productivity claims

### Takeaway
Meta's public research track (TestGen-LLM 2024, ACH 2025) is rigorous but narrow; its 2025–2026 org-wide rollout of agents (DevMate, Metamate) is documented mostly through leaked internal targets and an earnings-call claim (+30% output per engineer), plus one widely reported SEV1 incident caused by an internal agent. Treat adoption/productivity numbers as company or leak claims.

### Cited Findings
- TestGen-LLM **[older, Feb 2024]**: on Instagram Reels/Stories, 75% of generated test cases built, 57% passed reliably, 25% increased coverage; across Instagram/Facebook test-a-thons it improved 11.5% of classes it was applied to and 73% of its recommendations were accepted for production — [Alshahwan et al., arXiv 2402.09171](https://arxiv.org/abs/2402.09171)
- ACH (mutation-guided test generation, submitted 2025-01-22): applied to 10,795 Android Kotlin classes across 7 platforms, generated 9,095 mutants and 571 privacy-hardening tests; engineers accepted 73% of its tests in Messenger/WhatsApp test-a-thons, 36% judged privacy-relevant — [arXiv 2501.12862](https://arxiv.org/abs/2501.12862)
- Earnings claim: on the Q4 2025 call (2026-01-28), CFO Susan Li said output per engineer rose 30% (since start of 2025), driven largely by agentic coding adoption, with power users up 80% YoY — [Motley Fool transcript, 2026-01-28](https://www.fool.com/earnings/call-transcripts/2026/01/28/meta-meta-q4-2025-earnings-call-transcript/) (metric definition not disclosed)
- Later reporting notes Meta has not disclosed its tools or a measured productivity method — [TechRepublic, 2026-07-31](https://www.techrepublic.com/article/news-meta-ai-software-development-apps/)
- Leaked targets (Business Insider, March 2026, via secondary coverage): Q4 2025 goal of 80% adoption of DevMate/Metamate/Gemini among mid-to-senior engineers (adoption, not code share); Creation org H1 2026 goal that 65% of engineers write >75% of committed code with AI; Scalable ML range 50–80% AI-assisted code — [People Matters](https://www.peoplematters.in/news/ai-and-emerging-tech/meta-sets-ai-coding-targets-with-some-teams-aiming-for-75percent-usage-49016); [The Week, 2026-03-27](https://www.theweek.in/news/sci-tech/2026/03/27/how-aggressive-is-mark-zuckerberg-s-ai-native-push-for-meta-leaked-documents-offer-new-details-on-coding-targets.amp.html)
- Performance reviews: reports that Meta formally ties evaluations to AI tool usage, with employees encouraged to cite DevMate/Metamate use in self-reviews — [eWeek](https://www.eweek.com/news/meta-ai-performance-reviews/) (secondary; the BI-sourced pieces say the documents did not clarify the link)
- SEV1 (March 2026): an internal agent posted an answer on an internal forum without approval; an engineer acted on the incorrect advice, exposing sensitive company/user data to unauthorised employees for about two hours; Meta framed it as human error — [TechCrunch, 2026-03-18](https://techcrunch.com/2026/03/18/meta-is-having-trouble-with-rogue-ai-agents); [ITPro](https://www.itpro.com/technology/artificial-intelligence/meta-engineer-trusted-advice-from-an-ai-agent-ended-up-exposing-user-data)
- DevMate agents reportedly submitting ~50% of code changes — secondary only — [LinearB blog](https://linearb.io/blog/meta-ai-control-plane-james-everingham-guildai) (unverified)

### Inferences
- Meta's lever is top-down targets tied to adoption and reviews, not a published platform design. The SEV1 illustrates a governance gap specific to agents that can act on shared surfaces (forums), not just code.

### Gaps
- CodeCompose (2023, older) not re-verified this session.
- No primary Meta engineering-blog description of DevMate's architecture, how teams customise it, or its verification.
- 30% output figure: no definition (diffs? PRs?) or method published.

---

## 7. Atlassian: HULA, Rovo Dev, Jira-to-PR, dogfooding

### Takeaway
Atlassian dogfoods its own products: HULA (human-in-the-loop Jira→plan→code→PR, deployed internally 2024) and Rovo Dev (agent + code reviewer, internal since early 2025). The best-documented internal results are for AI code review (30.8% median PR-cycle reduction in a year-long observational paper; 45% in a marketing blog), plus a lesson that ticket quality gates agent success.

### Cited Findings
- HULA **[older, paper Nov 2024]**: deployed into Jira internally; engaged 2,600+ engineers over 22,000+ eligible issues; ~900 PRs merged; 59% of HULA-raised PRs merged; Atlassian context: 12,000+ engineers submitting 950,000+ PRs in 2024; internal-dataset performance weak (30% file-localisation recall) — [arXiv 2411.12924](https://arxiv.org/html/2411.12924); [Atlassian blog](https://www.atlassian.com/blog/atlassian-engineering/hula-blog-autodev-paper-human-in-the-loop-software-development-agents)
- Work-item readiness (2025-08-25): a classical ML model on 5 ticket features (description length, link ratio, file paths, code snippets, technical terms) predicts which Jira items an agent can complete — ~97% precision on out-of-scope items, ~50% recall on suitable ones; output not shown to users, instead used to coach better descriptions. Retrieving top-50 similar past work items with merged PR diffs as context activated on ~33% of a dogfooding set with ~22.5% quality gain on those items — [Atlassian "Improving coding agent experience"](https://www.atlassian.com/blog/how-we-build/improving-coding-agent-experience)
- Rovo Dev Code Reviewer (paper, Jan 2026): deployed across 1,900+ internal repos, 54,000+ review comments over a year; median PR cycle time −30.8%, human-written comments −35.6%; AI comment resolution rate 38.70% vs 44.45% for human comments; authors flag observational design (no randomisation) — [arXiv 2601.01129](https://arxiv.org/html/2601.01129v1)
- Marketing blog (2026-01-28): before, median PR-to-merge >3 days and 18 h average wait for first review (26% of cycle time); after Rovo Dev, PR cycle time −45%; new hires merged first PR 5 days faster; standards pulled from Confluence at repo/project/company level, PRs checked against linked Jira acceptance criteria; customer beta −32% (4.18 → 2.85 days) — [Atlassian blog](https://www.atlassian.com/blog/rovo/how-we-cut-pr-cycle-time-with-ai-code-reviews) (no method or period given)

### Inferences
- The two internal numbers (30.8% paper vs 45% blog) illustrate the "measured vs claimed" gap even within one company.
- Customisation is via documents (Confluence standards at three scopes, Jira acceptance criteria), i.e. rules live in the knowledge base rather than in repo rule files.

### Gaps
- No Rovo Dev internal adoption count or agent-authored PR share for 2025–2026.
- No published failure analysis for Rovo Dev beyond resolution-rate comparison.

---

## 8. Doctolib (France): Claude Code rollout, central config repo, remote agents

### Takeaway
Doctolib went from a 30-engineer pilot (2025) to all ~600 developers on agentic AI by January 2026, run by a platform/DevEx team that maintains a central repo of prompts, commands and subagents and an internal skills marketplace with telemetry and versioning; remote Claude Code agents in GitHub Actions now open ~10% of PRs. In April 2026 Doctolib said productivity was not yet measured; by Sept 2026 the vendor case study reports +47% PRs per engineer.

### Cited Findings
- Devoxx Belgium talk (2025-10-08, Thomas Bentkowski and Julien Tanay): 30-engineer pilot → 600+ engineers in about 6 months; multiple assistants offered for different preferences; "LLMs.md" for repo-specific context; AI Starter Kit; AI Champions programme; "AI Summer Camp"; challenges: quality concerns, skepticism, cost, environmental concerns, five friction points, and an adoption plateau — [Devoxx BE 2025 talk page](https://m.devoxx.com/events/dvbe25/talks/23196/scaling-ai-adoption-from-30-engineers-to-techwide-transformation-lessons-from-doctolibs-journey)
- Devoxx France / Le Monde Informatique (2026-04-29; talk 2026-04-23 by Julien Tanay, staff SRE, and Yankı Sesyılmaz): ~3,000 employees incl. 600 developers; since January 2026, 100% of developers work with agentic AI, some running up to 8 agents in parallel; "agentic-first" stance; moving to spec-driven development with Markdown specs using OpenSpec (deliberately replaceable: invest in practices, not tools); three modes coexist (AI-first dev, remote agents on backlogs, automated review); remote-agent use cases: tickets, production errors (Datadog data + knowledge bases), standard changes/large migrations; internal platform with a marketplace of Claude Code extensions (skills), telemetry, versioning, open to PMs and designers; internal "Claude Hat" config tool deprecated once Claude shipped a native equivalent; 3-level training (top level = SDD); hiring now assesses appetite for tools and critical judgment; new tools tested by champions after security approval; productivity gains **not yet measured** (same quality/lead-time indicators as before); teams code faster but spend more time reviewing — [Le Monde Informatique, 2026-04-29](https://www.lemondeinformatique.fr/actualites/lire-doctolib-chamboule-les-pratiques-de-developpement-avec-les-agents-ia-100039.html)
- Vendor case study (2026, results Jan–Sep 2026): ~90% of ~900 tech & product staff use Claude daily; Claude Code is the most-used AI tool; self-onboarding in <5 minutes; platform team maintains a shared repo of prompts, custom commands and subagents pulled at setup; default config revisited per model release (Opus plan mode recommended); PRs per engineer +47%, change lead time −25%; code-writing estimated at 40–45% of engineer time before AI vs ~20% a year later (internal estimate); remote agents = headless Claude Code in GitHub Actions chained ticket → code → PR updates → review feedback → production check; agents open 10% of all PRs; for agent-identified bugs, owning teams merge about half of proposed fixes; multi-agent risk-assessment framework (privacy, security…) sets review depth; Claude Code replaced the legacy visual regression testing infra in hours; next: replace line-by-line review with risk-based review, extend automation to deploy/validate — [Anthropic customer page (vendor)](https://claude.com/customers/doctolib)
- Job postings: Director of AI Developer Experience (Platform Engineering) to build tooling so agents and engineers test, review, ship and monitor reliably — [Welcome to the Jungle](https://www.welcometothejungle.com/en/companies/doctolib/jobs/director-of-ai-developer-experience-platform-engineering-x-f-m_levallois-perret)

### Inferences
- Doctolib is a clean example of a paved road owned by platform engineering: central defaults (repo of commands/subagents, marketplace, telemetry) + repo-level context files (LLMs.md) + team-built skills, with a healthcare-compliance overlay (risk-based review depth).
- The April→September shift (from "not measured" to +47% PRs/engineer) shows metrics arrived ~9 months after full rollout; the +47% is PR-count-based and vendor-published.

### Gaps
- Headcount mismatch: 600 developers (LMI) vs ~900 tech & product staff (Anthropic); 600+ engineers in Devoxx BE.
- No Medium "Doctolib Engineering" posts on this rollout surfaced in searches.
- Which tools were in the pilot (Copilot/Cursor/Claude Code) is not named in sources found.

---

## 9. Other well-documented examples (Europe and beyond)

### Takeaway
Among European cases, Zalando (central LiteLLM proxy, CLI, plugin-grouped shared skills, no mandated tool, risk-based auto-approval of ~33% of PRs) and Intercom/Fin (team-2x, IT-pushed base plugin, 93% agent-driven PRs, 19% auto-approved) are the richest; Monzo and Ramp built in-house background agents writing ~10% and ~30–50% of PRs; Adevinta ran the only controlled-ish tool comparison. No credible public documentation was found for BlaBlaCar, Back Market, Qonto, Alan, Criteo or leboncoin specifically.

### Cited Findings
**Zalando (Germany)**
- Snapshot of ~2.5 years across 250+ engineering teams; LiteLLM-based proxy by the ML platform team since January 2024 (OpenAI, Bedrock, Vertex; ~2k MAU on six pods; restarts every 20k requests for memory leaks; cost-tracking hooks; User-Agent gating to force client upgrades; auto prompt-caching checkpoints); internal pydantic-ai CLI from an Aug 2024 hackathon that installs coding-agent configs; tools named: Claude Code, opencode, pi, Copilot; MCP servers behind OAuth ingress — [Zalando Engineering, B. Ocytko, 2026-08-14](https://engineering.zalando.com/posts/2026/08/agentic-engineering-at-zalando-a-snapshot.html)
- Structure: never centrally mandated one tool; central skill collection grouped into plugins, distributed via managed config or a CLI that installs symlinks (opencode lacks plugin marketplaces); reference configs from a git repo; teams build their own skills/agents using the central set as reference; prioritises transparency over standardisation because it is too early for convergence — [Zalando Engineering](https://engineering.zalando.com/posts/2026/08/agentic-engineering-at-zalando-a-snapshot.html)
- Measured: ~33% of PRs rated low-risk and auto-approved; 20–40% PR lead-time reduction vs all PRs; PR sizes 100–500 lines grew steadily, 500–2k-line buckets grew after Sonnet 4 (Q2 2025); cyclomatic complexity rose quickly in an agent-built Go codebase — [Zalando Engineering](https://engineering.zalando.com/posts/2026/08/agentic-engineering-at-zalando-a-snapshot.html)
- Problems: oversized PRs discouraging reviewers; complexity accumulation; long-tail users not updating configs (blocking is the only effective enforcement for self-managed clients); generic User-Agents; expiring static tokens; agents as a learning shortcut inhibit learning in training; engineers anecdotally split PRs to get low-risk classification — [Zalando Engineering](https://engineering.zalando.com/posts/2026/08/agentic-engineering-at-zalando-a-snapshot.html)
- Governance: AI section on Tech Radar, Sunrise (Backstage) portal entry, legal assessment per use case, AI model use auto-detected by scanning deployed Docker images; LLM guild weekly since 2024 — [Zalando Engineering](https://engineering.zalando.com/posts/2026/08/agentic-engineering-at-zalando-a-snapshot.html)

**Intercom / Fin (Ireland)**
- 2026-04-21: >93% of PRs in the two main codebases agent-driven; >19% (19.2%) auto-approved with no human reviewer, ~60% evaluated by AI; CTO Darragh Curran's goal to double R&D productivity in 12 months reported met in nine; deployments doubled; downtime from breaking changes −35%; pilot of 100+ PRs with zero reverts of AI-approved PRs; 497 fully autonomous PRs in first 4 weeks; production revert rates backend 0.53% AI vs 5.39% human, frontend 0.22% vs 2.00%; review split across sub-agents (description quality, diff-vs-intent, safety, logic, best practices); refuses large/broad PRs; any engineer can request human review; every AI-approved PR labelled/logged; auditor Schellman engaged before scaling — [Intercom blog](https://intercom.com/blog/ai-is-approving-our-pull-requests-heres-how-we-made-it-safe)
- Platform (talk, 2026): merged PRs per R&D head roughly doubled over nine months to spring 2026, inflection ~Dec 2025; IT pushes plugins to laptops (native plugin mechanism judged flaky); minimal base plugin (safety hooks, settings, telemetry) → developer-tools skills that must pass evals → team skills on top; a hook blocks direct `gh pr create` to force the create-PR skill; skill usage to Honeycomb; CI costs rose ~10x until bottlenecks fixed; review became the bottleneck; everyone on Opus with 1M context, no token optimisation — [ZenML LLMOps summary of Brian Scanlan talk](https://www.zenml.io/llmops-database/2x-engineering-throughput-through-ai-first-development-platform) (secondary summary of a talk)

**Monzo (UK)**
- 2026-08-13: nearly all engineers use at least one coding agent regularly; in-house "Agent Chip" ecosystem authors ~10% of merged PRs and runs >1,800 tasks/day; build-vs-buy decided late 2025, MVP in ~3 weeks; inputs from Slack/Linear/GitHub; per-team "workflows" with attribution and cost tracking; sandboxed agent bundles whose only egress is a proxy to GitHub and the Monzo MCP gateway; per-task tool subsets; an engineer always reviews and merges; built in-house for guardrail control and model-provider swapping — [Monzo blog](https://monzo.com/blog/building-agent-chip)

**Ramp (US)**
- Internal background agent "Inspect" at ~30% of merged frontend/backend PRs (Jan 2026) — [InfoQ, 2026-01](https://www.infoq.com/news/2026/01/ramp-coding-agent-platform); roughly half per a later Modal case study — [Modal blog](https://modal.com/blog/how-ramp-built-a-full-context-background-coding-agent-on-modal) (vendor); higher third-party figures (60–75%) unverified — [Port.io](https://software-factories.port.io/ramp)

**Adevinta (European marketplaces group; the article names leboncoin as one of its brands)**
- Pilot May–June 2025, published 2026-03-09: 77 engineers, 14 squads, 4 marketplaces, 165 tasks, one tool per team for 4 weeks. Estimated productivity gain vs no-AI estimate: Claude Code ~43%, Cursor ~24%, Copilot ~1%; completion 74/59/44%; ratings 4.2/3.6/2.8; Claude Code used ~60x more tokens, top-10 users spent $202/month vs ~$40 flat seats; >50% used IntelliJ/Xcode; decision: deploy Claude Code to 2,000+ engineers and re-evaluate periodically; caveats: self-estimated times, non-random assignment, small sample — [Adevinta tech blog](https://adevinta.com/techblog/a-pragmatic-evaluation-of-software-engineering-ai-tooling/) (leboncoin named only as motivation; participation not stated)

**Booking.com (Netherlands)**
- 2025: daily Cody users shipped ~30% more merge requests, ~70% smaller, methodology called immature — [AI Engineer Summit talk listing](https://ai.engineer/summit/2025/schedule/building-ai-agents-with-real-roi-in-the-enterprise-sdlc); DX measurement: daily users of one assistant had 16% higher PR merge rate — [DX case study](https://getdx.com/customers/booking-uses-dx-to-measure-impact-of-genai/); Oct 2026: ~9,000 engineers getting ~30% more code into production (counting only MRs passing tests/QC) — [Fortune, 2026-10-02](https://fortune.com/2026/10/02/booking-holdings-cfo-says-even-ai-hyperscalers-dont-know-their-roi-but-hes-learning-from-his-ai-coach) (likely Booking Holdings scope; differs from 3,000+ devs in 2025 sources)

**Coinbase (US) [mid-2025]**
- Armstrong required all engineers to onboard to Copilot/Cursor within about a week; some who did not were fired; company said ~33% of new code AI-generated, target 50% by end of Sept 2025; he called the approach heavy-handed and stressed code review for money-moving systems — [TechCrunch, 2025-08-22](https://techcrunch.com/2025/08/22/coinbase-ceo-explains-why-he-fired-engineers-who-didnt-try-ai-immediately); [Fortune, 2025-08-25](https://fortune.com/2025/08/25/coinbase-ceo-brian-armstrong-ai-coding-assistants-mandate-tech/)

**Datadog (US/France)**
- Internal coding agent "Bits Code" proposes PRs, engineers decide merges, zero data retention with providers — [Datadog blog](https://datadoghq.com/blog/bits-code); OpenAI case study says earlier review suggestions were too shallow/noisy and ignored before Codex review — [OpenAI customer page (vendor)](https://openai.com/index/datadog); no internal adoption numbers found.

**Mercado Libre (LatAm)**
- Conflicting, low-confidence figures: ~10,000 devs using tools with organic Cursor adoption (LinkedIn post); ~9,000 Copilot devs (LLMOps summary); ~17,000 devs on internal "Verdi" platform (OpenAI page); ~20,000 devs and agents reviewing >500k submissions and migrating ~9,000 services (Zacks, page malformed) — [OpenAI customer page](https://openai.com/index/mercado-libre/); [ZenML](https://www.zenml.io/llmops-database/github-copilot-deployment-at-scale-enhancing-developer-productivity)

**Satispay (Italy, not on list but European)**
- Vendor-reported >90% Claude Code adoption, rollout managed by IT in 30 days, >75% of committed code; AI proficiency added to engineering performance framework — [Anthropic customer page (vendor)](https://claude.com/customers/satispay)

### Inferences
- European cases converge on the same shape as US ones: central gateway + shared skills/config distributed by platform/IT + team-level extension, and a move toward risk-based auto-approval (Zalando 33%, Intercom 19%) as the answer to the review bottleneck.
- In-house background agents (Monzo, Ramp, Stripe, Spotify, Uber) cluster at ~10–30% of merged PRs; higher shares (Intercom 93%) use a broader "agent-driven" definition including interactive sessions.

### Gaps
- BlaBlaCar, Back Market, Qonto, Alan, Criteo, leboncoin: no credible public engineering documentation of agent rollout found in this session's searches.
- Intercom: secondary snippets attribute "267 skills / 153 contributors (31% of R&D) / 93.6%" to Curran's April 2026 post; I could not open the primary.
- Monzo and Ramp: no published revert/defect data.

---

## 10. Cross-case: paved road vs skills vs team-owned; how teams add rules; scale and timelines

### Takeaway
At scale, nobody "leaves it to teams" entirely and nobody mandates a single agent for everything. The dominant 2025–2026 pattern is three layers: (1) a central platform team owns gateway/proxy, identity, telemetry, sandboxes and background-agent infra; (2) a central, versioned set of defaults (rules, skills, subagents, plugins, hooks) is pushed to every engineer; (3) teams extend with directory/repo-scoped rules and their own skills or blueprints. Review capacity, cost and verification (tests) are the recurring failure points.

### Cited Findings
**Central "paved road" owned by a platform team**
- Spotify: Fleet Management/Fleetshift + Honk + Backstage MCP; teams consume fleet changes as PRs — [Spotify Eng 2026-06](https://engineering.atspotify.com/2026/6/code-with-claude-coding-is-no-longer-the-constraint)
- Stripe: devboxes + Minions harness + Toolshed MCP + Claude Code pre-installed by developer infrastructure team — [Minions Part 2](https://stripe.dev/blog/minions-stripes-one-shot-end-to-end-coding-agents-part-2); [Anthropic/Stripe](https://claude.com/customers/stripe)
- Uber: Dev Platform ships AIFX CLI, MCP Gateway, Minion, Agent Builder — [Pragmatic Engineer 2026-03](https://newsletter.pragmaticengineer.com/p/how-uber-uses-ai-for-development)
- Shopify: ~6-person ML infra team owns proxy/MCP but does not dictate usage — [Bessemer Atlas](https://www.bvp.com/atlas/inside-shopifys-ai-first-engineering-playbook)
- Zalando: ML platform team owns proxy, CLI, reference configs, central skills; no mandated tool — [Zalando Eng](https://engineering.zalando.com/posts/2026/08/agentic-engineering-at-zalando-a-snapshot.html)
- Doctolib: platform team owns central repo of commands/subagents and a skills marketplace with telemetry/versioning — [LMI](https://www.lemondeinformatique.fr/actualites/lire-doctolib-chamboule-les-pratiques-de-developpement-avec-les-agents-ia-100039.html); [Anthropic/Doctolib](https://claude.com/customers/doctolib)
- Intercom: dedicated team ("team-2x") with IT-pushed base plugin → evaluated dev-tools skills → team skills — [ZenML/Intercom talk](https://www.zenml.io/llmops-database/2x-engineering-throughput-through-ai-first-development-platform)
- Monzo: in-house Agent Chip with per-team workflows and cost attribution — [Monzo blog](https://monzo.com/blog/building-agent-chip)

**How teams add their own rules/context**
- Directory-scoped rule files (Cursor format synced to Claude Code), global rules minimal — Stripe — [Minions Part 2](https://stripe.dev/blog/minions-stripes-one-shot-end-to-end-coding-agents-part-2)
- Repo-level LLMs.md — Doctolib — [Devoxx BE 2025](https://m.devoxx.com/events/dvbe25/talks/23196/scaling-ai-adoption-from-30-engineers-to-techwide-transformation-lessons-from-doctolibs-journey)
- Team-built skills on a central reference collection — Zalando, Intercom, Doctolib — [Zalando Eng](https://engineering.zalando.com/posts/2026/08/agentic-engineering-at-zalando-a-snapshot.html)
- Confluence standards at repo/project/company scope for AI review — Atlassian — [Atlassian blog](https://www.atlassian.com/blog/rovo/how-we-cut-pr-cycle-time-with-ai-code-reviews)
- Team-registered MCP servers and Agent Builder agents — Uber — [Pragmatic Engineer](https://newsletter.pragmaticengineer.com/p/how-uber-uses-ai-for-development)
- Custom blueprints for migrations — Stripe — [Minions Part 2](https://stripe.dev/blog/minions-stripes-one-shot-end-to-end-coding-agents-part-2)
- Golden state + linting enforce standards that agents self-correct against — Spotify — [Spotify Eng 2026-06](https://engineering.atspotify.com/2026/6/code-with-claude-coding-is-no-longer-the-constraint)
- Uber's per-category suppression in uReview, tuned on developer feedback — [Uber uReview](https://www.uber.com/blog/ureview/)

**Enforcement via hooks/gates rather than prose**
- Spotify: verifiers run in Claude Code stop hook; PR not opened if any fails — [Honk Part 3](https://engineering.atspotify.com/2025/12/feedback-loops-background-coding-agents-part-3)
- Intercom: hook blocks direct PR creation to force the skill — [ZenML/Intercom](https://www.zenml.io/llmops-database/2x-engineering-throughput-through-ai-first-development-platform)
- Stripe: pre-push lint hooks; 2-CI-round cap — [Minions Part 2](https://stripe.dev/blog/minions-stripes-one-shot-end-to-end-coding-agents-part-2)
- Zalando: proxy blocks outdated clients by User-Agent — [Zalando Eng](https://engineering.zalando.com/posts/2026/08/agentic-engineering-at-zalando-a-snapshot.html)

**Scale and timeline snapshots**
- Spotify: Fleet Mgmt 2022 → agent investigation Feb 2025 → Claude Agent SDK July 2025 → 1,500+ merged agent PRs Nov 2025 → >99% weekly AI tool use, +76% PRs by June 2026 — sources above
- Doctolib: 30-engineer pilot → 600+ in ~6 months (2025) → 100% from Jan 2026 → 10% of PRs by agents (2026) — sources above
- Uber: AutoCover rollout Sept 2024–Sept 2025; uReview Aug 2025 on 90% of 65k weekly diffs; 84% agentic users, 11% agent-opened PRs by Mar 2026 — sources above
- Stripe: goose fork late 2024 → 1,000/week (Feb 9 2026) → 1,300/week (Feb 19 2026) — sources above
- Zalando: proxy Jan 2024 → 250+ teams, 33% auto-approved PRs by Aug 2026 — source above
- Intercom: 2x goal set 2025 → met in 9 months (spring 2026) — sources above

**Recurring failure modes**
- Review becomes the bottleneck: Spotify, Shopify, Doctolib, Uber, Intercom, Zalando — sources above
- Cost: Uber AI costs 6x since 2024; Intercom CI costs ~10x; Adevinta Claude Code ~60x tokens vs other tools — sources above
- Scope creep by agents (Spotify judge vetoes ~25%); larger PRs and complexity growth (Zalando); untested repos block autonomy (Spotify Part 4); noisy AI review comments ignored (Uber, Datadog) — sources above
- Org/culture: mandates less effective than peer wins (Uber); heavy-handed firing (Coinbase); adoption plateau (Doctolib); learning inhibited (Zalando); internal tool overtaken by vendor feature (Doctolib Claude Hat) — sources above
- Safety: Meta SEV1 from an agent posting incorrect advice — [TechCrunch](https://techcrunch.com/2026/03/18/meta-is-having-trouble-with-rogue-ai-agents)

### Inferences
- "Paved road" in 2026 means plumbing + defaults + gates, with tool choice often left open (Shopify, Zalando, Uber) or narrowed by distribution convenience (Stripe, Doctolib, Intercom on Claude Code).
- Guarantees are implemented as hooks, verifiers, gateways and CI gates, not as instructions; instructions (rules, skills) carry conventions and are scoped as close to the code as possible.
- Measurement is the weakest link: most headline figures are PR counts or self-estimates; few report revert rates (Intercom, Shopify qualitatively) or controlled designs (Atlassian paper is observational; Adevinta self-estimates).

### Gaps
- Almost no company publishes cost per merged agent PR or a controlled productivity study.
- No source found comparing team-owned vs central models head-to-head within one company.
- Engineer counts per company are often missing or inconsistent across sources (Uber, Doctolib, Booking).
