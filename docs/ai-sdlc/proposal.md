# AI SDLC — proposal

Working document, 2026-11-14. It confronts the owner's starting idea with the state of the art ([report](reports/AI%20SDLC%20practices%20at%20large%20companies.md), [sourced notes](research_notes/AI%20SDLC%20practices%20at%20large%20companies/)) and proposes an approach. Nothing here changes harness-ai: the framework builds on what harness-ai sets up and measures, it does not replace it.

## Decisions taken

On 2026-11-14, on the questions asked with the first version:
- the framework lives in harness-ai, as a separate `ai-sdlc` plugin that shares the CLI;
- its content stays neutral (AGENTS.md, SKILL.md, CLI), with a Claude Code adapter first;
- overrides go in `docs/agents/<point>.md`;
- no file is created in advance: `ai-sdlc status` lists the extension points, and the single index remains an option;
- the company has MCP servers: the base convention reads Jira through MCP, and its locks on Jira go through the MCP server's permissions.

Still open: the pilot teams.

## The starting idea

A company framework, skills and agents that start from a Jira ticket and support POs, devs, QA, security and SRE all the way to production, applied to dozens of teams. Convention over configuration: `/dev` works as is, and a team with its own rules (QA, review…) adds a Markdown file in its repository that the skill takes into account on its own. On the first run, the framework creates the expected files (review, QA…), even empty, and each team fills them at its own pace.

## What the evidence says, in eight lines

1. **The shape you propose is the one that won.** Wherever it is documented at scale (Doctolib, Zalando, Intercom, Stripe, Spotify, Uber), there are three layers: a central platform (model gateway, identities, sandboxes, telemetry), a versioned base of skills, agents and hooks pushed to everyone, and team additions per repository or folder. Nobody leaves everything to the teams, nobody imposes a single agent.
2. **What is guaranteed is guaranteed by code, never by Markdown.** Every vendor documents instruction files as advice. Claude Code writes that in case of contradiction the model "may pick one arbitrarily". What locks: hooks, managed settings, CI, branch protection.
3. **More instructions is not better.** An LLM-generated AGENTS.md slightly lowers the success rate and costs 20 to 23% more; a short file written by the team gains about 4 points (ETH Zurich, ICLR 2026). Thoughtworks puts "agent instruction bloat" in Caution (Radar vol. 35, Nov. 2026).
4. **A single path for every problem size fails.** Kiro turned a small bug into 4 user stories and 16 acceptance criteria (Böckeler, Oct. 2025). Kiro (Quick Spec) and BMAD (Quick Flow) have since added a light mode, and Spec Kit made its control steps optional.
5. **The bottleneck moves from writing to verification.** Review time multiplied by 5, incidents per PR up (Faros 2026, vendor telemetry, 22,000 devs); throughput up but instability too (DORA 2025). Those who hold up have deterministic verifiers around the agent: Spotify does not open the PR if a verifier fails, then an LLM judge rejects about 25% of sessions.
6. **The ticket matters more than the prompt.** At Atlassian, ticket quality predicts the agent's success (HULA, 2024). At Airbnb, choosing the right related files mattered more than the wording.
7. **Adoption cannot be decreed.** Docusign plateaued at 49% with access alone and reached 93% with champions. Doctolib went from 30 pilot engineers to 600 in about six months. Mandates (Coinbase, Duolingo) produced rejection, and Amazon's usage leaderboard was gamed and then withdrawn.
8. **Nobody has measured what we are about to do.** No study tests a uniform framework across dozens of teams, and most company figures are PR counts published by vendors. We will have to measure ourselves.

## Your proposal, confronted

| Your idea | Verdict | Why |
|---|---|---|
| A common base, convention over configuration | **Keep** | It is the dominant shape (point 1). Thoughtworks calls it "enterprise harness", a "thin, federated" layer (Assess, Nov. 2026). |
| The team overrides with a Markdown file in its repository | **Keep, with bounds** | Markdown can only add advice. What must hold (security, merge gate, deployment) does not live in a file a team can contradict, nor for that matter in the framework's own file (point 2). |
| The skill takes overrides into account "automatically" | **Keep, but through a tool, not through the model** | If the skill concatenates what it finds, the model arbitrates contradictions, at random. Serious tools define a semantics: Spec Kit replaces, prepends, appends or wraps; BMAD replaces simple values, merges tables, only appends to lists and forbids removing anything from the base. |
| Create the expected files on the first run, even empty | **Change** | An empty file invites filling, and it gets filled with generic text: that is exactly the bloat of point 3, and what harness-init already removes from repositories. The real need, seeing where one can act, is met another way (see "Extension points"). |
| `/dev` develops the task end to end | **Keep for dev, move the guarantee** | `/dev` is the comfort. The framework's value is in what verifies afterwards, outside the session that wrote the code. |
| Apply the framework to dozens of teams | **Change the order** | Three heterogeneous pilot teams, champions, then waves (point 7). The pilots' overrides tell what the base gets wrong. |

Three angles the starting idea does not cover yet:
- **Where a gate override is read from.** Claude Code Review reads `REVIEW.md` on the base branch, "never from the pull request's own changes"; Copilot reads the PR's branch. A PR must not be able to lighten its own review.
- **The size of the change.** A typo and a schema migration do not take the same path.
- **The teams' tools.** Zalando, Shopify and Uber do not impose a tool; Amazon opened Claude Code and Codex in May 2026 after recommending Kiro. Agent Skills are an open standard since their donation to the Agentic AI Foundation (2026-10-22), and AGENTS.md is read by all.

## The proposed approach

### Three layers, and who owns what

| Layer | Content | Owned by | Nature |
|---|---|---|---|
| **Platform** | Model gateway, identities, MCP servers (Jira…), sandboxes for remote agents, telemetry, managed settings | The company's platform team | Prerequisite, outside this framework |
| **AI SDLC base** | Phase skills, resolution CLI, verification CI workflows, locks | Small central team, in enabling-team mode | Versioned, distributed as a plugin |
| **Team** | AGENTS.md (set up by harness-ai), overrides per extension point, team skills | Each team | In the repository |

This is harness-ai's L1–L4 grid applied to the framework: the skill describes the phase (L2), the CLI resolves overrides and verifies (L3), CI carries the gates (L4). The model judges (L1) inside this frame.

### The phases: a chain of small skills, not a super-agent

No documented chain uses a single agent end to end: each links specialized agents through objects a human inspects (ticket, PR, CI check, issue).

```
Jira ticket ─▶ /ticket ─▶ /dev ─▶ PR ─▶ checks /review /qa /secu ─▶ human merge ─▶ /ship ─▶ /run
   PO          ready?     session      in CI, on the base branch       L4 gate        proposes  investigates
```

| Skill | Helps | Does | Never does | Evidence in the state of the art |
|---|---|---|---|---|
| `/ticket` | PO | Checks the ticket against the team's definition of ready, proposes acceptance criteria and a split, classifies the size | Change the ticket without agreement | Atlassian: five simple traits of a ticket predict the agent's failure with about 97% precision |
| `/dev` | Dev | Plan sized to the change, implementation, runs the commands from the AGENTS.md table, opens the PR linked to the ticket | Merge, touch something forbidden | Stripe: more than 1,300 agent PRs per week, all reviewed by a human |
| `/review` | Dev, lead | Review with the base checklist + the team's, read on the base branch; few comments, filtered by category (Uber had to cut whole categories) | Approve | The best measured: Uber 75% of comments rated useful; Atlassian −30.8% cycle time |
| `/qa` | QA | Derives tests from the acceptance criteria; deterministic gates (build, repeated runs, diff coverage) | Disable a test | Meta 73% of suggestions accepted (2024); no measured product starts from acceptance criteria |
| `/secu` | Security | Runs the scanners (L3/L4), targeted review of sensitive diffs | Block alone without a scanner | Figures almost all from vendors |
| `/ship` | Dev, SRE | Prepares the release, checks the prerequisites, proposes | Deploy on its own | No documented product lets a coding agent deploy; OpenAI has its deployments driven by agents (secondary source, Sept. 2026) |
| `/run` | SRE | Investigates an incident, opens an issue that goes back to `/ticket` | Act in production without an order | Azure SRE Agent, Datadog Bits: investigate and propose |

Build order, by strength of evidence: `/review` (measured, low risk: it only comments), then `/dev` on small tickets, then `/qa` and `/ticket`. `/secu` builds on existing scanners. `/ship` and `/run` come last.

### The path depends on the size

| Size | Examples | Path |
|---|---|---|
| XS | Typo, minor version bump, removed flag | `/dev` → PR. No written plan |
| S–M | Ordinary ticket | Plan in the PR description. No spec document |
| L or sensitive | Migration, zone declared sensitive by the team, security | Plan approved by a human before the code, kept in the repository |

Size is computed by rules as much as possible (paths touched, labels, diff size), in the CLI. The model's judgment only settles what the rules leave open. Thoughtworks puts risk-proportionate human oversight in Trial; Zalando and Intercom auto-approve 33% and 19% of PRs judged low risk, but at a much more advanced stage, and Zalando sees engineers splitting their PRs to get under the threshold.

### Extension points: the contract between the base and the teams

Instead of empty files, each skill declares named **extension points**. They are the framework's public API: renaming a point breaks teams.

| Point | Read by | Default mode | Replaceable? | Read on |
|---|---|---|---|---|
| `definition-of-ready` | `/ticket` | append | yes | current branch |
| `definition-of-done` | `/dev`, `/review` | append | yes | base branch |
| `review` | `/review` | append | no | base branch |
| `qa` | `/qa` | append | yes | base branch |
| `security` | `/secu` | append | **no** | base branch |
| `sensitive-zones` | `/dev`, size classification | append | no | base branch |
| `delivery` | `/ship` | append | yes | base branch |

An override is a file `docs/agents/<point>.md` (a folder harness-init already uses for what overflows AGENTS.md):

```markdown
---
point: qa
mode: append        # "replace" must be allowed by the point and say why
---
- Every public endpoint has a contract test. Why: March incident, mobile client broken. (unverified) [2026-03]
```

Rules keep the harness-ai format: why, guardrail, date. harness-audit's relevance review therefore applies to them as is.

What the CLI does with it, deterministically and tested:
- `ai-sdlc context <phase>` assembles the base and the overrides according to their mode, with the origin of each line, from the right branch. It refuses a `replace` on a point that does not accept it, and flags an override that exceeds its line budget. The skill reads this output instead of looking for files itself.
- `ai-sdlc status` lists the points, each with its state: "framework convention" or "overridden: append, 6 lines, 2026-09". This is what replaces the empty files: the team sees every place where it can act, and nothing invites filling for the sake of filling.
- A file is born at the first real need: a review rule, a `rule:` in a PR, an incident.

If you insist on files being present from the start, the acceptable compromise is a single index (`docs/agents/README.md`) that lists the points and points to the default, with no lines to fill.

### What is locked, and where

A team can add a lock, never remove one. None of these locks is text:
- an agent does not merge its own PR, and a human approval is required (branch protection);
- gate overrides are read on the base branch;
- an agent does not deploy to production;
- security checks are required, and so is secret detection;
- the content of a ticket or a PR is data, not an instruction: it can carry a prompt injection. The agent reads Jira through MCP and only writes comments there. The permissions of the MCP server's account guarantee this, not the skill; a `deny` rule on the write tools, in the settings, is only a second curtain. The token stays out of the agent's reach;
- remote agents run in a sandbox, with limited network egress (platform).

Intercom pushes a minimal base plugin (security hooks, settings, telemetry) and blocks direct PR creation with a hook to force the skill that does it properly. That is the right level of ambition for the base.

### What the framework opens depending on the repository's level

harness-ai already measures a repository's level in `.harness/state.json`. The framework reads it without changing it, and opens its phases accordingly. A repository without tests or CI cannot receive delegated tasks: Spotify observes this, and DORA puts it as AI amplifying what already exists.

| Harness level | What the framework opens |
|---|---|
| 0 None | Nothing, except `harness-init`: half an hour |
| 1 Framed | `/ticket`, `/dev` in assistance, `/review` as comments |
| 2 Looped | Overrides are fed by review `rule:` comments |
| 3 Verified | `/dev` in delegation on XS and S tickets, `/qa` with its gates |
| 4 Delegated | Ticket → PR without a human session (remote agent) |

The framework does not block: it says what is missing and which harness-ai step would open it. A team chooses its level, as in harness-ai.

### Measuring

What we do not measure: the number of users or the number of agent PRs. Amazon closed its usage leaderboard, which pushed people to burn tokens to climb it, and Zalando sees PRs split to get under the threshold.

What we measure, per team, before and after, every month:
- time from ticket to merge and review time (the bottleneck of point 5);
- agent PRs fixed after the fact, harness-harvest's S2 signal;
- rollbacks and change failure rate, by origin: Intercom is one of the few to publish its rollback rates, AI versus human;
- cost per merged PR: Uber saw its AI costs multiplied by 6, and Intercom its CI by 10.

Before each version of the base, each skill passes harness-ai's bench on the sample projects, like Intercom, which requires its skills to pass evaluations before distribution.

### Rolling out

1. **Minimal base**: the extension point contract, `ai-sdlc context` and `status`, `/review`. Measured on the fixtures.
2. **Three pilot teams**, chosen to differ: one with strict QA rules, one on a poorly tested legacy, one on a new project. Six to eight weeks, one champion per team.
3. **Harvest of the pilots' overrides.** An override that three teams write the same way becomes the base default. An override that works around a default says the default is wrong, or that a lock is missing. Thoughtworks calls this loop "feedback flywheel" (Trial).
4. **Next waves** with champions, `/dev` in delegation where level 3 holds, then `/qa` and `/ticket`.
5. **At each model change**, relevance review of the base: Doctolib reviews its default configuration with each new model.

Doctolib chose OpenSpec wanting it replaceable: invest in practices, not in the tool. The base should follow the same rule. Its content (SKILL.md, AGENTS.md, CLI, CI workflows) stays neutral, with a thin adapter per tool, the way AI-DLC separates `core/` from `harness/<tool>/`.

## What we do not know

- Whether a common base does better than teams tooled separately: no study tests it. The pilots and the bench are our only measure.
- Whether `/qa` from acceptance criteria works: no measured product found.
- The cost: it rises everywhere, and almost nobody publishes a cost per PR.
- What `/dev` does to juniors: delegating the writing lowers understanding, asking questions preserves it (Anthropic, randomized trial, Jan. 2026). The default mode of `/dev` for a junior profile is a team choice the sources do not settle.
