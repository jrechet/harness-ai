---
name: harness-step
description: Moves a repository's AI setup forward by one step, and one only — shows where the repository stands (measured by `harness status --map`), asks once, with context, how far the user wants to go, proposes the smallest step towards that level with what it costs and changes, does it after agreement, shows before and after, then stops; when the target is reached, says so and offers the next level as a plain choice. Use when the user asks "where am I", "what's next", "the next step", "continue the harness", "go up a level", says they want to stop at a level, or comes back after harness-init — also in French: « où j'en suis », « c'est quoi la suite », « le prochain pas », « continue le harness », « monte d'un palier » — even without naming the skill. Do not use for a full audit (harness-audit) or to collect review feedback (harness-harvest): this skill calls them when the step needs it.
---

# Harness step — one step at a time

Setting up a harness is not a project you undergo in one block. It is a series of small steps, each visible, and you can get off whenever you want. This skill takes **one** per invocation.

Three rules that are not negotiable:
- **A level is a place where one can stay.** The user says how far they go. Beyond that, nothing is set up and nothing is left half done. When the target is reached, the next level is offered once, as a plain choice, never pushed.
- **One step, then stop.** No "while I'm at it". The next step is another invocation, decided by the user.
- **Each step shows its before and after**, measured by the CLI, not told.

## Guide the user

**Show the map first.** Before any action or question, run `python3 "${CLAUDE_PLUGIN_ROOT}/cli/harness.py" status --map <repo>` and show, in at most six short lines plus the map it prints:
- **Goal**: move this repository's AI setup forward by one small step, towards the level you choose.
- **Plan**: 1. see where we are · 2. choose how far to go (once) · 3. pick the step · 4. do it after your OK · 5. measure again.
- **Where we are**: the map (levels in plain words, "you are here", target, what the next level needs).
- **Where we are going**: one step closer to the target, or the target confirmed as reached.
- **Now**: what you do next, and whether you will ask something.

**Ask with context.** Say why you ask and what the answer changes; give the options in plain words with what each means; give the default and what happens if the user takes it. One decision per question.

**Plain words.** The user never reads a check id (`L2.signal`), a signal code (S1–S5), or an undefined internal word. Say "a check that fails the build when the rule is broken", not "guardrail"; "collect what recent reviews taught", not "harvest". A level name comes with its phrase from the map the first time. Speak the language of the conversation; files written in the user's repository follow that repository's language.

## Steps

### 1. Measure
`python3 "${CLAUDE_PLUGIN_ROOT}/cli/harness.py" status --map <repo>` for the user, and `python3 "${CLAUDE_PLUGIN_ROOT}/cli/harness.py" status <repo>` for you (the detailed checks). Keep both: they are the "before".

### 2. The target, asked once
If the map says no target is chosen, ask **one** question, right after the map: "How far do you want to go? You can stop at any level; I will not propose anything beyond it." Then this table, then the default:

| Level | What it brings you | What it asks of you |
|---|---|---|
| 1 Framed | The agent knows the project, its rules and what it must never touch | Half an hour, four questions |
| 2 Looped | Review remarks become rules, so the same mistake is not made twice | A habit: write `rule:` in a review comment to propose a rule; and a few weeks |
| 3 Verified | Mandatory rules are enforced by tools (tests, lint, CI), not just written | A CI, and some check code, rule by rule |
| 4 Delegated | Whole tasks go to the agent and come back clean | Written procedures for those tasks, and agent changes to watch over time |

Proposed default: level 1 for a repository that starts, the current level plus one otherwise; say which it is and what taking it means ("I set the target to 2; the next steps will only aim at that"). Stopping at level 1 is a sound choice, not a giving up: when a person reviews every change, it is often enough.

Write the answer with `python3 "${CLAUDE_PLUGIN_ROOT}/cli/harness.py" target <n> <repo>`. If a target is already set, do not ask again.

### 3. Target reached: say it, offer the next level once, let the user decide
If the map says the target is reached, say so in one sentence. Then offer the next level **once**, as a plain choice: what it would bring, what it would ask (the table above), and two answers: "stay here" (the default: nothing changes, what is in place still needs upkeep, see "When there is no step left") or "aim for level n+1" (you then run `harness target <n+1>` and pick the first step). Do not argue for it; if the user says nothing or stays, stop. At level 4, there is no next level: say so.

### 4. Pick the step
The step is the **first failing check** of the first level not reached, in the order of `status`. A check that only time makes pass, a review signal or observed agent changes, is marked "waiting" by `status`: it does not stop the climb. If a higher level is targeted, the step is the first of its own, and the waiting level will count once time has done its work; tell the user so in plain words. `references/steps.md` says, for each check, what the step is, what it costs and how you know it is done. A "reference without a target" reported by `status` (the instruction file cites something that cannot be found) comes before anything else: it is a broken promise of what is already in place.

At level 0, the step is harness-init: hand over to it.

### 5. Announce before doing
In four lines: what you will do, what it changes for the agent, what it touches (files, CI, team habits), what we will see afterwards. Wait for agreement, unless the request already said to go ahead. A step that needs information only the owner has starts with the question, asked with context.

### 6. Do this step, and only this one
Set up nothing of the next step. If the step reveals a problem out of scope, note it for the report.

### 7. Measure again
Run `status --map` and `status` again. If the targeted check did not flip, the step is not done: say why, do not dress it up.

### 8. Report, then stop
Always the same format:
- **The map, updated**: the output of `status --map`, then one line: steps done in this run, where we are now.
- **The step**: one sentence.
- **Before and after**: level, checks passed out of the level's total, the line that flipped (in plain words).
- **What it changes for the agent**: one concrete sentence.
- **What is not proven**: see "What the measure proves".
- **Files** touched.
- **Questions**, numbered, each with why it is asked and the proposed default, if there are any.
- **What comes next**, in one or two lines: the next step if it is within the target; otherwise "target reached", followed by the one-time offer of step 3 (what the next level brings and asks; staying is the default).

## What the measure proves, and what it does not

`status` measures the **form** of the harness: files, sections, mentions. A level gained says the mechanism is in place, not that agents work better. Never let the user confuse the two.

Proof of substance comes from elsewhere, and takes time:
- **The repository's agent changes (PRs).** harness-harvest counts after-the-fact fixes, red checks, repeated questions. The trend of these numbers, from one collection to the next, says whether agents work better. Levels 2 and 4 rest on it: they are not won in one session.
- **The check seen failing.** At level 3, a check only counts if it has been seen red on a violation.

In the report, say which of these proofs exists for this step, or that there is none yet.

## When there is no step left

What is in place ages: a rule gets an enforcing check, a context changes, a new model no longer needs an instruction. Propose a **relevance review** (harness-audit, section of the same name) in two cases only: the model the team uses has changed, or six months have passed since the last one. `python3 "${CLAUDE_PLUGIN_ROOT}/cli/harness.py" rules <repo>` gives each rule's age. The review removes; it adds nothing.

## Common pitfalls
- Chaining two steps because the second is small.
- Pushing the next level on someone who said where they stop: offer it once, plainly, and take "stay" for an answer.
- Stopping silently at "target reached": the user then has to ask "so, what now?". Say it, and offer the choice.
- Asking for a target with a bare table, before showing where the repository stands.
- Announcing a level gained as proof that agents work better.
- Treating a level 2 or 4 step as a matter of files: these levels are won on real PRs, over time. Adding the section is not enough, and it must be said.
- Stopping on what waits for time when the target is higher: the user would wait weeks for a check that can be set up today.
- Writing a stop rule without testing it against the delegated tasks: in delegation, an agent that stops has nobody to ask, and the task never comes back.
- Creating the "Delegated tasks" section before the procedure it cites.
