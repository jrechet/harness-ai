---
name: harness-audit
description: Audits the AI setup of a repository or a process — agents, skills, AGENTS.md / CLAUDE.md / Cursor rules, backing scripts, CLI, linters and architecture tests, GitHub Actions or another remote runner — and checks that each responsibility sits at the right layer (judgement / procedure / local logic / remote execution). Produces a fixed-format report (Markdown + JSON) with one verdict per item and a prioritised remediation plan. Use as soon as the user wants to audit, review, critique, harden, clean up or "flatten out" agents, skills, scripts, workflows or an AGENTS.md (theirs or a third-party repo's), wonders whether a skill does too much, whether a rule should become a linter or a CLI command, whether "we can cut the agent and it still works", or whether a file or an instruction line still serves now that models have changed — also in French: « audite mon AGENTS.md », « revois mes skills », « est-ce que cette règle sert encore » — even without the word audit. Do not use to write the first AGENTS.md (harness-init), to place one new piece (harness-design) or to move up a level (harness-step).
---

# Harness audit

A harness is healthy when **the agent is only an accelerator**: if you cut it, the team can still run the process with the CLI and the workflows. As soon as mandatory process lives only in a prompt or a SKILL.md, it can be skipped, misread or hallucinated. The goal of this audit is to find these leaks and say precisely where each piece must go.

## Guide the user

**Show the map first.** Before any action or question, run `python3 "${CLAUDE_PLUGIN_ROOT}/cli/harness.py" status --map --no-write <repo>` and show, in at most six short lines plus the map:
- **Goal**: find what in your AI setup is only written down when it should be enforced, what no longer serves, and say where each piece should go.
- **Plan**: 1. list everything · 2. "cut the agent" test · 3. judge each item · 4. report and remediation plan. Nothing is changed during the audit.
- **Where we are**: the map, and what is in scope (folders, files).
- **Where we are going**: a report with one verdict per item and an ordered plan; `.harness/audit.json` written for `harness status`.
- **Now**: what you read first, and whether you will ask something (a missing file, the scope).

**Offer the page.** With the map, write the picture of it: `python3 "${CLAUDE_PLUGIN_ROOT}/cli/harness.py" status --no-write --page <repo>/.harness/state.html <repo>`, and give its path: one file to open in a browser, showing the files present or missing layer by layer and the steps to the target. Write it again once `.harness/audit.json` exists: the page then carries your remarks file by file, shown apart as opinions, not as measurements. Never write that page yourself.

**Ask with context.** Say why you ask and what the answer changes; give the options in plain words and the proposed default. One decision per question.

**Plain words.** The report keeps its fixed sections, verdicts and JSON keys (they are compared from one audit to the next), but each verdict and layer is explained in plain words the first time it appears ("PUSH_DOWN: move it from written text into code that enforces it"). No undefined "guardrail" ("a test or CI check that enforces a rule"), no raw check id. Speak the language of the conversation.

## The four-layer model

Classify each observed responsibility in a layer. A responsibility at the wrong layer is a defect, even if "it works today".

| Layer | Role | Typical carrier | What belongs there |
|---|---|---|---|
| **L1 Judgement** | Decide: which kind of release, is it ready, what to do if it breaks, ask for approval | Agent (prompt, sub-agents) | Choices between options, interpretation of *structured* feedback, human dialogue, stop points |
| **L2 Procedure** | Tell: when to call what, in which order, how to read the results | Skill (SKILL.md, references) | Vocabulary, nominal sequence, abort cases, expected format of feedback |
| **L3 Local logic** | Guarantee: preconditions, computations, transformations, idempotence | Tested CLI (subcommands), or a script if truly isolated | Everything mandatory, checkable, reproducible without AI |
| **L4 Remote execution** | Act with rights: build, tag, publish, deploy | GitHub Actions / pipeline / API | What touches shared, audited resources, with secrets |

Severity rules that follow:
- A **precondition** told in L2 instead of being an `exit 1` in L3 → P1 defect (the agent can bypass it).
- An **L4 action** that can be triggered without going through L3 (the agent calls the API directly) → P1 (no guardrail, no uniform dry-run).
- **L3 logic duplicated** across several per-skill scripts → P2 (implicit, untested CLI).
- **Unstructured feedback** (the agent reads logs) where L1 must decide → P2 (hallucinated successes).
- **L1 judgement hard-coded** in a script ("if the ticket contains X then…") → P3 unless it blocks a real case.

## Steps

### 1. Inventory — judge nothing before seeing everything
List exhaustively: agents (definitions, system prompts, sub-agents), instruction files (`AGENTS.md`, `CLAUDE.md`, `.cursor/rules`, `copilot-instructions.md`, and their `@includes` or equivalents loaded automatically), skills (SKILL.md + references + `scripts/`), backing scripts (`.mjs`, `.sh`, `.py`), existing CLI commands, L3 guardrails (custom linters, Checkstyle, ArchUnit, check scripts, hooks, PR templates), workflows (`.github/workflows/*.yml`, inputs, secrets, `workflow_dispatch`), the `.harness/` folder if it exists (last state, last harvest, last audit: a signal collected and never acted on is a finding), and the process contracts or documents if any. For each item, note: path, *declared* layer (where it is filed), *actual* layer (what it really does), who calls it, what it calls.

Build the call graph before any analysis. If an item has no caller, that is already information (candidate BLOCK or MERGE).

If files are missing (a script referenced but absent, a workflow named in a skill but not found), ask for them rather than assume; the absence itself is a finding to report.

### 2. The "cut the agent" test
Before the details, answer one global question: *if we delete all agents and skills, can a hurried human or a cron run the process end to end with the CLI + workflows?* Walk the nominal process step by step and note each step that exists **only** in a prompt. This walk feeds the health score and the "Leaks" section of the report directly.

### 3. Item-by-item analysis
For each item, ask in order:

1. **Process truth**: is there a mandatory step here that is not encoded in L3/L4?
2. **Preconditions**: are they checked by code (non-zero exit, typed message) or told?
3. **Feedback**: is the output structured (JSON / exit codes / run URL / artifacts / possible next action) or free text to interpret?
4. **Dry-run**: can you get the plan without executing? For any irreversible L4 action (tag, publish, prod deploy), is there a human stop point between plan and execution?
5. **Duplication**: does this logic exist elsewhere (another script, CLI, workflow)?
6. **Testability**: does the L3 logic have tests? Can it run outside the agent?
7. **Rights**: are secrets and permissions held in L4 only?

### 4. Verdict
Give exactly one verdict per item:

| Verdict | Meaning | Example |
|---|---|---|
| **KEEP** | Right layer, right scope | Skill that describes the sequence and points to `release plan` / `release run` |
| **INLINE** | Too small to exist alone, to absorb into its caller | 10-line script that formats an argument before calling the CLI |
| **PUSH_DOWN** | Goes down one layer (L2→L3, L3→L4) | "develop is green" check written in the SKILL.md → CLI subcommand with `exit 1` |
| **PROMOTE** | Goes up one layer (L3→L2, L2→L1) | Script that decides the release type alone → decision given back to the agent, the script only exposes the options |
| **MERGE** | Merge with another item (duplicate) | Three `.mjs` that call `gh workflow run` with variations → one subcommand |
| **SPLIT** | Mixes several layers, to separate | Skill that contains procedure *and* version computation code |
| **BLOCK** | Dangerous or dead: remove or neutralise before anything else | Agent that can trigger the prod deploy without dry-run or approval; script never called |
| **REMOVE** | Instruction that no longer changes what the agent does, or degrades it: to remove, with its reason | A generated CLAUDE.md that paraphrases the tree; an instruction written to work around a tool limit that is gone |

Give a priority: **P1** = risk of an incorrect or uncontrolled release/deploy, **P2** = fragility or duplication that will end up breaking, **P3** = hygiene.

BLOCK targets an item that acts (script, agent, workflow). REMOVE targets instruction text, a whole file or a line: see "Relevance review".

### 5. Remediation plan
Order by priority then by dependency (create the CLI subcommand *before* deleting the scripts that duplicate it). Each item: verdict, item, concrete action (file to create/modify/delete), check criterion (how we will know it is done), and an explicit human approval point for any BLOCK or deletion. Change nothing yourself during the audit: the report is the input of a separate remediation step, item by item.

## Instruction files and relevance review

An AGENTS.md / CLAUDE.md is a pure L2 item, audited with its own questions (told rule vs enforced rule, context cost, justification, maintenance, what is missing). And every instruction line goes through the relevance review: does it still change what the agent does? Both are in `references/instruction-files.md`: read it whenever an instruction file is in scope, or when the user asks what no longer serves.

## Report

Always produce both outputs, in this order: the Markdown (human reading) then the JSON (machine reading, to follow the evolution from one audit to the next). The exact format is in `references/report-template.md` — read it before writing the report and keep the sections and keys exactly, even if a section is empty (then write "None"). A stable format lets you share and compare two audits; an improvised section breaks that.

The Markdown report opens with the map: the output of `status --map` after `.harness/audit.json` is written, and one line saying what the audit changes on it (the level that depended on an audit, the urgent items it found).

In the report, each finding cites its path and, if possible, the line. A finding without a locatable proof does not go in.

Also write the JSON block alone to `.harness/audit.json` in the audited repository: that is what `harness status` reads for the layer view and level 3. If the user wants no file in their repo, say so and give the JSON in the answer.

Before finishing, run `python3 "${CLAUDE_PLUGIN_ROOT}/cli/harness.py" audit check <repo>/.harness/audit.json` and fix the file until it passes: `harness status` leaves aside a file that fails this check and says why.

## What is not a defect

- A long skill because it describes many abort cases: that is procedure, it is its place.
- An isolated `.mjs` script that *only* translates a CLI call for an environment without the CLI installed — as long as it adds no logic.
- An agent that asks for confirmation "too often": prefer this defect to the reverse; report it as P3 only.
- Judgement left to the agent on genuinely open choices (communication order, release message): that is L1.

## Common pitfalls

- Judging the layer by the folder where the file is filed rather than by what it does.
- Recommending PUSH_DOWN everywhere: a CLI that encodes judgement becomes rigid and the team will work around it.
- Forgetting the workflows themselves: a `workflow_dispatch` without a `dry_run` input or without a protected `environment` is an L4 leak, not an agent problem.
- Ignoring drift between branches: when a repo has a work branch and a prod branch, "a fix on one is ported to the other" is a told rule as long as no job compares them (`git rev-list A..B` not empty → failure). It is an L4 guardrail to propose explicitly, and it must live on the default branch to be scheduled.
- Counting "readable" feedback as structured: if the agent must look for "SUCCESS" in a log, it is not structured.
- Reporting a healthy item to have something to say. A harness in good shape gives a short audit: almost all KEEP, and the two or three real defects.
- Removing what you do not understand. An odd, dated rule often has an incident behind it: look for it in the ADRs and post-mortems, otherwise ask.
- Classing a style or naming convention among the leaks: a leak is a rule whose violation has a consequence on the product, production or security. Style without a guardrail is a useless line, to remove, or a pointer to the linter: never a leak, and P3 at most.
