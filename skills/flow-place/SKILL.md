---
name: flow-place
description: Says where each step of a team workflow belongs — a skill for the agent, code, a state on the ticket, a human gate, no gate at all, a shared CI workflow, a fan-out by script, or a workflow engine — by running `harness flow place` on the flow's definition file and explaining each line. For a step the command leaves open, asks the questions it names, writes the answer in the definition only with agreement, and runs the command again; ends with the command's verdict for the whole flow, word for word. Use when the user asks "is a skill enough for this step of our flow, or do I need code?", "where does this step go?", "does this step of our flow need an engine?", "is this gate useful?", "place the steps of our flow" — also in French: « un skill suffit ou il faut du code ? », « où va cette étape ? », « cette étape de notre flux a-t-elle besoin d'un moteur ? », « ce point de validation sert-il ? » — even without naming the skill. Do not use for one piece inside one repository, such as a rule, a script, a linter or a hook (harness-design), to write the flow's definition when none exists (flow-map), or for a question about a tool such as LangChain, LangGraph or Temporal (flow-why).
---

# Flow place — each step of the flow in its place

A team workflow takes a ticket to a pull request, or further, with a coding agent doing part of the work. Each step lives somewhere: in a program, in a skill, on the ticket, in a person's hands. Put in the wrong place, a check becomes a sentence the agent can skip, and a wait becomes a job that burns money. This skill reads the placement from the command and explains it.

Three rules that are not negotiable:
- **Every place and the verdict come from `flow place`, never from your opinion.** You report a place even when you expected another. Only when the user disagrees with a place: name the answer that decided it (the "Decided by" part), ask them that question again, and write their answer only with agreement, said openly ("I change `survives` of `backfill` from `midway` to `restart`, because you said…"). If no honest answer leads to the place they expect, the grid has a hole: say so, do not work around it.
- **Nothing is written without agreement, and only the keys agreed.** Without agreement, this skill changes nothing.
- **It places, it does not build.** No pipeline wired, no agent started, no run promised.

## Guide the user

**Show the map first.** Before any question, run `python3 "${CLAUDE_PLUGIN_ROOT}/cli/harness.py" flow place <file>` (the definition is usually `.harness/flow/<name>.json`) and show, in at most six short lines plus the command's output as is:
- **Goal**: know, for each step of your flow, where it lives, and whether any step needs a workflow engine.
- **Plan**: 1. read the placement · 2. answer what the definition leaves open · 3. write those answers after your OK · 4. read the placement again · 5. one sentence per step and the verdict.
- **Where we are**: the output of `flow place`, one line per step, then its verdict.
- **Where we are going**: every step placed, and one verdict for the whole flow.
- **Now**: what you do next, and whether you will ask something.

**Ask with context.** For each open step: why you ask (the command cannot place the step without it), what the answer changes (the two places it leads to), the options in plain words, the default and what taking it means. One decision per question; all open steps in one message, one line per step.

**Plain words.** A key or a value (`survives`, `midway`, `can_judge`) is never shown without what it means. Say "must it go on from its middle after a crash, or may it start again?", not "restart or midway?". Speak the language of the conversation; the definition follows the language of the user's repository. When the conversation is not in English, show the command's lines as printed, then say each in the user's language right under it: never the translation in place of the printed line, never the printed line alone. When an output you show names a command (`flow status <file> --map`) or a page (`decide.md §3`), say once that the command is `python3 "${CLAUDE_PLUGIN_ROOT}/cli/harness.py" flow …` and that the page is under the plugin's folder, and give its full path.

## Steps

### 1. Find the definition, or hand over
The question decides before the file does:
- The question is whether a tool or an engine is needed and no definition exists, or it names a product (LangChain, LangGraph, Temporal, Rust): hand over to **flow-why**.
- The question is about one piece inside one repository (a rule, a script, a linter, a hook, a required CI check), or no team workflow is in the question: hand over to **harness-design**. `flow place` hands out no hook and no single CI job; `harness place` does.
- The user wants the steps of a team workflow placed and no definition exists: hand over to **flow-map**, which writes one. Do not invent steps here; if the step asked about is not in the definition, say so: adding a step is flow-map's work too.
- One file in `.harness/flow/`: take it and say which. Several, and the request names none: list them with their ticket type and ask which one; that single question may come before the map. Never place two flows in one go.
- Exit code 2: the file is unreadable or the usage is wrong. Show the message; fix nothing by guessing.

### 2. Read the placement
Each line reads: the step's name, who performs it, the place, then "Decided by" with the question that ended the walk and the answer read from the file. A gate's line ends with who judges and what they are shown. `${CLAUDE_PLUGIN_ROOT}/docs/workflow-harness/decide.md`, section 4, explains every part of the output: read it before you explain a line. For a gate placed with the answer yes, say who judges and what they are shown, and ask once whether that person confirmed it: a yes that came with the template is nobody's answer. If they did not, list it under Questions with the judge's name.

### 3. Ask what is open
A step that "cannot be placed yet" has a second line that names the key to add, its allowed values and every other key the step still lacks. Ask for the key it names and for every key listed after "Also needed", one line per key, all in the same message, and say which later answers stop mattering if an earlier one ends the walk (an answer that sends the step to an engine makes the rest unneeded). Take the meaning from this table (the full text of each question is in decide.md, section 1; every key is in `${CLAUDE_PLUGIN_ROOT}/docs/workflow-harness/flow-format.md`):

| Key | The question, in plain words | What the answer changes | Proposed default |
|---|---|---|---|
| `survives` | After a crash, may the step start again from its beginning (`restart`), or must it go on from its middle, never run twice, or be replayable step by step (`midway`)? | `midway` sends the step to a workflow engine; `restart` goes on to the next question | `restart`: a wait of days is a state on the ticket, not a long step |
| `units` | Is the work one unit (`one`) or tens of independent units (`many`)? | `many` makes it a fan-out by script, one writer per unit | `one` |
| `repositories` | Does one repository need this step (`one`) or several (`several`)? | `several` makes it a shared CI workflow with an owner | `one` |
| `weak_model` | Is the step here only because today's model is weak (`yes` or `no`)? | `yes`: a skill with its model and date written in it, tested again at each model release | `no` |
| `can_judge` | Can the person who approves really read what they are shown and refuse it (`yes` or `no`)? | `no` means "no gate here": the command refuses until the judge has something to read or the gate is removed (step 5) | None. Only the person named as judge answers. If the user is not that person and cannot ask now: write nothing, and list it under Questions with the judge's name. Write `no` only when the user says that nobody can read and refuse what is shown |

The defaults are this skill's proposals, not measurements: say so, and say what taking them means ("with these three defaults the step lands on a skill"). A value the grid does not know (`"can_judge": true`) is reported by the command as such: ask the same question.

### 4. Write the answers, on agreement, then read again
Show the exact keys and values you will add, step by step, and wait for the OK. Edit only those keys. Then, and also when nothing was open and nothing was written, run both and show both outputs:
- `python3 "${CLAUDE_PLUGIN_ROOT}/cli/harness.py" flow place <file>`
- `python3 "${CLAUDE_PLUGIN_ROOT}/cli/harness.py" flow check <file>`

The two commands answer two questions: `flow check` looks at the shape of the flow (loops, waits, spending without end), `flow place` at where each step lives. Each can pass while the other refuses, and each says so in a note. A refusal of `flow check` is reported as is; fixing the shape of the flow is flow-map's work.

### 5. One sentence per step
For each step, one sentence built from the command's line: the place in the command's own words, the question that decided, and where decide.md explains it. Steps that share the same place and the same deciding question get one sentence together. When the question is about one step, show the whole output once, then explain that step's line only.

| The command says | Plain meaning | Read in decide.md |
|---|---|---|
| this is code | A tested command, started by a short CI job; never a prompt | section 1, "Is the right output determined by the inputs?" |
| a skill is enough | The agent, inside this one step, guided by a skill; a check in code should follow | section 1, last question; section 5 |
| a skill is enough, with its date | The same; the model and the date are written in the skill file. The command only reminds, nothing checks it | section 1, last question |
| the ticket holds this | A state on the ticket or the pull request; nothing runs while it lasts | section 1, "Who performs this step?"; section 6 |
| this is a human gate | A state only a human account may set; the judge is shown something they can refuse | section 1, second question |
| no gate here | A refusal: nobody can judge this. The command exits with 1 until the gate is removed or the judge has something to read | sections 2 and 5 |
| this is a shared CI workflow | One versioned workflow with an owner, used by several repositories | section 1, "How many repositories" |
| this is a fan-out by script | A script starts one writer per unit; never a swarm of agents | section 1, "many independent units" |
| this would need an engine | A workflow engine holds the step. An answer, not a failure: try the cheap fixes first | section 3; then `engines.md` and `ci-as-engine.md` in the same folder |

When you quote a fact from one of these pages, give its "Date of the facts" line. Do not copy the pages: point to the section. A hook or a single CI job is never an answer of this command: for those, name harness-design.

On "no gate here", write nothing. Put the choice to the user under Questions, in this order: 1. give the judge something they can read and refuse (name what: a shorter plan, a summary of the diff, a test result), then the judge answers again; 2. remove the approval, which means nobody decides at this point: say in one sentence what then happens without a person (before a merge: the flow merges on the agent's work alone), and never propose it as the default. Either one changes the shape of the flow: that is flow-map's work, done after the user's word. Never set `can_judge` to `yes` to get exit code 0.

### 6. Report, then stop
Always the same format:
- **The map, updated**: steps of the plan done, and the last output of `flow place`.
- **Step by step**: the sentences of step 5, in the order of the file.
- **What changed**: the keys written in the definition, each marked "your answer" or "my proposed default, accepted"; or "nothing was changed".
- **Verdict**: the command's "Verdict:" line, word for word, and under it each "A gate nobody can judge" line, word for word.
- **`flow check`**: when it holds (exit code 0), its first line as is, and its "Careful:" line if it prints one; when it refuses (exit code 1), every line, as is.
- **What is not proven**: see below.
- **Questions**, numbered, each with why it is asked and the proposed default, if any remain.
- **What comes next**, one line: a step would need an engine → the cheaper fix of decide.md, section 3, then flow-why for the product; `flow check` refuses or a gate must go → flow-map; otherwise `python3 "${CLAUDE_PLUGIN_ROOT}/cli/harness.py" flow status <file> --map` gives the level reached on paper. Wiring a step is not built yet.

## What the result proves, and what it does not

Everything here is on paper. `flow place` reads the answers found in the file; after flow-map most of them are the template's, and nobody on the team gave them. It runs no agent, calls no forge, measures nothing. "No step needs an engine" means no step answered `midway`; it does not mean the flow works on real tickets. The other signs that an engine is needed (runs that die and pay twice, two runs on one ticket) are read from real runs, which this version does not do: decide.md, section 3, lists them, and a number counts only if the user typed it. A verdict "no step needs an engine" does not answer a symptom `flow fit` named: the two commands read different things. A place decided by a default you accepted says what the skill proposed, not what your team observed. Whether a judge can judge is the judge's word, not a check.

## Common pitfalls
- Asking questions before showing the command's output.
- Rewording the verdict, or softening "no gate here" into "a light gate".
- Answering `midway` because a step waits for days: the wait is a state on the ticket; only a step that must resume in its middle goes to an engine.
- Answering `can_judge` yourself, or `yes` to keep a gate "for comfort".
- Proposing another answer because you expected another place: an answer changes only when the user disagrees and answers the deciding question again.
- Writing a key the user did not agree to, or tidying the rest of the definition "while I'm at it".
- Reading "this would need an engine" as an order to install one: decide.md, section 3, gives the cheaper fix to try first, and the choice of a product is flow-why's question.
- Placing a rule, a hook or a linter of one repository with this command instead of handing over to harness-design.
- Showing `durable_engine` or `ticket_state` to the user instead of the command's plain words.
