---
name: flow-why
description: Answers "do I need LangChain, LangGraph, Temporal, a workflow engine or Rust for this?" before anything is built — shows the cases the `harness flow fit` command knows, with the date of its facts, asks what the user is building, how many tickets a week, whether the phases are started by hand and what was measured on their own runs, then gives the command's verdict word for word, the doc page that explains it, what it costs and the measurable symptom that would change the answer. Changes nothing in the repository. Use when the user asks "do I need LangGraph / Temporal / a workflow engine?", "is LangChain still useful?", "what is LangGraph for?", "should we write this in Rust?", "is CI enough to run our agent on tickets?", "which orchestrator for our agents?" — also in French: « est-ce qu'il me faut LangChain / LangGraph / Temporal ? », « à quoi sert LangGraph ? », « faut-il un moteur de workflow ? », « on l'écrit en Rust ? », « la CI suffit-elle ? » — even without naming the skill. Do not use to write the definition of a ticket workflow (flow-map), to say where one step of an existing definition goes or whether that step needs an engine (flow-place), or to place a skill, an agent or a rule (harness-design).
---

# Flow why — which tool, if any, before anything is built

A team that wants an agent to work on its tickets is told to pick a framework first. Most of the time the honest answer is "none yet", and the thing that would change it is a number the team can measure on its own runs. This skill gets that answer from a command, not from an opinion.

Three rules that are not negotiable:
- **The verdict comes from `flow fit`, not from you.** You do not soften it, extend it or add a tool it did not name, and you give it even when you expected another. If an answer contradicts something the user said earlier in the conversation, quote both and ask which holds, once, before running; after the run, change an answer only when the user corrects it themselves.
- **A number the user did not give is "not measured".** Never guess one, never round "I think it is rare" to 0, and never read "not measured" as "fine".
- **This skill changes nothing.** It writes one answers file, outside the repository unless the user chooses otherwise. It wires no pipeline, starts no agent, promises no run.

## Guide the user

**Show the map first.** Before any question, run `python3 "${CLAUDE_PLUGIN_ROOT}/cli/harness.py" flow fit --questions` and show, in at most six short lines plus the cases it prints:
- **Goal**: say whether you need one of these tools for what you are building, and what would change that.
- **Plan**: 1. the cases the command knows · 2. your answers (asked once, all together) · 3. the answers file · 4. the verdict, as printed · 5. the page that explains it, the cost, the symptom to watch.
- **Where we are**: the five things one can be building, in the command's own words, and "Facts dated ‹date›" as it prints it. Nothing is answered yet.
- **Where we are going**: one verdict for your case. No file in your repository.
- **Now**: the questions below.

**Ask with context.** Say why you ask and what the answer changes; give the options in plain words, the default, and what taking it means. One decision per question, all questions in one message.

**Plain words.** The keys of the answers file (`own_agent_app`, `runs_paid_twice`…) are for the file. To the user, use the sentence the command prints next to each key. When the verdict itself prints a key, keep the line as it is and add that sentence after it. Speak the language of the conversation. When the conversation is not in English, show the command's lines as printed, then say each in the user's language right under it: never the translation in place of the printed line, never the printed line alone. When an output you show names a command (`flow fit <file>`) or a page (`decide.md §3`), say once that the command is `python3 "${CLAUDE_PLUGIN_ROOT}/cli/harness.py" flow …` and that the page is under the plugin's folder, and give its full path.

## Steps

### 1. The questions, from the command
Everything you ask comes from the output of `flow fit --questions`: the choices, the eight symptoms, what each number counts, the threshold. Do not add a question, do not drop a symptom.

### 2. Ask, once
**A request to understand a tool** ("what is X for?", "is X still useful?"), not to decide for a project: read the tool's page first (table of step 5), answer in two or three sentences with the page's path and its date of facts, cite its last section, then offer once the verdict for the user's own case. Ask the four parts below only on a yes.

One message, four parts. Fill in what the conversation already said and show it as "understood: …" so the user can correct it.
1. **What are you building?** The five choices, in the command's words. Why: it decides which row of the table applies; for four of the five, the symptoms no longer decide. No default: if the request does not say, ask.
2. **How many tickets a week go through this path?** A number, an average is fine, 0 if none yet. Why: with 0, phases started by hand and no symptom measured above its threshold, the answer is that there is nothing to chain yet.
3. **Does a person start each phase today, or does something already start the next one?** Why: with no ticket yet, "a person starts each phase" gives "by hand may be enough"; "something already starts the next one" gives the ticket-and-CI answer. No default: ask.
4. **For each of the eight symptoms: a number from your own runs, or "not measured".** Show each with what its number counts. Why: on a ticket workflow, a measured symptom is the only thing that calls for more than the ticket and the CI. Default: "not measured" for all, which means the verdict lists them as unknown, not as fine.

An answer like "rarely", "a few", "never, I think" is not a number: write "not measured", and say so.

### 3. Write the answers file
Start from the example file the command prints. Default place: a file in a new temporary folder (`mktemp -d`), outside the repository; give its full path. Write it in the repository only if the user asks, at the path they give. Show the file before running.

### 4. Run, and give the verdict word for word
`python3 "${CLAUDE_PLUGIN_ROOT}/cli/harness.py" flow fit <answers file>`. Show the whole output as printed: verdict, why, what would change the answer, source, and the symptoms not measured. Say once that "report" in the source line is `${CLAUDE_PLUGIN_ROOT}/docs/workflow-harness/report.md`. Leave out the command's "Next:" line: step 6 replaces it.

**Refused (exit code 1).** The command lists each answer to fix. Fix a misspelt key yourself; for a missing or unreadable answer, ask the user that one question, with its context, then run again. Never fill it in to get a verdict. Exit code 2: the file is missing or is not JSON; fix the file.

### 5. Explain with the right page
Read the page in `${CLAUDE_PLUGIN_ROOT}/docs/workflow-harness/` before explaining, give its path, and quote its "Date of the facts" line. Do not copy the page: two or three sentences, then the pointer. Each page ends with "The symptom that would make you need it": that section is the one to cite.

| The verdict, or the tool the user named | Page to read |
|---|---|
| "Ticket state and CI are enough." | `ci-as-engine.md`: how a ticket state and short jobs make a flow, and its limits |
| One or more symptoms above their threshold; Temporal or any workflow engine | `engines.md`: what an engine gives and does not give; `decide.md` section 3 for the smallest fix to try first |
| "By hand … may be enough" | `decide.md` section 7 |
| Your own agent application; LangGraph | `langgraph.md` |
| LangChain, whatever the verdict | `langchain.md` |
| An agent product for users | `engines.md`, the section on who uses one |
| The same change across many repositories | `decide.md` section 1 |
| A long-lived orchestrator, a tool server, a binary; Rust, whatever the verdict | `rust.md` |
| What it costs, for every verdict | `costs.md`; for an engine, also `engines.md`, the section on its price |

If the user named a tool the verdict does not mention, read its page too and say in one sentence why the verdict does not call for it. A cost is a sentence quoted from the page, never a number alone and none from memory: for "Ticket state and CI are enough.", the published prices per run of `costs.md` section 1 and the sentence of its section 2 that says the estimate per ticket is only arithmetic; for an engine, `engines.md` section 5. Counting what a ticket really costs from recorded runs is not built yet: say so if asked.

### 6. Hand over, then stop
- Verdict "Ticket state and CI are enough.": offer **flow-map**, the skill that writes the workflow's definition file. Offer once; the user decides.
- A symptom above its threshold on a ticket workflow: the smallest fix the command names comes first, and the team applies it; this plugin builds none of them. No command of this version says which step a symptom comes from: `flow place` reads only whether a step must resume from its middle, not symptoms measured on runs. Say so. If no definition exists, offer **flow-map** once; offer **flow-place** only if the user asks where a step lives.
- "By hand may be enough": no handover; the path is the skills of the `ai-sdlc` plugin of the same marketplace (ticket, dev, qa, secu, review, ship), run one after the other by a person. Say they are a separate plugin to install, and that `flows.md` section 5 shows where each one fits.
- Any other case: stop at the explanation. This plugin builds nothing for it.

## Report
Always the same format:
- **The map, updated**: the five steps, all done, or where it stopped and why.
- **The verdict**: the command's output, unchanged.
- **Why, in your words**: two or three sentences, the page read, its date of facts.
- **What it costs**: from `costs.md` or `engines.md`, with the page's own caution.
- **What would change this answer**: the line of the command, and how the user could measure it on their runs.
- **Not measured**: each symptom listed as such, in plain words. Not counted as fine.
- **Files**: the answers file, full path. Nothing else was written.
- **Questions**, numbered, each with why it is asked and the default, if there are any.
- **What comes next**: the handover of step 6, or nothing.

## What the result proves, and what it does not
Everything here is on paper. Nothing ran, and nothing was measured: every number is one the user typed. The verdict says which row of a dated table matches those answers; it does not say the workflow will work, what it will cost for this team, or that a symptom listed "not measured" is absent. The facts carry a date: tools change, and the pages say what to check again. The cost is a quoted line of a dated page, not a figure a command computed. A verdict is worth asking again when a symptom gets its first real number.

## Common pitfalls
- Answering from what you remember about LangGraph or Temporal instead of the page or the command.
- Turning "we never saw that" into 0. Not seen and counted at zero are two different answers: ask which it is.
- Reading a verdict with eight symptoms "not measured" as a clean bill of health. It says nothing was found because nothing was looked for.
- Fixing a refusal by inventing the missing answer.
- Presenting an engine as the answer to an agent that loops: the command says an engine retries it faithfully.
- Deciding yourself whether the count of steps with their own retry rule is "many": the command names no threshold, it is the user's call.
- Applying the symptoms to a case that is not a ticket workflow: the command lists them and says they did not decide.
- Showing the user the keys of the file instead of the sentences.
- Writing the answers file in the repository without being asked, or starting the definition "while we are here": that is flow-map, after a yes.
- Citing a command of the run side as something to launch: beyond `flow fit`, `flow new`, `flow check`, `flow place`, `flow status` and `flow next`, nothing is built yet.
