# Ticket to production: end-to-end AI agent pipelines and role-specific agents (state as of 2026-11-14)

Notes from about 40 searches and fetches. "Vendor" means the vendor's own claim. "Independent" means a third party or peer-reviewed measurement. A product that was renamed or merged is flagged. Every figure carries its date and URL. When only a secondary source was found, the finding says so.

## 1. Ticket intake and refinement, and Jira/Linear to agent to PR flows

### Takeaway
By late 2026 the issue tracker is where agents get assigned work. Jira and Linear both put agents in the assignee field next to people, and assigning a ticket to Jira Coding Agent (formerly Rovo Dev in Jira), Copilot cloud agent, Cursor, Devin or Factory produces a draft PR. Refinement (readiness checks, acceptance criteria, triage, dedup) is mostly assistive: agents suggest and humans accept, with auto-apply as an opt-in.

### Cited Findings
**Atlassian / Jira**
- Atlassian's support docs now call the Jira-to-code feature **Jira Coding Agent**. "Rovo Dev" only appears in a link. You start it from a work item ("Start work" > Jira Coding Agent) or by assigning the work item to it. It runs in a cloud sandbox that only the person who started the session can access, and it can optionally push a draft PR. Including the work item key in the commit message or PR description links the PR automatically. The PR author is the human, and "the agent doesn't merge pull requests". It acts with the initiating user's permissions, can create, read and update but not delete in Jira and Confluence, and does not connect to MCP sources. The page describes no plan-approval step. — [Atlassian Support, fetched 2026-11-14](https://support.atlassian.com/rovo/docs/generate-code-from-a-work-item-in-jira/)
- The New Stack reports the rename ("until recently, called Rovo Dev") and says it is included in every paid plan. That is secondary, but the Atlassian docs above confirm the name. — [The New Stack](https://thenewstack.io/?p=22830395)
- **Flag on dates:** Atlassian announced Rovo Dev in Jira, with work items going to a merge-ready PR in the background. A mirrored press release is dated 2026-04-08. — [Atlassian blog](https://www.atlassian.com/blog/announcements/rovo-dev-in-jira); [mirror, 2026-04-08](https://aeo.washinmura.jp/ai/atlassian-com/en/news/2026-04-08-press-release-launch-of-rovo-dev-an-ai-a)
- In "Your Jira Board just got a new kind of teammate" (2026-06-18):
  - Agents appear in the assignee field next to humans and can be @mentioned in comments.
  - Automation rules can trigger them on creation, field update or schedule.
  - Dragging an issue into a configured board column can auto-assign it to an agent, and a "Trigger agent action" rule can sit on a workflow transition.
  - Third-party agents (GitHub Copilot, Cursor, custom ones) connect through Atlassian's agent framework, and there are more than 20 ready-made Rovo agents.
  - Governance: agents act within existing permissions, and every action is "visible and traceable". — [Atlassian blog, 2026-06-18](https://www.atlassian.com/blog/ai-at-work/your-jira-board-just-got-a-new-kind-of-teammate)
- Atlassian's **Readiness checker** Rovo agent checks work items against a team's "definition of ready": required fields, clear description, acceptance criteria, estimates, links. It can run in bulk through Jira automation. — [Atlassian use case page](https://www.atlassian.com/it/software/rovo/use-cases/agent-readiness-checker); [Atlassian Community course "Rovo for product owners"](https://community.atlassian.com/learning/lesson/prepare-for-sprint-planning-with-rovos-readiness-checker-agent)
- Rovo prompts in the work-item editor include generating acceptance criteria from a description and brainstorming QA edge cases. Community examples show custom agents that write User Story, Context and Acceptance Criteria sections, put "TBD" where information is missing, and ask for explicit approval before creating items. These are community and third-party sources, not official docs. — [Atlassian Community, "Break down work with Rovo"](https://community.atlassian.com/learning/course/rovo-for-product-owners/lesson/break-down-work-with-rovo); [Automation Consultants](https://www.automation-consultants.com/creating-a-custom-rovo-agent-for-smarter-demand-intake/)

**GitHub Copilot cloud agent (formerly "Copilot coding agent")**
- Copilot cloud agent for **Linear** reached GA on 2026-07-23, after a public preview from 2025-10-28. GA added model choice and custom agents. — [GitHub changelog 2026-07-23](https://github.blog/changelog/2026-07-23-copilot-cloud-agent-for-linear-is-now-generally-available/); [GitHub changelog 2025-10-28](https://github.blog/changelog/2025-10-28-github-copilot-for-linear-available-in-public-preview)
- Copilot for **Jira**: assigning an issue (or mentioning Copilot) starts the agent, which reads the description and comments and opens a draft PR. It needs Jira Cloud with Rovo enabled. Public preview according to the Marketplace listing. — [GitHub Docs](https://docs.github.com/en/copilot/how-tos/use-copilot-agents/cloud-agent/integrate-cloud-agent-with-jira); [DevOps.com](https://devops.com/github-copilot-coding-agent-for-jira-connects-planning-to-pull-requests-without-leaving-your-workflow/); [Atlassian Marketplace](https://marketplace.atlassian.com/apps/2210929719/github-copilot-for-jira)
- GitHub Docs (per the search summary) say third-party integrations (Azure Boards, Jira, Linear) only support creating a PR directly. — [GitHub Docs, Linear integration](https://docs.github.com/en/copilot/how-tos/use-copilot-agents/coding-agent/integrate-coding-agent-with-linear)
- Inside GitHub, work starts from an issue, a PR, chat or an **automation**. Automations can run on a schedule or on repository events "such as triaging issues". Copilot can also be assigned code-scanning alerts from security campaigns. — [GitHub Docs, About cloud agent](https://docs.github.com/en/copilot/concepts/agents/cloud-agent/about-cloud-agent)

**Linear**
- Triage Intelligence was previewed in August 2025 as "Product Intelligence" and later renamed. It uses LLMs to suggest team, assignee, labels, duplicates and related issues, and teams can turn on auto-apply. Linear's docs list it on Business and Enterprise plans. — [Linear docs](https://linear.app/docs/triage-intelligence); [Linear changelog 2025-08-14](https://linear.app/changelog/2025-08-14-product-intelligence-technology-preview); [Linear changelog 2025-09-19, auto-apply](https://linear.app/changelog/2025-09-19-auto-apply-triage-suggestions)
- Linear Agent for Intercom, Zendesk and Gong (2025-12-11) merges duplicate customer requests into existing issues. — [Linear changelog](https://linear.app/changelog/2025-12-11-linear-agent-for-intercom-zendesk-gong)
- **Conflict:** sources disagree on which plans include Linear Agent. One secondary source says every plan, including Free, as of 2026-10-19; another says Business and Enterprise only. — [Sentra](https://www.sentra.app/articles/linear-ai); [BuildBetter](https://blog.buildbetter.ai/linear-ai-agents-2026-guide-5-alternatives-for-engineering-teams/)

**Other ticket-to-PR agents**
- **Cursor:** its Jira page says assigning an issue or mentioning @Cursor makes a cloud agent open the PR. Cursor's "background agents" are now called "cloud agents". — [cursor.com/product/jira](https://cursor.com/product/jira)
- **Devin:** you tag Devin on a Jira or Linear ticket and it plans the work. A third-party write-up dates the native Linear integration to Devin 2.2 (2026-02-24). — [Cognition blog](https://cognition.ai/blog/how-cognition-uses-devin-to-build-devin); [Linear integrations: Devin](https://linear.app/integrations/devin)
- **Factory:** tagging a Linear issue lets Droids pull its context and produce a PR. Remote delegation (assign the ticket or mention @Factory) is in private preview, per a secondary source. — [Linear integrations: Factory](https://linear.app/integrations/factory); [Factory product page](https://factory.ai/product/ai-project-manager); [AlphaSignal](https://alphasignal.ai/news/factory-s-droid-now-turns-linear-tickets-into-pull-requests-autonomously)
- **OpenAI Symphony** (open-sourced 2026-04-27) is a spec plus an Elixir reference implementation:
  - A daemon polls Linear, claims unblocked issues, provisions isolated workspaces and launches Codex.
  - Agents update Linear only through a `linear_graphql` tool exposed by the orchestrator, so the Linear token stays out of the containers.
  - OpenAI says ambiguous work still goes to developers in interactive sessions. — [OpenAI](https://openai.com/index/open-source-codex-orchestration-symphony); [Help Net Security 2026-04-28](https://www.helpnetsecurity.com/2026/04/28/openai-symphony-codex-orchestration-linear/)

### Inferences
- Three intake models coexist:
  - The tracker is the control plane (Jira assignee and transitions, Linear assign, Symphony polling).
  - Chat is the entry point (Stripe from Slack, see Q7).
  - The agent is called from the PR or IDE.
- Each tracker exposes the agent as an assignee, so the ticket stays the unit of traceability.
- Refinement agents act as gatekeepers on "definition of ready" (readiness checker) more than as authors. None of the sources shows a refinement agent writing stories without a human PO accepting them.
- The "Rovo Dev" name now covers several surfaces (CLI, code reviewer, Jira agent). For Jira-to-PR, the current name is Jira Coding Agent.

### Gaps
- No acceptance or quality metrics found for refinement agents (AI-written acceptance criteria, readiness scoring, triage auto-apply accuracy).
- No official documentation found for the Readiness checker's scoring criteria.
- Copilot on GitHub Issues (issue-form refinement, sub-issue generation): only the "automations" mention was found, with no detail.

## 2. Code review agents

### Takeaway
AI review is the most widely deployed and best-measured stage. The useful numbers:
- Two in-house studies: Uber, about 65% of comments addressed (2025-08), and Atlassian, 38.7% of comments led to a code change and median PR cycle time dropped 30.8% (arXiv paper, 2026-01).
- One vendor figure: Copilot code review covers more than one in five reviews on GitHub (2026-03).
- No independent cross-vendor acceptance benchmark was found.

Teams encode checklists as rule registries, per-category confidence thresholds, and repo instruction files.

### Cited Findings
**Uber uReview (in-house, 2025-08-12)**
- Pipeline: ingestion that drops low-signal files, then three pluggable assistants (Standard for bugs, Best Practices for Uber conventions, AppSec for security), then quality filtering (a second prompt scores confidence, similar comments are merged, a category classifier suppresses low-value categories), then inline posting with feedback streamed to Hive. — [Uber blog](https://www.uber.com/blog/ureview/)
- Checklists live in "a shared registry of style rules". Confidence thresholds are tuned per assistant, language and category from developer feedback. Simple syntactic rules stay in linters. — [Uber blog](https://www.uber.com/blog/ureview/)
- Uber suppresses readability nits, minor logging tweaks, low-impact performance suggestions and style issues because developers rated them poorly. It keeps correctness bugs, missing error handling and best-practice violations with links to internal docs. — [Uber blog](https://www.uber.com/blog/ureview/)
- Metrics (in-house):
  - Usefulness above 75%.
  - About 65% of comments addressed, versus 51% for human reviewers' comments.
  - "Addressed" is measured by re-running uReview five times on the final commit.
  - It analyzes over 90% of about 65,000 diffs. The post says "weekly" in one place and "per month" in another.
  - Median review time in CI is 4 minutes; Uber estimates about 1,500 hours saved per week. — [Uber blog](https://www.uber.com/blog/ureview/)

**Atlassian RovoDev Code Reviewer**
- A year-long online evaluation across more than 1,900 repositories: median PR cycle time down 30.8%, human-written review comments down 35.6%, and 38.70% of agent comments led directly to a change in the next commit. This is an arXiv paper with a published method. A secondary summary calls it ICSE 2026; I did not verify the venue. — [arXiv 2601.01129](https://arxiv.org/abs/2601.01129v2)
- Atlassian's blog (vendor, Rovo Dev broadly) claims PR cycle time down 45%, and the average wait for a first review comment going from 18 hours to "0". Its method is not given. — [Atlassian blog](https://www.atlassian.com/blog/rovo/how-we-cut-pr-cycle-time-with-ai-code-reviews); [Atlassian blog, developer productivity](https://www.atlassian.com/blog/ai-at-work/developer-productivity-improved-with-rovo-dev)

**GitHub Copilot code review**
- Vendor claim (2026-03): usage grew tenfold and now accounts for more than one in five code reviews on GitHub. Secondary outlets cite 60 million reviews; I did not find the GitHub primary post. — [StartupHub](https://www.startuphub.ai/ai-news/technology/2026/copilot-code-review-hits-60-million); [mirror of the GitHub post 2026-03-05](https://pbnews.pages.dev/stories/2026-03-05-60-million-copilot-code-reviews-and-counting-0ea6d1bad7b0dca7)
- Since 2026-09-11, Copilot closes its own comments once a later commit addresses them. — [GitHub changelog](https://github.blog/changelog/2026-09-11-auto-resolution-and-analysis-updates-in-copilot-code-review)
- Since 2026-11-05, the usage metrics API exposes `total_comments_evaluated` and `total_comments_addressed` per repository, measured when the PR merges. Each org can compute its own addressed rate, but GitHub publishes no aggregate. Earlier additions: comment types (2026-05-08) and merge metrics for Copilot-reviewed PRs (2026-04-08). — [GitHub changelog 2026-11-05](https://github.blog/changelog/2026-11-05-usage-metrics-api-adds-code-review-details-and-addressed-rate); [2026-05-08](https://github.blog/changelog/2026-05-08-copilot-code-review-comment-types-now-in-usage-metrics-api); [2026-04-08](https://github.blog/changelog/2026-04-08-copilot-reviewed-pull-request-merge-metrics-now-in-the-usage-metrics-api)
- A third-party guide reports 56.5% precision. The method is unclear, so treat it as weak. — [MorphLLM](https://www.morphllm.com/copilot-code-review)

**Anthropic**
- **Claude Code Review** (launched 2026-03-09, research preview for Team and Enterprise):
  - Several reviewer agents run in parallel, verify their findings and rank them by severity.
  - It runs automatically on new PRs once the GitHub app is installed.
  - Reported cost averages $15–25 per review.
  - Vendor results: the share of internal PRs with substantive comments rose from 16% to 54%; 84% of PRs over 1,000 lines get findings, averaging 7.5 issues. — [Help Net Security 2026-03-10](https://www.helpnetsecurity.com/2026/03/10/anthropic-claude-code-review/); [InfoQ 2026-04](https://infoq.com/news/2026/04/claude-code-review); [DevOps.com](https://devops.com/anthropic-code-review-dispatches-agent-teams-to-catch-the-bugs-that-skim-reads-miss/)
- The `claude-code-security-review` GitHub Action and the `/security-review` command are covered in Q4.

**Cursor / Graphite**
- Cursor announced its acquisition of Graphite on 2025-12-19. Graphite stays a standalone product; the plan is to merge Graphite's AI Reviewer with Cursor's Bugbot and integrate stacked PRs. Graphite's "Diamond" brand is not mentioned in the coverage, so its status is unclear (flag). — [SiliconANGLE](https://siliconangle.com/2025/12/19/cursor-acquires-ai-code-review-startup-graphite/); [Fortune](https://fortune.com/2025/12/19/cursor-ai-coding-startup-graphite-competition-heats-up/); [DevOps.com](https://devops.com/cursor-acquires-graphite-to-streamline-ai-powered-development/)

**CodeRabbit (vendor study on AI-written code, 2025-12-17)**
- 470 open-source PRs (320 AI co-authored, 150 human-only): 10.83 issues per AI PR versus 6.45 per human PR, with 1.4x more critical and 1.7x more major issues. Authorship was inferred, not verified. CodeRabbit sells AI review, so this is a vendor study. — [CodeRabbit](https://www.coderabbit.ai/blog/state-of-ai-vs-human-code-generation-report); [The Register](https://www.theregister.com/2025/12/17/ai_code_bugs/)

### Inferences
- The two in-house measurements put "comment acted upon" between about 39% (Atlassian, next-commit change) and about 65% (Uber, re-run method). The definitions differ, so the figures should not be compared directly.
- Uber's lesson is to suppress style and nit categories and to tune per category. It suggests a review agent's precision comes from a curated category list and thresholds more than from the model.
- In every source, the review agent is an extra reviewer, not the approver. No source shows an AI review counting as the required approval.

### Gaps
- No independent, cross-vendor measurement of acceptance rates (CodeRabbit, Copilot, Claude, Bugbot, Qodo Merge).
- CodeRabbit's own acceptance figures and Graphite Diamond's post-acquisition status were not found.
- The exact GitHub primary post with the "60 million reviews" figure was not retrieved.

## 3. QA and testing agents

### Takeaway
Test generation has the strongest industrial evidence (Meta TestGen-LLM, Uber AutoCover). Both rely on deterministic validation gates (it builds, it passes repeatedly, coverage goes up, mutation checks) before anything reaches a human. Playwright now ships planner, generator and healer agents for E2E tests. "QA agents" that read acceptance criteria are mostly readiness checks or spec formats (EARS in Kiro) rather than measured products.

### Cited Findings
- **Meta TestGen-LLM** (paper from February 2024, so older):
  - It improves existing human-written tests rather than writing new suites.
  - Instagram Reels and Stories evaluation: 75% of generated tests built, 57% passed reliably, 25% increased coverage.
  - In test-a-thons, 73% of its recommendations were accepted, and it improved 11.5% of the classes it was applied to.
  - A candidate is shown to humans only after passing the build, pass-reliably and coverage filters. — [arXiv 2402.09171](https://ar5iv.labs.arxiv.org/html/2402.09171)
- **Uber AutoCover** (ICSE-SEIP 2026):
  - A multi-agent generator built on LangGraph, deployed to all engineers from September 2024 to September 2025.
  - About 11% of new tests reviewed and added to Uber's codebase come from it.
  - Experts rated its tests higher than Cursor's on a sample of production Go code.
  - Validation gates include coverage deltas and mutation or branch checks. — [ICSE 2026 SEIP listing](https://conf.researchr.org/details/icse-2026/icse-2026-software-engineering-in-practice/58/Automated-Software-Test-Generation-at-Industry-Scale-Using-a-Multi-Agent-Architecture); [paper PDF](https://homes.cs.washington.edu/~rjust/publ/auto_cover_icse_2026.pdf)
- **Playwright Test Agents** (introduced in v1.56, October 2025): a **planner** explores the app and writes a Markdown test plan, a **generator** turns the plan into Playwright tests checked against the live app, and a **healer** runs the suite and repairs failing tests. They can be wired into Claude Code, VS Code or opencode. — [playwright.dev/docs/test-agents](https://playwright.dev/docs/test-agents)
- **Qodo** (formerly CodiumAI) publishes `cover-agent`, an open-source implementation of the TestGen-LLM approach. — [GitHub codium-ai/cover-agent](https://github.com/codium-ai/cover-agent)
- **Acceptance criteria as test input:**
  - Kiro specs use EARS-style acceptance criteria in requirements.md and a checkbox task list (secondary source).
  - Atlassian's readiness checker verifies that acceptance criteria exist before sprint planning. — [Verdent guide on Kiro](https://www.verdent.ai/guides/agents/kiro-spec-driven-development); [Atlassian readiness checker](https://www.atlassian.com/it/software/rovo/use-cases/agent-readiness-checker)
- **Team-specific QA rules:**
  - Stripe's agents read the same rule files as Cursor and Claude Code, mostly applied per subdirectory.
  - Uber keeps a shared rule registry.
  - Both run deterministic test subsets: Stripe picks from more than 3 million tests. — [Stripe Minions part 1](https://stripe.dev/blog/minions-stripes-one-shot-end-to-end-coding-agents); [Uber uReview](https://www.uber.com/blog/ureview/)

### Inferences
- Across sources, a test agent's output is trusted only after deterministic filters (build, repeated passes, coverage delta, mutation). Teams encode QA rules as executable gates more than as prompt text.
- E2E agents (Playwright healer) raise the question of who is allowed to "heal" a failing test. None of the sources shows a governance rule for that, which is a risk: a healed test can mask a regression.

### Gaps
- No measured product found for an "agent reads acceptance criteria and runs a QA pass" (Jira AC to test results). Vendor marketing exists, but no data.
- No 2026 acceptance figures found for Qodo or Copilot test generation.
- No independent evaluation of Playwright healer accuracy.

## 4. Security agents

### Takeaway
Security agents sit in four places:
1. In the PR, as a diff review (Claude security-review action, Copilot's built-in CodeQL and secret scanning on agent PRs, Copilot Autofix).
2. As a continuous repository scanner proposing patches (OpenAI Codex Security, formerly Aardvark; Google CodeMender).
3. As SAST triage that cuts false positives (Semgrep, Snyk).
4. As pre-production pentesting (AWS Security Agent).

Almost every figure is a vendor claim, and every source keeps a human before merge or upstream submission.

### Cited Findings
- **OpenAI Aardvark, renamed Codex Security (flag):**
  - Private beta in October 2025; 92% recall on "golden" repositories with known and planted vulnerabilities.
  - Rebranded as Codex Security on 2026-03-06 (research preview).
  - It builds a project threat model, validates findings in sandboxes and proposes patches.
  - Vendor figures for the last 30 days of the beta: 1.2 million commits scanned, 792 critical and 10,561 high-severity findings, 14 CVEs from open-source audits, over-reported severity down more than 90%, false positives down more than 50%. — [OpenAI, Introducing Aardvark](https://openai.com/index/introducing-aardvark); [The Decoder](https://the-decoder.com/openai-launches-codex-security-an-ai-agent-designed-to-detect-vulnerabilities-in-software-projects/); [Gigazine 2026-03-09](https://www.gigazine.net/gsc_news/en/20260309-codex-security)
- **Google DeepMind CodeMender** (2025-10-06):
  - Built on Gemini Deep Think; validates patches with differential testing, fuzzing and SMT solvers.
  - 72 fixes upstreamed in six months, on codebases up to 4.5 million lines.
  - A human reviews every patch before submission.
  - Folded into Google's Agent Platform after I/O 2026; enterprise availability "soon". — [The Hacker News](https://thehackernews.com/2025/10/googles-new-ai-doesnt-just-find.html); [InfoWorld](https://www.infoworld.com/article/4176170/google-folds-codemender-into-agent-ecosystem-amid-push-for-ai-led-appsec-2.html)
- **GitHub Copilot Autofix** (beta data May–July 2024, so older): median time to fix a PR alert was about 28 minutes with Autofix versus about 1.5 hours manually, and XSS fixes were 7x faster. — [GitHub blog](https://github.blog/news-insights/product-news/secure-code-more-than-three-times-faster-with-copilot-autofix/)
- **Security built into Copilot cloud agent PRs:** CodeQL, a check of new dependencies against the Advisory Database, and secret scanning all run on agent-written code without an extra license. Hidden characters and HTML comments are removed from issues to blunt prompt injection. — [GitHub Docs, risks and mitigations](https://docs.github.com/en/copilot/concepts/agents/cloud-agent/risks-and-mitigations)
- **Claude Code security review** (2025-08):
  - A `/security-review` slash command plus a GitHub Action that analyzes only changed files on `pull_request` and posts inline comments.
  - Teams can customize it by copying `security-review.md` into `.claude/commands/` or passing filtering instructions.
  - The README warns it is not hardened against prompt injection: use it only on trusted PRs. — [GitHub anthropics/claude-code-security-review](https://github.com/anthropics/claude-code-security-review); [Anthropic](https://www.anthropic.com/news/automate-security-reviews-with-claude-code)
- **AWS Security Agent** (one of the "frontier agents" from re:Invent December 2025, GA around March/April 2026 per secondary sources) does on-demand pentesting and continuous security review. — [Amazon press release 2025-12](https://press.aboutamazon.com/2025/12/aws-unveils-frontier-agents-a-new-class-of-ai-agents-that-work-as-an-extension-of-your-software-development-team); [The Letter Two 2026-03-31](https://thelettertwo.com/2026/03/31/aws-frontier-agents-ga-devops-security/)
- **Semgrep (vendor, 2025):** the AI handles about 60% of incoming SAST triage, and users agree with its decisions over 96% of the time. Semgrep's docs note that its "false positive confidence" metric measures precision on what it flags as false positives, not overall recall. — [Semgrep blog](https://semgrep.dev/blog/2025/semgrep-is-confidently-handling-60-of-all-triage-for-users-without-reducing-coverage); [Semgrep docs, metrics](https://cloudflare.semgrep.dev/docs/semgrep-assistant/metrics)
- **Snyk Agent Fix** generates up to five candidate fixes and re-tests them with Snyk Code. That comes from a secondary source, and no independent accuracy figure was found. — [Corgea comparison](https://corgea.com/blog/compare/snyk-vs-semgrep)

### Inferences
- The pipeline shape is "scan, then patch PR, then human". Codex Security, CodeMender and Autofix all produce PRs or suggestions, and none merges itself.
- AI security review of PRs written by agents adds its own attack surface (prompt injection in PR content). Anthropic says so explicitly, and GitHub filters hidden content.

### Gaps
- No independent benchmark found for Codex Security, CodeMender, AWS Security Agent or Snyk Agent Fix.
- Google Big Sleep was not researched in this pass.
- Codex Security pricing and GA status as of November 2026 are not confirmed.

## 5. Deployment and SRE agents

### Takeaway
Ops agents are now generally available from the three hyperscaler and observability ecosystems: Azure SRE Agent (GA 2026-03-10), AWS DevOps Agent (GA around 2026-03/04, secondary sources) and Datadog Bits AI SRE (GA 2025-12-02). Their main job is investigation and root cause analysis. Remediation is either advisory or limited to playbooks, and the fix to code goes back to dev as an issue or PR. No source shows a coding agent allowed to deploy to production on its own.

### Cited Findings
- **Azure SRE Agent:**
  - GA announced 2026-03-10. Microsoft says it runs it internally with 1,300+ agents deployed, 35,000+ incidents mitigated and 20,000+ engineering hours saved per month (vendor).
  - VNet integration is GA, and a 30-day trial became GA around August 2026.
  - Billing is in Azure Agent Units; one source cites 4 AAU per hour of background monitoring (secondary, unverified). — [Microsoft Tech Community GA post](https://techcommunity.microsoft.com/blog/appsonazureblog/announcing-general-availability-for-the-azure-sre-agent/4500682); [Azure update AZ558321](https://mc.merill.net/message/AZ558321); [AZ569695](https://mc.merill.net/message/AZ569695); [AZ569760](https://mc.merill.net/message/AZ569760)
- **Ops-to-dev handoff:**
  - Azure SRE Agent can create a GitHub or Azure DevOps work item after an investigation.
  - Microsoft demos show it assigning the issue to `@copilot`, after which Copilot cloud agent opens a PR for human review. This needs a paid Copilot plan.
  - One Microsoft post mentions merging validated fixes, but most sources show a human merge, so autonomous merge is unconfirmed. — [Microsoft Learn: connect a code repository](https://learn.microsoft.com/en-us/azure/sre-agent/code-repository-connect); [Microsoft Tech Community](https://techcommunity.microsoft.com/blog/appsonazureblog/-/4482000); [Dynatrace](https://www.dynatrace.com/news/blog/boost-cloud-reliability-dynatrace-and-azure-sre-agent-unite-for-autonomous-operations/)
- **AWS frontier agents:**
  - Announced at re:Invent in December 2025: Kiro autonomous agent, AWS Security Agent and AWS DevOps Agent.
  - DevOps Agent and Security Agent reached GA around 2026-03-31 / 04-06 per secondary sources, with DevOps Agent billing from 2026-04-10.
  - DevOps Agent investigates incidents, correlates telemetry with code and deployments, and runs operational playbooks. GA added connectors (Datadog, Splunk, GitHub, PagerDuty).
  - Preview-customer claims via secondary sources: MTTR up to 75% lower, 94% root-cause accuracy. Pricing of about $30/h (DevOps) and $50/h (pentest) is unverified. — [Amazon press release](https://press.aboutamazon.com/2025/12/aws-unveils-frontier-agents-a-new-class-of-ai-agents-that-work-as-an-extension-of-your-software-development-team); [Engineered.at roundup 2026-04-06](https://engineered.at/articles/aws-weekly-roundup-aws-devops-agent-security-agent-ga-product-lifecycle-updates-and-more-april-6-2026); [Enterprise DNA](https://enterprisedna.co/resources/news/aws-frontier-agents-devops-security-ga-2026)
- **Datadog Bits AI SRE:**
  - GA 2025-12-02. It investigates alerts on its own using runbooks and telemetry, often has a likely root cause or proposed code fix before the paged engineer opens a laptop, and posts its conclusion to collaboration tools.
  - Vendor figures: tested in more than 2,000 customer environments, tens of thousands of investigations. — [Datadog press release](https://www.datadoghq.com/about/latest-news/press-releases/datadog-launches-bits-ai-sre-agent-to-resolve-incidents-faster/); [Datadog blog](https://datadoghq.com/blog/bits-ai-sre/)
- **AI SRE startups** (mostly comparison articles written by competitors, so weak):
  - Cleric is described as read-only by design.
  - Resolve.ai is described as generating PRs and remediation commands, and its guidance is to start in advisory mode and widen autonomy as accuracy is proven. Reported funding: $125M at a $1B valuation (February 2026).
  - incident.io claims MTTR down up to 80% (vendor). — [Better Stack](https://betterstack.com/community/comparisons/cleric-alternatives/); [Augment Code](https://www.augmentcode.com/tools/best-ai-sre-tools); [dev.to roundup](https://dev.to/siddharth_singh_409bd5267/top-15-ai-sre-tools-in-2026-open-source-and-commercial-1bl7); [incident.io blog](https://incident.io/blog/best-resolve-ai-alternatives-2026)
- **Progressive delivery with agents:** only vendor or academic material was found. It recommends rings or canaries with an explicit rollback owner per stage, enforcement at the point where a side effect happens, and semantic signals such as cost regressions alongside infrastructure metrics. An arXiv paper notes that progressive delivery tools still rely on static rules and human approval. — [Gravitee](https://www.gravitee.io/corpus/gen-1950/devops/progressive-delivery-strategies-for-ai-agent-gateways-and-mcp-servers.html); [arXiv 2508.11867](https://arxiv.org/pdf/2508.11867v1)
- **Who can deploy:**
  - Copilot cloud agent PRs do not run GitHub Actions workflows until a user with write access clicks "Approve and run workflows", so automation chains cannot trigger themselves.
  - The agent cannot approve, merge or mark a PR ready for review. — [GitHub Docs, risks and mitigations](https://docs.github.com/en/copilot/concepts/agents/cloud-agent/risks-and-mitigations)

### Inferences
- The production boundary is held by CI/CD gates and merge rights, not by the agents. Coding agents cannot merge, and ops agents investigate and propose. Where they execute, they are limited to playbooks.
- The documented closed loop is incident, SRE agent, issue, coding agent, PR, human review and merge, then the normal pipeline. The handoff object is always a tracker issue, which keeps it traceable.

### Gaps
- PagerDuty's agent products (names, GA, autonomy levels) were not researched in primary sources.
- No primary source found on agents driving deploy and rollback (Argo Rollouts, Harness, LaunchDarkly) with measured results.
- No independent MTTR measurement found for any AI SRE product.
- The execution scope of Azure SRE Agent mitigations (learn.microsoft.com/azure/sre-agent/execute-mitigations) was not fetched.

## 6. Orchestration patterns, human gates, traceability and definitions of done

### Takeaway
Five patterns coexist:
- **Tracker-driven** (assign or transition a ticket, an agent runs).
- **CI-triggered** specialized agents (review, security and test on every PR).
- **Deterministic plus agent "blueprints"** (Stripe, Uber AutoCover).
- **Spec-driven phase gates** (AWS AI-DLC, Spec Kit, Kiro).
- **Mission control** across vendors (GitHub Agent HQ).

Nobody documents a "super agent" running end to end. Human gates sit at spec approval (in spec-driven setups), at PR review and merge (everywhere), and at workflow approval for agent PRs (GitHub). Traceability rests on ticket keys in PRs, co-authored signed commits, and session logs.

### Cited Findings
- **GitHub Agent HQ** (Universe 2025-10-28):
  - A "mission control" to assign, steer and track agents across GitHub, VS Code, mobile and the CLI.
  - Third-party agents (Anthropic, OpenAI, Google, Cognition, xAI) inside GitHub.
  - Branch controls deciding when CI runs on agent code, and agent identity and access.
  - A secondary source reports a public preview on 2026-02-04 with Claude and Codex. — [GitHub blog](https://github.blog/news-insights/product-news/welcome-home-agents/); [VentureBeat](https://venturebeat.com/ai/githubs-agent-hq-aims-to-solve-enterprises-biggest-ai-coding-problem-too); [Eficode](https://www.eficode.com/blog/why-github-agent-hq-matters-for-engineering-teams-in-2026)
- **GitHub's human gates on agent PRs:**
  - The requester cannot approve the PR, the agent cannot approve or merge or mark it ready, and draft PRs need human review.
  - When the PR is attributed to the app identity, one more approval is required.
  - The agent pushes only to a single `copilot/` branch.
  - Commits are authored by Copilot with the requester as co-author, signed, and linked to session logs. — [GitHub Docs, risks and mitigations](https://docs.github.com/en/copilot/concepts/agents/cloud-agent/risks-and-mitigations)
- **Repository-level controls:** custom instructions, custom agents and skills, MCP servers and **hooks** (commands run during agent work for validation or logging). GitHub Actions sessions are capped at 59 minutes. — [GitHub Docs, About cloud agent](https://docs.github.com/en/copilot/concepts/agents/cloud-agent/about-cloud-agent)
- **AWS AI-DLC** (open-sourced 2025-11-29):
  - Three phases: Inception, Construction, Operations.
  - Human approvals "embedded at every decision gate"; collective "Mob Elaboration" and "Mob Construction" rituals.
  - The workflow is adaptive: it skips or deepens stages (a simple defect fix skips requirements analysis).
  - It ships as Amazon Q Rules and Kiro steering files in `awslabs/aidlc-workflows`. — [AWS DevOps blog](https://aws.amazon.com/blogs/devops/open-sourcing-adaptive-workflows-for-ai-driven-development-life-cycle-ai-dlc)
  - Later versions reportedly add more phases and stages and more targets (Claude Code, Cursor, Codex CLI, Copilot). Versions differ by source (secondary). — [SourcePulse](https://www.sourcepulse.org/projects/24376265)
- **Spec Kit and Kiro:** spec, plan, tasks, implementation, with explicit human approval between phases; Kiro's "Quick Spec" mode skips the gates. Secondary sources only; not checked against official docs. — [Medium guide](https://medium.com/@visrow/comprehensive-guide-to-spec-driven-development-kiro-github-spec-kit-and-bmad-method-5d28ff61b9b1); [Verdent](https://www.verdent.ai/guides/agents/kiro-spec-driven-development)
- **Hybrid deterministic plus agent orchestration:**
  - Stripe interleaves agent loops with deterministic code for git, lint and test, so required steps always run.
  - Context is pre-hydrated by running MCP tools deterministically before the agent starts.
  - CI rounds are capped ("at most two").
  - Uber AutoCover is a LangGraph pipeline with validation gates. — [Stripe Minions part 1](https://stripe.dev/blog/minions-stripes-one-shot-end-to-end-coding-agents); [AutoCover PDF](https://homes.cs.washington.edu/~rjust/publ/auto_cover_icse_2026.pdf)
- **Tracker-driven orchestration:**
  - Jira agents can sit in the assignee field, board columns and workflow transitions.
  - Symphony claims only unblocked Linear issues, so a task tree runs in parallel, and it keeps credentials in the orchestrator. — [Atlassian 2026-06-18](https://www.atlassian.com/blog/ai-at-work/your-jira-board-just-got-a-new-kind-of-teammate); [OpenAI Symphony](https://openai.com/index/open-source-codex-orchestration-symphony)
- **Traceability, ticket to PR:**
  - Jira Coding Agent links the PR through the work item key and lists the human as author.
  - Linear shows a "[WIP]" PR in the issue's Links.
  - Atlassian says every agent action leaves an activity trail. — [Atlassian Support](https://support.atlassian.com/rovo/docs/generate-code-from-a-work-item-in-jira/); [GitHub Docs, Linear](https://docs.github.com/en/copilot/how-tos/use-copilot-agents/coding-agent/integrate-coding-agent-with-linear)
- **Definitions of ready and done:**
  - Ready: Atlassian's readiness checker scores items against a team's "definition of ready".
  - Done: GitHub measures whether review comments were addressed when the PR merges.
  - Done: Stripe's minion output must pass lints and selected CI and be reviewed by another engineer. — [Atlassian readiness checker](https://www.atlassian.com/it/software/rovo/use-cases/agent-readiness-checker); [GitHub changelog 2026-11-05](https://github.blog/changelog/2026-11-05-usage-metrics-api-adds-code-review-details-and-addressed-rate); [Stripe](https://stripe.dev/blog/minions-stripes-one-shot-end-to-end-coding-agents)

### Inferences
- The dominant pattern is chained specialized agents linked by artifacts (ticket, spec, PR, CI check, issue), not one super agent. Each handoff object is something a human can review.
- Gates that are enforced by the platform (GitHub's requester-cannot-approve and approve-and-run-workflows rules, Jira Coding Agent's no-merge) are more reliable than gates written in agent prompts. This matches the repo rule that guarantees belong in deterministic code.
- Spec approval exists as a gate only in spec-driven methods (AI-DLC, Spec Kit, Kiro). Tracker-to-PR products (Jira Coding Agent, Copilot via Jira or Linear) have no plan-approval step, so PR review is the first human checkpoint.

### Gaps
- No primary source found for a formal agent definition of done that covers deploy (for example, "merged + deployed + SLO healthy").
- No documented traceability chain that extends past the PR to deployment and incident in a single tool.
- GitHub Universe 2026 announcements (if any) were not found.

## 7. Organizations that documented the whole chain, and measured results

### Takeaway
No organization has published an audited ticket-to-production chain with outcome metrics across all stages. The best documented partial chains are:
- Stripe Minions (Slack or ticket to merged PR, about 1,300 agent PRs merged per week, all human-reviewed).
- Atlassian (Jira to PR to AI review, with a 30.8% cycle-time reduction measured in a paper).
- AWS AI-DLC (a method with gates, no figures).
- OpenAI Symphony (Linear to landed PR, +500% for some teams, vendor).
- Microsoft's SRE-agent-to-Copilot loop (demos).

Independent measurements (DORA 2025, METR) are more cautious: throughput is up but instability is rising, and experienced developers were slower in a controlled trial.

### Cited Findings
- **Stripe Minions** (2026-02-09 and part 2, February 2026):
  - Entry from Slack (most common), CLI, web, or internal tools; flaky-test tickets have a "start a minion" button.
  - Runs in isolated devboxes cut off from production and the internet.
  - More than 1,000 merged PRs per week are entirely minion-written in part 1, rising to more than 1,300 in part 2. They are human-reviewed and contain no human-written code.
  - Stripe has not published an ROI method. — [Stripe part 1](https://stripe.dev/blog/minions-stripes-one-shot-end-to-end-coding-agents); [Stripe part 2](https://stripe.dev/blog/minions-stripes-one-shot-end-to-end-coding-agents-part-2)
- **OpenAI Symphony:** some OpenAI teams saw landed PRs rise 500% in the first three weeks (vendor, 2026-04). — [OpenAI](https://openai.com/index/open-source-codex-orchestration-symphony)
- **Cognition / Devin:**
  - Internally, 659 Devin PRs merged in one week versus 154 in the best week of 2025 (vendor).
  - Merge rate 67%, up from 34%, in the 2025 year in review (vendor).
  - Independent count on public GitHub: 60.3% merged (38,374 of 63,599), 2026-06-22 to 2026-08-16. — [Cognition blog](https://cognition.ai/blog/how-cognition-uses-devin-to-build-devin); [Cognition 2025 review](https://cognition.ai/blog/devin-annual-performance-review-2025); [amplifying.ai](https://amplifying.ai/coding-agents/devin)
- **Atlassian:** Jira (readiness checker), then Jira Coding Agent, then a PR, then RovoDev Code Reviewer. Measured result for the review stage: median PR cycle time down 30.8% (arXiv paper). — [arXiv 2601.01129](https://arxiv.org/abs/2601.01129v2); [Atlassian Support](https://support.atlassian.com/rovo/docs/generate-code-from-a-work-item-in-jira/)
- **AWS AI-DLC:** a methodology covering Inception, Construction and Operations with human approvals at each gate. It reports no quantitative results; AWS only says its principles are "validated by all engineering teams we've engaged". — [AWS DevOps blog 2025-11-29](https://aws.amazon.com/blogs/devops/open-sourcing-adaptive-workflows-for-ai-driven-development-life-cycle-ai-dlc)
- **Microsoft:** Azure SRE Agent (internal figures in Q5) plus a handoff to Copilot cloud agent through GitHub issues, shown in demos. — [Microsoft Tech Community](https://techcommunity.microsoft.com/blog/appsonazureblog/announcing-general-availability-for-the-azure-sre-agent/4500682)
- **Factory:** one secondary source claims customers saved 550,000 engineering hours, and one case went from 4-month migrations to 3.5 days. Neither is verified. — [yespress.io](https://yespress.io/factory); [ZenML LLMOps database](https://www.zenml.io/llmops-database/enterprise-autonomous-software-engineering-with-ai-droids)
- **Independent, DORA 2025** (about 5,000 respondents, survey June–July 2025): AI adoption now improves delivery throughput but is still associated with **more instability**, and developer trust remains low. — [DORA report PDF](https://services.google.com/fh/files/misc/2025_state_of_ai_assisted_software_development.pdf); [InfoQ](https://www.infoq.com/news/2025/09/dora-state-of-ai-in-dev-2025)
- **Independent, METR randomized trial** (July 2025, early-2025 tools: Cursor Pro with Claude 3.5/3.7):
  - 16 experienced open-source developers, 246 tasks; allowing AI made tasks take 19% longer.
  - Developers had expected a 24% speedup and afterwards believed they had been 20% faster.
  - Older tools, so this is a dated result. — [arXiv 2507.09089](https://arxiv.org/pdf/2507.09089)

### Inferences
- Published "results" mostly measure throughput (PRs merged, cycle time). None of the end-to-end cases reports change-failure rate or incidents caused by agent PRs. DORA's finding that instability is rising is the counterweight.
- Every documented case keeps a human reviewer at merge. The verified "autonomy" stops at a reviewed PR. Deploy and remediation stay under human or pipeline control.

### Gaps
- No organization was found publishing a full ticket-to-deploy chain with change-failure rate or rollback rate for agent-written changes.
- No independent audit found of Stripe's, OpenAI's or Factory's figures.
- No Pragmatic Engineer, LeadDev or Latent Space practitioner write-up was retrieved in this pass. A LeadDev article, "AI coding agents are now the default", appeared in results but was not read: https://leaddev.com/ai/ai-coding-agents-are-now-the-default-what-comes-next
