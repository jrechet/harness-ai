# Frameworks, methodologies and override mechanisms for packaging an AI-assisted SDLC (state as of 2026-11-14)

Scope note: primary sources (official docs, official repos) were fetched on 2026-11-14 unless marked "secondary". Several tools changed a lot during 2026: Spec Kit reached 1.x, OpenSpec 2.x, BMAD v6.12 with v7 in alpha, AI-DLC 2.11, Gemini CLI was retired. Check version numbers before reusing a detail.

## 1. Spec-driven and phase-based tools: phases, artefacts, human checkpoints, and how a team overrides defaults

### Takeaway
All the major SDD tools now follow a "versioned core + layered local override" model. Spec Kit (presets/overrides stack with priorities and replace/prepend/append/wrap strategies), BMAD (customize.toml → team TOML → personal TOML), OpenSpec (config.yaml context/rules + custom schemas), Kiro (global vs workspace steering) and AI-DLC (core/ vs harness/ plus plugins) all ship one. Phases always converge on specify → plan/design → tasks → implement, with optional quality gates (clarify, checklist, analyze, converge) and human review between phases. Each tool has an opt-out "quick" path for small changes.

### Cited Findings

**GitHub Spec Kit (latest release v1.4.0, published 2026-11-10)**
- Latest release tag is v1.4.0, published 2026-11-10 — [GitHub releases API for github/spec-kit](https://github.com/github/spec-kit/releases)
- Canonical command sequence: `/speckit.constitution -> /speckit.specify -> /speckit.clarify -> /speckit.plan -> /speckit.checklist -> /speckit.tasks -> /speckit.analyze -> /speckit.implement -> /speckit.converge` — [docs/reference/agentic-sdd.md](https://github.com/github/spec-kit/blob/main/docs/reference/agentic-sdd.md)
- Only `/speckit.specify` is strictly required before `/speckit.plan`. clarify, checklist and analyze are optional "quality gates" for work with meaningful ambiguity. `/speckit.clarify` was formerly `/quizme` — [agentic-sdd.md](https://github.com/github/spec-kit/blob/main/docs/reference/agentic-sdd.md)
- The invocation syntax depends on the agent integration: dotted `/speckit.*` in the docs, `/speckit-*` in GitHub Copilot's default skills mode, `$speckit-*` for Codex, `/skill:speckit-*` for Kimi — [agentic-sdd.md](https://github.com/github/spec-kit/blob/main/docs/reference/agentic-sdd.md); the README itself uses hyphenated names — [github/spec-kit README](https://github.com/github/spec-kit)
- What each command does:
  - `/speckit.clarify` asks up to five targeted questions and writes the answers back into `spec.md`.
  - `/speckit.analyze` is read-only. It checks consistency across `spec.md`, `plan.md` and `tasks.md`.
  - `/speckit.tasks` produces a dependency-ordered `tasks.md` in phases: Setup, Foundational, one phase per user story, then Polish.
  - `/speckit.converge` is append-only. It never edits code and only adds tasks to `tasks.md` until it reports "Converged".
  - Source: [agentic-sdd.md](https://github.com/github/spec-kit/blob/main/docs/reference/agentic-sdd.md)
- Human checkpoint built into the artefacts: custom checklists are "reviewer-owned". `/speckit.implement` reads checklist checkbox state as a gate and asks before proceeding when items are unchecked, and it "must not silently self-approve" them — [agentic-sdd.md](https://github.com/github/spec-kit/blob/main/docs/reference/agentic-sdd.md). The README says to run each step "one at a time, reviewing each result before continuing" — [README](https://github.com/github/spec-kit)
- Active-feature tracking:
  - The active feature is tracked in `.specify/feature.json` (override: `SPECIFY_FEATURE_DIRECTORY`), not from the checked-out git branch.
  - Numbered feature branches (`001-feature-name`) now come from an opt-in **git** extension.
  - Source: [docs/quickstart.md](https://github.com/github/spec-kit/blob/main/docs/quickstart.md)
- Constitution lifecycle: initialization seeds `.specify/memory/constitution.md` once from the resolved `constitution-template` and preserves an existing one. The bundled opt-in `constitution-sync` preset propagates stack changes but protects hand-edited constitutions — [docs/presets/overview.md](https://github.com/github/spec-kit/blob/main/docs/presets/overview.md)
- **Override stack.** Each logical file name is resolved independently through these layers, highest first:
  1. Project-local overrides in `.specify/templates/overrides/`
  2. Enabled presets, ordered by priority then preset ID
  3. Extension contributions, ordered by priority then extension ID
  4. Spec Kit core defaults

  Lower priority numbers win, and an extension cannot outrank the preset layer — [docs/presets/overview.md](https://github.com/github/spec-kit/blob/main/docs/presets/overview.md)
- Composition strategies are `replace` (the default; ignore lower layers), `prepend`, `append` and `wrap` (insert lower content at a placeholder). Example: `specify preset add --dev ./compliance --priority 5`. `specify preset resolve spec-template` shows which file wins — [presets/overview.md](https://github.com/github/spec-kit/blob/main/docs/presets/overview.md)
- Templates and scripts are resolved at runtime. Commands are "materialized" at install/reconcile time: agents do not resolve the stack on each invocation — [presets/overview.md](https://github.com/github/spec-kit/blob/main/docs/presets/overview.md)
- Presets are described as a way to "enforce organizational standards". Extensions add commands, quality gates, and hooks that run before or after Spec Kit commands. There are also workflows, overlays (modify an installed workflow without forking), bundles, and private catalogs — [presets/overview.md](https://github.com/github/spec-kit/blob/main/docs/presets/overview.md); [README](https://github.com/github/spec-kit)
- Extra agentic processes ship as extensions: `bug` (`/speckit-bug-assess`, `-fix`, `-test`, with reports in `.specify/bugs/<slug>/`) and `assess` (intake → research → define → shape → decide, producing `decision.md` with go / needs-clarification / kill) — [README](https://github.com/github/spec-kit)
- Organizations can host their own catalogs with "source priority and trust". Community extensions such as Quality Gates and Architecture Guard add policy checks — [Spec Kit docs site](https://github.github.io/spec-kit/)

**AWS Kiro**
- Specs:
  - A Feature Spec produces `requirements.md` (user stories + acceptance criteria), `design.md` and `tasks.md`, in either a "Requirements-First" or a "Design-First" variant.
  - A Bugfix Spec produces `bugfix.md` covering current, expected and unchanged behavior.
  - A "Quick Spec" generates all three artefacts "without approval gates".
  - Review uses a Review button and inline comments on each phase document.
  - Tasks run individually or as dependency-ordered concurrent "waves".
  - Source: [kiro.dev/docs/specs](https://kiro.dev/docs/specs/)
- Requirements use GIVEN/WHEN/THEN acceptance criteria, and each task traces to requirement numbers (observed Oct 2025) — [Böckeler, martinfowler.com](https://martinfowler.com/articles/exploring-gen-ai/sdd-3-tools.html)
- Steering:
  - Workspace steering lives in `.kiro/steering/`, global steering in `~/.kiro/steering/`. The default files are `product.md`, `tech.md` and `structure.md`.
  - YAML front-matter `inclusion` takes `always` (default), `fileMatch` + `fileMatchPattern` (globs), `manual` (`#steering-file-name`) or `auto` (needs `name` + `description`).
  - `#[[file:...]]` references are supported. An unresolved reference shows a visible marker "rather than being silently dropped".
  - Source: [kiro.dev/docs/steering](https://kiro.dev/docs/steering/)
- Conflicts: when global and workspace steering conflict, Kiro prioritizes the workspace instructions. Teams push global steering through MDM / Group Policy, or users download it into `~/.kiro/steering/`. AGENTS.md is supported at the root and in subdirectories, is always included, and does not support inclusion modes — [kiro.dev/docs/steering](https://kiro.dev/docs/steering/)
- Hooks:
  - Workspace hooks are `.json` files in `.kiro/hooks/`. Global hooks live in `~/.kiro/hooks/` (CLI V3).
  - Triggers include `PostFileSave`, `Stop`, `PreToolUse` and `PostToolUse`.
  - Actions are `command` (shell, JSON on STDIN, 60 s timeout) or `agent` (prompt injection).
  - PreToolUse can block tool execution. Global and workspace hooks "run alongside each other".
  - Source: [kiro.dev/docs/hooks](https://kiro.dev/docs/hooks/)

**BMAD Method**
- Versions and loop:
  - Stable line is v6.12 (`npx bmad-method install`, frozen except bug fixes). V7 is in "preview alpha" with a release ETA of mid-November 2026.
  - The README describes the delivery loop as Clarify → Plan → Build and verify → Learn and adjust.
  - Small changes go straight to build, and larger work gets deeper planning.
  - Source: [BMAD-METHOD README](https://github.com/bmad-code-org/BMAD-METHOD)
- Modules: BMad Method (core), BMad Builder, Creative Intelligence Suite, Test Architect, BMad Loop (builds/verifies/retros a whole epic unattended), Game Dev Studio, plus V7 optional Toolsmith and Founder. The README no longer uses the term "expansion packs" — [README](https://github.com/bmad-code-org/BMAD-METHOD)
- Named agents/skills in current docs: Mary (`bmad-agent-analyst`), John (`bmad-agent-pm`), Amelia (dev), and roster-driven skills `bmad-party-mode`, `bmad-retrospective` and `bmad-advanced-elicitation` — [Adopt BMad across a team](https://docs.bmad-method.org/customize/adopt-bmad-across-a-team/)
- **Three-layer override model**, highest first:
  1. `_bmad/custom/<skill>.user.toml` (personal, gitignored)
  2. `_bmad/custom/<skill>.toml` (team, committed)
  3. The skill's shipped `customize.toml` ("never edit")

  Central config follows the same split: `_bmad/custom/config.toml` and `config.user.toml` — [Customize BMad](https://docs.bmad-method.org/customize/customize-bmad/); [Adopt across a team](https://docs.bmad-method.org/customize/adopt-bmad-across-a-team/)
- Merge semantics: [Customize BMad](https://docs.bmad-method.org/customize/customize-bmad/)
  - Scalars: the override wins.
  - Tables: deep merge.
  - Arrays of tables keyed by `code` or `id`: replace in place or append.
  - Other arrays: append in base → team → user order.
  - An override cannot delete a base item. You neutralize it via its `code`, or fork the skill.
- Overridable fields:
  - Agents: `icon`, `role`, `identity`, `communication_style`, `persistent_facts`, `principles`, `activation_steps_prepend` / `_append`, and the `[[agent.menu]]` array.
  - Workflows: the same hooks plus `on_complete`; `bmad-code-review` and others add `review`.
  - Source: [Customize BMad](https://docs.bmad-method.org/customize/customize-bmad/)
- Superseded: older v6 docs and mirrors describe `_bmad/_config/agents/<agent>.customize.yaml` plus a "Recompile Agents" step. The official docs now use TOML overrides — [mintlify mirror (older)](https://www.mintlify.com/bmad-code-org/BMAD-METHOD/guides/customize-bmad) vs [docs.bmad-method.org](https://docs.bmad-method.org/customize/customize-bmad/)

**OpenSpec (Fission-AI), 2.x line**
- 2.x commands are `/openspec-explore`, `/openspec-propose <name>`, `/openspec-apply-change` and `/openspec-archive-change` (Codex uses `$openspec-propose`). An expanded profile adds new/continue/ff/verify/bulk-archive/onboard. The 1.x commands were `/opsx:*` — [OpenSpec README](https://github.com/Fission-AI/OpenSpec)
- Layout: live specs live in `openspec/specs/`. Each change gets `openspec/changes/<name>/` with `proposal.md`, `specs/`, `design.md` and `tasks.md`, and archiving moves it to `openspec/changes/archive/YYYY-MM-DD-<name>/` and updates the specs. Requirements use `### Requirement:` and `#### Scenario:` WHEN/THEN blocks — [README](https://github.com/Fission-AI/OpenSpec)
- Human checkpoint: "you review the plan before any code is written". Apply and archive are separate, human-triggered steps. "Stores" (beta) keep planning in a separate repo, and one change can span several code repos — [README](https://github.com/Fission-AI/OpenSpec)
- `openspec/config.yaml` holds:
  - `schema` (default schema)
  - `context` (injected into every artefact prompt as a `<context>` block)
  - `rules` (per artefact ID, injected only for that artefact)
  - `operations.apply.guidance` / `archive.guidance`

  Source: [docs/customization.md](https://github.com/Fission-AI/OpenSpec/blob/main/docs/customization.md)
- Custom schemas live in `openspec/schemas/<name>/` (project) or `~/.local/share/openspec/schemas/` (user); `spec-driven` is built in. Schema resolution order is CLI `--schema` > change metadata `.openspec.yaml` > project config > default `spec-driven` — [docs/customization.md](https://github.com/Fission-AI/OpenSpec/blob/main/docs/customization.md)

**AWS AI-DLC (AI-Driven Development Life Cycle)**
- The original methodology has three phases: Inception (what/why), Construction (how) and Operations. Its team rituals are "Mob Elaboration" and "Mob Construction", with adaptive depth per phase — [AWS DevOps blog](https://aws.amazon.com/blogs/devops/ai-driven-development-life-cycle); [Open-sourcing adaptive workflows for AI-DLC](https://aws.amazon.com/blogs/devops/open-sourcing-adaptive-workflows-for-ai-driven-development-life-cycle-ai-dlc)
- Current repo `awslabs/aidlc-workflows`:
  - Version badge 2.11.4, with "5 phases and 33 stages".
  - Workflow profiles: Classic, Express, and focused ones for features, bug fixes, infrastructure, security and PoCs.
  - 14 agents: 11 domain experts, 2 reviewers and an adaptive composer.
  - It "stops at approval gates", with a 134-event audit trail, persistent state, team knowledge and learned rules.
  - Source: [awslabs/aidlc-workflows](https://github.com/awslabs/aidlc-workflows)
- Packaging:
  - `core/` holds the harness-neutral methodology and `harness/<name>/` the per-tool manifests.
  - `aidlc config --harness <name>` targets Claude Code, Kiro, Codex CLI, Cursor, opencode or GitHub Copilot.
  - Plugins live in `plugins/<name>/`, synced with `/aidlc plugin sync`.
  - A "Harness Engineer Guide" covers reshaping stages, agents, rules, sensors and knowledge.
  - Source: [awslabs/aidlc-workflows](https://github.com/awslabs/aidlc-workflows)
- Conflict between sources: the AWS blog describes three phases, while the current repo README describes five phases / 33 stages. The repo is the newer source — [AWS blog](https://aws.amazon.com/blogs/devops/ai-driven-development-life-cycle) vs [repo](https://github.com/awslabs/aidlc-workflows)

**Tessl**
- In Oct 2025 the Tessl Framework was a private beta CLI and MCP server aiming at spec-anchored and spec-as-source development, with a 1:1 spec-to-code-file mapping. Generated code carried a "DO NOT EDIT" header, and output was non-deterministic across runs — [Böckeler, martinfowler.com](https://martinfowler.com/articles/exploring-gen-ai/sdd-3-tools.html)
- 2026 repositioning (secondary sources): Tessl now presents itself as a package manager / registry for evaluated agent skills (announced 2026-01-29). Its `tessl-labs/spec-kit` tile was archived on 2026-02-04 and superseded by `intent-integrity-kit`, and the Framework had apparently not reached GA by mid-2026 — [Tessl blog](https://tessl.io/blog/my-coding-agent-needed-a-package-manager-for-its-own-brain-and-i-gave-it-one-using-a-skills-registry); [codemyspec review (secondary)](https://codemyspec.com/blog/tessl-review)

### Inferences
- Spec Kit's presets and BMAD's TOML layers are the most explicit "convention over configuration with local overrides" designs found:
  - **Spec Kit**: file-level replace/compose with numeric priority. The project-local override always wins.
  - **BMAD**: field-level deep merge. Arrays only append, so a lower layer can never delete a base item. This is the only "partially locked" semantics among the SDD tools.
- No SDD tool reviewed offers a central layer that a repo **cannot** override. "Enforcement" goes through extensions and quality gates (Spec Kit), the reviewer-owned checklist gate (Spec Kit), or approval gates (AI-DLC, Kiro).
- Spec Kit 1.x addressed two of Böckeler's 2025 criticisms:
  - Branch-per-spec is now an opt-in git extension.
  - Optional gates and a Quick-Spec-like separation of bug and assess flows reduce the "one size fits all" weight. Kiro answers the same criticism with Quick Spec.
- A framework packaging a `/develop` skill could mirror the Spec Kit stack (core template → org preset → project override) and the BMAD merge semantics (scalars replace, lists append, no deletion of base items) to get the "required vs suggested" split.

### Gaps
- Could not confirm in current BMAD docs the full classic role roster (analyst, PM, architect, PO, SM, dev, QA) or the v6 phase names (analysis / planning / solutioning / implementation). The current README describes neither.
- Kiro's spec storage path (`.kiro/specs/<name>/`) and EARS notation were not confirmed on the current specs page.
- AI-DLC stage names and artefact paths (e.g. `aidlc-docs/`, `audit.md`) were not visible in the README. They sit in `core/` or in the 2.0 Specification PDF, which was not read.
- Tessl's current product state rests on secondary sources only.

## 2. Instruction-file layering: AGENTS.md, Claude Code, Copilot, Cursor, Codex, Gemini CLI

### Takeaway
Every tool layers org/global → user → repo → subdirectory, but they differ on what "precedence" means:
- **Concatenation (no hard override):** Claude Code, Gemini CLI and Codex concatenate files root-to-leaf, so later, closer text "wins" only by position.
- **Nearest file wins:** AGENTS.md and Copilot rely on the "nearest file wins" convention.
- **Explicit ordering:** Cursor defines a strict order Team → Project → User where earlier wins. Kiro lets workspace beat global.

Hard enforcement lives outside instruction files: Claude managed settings, hooks and permissions; Cursor's "Enforce this rule" toggle.

### Cited Findings

**AGENTS.md (open standard)**
- Plain Markdown with no required fields. Agents read the nearest file in the directory tree, and "explicit user chat prompts override everything". Migration path: rename the old file and symlink the old name — [agents.md](https://agents.md/)
- Stewarded by the Agentic AI Foundation under the Linux Foundation. Supporters listed include Codex, Jules, Factory, Aider, goose, opencode, Zed, Warp, VS Code, Devin/Windsurf, Junie, Amp, Cursor, RooCode, Gemini CLI, Kilo Code, Copilot coding agent, Augment and others — [agents.md](https://agents.md/)
- Anthropic donated the Agent Skills standard to the Agentic AI Foundation on 2026-10-22 — [Simon Willison, tag "skills"](https://simonwillison.net/tags/skills/)

**Claude Code memory (CLAUDE.md)**
- Scopes, in load order from broadest to most specific:
  1. Managed policy: `/Library/Application Support/ClaudeCode/CLAUDE.md` (macOS), `/etc/claude-code/CLAUDE.md` (Linux/WSL), `C:\Program Files\ClaudeCode\CLAUDE.md` (Windows)
  2. User `~/.claude/CLAUDE.md`
  3. Project `./CLAUDE.md` or `./.claude/CLAUDE.md`
  4. Local `./CLAUDE.local.md` (gitignored)

  Source: [code.claude.com/docs/en/memory](https://code.claude.com/docs/en/memory)
- Files above the working directory load at launch, and subdirectory CLAUDE.md files load on demand when Claude reads, writes or edits a file there. All discovered files "are concatenated into context rather than overriding each other". Order runs filesystem root → cwd, with `CLAUDE.local.md` after `CLAUDE.md` at each level — [memory](https://code.claude.com/docs/en/memory)
- `@path` imports are relative to the importing file, recursive up to four hops. External imports need one-time approval — [memory](https://code.claude.com/docs/en/memory)
- `.claude/rules/*.md` files are discovered recursively and may carry `paths:` glob frontmatter, which loads them only when a matching file is read or edited. User-level rules in `~/.claude/rules/` load before project rules. "Neither set overrides the other", so Claude "may follow either one". Symlinked shared rule directories are supported, and external targets need approval — [memory](https://code.claude.com/docs/en/memory)
- Managed instructions:
  - The managed CLAUDE.md cannot be excluded via `claudeMdExcludes`. The docs say to use it "for guidance" and enforce rules with managed settings such as `permissions.deny`.
  - A `claudeMd` key in `managed-settings.json` can carry the content inline. It is honored only in managed/policy settings.
  - Source: [memory](https://code.claude.com/docs/en/memory)
- AGENTS.md support:
  - Native since v2.1.277. Default mode `claude-md-or-agents-md` reads AGENTS.md only when no CLAUDE.md / CLAUDE.local.md exists in cwd or above.
  - Other modes: `claude-md-and-agents-md`, `claude-md` and `managed-only`, set via `/config` or `pluginConfigs."cc-plugin-agents-md@builtin"`.
  - `AGENTS.override.md`, `AGENTS.local.md` and `.agents/` are not read.
  - The plugin ID was `agents-md@builtin` before v2.1.285.
  - Source: [memory](https://code.claude.com/docs/en/memory)
- `/doctor prompt-audit` (v2.1.283+) reports conflicting or outdated instructions across CLAUDE.md, AGENTS.md, rules, skills, subagents and commands — [memory](https://code.claude.com/docs/en/memory)
- Settings precedence, highest first: managed > command line `--settings` > `.claude/settings.local.json` > `.claude/settings.json` > `~/.claude/settings.json`:
  - List keys such as `permissions.allow` merge across files.
  - "Nothing in your own settings files" overrides a managed key.
  - A few security keys honor a stricter value from a lower scope, e.g. `disableClaudeAiConnectors: true` or `permissions.blockReadsOutsideWorkingDirectories: true`.
  - Source: [code.claude.com/docs/en/settings](https://code.claude.com/docs/en/settings)
- Managed settings arrive as server-managed settings (claude.ai admin console), MDM or OS policy (plist / registry), or `managed-settings.json` plus a `managed-settings.d/` drop-in directory. By default only the first source that delivers a policy key applies (server > MDM > file), unless `managedSourcesBehavior: "merge"` — [plugins/org](https://code.claude.com/docs/en/plugins/org)
- Skills:
  - Locations: Enterprise (managed directory), personal `~/.claude/skills/`, project `.claude/skills/`, nested `<subdir>/.claude/skills/` (on demand), `--add-dir`, plugin (`/plugin-name:skill`), and claude.ai-synced skills.
  - On a name collision, "Enterprise overrides personal, and personal overrides project". Plugin skills are namespaced, and nested and root skills both load.
  - `.claude/commands/` still works but is merged into skills, which are "the recommended format".
  - Source: [code.claude.com/docs/en/skills](https://code.claude.com/docs/en/skills)
- Plugins for organizations:
  - Managed `extraKnownMarketplaces` plus `enabledPlugins` pre-install plugins.
  - A managed `true` force-enables a plugin: disabling it at user scope "doesn't stop it from loading".
  - A managed `false` blocks a plugin at every scope.
  - `strictKnownMarketplaces` (allowlist) and `blockedMarketplaces` restrict marketplace sources.
  - `strictPluginOnlyCustomization` blocks skills, agents, hooks and MCP from user and project sources.
  - `disableSideloadFlags` rejects `--plugin-dir` and similar flags.
  - Per-repo plugins can be required via the repo's `.claude/settings.json`, applied after workspace trust.
  - Source: [code.claude.com/docs/en/plugins/org](https://code.claude.com/docs/en/plugins/org)

**GitHub Copilot**
- Instruction files:
  - Repository-wide: `.github/copilot-instructions.md`.
  - Path-specific: `.github/instructions/**/NAME.instructions.md`, with an `applyTo` glob frontmatter and an optional `excludeAgent: "code-review" | "cloud-agent"`.
  - Agent instructions: any number of `AGENTS.md` files (the nearest one takes precedence), or a single root `CLAUDE.md` or `GEMINI.md`.
  - When a path-specific file and the repo-wide file both match, both are used.
  - Source: [docs.github.com – add repository instructions](https://docs.github.com/en/copilot/how-tos/configure-custom-instructions/add-repository-instructions)
- Precedence on Copilot Chat on GitHub.com is personal > path-specific > repository-wide > agent instructions > organization. VS Code, Visual Studio and Copilot CLI "combine applicable files" without a general precedence order. Organization instructions need Copilot Business or Enterprise and are supported on GitHub-website sessions and Copilot code review, not in local clients — [docs.github.com – response customization](https://docs.github.com/en/copilot/concepts/prompting/response-customization)
- Path-specific instructions on GitHub.com are supported only for the Copilot cloud agent and code review. For pull requests, Copilot reads instructions and skills from the head branch — [add repository instructions](https://docs.github.com/en/copilot/how-tos/configure-custom-instructions/add-repository-instructions)
- Custom agents:
  - Files are `*.agent.md` in `.github/agents`.
  - Org-level agents go in `/agents` of the org's `.github` or `.github-private` repo. Enterprise-level agents go in a designated org's `.github-private`.
  - "Chat modes" were renamed custom agents (VS Code 1.106).
  - Source: [GitHub docs – about custom agents](https://docs.github.com/en/enterprise-cloud@latest/copilot/concepts/agents/copilot-cli/about-custom-agents); [VS Code – custom agents](https://code.visualstudio.com/docs/copilot/customization/custom-agents)
- Prompt files (`.github/prompts/*.prompt.md`): whether they are deprecated is contested. A community glossary marks them deprecated, while GitHub's customization cheat sheet still lists them as VS Code–only — [awesome-copilot glossary (community)](https://awesome-copilot.github.com/learning-hub/github-copilot-terminology-glossary/) vs [customization cheat sheet](https://docs.github.com/en/enterprise-cloud@latest/copilot/reference/customization-cheat-sheet)

**Cursor**
- Four rule types:
  - Project Rules: `.cursor/rules/*.mdc`, version-controlled; "a plain `.md` file there is ignored".
  - User Rules: global settings.
  - Team Rules: dashboard, Team and Enterprise plans.
  - AGENTS.md: root and subdirectories, no frontmatter.
  - Source: [cursor.com/docs/context/rules](https://cursor.com/docs/context/rules)
- Project-rule modes are Always Apply, Apply Intelligently (by `description`), Apply to Specific Files (`globs`) and Apply Manually (@-mention). Frontmatter fields are `description`, `globs` and `alwaysApply` — [Cursor rules](https://cursor.com/docs/context/rules)
- Precedence is "Team Rules → Project Rules → User Rules", and "earlier sources take precedence when guidance conflicts". Nested AGENTS.md files combine with their parents, with "more specific instructions taking precedence". Legacy `.cursorrules` is not mentioned in the current doc — [Cursor rules](https://cursor.com/docs/context/rules)

**OpenAI Codex (docs moved from developers.openai.com to learn.chatgpt.com, HTTP 308)**
- Global level: `~/.codex` (or `$CODEX_HOME`) reads `AGENTS.override.md`, else `AGENTS.md`, using "only the first non-empty file" — [Codex AGENTS.md guide](https://learn.chatgpt.com/docs/agent-configuration/agents-md)
- Project level: Codex walks from the git root down to cwd. In each directory it takes `AGENTS.override.md`, then `AGENTS.md`, then the `project_doc_fallback_filenames`, and includes at most one file per directory. Files are joined root-first, so files closer to cwd "override earlier guidance" — [Codex AGENTS.md guide](https://learn.chatgpt.com/docs/agent-configuration/agents-md)
- Empty files are skipped. Loading stops when the combined size reaches `project_doc_max_bytes` (default 32 KiB) — [Codex AGENTS.md guide](https://learn.chatgpt.com/docs/agent-configuration/agents-md)

**Gemini CLI (retired) / Antigravity CLI**
- Gemini CLI loads `~/.gemini/GEMINI.md` (global), then files in workspace directories and their parents, then just-in-time files up to a trusted root when tools touch a path. All are concatenated:
  - `context.fileName` can switch the file names, e.g. to `["AGENTS.md", "GEMINI.md"]`.
  - `@file.md` imports work.
  - `/memory show` and `/memory reload` inspect and refresh memory.
  - The docs page notes Gemini CLI "was replaced by Antigravity CLI on June 18, 2026".
  - Source: [geminicli.com/docs/cli/gemini-md](https://geminicli.com/docs/cli/gemini-md/)
- Antigravity CLI (`agy`) uses AGENTS.md for project instructions and keeps GEMINI.md for backward compatibility, with a recommendation to rename. Secondary sources disagree on precedence when both files exist — [Flutter docs – Antigravity CLI](https://docs.flutter.dev/ai/antigravity-cli.md); [migration guide (secondary)](https://toolsbase.dev/en/blog/gemini-cli-to-antigravity-migration)

### Inferences
- Two families:
  - **Concatenate + position:** Claude Code, Gemini/Antigravity and Codex, which are effectively "last text read wins, probabilistically".
  - **Declared ordering:** Cursor (Team > Project > User), Copilot on GitHub.com (personal > path > repo > agent > org) and Kiro (workspace > global).
- Copilot ranks organization instructions *lowest*, so org instructions behave as suggested defaults. Cursor ranks Team *highest* and adds a hard "Enforce" toggle.
- AGENTS.md is the de-facto portable layer: native in Codex, Cursor, Copilot, Kiro, Antigravity, and Claude Code since v2.1.277. Its nesting semantics ("nearest wins") is portable, but `AGENTS.override.md` is Codex-specific and Claude Code ignores it.

### Gaps
- Gemini CLI's system-level settings (`/etc/gemini-cli/settings.json`, system defaults) and their precedence were not verified, and are moot after the retirement. Antigravity CLI's own managed/enterprise configuration was not researched.
- Codex managed configuration (`requirements.toml`, managed config) was not fetched. The AGENTS.md page links to a "Managed configuration" page but does not describe it.
- The official per-surface support table for Copilot instruction types was not retrieved.

## 3. Conflict resolution between central and local instructions; "required/locked" vs "suggested" central rules

### Takeaway
Only a few mechanisms provide truly *locked* central policy:
- Claude Code managed settings (permissions, hooks via `allowManagedHooksOnly`, force-enabled or blocked plugins, `strictPluginOnlyCustomization`).
- Cursor Team Rules with "Enforce this rule".
- MDM-deployed files that a developer cannot exclude, such as the Claude managed CLAUDE.md.

Everything expressed as Markdown instructions is, by every vendor's own documentation, guidance that the model may weigh against conflicting local text. Locking is achieved deterministically (settings, hooks, CI), not textually.

### Cited Findings
- Claude Code states that CLAUDE.md and auto memory are "context, not enforced configuration". To block an action regardless of what Claude decides, use a PreToolUse hook — [memory](https://code.claude.com/docs/en/memory)
- When instructions contradict, "Claude may pick one arbitrarily". The fix is periodic review and `/doctor prompt-audit` — [memory](https://code.claude.com/docs/en/memory)
- The managed CLAUDE.md cannot be excluded with `claudeMdExcludes`, but a session with CLAUDE.md loading turned off "doesn't load the managed content either". The `managed-only` mode loads only managed CLAUDE.md and auto memory at launch — [memory](https://code.claude.com/docs/en/memory)
- The docs split responsibilities:

  | Concern | Mechanism |
  |---|---|
  | Block tools, commands, paths | Managed settings `permissions.deny` |
  | Sandboxing | `sandbox.enabled` |
  | Login method | `forceLoginMethod` |
  | Code style, compliance reminders, behavior | Managed CLAUDE.md |

  Source: [memory](https://code.claude.com/docs/en/memory)
- In Claude settings, a managed key wins over every other scope. List keys merge unless `allowManagedPermissionRulesOnly` is set. Some keys honor a *stricter* local value even over managed (e.g. `blockReadsOutsideWorkingDirectories: true`, a lower `maxEffortLevel`) — [settings](https://code.claude.com/docs/en/settings)
- Plugin locking in Claude: a managed `enabledPlugins: true` cannot be disabled by users; `false` blocks at every scope; `strictPluginOnlyCustomization` makes managed plugins the only source of skills, agents, hooks and MCP — [plugins/org](https://code.claude.com/docs/en/plugins/org)
- Skill-name collisions resolve Enterprise > personal > project — [skills](https://code.claude.com/docs/en/skills)
- Cursor Team Rules: admins configure whether each rule is required. With "Enforce this rule" enabled the rule "cannot be disabled" by members. Without it, members can toggle it off — [Cursor rules](https://cursor.com/docs/context/rules)
- Copilot: "All relevant sets are provided" to the model, ranked personal > repository > organization. The docs say to avoid conflicting sets, and that repository instructions can be disabled temporarily — [add repository instructions](https://docs.github.com/en/copilot/how-tos/configure-custom-instructions/add-repository-instructions); [response customization](https://docs.github.com/en/copilot/concepts/prompting/response-customization)
- Kiro: workspace steering wins over global, which lets teams "set broad global defaults and override them per workspace". Global and workspace hooks both run — [Kiro steering](https://kiro.dev/docs/steering/); [Kiro hooks](https://kiro.dev/docs/hooks/)
- AGENTS.md: the closest file wins, and user prompts override everything — [agents.md](https://agents.md/)
- Codex: `AGENTS.override.md` replaces `AGENTS.md` in the same directory. Closer files override earlier ones — [Codex AGENTS.md guide](https://learn.chatgpt.com/docs/agent-configuration/agents-md)
- Spec Kit: project-local overrides outrank every preset. Presets with priority numbers resolve conflicts among org layers, e.g. `compliance` at priority 3 beats `team-base` at 10 — [presets/overview.md](https://github.com/github/spec-kit/blob/main/docs/presets/overview.md)
- BMAD: user > team > shipped defaults for scalars. Arrays only append and "an override can't delete a base item" — [Customize BMad](https://docs.bmad-method.org/customize/customize-bmad/)

### Inferences
Mechanisms by locking strength:

| Strength | Mechanisms |
|---|---|
| Hard lock (deterministic) | Claude managed settings, hooks, permissions, plugin force/block; Cursor enforced Team Rules; Kiro PreToolUse hooks; CI checks |
| Soft lock (always in context, cannot be removed by the dev) | Claude managed CLAUDE.md, BMAD base array items, Copilot org instructions (lowest priority) |
| Suggested default (local wins) | Spec Kit core/presets vs project overrides, Kiro global steering, BMAD scalars, Codex/AGENTS.md parent files, OpenSpec built-in schema |

- A framework that needs "required" central rules should express them as deterministic checks (hooks, CLI, CI) rather than Markdown. This matches the repo's own AGENTS.md rule that guaranteed behavior goes in `cli/`, not skill text.
- None of the instruction-file mechanisms detects or reports conflicts at load time, except Claude's on-demand `/doctor prompt-audit`.

### Gaps
- No vendor documents a model-level "this instruction is non-negotiable" marker inside instruction files. If one exists, it was not found.
- Copilot org-level "required" vs "optional" instructions were not documented in the pages read; org instructions appear simply as the lowest-priority layer.

## 4. Patterns for a framework skill (e.g. /develop) that auto-reads team-specific markdown overrides: examples, discovery, empty or missing files

### Takeaway
The most precise, documented example is Anthropic's managed Claude Code Review:
- It reads `REVIEW.md` (root + subdirectories) plus `CLAUDE.md` ancestors of changed files.
- It reads from the protected base/default branch, never from the PR.
- One-level `@file` includes are capped at 8 files and 150,000 bytes.
- A non-matching include line silently stays as plain text.

BMAD (`persistent_facts` with `file:` globs), OpenSpec (`config.yaml` context/rules injected per artefact), Spec Kit (constitution + project overrides) and Kiro (fileMatch/auto steering) are the other documented "framework reads team files" patterns. Missing files consistently fall back to the lower layer or shipped default.

### Cited Findings
- **Claude Code Review — files read:**
  - It reads the root `CLAUDE.md` and the `CLAUDE.md` files in the parent directories of each changed file.
  - `REVIEW.md` at the root holds review-only rules. A subdirectory `REVIEW.md` adds checks for changes under that path "on top of the root file".
  - Subdirectory files are not applied under directories named test/tests/fixtures/examples/generated/vendor/node_modules/third_party, among others.
  - Source: [Customize Code Review](https://code.claude.com/docs/en/code-review-customize)
- **Claude Code Review — branch and trust model:**
  - `REVIEW.md` is read from the PR's base branch or the default branch, "never from the pull request's own changes".
  - Severity lowering, path exclusions and nit caps are honored only when the root file sits on a protected branch.
  - With an unprotected default branch only the root file is read. If protection cannot be confirmed, no file is read.
  - Source: [Customize Code Review](https://code.claude.com/docs/en/code-review-customize)
- **Claude Code Review — includes and limits:**
  - A line with only `@file` includes a root-level file. Includes are one level only, at most eight files, 150,000 bytes combined. A file that would exceed the limit is skipped whole.
  - A line whose name matches no file "stays in REVIEW.md as plain text", and the check run does not report it.
  - Skill files can be included as `@.claude/skills/<folder>/SKILL.md` (≤30,000 bytes). Code Review does not run `!` commands, substitutions or supporting files from the skill.
  - Source: [Customize Code Review](https://code.claude.com/docs/en/code-review-customize)
- **Claude Code Review — local vs managed:** the local `/code-review` command reads `CLAUDE.md` but not `REVIEW.md`. Rules needed in both places belong in `CLAUDE.md` — [Customize Code Review](https://code.claude.com/docs/en/code-review-customize)
- **GitHub Copilot code review** (contrast): it reads custom instructions and skills from the PR **head** branch. Custom instructions for review can be toggled per repo ("Use custom instructions when reviewing pull requests"), and `excludeAgent: "code-review"` scopes an instructions file away from review — [add repository instructions](https://docs.github.com/en/copilot/how-tos/configure-custom-instructions/add-repository-instructions)
- **BMAD**:
  - `persistent_facts` entries can be literal sentences or `file:` references with globs, and the referenced contents "load as facts". Workflows also accept `skill:` references.
  - Activation order: resolve config, prepend steps, load facts, load config/vars, greet, append steps.
  - `_bmad/custom/` starts empty. A missing layer means the lower layer applies, and deleting an override restores shipped defaults. The docs advise sparse overrides because a full copy "shadows future updates".
  - Source: [Customize BMad](https://docs.bmad-method.org/customize/customize-bmad/)
- **BMAD team adoption**: `doc_standards` and `external_handoffs` are "append" arrays, so team entries stack. `extends:` templates in `_bmad/custom/facilitate-templates/` add rules without copying, letting upstream updates "still reach you" — [Adopt BMad across a team](https://docs.bmad-method.org/customize/adopt-bmad-across-a-team/)
- **OpenSpec**: every artefact prompt is assembled from `<context>` (from `config.yaml` `context`, all artefacts), `<rules>` (per-artefact `rules`) and `<template>`. Apply and archive read the context and operation guidance at execution time via `openspec instructions ... --json`. The only documented fallback is the default `spec-driven` schema — [OpenSpec customization](https://github.com/Fission-AI/OpenSpec/blob/main/docs/customization.md)
- **Spec Kit**: "every later phase is evaluated against" the constitution. Templates resolve through `.specify/templates/overrides/` first. With no preset installed, project overrides, extension contributions and core defaults "continue to apply" — [agentic-sdd.md](https://github.com/github/spec-kit/blob/main/docs/reference/agentic-sdd.md); [presets/overview.md](https://github.com/github/spec-kit/blob/main/docs/presets/overview.md)
- **Kiro**: `fileMatch` and `auto` steering load team files by glob or description match. Unresolved `#[[file:...]]` references show a visible marker instead of failing silently — [Kiro steering](https://kiro.dev/docs/steering/)
- **Codex**: empty AGENTS files are skipped. Only names listed in `project_doc_fallback_filenames` (e.g. `TEAM_GUIDE.md`) are discovered, and other names are ignored — [Codex AGENTS.md guide](https://learn.chatgpt.com/docs/agent-configuration/agents-md)
- **Claude Code skills — mechanisms a framework skill can use to read optional team files:**
  - `` !`command` `` dynamic context injection runs before the model sees the skill. A failing command aborts the whole skill invocation (exit code 1 from search commands excepted).
  - `paths:` globs limit auto-activation.
  - `${CLAUDE_PROJECT_DIR}` and `${CLAUDE_SKILL_DIR}` substitutions are available.
  - Supporting files load when referenced.
  - Source: [skills](https://code.claude.com/docs/en/skills)
- **Claude Code rules**: path-scoped `.claude/rules/` and nested CLAUDE.md load on demand when matching files are touched, which gives automatic folder-level overrides — [memory](https://code.claude.com/docs/en/memory)
- **AI-DLC 2.x** advertises "team knowledge, and learned rules" as persistent harness layers, customizable through the Harness Engineer Guide — [awslabs/aidlc-workflows](https://github.com/awslabs/aidlc-workflows)
- **Superpowers** (Jesse Vincent) is a widely cited community Claude Code plugin packaging a skills-based development workflow — [Simon Willison, Oct 2025](https://simonwillison.net/tags/skills/)

### Inferences
- Discovery patterns observed:
  - (a) Fixed well-known filename at root, plus optional per-directory copies: REVIEW.md, CLAUDE.md, AGENTS.md, constitution.md.
  - (b) Explicit include list in a config file: BMAD `persistent_facts: file:` globs, OpenSpec `config.yaml`, Codex `project_doc_fallback_filenames`.
  - (c) Glob- or description-triggered loading: Kiro fileMatch/auto, Claude `paths:` rules and skills, Cursor globs.
- A `/develop` skill reading `.ai/qa.md`, CONTRIBUTING.md or checklists would most closely follow (a)+(b): a fixed default list, extended by config.
- Missing or empty file behavior is uniformly "fall back silently to the lower layer". Kiro is the only tool that makes an unresolved reference *visible*, and Claude Code Review even hides unmatched include lines from its report. A framework that wants auditability should log which override files were found, empty, or absent.
- In Claude Code, a skill using `` !`cat .ai/qa.md` `` would abort if the file is missing, because a failing injected command aborts the skill. Robust patterns are `cat file 2>/dev/null || echo "(no team override)"` or a CLI helper that prints the resolved stack. This is a derived inference, not documented guidance.
- Reading the override files from a protected branch rather than the working tree (Claude Code Review's model) stops a PR from weakening its own review rules. Copilot code review takes the opposite choice (head branch).

### Gaps
- No public framework was found that specifically auto-reads `.ai/qa.md`-style files or `CONTRIBUTING.md` as an override convention. CONTRIBUTING.md auto-discovery is not documented by any tool reviewed.
- Claude Code Review's behavior when `REVIEW.md` is absent is implied (default review guidance applies) but not stated verbatim.
- BMAD's "Set and Maintain Project Context" page (`project-context.md`) was not read.

## 5. Expert analyses: Böckeler / martinfowler.com, Thoughtworks Radar, Simon Willison, Anthropic

### Takeaway
Expert consensus by late 2026:
- Context engineering and curated shared instructions are mainstream (Thoughtworks Adopt).
- Progressive context disclosure is the preferred loading model (Adopt, Nov 2026).
- Plugin marketplaces are the organizational distribution channel (Trial).
- SDD remains at Assess, with recurring warnings about review overload, instruction bloat, and the illusion of control that Markdown instructions give.

### Cited Findings

**Böckeler, "Understanding Spec-Driven Development: Kiro, spec-kit, and Tessl" (15 Oct 2025)**
- Defines three levels:
  - spec-first
  - spec-anchored
  - spec-as-source, where "the human never touches the code"

  Source: [martinfowler.com](https://martinfowler.com/articles/exploring-gen-ai/sdd-3-tools.html)
- Distinguishes specs from a "memory bank" (rules files, product/codebase descriptions); Kiro's steering is its memory bank — [martinfowler.com](https://martinfowler.com/articles/exploring-gen-ai/sdd-3-tools.html)
- Criticisms:
  - One workflow does not fit all sizes: Kiro turned a small bug into 4 user stories and 16 acceptance criteria.
  - Review overload from repetitive Markdown.
  - False sense of control: agents ignored instructions or over-applied the constitution.
  - Comparison with model-driven development: risk of combining MDD's inflexibility with LLM non-determinism.
  - "Spec" drifting into a synonym for "detailed prompt".

  Source: [martinfowler.com](https://martinfowler.com/articles/exploring-gen-ai/sdd-3-tools.html)

**Böckeler, "Context Engineering for Coding Agents" (5 Feb 2026)**
- Taxonomy: *instructions* vs *guidance*, plus context interfaces (tools, MCP, skills). Claude Code features: CLAUDE.md, path-scoped rules, slash commands ("now deprecated in favour of skills"), skills, subagents, MCP, hooks, plugins — [martinfowler.com](https://martinfowler.com/articles/exploring-gen-ai/context-engineering-coding-agents.html)
- Who decides to load context: the LLM (automation, but uncertain), the human (control, less automation), or the agent software (deterministic, e.g. hooks) — [martinfowler.com](https://martinfowler.com/articles/exploring-gen-ai/context-engineering-coding-agents.html)
- On sharing:
  - Sharing works best within teams with similar contexts.
  - Copying instructions wholesale leads to over-engineering and conflicting rules.
  - Plugins can distribute shared commands, skills and hooks.
  - She writes that "there are no unit tests for context engineering".

  Source: [martinfowler.com](https://martinfowler.com/articles/exploring-gen-ai/context-engineering-coding-agents.html)

**Thoughtworks Technology Radar Vol. 35 (November 2026), Techniques**
- Adopt: progressive context disclosure (keep AGENTS.md lean, defer MCP tools and skills), agent sandboxing, mutation testing.
- Trial:
  - Agent plugin marketplace: share skills, instructions, MCP and subagents org-wide via Git repos.
  - Anchoring coding agents to a reference application.
  - Feedback flywheel: session learnings become shared harness edits.
  - Risk-tiered human oversight.
  - Self-improving harness.
  - Subagents for context management.
- Assess:
  - Enterprise harness: "a thin, federated organization-wide layer" of shared skills, tools, policies.
  - Harness quality evaluation.
  - Context profiling.
- Caution:
  - Agent instruction bloat.
  - Agent skill cognitive surrender.
  - AI-driven documentation sprawl.
  - Human-in-the-loop theater.
- Earlier blips: context engineering Adopt (Apr 2026); curated shared instructions for software teams Adopt (Apr 2026); AGENTS.md Trial (Nov 2025); Agent Skills Trial (Apr 2026); spec-driven development Assess (Nov 2025).
- Source for all of the above: [thoughtworks.com/radar/techniques](https://www.thoughtworks.com/radar/techniques)
- Vol. 34 (Apr 2026), via secondary summaries and the techniques page:
  - Recommends placing CLAUDE.md, AGENTS.md or .cursorrules in the baseline repository used to scaffold new services.
  - Frames SDD and Agent Skills as "feedforward" controls, complementing feedback controls such as linters and review.

  Sources: [Thoughtworks techniques (earlier volume capture)](https://www.thoughtworks.com/en-au/radar/techniques); [Vol. 34 digest (secondary)](https://agentic-ai.readthedocs.io/en/latest/AgenticTechStack/thoughtworks-radar-vol34/)

**Anthropic, "Effective context engineering for AI agents" (29 Sep 2025)**
- Context is "a finite resource with diminishing marginal returns" (context rot, attention budget). The goal is the "smallest possible set of high-signal tokens" — [anthropic.com/engineering](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)
- System prompts should sit at the "right altitude", between brittle if-else logic and vague guidance. Start minimal and add instructions based on observed failures — [anthropic.com/engineering](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)
- Claude Code's hybrid model loads CLAUDE.md up front and retrieves the rest just in time (glob/grep). Long-horizon techniques: compaction, structured note-taking, sub-agents returning 1–2k token summaries — [anthropic.com/engineering](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)

**Simon Willison**
- "Claude Skills are awesome, maybe a bigger deal than MCP" (16 Oct 2025).
- Agent Skills as an open standard (19 Dec 2025): he calls the spec "deliciously tiny" but under-specified.
- OpenAI quietly adopting skills in Codex CLI and ChatGPT (12 Dec 2025).
- Skills in the OpenAI API (11 Feb 2026).
- Donating Agent Skills to the AAIF (22 Oct 2026).
- Source for all of the above: [simonwillison.net/tags/skills](https://simonwillison.net/tags/skills/)
- He suggested `@AGENTS.md` inside CLAUDE.md to keep a single source of truth (Oct 2025, search excerpt). Claude Code docs now document the same import pattern — [simonwillison.net (excerpt)](https://feeds.simonwillison.net/2025/Oct/25/); [Claude memory docs](https://code.claude.com/docs/en/memory)

### Inferences
- The experts converge on three design rules for a packaged AI-SDLC framework:
  - Keep always-loaded instructions lean and push detail into on-demand skills or path-scoped rules (progressive disclosure).
  - Distribute through versioned plugin marketplaces or registries, not copy-paste.
  - Make anything that must be guaranteed deterministic (hooks, CLI, CI), because Markdown guidance is probabilistic.
- Thoughtworks' "enterprise harness" (thin, federated) and "agent instruction bloat" entries line up with a model of minimal central defaults plus local overrides, with periodic pruning.

### Gaps
- Anthropic's "Writing effective tools for agents — with agents" was not fetched in this session, so no claims from it are included.
- The official Thoughtworks blip pages for Vol. 34 entries ("curated shared instructions", "context engineering") were seen only as related-blip links or secondary summaries. Their exact wording is not verified.
- The founding date of the Agentic AI Foundation and the date AGENTS.md was donated to it were not re-verified in this session. agents.md confirms only the stewardship.
