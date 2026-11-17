# Organizational adoption of AI-assisted software development at scale: governance, standardization vs autonomy, maturity, measurement (as of 2026-11-14)

Reading conventions for the report writer:
- **[PRIMARY]** = I read the page from the publisher itself. **[SECONDARY]** = I saw it only in search summaries or third-party write-ups, so verify before quoting.
- **[PERCEPTION]** = survey or self-report. **[TELEMETRY]** = measured from systems (git, CI, issue trackers, incidents).
- **[OLDER]** = evidence from before 2025, or a 2025 item superseded by 2026 data.
- Most measurement sources are vendors (DX, Faros, LinearB, Jellyfish) that sell AI-impact analytics. Their incentive is to show that measurement gaps exist.

---

## 1. DORA 2025 "State of AI-assisted Software Development", the DORA AI Capabilities Model, the "amplifier" finding, platform engineering, and 2026 follow-ups

### Takeaway
DORA's central 2025 finding is that AI is an amplifier. It does not automatically improve delivery: it magnifies whatever organizational strengths or dysfunctions are already there. The seven-capability model says AI's payoff depends on foundations (a clear AI stance, data, version control, small batches, user focus, internal platforms) more than on the tools. DORA's 2026 follow-up is an ROI report, not a new State-of survey. It frames adoption as a J-curve: productivity dips first, partly because of a "verification tax", before gains appear.

### Cited Findings
**2025 State of AI-assisted Software Development report (published Sept 2025)**
- Sample: nearly 5,000 technology professionals worldwide, plus more than 100 hours of qualitative interviews. The full report is about 142 pages. [PERCEPTION] [PRIMARY: InfoQ coverage] — [InfoQ, Sept 2025](https://www.infoq.com/news/2025/09/dora-state-of-ai-in-dev-2025/)
- About 90% of respondents use AI at work. More than 80% believe AI increased their productivity, and 59% see a positive effect on code quality. Writing new code is the most common use: 71% of code writers use AI for it. [PERCEPTION] — [InfoQ, Sept 2025](https://www.infoq.com/news/2025/09/dora-state-of-ai-in-dev-2025/)
- AI adoption now has a positive relationship with delivery throughput, but delivery instability continues to rise. InfoQ gives no coefficient for either. — [InfoQ, Sept 2025](https://www.infoq.com/news/2025/09/dora-state-of-ai-in-dev-2025/)
- Platform engineering: 90% of organisations have adopted internal platforms, and 76% have dedicated platform teams. These are platform-adoption figures, not AI-adoption figures. — [InfoQ, Sept 2025](https://www.infoq.com/news/2025/09/dora-state-of-ai-in-dev-2025/)
- The report defines seven team archetypes, or performance profiles, from a cluster analysis. Coverage names only two, "harmonious high-achievers" and teams facing "foundational challenges". — [InfoQ, Sept 2025](https://www.infoq.com/news/2025/09/dora-state-of-ai-in-dev-2025/)
- Trust: sources conflict on where the figure that only 3% of developers report "high trust" in AI output comes from. InfoQ attributes it, with 46% distrust and 33% trust, to the 2025 Stack Overflow Developer Survey, not to DORA. Some secondary summaries attribute it to DORA. Treat it as a Stack Overflow figure. — [InfoQ, Sept 2025](https://www.infoq.com/news/2025/09/dora-state-of-ai-in-dev-2025/)
- InfoQ revisited the 2025 report in March 2026. It frames AI as a "multiplier" of existing engineering conditions and platform engineering as a "critical enabler": standardized environments, pipelines and infrastructure give AI a predictable ecosystem. It closes with the line that AI "will not fix broken engineering systems". — [InfoQ, 17 Mar 2026](https://infoq.com/news/2026/03/ai-dora-report/)

**DORA AI Capabilities Model (Google Cloud blog, 23 Sept 2025) [PRIMARY]**
The seven capabilities, each with the outcome DORA says it amplifies:
1. **Clear and communicated AI stance**: expectations, support for experimentation, and permitted tools. It amplifies AI's effect on individual effectiveness and organizational performance and reduces friction. What matters is that the stance is clear, not what the policy says. — [Google Cloud blog, 23 Sept 2025](https://cloud.google.com/blog/products/ai-machine-learning/introducing-doras-inaugural-ai-capabilities-model)
2. **Healthy data ecosystems**: internal data that is high-quality, accessible and unified. It substantially amplifies AI's effect on organizational performance. — same source
3. **AI-accessible internal data**: AI tools connected to internal sources. It boosts individual effectiveness and code quality. — same source
4. **Strong version control practices**: frequent commits amplify AI's effect on individual effectiveness, and frequent use of rollback boosts the performance of AI-assisted teams. — same source
5. **Working in small batches**: amplifies AI's effect on product performance and reduces friction. — same source
6. **User-centric focus**: amplifies AI's effect on team performance. Without it, AI adoption can *harm* team performance. — same source
7. **Quality internal platforms**: AI's effect on organizational performance is amplified where quality internal platforms exist. DORA recommends platforms that provide "guardrails and shared capabilities" so the benefits scale securely. — same source
- The full Capabilities Model report on dora.dev (last updated 25 Nov 2025) covers, for each capability, implementation strategies, starter tactics and ways to monitor progress. — [dora.dev capabilities model](https://dora.dev/ai/capabilities-model)
- Google also published a follow-up post on applying the model, titled "From adoption to impact: putting the DORA AI Capabilities Model to work". I did not read it. — [Google Cloud blog](https://cloud.google.com/blog/products/ai-machine-learning/from-adoption-to-impact-putting-the-dora-ai-capabilities-model-to-work)

**2026 follow-up: "The ROI of AI-assisted Software Development"**
- dora.dev lists this as its latest report. It describes a "practical framework" for AI adoption that covers the initial productivity dip of a rollout and offers calculations and conversation starters for budget discussions. The page gives no publication date. [PRIMARY] — [dora.dev](https://dora.dev/); report at [cloud.google.com](https://cloud.google.com/resources/content/dora-roi-of-ai-assisted-software-development)
- A third-party summary (Kodus, 24 Jul 2026) describes a J-curve: a temporary dip from learning the tools, changing workflows, reviewing AI code and added pressure on tests and approvals. According to the summary, DORA calls part of this cost the "verification tax". The ROI model ties returns to throughput *and* instability, with the goal of more throughput without more instability. [SECONDARY] — [Kodus, 24 Jul 2026](https://kodus.io/en/dora-accelerate-state-of-devops/)
- The summary also reports the report's illustrative calculator, which the summarizer says is *not* a benchmark. Inputs: 500 technical staff, a 12.5% net time gain (about 1 h/day), a 15% productivity dip for 3 months, and change failure rate rising from 5% to 6%. Outputs: $11.6M annual value, $8.4M first-year investment, 39% ROI, payback in about 8 months. [SECONDARY] — [Kodus, 24 Jul 2026](https://kodus.io/en/dora-accelerate-state-of-devops/)
- Another secondary source also describes the J-curve warning: productivity dips first because of the learning curve and the extra review burden. — [i-scoop](https://www.i-scoop.eu/ai-developer-productivity/)
- A QCon London talk (March 2026) is titled "AI amplifier: scale high performance, not dysfunction". This shows the framing has become mainstream among practitioners. I did not read the talk content. — [QCon London 2026](https://qconlondon.com/presentation/mar2026/ai-amplifier-scale-high-performance-not-dysfunction)

**Contradiction to flag**
- Faros AI's Q2 2026 telemetry report claims engineering maturity does *not* protect high performers from AI-driven quality decline, and presents this as contradicting DORA 2025. [TELEMETRY, vendor] — [Faros AI, Acceleration Whiplash (Q2 2026)](https://www.faros.ai/research/ai-acceleration-whiplash)
- [OLDER] DORA 2024 reportedly linked higher AI adoption to a 7.2% reduction in delivery stability alongside a small code-quality gain. I saw this only in secondary coverage and did not verify it against the DORA 2024 primary. — [DevClass coverage, Feb 2025](https://www.devclass.com/ai-ml/2025/02/20/ai-is-eroding-code-quality-states-new-in-depth-report/1626250)

### Inferences
- DORA's model gives a central enablement or platform team a defensible scope. Capabilities 1, 2, 3 and 7 (stance, data ecosystem, AI-accessible internal data, platform) are naturally owned centrally. Capabilities 4, 5 and 6 (version control discipline, small batches, user focus) are team practices that a center can measure and coach but not impose.
- The "amplifier" finding argues against forcing one AI workflow on all teams. Teams with weak foundations (large batches, poor tests) get worse with more AI, so for them the first move is the foundations, not more AI.
- The 2026 ROI framing (J-curve, verification tax) means adoption programs should budget for a dip of about one quarter and judge success on throughput *and* instability together, not on time saved.

### Gaps
- I could not open the 2026 ROI report itself. Its date, sample and method, and whether it contains new survey data, are unconfirmed. The details above come from third-party summaries.
- I found no "2026 State of AI-assisted Software Development" survey. If DORA released one in autumn 2026, the searches did not surface it.
- I could not obtain the effect sizes per capability or the names of all seven team archetypes; they are only in the full PDF.

---

## 2. Measurement: DX (AI Measurement Framework, Core 4, AI-authored code share, time saved), LinearB, Jellyfish, Faros, GitClear

### Takeaway
By late 2026 adoption is close to universal: above 90% in DX's data. Self-reported time savings have roughly doubled, from about 3.6 h/week in late 2025 to 4–6 h/week by mid-2026. Telemetry, however, shows modest delivery gains at company level: in DX's longitudinal sample, PR throughput rose by a median 7.76%. It also shows clear stress downstream: bigger PRs, review queues, and in Faros's data more bugs and incidents. The consistent practitioner advice is to measure utilization, impact and cost together, at team rather than individual level, and against flow and stability rather than "% of code written by AI".

### Cited Findings
**DX AI Measurement Framework [PRIMARY: DX blog and PDF]**
- The framework has three layers that must be read together: utilization, impact and cost. DX warns that tracking one layer alone is misleading. — [DX guide](https://getdx.com/blog/ai-measurement-framework-guide/); [DX framework PDF](https://getdx.com/uploads/ai-measurement-framework.pdf)
- Utilization metrics: daily and weekly active users by team and role, the share of PRs that are AI-assisted, the share of committed code that is AI-generated, and tasks assigned to agents. Impact metrics include time savings and change failure rate. Cost metrics: AI spend in total and per developer, net time gained (time saved minus spend), and an "AI hourly rate" (human-equivalent hours divided by AI spend). — [DX: how to measure AI impact](https://getdx.com/blog/how-to-measure-ai-impact-engineering-team/)
- DX's own caveats: AI-authored code share is mostly self-reported. Acceptance-rate metrics are flawed because accepted AI code is often later edited or deleted. Over-emphasizing "% of code written by AI" without tying it to outcomes misleads. — [DX: how to measure AI impact](https://getdx.com/blog/how-to-measure-ai-impact-engineering-team/)
- Microsoft's usage definitions, reported by DX: daily = 4+ days a week, weekly = 1–2 days a week, monthly = 1–2 days a month. DX also recommends tracking people who tried a tool and stopped using it for over a month. — [DX newsletter, 23 Apr 2025](https://newsletter.getdx.com/p/driving-ai-tool-adoption-lessons-from-microsoft) [OLDER, 2025]

**DX quarterly data series (vendor; mixes self-report and telemetry)**
- Q4 2025: about 3.6 h/week saved and 22% of merged code AI-authored. Sources describe the sample differently, as 135,000+ developers across about 425 organizations or as about 34,491 developers across 248 companies. [PERCEPTION] [SECONDARY] — [DX Q4 2025 report PDF](https://getdx.com/uploads/ai-assisted-engineering-q4-impact-report.pdf)
- Q1 2026, from a DX deck presented at LeadDev LXD (June 2026) [PRIMARY: I read the slides]:
  - Sample: 190,000 developers at 460+ companies, engineering orgs of 50 to 10,000 people, headquartered in North America, LatAm, Europe and APAC.
  - Adoption above 93%. Regular AI users save 4.7 h/week. 27.4% of merged code is AI-authored. Daily AI users ship 60% more PRs.
  - — [DX deck, LeadDev LXD 2026](https://leaddev.com/wp-content/uploads/2026/06/LXD3-2026-AI-in-the-SDLC.pdf), citing [DX Q1 2026 report](https://getdx.com/uploads/ai-assisted-engineering-q1-impact-report.pdf)
  - Quality effects are modest on average and vary widely between companies. Change Confidence: +2.6 points on average (n=19,251 devs). Code Maintainability: +2.2 points (n=20,012). Change failure rate: −0.11 points on average (61 companies), ranging from 1.77 points better to 1.07 points worse depending on the company. — same deck
  - **[TELEMETRY]** A longitudinal study from Nov 2024 to Feb 2026 used a random sample of 400+ companies, excluding firms with PR-throughput incentives and those with recent M&A, IPO or regulatory changes. Weighted PR throughput rose by a **median 7.76%** (average 13.1%). The slide headlines: "Productivity gains more modest than expected" and "Non-AI factors still outweigh AI benefits". — same deck; see also [DX news: impact more modest than expected](https://getdx.com/news/new-data-ais-impact-on-engineering-velocity-is-more-modest-than-expected/)
  - Also from the deck: "Shadow AI can't be ignored". Engineering managers ship 4x more code. 75% of designers and PMs also use AI code assistants. Junior engineers use AI the most. Staff+ and junior engineers save the most time. — same deck
  - Inconsistency: other DX Q1 pages give 3.9 h/week rather than 4.7. The figures may cover different populations (all users vs "regular" users). DX describes the 27.4% as self-reported, with a system-based measure planned. [SECONDARY] — [DX Q1 impact report page](https://getdx.com/report/ai-assisted-engineering-q1-impact-report/)
- Q2 2026, DX newsletter of 22 Jul 2026 [PRIMARY, teaser of a gated report]:
  - Sample "500+ organizations", with no developer count given. Adoption above 90%.
  - AI-authored code went "from 34% in Q1 2026 to 52% in Q2 2026". The measurement method is not stated, and the Q1 baseline of 34% conflicts with the 27.4% above, which suggests a change of method.
  - AI users save an estimated 4–6 h/week. Median PR size "nearly doubled".
  - DXI fell from 67 to 65 over four quarters. Code Maintainability rose 3.8% and Change Confidence fell 6.1% versus Q1. The innovation ratio has stayed flat, meaning saved time is not reaching new-feature work.
  - Median quarterly AI spend per organization went from about $1.5K to about $44K over four quarters (about 28x in the tech sector).
  - — [DX newsletter, 22 Jul 2026](https://newsletter.getdx.com/p/the-state-of-ai-impact-in-engineering)
- DX's 2026 analysis reportedly describes a "net-zero" dynamic: coding time saved is consumed by review and remediation. [SECONDARY] — [DX: AI accelerates output, not innovation](https://getdx.com/blog/ai-accelerates-output-not-innovation/)

**DX Core 4**
- Not verified in this session; see Gaps.

**Faros AI [TELEMETRY, vendor]**
- "AI Productivity Paradox" (July 2025) [OLDER]: telemetry from 10,000+ developers in 1,255 teams. High-AI teams completed 21% more tasks and merged 98% more PRs, but PR review time rose 91%, and there was no measurable gain at company level. [SECONDARY for the 91% figure] — [Faros AI Productivity Paradox 2025](https://www.faros.ai/blog/ai-productivity-paradox-report-2025)
- "The Acceleration Whiplash", AI Engineering Report Q2 2026 [PRIMARY: landing page]:
  - Method: two years of telemetry from 22K developers in 4K teams, comparing high vs low AI adoption *within the same organizations*.
  - Throughput: epics completed +66.2%, task throughput +33.7%, PR merge rate +16.2%, but **deployments per week −11.7%**.
  - Quality: PR size +51%, bugs per PR +28.7%, bugs per developer +54%, **incidents per PR +242.7%**, monthly incidents +57.9%, median review time 5x, code churn +861%.
  - Adoption context: 60% of developers use at least one AI tool weekly, 80% of teams exceed 50% weekly active users, and 25% of PRs are reviewed by an AI agent.
  - — [Faros AI, Q2 2026](https://www.faros.ai/research/ai-acceleration-whiplash)
  - A Q3 2026 Faros report, "The Speed Trap", exists; I did not read it. — same page

**LinearB 2026 Software Engineering Benchmarks [TELEMETRY, vendor; published around Dec 2025]**
- Sample: about 8.1M PRs from 4,800 teams. AI-generated PRs had a **32.7% acceptance rate vs 84.4% for manual PRs**, where acceptance means merged within 30 days. Among elite teams the rates are about 71% for AI PRs vs above 95% for manual ones. AI PRs wait **4.6x longer** before review but are reviewed 2x faster once picked up. [SECONDARY: LinearB pages] — [LinearB 2026 Benchmarks](https://linearb.io/resources/engineering-benchmarks-report); [PDF](https://assets.linearb.io/image/upload/v1765300694/resources/LinearB_2026_Software_Engineering_Benchmarks_Report.pdf)
- In a separate LinearB table of about 2.7M PRs, PRs written by autonomous agents are 4.7% of PRs in the heaviest-AI band and 0.1% in the lightest. [SECONDARY] — [LinearB AI productivity gap](https://linearb.io/resources/ai-engineering-productivity-gap)

**Jellyfish [vendor]**
- State of Engineering Management 2026: 636 engineering leaders, surveyed March 2026. 64% report at least a 25% velocity or productivity gain from AI. [PERCEPTION] [SECONDARY] — [Jellyfish SEMR 2026](https://jellyfish.co/2026-state-of-engineering-management/)
- Telemetry from 1,000+ companies, 200,000 engineers and 37M PRs: top AI adopters see 1.8x PR throughput, and autonomous agents generate 21% of PRs for those teams. [TELEMETRY] [SECONDARY] — [Jellyfish newsroom](https://jellyfish.co/newsroom/jellyfish-reveals-ais-real-impact-on-engineering-teams/)
- The H1 2026 State of AI in Software Engineering covers 130,000+ developers in 670 companies, under the theme "exploding spend, diverging returns". Leaders' focus is shifting "from AI adoption to AI accountability", including token costs. [SECONDARY] — [Jellyfish State of AI in SE](https://jellyfish.co/resources/state-of-ai-in-software-engineering-report/); [Jellyfish blog](https://jellyfish.co/blog/2026-engineering-leaders-shifting-from-ai-adoption-to-ai-accountability/)

**GitClear [TELEMETRY; OLDER: data from 2020–2024, published early 2025]**
- Based on 211M changed lines. Code blocks with 5+ duplicated lines rose 8x during 2024. Moved lines, a proxy for refactoring, fell 39.9%, from about 25% to under 10% of changes. 2024 was the first year copy/pasted lines exceeded moved lines. [SECONDARY] — [DevClass, Feb 2025](https://www.devclass.com/ai-ml/2025/02/20/ai-is-eroding-code-quality-states-new-in-depth-report/1626250); [LeadDev](https://leaddev.com/software-quality/how-ai-generated-code-accelerates-technical-debt)

**Other perception data**
- Atlassian State of DevEx 2026: developers saving more than 10 h/week fell from 68% in 2025 to about a quarter in 2026. Reported via a secondary summary; not verified. [PERCEPTION] [SECONDARY] — [i-scoop summary](https://www.i-scoop.eu/ai-developer-productivity/)
- McKinsey: in a study of about 300 public companies, the top fifth reported 16–30% gains in team productivity, customer experience and time to market, and 31–45% in software quality. These are self-reported and correlational, and the publication date is unverified. [PERCEPTION] [SECONDARY] — [McKinsey, Unlocking the value of AI in software development](https://www.mckinsey.com/industries/technology-media-and-telecommunications/our-insights/unlocking-the-value-of-ai-in-software-development)

### Inferences
- **Perception vs telemetry gap.** The perception surveys (DORA: >80% feel more productive; Jellyfish: 64% report ≥25% gains) are far more positive than the longitudinal telemetry (DX: +7.76% median PR throughput; Faros: deployments down 11.7% with incidents up). A measurement program should not use self-reported time saved as its success metric.
- **Vendors converge on where the bottleneck moved:** review (LinearB's 4.6x wait, Faros's 5x review time, DX's PR size doubling) and stability (Faros incidents, DORA instability). A central team's measurement should therefore track PR size, review wait, change failure rate and incidents next to adoption, which matches the DORA ROI framing.
- **AI-authored code share is unreliable as a KPI.** DX's own figures jump between methods (27.4% vs 34% for the same quarter), and DX itself calls the metric misleading in isolation.
- **Cost is now a first-class dimension:** DX's 28x spend increase and Jellyfish's "accountability" shift. Budget per developer and net time gained per dollar belong in the dashboard.

### Gaps
- DX Core 4: I did not fetch its primary definition. From prior knowledge it is four dimensions (speed, effectiveness, quality, business impact), with key metrics such as diffs per engineer, DXI, change failure rate and % time on new capabilities. Verify at getdx.com before citing.
- The Faros Q3 2026 report ("The Speed Trap") and DX Q3 2026 data were not read. Newer numbers may exist.
- I found no GitClear 2026 update.
- I did not verify the METR 2025 randomized trial or newer RCTs in this session.
- Exact sample definitions for DX Q2 2026 (developers, self-report vs system) are behind the gated report.

---

## 3. Platform engineering applied to AI: golden paths for agents, internal developer platforms, central prompt and skill libraries

### Takeaway
Practitioners and researchers converge on the platform team becoming the delivery vehicle for AI. It provides paved paths, guardrails, data and context access (MCP), shared instruction files distributed through service templates, and cost control. DX explicitly calls "AI readiness" the "new mandate" for platform teams and notes that it is essentially good developer experience. Thoughtworks moved curated, repository-anchored shared instructions to "Adopt" in April 2026, while cautioning against instruction bloat.

### Cited Findings
- DORA capability 7: the effect of AI on organizational performance is amplified by quality internal platforms that provide "guardrails and shared capabilities". — [Google Cloud blog, 23 Sept 2025](https://cloud.google.com/blog/products/ai-machine-learning/introducing-doras-inaugural-ai-capabilities-model). 90% of organisations have internal platforms and 76% have dedicated platform teams. — [InfoQ, Sept 2025](https://www.infoq.com/news/2025/09/dora-state-of-ai-in-dev-2025/)
- The DX deck at LeadDev (June 2026) lists "The new mandate for Platform Engineering teams" [PRIMARY]:
  - drive "AI readiness" initiatives
  - data-driven AI rollout and optimization
  - "Measure for impact, not for activity or speed"
  - paved paths and guardrails for AI engineering
  - AI infrastructure cost optimization
  - It defines AI readiness as clear documentation, simple data structures, modular code, fast and reliable local and CI feedback, and non-flaky test suites, adding "we used to call it 'good DevEx'".
  - — [DX deck, LeadDev LXD 2026](https://leaddev.com/wp-content/uploads/2026/06/LXD3-2026-AI-in-the-SDLC.pdf)
- Internal-platform case studies from the same deck, as cited by DX:
  - Morgan Stanley "DevGen.AI": agents read legacy code and generate specs, saving over 280,000 developer hours a year.
  - Faire "Fairey" review agent: about 3,000 reviews a week on every GitHub PR.
  - Spotify incident-management agent platform: handles 90% of incidents.
  - Canva PRD generator connected to internal docs, Jira and Figma via MCP.
  - Zapier internal agents for standups and onboarding: new engineers productive within 2 weeks.
  - These are company claims relayed by DX. — same deck
- Thoughtworks Technology Radar Vol. 34 (April 2026) puts **"curated shared instructions for software teams"** in **Adopt**; the entry first appeared Nov 2025. Its recommendations:
  - treat AI guidance as a team asset, not a personal workflow
  - commit instruction files such as AGENTS.md to the repository
  - put CLAUDE.md, AGENTS.md or .cursorrules in the template used to scaffold new services, so "the template becomes a powerful distribution mechanism"
  - keep general-purpose prompt libraries separate from repository-specific configuration
  - Thoughtworks also lists anchoring agents to a live, compilable reference application as the source of truth.
  - [PRIMARY: Radar entry via search] — [Thoughtworks Radar](https://www.thoughtworks.com/radar/techniques/curated-shared-instructions-for-software-teams)
- The same Radar volume reportedly places "agent instruction bloat" in Caution. It also notes that tools disagree on file precedence: Claude Code prefers CLAUDE.md, Codex reads AGENTS.md. [SECONDARY] — [Tenki blog](https://tenki.cloud/blog/agents-md-shared-instructions-config); [Radar Vol. 34 digest](https://agentic-ai.readthedocs.io/en/latest/AgenticTechStack/thoughtworks-radar-vol34/)
- Docusign is deploying a **Skill Marketplace** where engineers package, publish and discover prompts, agent configurations and automated skills across the company. Status and usage are not given. [PRIMARY] — [Docusign engineering blog](https://www.docusign.com/blog/how-we-drove-ai-adoption-across-docusign-engineering-without-mandating-it)
- Shopify reportedly standardized the infrastructure layer *beneath* all AI tools rather than mandating a single tool. [SECONDARY] — [BVP Atlas, Inside Shopify's AI-first engineering playbook](https://www.bvp.com/atlas/inside-shopifys-ai-first-engineering-playbook)
- Practitioner views on golden paths for agents, all [SECONDARY, practitioner or vendor blogs]:
  - Mature platforms treat agents as another user persona, with RBAC, quotas and policies, and define "agent golden paths". — [Spacelift](https://spacelift.io/blog/ai-in-platform-engineering); [DuploCloud](https://duplocloud.com/blog/agentic-internal-developer-platform/)
  - A service template can be ready for humans yet "invisible" to agents if it lacks AGENTS.md, agent configuration and MCP registration. — [Codex CLI for platform teams, Jun 2026](https://codex.danielvaughan.com/2026/06/13/codex-cli-platform-engineering-golden-paths-idp-agent-ready-templates/)
  - Counterpoint: standard templates risk becoming "golden cages", and the internal developer platform must guard against agent mistakes as robustly as against human ones. — [DZone](https://dzone.com/articles/platform-engineering-ai-agents)
- A blog attributes to a "CNCF Platform Engineering Survey 2026" the finding that 73% of platform teams have integrated AI assistants into at least one workflow. Unverified; I found no primary CNCF source. — [Nitor Infotech](https://www.nitorinfotech.com/blog/how-to-build-an-ai-ready-internal-developer-platform-a-platform-engineering-guide-for-2026/)
- LeadDev ran a piece titled "AI made platform engineering strategic again". I did not read its content. — [LeadDev](https://leaddev.com/technical-direction/ai-made-platform-engineering-strategic-again)

### Inferences
- A defensible split of ownership:
  - The **central platform team owns** the substrate: approved models and tools, identity and permissions for agents, MCP and context connectors to internal data (DORA capabilities 2–3), sandboxes, CI guardrails, telemetry, cost, the template that seeds instruction files, and a shared skill or prompt registry.
  - **Teams own** repo-specific instructions, the choice of workflows on top of the substrate, and their delivery practices.
  - Thoughtworks' separation of general prompt libraries from repo-specific configuration, Shopify's "standardize infrastructure, not the tool", and Docusign's marketplace all point the same way.
- Distributing instruction files through scaffolding templates is the main lever for standardization. It needs an update path for existing repositories and a check against bloat.
- The "golden cage" risk suggests golden paths for agents should stay optional and paved, not mandatory gates, except for security and compliance guardrails.

### Gaps
- I found no platformengineering.org primary content, no PlatformCon or CNCF talk transcripts, and no Backstage-specific data on exposing AI tools or a skills catalog. Search results were dominated by vendor blogs.
- I found no primary survey quantifying how many organizations run a central prompt or skill library.

---

## 4. Maturity models for AI-assisted engineering: levels and transitions

### Takeaway
There is no consensus maturity model. The landscape mixes three kinds of model:
- **Capability-based** models of organizational preconditions: DORA's seven capabilities with seven team archetypes; Gartner's March 2026 "Maturity Model for AI-Native Software Engineering", whose levels are behind a paywall.
- **Individual or practice-level** autonomy ladders: Steve Yegge's eight levels, from no AI to building your own agent orchestrator.
- **Methodology** models: AWS AI-DLC's three phases with "mob" rituals, which has no published adoption stages.

Real rollouts, such as Docusign's, follow a de facto sequence: pilot, broad access, champions and enablement, then agentic workflow automation.

### Cited Findings
- **Gartner**:
  - Gartner published a "Maturity Model for AI-Native Software Engineering" on 12 March 2026 for assessing maturity gaps and building an AI implementation roadmap. I could not see the level definitions. — [Gartner document 7586633](https://www.gartner.com/en/documents/7586633)
  - Gartner predicts 60% of organizations will adopt smaller software engineering teams at scale by 2029, up from 15% in 2026. It warns that organizations using AI to eliminate junior roles by 2028 will weaken their talent pipeline. [SECONDARY: press release returned 403, figures from search summaries] — [Gartner press release, 7 Jul 2026](https://www.gartner.com/en/newsroom/press-releases/2026-07-07-gartner-predicts-60-percent-of-organizations-will-adopt-smaller-software-engineering-teams-by-2029); [DevOps Digest](https://www.devopsdigest.com/node/14571)
  - [OLDER, 2024] Earlier predictions: 75% of software engineers will use AI coding assistants by 2028, and 80% will need to upskill by 2027. — [HR Dive](https://www.hrdive.com/news/software-engineers-upskilling-generative-AI-Gartner/728988/); [ITPro](https://www.itpro.com/software/software-engineers-are-in-for-a-rough-ride-as-ai-adoption-ramps-up-80-percent-will-be-forced-to-upskill-by-2027-as-the-profession-is-transformed)
  - A secondary site claims "80% by 2030" smaller teams. This conflicts with the 60%-by-2029 figure and is unverified. — [DesignRush](https://news.designrush.com/ai-native-dev-teams-shrink-2030-igor-repeta-empat)
- **Steve Yegge's "eight levels"**, from the "Welcome to Gas Town" post of 1 Jan 2026, via secondary summaries:
  - Levels 1–4 are increasingly sophisticated IDE assistance. Levels 5–8 are coding agents.
  - The pivot is level 5, where the IDE "goes away". Level 8 is building your own orchestrator.
  - In a Pragmatic Engineer interview (11 Mar 2026), Yegge placed most engineers at levels 1–2, which he characterized as asking the IDE for suggestions and reviewing them carefully, and said he suspects they will be "left behind". He named large monoliths, roughly 0.5M to several million lines, as a blocker to enterprise agent adoption, and described a "Dracula effect" of fatigue when only high-intensity work remains.
  - He also says most developers should *not* use Gas Town.
  - — [Pragmatic Engineer, 11 Mar 2026](https://newsletter.pragmaticengineer.com/p/from-ides-to-ai-agents-with-steve); [Augment summary of the 8 levels](https://www.augmentcode.com/guides/steve-yegge-8-levels-ai-assisted-development); [O'Reilly Radar](https://www.oreilly.com/radar/steve-yegge-wants-you-to-stop-looking-at-your-code/)
- **AWS AI-DLC** (introduced July 2025; workflows open-sourced later in 2025):
  - Three phases: Inception, Construction, Operations.
  - In "Mob Elaboration", a cross-functional team validates AI-generated questions and user stories. In "Mob Construction", the team and the AI write, test and deploy code together.
  - I found no published *adoption stages*; AWS directs customers to the whitepaper, Kiro or Q Developer rules, or their account team.
  - — [AWS DevOps blog: AI-DLC](https://aws.amazon.com/blogs/devops/ai-driven-development-life-cycle); [AWS: open-sourcing adaptive workflows](https://aws.amazon.com/blogs/devops/open-sourcing-adaptive-workflows-for-ai-driven-development-life-cycle-ai-dlc)
- **DORA**: the capabilities model with seven team archetypes from cluster analysis. These are performance profiles, not linear levels. — [dora.dev capabilities model](https://dora.dev/ai/capabilities-model); [InfoQ](https://www.infoq.com/news/2025/09/dora-state-of-ai-in-dev-2025/)
- **Docusign's de facto staged rollout** (more than 1,000 engineers) [PRIMARY]:
  - Dec 2023–Jun 2024: Copilot pilot for about 20% of engineering.
  - Jun 2024: company-wide access. Adoption reached 49% with an 18% productivity gain, then **plateaued**.
  - Jun–Nov 2025: Eng AI Champions plus embedded "Multipliers". Adoption was 65% in Oct 2025 and reached a 93% active-user rate two months after Multipliers launched.
  - Dec 2025 onward: end-to-end workflow automation with internal agents. Agent-generated merged PRs went from under 1% to over 8% in about 4 months, and about 75% of new code is AI-assisted.
  - — [Docusign engineering blog](https://www.docusign.com/blog/how-we-drove-ai-adoption-across-docusign-engineering-without-mandating-it)
- **Practical adoption thresholds in vendor data**: Faros counts "80% of teams exceed a 50% weekly active user threshold". Microsoft defines daily, weekly and monthly users. — [Faros Q2 2026](https://www.faros.ai/research/ai-acceleration-whiplash); [DX newsletter](https://newsletter.getdx.com/p/driving-ai-tool-adoption-lessons-from-microsoft)

### Inferences
- Two axes are usually conflated and should be kept separate:
  - **Organizational readiness** (DORA capabilities, the Gartner model) caps what teams can safely do.
  - **Practice autonomy** (Yegge's levels, from completions to agents to orchestrated agents) describes what individuals or teams do.
- Transitions in practice are driven by plateaus. Docusign stalled at about 49% with access alone and needed a human enablement layer, then a platform and agent layer, to move. This matches the J-curve in DORA's ROI framing.
- Yegge's monolith remark and the DX "AI readiness" list both suggest codebase properties (modularity, tests, documentation) are prerequisites for moving to agent levels. That argues for gating a team's level on repository readiness, not on mandate.

### Gaps
- I could not access the level definitions of Gartner's March 2026 model.
- I found no published maturity models from Thoughtworks, GitLab, Microsoft or Anthropic in this session; they may exist but did not surface.
- I did not research SAE-style "levels of autonomy" analogies for coding agents.
- I did not open the original Yegge post, so the per-level definitions for levels 3–7 come only from secondary summaries.

---

## 5. Change management: mandates vs champions, guilds, enablement, local variation, Team Topologies

### Takeaway
Most of the evidence favors a **hybrid** approach:
- Visible executive advocacy and a clear stance, the strongest single lever in Microsoft research at about 7x more daily users.
- Peer champions embedded in teams to get past the "access-only" plateau.
- Workflow and role redesign rather than bolting tools onto unchanged processes.

Hard mandates with deadlines (Coinbase) exist but are documented only anecdotally. Several practitioners report that mandates breed shallow use. Successful organizations standardize the infrastructure and the guardrails and let teams vary the tools and workflows on top.

### Cited Findings
- **Microsoft research** (Brian Houck, interviewed by DX on 23 Apr 2025) [OLDER; sample and method not stated]:
  - Leadership advocacy makes developers about **7x** more likely to become daily users.
  - Formal training makes organizations about **20%** more likely to have most or all developers adopt.
  - Local champions make it about **22%** more likely.
  - Other recommendations: repeat the messaging every few weeks; track adoption at team level, not individual; avoid overpromising (about 30% of developers worry AI won't live up to the hype); stress that humans remain responsible for quality.
  - — [DX newsletter, 23 Apr 2025](https://newsletter.getdx.com/p/driving-ai-tool-adoption-lessons-from-microsoft)
- **Docusign** (more than 1,000 engineers) [PRIMARY]:
  - A central team of **6 "Eng AI Champions"** sets guardrails, curates practices, designs workshops and plans how AI is woven across the SDLC.
  - Embedded **"Multipliers"** (peer early adopters inside teams) help teammates through their first week, run local workshops and send friction points back to the center.
  - The friction they found: lack of dedicated experimentation time, lack of codebase-specific guidance, no structure for when prompting failed.
  - Their conclusion: "top-down corporate mandates have limits in engineering cultures". Every line is still human-reviewed before shipping.
  - — [Docusign engineering blog](https://www.docusign.com/blog/how-we-drove-ai-adoption-across-docusign-engineering-without-mandating-it)
- **Shopify** [SECONDARY]: Farhan Thawar is quoted as saying cultural adoption beats top-down mandates, even though Shopify is often cited as a mandate case. The company reportedly standardized the infrastructure layer rather than a single tool, and brought in Copilot before formal procurement. — [BVP Atlas](https://www.bvp.com/atlas/inside-shopifys-ai-first-engineering-playbook)
- **Coinbase** [SECONDARY, unverified details]: a CEO-driven mandate with about a one-week adoption deadline and reported dismissals for non-compliance (2025). I found no primary source in this session. — [dev.to commentary](https://dev.to/gabrielanhaia/coinbase-fired-engineers-who-didnt-learn-ai-in-five-days-the-industry-barely-flinched-34j7)
- LeadDev argues "AI champions are the key to engineering adoption". BVP's "AI-pilled teams" piece gives five lessons for scaling. I did not read either beyond search snippets. — [LeadDev](https://leaddev.com/ai/ai-champions-are-the-key-to-engineering-adoption); [BVP Atlas](https://bvp.com/atlas/inside-ai-pilled-engineering-teams-five-lessons-for-scaling-without-losing-the-plot)
- **McKinsey** [PERCEPTION, SECONDARY, date unverified]:
  - 57% of top performers vs 20% of bottom performers report measurable gains from hands-on workshops and one-on-one coaching.
  - About 80% of top performers link gen-AI goals to PM and developer evaluations.
  - In a separate survey of 334 product and engineering leaders, organizations that embedded AI *without changing roles or ways of working* became top accelerators only 27% of the time.
  - — [McKinsey, Unlocking the value of AI in software development](https://www.mckinsey.com/industries/technology-media-and-telecommunications/our-insights/unlocking-the-value-of-ai-in-software-development)
- McKinsey State of AI (cross-functional, not software-specific): 88% of organizations use AI in at least one function in 2025, but most are stuck in pilots. In 2026, 37% report a positive EBIT contribution from AI. — [McKinsey State of AI 2026](https://www.mckinsey.com/capabilities/quantumblack/our-insights/the-state-of-ai?highlight=2025)
- **Team Topologies**:
  - Matthew Skelton at QCon London (17 Mar 2026) framed Team Topologies as "infrastructure for agency" with AI. He argued the main obstacle to AI adoption is organizational maturity rather than technology, drew a parallel between human cognitive load and AI context windows, and warned against unbounded data access (OWASP "Excessive Agency"). — [InfoQ, Mar 2026](https://www.infoq.com/news/2026/03/ai-agency-team-topologies); [Team Topologies keynote page](https://teamtopologies.com/keynote-talks/team-topologies-as-the-infrastructure-for-agency-with-ai)
  - A claim attributed to the talk, that "80% of firms see no tangible AI benefit", is unverified.
  - The Team Topologies blog argues AI ROI depends on "stewardship" boundaries and governance for value flow. — [Team Topologies blog](https://teamtopologies.com/news-blogs-newsletters/team-topologies-for-the-ai-age-stewardship-of-value-flow)
  - A third-party analysis argues agents do not create a fifth team type; they change the composition and interaction load of the existing four. [SECONDARY] — [Rework](https://resources.rework.com/libraries/ai-future-of-work/team-topologies-for-human-plus-agent-teams)
- **DORA**: a "clear and communicated AI stance" reduces friction regardless of the policy content. Clarity on permitted tools and experimentation is itself the lever. — [Google Cloud blog](https://cloud.google.com/blog/products/ai-machine-learning/introducing-doras-inaugural-ai-capabilities-model)

### Inferences
- The best-supported operating model has three parts:
  - **Executive layer:** a clear stance and repeated advocacy (DORA capability 1, the Microsoft 7x figure).
  - **Small central enablement team, the Team Topologies "enabling team":** curates practices, guardrails and shared skills, runs workshops, and measures at team level.
  - **Embedded champions per team:** adapt practices to the local codebase and feed friction back.
- Docusign's numbers show the cost of skipping the human layer: access alone plateaued at about 49%.
- Linking AI goals to individual evaluations (McKinsey's ~80% of top performers) conflicts with Microsoft's advice not to call out individuals, and may create EU AI Act exposure (see section 6). Measure at team level and use individual data only for coaching.
- Local variation is best managed as "standardize the substrate and guardrails, let teams choose the workflow". Imposing one agent workflow on heterogeneous teams cuts against both the amplifier finding and Yegge's observation that readiness varies with codebase shape.

### Gaps
- I found no primary 2025–2026 source on the Spotify squad model applied specifically to AI adoption. Spotify appears only as an internal-platform case in the DX deck.
- I found no primary source documenting Coinbase's mandate or its measured outcome.
- I found no source confirming whether Team Topologies authors use "thinnest viable platform" specifically for AI platforms.
- I found no quantitative study comparing mandate vs champion rollouts with telemetry outcomes; the Microsoft figures lack published method and sample.

---

## 6. Governance and compliance: AI usage policies, security and legal guardrails, the EU AI Act for dev tooling, audit trails of agent actions

### Takeaway
For dev tooling, governance in 2026 rests on four pillars:
- a clear, communicated AI stance on permitted tools, data and experimentation;
- human review and accountability for shipped code;
- agent-specific security controls (least privilege, guardrails on agent *outputs* and tool calls, tamper-evident audit logs, kill-switches), anchored on OWASP's agentic and LLM risk lists;
- EU AI Act awareness.

Coding assistants are generally *not* high-risk under the Act, and most duties sit with model providers. The exposure for engineering organizations is using AI to evaluate or manage engineers, plus transparency duties. GPAI enforcement powers began on 2 Aug 2026.

### Cited Findings
- **Clear AI stance** (DORA capability 1): covers expectations, support for experimentation and permitted tools. Its value lies in clarity and communication. — [Google Cloud blog, Sept 2025](https://cloud.google.com/blog/products/ai-machine-learning/introducing-doras-inaugural-ai-capabilities-model)
- **Shadow AI** is flagged as something that "can't be ignored" in DX's Q1 2026 data, which argues for approved tools over prohibition. — [DX deck, LeadDev LXD 2026](https://leaddev.com/wp-content/uploads/2026/06/LXD3-2026-AI-in-the-SDLC.pdf)
- **Human accountability:** at Docusign, every line is reviewed and approved by a human before shipping. — [Docusign](https://www.docusign.com/blog/how-we-drove-ai-adoption-across-docusign-engineering-without-mandating-it). Microsoft research advises messaging that humans remain responsible for quality through testing. — [DX newsletter](https://newsletter.getdx.com/p/driving-ai-tool-adoption-lessons-from-microsoft)
- **OWASP Top 10 for Agentic Applications 2026** (published Dec 2025, risks ASI01–ASI10):
  - Microsoft's open-source Agent Governance Toolkit maps its controls to these risks, including a **tamper-evident audit log** for "agent untraceability". The mapping is Microsoft's own self-assessment, not a certification.
  - The sources disagree on the count (10 vs 11 risks).
  - — [Microsoft Agent Governance Toolkit, OWASP mapping](https://microsoft.github.io/agent-governance-toolkit/compliance/owasp-agentic-top10-architecture/)
- **Excessive agency:** Skelton cited OWASP LLM06 "Excessive Agency" in March 2026. — [InfoQ](https://www.infoq.com/news/2026/03/ai-agency-team-topologies). A secondary source says the 2026 OWASP LLM list moved Excessive Agency to LLM03. The numbering is unverified and conflicts with Skelton's reference. — [Fiddler AI blog](https://www.fiddler.ai/blog/artificial-intelligence-security-issues)
- **Regulated-sector practice** [SECONDARY]:
  - Organizations are moving toward explicit per-task approval, immutable audit trails and emergency kill-switches for agent tokens and sessions. — [NHI Mgmt Group](https://nhimg.org/faq/how-should-security-teams-govern-coding-agents-that-already-have-access-to-produ/)
  - A common misconfiguration is guarding user inputs but not agent-generated outputs and tool calls. — [Fiddler AI](https://www.fiddler.ai/blog/artificial-intelligence-security-issues)
- **EU AI Act timeline:** GPAI provider obligations have applied since 2 Aug 2025. The Commission's enforcement powers over GPAI providers began on **2 Aug 2026**, with fines up to 3% of global turnover or €15M. — [CSA research note, Aug 2026](https://labs.cloudsecurityalliance.org/research/csa-research-note-eu-ai-act-gpai-enforcement-20260803-csa-st/); [EU AI Act Service Desk FAQ](https://ai-act-service-desk.ec.europa.eu/en/faq); [WSGR, Aug 2026](https://www.wsgrdataadvisor.com/2026/08/eu-ai-act-enforcement-phase-begins/)
- **EU AI Act scope for dev tooling** [SECONDARY, developer-oriented guides]:
  - Standard coding assistants fall outside Annex III high-risk categories; what matters is the use case.
  - GPAI duties fall on model vendors. A company building software with agents mainly needs documentation from its upstream providers.
  - Using AI to evaluate engineers could trigger high-risk obligations (employment use case).
  - — [Developer Toolkit, EU AI Act for companies building with agents](https://developertoolkit.ai/en/org/eu-ai-act/); [Augment, EU AI Act 2026](https://augmentcode.com/guides/eu-ai-act-2026)
  - Sources conflict on high-risk timing: one dates Annex III obligations to 2 Dec 2027 after a delay. Unverified against the official text. Several blogs mis-cite transparency as "Article 52"; it is Article 50. — [SIG EU AI Act summary, updated 14 Aug 2026](https://www.softwareimprovementgroup.com/eu-ai-act-summary/)

### Inferences
- A central platform or enablement team should own the *mechanisms* of governance:
  - an approved tool and model list;
  - agent identity and least-privilege credentials;
  - output and tool-call guardrails in CI;
  - a tamper-evident log of agent actions (prompt, tool calls, diffs, approver);
  - kill-switches;
  - the vendor documentation needed for the EU AI Act.
- Teams own human review and the content of their repository rules.
- The biggest EU AI Act risk for an engineering organization is not the coding assistant itself. It is using AI telemetry to rate individual engineers. This is another reason, beyond culture, to measure AI impact at team level.
- Because DORA finds the stance's *clarity* matters more than its content, a short, published, versioned policy (what is allowed, what data may be sent, who reviews) is a low-cost, high-leverage first step for a central team.

### Gaps
- I found no primary survey data on what share of engineering organizations have a written AI usage policy or an agent audit log in 2026.
- I did not read the OWASP Agentic Top 10 primary text, so the ASI numbering and count are unconfirmed.
- I did not verify the exact Annex III high-risk application date after the 2025–2026 "digital omnibus" discussions.
- I found no source on legal and IP guardrails specific to code (license contamination, indemnities) in 2026.
