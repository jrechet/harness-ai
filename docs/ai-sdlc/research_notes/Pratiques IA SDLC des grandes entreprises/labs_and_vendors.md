# How AI labs and dev-tool vendors changed their OWN SDLC with coding agents (2024 → Nov 2026)

Scope: Anthropic, OpenAI, GitHub, Microsoft, Google, Amazon/AWS. Research date: 2026-11-14.
Reading conventions used below:
- **[MEASURED]** = figure produced by instrumentation, telemetry, a survey with stated n, or a paper. **[SELF-REPORTED / EXEC CLAIM]** = executive statement, marketing post or estimate without method. **[SECONDARY]** = only found via press/aggregators, primary not retrieved.
- **[OLDER]** = pre-2025 or superseded material, kept only for trend.
- Note: OpenAI's "Harness engineering" post (openai.com/index/harness-engineering) returned HTTP 403 to the fetcher; its figures below are cross-checked across several secondary summaries but not read in the primary.

---

## 1. Anthropic — how Anthropic teams use Claude Code internally

### Takeaway
Anthropic is the most heavily instrumented case: a Dec 2025 internal study (132 surveyed, 53 interviews, 200k Claude Code transcripts) shows usage rising from 28% to 59% of daily work and merged PRs/engineer/day +67%; by Jan 2026 a spokesperson put company-wide AI-written code at 70–90%. The published methodology has shifted from "prompt the model harder" (2025: IMPORTANT/YOU MUST in CLAUDE.md) to "short CLAUDE.md + skills for procedures + hooks/deny rules/managed settings for anything that must be guaranteed" (current docs, 2026), with multi-agent Code Review on nearly every internal PR.

### Cited Findings
**Adoption and productivity data**
- [MEASURED, survey] "How AI is transforming work at Anthropic", published 2025-12-02 (research done Aug 2025): survey of 132 engineers/researchers, 53 interviews, 200,000 internal Claude Code transcripts (Feb vs Aug 2025). Models at the time: Claude Sonnet 4 / Opus 4. Response rate 31% (68 via Slack, 64 via direct outreach). — [Anthropic](https://www.anthropic.com/research/how-ai-is-transforming-work-at-anthropic)
- [SELF-REPORTED, survey] Share of daily work using Claude: 28% (≈12 months earlier) → 59%; self-reported productivity gain +20% → +50%; 14% of respondents report >100% gains. — [Anthropic](https://www.anthropic.com/research/how-ai-is-transforming-work-at-anthropic)
- [MEASURED, telemetry] Merged pull requests per engineer per day +67% after Claude Code adoption across the Engineering org. — [Anthropic](https://www.anthropic.com/research/how-ai-is-transforming-work-at-anthropic)
- [MEASURED, transcripts Feb→Aug 2025] Avg task complexity 3.2 → 3.8 (1–5 scale); max consecutive tool calls per transcript 9.8 → 21.2 (+116%); human turns per transcript 6.2 → 4.1 (−33%); feature implementation share of tasks 14.3% → 36.9%; code design/planning 1.0% → 9.9%; 8.6% of tasks were "papercut" fixes. — [Anthropic](https://www.anthropic.com/research/how-ai-is-transforming-work-at-anthropic)
- [SELF-REPORTED] 27% of Claude-assisted work would not have been done otherwise; >50% of respondents can "fully delegate" only 0–20% of their work; daily uses: debugging 55%, code understanding 42%, feature implementation 37%. — [Anthropic](https://www.anthropic.com/research/how-ai-is-transforming-work-at-anthropic)
- [EXEC CLAIM] Jan 2026: an Anthropic spokesperson told Fortune the company-wide share of AI-written code is 70–90%, and ~90% of Claude Code's own code is written by Claude Code; Boris Cherny (head of Claude Code) said 100% of his personal code for 2+ months. — [Fortune, 2026-01-29](https://fortune.com/2026/01/29/100-percent-of-code-at-anthropic-and-openai-is-now-ai-written-boris-cherny-roon/)
- [SECONDARY] A June 2026 talk summary attributes "80–90% across Anthropic, many teams at 100%" to Cherny. — [Dealroom note](https://app.dealroom.co/news/note/boris-cherny-on-coding-from-his-phone-and-the-post-coding-bottleneck)
- [SELF-REPORTED] Code Review launch post (2026-03-09): "code output per Anthropic engineer" grew 200% over the prior year, straining human reviewers. — [Claude blog](https://claude.com/blog/code-review)

**Role changes**
- [SELF-REPORTED, interviews] Engineers broaden toward full-stack; some shift toward reviewing/managing AI output (one estimated 70%+ of their work had become code review); concerns: skill atrophy, a "paradox of supervision" (oversight needs the skills that erode), fewer mentorship interactions (one engineer: Claude handles 80–90% of questions previously asked to colleagues). — [Anthropic](https://www.anthropic.com/research/how-ai-is-transforming-work-at-anthropic)

**Team practices (case study, 2025-07-24)**
- Security Engineering moved to "pseudocode → TDD with periodic check-ins"; incident stack-trace analysis ~3x faster; docs converted to markdown runbooks used as debugging context. Inference team: describe test intent, Claude writes tests in the codebase's language (e.g. Rust); research time on model functions cut ~80% (1h → 10–20 min). Data Infrastructure: K8s outage diagnosed from dashboard screenshots. Product Design: Figma → autonomous code/test loops, then human review; Claude built Vim key bindings for Claude Code with minimal review. Growth Marketing: two sub-agents generate ad variations (hours → minutes). Legal and non-engineers build their own tools. Onboarding via CLAUDE.md files. — [Claude blog, "How Anthropic teams use Claude Code"](https://claude.com/blog/how-anthropic-teams-use-claude-code)

**Guardrails: automated review**
- `/security-review` command + GitHub Action launched 2025-08-06; used internally first. Reported catches: an RCE reachable via DNS rebinding in a local HTTP server for an internal tool, and an SSRF, both fixed before merge. — [Anthropic news](https://www.anthropic.com/news/automate-security-reviews-with-claude-code); [The New Stack](https://thenewstack.io/anthropic-adds-auto-security-reviews-to-claude-code/)
- Independent check: Checkmarx showed the review missed an RCE via pandas and flagged it as a false positive; it also generates and executes its own test cases (risk). — [The Register, 2025-09-09](https://www.theregister.com/2025/09/09/ai_security_review_risks/)
- [MEASURED, internal] Code Review (multi-agent, research preview 2026-03-09): agents search for bugs in parallel, a verification step filters false positives, findings ranked by severity; ~20 min average; does not approve PRs (human approval kept). Internally: PRs with substantive review comments 16% → 54%; <1% of findings marked incorrect by engineers; PRs >1,000 lines: 84% get findings (avg 7.5 issues); PRs <50 lines: 31% (avg 0.5). Used on "nearly every" internal PR. — [Claude blog](https://claude.com/blog/code-review); [eWeek](https://www.eweek.com/news/anthropic-claude-code-review/)

**Published methodology / conventions**
- [OLDER, superseded in part] "Claude Code: Best practices for agentic coding" (Apr 2025) recommended tuning CLAUDE.md with emphasis ("IMPORTANT", "YOU MUST") and running it through a prompt improver; explore-plan-code-commit, TDD, multi-Claude, worktrees, headless mode. The URL now 308-redirects to the docs. — [anthropic.com/engineering (redirect)](https://www.anthropic.com/engineering/claude-code-best-practices)
- [CURRENT docs, 2026] "Best practices for Claude Code": explicit split between **non-deterministic** instructions (prompt, CLAUDE.md, skills) and **deterministic** controls (hooks, deny rules, managed settings). Rule of thumb: if you keep adding emphasis and Claude still misses a line, it belongs in a hook. CLAUDE.md should hold only what Claude cannot infer from code (exact test/lint commands, misleading code, undocumented decisions, "anything corrected twice"); personal preferences in `CLAUDE.local.md` (gitignored); path-scoped rules in `.claude/rules/*.md` with `paths:` frontmatter; team procedures in `.claude/skills/<name>/SKILL.md` (loaded on demand; `disable-model-invocation: true` for side-effecting workflows like releases); Stop hook to enforce "typecheck passes before done"; read-only reviewer subagent in `.claude/agents/` with `tools: Read, Grep, Glob`; fresh-context `/code-review`; `claude -w` worktrees for parallel sessions; `/batch` splits a migration into 5–30 units each in its own worktree/PR; `claude -p --bare` for reproducible CI runs. "What you can stop doing": ALL-CAPS emphasis, describing architecture in CLAUDE.md, "don't be lazy" prompts. Keep enforced set small ("if you find yourself at forty [hooks], most are preferences"). — [code.claude.com/docs/en/best-practices](https://code.claude.com/docs/en/best-practices)
- Scope hierarchy (what is central vs team vs individual): `~/.claude/settings.json` and `.claude/settings.local.json` = individual; `.claude/settings.json` + hooks committed in repo = whole repo team (deny rules apply immediately; allow rules wait for workspace trust); **managed settings** (admin console, MDM or `managed-settings.json`) = organization, cannot be overridden, "the only place for a security team's policy". — [code.claude.com/docs/en/best-practices](https://code.claude.com/docs/en/best-practices)
- Extension primitives timeline: Claude Code plugins (bundle slash commands, subagents, MCP servers, hooks) announced ~2025-10-10 with marketplaces; Agent Skills launched Oct 2025; org-wide skill management + Agent Skills published as an open standard Dec 2025. — [DevOps.com](https://devops.com/claude-introduces-agent-skills-for-custom-ai-workflows/); [@IT/ITmedia (JP)](https://atmarkit.itmedia.co.jp/ait/articles/2510/16/news034.html); [@IT/ITmedia (JP), Jan 2026](https://atmarkit.itmedia.co.jp/ait/articles/2601/29/news055.html)
- MCP donated to the Linux Foundation's Agentic AI Foundation (AAIF), co-founded with OpenAI and Block, announced 2025-12-09. — [OpenAI](https://openai.com/index/agentic-ai-foundation/); [InfoQ](https://www.infoq.com/news/2025/12/agentic-ai-foundation)

### Inferences
- Anthropic's own guidance converges with this repo's rule "what must be guaranteed goes into the CLI/hooks, not the skill text": the vendor itself now classifies CLAUDE.md as *advisory* and hooks/managed settings as *enforcement*.
- The +67% merged PRs/engineer/day (telemetry) vs +50% self-reported productivity vs "200% code output" (launch marketing) are three different metrics; only the first is a measured throughput figure, and none measures outcome quality. The review-load problem (output up, review the bottleneck) is what drove Code Review.
- The 70–90% "AI-written code" figure is a spokesperson statement with no published method (line attribution? accepted diffs?), so it is not comparable with Google's 75% or Microsoft's 30%.

### Gaps
- No published Anthropic method for computing "% of code written by Claude".
- No primary source found for a formal internal policy document (e.g., mandatory CLAUDE.md template, mandatory review gates) beyond what the docs and launch posts imply.
- No measured defect/incident-rate data for AI-written code at Anthropic.

---

## 2. OpenAI — how OpenAI teams use Codex internally

### Takeaway
OpenAI's internal model is the "agentic software factory": AGENTS.md as a short map into a versioned docs/ system of record, mechanical architecture enforcement (custom linters, structural tests), Codex reviewing almost all PRs before humans, risk-tiered review with opt-in auto-approval for low-risk areas, and agents that also run rollout and incident triage. The flagship "harness engineering" experiment (Feb 2026) built ~1M LOC with zero hand-written code; adoption figures (92% of technical staff daily, +70% PRs/week) are company-reported.

### Cited Findings
**Adoption and productivity**
- [EXEC CLAIM] DevDay 2025-10-06: ~92% of OpenAI technical staff use Codex daily (up from ~50% earlier in the year); engineers complete ~70% more PRs per week; usage ~10x since August 2025. — [VentureBeat](https://venturebeat.com/ai/the-most-important-openai-announcement-you-probably-missed-at-devday-2025); [Analytics India Mag](https://analyticsindiamag.com/ai-news-updates/almost-all-new-code-written-at-openai-today-is-from-codex-users/)
- [EXEC CLAIM] GPT-5-Codex launch (Sept 2025): Codex "reviews the vast majority of our PRs", catching hundreds of issues daily, often before human review. Internal eval: 4.4% of GPT-5-Codex review comments incorrect vs 13.7% for GPT-5 (high); 52% judged "high-impact" vs 39%. — [OpenAI](https://openai.com/index/introducing-upgrades-to-codex/)
- [MEASURED, proxy] OpenAI alignment post: Codex code review comments on 36% of PRs entirely generated by Codex cloud; OpenAI notes no clean direct measurement exists. — [OpenAI Alignment blog](https://alignment.openai.com/scaling-code-verification/)
- [SELF-REPORTED, personal] An OpenAI researcher ("roon") says 100% of his code is AI-written. — [Fortune, 2026-01-29](https://fortune.com/2026/01/29/100-percent-of-code-at-anthropic-and-openai-is-now-ai-written-boris-cherny-roon/)

**"Harness engineering" (Ryan Lopopolo, Codex team, 2026-02-11) — primary returned 403; figures via secondaries**
- Internal beta product built in ~5 months with zero manually written source code: ~1M lines; ~1,500 merged PRs; team of 3 engineers growing to 7; ~3.5 PRs per engineer per day (one podcast summary says "per week" — unit conflict noted). Codex wrote app logic, docs, CI config, observability setup and tooling. — [InfoQ, 2026-02-21](https://www.infoq.com/news/2026/02/openai-harness-engineering-codex); [ZenML summary](https://zenml.io/llmops-database/harness-engineering-building-software-where-humans-steer-and-agents-execute); [The Neuron](https://www.theneuron.ai/explainer-articles/openais-harness-engineering-playbook-how-to-ship-1m-lines-of-code-without-writing-any/); primary: [openai.com/index/harness-engineering](https://openai.com/index/harness-engineering/)
- AGENTS.md kept to ~100 lines as a **map/table of contents** pointing into a structured `docs/` directory (maps, execution plans, design specs) treated as single source of truth; a single big AGENTS.md failed because it crowded out task context. Knowledge not in the repo "effectively doesn't exist" for the agent. — [The Neuron](https://www.theneuron.ai/explainer-articles/openais-harness-engineering-playbook-how-to-ship-1m-lines-of-code-without-writing-any/); [InfoQ](https://www.infoq.com/news/2026/02/openai-harness-engineering-codex)
- Architecture enforced mechanically: fixed dependency layers (Types → Config → Repo → Service → Runtime → UI) checked by structural tests and custom linters; docs cross-links validated in CI; example custom ESLint rule (written by Codex, 100% tested) banning a duplicated helper outside its approved location. — [InfoQ](https://www.infoq.com/news/2026/02/openai-harness-engineering-codex); [The Neuron](https://www.theneuron.ai/explainer-articles/openais-harness-engineering-playbook-how-to-ship-1m-lines-of-code-without-writing-any/)
- "Garbage collection": the team first spent every Friday cleaning "AI slop", which didn't scale; replaced by recurring agent tasks that scan for violations and open targeted cleanup PRs. Humans "encode taste" as enforceable rules. Agents get logs/metrics/spans and isolated environments to reproduce bugs. — [The Neuron](https://www.theneuron.ai/explainer-articles/openais-harness-engineering-playbook-how-to-ship-1m-lines-of-code-without-writing-any/); [InfoQ](https://www.infoq.com/news/2026/02/openai-harness-engineering-codex)
- [SECONDARY] April 2026 Latent Space summary: team pushed from 3.5 to 5–10+ PRs/engineer/day. — [Latent Space summary](https://summaries-5ws.pages.dev/summaries/2026-04-07-latent-space-extreme-harness-engineering-for-token-billionaires-1m-loc-1b-toksday-0-human-code-0-human-review)

**Software factory (Pragmatic Engineer, 2026-09-15)**
- Pipeline: human defines outcome → Codex gathers context from in-repo docs, GitHub, Slack, Notion, Databricks, Datadog, logs, internal skills → implements, tests, opens PR and "babysits" CI → perf harness routes risky PRs to A/B → **multiple domain-specialist review agents** (e.g. cloud infra, security) → **changes classified by risk**: high-risk get stricter human review, low-risk areas can **opt in to auto-approval** → after human approval, a per-change agent runs rollout (feature flags) and builds its own monitoring dashboard → "Perf Factory" agents analyze latency regressions → "Sevbot" incident agent suggests mitigations but executes only on engineer instruction; on-call still exists. — [Pragmatic Engineer](https://newsletter.pragmaticengineer.com/p/openai-software-factory)
- Codex became central around Jan 2026; non-engineering teams (finance, recruiting, legal) went ~0% → 90% Codex usage in four months; `/goal` usage 60% → 90% (Apr→May 2026); IDE usage declining; PRs per engineer "like a hockey stick"; CI/CD and VCS seeing ~10x load within ~6 months. Teams distribute **role- and team-specific plugins and skills**; engineers described as becoming more like PMs. — [Pragmatic Engineer](https://newsletter.pragmaticengineer.com/p/openai-software-factory)
- "How OpenAI uses Codex" guide (2025): used daily by Security, Product Engineering, Frontend, API, Infrastructure, Performance Engineering; seven use cases (code understanding, refactors/migrations, perf, test coverage, velocity, staying in flow, exploration); practices incl. "Ask mode first", give structure/context/room to iterate. — [OpenAI guide](https://openai.com/business/guides-and-resources/how-openai-uses-codex/); [PDF](https://cdn.openai.com/pdf/6a2631dc-783e-479b-b1a4-af0cfbd38630/how-openai-uses-codex.pdf)

**AGENTS.md as a cross-vendor standard**
- AGENTS.md (contributed by OpenAI; origin date not verified in this pass) donated to the Linux Foundation's Agentic AI Foundation (announced 2025-12-09), alongside Anthropic's MCP and Block's goose; >60,000 projects reported using it at donation time. — [OpenAI](https://openai.com/index/agentic-ai-foundation/); [InfoQ](https://www.infoq.com/news/2025/12/agentic-ai-foundation)

### Inferences
- OpenAI's guardrail philosophy is "prevent mechanically, review by agents, escalate by risk" rather than "humans read every diff": human review is concentrated on high-risk changes, and low-risk areas can bypass it by opt-in. This is a team-level opt-in on top of a centrally maintained harness.
- The "AGENTS.md as ~100-line map + docs/ as system of record" pattern is the clearest vendor statement that root instruction files must stay small and point elsewhere — consistent with Anthropic's current "keep CLAUDE.md short" guidance.

### Gaps
- The primary harness-engineering post could not be read (403); team-size and PR-rate figures rest on consistent secondaries, with one unit conflict (per day vs per week).
- No OpenAI-published method for the 70% PR uplift or 92% adoption; no defect/incident data for agent-authored changes.
- Paywalled parts of the Pragmatic Engineer piece (AGENTS.md usage details, % of code by Codex) not accessible.

---

## 3. GitHub — Copilot coding agent, Agent HQ, code review, custom instructions, Spec Kit, agentic workflows

### Takeaway
GitHub dogfoods the issue→agent→PR loop in its core `github/github` monolith (renames, flag removals, security gates, migrations, audits), always merged through normal human review. Its product surface encodes a layered instruction model (personal > repository > organization; path-specific `.instructions.md` with `applyTo`; nearest `AGENTS.md` wins) plus admin control planes (Agent HQ) and two published methodologies: Spec Kit (spec-driven) and Agentic Workflows / "Continuous AI" (Markdown workflows compiled to Actions with read-only defaults and "safe outputs").

### Cited Findings
**Internal use (dogfooding)**
- "How Copilot helps build the GitHub platform" (Matt Nigh, 2025-11-12): engineers assign issues in the core repo to Copilot; it opens first-pass PRs; engineers review like any PR and merge, iterate or close. Analyzed one month of Copilot PRs. Task types: typo cleanup (one PR fixed 161 typos across 100 files), removing deprecated feature flags, repository-wide class renames, performance anti-patterns, production errors, flaky tests, a new REST endpoint, security gates preventing internal integrations from modifying releases, DB column type migrations, audits returned as PRs+reports. Copilot's merged-PR rate is **lower** than humans' (no figure given). — [GitHub blog](https://github.blog/ai-and-ml/github-copilot/how-copilot-helps-build-the-github-platform/)
- Billing team (≈June 2025): assigns tech-debt tasks to the coding agent in parallel with feature work; humans choose which debt and judge business impact; tip: write repository Copilot instructions for a "much better experience". — [GitHub blog](https://github.blog/ai-and-ml/github-copilot/how-the-github-billing-team-uses-the-coding-agent-in-github-copilot-to-continuously-burn-down-technical-debt/)
- [SECONDARY] A GitHub product lead said the agent was the #5 contributor in the repo where the agent itself is built; a GitHub employee on HN said the coding agent had been used internally at GitHub and across Microsoft for ~3 months before May 2025 launch. — [LeadDev](https://leaddev.com/technical-direction/githubs-coding-agent-your-newest-junior-dev); [HN thread](https://hn.svelte.dev/item/44031432)

**Code review**
- [SELF-REPORTED, product telemetry] "60 million Copilot code reviews and counting" (2026-03-05): 10x growth since April 2025 launch; >1 in 5 code reviews on GitHub; >12,000 orgs run it automatically on every PR; 71% of reviews surface actionable feedback, 29% post nothing; ~5.1 comments per review; agentic architecture with tool calling, memory across reviews, review plan for long PRs, reads linked issues/PRs. — [GitHub blog](https://github.blog/news-insights/product-news/60-million-copilot-code-reviews-and-counting/)

**Custom instructions (repo-level conventions and overrides)**
- Repository-wide `.github/copilot-instructions.md`; path-specific `.github/instructions/**/NAME.instructions.md` with `applyTo` glob frontmatter; `AGENTS.md` anywhere (nearest in tree takes precedence) or a single root `CLAUDE.md`/`GEMINI.md`; `excludeAgent: "code-review" | "cloud-agent"` to scope a file to one agent. Precedence: **personal > repository > organization**, but all relevant sets are sent, so GitHub advises avoiding conflicts. Code review reads instructions from the PR head branch. Agent-generated onboarding instructions limited to 2 pages. — [GitHub Docs](https://docs.github.com/en/copilot/how-tos/configure-custom-instructions/add-repository-instructions)
- Copilot cannot merge its own PRs (guardrail). — [GitHub Docs](https://docs.github.com/en/copilot/rolling-out-github-copilot-at-scale/enabling-developers/integrating-agentic-ai)

**Agent HQ / mission control (Universe, 2025-10-28)**
- Mission control across github.com, VS Code, mobile, CLI to assign, watch and review agent sessions, incl. running several agents on the same task; third-party agents (OpenAI, Anthropic, Google, xAI…); custom agents defined in source-controlled files so rules/guardrails version with code; **AI control plane** for admins (security policies, model/agent access limits, audit logs). Timing of third-party availability differed across sources at launch. — [GitHub blog](https://github.blog/news-insights/company-news/welcome-home-agents/); [The New Stack](https://thenewstack.io/github-embraces-the-coding-agent-competition-with-agent-hq/); [TechTarget](https://www.techtarget.com/it-infrastructure/news/366633584/GitHub-Agent-HQ-opens-platform-to-third-party-coding-agents)

**Published methodologies**
- Spec Kit (2025-09-02): open-source spec-driven development toolkit; `specify` CLI; flow constitution → specify → plan → tasks → implement (optional clarify/analyze); launched for Copilot, Claude Code, Gemini CLI, now 30+ agents; GitHub calls it an experiment. — [Visual Studio Magazine](https://visualstudiomagazine.com/articles/2025/09/03/github-open-sources-kit-for-spec-driven-ai-development.aspx); [Spec Kit docs](https://github.github.com/spec-kit/); [Microsoft dev blog, 2025-09-15](https://developer.microsoft.com/blog/spec-driven-development-spec-kit/)
- GitHub Agentic Workflows (technical preview 2026-02-13, GitHub Next + Microsoft Research): Markdown workflow files in `.github/workflows/` compiled by `gh aw` into standard Actions running a coding agent; **read-only permissions by default**, writes only via pre-approved "safe outputs"; positioned as "Continuous AI" augmenting, not replacing, CI/CD; `gh aw audit` for runs. — [GitHub changelog](https://github.blog/changelog/2026-02-13-github-agentic-workflows-are-now-in-technical-preview/); [GitHub blog](https://github.blog/ai-and-ml/automate-repository-tasks-with-github-agentic-workflows/); [The Register](https://www.theregister.com/2026/02/17/github_previews_agentic_workflows/)

### Inferences
- GitHub's internal framing is "first pass, not starting from zero" — the agent is a PR author subject to the same review gates as humans, with a lower merge rate; value is in throughput on chores, migrations and debt.
- GitHub is the only vendor that publishes an explicit three-level precedence (personal/repo/org) plus path-scoping and per-agent exclusion — the most complete reference model for "centrally standardized vs repo override".

### Gaps
- No published internal metrics (share of github/github PRs authored by Copilot, merge rate, review time) from a primary source.
- Whether GitHub itself enforces org-level instructions or custom agents internally is not documented.

---

## 4. Microsoft — agentic DevOps, Azure SRE Agent, AI code review, org changes

### Takeaway
Microsoft's internal story is "customer zero" at scale: an internal AI PR reviewer on >90% of PRs (~600k PRs/month, July 2025), Azure SRE Agent handling incidents (35,000+ autonomously handled, 50,000+ dev hours saved over nine months to April 2026), and the SRE Agent team itself "building agents with agents" via spec-driven development. Code-share claims are lower (~20–30% in April 2025) and all figures are self-reported.

### Cited Findings
- [SELF-REPORTED] Internal AI code review assistant: started as an internal experiment, scaled to >90% of PRs company-wide, >600K PRs/month; generates structured feedback and PR summaries (Engineering at Microsoft blog, 2025-07-14). — [Microsoft devblogs](https://devblogs.microsoft.com/engineering-at-microsoft/enhancing-code-quality-at-scale-with-ai-powered-code-reviews/); [Neowin](https://www.neowin.net/news/microsoft-is-using-ai-copilot-internally-for-code-reviews-impacting-600000-prs-per-month/)
- [SECONDARY] 10–20% median PR completion time improvement in early-adopter repos (not verified against primary). — [ZenML summary](https://www.zenml.io/llmops-database/ai-powered-code-review-assistant-at-enterprise-scale)
- [SELF-REPORTED] "How we build and use Azure SRE Agent with agentic workflows" (2026-04-05, Customer Zero series): SDLC split into specialized agents — Plan & Code (spec-driven development; agents draft specs, build prototypes, check into staging), Verify/Test/Deploy (code quality, security, evaluation, deployment agents), Operate & Optimize (SRE Agent; a dedicated instance maintains the agent itself). Over last nine months: 35,000+ incidents handled autonomously, 50,000+ developer hours saved; Azure Container Apps: 89% positive engineer responses to RCA results covering >90% of incidents; Azure App Service: time-to-mitigation 3 minutes vs 40.5-hour human-only average. Guardrails: governance, human approval checks, RBAC, escalation paths. — [Microsoft Tech Community](https://techcommunity.microsoft.com/blog/appsonazureblog/how-we-build-azure-sre-agent-with-agentic-workflows/4508753)
- [SELF-REPORTED, conflicting] SRE Agent GA announcement cites 1,300+ agents deployed internally, 35,000+ incidents mitigated, 20,000+ engineering hours saved; Microsoft DevOps page now cites 50,000+ hours; an older version cited 13k+ incidents / 10.5k+ hours. Figures differ by date and scope. — [GA announcement](https://techcommunity.microsoft.com/blog/appsonazureblog/announcing-general-availability-for-the-azure-sre-agent/4500682); [DevOps at Microsoft](https://azure.microsoft.com/en-us/solutions/devops/devops-at-microsoft); [The New Stack](https://thenewstack.io/azure-sre-agent-operations/)
- [SECONDARY] "91% of Microsoft's global engineering team uses GitHub Copilot" appeared in a search snippet of the DevOps at Microsoft page but was **not** present in the fetched version — treat as unverified. — [DevOps at Microsoft](https://azure.microsoft.com/en-us/solutions/devops/devops-at-microsoft)
- [EXEC CLAIM] Satya Nadella, April 2025: ~20–30% of code in Microsoft repos written by AI. — [Fortune, 2026-01-29 (recap)](https://fortune.com/2026/01/29/100-percent-of-code-at-anthropic-and-openai-is-now-ai-written-boris-cherny-roon/)
- Org change: CoreAI division (Jan 2025, led by Jay Parikh) merges Developer Division, AI Platform and parts of Office of the CTO; "agent factory" (Foundry) vision; Parikh runs team-by-team "Ops Reviews" to find common engineering pain. [SECONDARY, Business Insider memos] Foundry delivered $337M favorable COGS YTD, $606M annualized projection (2025). — [ITPro](https://www.itpro.com/technology/artificial-intelligence/Microsoft-coreai-division-satya-nadella); [Benzinga](https://benzinga.com/z/45561957)

### Inferences
- Microsoft's most mature internal agent use is in **review and operations** (PR review, incident RCA/mitigation) rather than authoring; the SDLC is being split into stage-specific agents with human approval boundaries.
- Spec-driven development is the common thread between GitHub Spec Kit (Microsoft-promoted) and the SRE Agent team's internal process.

### Gaps
- No primary source found for an internal Microsoft standard for AI-assisted development (e.g., mandated instruction files, review policies), nor for Copilot coding-agent internal adoption metrics across Microsoft.
- No independent verification of SRE Agent or code-review figures; the 91% Copilot figure could not be confirmed.

---

## 5. Google — share of AI-generated code, internal migrations, Jules / Gemini CLI / Antigravity, internal tooling

### Takeaway
Google's headline metric rose from ~25% of new code AI-generated (Oct 2024) to 50% (fall 2025) to 75% "AI-generated and approved by engineers" (Cloud Next, 2026-04-22), framed as a shift to "truly agentic workflows". The strongest *measured* evidence is the FSE-track migration paper (39 migrations, 74.45% of code changes LLM-generated, ~50% time saved). Internal tooling (Cider IDE agent, "Jetski", "Agent Smith") and usage mandates are documented only via press reports.

### Cited Findings
- [EXEC CLAIM] Sundar Pichai, Cloud Next 2026 (2026-04-22): ~75% of all new code at Google is AI-generated and approved by engineers, up from 50% the previous fall; a complex code migration by agents + engineers finished 6x faster than a year earlier with engineers alone. — [blog.google](https://blog.google/innovation-and-ai/infrastructure-and-cloud/google-cloud/cloud-next-2026-sundar-pichai/); [Semafor](https://www.semafor.com/article/04/24/2026/google-ceo-says-75-of-companys-new-code-is-ai-generated); [TechSpot](https://www.techspot.com/news/112152-google-ai-now-generates-75-new-code-up.html)
- Definitional caveat: the claim covers *new* code, counted as AI-suggested code accepted/edited by humans; not the whole codebase. — [dev.to analysis](https://dev.to/simon_paxton/googles-75-ai-generated-code-claim-hides-the-real-shift-abe)
- [MEASURED, paper] "Migrating Code At Scale With LLMs At Google" (Ziftci et al., arXiv 2504.09691, 2025-04-13): 39 migrations over 12 months by 3 developers; 595 code changes, 93,574 edits submitted; 74.45% of code changes and 69.46% of edits LLM-generated; developers *estimated* 50% reduction in total migration time; method combines change-location discovery with an LLM. — [arXiv](https://arxiv.org/abs/2504.09691)
- [MEASURED, experience report] "How is Google using AI for internal code migrations?" (arXiv 2501.06972, Jan 2025). — [arXiv](https://arxiv.org/abs/2501.06972v1)
- [OLDER, 2024] Google Research (2024-06-06): >8% of code review comments addressed with AI assistance; pasted-code adaptation ~2% of IDE code (completion era). 2023 ICSE-SEIP paper on ML-resolved review comments (~7%). — [Google Research blog](https://research.google/blog/ai-in-software-engineering-at-google-progress-and-the-path-ahead/); [Resolving code review comments with ML](https://research.google/blog/resolving-code-review-comments-with-ml/)
- Public products: Jules async coding agent GA 2025-08-06 (Gemini 2.5 Pro); Gemini CLI GitHub Actions; at I/O 2026-05-19 Google announced Gemini CLI transitioning into **Antigravity CLI** (Agent Skills, Hooks, Subagents, Extensions carried over), and Gemini CLI/Code Assist IDE extensions stopped serving consumer tiers on 2026-06-18. — [SiliconANGLE](https://siliconangle.com/?p=706416); [InfoQ](https://www.infoq.com/news/2025/08/google-jules); [Google Developers Blog](https://developers.googleblog.com/an-important-update-transitioning-gemini-cli-to-antigravity-cli/); [Virtualization Review](https://virtualizationreview.com/articles/2026/05/19/google-moves-gemini-cli-into-antigravity-cli-as-agent-platform-expands.aspx)
- [SECONDARY, press reports of internal memos] Sergey Brin memo: Gemini engineers "must" use internal agents for complex multi-step tasks; Business Insider reported AI usage added to some SWE job requirements and to the GRAD performance process, with managers given usage-tracking dashboards; internal tools named Cider (IDE with coding agent), Jetski, and "Agent Smith" (async background agent, access restricted after demand). Naming hierarchy inconsistent across sources. — [The Decoder](https://the-decoder.com/google-builds-elite-team-to-close-the-coding-gap-with-anthropic/); [Android Authority](https://www.androidauthority.com/google-ai-coding-strike-team-report-3659975/); [People Matters](https://sea.peoplemattersglobal.com/news/ai-and-emerging-tech/google-increases-pressure-on-employees-to-adopt-ai-report-48596)

### Inferences
- Google's metric is the most longitudinal (25% → 50% → 75% over ~18 months) but its definition (accepted AI suggestions incl. completion) makes it a measure of *authorship assistance*, not of agent autonomy.
- Google's published, peer-reviewable evidence is concentrated on **migrations** — a bounded, verifiable task class with a human reviewer per change — which is where the measured gains are.
- Reports of mandates and usage tracking tied to performance processes suggest central, top-down adoption pressure, but unconfirmed by Google.

### Gaps
- No primary Google source on internal agent tooling (Cider/Jetski/Agent Smith), instruction-file conventions in google3, or internal review policy for agent-authored CLs.
- No measured productivity/quality figures beyond the migration papers.

---

## 6. Amazon / AWS — AI-DLC, Kiro, Amazon Q transformations, rituals, internal mandates

### Takeaway
AWS published the most explicit *methodology* — AI-DLC (July 2025): AI plans/asks/implements only after human validation, artifacts persisted in the repo, "bolts" of hours/days instead of sprints, and team rituals (Mob Elaboration, Mob Construction) — then open-sourced it as adaptive rule files for Kiro, Q, Claude Code, Copilot, etc. Internally, Amazon centralized tooling (Nov 2025 memo making Kiro the recommended tool, 80% weekly-AI-use target), then loosened it (Claude Code and Codex allowed, May 2026) and admitted its usage metrics are flawed (Oct 2026). The Amazon Q Java-upgrade savings (Aug 2024) are executive estimates.

### Cited Findings
**AI-DLC methodology**
- "AI-Driven Development Life Cycle: Reimagining Software Engineering" (Raja SP, AWS DevOps blog, 2025-07-31): two dimensions — AI-powered execution with human oversight, dynamic team collaboration. Phases: **Inception** (AI turns intent into requirements, stories, units via **Mob Elaboration** where the team validates AI's questions/proposals), **Construction** (AI proposes architecture, domain model, code, tests via **Mob Construction**), **Operations** (IaC/deployments with team oversight). "Bolts" replace sprints (hours/days); "Units of Work" replace epics. AI creates a plan, asks clarifying questions, implements only after human validation; plans/requirements/design artifacts saved in the repo for persistent context. No quantified metrics; no statement of internal Amazon usage. — [AWS DevOps blog](https://aws.amazon.com/blogs/devops/ai-driven-development-life-cycle/)
- Open-sourced "adaptive workflows" (~2025-11-29): workflows select stages and depth per problem type (greenfield, brownfield/refactor, defect fix…), with mandatory vs conditional stages (e.g., Reverse Engineering for brownfield vs Requirements Analysis for greenfield); implemented as rules/steering files (e.g., core file in `.amazonq/rules`, detailed stage rules loaded on demand to save tokens); repo `awslabs/aidlc-workflows` with setup for Kiro, Amazon Q, Cursor, Cline, Claude Code, GitHub Copilot. — [AWS DevOps blog](https://aws.amazon.com/blogs/devops/open-sourcing-adaptive-workflows-for-ai-driven-development-life-cycle-ai-dlc); [aws-news.com](https://aws-news.com/article/2025-11-29-open-sourcing-adaptive-workflows-for-ai-driven-development-life-cycle-ai-dlc)
- AI-DLC presented at re:Invent 2025 (session DVT214). — [dev.to recap](https://dev.to/kazuya_dev/aws-reinvent-2025-introducing-ai-driven-development-lifecycle-ai-dlc-dvt214-32b)

**Kiro (spec-driven)**
- Kiro launched July 2025; specs under `.kiro/specs/` produce `requirements.md` (user stories + acceptance criteria in EARS notation), `design.md` (data flow, interfaces, schemas, endpoints), `tasks.md` (dependency-ordered, traced to requirements), with human approval between phases; **steering files** for persistent project constraints; **hooks** (event-driven automations). [SECONDARY] GA reported 2025-11-17 with Kiro CLI, team plans, checkpointing, property-based testing (single source). — [SD Times](https://sdtimes.com/ai/amazon-launches-spec-driven-ai-ide-kiro/); [Kiro specs explained](https://codemyspec.com/blog/kiro-specs-explained); [horadecodar (PT)](https://horadecodar.com.br/kiro-spec-driven-development/)

**Amazon Q transformations [OLDER, Aug 2024]**
- [EXEC CLAIM] Andy Jassy (Aug 2024): Java 17 upgrade time fell from ~50 developer-days per app to a few hours; "4,500 developer-years" saved (his own estimate); >half of production Java systems upgraded in <6 months; ~$260M annualized efficiency gains (includes security and infra cost, not only labor). — [The Decoder](https://the-decoder.com/amazons-ai-assistant-saves-4500-years-of-development-time-ceo-andy-jassy-says/); [Benzinga](https://www.benzinga.com/news/24/08/40537747/amazon-ceo-andy-jassy-says-companys-ai-assistant-has-saved-260m-and-4-5k-developer-years-of-work-its)

**Internal mandates and metrics**
- [SECONDARY, Reuters-viewed memo] Nov 2025 memo (Peter DeSantis, Dave Treadwell): Kiro is "our recommended AI-native development tool for Amazon"; no plan to support additional third-party AI dev tools; existing tools stay supported. Codex had been marked "Do Not Use" after ~6-month assessment (Oct 2025). — [The Star / Reuters](https://www.thestar.com.my/tech/tech-news/2025/11/25/amazon-pushes-in-house-ai-coding-tool-kiro-over-competitors039-memo-shows); [People Matters](https://www.peoplematters.in/news/ai-and-emerging-tech/amazon-memo-reveals-push-for-employees-to-use-only-kiro-its-in-house-ai-tool-47390)
- [SECONDARY] May 2026 memo (Jim Haughwout, VP Software Builder Experience): Claude Code made available immediately to employees; Codex rolling out company-wide from 2026-05-12; Kiro remains in use. — [Pulse (aggregator of Reuters/BI)](https://www.pulse.bot/ai/news/amazon-relents-lets-its-programmers-use-openais-codex-and-anthropics-claude-92670cfd-f430-466c-a045-540799a3bef9/); [Slashdot](https://tech.slashdot.org/story/26/05/10/0618225/)
- [SECONDARY] Oct 2026 memo published internally (intro by VP/Distinguished Engineer Terk Terkowitz): target >80% of developers using AI weekly; input metrics (tokens, adoption) and throughput metrics (code changes, reviews) used despite leaders writing they are "deeply flawed"; "Kirorank" leaderboard (June) led to "tokenmaxxing" and was shut down; new metric "normalised deployments"; managers review the 10th and 90th percentile of adoption; engineers for whom AI doesn't help should document why ("a finding rather than a failing"); Treadwell: don't use AI "just for the sake of using AI". — [HRD/HCAmag, 2026-10-28](https://www.hcamag.com/au/news/general/amazon-admits-ai-metrics-are-flawed-but-says-they-still-count/595194)

### Inferences
- AWS separates **methodology** (AI-DLC, tool-agnostic, open rules files, ritualized team validation) from **tooling** (Kiro, centrally pushed then relaxed). The methodology puts the human checkpoint at *intent/requirements and design* (mob rituals, phase gates) rather than only at code review.
- Amazon's experience is the clearest documented case of adoption metrics backfiring (leaderboard → tokenmaxxing) and of a central single-tool mandate being reversed under engineer pressure.

### Gaps
- No primary evidence that AI-DLC is used by Amazon's own product teams (vs. customer engagements); no measured AI-DLC outcomes.
- Kiro GA date and internal adoption share (e.g., reported "30% of devs hadn't touched Kiro by Jan 2026") rest on weak secondary sources.
- Reports linking a Dec 2025 AWS outage to Kiro were not verified and are excluded.
- The often-quoted Amazon Q figure "79% of auto-generated code reviews shipped without changes" (Aug 2024) was not re-verified in this pass.

---

## 7. Cross-cutting — what is centrally standardized vs left to teams; how repo-level instructions and overrides work

### Takeaway
All six converge on a three-layer model: (1) org-level central controls (managed settings, admin control planes, approved-tool lists, adoption metrics), (2) repo-level versioned instructions and enforcement (CLAUDE.md/AGENTS.md/copilot-instructions/steering files + hooks, linters, CI), (3) team/individual extensions (skills, plugins, custom agents, local overrides). The vendors' 2026 guidance is that root instruction files stay short (map, not encyclopedia), path-scoped rules handle subtrees, and anything that must always hold moves from prose to deterministic enforcement.

### Cited Findings
- Anthropic: individual (`~/.claude`, `settings.local.json`, `CLAUDE.local.md`) < repo (`.claude/settings.json`, hooks, CLAUDE.md, `.claude/rules/` with `paths:`, `.claude/skills/`, `.claude/agents/`) < **managed settings** (org, non-overridable). — [Claude Code docs](https://code.claude.com/docs/en/best-practices)
- GitHub: personal > repository > organization precedence for instructions (all sent); path-specific `applyTo`; nearest `AGENTS.md` wins; `excludeAgent`; Agent HQ control plane for policies, model/agent access and audit logs. — [GitHub Docs](https://docs.github.com/en/copilot/how-tos/configure-custom-instructions/add-repository-instructions); [The New Stack](https://thenewstack.io/github-embraces-the-coding-agent-competition-with-agent-hq/)
- OpenAI: central shared Codex harness + Codex-team-maintained internal skills; team-owned plugins/skills; per-area opt-in to auto-approval for low-risk PRs; risk-tiered review. AGENTS.md ~100 lines as map into `docs/`. — [Pragmatic Engineer](https://newsletter.pragmaticengineer.com/p/openai-software-factory); [The Neuron](https://www.theneuron.ai/explainer-articles/openais-harness-engineering-playbook-how-to-ship-1m-lines-of-code-without-writing-any/)
- AWS: AI-DLC core rules always loaded, stage rules loaded on demand; tool-specific locations (`.amazonq/rules`, Kiro steering); central tool policy and adoption targets at company level. — [AWS DevOps blog](https://aws.amazon.com/blogs/devops/open-sourcing-adaptive-workflows-for-ai-driven-development-life-cycle-ai-dlc); [HCAmag](https://www.hcamag.com/au/news/general/amazon-admits-ai-metrics-are-flawed-but-says-they-still-count/595194)
- Microsoft: governance guardrails, human approval checks, RBAC, escalation paths around SRE agents. — [Microsoft Tech Community](https://techcommunity.microsoft.com/blog/appsonazureblog/how-we-build-azure-sre-agent-with-agentic-workflows/4508753)
- Google: (press-reported) central mandates and usage tracking tied to performance processes. — [People Matters](https://sea.peoplemattersglobal.com/news/ai-and-emerging-tech/google-increases-pressure-on-employees-to-adopt-ai-report-48596)
- Instruction-file standardization: AGENTS.md (OpenAI) and MCP (Anthropic) under Linux Foundation AAIF since Dec 2025; GitHub Copilot reads AGENTS.md/CLAUDE.md/GEMINI.md; Google's Antigravity CLI keeps Agent Skills, Hooks, Subagents. — [OpenAI](https://openai.com/index/agentic-ai-foundation/); [GitHub Docs](https://docs.github.com/en/copilot/how-tos/configure-custom-instructions/add-repository-instructions); [Google Developers Blog](https://developers.googleblog.com/an-important-update-transitioning-gemini-cli-to-antigravity-cli/)
- Review as the universal guardrail: Anthropic Code Review on nearly every internal PR (no auto-approve), OpenAI Codex review on the vast majority of PRs plus specialist review agents, Microsoft AI reviewer on >90% of PRs, GitHub Copilot review on >1 in 5 GitHub reviews, Copilot coding agent cannot merge its own PRs. — sources as cited in sections 1–4.

### Inferences
- Common pattern across labs: **agent writes → agent reviews → human approves (risk-weighted)**, with deterministic gates (linters, structural tests, hooks, CI) as the non-negotiable layer. OpenAI is the furthest along in letting low-risk changes skip human review.
- Methodologies published for others split into two families: **spec-first** (AWS AI-DLC/Kiro, GitHub Spec Kit, Microsoft SRE Agent team) and **harness-first** (OpenAI harness engineering, Anthropic's deterministic-vs-advisory guidance). They are complementary: specs fix intent, harness fixes enforcement.
- Metrics culture is the weak spot: every "% of code by AI" figure uses an undisclosed or different definition; only Anthropic (telemetry, survey with n) and Google (migration paper) publish method; Amazon openly states its adoption metrics are flawed.

### Gaps
- No vendor publishes a full internal policy document (who may enable which agent with which permissions, retention, approval matrix).
- No comparable, independently measured quality outcomes (defect escape, incident rate, rework) for agent-authored code at any of the six companies.
