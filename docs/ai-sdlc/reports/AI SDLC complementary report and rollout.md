# Harness AI: state of the AI SDLC at large tech companies and a rollout strategy across dozens of teams

Your "convention over configuration" intuition is the right one, and it is the one the most advanced players follow: Stripe, Spotify, Uber, Doctolib and OpenAI all centralized a platform and opinionated defaults, then let each repository add its own context. Two points of your proposal must change, though. First, markdown overrides cannot carry non-negotiable rules (security, compliance). Second, automatically creating empty files runs against what the industry is learning in 2025-2026 about context bloat and documentation sprawl. The main lever is not the tool: it is the maturity of the foundations (tests, CI, small batches, internal platform) and change management by levels.

## TL;DR

- **Leaders standardize the platform, not the way of working.** Stripe (Minions, more than 1,000 merged PRs per week), Spotify (Honk, 1,000 merged PRs in 10 days versus 3 months before, QCon London 2026), Uber (Minion, uReview, MCP Gateway) and Doctolib (30-person pilot, then generalization) have all built a central "harness". It reuses the existing human infrastructure (devbox, CI, migration tools) and per-repository context files (Cursor rules, CLAUDE.md, AGENTS.md). DORA 2025 confirms it: AI is an **amplifier**, useful only where the foundations are sound.
- **Your defaults-and-overrides model is good, on three conditions.** (1) Separate a **non-overridable** layer, enforced by the platform through hooks, CI and managed policies, from an **overridable** markdown layer. (2) Replace empty-file scaffolding with **progressive discovery**: create only what is used, or generate the content from an analysis of the repository. (3) Version and instrument the framework as an internal product.
- **Roll out in waves and maturity levels.** Start with volunteer, diverse pilot teams, with champions per team, DORA and quality metrics rather than "% of generated code", and weekly feedback loops. METR (−19% measured speed versus +20% perceived) and GitClear (copy-paste overtakes moved code in 2024) are reminders that perceived productivity is not real productivity.

---

## Part 1 — State of play 2023-2026

### 1.1 By company

#### Anthropic (Claude Code)
- **Internal use.** Anthropic surveyed its teams: Product Engineering makes Claude Code its "first stop" for any programming task. New data science hires on the Infrastructure team rely on CLAUDE.md files to understand pipeline dependencies. Security Engineering feeds it stack traces and documentation during incidents. Product Design plugs Figma mockups into autonomous "write, test, iterate" loops.\[1\]\[2\]\[3\]
- **Practices recommended by the teams.** Write detailed CLAUDE.md files. Go through an MCP server rather than a raw CLI when data is sensitive, to keep control of access. Hold sharing sessions where members show each other their real usage.\[2\] According to the Claude Code team itself: use near-"vanilla" configurations, plan mode, a short CLAUDE.md enriched correction after correction, and verification loops.\[4\] Critical code is worked on synchronously; auto-accept mode is reserved for peripheral features.\[5\]
- **Standardization mechanisms.** Claude Code defines a **configuration hierarchy**. *Managed settings* (server, MDM, system file) take precedence over everything else,\[6\]\[7\] and the organization can inject a "managed" CLAUDE.md there, loaded before user and project CLAUDE.md files.\[8\]\[9\] Then come CLI arguments, then `.claude/settings.local.json`, `.claude/settings.json` and `~/.claude/settings.json`.\[6\]\[10\] Administrators can also allow only managed hooks (`allowManagedHooksOnly`), restrict plugin marketplaces (`strictKnownMarketplaces`) and force plugin installation across the whole fleet. In that case, disabling a plugin at one's own level does not stop it from loading, because managed settings take precedence over all other levels.\[8\]\[11\]
- **Key point for Harness AI.** Anthropic's documentation explicitly distinguishes **instruction context** (CLAUDE.md, rules: concatenated, non-binding) from **enforced policies** (permissions, hooks, managed settings). An instruction file does not enforce a tool permission.\[7\]\[12\]

#### Agent Skills and AGENTS.md (open standards)
- **Agent Skills.** Launched by Anthropic in October 2025, then published as an open standard on December 18, 2025 (agentskills.io). A skill is a folder containing a `SKILL.md` (frontmatter `name` and `description`) and, optionally, `scripts/`, `references/` and `assets/`. The principle of **progressive disclosure** works as follows: at startup, only the metadata is loaded (about 100 tokens per skill). The body, recommended under 5,000 tokens and 500 lines, is loaded only on activation, and the resources only if needed. The format is adopted by OpenAI Codex, GitHub Copilot, Cursor, Gemini CLI and VS Code.\[13\]\[14\]\[15\]
- **AGENTS.md.** Published by OpenAI in August 2025, the result of collective work (Codex, Amp, Google's Jules, Cursor, Factory). Donated on December 9, 2025 to the Agentic AI Foundation (Linux Foundation), co-founded by OpenAI, Anthropic and Block with support from Google, Microsoft, AWS, Bloomberg and Cloudflare. The standard's site claims more than 60,000 open source projects as users. An empirical study of 466 open source projects (arXiv 2510.21413, "Context Engineering for AI Agents in Open-Source Software") finds, however, that "there is no established structure yet for organizing content in AGENTS.md files"; according to another arXiv study, these files serve sometimes as a full governance document, sometimes as a mere pointer to another file, sometimes as a hybrid.

#### OpenAI — "Harness engineering"
- **The experiment.** On February 11, 2026, Ryan Lopopolo (OpenAI) describes an internal product built in five months with no line of code written by hand: "on the order of a million lines of code", in about a tenth of the time hand-writing would have taken, and about 1,500 PRs opened and merged by only three engineers driving Codex (3.5 PRs per engineer per day), the team later growing to seven engineers. The engineers' role becomes to "enable the agents to do useful work".
- **Lesson directly applicable to Harness AI.** The "one big AGENTS.md" approach failed: it cluttered the context, everything in it seemed important and the file went stale fast. The team replaced it with an AGENTS.md of about 100 lines serving as a **table of contents**, pointing to a structured `docs/` directory, a versioned system of record. It also enforced the architecture **mechanically** (linters, structural tests) rather than through documentation alone. What is not in the repository does not exist for the agent.\[16\]\[17\]\[18\]

#### GitHub (Copilot)
- **Instruction hierarchy.** The `.github/copilot-instructions.md` file applies to the whole repository. `.github/instructions/NAME.instructions.md` files are targeted by path through an `applyTo` frontmatter (glob), with an `excludeAgent` option to exclude the code review agent or the coding agent. On top of these come `AGENTS.md`, `CLAUDE.md` and `GEMINI.md`, plus organization instructions configured in the GitHub interface.\[19\]\[20\]\[21\]
- **Documented priority order on GitHub.com.** Personal, then repository, then organization, all sets being provided to Copilot. A notable consequence: a personal setting can take precedence over team intent.\[22\]\[23\]
- **GitHub's recommendation.** Move language- or path-specific rules into targeted files so as not to overload the global file. You can also ask the coding agent to generate the instruction file itself, then iterate.\[19\]\[24\]

#### Stripe — Minions
- **The system.** Fully unsupervised "one-shot" agents, most often launched from Slack. They produce a PR that passes CI, reviewed by a human, with no code written by a human. They account for **more than a thousand merged PRs per week**.\[25\]\[26\]\[27\]
- **The infrastructure.** They run on engineers' standard **devbox** (pre-warmed, ready in 10 seconds) and on a fork of goose (Block) adapted in late 2024.\[25\]\[28\]
- **Rule standardization.** Stripe syncs its **Cursor rules** into a format readable by Claude Code, so that its three most-used agents (Minions, Cursor, Claude Code) benefit from the same rules, which engineers add progressively in the code.\[28\]
- **Restricted toolbox.** Each agent requests only a subset of the internal tools (Toolshed): agents do better in a "smaller box" with a carefully chosen set of tools.\[28\]
- **Lesson.** The success rests on a decade of investment in tooling for humans.\[29\]

#### Spotify — Honk, Backstage, Fleet Management
- **The agent.** Honk is a background coding agent based on Claude (Agent SDK), run in Kubernetes pods. It first served fleet migrations, on the "long tail" of about 30% of cases that deterministic scripts could not handle, then became accessible from Slack.\[30\]\[31\]\[32\]
- **Volume.** At QCon London 2026, Jo Kelly-Fenton and Aleksandar Mitic sum it up: "we had 1,000 merged PRs in 3 months. Today, we do this in 10 days".
- **Key architecture choices.** The agent runtime is separate from the verification runtime (trusted CI), and diffs are evaluated by an LLM in addition to lint and formatting.\[32\]\[33\]
- **Governance.** Advisory boards of seniors define "golden" technologies; Honk is then used to push migrations to 100%.\[30\]
- **The datasets case.** A dataset migration touched about 1,800 downstream pipelines and saved about 10 engineer-weeks. During these migrations, Honk deliberately had **no skills and no customizable configuration**, a deliberate guardrail.\[34\]\[35\]
- **Spotify's conclusion.** Success depends on the **consolidation and standardization** of the technical landscape.\[35\]

#### Uber
- **Layered platform** (presented at the Pragmatic Summit by Ty Smith, Principal Engineer, and Anshu Chada, Director of Engineering, a session summarized by Gergely Orosz in The Pragmatic Engineer on March 10, 2026, and also at LangChain):
  - **MCP Gateway**: centralized access to internal APIs, with authentication, logs and telemetry;\[36\]
  - **Agent Builder** (no-code) and **AIFX CLI** (agent provisioning);\[36\]
  - **Minion**: background agents with access to the monorepo and "optimized defaults";\[37\]
  - **uReview**: AI code review that filters by confidence level, after finding that external tools produced too many low-value comments;\[38\]
  - **Code Inbox**: PR routing;\[36\]
  - **Autocover**: test generation, about 5,000 per month.\[38\]
- **Figures reported in early 2026.** According to The Pragmatic Engineer (figures corrected on March 11, 2026), "84% of devs at Uber are agentic coding users" and "65-72% of code is AI-generated inside IDE-based tools"; other summaries cite 11% of PRs opened by agents and AI costs multiplied by 6 since 2024.
- **Uber's finding.** According to The Pragmatic Engineer, "AI adoption is slower than expected" and "top-down mandates are less efficient than engineers sharing their wins with peers".

#### Doctolib (France)
- **Trajectory.** A Claude Code pilot with 30 engineers, then rollout to the whole development team, with self-onboarding in under five minutes (VS Code, JetBrains, CLI).\[39\]
- **Central base.** The platform team created a **centralized repository of prompts, commands and subagents** that every developer pulls at installation. Claude Code runs in headless mode in CI for maintenance, documentation updated on every code change, and automatic PR review.\[39\]
- **Adoption program** (Devoxx Belgium 2025). **AI Champions** program, **AI Summer Camp**, "AI Starter Kit", **LLMs.md** approach for per-repository context. The talk mentions an **adoption plateau** and five friction points.\[40\]
- **Adoption figures.** The French press (Le Monde Informatique) reports that the 600 engineers have been working with agents since January 2026.\[41\] A recent version of the Anthropic case study mentions about 90% of the roughly 900 tech and product people using Claude every day, 47% more PRs per engineer, a change lead time reduced by 25% and 10% of PRs opened by remote agents.\[39\] These figures come from the vendor and do not appear in the version of the page we were able to consult.
- **Vision.** Mike Aidane (VP Platform Engineering): "a software factory where engineers build and maintain the agentic loops".\[39\]

#### Shopify
- **The memo.** In April 2025, CEO Tobi Lütke publishes: "Reflexive AI usage is now a baseline expectation at Shopify."\[42\]\[43\]
- **What it mandates.** AI is mandatory in the prototyping phase (GSD), questions on AI usage enter performance and peer reviews, and teams must demonstrate why AI is not enough before asking for headcount.\[44\]\[45\]
- **Limits.** This is the textbook example of a top-down cultural adoption. Its limits are documented: in a small group, evaluating individual usage produces "theater". In Germany, systematic monitoring of usage falls under works council co-determination (§ 87 BetrVG), which is relevant for a European context.\[46\]

#### Amazon (Q Developer, Java transformations)
- **Announced results** (Andy Jassy, August 2024): upgrading an application to Java 17 goes from about 50 developer-days to a few hours. More than 50% of production Java systems were migrated in under six months, about 30,000 applications. Amazon estimates the savings at **4,500 developer-years** and $260M per year. 79% of the automatically generated code reviews were shipped without changes.\[47\]\[48\]\[49\]
- **Caution.** These are internal estimates from a vendor that sells the tool. The time saved was computed from the number of migrated dependencies, and the $260M comes from Java 17 performance gains, not from the agent itself.\[50\]
- **Lesson.** **Targeted, verifiable** transformations (build and tests) are the best first use case.

#### Google
- **Share of generated code.** Sundar Pichai announces that more than 25% of new code is AI-generated in October 2024, 50% in fall 2025, then **75% "AI-generated and approved by engineers"** in April 2026 (Cloud Next).\[51\]\[52\]\[53\]
- **Productivity.** Pichai considers **engineering velocity** the most important metric, and put it at **+10%**, measured in hours of capacity freed per week.\[54\]
- **What the gap reveals.** 75% AI code versus +10% velocity perfectly illustrates why "% of generated code" is a poor steering metric. Google has published no rejection rate.\[52\]\[55\]
- **Research.** Google also runs DORA (see 1.2).

#### Airbnb
- **The migration.** About 3,500 test files moved from Enzyme to React Testing Library in **6 weeks**, versus 1.5 years estimated by hand.\[56\]
- **How.** A staged pipeline (state machine), retry loops and context-rich prompts. Result: 75% success on the first 4-hour pass, 97% after 4 days of tuning, and 3% finished by hand.\[56\]\[57\]
- **Lesson.** Same model as Amazon and Spotify: massive migrations, automatic validation, a human at the end of the chain.

#### Atlassian (Rovo Dev, Jira agents)
- **From ticket to PR.** Rovo Dev starts from the **Jira ticket**: it creates a code plan from the ticket, generates the code and opens a Bitbucket PR. It checks that PRs meet the **acceptance criteria** of the linked Jira ticket, and diagnoses failing builds. "Agentic Pipelines" (automatic fixes in CI) are in beta.\[58\]\[59\]\[60\]\[61\]
- **Internal results, published by Atlassian, which do not agree with each other:**
  - January 2026: −45% PR cycle time, with no published methodology;\[62\]
  - April 2026: **−30.8% median cycle time and −35.6% human review comments** across more than 1,900 repositories over a year, a study accepted at ICSE 2026, the most rigorous source;\[63\]
  - November 2026: −31% median cycle time, and 39% of Code Reviewer comments followed by a code change in the next commit.\[64\]
- **Side effect.** Atlassian also notes that teams heavily reliant on AI wait more than twice as long for a human review (71 min versus 32). **Human review becomes the bottleneck.**\[64\]
- **Relevance.** This is the closest model to your "/dev on a Jira ticket".

#### Not covered or insufficiently sourced in this research
Microsoft (outside GitHub), Meta, Netflix, Zalando, BlaBlaCar, Criteo, Datadog, ManoMano and Malt could not be documented from primary sources within the research budget. The figures circulating about these companies (for example percentages of generated code announced by executives) are not repeated here for lack of verification. This is a watch item to complete, ideally through Devoxx France talks and these companies' engineering blogs.

### 1.2 Conceptual frameworks and impact studies

**DORA 2025 (Google).** According to Google Research, the "State of AI-assisted Software Development" report draws on more than 100 hours of qualitative data and on the answers of nearly 5,000 tech professionals. 90% of them use AI, but AI is an **amplifier**: it magnifies the strengths of high-performing organizations and the dysfunctions of the others. The **DORA AI Capabilities Model** identifies 7 capabilities:\[65\]
1. a clear and communicated stance on AI;
2. healthy data ecosystems;
3. internal data accessible to AI;
4. strong version control;
5. working in small batches;
6. a user focus;
7. quality internal platforms ("paved roads").

The report also offers **7 team profiles**, from "Foundational challenges" to "Harmonious high achievers",\[66\] which provides a natural basis for addressing teams by maturity level.

**Harness and context engineering.** The harness is everything around the model: instructions, tools, mechanically enforced rules (linters, hooks, CI) and cleanup loops.\[16\] The converging lesson from OpenAI, Stripe and Anthropic: **short** entry files that point to the documentation, and context loaded on demand.

**Spec-driven development.** GitHub Spec Kit (September 2025, with a "constitution" of immutable principles), AWS's Kiro (requirements, design, tasks), Tessl (the spec as source) and BMAD. The Thoughtworks Radar placed it in **Assess** in November 2025, warning that "handcrafting detailed rules for AI ultimately doesn't scale".\[67\]\[68\]\[69\] In her evaluation, Birgitta Böckeler saw Kiro turn a small bug into 4 user stories and 16 acceptance criteria.\[70\] In November 2026, **Radar vol. 35** places "AI-driven documentation sprawl" in **Caution**: masses of markdown generated by Spec-kit or BMAD, verbose, unmaintained and contradictory, which create an "illusion of quality". Its other cited entries include *progressive context disclosure*, *agent instruction bloat*, *risk-tiered human oversight*, *human-in-the-loop theater* and *agent sandboxing*.\[71\]\[72\]

**Studies on real impact.**
- **METR (July 2025)**: randomized trial, 16 experienced open source developers, 246 tasks. With AI, they were **19% slower**, while they expected +24% and afterwards believed they had been 20% faster. The setting is specific (mature, familiar repositories, early-2025 tools).\[73\]\[74\]\[75\]
- **GitClear (February 2025, 211M lines, 2020-2024)**: "moved" code (refactoring) falls from 24.1% to 9.5%, while copy-paste rises from 8.3% to 12.3%. 2024 is the first year in which copy-paste exceeds moved code.\[76\] This is a correlation with AI adoption, not a line-by-line attribution, and the study comes from a vendor of quality tools.

---

## Part 2 — Critical analysis of the "convention over configuration" proposal

### 2.1 What the proposal gets right (and the field confirms)
1. **Opinionated defaults and a single entry point (`/dev` on a ticket).** This is exactly the pattern of Stripe (Slack, then Minion, then PR), Uber (Minion and its "optimized defaults"), Doctolib (central pack installed from day one) and Atlassian (Jira ticket, plan, PR). Low initial friction is the first adoption factor: Doctolib's self-onboarding in under five minutes is the proof.
2. **Per-repository markdown overrides.** This is the de facto standard: CLAUDE.md, AGENTS.md, `.github/instructions/*.instructions.md` with `applyTo`, synced Cursor rules at Stripe, LLMs.md at Doctolib.
3. **Starting from the Jira ticket.** This aligns AI with the value stream, what DORA calls user focus and value stream management, rather than with the IDE alone.

### 2.2 Risks and blind spots

| Risk | Why it is real | Source / signal |
|---|---|---|
| **Overridable non-negotiable rules** | A markdown file is *context*, not a *policy*. A team can weaken a security rule through mere wording, and the model can ignore it. | Claude Code documentation separates instructions from enforced policies (managed settings, hooks); GitHub puts personal before repository, then organization.\[7\] |
| **Automatically generated empty files** | Cognitive noise, a false compliance signal ("the file exists so it's handled"), and they open the door to verbose AI filling. | Radar vol. 35: "AI-driven documentation sprawl" in Caution; *agent instruction bloat*. |
| **Context bloat** | Central defaults, overrides, CLAUDE.md and AGENTS.md are concatenated: the agent misses constraints or optimizes the wrong one. | Failure of the "one big AGENTS.md" at OpenAI; progressive disclosure in Agent Skills. |
| **Unresolved central / local conflicts** | Concatenation is not merging: two contradictory rules coexist and the model decides at random. | Claude Code: CLAUDE.md files are concatenated, not strictly overridden.\[12\] |
| **Drift and staleness** | Overrides age without tests, and the central framework evolves beneath them. | OpenAI: "rapid rot" of the big file. |
| **Framework versioning** | Dozens of teams on different versions with no update channel and no guaranteed compatibility. | Practice of managed plugin marketplaces (pinned versions, forced plugins).\[11\] |
| **No observability** | Without telemetry, no way to know which skills are used, fail, cost. | Uber (MCP Gateway: logs and telemetry, costs ×6), Doctolib (cost monitoring, plateau). |
| **Human review bottleneck** | More generated PRs, but the same reviewers. | Atlassian: 71 min versus 32 of waiting; Uber had to create Code Inbox and uReview. |
| **Weak foundations** | On a team without reliable tests or CI, `/dev` quickly produces fragile code. | DORA ("amplifier"), GitClear, Spotify (standardization as a prerequisite). |
| **"Human-in-the-loop theater"** | Purely formal human approvals on large PRs. | Radar vol. 35; Böckeler ("false sense of control"). |

### 2.3 Recommended improvements (without touching existing artifacts)

1. **Three explicit layers, each with its enforcement mechanism.**
   - **Layer 0 — Non-negotiable** (security, secrets, compliance, licenses, health or personal data). It is enforced **outside the prompt**: managed settings, `allowManagedHooksOnly`, allowed marketplaces, CI checks (SAST, secret detection, branch policy), MCP permissions through a gateway. It is never overridable by a markdown file.\[6\]\[7\]
   - **Layer 1 — Organization defaults** (`/dev` workflow, definition of done, PR style, default testing strategy). Delivered as a versioned plugin or marketplace.\[11\]\[77\]
   - **Layer 2 — Team extensions** (QA, review, domain rules). This is where your overrides live.
2. **Prefer extension to override.** Team files *add* criteria (for example "in addition, check X") instead of *replacing* the defaults. When a replacement is truly needed, it must be declared explicitly (frontmatter such as `overrides: code-review.tests-min-coverage` and a justification) so that it is visible and auditable. This is the equivalent of GitHub's `applyTo` and `excludeAgent`.
3. **Replace empty scaffolding with progressive discovery.**
   - On first run, **analyze** the repository (languages, build, tests, CI) and propose a **single** short entry file (AGENTS.md as a table of contents), **pre-filled from detected facts** (build and test commands), for the team to validate in a PR.
   - Create `qa.md` or `code-review.md` only **when the team needs it**: for example, when AI review receives three similar corrections, the framework offers to add the rule (Anthropic's model of the "CLAUDE.md that grows correction after correction").
   - If you insist on making the structure visible, document it (`/harness doctor` lists the available extension points) rather than materializing it as empty files.
4. **Converge on open standards.** AGENTS.md as a portable entry point (read by Copilot, Codex, Cursor; Claude Code can load it) and Agent Skills for skills.\[9\] This avoids lock-in and prepares for multi-tool coexistence, like the syncing of Cursor rules to Claude Code at Stripe.
5. **Lint the overrides.** A CI check verifies maximum size, absence of contradiction with layer 0, dead references and freshness (date of last review). Agentic documentation must go through quality gates like code, which is precisely what Radar vol. 35 faults teams for not doing.\[71\]
6. **Version the framework as a product.** SemVer, changelog, stable and beta channels, a version pinned per repository with automatic updates by PR, and a suite of non-regression **evals** of the skills on reference repositories before each release.
7. **Instrument from day one.** Per-skill telemetry (invocations, success rate, PRs merged or abandoned, token costs) and collection of existing overrides. The most frequent overrides point to central defaults to fix.

---

## Part 3 — Rollout proposal

### 3.1 Guiding principles
- **The platform owns the harness, the teams own their context.** This is the Team Topologies model: an "enabling" platform team and stream-aligned teams that consume it as self-service.
- **Paved paths, not mandatory paths** (except layer 0). `/dev` must be the easiest path, not the only one.
- **Measure outcomes, not usage.** No "% of generated code" as a target; do not evaluate people on their individual usage, because of the risks of theater and the labor law issues in Europe.
- **Invest in the foundations in parallel.** Tests, fast and reliable CI, small batches: these are the DORA capabilities.

### 3.2 Team maturity levels ("Harness levels")

| Level | Name | What the team does | Exit criterion |
|---|---|---|---|
| **N0** | Foundations | Green and reliable CI, tests runnable by command, minimal AGENTS.md validated | Build and tests runnable by the agent without human help |
| **N1** | Assisted | Interactive use (plan mode, code explanation, tests), default skills without overrides | ≥ 70% of devs active each week; feedback collected |
| **N2** | Workflow | End-to-end `/dev` on well-scoped tickets; AI review in addition to human review; first team extensions | Stable rate of merged agent PRs; no degradation of the change failure rate |
| **N3** | Delegated | Background agents on toil (migrations, version upgrades, missing tests, debt) like Honk or Minions; lightweight specs upstream | Growing share of agent PRs on toil, with stable quality |
| **N4** | Loops | The team maintains its own loops (team skills shared in the catalog, contributions to the framework) | Contributions accepted into the central framework |

Not all teams advance at the same pace. This is not a failure: DORA shows very different team profiles. For a team in "foundational challenges", the priority is N0, not `/dev`.

### 3.3 Roadmap

**Phase 0 — Scoping (4 to 6 weeks)**
- Publish a **clear AI stance** (first DORA capability): what is expected, allowed, forbidden (data, secrets, customer code) and how usage will be measured. It must be co-built with security, legal, the DPO and staff representatives if needed.
- Define **layer 0** and its enforcement mechanisms (managed settings, hooks, CI, MCP gateway).
- Set up telemetry and a **DORA baseline measurement**: lead time, deployment frequency, change failure rate, time to restore, PR cycle time and review wait time.

**Phase 1 — Pilots (8 to 12 weeks, 3 to 5 teams)**
- Choose **volunteer and diverse** teams (stacks, maturities, a legacy product), on the model of Doctolib's 30-person pilot "from all backgrounds".\[78\]
- Support each team with a platform pair. Hold a weekly feedback check-in and an AI retrospective each sprint.
- Start with **strong verification** cases: migrations, version upgrades (the Amazon Java and Airbnb model), test generation, documentation.
- Deliverable: list of central defaults fixed, catalog of truly useful extensions, documented frictions.

**Phase 2 — Waves (quarter by quarter, 5 to 10 teams per wave)**
- Self-service onboarding (target under 5 minutes), starter kit and concrete use cases per role.
- **Champion network**: one per team, allocated time (10 to 20%), a monthly community of practice with "show me your real usage" demos (a practice recommended by Anthropic's teams), visible recognition.
- Role-based training (see 3.5) and "AI Summer Camp" or hackathons (Doctolib; the creation of Honk via Slack was born at a Spotify Hack Week).\[30\]
- Anticipate the **adoption plateau** (seen at Doctolib and Uber): relaunch with new use cases rather than with injunctions.

**Phase 3 — Industrialization**
- Background agents on cross-cutting toil, driven by the platform (Fleetshift and Honk model).
- Managing the **review bottleneck**: AI review filtered by confidence level (uReview model), routing, human oversight proportional to risk (*risk-tiered human oversight*).
- Internal skill catalog open to team contributions, with review by the platform.

### 3.4 Governance
- **Harness AI platform team**: owner of layer 0 and layer 1, releases, evals, telemetry and the catalog. It treats the framework as an **internal product**: product manager, roadmap, developer NPS. Doctolib gives this role to a Platform Product Manager paired with a Staff SRE.\[40\]
- **AI Guild or Advisory board** (Spotify model): seniors from each discipline (Dev, QA, Security, SRE, PO) who decide on adding a central rule and validate the promotion of local extensions into defaults.
- **Promotion rule**: an extension present in at least 3 teams becomes a candidate for layer 1. An override that contradicts a central rule opens a discussion, not a silent exception.
- **Exception process** for layer 0: tracked request, limited duration, approval by security.

### 3.5 How roles evolve
- **PO**: writes "agent-ready" tickets (testable acceptance criteria, context, limits). Rovo Dev checks PRs precisely against these criteria. **Lightweight** specs, proportional to the size of the task, to avoid the Kiro trap of "16 criteria for one bug".
- **Developer**: moves from author to orchestrator and reviewer. Masters plan mode, decomposition, verification and curation of their repository's context.
- **QA**: designs the test strategies and oracles (mutation testing, contracts) that serve as the agents' verification loop, and writes the team's `qa` extensions.
- **Security**: owns layer 0, the hooks, agent sandboxing and the analysis of tool flows (MCP).
- **SRE**: integrates agents into incident diagnosis (stack traces, runbooks, as at Anthropic Security Engineering) and defines the limits of agent actions in production.

### 3.6 Measurement dashboard

| Category | Indicators | Use |
|---|---|---|
| Adoption | Weekly active users, teams per level N0 to N4, skills invoked | Steering the rollout, not individual evaluation |
| Flow (DORA) | Lead time, deployment frequency, PR cycle time, wait for first review | Main outcome |
| Quality | Change failure rate, time to restore, revert rate of agent PRs, duplication and churn (GitClear-style) | Guardrail: any increase blocks the next wave |
| Agent efficiency | Rate of agent PRs merged without rework, abandonments, token costs per merged PR | Improving the framework |
| Experience | Quarterly survey (perception, cognitive load, trust), verbatims | Detecting friction; never rely on it alone (METR bias) |

### 3.7 Managing change and friction
- **Name the fears**: jobs, loss of skills, surveillance. The Shopify memo was criticized on this point.
- **No individual usage mandate.** Set team expectations on outcomes instead.
- **Highly responsive feedback channel**: a fix or an answer within a week during the pilots.
- **Show failures** as much as successes: Spotify publishes its limits, Doctolib its plateau and its costs.
- **Transparent budget and costs** per team (Uber: ×6; the Doctolib experience: about $1,000 for 3 weeks of a trio), with model rightsizing.\[79\]

---

## Caveats
- **Source bias.** A large share of the adoption figures (Doctolib, Spotify, Amazon, Atlassian) comes from the companies themselves or their vendors (Anthropic and AWS case studies). Uber's figures come mostly from secondary summaries of conference talks. "Generated code" percentages are neither defined consistently nor audited.
- **Contradictory data**: Atlassian publishes −45%, then −30.8% and −31% PR cycle time, and only the second measurement is methodologically documented. For Doctolib, the press speaks of 600 engineers and the latest case study of about 900 tech and product people, two different scopes.
- **Impact studies**: METR covers early-2025 tools and a very specific profile. GitClear establishes a correlation, not causation. Neither should be generalized, but both justify measuring rather than believing.
- **Incomplete coverage**: Microsoft (outside GitHub), Meta, Netflix, Zalando and French players other than Doctolib were not documented from primary sources here.
- **Fast changes**: configuration mechanisms (managed settings, plugins, Agent Skills) change every month. The technical details cited are valid as of November 2026 and must be rechecked at implementation time.

## Sources

1. [How Anthropic Teams Use Claude Code (2027 Guide)](https://blog.buildbetter.ai/how-anthropic-teams-use-claude-code/)
2. [How Anthropic's Own Teams Use Claude Code](https://moeed.app/posts/how-anthropic-teams-use-claude-code/)
3. [Case Study](https://www.anthropic.com/news/how-anthropic-teams-use-claude-code)
4. [How the Claude Code Team Actually Uses Claude Code - The doctrine the people who built Claude Code at Anthropic teach every new hire — Vibe Coder Blog](https://blog.vibecoder.me/how-claude-code-team-uses-claude-code)
5. [How Anthropic engineering teams use Claude Code every day](https://codingscape.com/blog/how-anthropic-engineering-teams-use-claude-code-every-day)
6. [Enterprise Claude Code with Managed Settings](https://systemprompt.io/guides/enterprise-claude-code-managed-settings)
7. [Configuration Precedence and Hierarchy](https://deepwiki.com/FlorianBruniaux/claude-code-ultimate-guide/4.3-configuration-precedence-and-hierarchy)
8. [All settings - Claude Code Docs](https://code.claude.com/docs/en/settings-reference)
9. [How Claude remembers your project - Claude Code Docs](https://code.claude.com/docs/en/memory)
10. [Claude Code Extension Layer Decision Guide - Choosing Among Skills, Subagents, Hooks, and Plugins](https://hidekazu-konishi.com/entry/claude_code_extension_layers_decision_guide.html)
11. [Manage Claude Code plugins for your organization - Claude Code Docs](https://code.claude.com/docs/en/plugins/org)
12. [claude-howto/02-memory/README.md at main · luongnv89/claude-howto · GitHub](https://github.com/luongnv89/claude-howto/blob/main/02-memory/README.md)
13. [What Are Agent Skills and How To Use Them](https://strapi.io/blog/what-are-agent-skills-and-how-to-use-them)
14. [The Agent Skills Standard: One SKILL.md, Every Tool — AgentsCamp](https://agentscamp.com/guides/skills/agent-skills-open-standard)
15. [Specification - Agent Skills](https://agentskills.io/specification)
16. [Harness Engineering Guide: How to Build an AI Agent Harness](https://www.nxcode.io/resources/news/harness-engineering-complete-guide-ai-agent-codex-2026)
17. [OpenAI's Agent-First Codebase Learnings](https://alexlavaee.me/blog/openai-agent-first-codebase-learnings/)
18. [Harness Engineering: Leveraging Codex in an Agent-First World](https://2ooks.github.io/knowledge-base/summaries/openai-harness-engineering.html)
19. [Unlocking the full power of Copilot code review: Master your instructions files - The GitHub Blog](https://github.blog/ai-and-ml/github-copilot/unlocking-the-full-power-of-copilot-code-review-master-your-instructions-files/)
20. [Adding repository custom instructions for GitHub Copilot - GitHub Docs](https://docs.github.com/copilot/customizing-copilot/adding-custom-instructions-for-github-copilot)
21. [GitHub Copilot Instructions: Setup Guide](https://codetocloud.io/blog/github-copilot-instructions/)
22. [copilot-instructions.md as a Repo-Level Instruction Convention — AgentPatterns.ai](https://agentpatterns.ai/tools/copilot/copilot-instructions-md-convention/)
23. [Copilot Custom Instructions: 8 Copy-Paste Templates](https://prompt-architects.com/blog/339-github-copilot-custom-instructions-templates-that-work)
24. [Path-specific Copilot custom instructions: a guide - DEV Community](https://dev.to/sascha-ms/path-specific-copilot-custom-instructions-a-guide-54lg)
25. [Minions: Stripe’s one-shot, end-to-end coding agents](https://stripe.dev/blog/minions-stripes-one-shot-end-to-end-coding-agents)
26. [Minions one-shot coding agents - Jacob Bennett](https://jacob.blog/links/minions-one-shot-coding-agents/)
27. [Minions: Stripe’s One-Shot, End-to-End Coding Agents (Stripe Engineering Blog)](https://antolinez.ch/2026/Apr/12/stripe-minions-coding-agents/)
28. [Minions: Stripe’s one-shot, end-to-end coding agents—Part 2](https://stripe.dev/blog/minions-stripes-one-shot-end-to-end-coding-agents-part-2)
29. [Stripe Minions Explained: Autonomous Coding Agents Ship 1300+ PRs/Week](https://www.paperclipped.de/en/blog/stripe-minions-autonomous-coding-agents/)
30. [Spotify: Fleet-Wide Autonomous Code Migrations with AI Coding Agents - ZenML LLMOps Database](https://www.zenml.io/llmops-database/fleet-wide-autonomous-code-migrations-with-ai-coding-agents)
31. [How Spotify Uses AI Agents to Rewrite Its Entire Codebase](https://grindengineer.substack.com/p/how-spotify-uses-ai-agents-to-rewrite-its-entire-codebase)
32. [QCon London 2026: Rewriting All of Spotify's Code Base, All the Time - InfoQ](https://www.infoq.com/news/2026/03/spotify-honk-rewrite/)
33. [Honk at Spotify · Internal Agents Map](https://internal-agents.com/agents/spotify-honk-xirp)
34. [Spotify: Background Coding Agents for Large-Scale Dataset Migrations - ZenML LLMOps Database](https://www.zenml.io/llmops-database/background-coding-agents-for-large-scale-dataset-migrations)
35. [Background Coding Agents: Supercharging Downstream Consumer Dataset Migrations (Honk, Part 4)](https://engineering.atspotify.com/2026/4/background-coding-agents-dataset-migrations-honk-part-4)
36. [Inside Uber's AI Dev Stack: 92% of Engineers Use Agents Monthly](https://aiproductivity.ai/news/uber-ai-development-inside-look/)
37. [How Uber uses AI for development: inside look - Mobile & Accessories](https://abc.microfintool.com/how-uber-uses-ai-for-development-inside-look/)
38. [How Uber is building AI agents for its developers - Staniscia.net](https://www.staniscia.net/2921-how-uber-is-building-ai-agents-for-its-developers/)
39. [Doctolib Claude Code case study](https://claude.com/customers/doctolib)
40. [Scaling AI Adoption: From 30 Engineers to Tech-Wide Transformation - Lessons from Doctolib's Journey - Devoxx Belgium 2025](https://m.devoxx.com/events/dvbe25/talks/23196/scaling-ai-adoption-from-30-engineers-to-techwide-transformation-lessons-from-doctolibs-journey)
41. [How Doctolib is revolutionizing development methods thanks to AI agents - Le Monde Informatique](https://www.javascrypte.com/en/how-doctolib-is-revolutionizing-development-methods-thanks-to-ai-agents-le-monde-informatique/)
42. [AI is baseline: what Shopify's memo means for your hiring process. · Metaview Blog](https://www.metaview.ai/resources/blog/ai-baseline-shopify-memo-hiring-process)
43. [How Shopify's CEO Delivered the AI Mandate to His Workers - Ragan Consulting](https://raganconsulting.com/analyzing-tobias-lutkes-artificial-intelligence-memo-ai/)
44. [Tobi's Shopify Memo - New Internet, by Jeff Morris Jr.](https://www.newinternet.tech/p/tobis-shopify-memo)
45. [Tobi Lutke's Public AI Memo: How a CEO Made AI Use a Hiring Bar](https://www.thefoundersreport.com/tobi-lutke-shopify-ai-mandate-public-memo)
46. [Tobi Lütke's AI Memo: The Part About Headcount - Sondero](https://www.sondero.ai/blog/authority-luetke-reflexive-ai)
47. [Amazon CEO: AI-Assisted Code Transformation Saved Us 4,500 Years of Developer Work - Slashdot](https://developers.slashdot.org/story/24/08/25/0049230/amazon-ceo-ai-assisted-code-transformation-saved-us-4500-years-of-developer-work)
48. [A quote from Andy Jassy - Amazon CEO](https://simonwillison.net/2024/Aug/24/andy-jassy-amazon-ceo/)
49. [How Amazon’s generative AI tool for developers is saving 4,500 years of work, \$260 million annually - Digiday](https://digiday.com/media/how-amazons-genai-tool-for-developers-is-saving-4500-years-of-work-260-million-annually/)
50. [Amazon upgraded 30,000 internal apps to Java 17 with Amazon Q Developer](https://agentsinthewild.co/use-cases/amazon-q-java-upgrades)
51. [Google CEO says 75% of the company’s code is AI-generated - Fast Company](https://www.fastcompany.com/91531519/google-ceo-says-75-of-the-companys-code-is-ai-generated)
52. [Google's 75% AI Code: What Pichai Didn't Say at Cloud Next](https://newsanalysis.net/pichai-google-75-percent-ai-code-claim/)
53. [googles code ai sundar pichai](https://fortune.com/2024/10/30/googles-code-ai-sundar-pichai)
54. [sundar pichai says ai making 141602216](https://www.aol.com/sundar-pichai-says-ai-making-141602216.html)
55. [75% Of Code At Google Is Now Generated By AI: CEO Sundar Pichai](https://officechai.com/ai/75-of-code-at-google-is-now-generated-by-ai-ceo-sundar-pichai/)
56. [AirBnB: Large-Scale Test Framework Migration Using LLMs - ZenML LLMOps Database](https://www.zenml.io/llmops-database/large-scale-test-framework-migration-using-llms)
57. [How Airbnb Leveraged Large Language Models for a Groundbreaking Code Migration - Christopher Zerafa, PhD](https://zerafachris.github.io/bio/ai-airbnb-code-migration/)
58. [Atlassian Rovo & Rovo Dev: AI Agents in Jira for Software Teams](https://lupusconsulting.com/blog/atlassian-rovo-and-rovo-dev-the-rise-of-ai-agents-for-software-teams)
59. [Work with Rovo Dev in Bitbucket Pipelines](https://support.atlassian.com/rovo/docs/work-with-rovo-dev-in-bitbucket-pipelines/)
60. [How we made vulnerability fixes review-ready with Agentic Pipelines - Inside Atlassian](https://www.atlassian.com/blog/bitbucket/vulnerability-fixes-with-agentic-pipelines)
61. [Rovo DevOps Integration: Connectors, Rovo Dev, Bitbucket](https://crosstowntech.com/apps/rovo-devops-integration/)
62. [Atlassian says Rovo cut PR review time 45%. Here's the measurement they didn't publish. - DEV Community](https://dev.to/cole_halton_42f71d71b809b/atlassian-says-rovo-cut-pr-review-time-45-heres-the-measurement-they-didnt-publish-53po)
63. [30.8% Faster PRs: How AI-Driven Rovo Dev Code Reviewer Improved the Developer Productivity at Atlassian - Inside Atlassian](https://www.atlassian.com/blog/ai-at-work/developer-productivity-improved-with-rovo-dev)
64. [Meet Code Reviewer, now available with Jira - Inside Atlassian](https://www.atlassian.com/blog/development/code-reviewer)
65. [DORA 2025 Report: How AI Is Reshaping Development - Opsera](https://opsera.ai/blog/dora-2025-report-ai-software-development)
66. [2025 DORA Report: State of AI-assisted Software Development](https://businessdatasolutions.github.io/ai-wiki/sources/2025-09-23-dora-2025-state-of-ai-assisted-software-development)
67. [Technology Radar Vol. 33 (Nov 2025)](https://www.thoughtworks.com/content/dam/thoughtworks/documents/radar/2025/11/tr_technology_radar_vol_33_en.pdf)
68. [Spec-driven development](https://www.thoughtworks.com/radar/techniques/spec-driven-development)
69. [Spec-Driven Development: Spec Kit, Kiro, OpenSpec Compared](https://juliantellez.com/blog/what-spec-driven-development-is)
70. [Understanding Spec-Driven-Development: Kiro, spec-kit, and Tessl](https://daniliants.com/insights/understanding-spec-driven-development-kiro-spec-kit-and-tessl/)
71. [Techniques](https://www.thoughtworks.com/radar/techniques)
72. [Thoughtworks Radar 35: what to adopt with agents](https://www.onext.es/en/insights/thoughtworks-radar-35-what-to-adopt-agents/)
73. [Measuring the Impact of Early-2025 AI on Experienced Open-Source Developer Productivity - METR](https://metr.org/blog/2025-07-10-early-2025-ai-experienced-os-dev-study/)
74. [A randomized trial by METR found that experienced developers completed real coding tasks 19% slower when allowed to use AI tools — yet afterwards, they estimated on average that AI had made them 20% faster. - ScienceBlog.com](https://scienceblog.com/t-a-randomized-trial-by-metr-found-that-experienced-developers-completed-real-coding-tasks-19-slower-when-allowed-to-use-ai-tools-yet-afterwards-they-estimated-on-average-that-ai-had-made-them-20-fast/)
75. [METR 2026: AI Made Developers 19% Slower. Is That Still True?](https://ingenire.com/blog/metr-2026-developer-productivity-study)
76. <https://gitclear-public.s3.us-west-2.amazonaws.com/GitClear-AI-Copilot-Code-Quality-2025.pdf>
77. [Manage mods for your organization - Claude Code Docs](https://code.claude.com/docs/en/plugins/mods/admin)
78. [Doctolib: Doctolib's AI Adoption Playbook: from 30-person pilot to company-wide deployment](https://dust.tt/customers/doctolibs-ai-adoption-playbook-from-30-person-pilot-to-company-wide-deployment)
79. [Agentic AI Transforms Work Practices: Doctolib's Pioneering Approach - Dawn Liphardt](https://www.dawnliphardt.com/agentic-ai-transforms-work-practices-doctolibs-pioneering-approach/)
