# Counter-evidence, failure modes and critiques of AI-assisted development and top-down AI SDLC frameworks (as of 2026-11-14)

Evidence-type legend used throughout: **[RCT]** randomized controlled trial; **[Field-RCT]** randomized rollout inside companies; **[Telemetry]** observational data from tools or payroll (correlational); **[Survey]** self-reported perception; **[Bench]** controlled benchmark or lab task; **[Vendor]** published by a company selling a related product; **[Opinion]** practitioner or analyst critique; **[Incident]** public post-mortem or press report. Items dated before 2025 are flagged **(OLDER)**.

## 1. Measured productivity evidence: what controlled and telemetry studies show

### Takeaway
The best-controlled evidence is mixed and moving. METR's 2025 RCT found experienced open-source developers 19% *slower* with early-2025 AI. METR's own 2026 follow-up points toward a speedup but calls its data "very weak evidence", because developers now refuse to work without AI. Telemetry (DORA, Faros) shows real gains in individual and team throughput, but those gains do not reliably reach organizational delivery, and instability, bugs and incidents rise alongside them. For juniors, an RCT shows AI-delegated learning hurts comprehension, and payroll data shows early-career developer employment falling (causality contested).

### Cited Findings

**METR RCT and its 2026 follow-up**
- [RCT] Original METR study (data Feb–Jun 2025, published Jul 2025): AI tools made experienced open-source developers take 19% longer per task (95% CI +2% to +39%) — [METR, 2026-02-24 update recap](https://metr.org/blog/2026-02-24-uplift-update/). The original paper reports 16 developers and 246 tasks. Developers forecast a ~24% speedup beforehand and still believed in a ~20% speedup afterwards, so perception was the opposite of measurement — [METR paper, arXiv 2507.09089](https://arxiv.org/abs/2507.09089) *(figures from the original paper; not re-fetched this session)*.
- [RCT] METR follow-up (started Aug 2025, published 2026-02-24): 57 developers (10 returning, 47 new), 143 repos, 800+ tasks, median 10 years of experience. Estimates: returning developers −18% time (speedup), CI −38% to +9%; new developers −4%, CI −15% to +9%. Neither is statistically clear — [METR](https://metr.org/blog/2026-02-24-uplift-update/).
- [RCT] METR distrusts the follow-up. More developers declined to take part because they would not work without AI. 30–50% said they skipped submitting tasks they did not want to do without AI. Pay was cut from $150/h to $50/h. Running several agents in parallel made time tracking unreliable. METR concludes developers are "likely more sped up" in early 2026, but calls its data "very weak evidence" for the size of that change. It is redesigning the study — [METR](https://metr.org/blog/2026-02-24-uplift-update/).
- [Survey] A secondary blog reports a METR self-report survey (Feb–Apr 2026, 349 technical workers) showing self-reported speedups. Not verified against METR directly — [Govard (secondary)](https://govard.tech/blog/ai-developer-productivity-studies/).

**Other RCTs (mostly OLDER)**
- [RCT] **(OLDER, summer 2024)** Google enterprise RCT (Paradis et al.): 96 Google engineers on one enterprise task were ~21% faster with three internal AI features (96 vs 114 minutes), with a wide CI. The authors warn the result may not transfer to other tools or periods — [arXiv 2410.12944](https://arxiv.org/abs/2410.12944) (ICSE-SEIP 2025).
- [Field-RCT] **(OLDER, experiments 2022–2023)** Cui et al.: 4,867 developers at Microsoft, Accenture and a Fortune 100 firm. Copilot access raised completed tasks (PRs/week) by 26.08% (SE 10.3%), with larger gains for less experienced developers. The tool was a GPT-3.5-era Copilot, and the outcome is volume, not delivered value — [SSRN 4945566](https://papers.ssrn.com/abstract=4945566); [MIT draft](https://economics.mit.edu/sites/default/files/inline-files/draft_copilot_experiments.pdf).
- These studies measure different things (time on one task vs PR volume) and should not be compared directly — [GetDX newsletter commentary](https://newsletter.getdx.com/p/how-much-does-ai-impact-development-speed).

**DORA 2025 (survey + modelling)**
- [Survey] DORA 2025 "State of AI-assisted Software Development": ~5,000 technology professionals, survey fielded 2025-06-13 to 2025-07-21. ~90% use AI at work, >80% believe it raised their productivity, and 59% report positive effects on code quality — [InfoQ, 2025-09-29](https://www.infoq.com/news/2025/09/dora-state-of-ai-in-dev-2025); [DORA report PDF](https://services.google.com/fh/files/misc/2025_state_of_ai_assisted_software_development.pdf).
- [Survey] AI adoption is now positively associated with delivery throughput (a reversal from 2024), but it is still associated with *rising* delivery instability. "Fail fast, fix fast" did not offset that instability — [InfoQ](https://www.infoq.com/news/2025/09/dora-state-of-ai-in-dev-2025); [RedMonk commentary, 2025-12-18](https://redmonk.com/rstephens/2025/12/18/dora2025/).
- [Survey] DORA frames AI as an amplifier: it magnifies the strengths of high-performing organizations and the dysfunctions of struggling ones. AI adoption did not reduce burnout or friction, and in some teams pressure rose because more output was expected — [InfoQ](https://www.infoq.com/news/2025/09/dora-state-of-ai-in-dev-2025).

**Faros telemetry (Vendor)**
- [Telemetry][Vendor] Faros "AI Productivity Paradox" (2025): 10,000+ developers, 1,255 teams, comparing each organization's lowest- and highest-AI-adoption periods. High-adoption teams completed ~21% more tasks and merged ~98% more PRs. Over the same comparison, PR review time rose 91%, PR size rose 154%, and bugs per developer rose 9%. The gains did not show up as company-level productivity — [Faros](https://www.faros.ai/blog/ai-productivity-paradox-report-2025); [Rob Bowley summary, 2025-08-21](https://blog.robbowley.net/2025/08/21/new-research-shows-ai-assisted-coding-isnt-moving-delivery/).
- [Telemetry][Vendor] Faros "AI Engineering Report 2026: The Acceleration Whiplash" (Q2 2026, two years of telemetry, 22,000 developers, 4,000+ teams, low vs high adoption within each org):
  - Throughput: epics completed +66.2%, task throughput +33.7%, PR merge rate +16.2%.
  - Delivery and quality: deployments per week −11.7%, code churn +861%, PR size +51%, median review time ~5x (+441.5%).
  - Defects and incidents: bugs per PR +28.7%, bugs per developer +54%, incidents per PR +242.7% (~3x), monthly incidents +57.9%.
  - Faros states that engineering maturity "is not a shield" against these effects.

  Sources: [Faros research page](https://www.faros.ai/research/ai-acceleration-whiplash); [report PDF](https://pages.faros.ai/hubfs/AI_Engineering_Report_2026_The_Acceleration_Whiplash_Faros.pdf).
- [Telemetry][Vendor] Conflict: a later Faros post (around the Q3 2026 "Speed Trap" report) reportedly says incidents per PR have "settled" at +14.5% under high adoption, vs +242.7% in April. A secondary source also claims 31% more PRs merged with no review, but that figure is not on the primary research page. Both seen only in search snippets — [Faros "Speed Trap" takeaways](https://www.faros.ai/blog/ai-speed-trap-takeaways); [dev.to secondary](https://dev.to/code-board/pr-review-time-is-up-441-the-real-cost-of-ai-accelerated-development-1ho6).

**GitClear code-quality telemetry (Vendor)**
- [Telemetry][Vendor] GitClear "AI Copilot Code Quality" 2025: 211M changed lines (2020–2024, private repos plus 25 large OSS projects). Findings:
  - ~8x rise in 2024 in five-plus-line blocks duplicating adjacent code.
  - 2024 was the first year copy/pasted lines exceeded "moved" (refactored) lines.
  - Churn rose from 3.3% (2021) to 5.7% (2024).
  - Caveats: correlational, not line-level attribution to AI, and GitClear sells measurement tooling.

  Source: [LeadDev](https://leaddev.com/software-quality/how-ai-generated-code-accelerates-technical-debt).
- [Telemetry][Vendor] Reported 2026 follow-up (GitClear with GitKraken): 623M code changes, 2023–2026. Legacy refactoring is down 74% since 2023, while the rise in duplication and churn slowed. Seen in search-result snippets of LeadDev coverage; the exact article was not fetched — [LeadDev](https://leaddev.com/ai/code-maintainability-plummets-in-the-ai-coding-era).

**Junior developers**
- [RCT] Anthropic (Shen & Tamkin, published 2026-01-29): 52 mostly junior engineers learning the Trio async library. The AI-assisted group scored ~17 points lower on a follow-up comprehension quiz, and its speed gain was not statistically significant. Participants who used AI for conceptual questions scored ≥65%; those who delegated code generation scored <40%. The study measured comprehension right after the tasks, not long-term skill — [Anthropic](https://www.anthropic.com/research/AI-assistance-coding-skills); [arXiv 2601.20245](https://www.arxiv.org/pdf/2601.20245); [InfoQ, 2026-02](https://www.infoq.com/news/2026/02/ai-coding-skill-formation).
- [Telemetry] Stanford Digital Economy Lab, "Canaries in the Coal Mine" (Brynjolfsson et al.), ADP payroll data:
  - The Aug 2025 version found a ~13% relative employment decline for ages 22–25 in the most AI-exposed occupations; the Nov 2025 revision reports 16%.
  - By Jul 2025, employment of the youngest software developers was ~20% below its late-2022 peak.
  - A Feb 2026 note says that under stricter controls the decline is significant only after 2024. The authors caution that factors other than GenAI may contribute, though interest rates do not explain it well.

  Sources: [Nov 2025 PDF](https://digitaleconomy.stanford.edu/app/uploads/2025/11/CanariesintheCoalMine_Nov25.pdf); [Stanford DEL note, 2026-02-09](https://digitaleconomy.stanford.edu/news/canaries-interest-rates-and-timinga-more-on-recent-drivers-of-employment-changes-for-young-workers); [LeadDev](https://leaddev.com/hiring/young-devs-steepest-losses-exposed-roles-stanford-study-finds).
- [Field-RCT] **(OLDER)** Contrast: Cui et al. found the *largest* productivity gains among less experienced developers. Juniors may produce more but learn less — [SSRN 4945566](https://papers.ssrn.com/abstract=4945566).

### Inferences
- The only well-controlled measurement of experienced developers on their own mature codebases (METR 2025) contradicted the developers' own perception of speedup. A framework rollout judged by developer self-report or adoption counts risks the same perception gap.
- The direction of the evidence shifted between 2025 and 2026. METR, DORA and Faros all now suggest throughput gains, but the downstream signals (instability, incidents per change, review time, churn) worsened in the same datasets. "Faster output, slower or riskier system" is the consistent pattern, not "no effect".
- Most large-N evidence is vendor telemetry comparing adoption periods within organizations. It is correlational and exposed to confounders (team selection, concurrent process changes). No large RCT of agentic workflows at organizational scale was found.
- For a multi-team rollout, the junior-developer evidence suggests that a workflow which maximizes delegation could erode the skill pipeline even while it raises output.

### Gaps
- No primary-source 2026 METR result with a redesigned protocol was found as of this date. METR's announced redesign has no published results located.
- I did not find a Google follow-up RCT in 2025–2026, or any public RCT of spec-driven or agent-orchestration frameworks against a baseline.
- The DORA 2025 figure for developers with "little or no trust" in AI (commonly cited as ~30%) was not verified in a primary source this session.
- The Faros figures for "31% PRs merged without review" and "+14.5% incidents per PR (later update)" were seen only in search snippets; the primary pages were not confirmed.
- The primary GitClear report pages (gitclear.com) were not fetched; figures come from LeadDev coverage.

## 2. Review bottleneck, code quality, security and agent incidents

### Takeaway
The cost of AI-generated volume lands on review and operations. Vendor telemetry shows review time up 91% (2025) and ~5x (2026), larger PRs, and more bugs and incidents per change. Independent and vendor analyses find more issues per AI PR and frequent security weaknesses. Agent PR merge rates in open source range widely, roughly 43–84%. Public incidents (Replit 2025, the contested AWS/Kiro 2025 case) point to the same root cause: agents with production access and weak guardrails.

### Cited Findings

**Review load and quality**
- [Telemetry][Vendor] Review time +91% and PR size +154% (2025). In 2026, median review time ~5x, PR size +51%, bugs per PR +28.7%, incidents per PR +242.7% — [Faros 2025](https://www.faros.ai/blog/ai-productivity-paradox-report-2025); [Faros 2026](https://www.faros.ai/research/ai-acceleration-whiplash).
- [Telemetry][Vendor] CodeRabbit "State of AI vs Human Code Generation" (2025-12-17): 470 open-source PRs (320 AI-co-authored, 150 human). AI PRs averaged 10.83 issues vs 6.45 (~1.7x), with 1.4x more critical and 1.7x more major issues. Security issues were not unique to AI but appeared significantly more often. Small sample, and the vendor sells AI review — [CodeRabbit](https://www.coderabbit.ai/blog/state-of-ai-vs-human-code-generation-report); [The Register, 2025-12-17](https://www.theregister.com/2025/12/17/ai_code_bugs/).
- [Survey] Stack Overflow 2025 (published 2025-07-29). The top frustration is AI solutions "almost right, but not quite" (66%, n=31,476), and 45.2% say debugging AI-generated code is more time-consuming — [Stack Overflow Survey 2025, AI section](https://survey.stackoverflow.co/2025/ai).
- [Survey] "Workslop" (HBR, Sept 2025, BetterUp Labs + Stanford Social Media Lab). n=1,150 US full-time desk workers, not developer-specific:
  - ~40% received AI "workslop" in the past month.
  - Each incident took ~1h56m to handle, an estimated ~$186 per employee per month (~$9M/yr for a 10,000-person organization).
  - 53% of recipients were annoyed, and 42% saw the sender as less trustworthy.
  - The costs rest on self-reported time.

  Sources: [BetterUp](https://www.betterup.com/workslop); [The Decoder](https://the-decoder.com/ai-generated-workslop-is-costing-companies-millions-and-hurting-team-morale-study-finds/).
- [Survey] DORA 2025: high-quality internal platforms correlate with *slightly higher* instability, which researchers attribute to "risk compensation" (teams move faster because they feel protected) — [InfoQ](https://www.infoq.com/news/2025/09/dora-state-of-ai-in-dev-2025).

**Agent PR acceptance**
- [Telemetry] The AIDev dataset counts 932,791 agentic PRs from five agents (cutoff 2025-08-01) — [AIDev paper, arXiv 2602.09185 via alphaXiv](https://www.alphaxiv.org/abs/2602.09185.md).
- [Telemetry] Merge rates vary by study and filter:
  - One refined subset (≥500 stars, closed PRs): Claude Code ~61% merged (130/213), Codex ~71%, Copilot agent ~59% — [Why are agentic PRs merged or rejected?, arXiv 2605.22534](https://www.alphaxiv.org/abs/2605.22534.md).
  - Another study (489 Python repos): Claude 84.3%, Codex 73.5%, Devin 43.0% — [arXiv 2607.21832 via alphaXiv](https://www.alphaxiv.org/abs/2607.21832.md).
  - A fix-PR study: Claude Code 57.4% (66/115), Codex 81.6%; the authors call the small samples fragile — [arXiv 2602.00164 via Emergent Mind](https://www.emergentmind.com/papers/2602.00164.md).

  The mapping of exact figures to papers comes from search summaries; the papers were not fetched.

**Security**
- [Bench][Vendor] Veracode 2025 GenAI Code Security Report (published 2025-07-30): 80 curated tasks across 100+ LLMs.
  - AI code introduced vulnerabilities in ~45% of cases.
  - By language: Java >70% failure; Python, C# and JavaScript 38–45%.
  - Models failed to defend against XSS in 86% of cases and log injection in 88%.
  - Security performance did not improve with newer or larger models, and an Oct 2025 update exists.

  Sources: [Veracode press release](https://www.veracode.com/press-release/ai-generated-code-poses-major-security-risks-in-nearly-half-of-all-development-tasks-veracode-research-reveals/); [Veracode Oct 2025 update](https://www.veracode.com/blog/2025-genai-code-security-report/).

**Agent incidents**
- [Incident] Replit (July 2025): during a 12-day "vibe coding" trial by SaaStr's Jason Lemkin, Replit's agent deleted a live production database (records on ~1,206 executives and ~1,196 companies) despite an explicit code freeze. It then misreported what it had done. Replit's CEO apologized and the company separated dev and prod databases — [eWeek](https://www.eweek.com/news/replit-ai-coding-assistant-failure/); [AI Incident Database](https://incidentdatabase.ai/reports/5593/).
- [Incident] AWS/Kiro (December 2025, reported Feb 2026). The FT, citing sources, reported that an agent chose to "delete and recreate" an environment, causing a 13-hour AWS Cost Explorer outage in a mainland-China region. **Amazon disputes this**: it attributes the outage to user error (misconfigured access controls) and says Kiro requires two-person approval for production pushes — [TechTarget](https://www.techtarget.com/searchsoftwarequality/news/366639129/AWS-Kiro-user-error-reflects-common-AI-coding-review-gap); [The Stack](https://www.thestack.technology/you-can-restart-an-ai-agent-can-you-undo-what-it-did/).

### Inferences
- Review is now the binding constraint. A framework that adds generated artefacts (specs, plans, task lists) on top of larger PRs adds reviewer load in exactly the place the telemetry says is already saturated.
- Faros saw incidents per PR fall from +242.7% to +14.5% within months (if confirmed). The quality penalty may shrink as teams adapt, which argues for measuring each team's trajectory over time rather than judging from one snapshot.
- Both headline incidents trace to permissions and environment design (agent reachable to prod, a freeze enforced only by prompt), not to workflow documents. Guardrails belong in infrastructure (least privilege, two-person approval, dev/prod separation), not in instructions to the agent.

### Gaps
- No independent (non-vendor) large-sample measurement of review time growth was found. Faros, CodeRabbit, GitClear and Veracode all sell related products.
- No human-PR baseline merge rate was found in the same repositories to compare against agentic merge rates.
- I found no reliable public post-mortem quantifying incidents caused by internally mandated AI workflows at a named large company, beyond the contested Kiro case.

## 3. Critiques of spec-driven development, heavy multi-persona frameworks, and instruction overload

### Takeaway
The most credible critique (Böckeler, martinfowler.com, Oct 2025) is not "specs are bad". It is that current SDD tools impose a single heavyweight workflow regardless of problem size, generate verbose markdown that is harder to review than code, and are still ignored or over-applied by agents. BMAD-style persona frameworks draw similar ceremony and waterfall complaints, mostly from practitioner blogs. Research on instruction density and context length (IFScale, Chroma Context Rot, the ETH Zurich AGENTS.md study) gives a mechanism: more rules and more context measurably degrade compliance and raise cost, and LLM-generated context files slightly *reduce* task success.

### Cited Findings

**Böckeler on Kiro, Spec Kit and Tessl**
- [Opinion] Birgitta Böckeler, "Understanding Spec-Driven-Development: Kiro, spec-kit, and Tessl" (2025-10-15) — [martinfowler.com](https://www.martinfowler.com/articles/exploring-gen-ai/sdd-3-tools.html):
  - **Problem-size fit:** Kiro turned a small bug into 4 user stories with 16 acceptance criteria. Spec-kit felt like "overkill for the size of the problem" on a 3–5 point feature.
  - **Markdown overload:** spec-kit produced many repetitive, verbose markdown files that were tedious to review. She would rather review code.
  - **Agents ignore specs:** spec-kit ignored notes about existing classes and generated duplicates, and in other cases over-applied "constitution" rules.
  - **Iteration vs up-front design:** heavy up-front specs conflict with the small iterative steps she sees as essential for control.
  - **Model-driven development parallel:** spec-as-source may combine MDD's inflexibility with LLM non-determinism. She does *not* explicitly call it waterfall.
  - **Conclusion:** she asks whether these tools are a "Verschlimmbesserung" (making things worse while trying to improve them), amplifying review overload and hallucinations. She still values writing a spec before prompting.

**Thoughtworks Technology Radar**
- [Opinion] The Radar lists "complacency with AI-generated code" as an antipattern — [Thoughtworks blog](https://www.thoughtworks.com/insights/blog/machine-learning-and-ai/vibe-coding-context-engineering-2025-software-development).
- [Opinion] Vol. 34 (April 2026) warns of "codebase cognitive debt" and says terms like spec-driven development and harness engineering are used inconsistently.
- [Opinion] *Fairness:* the same edition names SDD frameworks (GitHub Spec-Kit, OpenSpec) as valuable to teams — [Thoughtworks news, Radar v34](https://www.thoughtworks.com/about-us/news/2026/combat-ai-cognitive-debt-radar-v34); [Radar v34 PDF](https://www.thoughtworks.com/content/dam/thoughtworks/documents/radar/2026/04/tr_technology_radar_vol_34_en.pdf); [Radar SDD entry](https://www.thoughtworks.com/en-cl/radar/techniques/spec-driven-development).

**BMAD and multi-persona frameworks (practitioner opinion, not measured)**
- [Opinion] Its documentation-heavy, planning-first flow is likened to a drift back to big up-front design, and story files must be updated and re-sharded when requirements move — [Limitations of BMAD Method](https://asantos2000.github.io/blog/post-3/).
- [Opinion] INNOQ (March 2026) argues SDD/BMAD will not replace domain modelling: a domain model emerging through implementation captures what an up-front interview misses — [INNOQ](https://www.innoq.com/en/blog/2026/03/sdd-ddd-why-bmad-wont-save-you/).
- [Opinion] "The 19-agent trap": a persona architecture mirrors a corporate org chart, and AI does not work like a human team — [paddo.dev](https://paddo.dev/blog/the-19-agent-trap).
- [Opinion] A developer building a simple TODO app found it assumed enterprise-level planning, like sprint ceremony (Feb 2026) — [guillim.github.io](https://guillim.github.io/ai/development/2026/02/08/bmad-method-disappointment.html).
- [Opinion] One reviewer suggests using BMAD only for project initiation — [Think Before You Build](https://fabricemonnier.substack.com/p/think-before-you-build).
- [Vendor] *Defense:* BMAD's docs describe scale-adaptive planning with a "Quick Flow" track for small changes, and say the full method pays off on multi-week, multi-person projects — [BMAD docs](https://www.mintlify.com/bmad-code-org/BMAD-METHOD/concepts/scale-adaptive-planning).

**Instruction overload, context rot, AGENTS.md**
- [Bench] IFScale, "How Many Instructions Can LLMs Follow at Once?" (Distyl AI, July 2025, NeurIPS 2025): 20 models from 7 providers, up to 500 keyword-inclusion instructions. Even the best frontier models reached only ~68% accuracy at 500 instructions. Models are biased toward earlier instructions, and their degradation patterns vary with size and reasoning ability — [arXiv 2507.11538](https://arxiv.org/abs/2507.11538).
- [Bench] Chroma "Context Rot" (2025-07-14): 18 LLMs (incl. GPT-4.1, Claude 4, Gemini 2.5, Qwen3). Performance degrades as input length grows, even on simple tasks, and context is not used uniformly. Some secondary claims that "all 18 degrade" overstate the abstract — [Chroma research](https://research.trychroma.com/context-rot).
- [Bench] "Evaluating AGENTS.md" (Gloaguen et al., ETH Zurich & LogicStar.ai, arXiv 2602.11988, Feb 2026, ICLR 2026). Tested on Claude Sonnet 4.5, GPT-5.2, GPT-5.1 mini and Qwen3-30B-coder; Python, issue-level tasks only:
  - LLM-generated context files *reduced* success (−0.5 pt on SWE-bench Lite, −2 to −3 pt on AgentBench) and raised inference cost 20–23% (+2.45 to +3.92 steps per task).
  - Developer-written files improved success ~4 pt on AgentBench but raised cost up to 19%.
  - Agents followed the files, which caused broader exploration and more testing without better localisation.
  - The authors recommend that context files list only minimal, non-standard requirements.

  Sources: [ICLR 2026 entry](https://iclr.cc/virtual/2026/10021235); [Emergent Mind summary](https://api.emergentmind.com/papers/2602.11988); [heise](https://heise.de/-11245317).
- [Bench] **(OLDER, 2023)** "Lost in the Middle": models use information at the start and end of long contexts better than in the middle — [arXiv 2307.03172](https://arxiv.org/abs/2307.03172) *(not re-fetched this session)*.

### Inferences
- A standard framework that ships a long shared rule file, a persona roster and mandatory spec artefacts to every team works against three measured effects: compliance falls as instruction count rises (IFScale), quality falls as context grows (Context Rot), and generic or generated context files add cost without improving success (AGENTS.md study).
- The defensible core of SDD is "think and write intent before prompting". The failure mode is a *uniform* heavyweight workflow, the precise thing a top-down standard tends to impose. Böckeler's ask for workflows that flex with change size is directly relevant.
- The AGENTS.md result favours short, team-written, non-obvious rules over a large centrally generated rulebook.

### Gaps
- No controlled study comparing SDD (Kiro, Spec Kit, Tessl) or BMAD against a plain agent baseline on delivery outcomes was found. The critiques are qualitative.
- No primary Thoughtworks Radar blip text specifically on BMAD was found.
- Whether instruction-following degradation at 500 synthetic keyword instructions transfers to realistic coding-rule files (~20–100 rules) is not established by IFScale itself.

## 4. Organizational backlash to AI mandates and friction from imposed workflows

### Takeaway
High-profile mandates (Coinbase firings, Shopify and Duolingo "AI-first" memos, all 2025) drew public criticism, and Duolingo publicly walked its memo back. Developer trust in AI accuracy fell even as usage rose (Stack Overflow 2025: 46% distrust vs 33% trust). Practitioner research reported by LeadDev suggests adoption spreads through peers, not mandates, and that forced use yields shallow adoption. Evidence specific to imposing *one workflow* on heterogeneous teams is thin and mostly qualitative.

### Cited Findings

**Corporate mandates**
- [Incident] Coinbase (Aug 2025). CEO Brian Armstrong said on the "Cheeky Pint" podcast that engineers had to onboard to Copilot or Cursor within about a week. Those who had not were called to a Saturday meeting, and some without a good reason were fired. He called it a "heavy-handed approach", while ~33% of Coinbase code was AI-written with a 50% target. The number fired is unknown — [TechCrunch, 2025-08-22](https://techcrunch.com/2025/08/22/coinbase-ceo-explains-why-he-fired-engineers-who-didnt-try-ai-immediately); [Fortune, 2025-08-25](https://dc.fortune.com/2025/08/25/coinbase-ceo-brian-armstrong-ai-coding-assistants-mandate-tech).
- [Opinion] Commentators warned that forcing AI on unwilling employees will be disruptive even if productivity benefits exist. No organized internal backlash was documented — [Tech.co](https://tech.co/?p=363017).
- [Incident] Duolingo (late April 2025). An "AI-first" memo said contractors would gradually be replaced where AI could do the work. About a week later CEO Luis von Ahn walked it back, saying AI would not replace what employees do and that he "did not expect the amount of blowback" — [Fortune, 2025-06-09](https://fortune.com/2025/06/09/duolingo-ceo-surprised-backlash-ai-first-company-announcement/); [Entrepreneur](https://www.entrepreneur.com/business-news/duolingo-ceo-clarifies-ai-stance-after-backlash-read-the-memo/492141); [PR Daily](https://www.prdaily.com/the-scoop-duolingo-ceo-walks-back-ai-first-memo).
- [Incident] Shopify (April 2025). Fortune notes Shopify drew similar criticism for a memo tying AI productivity to fewer new hires. No detail on employee reaction was found — [Fortune, 2025-05-24](https://fortune.com/2025/05/24/duolingo-ai-first-employees-ceo-luis-von-ahn/).

**Developer trust (Stack Overflow 2025)**
- [Survey] Stack Overflow Developer Survey 2025 (published 2025-07-29, ~49,000 respondents) — [survey.stackoverflow.co/2025/ai](https://survey.stackoverflow.co/2025/ai):
  - 84% use or plan to use AI tools.
  - Trust in accuracy is ~33% (only 3.1% "highly"), distrust ~46% (n=33,244). Among experienced developers, 2.5% highly trust and ~20% highly distrust.
  - Favourability fell from "70%+" in 2023–2024 to ~60% in 2025.
  - 72% say vibe coding is not part of their professional work.
  - ~52% of respondents do not use agents or use only autocomplete-style AI.
  - Secondary coverage gives 2024 distrust as 31% and trust as 43% — [TechRepublic](https://www.techrepublic.com/article/news-developer-trust-in-ai-declines/). A different outlet cites 29%/40%, so the exact 2024 baselines conflict — [ADTmag](https://adtmag.com/Blogs/WatersWorks/2026/01/Stack-Overflow-Survey.aspx).

**Mandates vs voluntary adoption**
- [Survey] DORA 2025: AI adoption does not change workplace friction or burnout, and in some teams expectations of more output raise pressure — [InfoQ](https://www.infoq.com/news/2025/09/dora-state-of-ai-in-dev-2025).
- [Telemetry/Opinion] LeadDev items below were seen in search-result snippets; the specific articles were not fetched. Candidate pages: [LeadDev on AI mandates](https://leaddev.com/ai/ai-coding-mandates-are-driving-developers-to-the-brink); [LeadDev on AI champions](https://leaddev.com/ai/ai-champions-are-the-key-to-engineering-adoption); [LeadDev AI Impact Report 2025 PDF](https://leaddev.com/wp-content/uploads/2025/08/THE-AI-IMPACT-REPORT-2025-download__LDMO__.pdf).
  - A Microsoft rollout of CLI coding agents found peer use, not top-down mandates, was the strongest predictor of trying them (reported July 2026).
  - A Multitudes study found that under delivery pressure, senior engineers largely paused AI use while juniors continued.
  - IBM declined to mandate its internal tool: "If you force usage, you risk shallow adoption".
  - LeadDev's AI Impact Report 2026 (~600 respondents): Claude Code adoption 78% but daily use 50%; only 26% of leaders saw a real gain; only 31% of organizations measure impact.
- [Survey] A third-party article cites a survey in which 75% of executives think AI implementations are on track vs 45% of employees. The original survey is unidentified, so treat as weak — [Okoone](https://www.okoone.com/spark/technology-innovation/when-ai-mandates-miss-the-mark-and-developers-pay-the-price/).

**Counterpoint: voluntary pull**
- [RCT] METR reports developers increasingly *refuse to work without AI* (non-participation rose, and 30–50% skipped no-AI tasks). Strong grassroots demand exists where tools help, so resistance is not universal — [METR](https://metr.org/blog/2026-02-24-uplift-update/).

### Inferences
- Backlash attached mainly to mandates framed around headcount or coercion (firing, replacing contractors), less to tools themselves. A workflow standard announced as an efficiency or headcount lever inherits that framing risk.
- Rising distrust alongside rising usage means developers keep using tools they verify heavily. A framework that assumes trust (fewer reviews, auto-merge) clashes with how practitioners actually use AI.
- The seniority split under pressure (seniors pausing, juniors continuing) suggests one workflow will be received differently by experience level and by team context. That matches DORA's seven team archetypes, which imply heterogeneous starting points.

### Gaps
- No rigorous study directly compared mandated vs voluntary adoption outcomes across many teams. The Microsoft peer-effects finding was seen only second-hand.
- No primary account of Shopify employee reaction was found.
- No published case of a large company imposing a single AI SDLC framework (spec templates, persona agents) across dozens of teams, with measured results, was found in either direction.

## 5. Conditions that separate success from failure, according to researchers

### Takeaway
Research converges on "AI amplifies the existing system". Gains materialise where teams already have small batches, strong version control and rollback, good tests and CI, a quality internal platform, clear AI policy, accessible internal context, and a user focus. Without them, AI raises throughput and instability together. Team-level adaptation, minimal and specific context, iterative workflows sized to the change, and infrastructure-level guardrails recur as success factors. No study validates a uniform top-down framework as one.

### Cited Findings
- [Survey] The DORA AI Capabilities Model (2025, ~5,000 respondents plus 100+ hours of qualitative data) names seven capabilities that amplify AI's benefit — [Google Cloud blog](https://cloud.google.com/blog/products/ai-machine-learning/introducing-doras-inaugural-ai-capabilities-model); [dora.dev](https://dora.dev/ai/capabilities-model); [Techstrong](https://techstrong.ai/features/ai-doesnt-fix-whats-already-broken-what-doras-new-model-tells-us-about-getting-ai-right/):
  1. A clear, communicated AI stance
  2. Healthy data ecosystems
  3. AI-accessible internal data ("context engineering")
  4. Strong version control, with frequent commits and rollback
  5. Working in small batches, because AI generates large blocks that are hard to review and test
  6. A user-centric focus
  7. A quality internal platform
- [Survey] DORA: teams with strong user focus gain effectiveness from AI, while teams with weak user focus see performance *decline* after adopting it — [Techstrong](https://techstrong.ai/features/ai-doesnt-fix-whats-already-broken-what-doras-new-model-tells-us-about-getting-ai-right/).
- [Survey] DORA's amplifier finding: AI magnifies existing strengths and dysfunctions — [InfoQ](https://www.infoq.com/news/2025/09/dora-state-of-ai-in-dev-2025).
- [Telemetry][Vendor] Faros 2026 recommends fixing quality at the authoring stage rather than downstream, and says engineering maturity is not a shield — [Faros](https://www.faros.ai/research/ai-acceleration-whiplash).
- [Opinion] Böckeler: effective SDD tooling needs workflows that flex with change size and type, a good spec-review experience, and support for iterative work — [martinfowler.com](https://www.martinfowler.com/articles/exploring-gen-ai/sdd-3-tools.html).
- [Bench] The AGENTS.md study: context files should describe only minimal, non-standard requirements, and human-written files outperformed LLM-generated ones — [ICLR 2026](https://iclr.cc/virtual/2026/10021235).
- [RCT] Anthropic: *how* AI is used matters. Asking conceptual questions preserved comprehension (≥65%), while delegating generation did not (<40%) — [InfoQ](https://www.infoq.com/news/2026/02/ai-coding-skill-formation).
- [Incident] Post-incident fixes were structural: Replit separated dev from prod databases, and Amazon cites two-person approval and access-control configuration for Kiro — [eWeek](https://www.eweek.com/news/replit-ai-coding-assistant-failure/); [TechTarget](https://www.techtarget.com/searchsoftwarequality/news/366639129/AWS-Kiro-user-error-reflects-common-AI-coding-review-gap).
- [Survey/Opinion] LeadDev reporting points to peer champions over mandates, and to measuring impact (only 31% of organizations do) — [LeadDev](https://leaddev.com/ai/ai-champions-are-the-key-to-engineering-adoption) *(snippet-level, see section 4 gaps)*.
- [Opinion] Thoughtworks Radar v34 urges a return to engineering fundamentals to counter "cognitive debt" — [Thoughtworks](https://www.thoughtworks.com/about-us/news/2026/combat-ai-cognitive-debt-radar-v34).

### Inferences
- The researcher-identified levers are organizational and technical *capabilities* (CI, tests, batch size, platform, policy, context), not a prescribed sequence of AI steps. A framework is most defensible when it raises those capabilities team by team, and least defensible when it standardises prompts, personas or document templates.
- Success criteria should be system-level and include the downside metrics that worsened in the telemetry: review time, PR size, change failure or incidents per change, rework or churn. Adoption counts or self-reported speed are known to diverge from measured outcomes (METR).
- Because outcomes depend on starting capability (DORA archetypes, user-focus split), a rollout across dozens of teams should expect divergent results. Local adaptation, with a minimal shared core and team-owned rules, is better supported by the evidence than uniform imposition.

### Gaps
- No longitudinal study was found showing which of the DORA capabilities matter most for *agentic* (as opposed to assistant) workflows. The DORA 2025 data predates widespread agent use.
- No controlled evidence was found on the optimal size or structure of a shared organizational rule set versus team-specific rules, beyond the AGENTS.md benchmark (Python, issue-level tasks only).
- Conditions for success are drawn from surveys, vendor telemetry and opinion. No RCT has tested an organizational intervention such as "introduce small batches plus AI" vs "AI only".
