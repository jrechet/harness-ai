---
name: harness-design
description: Helps create or review a skill, an agent, a tool or a rule by saying where each piece goes — a line in AGENTS.md, a skill, a sub-agent, a CLI subcommand, a hook, a permission, an MCP server, a CI check, a managed setting, or nothing — and why. Splits the request, answers the closed questions of the `harness place` grid, asks the user only what is a decision, shows the plan, then sets up the files on agreement. Use when the user wants to "create a skill", "make an agent that…", "add a rule", "tool up" a task, wonders "skill or agent?", "should this be code?", "where do I put this?", or asks to review a specific skill, agent or instruction — also in French: « créer un skill », « faire un agent qui… », « ajouter une règle », « skill ou agent ? », « où je mets ça ? » — even without naming the skill. Do not use to audit a whole harness (harness-audit), to write the first AGENTS.md (harness-init) or to go up a level (harness-step).
---

# Harness design — each piece in its place

A request for a skill or an agent almost always mixes several things: a procedure, a check that must hold, a computation, a permission, a judgement. Filed together in a SKILL.md, the check becomes a sentence the agent can skip. This skill splits the request and gives each piece its place **before** a line is written.

Three rules that are not negotiable:
- **The place comes from `harness place`, not from your opinion.** If a destination seems wrong to you, it is an answer that is wrong: change it and say why. If no honest answer leads to the right place, the grid has a hole: tell the user, do not work around it.
- **One piece, one nature.** What mixes two natures is cut in two.
- **Nothing is set up without agreement, and only what the plan places.** No empty file "for later".

## Guide the user

**Show the map first.** Before any action or question, show in at most six short lines:
- **Goal**: decide where each part of what you want should live (a sentence for the agent, code, a CI check, a setting…), so that what must hold cannot be skipped.
- **Plan**: 1. the need in one sentence · 2. split it into pieces · 3. answer the grid's questions · 4. show the plan · 5. set up the files after your OK.
- **Where we are**: what exists today (the artifact under review, or nothing yet); if the repository has a harness, the one-line summary of `python3 "${CLAUDE_PLUGIN_ROOT}/cli/harness.py" status --map --no-write <repo>` ("you are here").
- **Where we are going**: a plan with one place per piece, then the files set up, if you agree.
- **Now**: what you do next, and whether you will ask something.

**Ask with context.** Ask only what is a decision. For each question, say why it is asked and what the answer changes (the place of the piece); give the options in plain words and your proposal as the default. One decision per question; when several pieces need the same kind of decision, one line per piece in the same message.

**Plain words.** The grid's ids (`incident`, `bypass_rule`, `ci_check`…) and verdicts are for the plan file, not for the user: say "what does it cost when this is not respected?", "who must not be able to skip it?", "a check in the CI that blocks merging". Speak the language of the conversation; files written in the user's repository follow that repository's language.

## Steps

### 1. The need, in one sentence
Rephrase what the user wants to obtain, not the artifact they named: "a release skill" is a form, "every release is tagged, published and announced without omission" is the need. In review, read the whole artifact (skill, agent, instruction, hook): its sentences and steps are the pieces.

### 2. Split
`python3 "${CLAUDE_PLUGIN_ROOT}/cli/harness.py" place grid` gives the natures and their definitions. Split the need into pieces of a single nature. Signs of a piece to cut: "and check that", "without ever", a step followed by a condition. A procedure that contains a mandatory step gives two pieces: the procedure, and the rule or computation it calls.

### 3. Answer the questions
For each piece, answer the grid's questions from the conversation and the repository. Read what answers without asking: the forge and its CI, `.claude/settings.json`, the declared MCP servers, `.harness/state.json` if it exists. `python3 "${CLAUDE_PLUGIN_ROOT}/cli/harness.py" place one <question=answer>…` says which question is still missing for a piece.

Ask the user only what is a decision, not a fact. In practice, almost always two questions: what it costs when it is not respected (`incident`), and who must not be able to bypass it (`bypass_limit`, `bypass_rule`). Ask them all at once, one line per piece, with your proposal, why you ask, and what the answer changes.

### 4. The plan
Write the pieces in a JSON file outside the repository, then run `python3 "${CLAUDE_PLUGIN_ROOT}/cli/harness.py" place plan <file>` and show the plan as is, followed by one plain sentence per piece saying where it goes and why:

```json
[{"piece": "Never push to main", "answers": {"nature": "limit", "bypass_limit": "dev"}, "current": "agents_md"}]
```

`current` only serves in review: it is the id of the destination where the piece lives today (`place grid` lists them). A piece that does not exist yet has no `current`. The plan then gives a verdict: KEEP, PUSH_DOWN, PROMOTE, MOVE (same layer, another place) or REMOVE. No verdict while an answer is missing.

For a state of play to read or share, `python3 "${CLAUDE_PLUGIN_ROOT}/cli/harness.py" report from-place <file> --kind skill --name <name> -o <report.html>` writes the same thing as one page: what is evaluated, expected, observed, suggested. In review, each piece then carries `"evidence": ["path:line"]`: a gap without proof is refused. Write the page outside the repository, unless the user wants it inside.

Exit code 3: an answer is missing, go back to step 3. Exit code 2: invalid input, fix it. Under the plan, one line per piece you could not place, with the reason.

### 5. Set up, on agreement
Ask for agreement on the plan, then set up for each piece the smallest file that makes it exist in its place, in the user's repository:

| Destination | What is set up |
|---|---|
| Skill | `SKILL.md`: when to use it and when not, the sequence; each guaranteed step calls the command of the matching piece |
| Sub-agent | `.claude/agents/<name>.md`: tools listed one by one, structured return format |
| CLI subcommand, hook, workflow | The command and a test that fails first; without a CLI in the repository, a script in the project's language or a target of the existing launcher (Makefile, manifest scripts). Then its wiring: hook in `.claude/settings.json`, or workflow |
| Permission | The `deny` or `ask` rule in `.claude/settings.json` |
| MCP server | Its declaration, and the rights to request for the server's account |
| Delivery workflow | The workflow with its plan mode (dry-run), and the subcommand that triggers it. The protected environment and its secrets are set on the forge: write down the setting, do not do it |
| Blocking step of the delivery workflow | The step in the workflow, before the first irreversible action, and the command it calls with its test |
| Server-side protection, managed settings, organisation check | Nothing in the repository is enough. Write down the setting to make and who can make it (forge administrator, platform team). Do not do it yourself |
| A line in AGENTS.md | In harness-init's format: the rule, `Why: …`, `Enforced by: <path>` or `(unverified)`, `[YYYY-MM]` (in a French repository: `Pourquoi :`, `Vérifiée par :`, `(non vérifiée)`) |
| Folder AGENTS.md | The same line, in the AGENTS.md of the folder concerned |
| Document read on demand | The file in `docs/agents/`, and the line that points to it |
| Agent judgement, in the skill | No file: a sentence in the skill that says where the agent decides, and between which options |
| Judge and human review | The measurable part goes back through the grid; the rest goes in the review skill or sub-agent |
| Nothing to write | Nothing. In review, remove the line |

### 6. Report, then stop
Open with the updated map: steps done, what is now in place and where. Then what remains to be done by someone else (server-side settings); what is not checked. No "while I'm at it".

## Reviewing a skill or an agent
Same steps, with `current` filled in for each piece. This skill reviews one artifact or one request. For a whole harness (call graph, "cut the agent" test, relevance review), use harness-audit.

## Common pitfalls
- **Confusing limit and rule.** "Never push to main" bounds an action of the agent (`limit`). "No secret in the code" requires something of the result (`rule`). A precondition ("do not start if…", "refuse without…") is a rule, even without severity: `incident=forget` gives it its check. Do not file it as a limit to get a lock.
- **A computation whose error is an incident.** The grid does not ask for the severity of a computation: it places it where it runs. If an error in this computation is an incident, cut it in two pieces: the computation, and the rule that checks its result ("the published version follows the commits"), which goes through `incident`.
- **Answering according to effort.** `bypass_rule=agent` to avoid touching the CI is answering the wrong question: it is about what a bypass would cost.
- **Pushing everything into code.** If a program cannot check it with the same answer every time, `checkable` is `no`: hard-coded judgement becomes rigid, and the team works around it.
- **A sub-agent to look tidy.** Without a separate context, an independent look, different rights or parallelism, it is a skill, or the session's judgement.
- **Getting `current` wrong in review.** `current` says where the piece is held today, not in which file the sentence is written. A choice the skill leaves to the agent has `current` `session`. An AGENTS.md rule that cites an existing, blocking CI check has `current` `ci_check`: open the workflow to check it. If you cannot open it, do not decide: ask, or leave the piece out of the plan and say so below. Whether a check is *required* cannot be read in the repository: it is a forge setting (branch protection, ruleset). If you have access, read it; otherwise keep `ci_check` and write under the plan "to confirm: is the check required?".
- **Asking the plan what it does not say.** The plan places, it does not rewrite. A step to rephrase, a tool missing from a sub-agent, a wrong sentence: one line each under the plan, not a piece.
- **Writing what the agent finds alone.** Manifest commands, tree: `scope=discoverable`, nothing to write.
- **Showing the user the grid's ids instead of plain questions.**
