---
name: flow-map
description: Writes down a team's path from a ticket to production as one checked definition file — shows first the reference flow for the ticket type (each step done by a program, an agent, a person, or nobody while the run waits, with the points where a run can stop on purpose) and the level of the repository the flow will write in, asks once which ticket type, where tickets live, which forge, where the flow must stop and who judges each approval, writes `.harness/flow/<name>.json` with `harness flow new`, puts the team's own names in it, runs `harness flow check` until it passes, then shows the level reached on paper and the map redrawn. Nothing runs: it is a map, not a pipeline. Use when the user says "we want a workflow for feature tickets", "write down how we handle a bug ticket end to end", "draw our path from ticket to production", "map our ticket flow", "write our flow down" — also in French: « on veut un workflow pour les tickets de feature », « écris comment on traite un ticket de bug de bout en bout », « dessine notre chemin du ticket à la prod », « cartographie notre flux de tickets » — even without naming the skill. Do not use to ask whether LangChain, LangGraph, a workflow engine or Rust is needed (flow-why), to decide where one step lives or whether a skill is enough (flow-place), to move a single repository's AI setup up a level (harness-step), or to do one ticket now (the dev skill of the ai-sdlc plugin).
---

# Flow map — the team's path from ticket to production, written down

A team that hands tickets to an agent usually has its workflow in people's heads: two people list the steps and the lists differ. This skill writes **one** file that says every step, who performs it, where a run stops on purpose, how many times a step may repeat, what one ticket may cost and who decides each approval.

Three rules that are not negotiable:
- **A map, not a machine.** This skill writes one definition file. It wires no pipeline, starts no agent, and promises no run: this version runs nothing on a real ticket.
- **A template describes more than it runs.** Every flow has a stop point: the steps after it are written down but would not be run. Say it every time you show a flow.
- **A refusal is fixed by adding what the line asks.** `flow check` refuses a flow without a repeat limit, a budget, a deadline, a judge, the check that follows a wait, or a gate before a merge or a deploy: those it guards itself, but only under the stop point names `merged` and `deployed`, or, when the file has the key, the ones listed under `irreversible`: `irreversible` replaces the default list, so it names every stop point the team cannot take back, `merged` and `deployed` included when the flow reaches them. What it cannot see stays yours: never change a step's type to escape a refusal, except to `gate` (or `human`) when the user says a person really decides or makes that write at that step, the second way out the line offers: ask, never choose it yourself; never delete what a step writes, never drop an approval step, never raise a limit or the budget without a number the user gave, never write `"checks_premise": true` on a step whose sentence does not say it checks the facts it starts from (`flow check` cannot see whether it does), never rename the stop points `merged` or `deployed` unless the same edit lists under `irreversible` the new name and every other stop point that cannot be taken back, and never write `irreversible` to say a merge or a deploy can be taken back without the user's word.

## Guide the user

**Show the map first.** Before any question, show in at most six short lines, plus the two outputs named below:
- **Goal**: your workflow for one kind of ticket, written in one file a program has checked.
- **Plan**: 1. see the reference flow and where your repository stands · 2. five questions, asked once · 3. write the file · 4. put your names in it · 5. check it until it holds · 6. show the result.
- **Where we are**: the reference flow, and the repository's level (step 1).
- **Where we are going**: `.harness/flow/<name>.json`, checked, and its map with your names. Still on paper.
- **Now**: what you do next, and that five questions follow.

**Ask with context.** For each question: why you ask, what the answer changes in the file, the options in plain words, the default and what taking it means. One decision per question, the five in one message; one exception: when the request names no ticket type, that question is asked alone, first (step 2).

**Plain words.** A step name (`mark_ready`), a stop point (`ready_pr`), a key (`cap`, `stop_at`) or a refusal code never reaches the user without what it means: "the run ends once the pull request is marked ready for a person to review", "the most times one run may enter this step". Speak the language of the conversation; the sentences written in the file follow the language of the user's repository. When the conversation is not in English, show the command's lines as printed, then say each in the user's language right under it: never the translation in place of the printed line, never the printed line alone. Every `flow` command that exits 0 or 1 ends with a note that says how "flow" is typed here and which folder holds the pages: when an output you show names a command (`flow check <file>`) or a page (`flow-format.md`), give that note once, as printed. On exit 2 there is none: a command named in the message is typed as `python3 "${CLAUDE_PLUGIN_ROOT}/cli/harness.py" flow …`.

## Steps

### 1. Show the reference flow and the repository's level
The reference flow comes from the template, written **outside** the repository so that nothing changes yet: `python3 "${CLAUDE_PLUGIN_ROOT}/cli/harness.py" flow new <feature|bug> --out <temporary folder>/<kind>.json`. It prints every step with who performs it, the step a run stops after, and how many steps are only described. Show the step lines as printed. Say the stop line in plain words ("a run ends once the pull request is marked ready for a person to review; the six steps after that are written down but would not be run"). Say the note on the approvals that wait for their judge in plain words: on a fresh file it is expected. Leave out the "Next:" line: it points to the temporary file. If the request does not say which ticket type, show both.

Read `${CLAUDE_PLUGIN_ROOT}/docs/workflow-harness/flows.md` for what you say around it, three sentences at most: where the steps come from, that a run stops on purpose, and the page's path with its date of facts. The drawing of one run (feature flow only; the bug flow has its table), the table of stop points and where the template differs from the study's report (`report.md`, same folder): only if the user asks. Do not copy the page.

For the repository the flow will write in (branches, pull requests): `python3 "${CLAUDE_PLUGIN_ROOT}/cli/harness.py" status --map --no-write <repo>`. Show the map it prints, and say that this is the repository's own ladder (its AI setup, the one harness-step climbs), not the flow's: the flow has a second ladder, shown at step 6. Leave out the "Next step" line of this output: it is not this skill's work. If it says level 0, say plainly that the agent steps of the flow would work with no written project rules, and that harness-init sets them up; the user decides, the map can still be drawn.

### 2. Five questions, asked once
| Question | Why, and what the answer changes | Default |
|---|---|---|
| Which ticket type: feature or bug? | The starting template. There are two; an incident has none (flows.md says what is nearest) | The one the request names. If it names none: ask this one question alone, first, after showing both flows; the four others follow in one message |
| Where do tickets live? | The wording of every step that reads or writes the ticket | The forge's own issues |
| Which forge and CI? | The wording of the pull request, CI and merge steps; a team without a merge queue or without CI has a step to reword; a step is dropped only on the user's word (step 4) | The one read from the repository's remote and workflow files; say what you read |
| Where must a run stop? | The stop point of the file: everything after it stays described, not run | The template's, said in plain words: for a feature, a pull request marked ready for a person to review; for a bug, the root cause written on the ticket, nothing fixed |
| Who judges each approval? | One line per approval step that comes before the stop point: a role or a name, written in the file. The approvals after it keep the template's wording, and you say so (flow-place still asks their judges: level 1 needs every answer); ask for them only if the user moves the stop point later | The template's wording ("a maintainer…"), which names nobody on your team |

The stop options, earliest to latest, are in the stop-point table of flows.md (section 4). Propose the template's. Name the earlier ones as options in plain words (for a feature: the plan posted on the ticket; a draft pull request open). A later one is a choice the user makes, not one you argue for.

### 3. Write the file
From the repository root: `python3 "${CLAUDE_PLUGIN_ROOT}/cli/harness.py" flow new <kind> --out .harness/flow/<name>.json`; `<name>` is the ticket type (`feature`, `bug`) unless the user gives another. If the file already exists the command leaves it and says so: never add `--force` without the user's word, since it would replace their flow. Read the existing file and continue from it: a `can_judge` already in it may be an older template's, not a judge's; say so, and leave the question to flow-place.

### 4. Put the team's names in it
Follow `${CLAUDE_PLUGIN_ROOT}/docs/workflow-harness/flow-format.md`, key by key. Edit only what the answers decide: the flow's name, the sentence of each step (the tracker, the forge, the CI by their names), the person who decides each approval, the stop point. A step the team does not have is dropped only on the user's word, and named in the report; an approval step, or the step after a wait that checks the facts, is never dropped by you: ask. A fresh file answers no approval: no step has `can_judge`, so each approval waits for its judge, `flow place` leaves it open and the flow stays at level 0 (None). That answer is the judge's, asked by flow-place: never write it here. Renaming a step means renaming it everywhere another step points to it; what an approval shows must match, to the letter, what another step writes. The format has no key for the tracker or the forge: they live in the steps' sentences, and an invented key is ignored. Keep the template's repeat limits, deadlines and budget unless the user gives a number: they are starting values, not measured costs (flows.md, sections 2 and 3, says so of the budget, the deadlines and the caps; `costs.md` in the same folder gives the published prices to compare with, with its date).

### 5. Check until it holds
`python3 "${CLAUDE_PLUGIN_ROOT}/cli/harness.py" flow check .harness/flow/<name>.json`. Exit 0: it holds. Exit 1: each line says what is wrong and the key to write; fix the file and run it again. Exit 2: the file is not JSON any more, a key is written twice, or the path is wrong; the message says which. Repair your last edit, change nothing else, and run it again; when the two values of a key differ, ask which one holds. Tell the user each refusal in one plain sentence and what you changed ("the coding and checks steps could repeat without end; I put back a limit of 6 entries"). When the fix needs a decision (a number, a person, a stop point, which of the ways out a line offers), ask. An approval nobody can judge is removed only on the user's word, and is named in the report. When the flow holds, the command prints what bounds one run (the budget, how many times in all the capped steps of each circle can be entered, an upper bound, the last gate before each write that cannot be taken back): show it as printed; it applies no threshold, and neither do you. A line "No transition of this file reaches …" names a write `flow check` cannot see: ask the user whether a step of theirs does that write under another name; if one does, on their word, write its stop point under `irreversible`, beside the default names the flow still reaches; if none does, nothing changes.

### 6. Show the level and the map with the team's names
`python3 "${CLAUDE_PLUGIN_ROOT}/cli/harness.py" flow status .harness/flow/<name>.json --map`: show it as is, and say again that this is the flow's ladder: the repository's level did not move. Then redraw the list of step 1 from the file: one line per step, who performs it, its sentence, the stop line, the steps only described. While any approval waits for its judge, the steps behind the stop point included, the level reads "None" and the map's "Next step" names whom to ask: do not answer for the team, that question is flow-place's, to the judge.

### 7. Report, then stop
Always the same format:
- **The file**: its path, the number of steps, the budget for one ticket (figures from `flow check`); if the work stopped early, at which step, and whether the file is still the unchanged template.
- **The map**: the output of `flow status --map`, then the flow with the team's names.
- **Where a run would stop**, in plain words, and the steps only described.
- **What I changed from the template**: one line per edit; one line per refusal fixed; every step removed and every limit changed, with who asked.
- **What is not proven**: see below.
- **Questions**, numbered, each with why it is asked and the proposed default, if any.
- **Next**: flow-place, to say where each step lives (a skill, code, a CI job, the ticket, an approval) and whether anything needs an engine. To try the file by hand, one event at a time, `python3 "${CLAUDE_PLUGIN_ROOT}/cli/harness.py" flow next --help` shows how. Running a step on a real ticket is not built yet.

## What the result proves, and what it does not
Everything here is on paper. `flow check` proves the file holds together: no circle of steps without a limit, no wait without a deadline, no approval without a person who can refuse, no write to a stop point listed as cannot be taken back (`merged` and `deployed` unless the file says otherwise) that a run reaches without crossing such an approval. It reads the file, not the programs: a step given the wrong type, a write the file does not declare, a gate far before the write it should guard, a cap that is too high, it does not see. The level "Mapped" proves the flow is written and every step has a place; it is not reached until each judge has answered. Neither proves the flow works: nothing ran, no ticket went through it, and no cost or duration was measured unless the user typed the number. The reference flows are a synthesis of what companies wrote about themselves; flows.md says no account was found of a small team running them as written.

## Common pitfalls
- Asking the five questions before showing the reference flow and the repository's level.
- Showing the flow without its stop line: the user believes the file merges and delivers.
- Saying "your workflow is set up" or "the flow will now handle tickets": nothing runs.
- Making `flow check` pass by what it cannot see: retyping a step, deleting what a step writes, raising a limit, or listing under `irreversible` only what suits the check.
- Writing `can_judge` for a judge: nobody asked that person.
- Setting the stop point to a step's name: a stop point is the name of a milestone a step leads to; `flow check` lists the valid ones.
- Moving the stop point later because the template "already describes" the merge: it is the user's decision, and the default is the template's.
- Renaming a step in one place only, or rewording what a step writes without rewording what the approval shows.
- Writing a command of the run side (starting a step, a report, a sweep) as something to type: not built yet.
- Deciding where a step lives, or whether an engine is needed: flow-place and flow-why.
- Running `flow new` in the user's repository to "show" the template: show it from a temporary folder, write in the repository only at step 3.
