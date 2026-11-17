---
name: harness-stress
description: Puts the harness-ai skills to the test on the sample projects of `fixtures/`, blind, then proposes their fixes in a dedicated PR — announces the plan and its cost before launching anything, has each skill or task played by a fresh agent that has never seen the answer key, grades with the CLI, files each gap under a single cause, fixes only the skills' text, then measures on held-out projects. Use when the owner asks to "stress", "test", "measure" or "evaluate" a skill or the whole harness, to replay the bench after a model change, to check that a SKILL.md change broke nothing, or to know whether a rule or a layer of the harness still serves — also in French: « stresse », « teste », « mesure », « évalue » un skill ou le harness. Never launch on your own: a campaign costs hundreds of thousands of tokens.
---

# Harness stress

A skill does not improve by rereading it: it improves by watching it fail. This skill organises that failure, grades it without indulgence, and draws fixes from it **that hold elsewhere than on the bench**.

The risk of the exercise is known: an agent that can change both the copy and the answer key always raises the grade. Hence four rules that are not up for discussion.

- **You never touch the answer key.** `expected.json`, `traps.md`, `tasks/`, `owner.md`, `owner.json` and the grader's code (`cli/`) are out of your write reach. If the answer key looks wrong to you, it is a question for the owner, in the PR.
- **You only fix the skills' text** (`skills/**`), one lesson per commit.
- **A lesson is stated without naming the bench.** If you cannot write it without citing a sample project or one of its identifiers, it is not a lesson: it is learning by heart.
- **`holdout` projects only serve to measure.** You do not read their gaps to fix a skill. You only look at whether their grade moved.

## Guide the owner

**Show the map first.** Before launching anything, show in at most six short lines: **Goal** (what this campaign measures, in one sentence) · **Plan** (the numbered steps below that apply, a few words each) · **Where we are** (`python3 cli/harness.py bench report`: the last grades of what is in scope) · **Where we are going** (grades before and after, and a PR if a fix is found) · **Now** (the plan and its cost, and the question if the scope is open). Update it in the report.

**Ask with context**: one decision per question, why it is asked, the options with their cost, the proposed default. **Plain words**: say "the expected answers" before "answer key", "held-out projects (only measured, never tuned on)" before "holdout"; no bare run id or arm name without what it means (`bare`: no instructions; `asis`: the instructions found in the repository; `harness`: the ones the skills produce).

## Steps

### 1. The plan, and its price, before anything
`python3 cli/harness.py bench plan` lists the agent runs and their estimated cost. For a task, first run `bench selftest <project>`: if it warns that the attempted solution is caught by the project's commands, the task will not tell the arms apart, pick another. Narrow with `--kind audit|init|task`, `--fixture <name>`, `--role tuning|holdout|all`.

Announce to the owner: what the campaign measures, how many runs, how many tokens, and what it does not measure. If the request already named the scope ("stress the audit on ts-monorepo"), launch. If it was open ("stress the harness"), propose two or three scopes with their price and wait for the choice. Never exceed the announced budget without asking again.

### 2. Prepare each run, outside the repository
The evaluated agent must be unable to read anything of the answer key. Everything happens in a temporary working folder, never under `fixtures/`. One parent folder per run, with a neutral name, and the repository under its project's name: neither the arm nor the bench can be read from the path. First empty this temporary folder of working copies that carry a solution.

- **The kit**: a copy of `skills/` and `cli/` in the temporary folder. That is all the agent knows of harness-ai.
- **The repository**:
  - audit measurement: `bench prepare <project> <dir> --arm asis`;
  - step 1 measurement: nothing to prepare, `bench init` takes care of it;
  - task measurement: nothing to prepare, `bench play` takes care of it.

### 3. Play, blind
A **fresh agent per run**, with no memory of this session. Its message contains, and nothing else:
- for a skill: the kit path, the repository path, the skill to follow, and for an init the content of `owner.md` presented as the owner's answers. It hands its files back in the working repository, and its report;
- for step 1: you do not launch the agent yourself. `python3 cli/harness.py bench init <project> --work-root <temporary folder> --label <label>` does it: separate process, kit, and the owner. If the project has an `owner.json`, the owner only answers questions, through a command laid in the kit: it is the only way to measure the interview, and `interview.md` says whether the fact only the owner holds was asked. Otherwise, its `owner.md` answers are given in advance, without the preamble (`--answers given` forces this mode). The command grades what was written and the report, and files in `overlay/` what the step changed. To play the whole chain, then give this folder to `bench play --arm harness --overlay`: the task is then played with the harness the skill produced, not the project author's;
- for a task: you do not launch the agent yourself. `python3 cli/harness.py bench play <project> <task> --arm <arm> --work-root <temporary folder> --label <label>` does it, one command per arm, to run in parallel. The agent is a separate process that receives only `task.md` and loads only the working repository's instructions, like a real session. It is confined: its commands are limited to the task's `agent_bash` list, and what is refused is kept in `usage.json`. The command grades, files the outputs and writes the registry.

An agent launched from your session inherits its instructions and tools: the arm without instructions is then not bare, and the arms look more alike than they should. That is why tasks go through `bench play`. The audit measurement, though, is still played by an agent of your session: say in the report that its instructions are added to it.

Give it no hint, no grading criterion, not the sample project's name. Do not launch the same run twice hoping for better: variance is handled in step 5.

### 4. Grade and record
```bash
python3 cli/harness.py fixture check <project> --audit <dir>/.harness/audit.json
python3 cli/harness.py fixture check <project> --init <dir>
python3 cli/harness.py bench check <project> <task> <dir>
python3 cli/harness.py bench record --kind <audit|init|task> --fixture <project> [--task <task> --arm <arm>] \
    --model <generation label> --score <grade> [--ok] --run <path of the outputs>
```
File the outputs in `fixtures/repos/<project>/runs/<date>-<measure>-blind[-<arm>]/`: what the agent wrote (for a task, its diff), its report, the grader's output. Record **all** runs, the bad ones included.

The generation label is the one the owner gives the period, a date for example. It serves to compare two campaigns when the model has changed; it does not need to be the model id.

### 5. File each gap under one cause, and one only

| Cause | How you recognise it | What you do with it |
|---|---|---|
| **Skill** | The skill's text led there, or said nothing to prevent it. You can quote the sentence, or its absence | A fix of the skill, step 6 |
| **Grader** | The agent is right and the answer key is wrong, or too narrow: a defensible verdict refused, a keyword that depends on the language | A question for the owner. You touch nothing |
| **Project** | The sample project has a defect: a broken command, an unplanted trap the agent found | A question for the owner. An extra trap found is good news |
| **Variance** | Replayed once, the run gives the opposite | You note it. No fix on a roll of the dice |

A gap without an established cause stays "unexplained" in the report. That is an honest answer.

### 6. Fix the skills, in a dedicated PR
Branch `stress/<YYYY-MM-DD>`, never `main`. One commit per lesson: `stress(<skill>): <the lesson in one sentence>`, with the run that showed it in the body.

Before each commit, check that the lesson is general:
```bash
git diff --cached -- skills | grep -nE "^\+.*($(ls fixtures/repos | paste -sd'|'))" && echo "lesson learned by heart: rewrite it"
```
Also check that it does not grow the skill without end: a lesson replaces or sharpens a sentence more often than it adds one. A skill that goes past 150 lines is split.

### 7. Measure the fix
- Replay **only** the failed runs, on the `tuning` projects.
- Then play the `holdout` projects once (`bench plan --role holdout`). It is the only measure that counts: if it did not move, the fix learned nothing general; if it went down, remove the fix.
- Two fixing rounds at most per campaign. Beyond that, you are tuning the skill to the bench.

### 8. The report, fixed format
In the PR description, and in the answer to the owner:
- **The map, updated**: steps done, where the grades stand now, what is left or why we stop.
- **What was measured**: scope, number of runs, real cost against announced cost.
- **Before and after**, one line per run: project, measure, arm, grade before, grade after. `python3 cli/harness.py bench report` gives the registry.
- **The held-out projects**: their grade before and after, separately.
- **The gaps, by cause**, with the proof of each.
- **The fixes**, one line per commit.
- **Questions for the owner**, numbered, each with why and the proposed default: everything that touches the answer key, the grader or a sample project.
- **What is not proven.**

## The generation campaign: what no longer serves

When the model in use changes, the owner can ask to replay the **tasks** on all their arms. It is the measure of dead weight:
- where the `bare` arm catches up with the `harness` arm, the rules the task exercises no longer change anything for this model: they are candidates for removal;
- where the `asis` arm does worse than `bare`, the instructions found in the repository get in the way.

You remove nothing yourself. You list the candidates with both grades, and it is a question for the owner. The harness-ai skills are subject to the same measure: a skill instruction that no run makes useful any more is reported the same way.

A task succeeded on a single arm proves nothing either way: one run is one draw. Say so, and propose to replay before concluding.

## Common pitfalls
- Launching "just one run to see" without announcing it.
- Reading `traps.md` to understand a gap on a `holdout` project.
- Fixing the skill so that it says the word the grader looks for.
- Concluding on a single run.
- Reading a tie between arms as "the harness is useless" before checking that the task could tell them apart. The check to look at first is the one `task.json` marks `exercises`: it is about the fact written nowhere else.
- Stacking lessons: ten local fixes make a skill nobody reads in full any more, model included.
