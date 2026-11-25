---
name: harness-coach
description: Reviews one skill, agent, rule or instruction file and says what is good, what is weak, and which concept each weakness comes from — a condition that can be skipped, a determinism problem, a limit that is only asked for, something not in the right place, dead weight — in plain words, with the line that shows it; also answers questions about how to write a skill and explains those concepts. Writes nothing in the repository and never speaks of levels. Use when the user asks to "review this skill", "is my skill any good?", "what is wrong with this agent?", "explain why this should be code", "what is a determinism problem?", "help me write a skill" and wants to understand before anything is built — also in French: « fais une revue de ce skill », « il est bien mon skill ? », « qu'est-ce qui ne va pas dans cet agent ? », « explique-moi pourquoi ça devrait être du code », « aide-moi à écrire un skill » — even without naming the skill. Do not use to place the pieces and set up the files (harness-design), to audit a whole setup (harness-audit), to know or raise the repository's level (harness-step), or to choose between the skills (harness-guide).
---

# Harness coach — what is good, what is weak, and why

A person who wrote a skill wants to know whether it holds, and to understand why when it does not. A level number or a verdict code tells them neither. This skill reads one artifact, says what is well placed, names the concept behind each weakness, and explains it. It stays outside the level ladder: no state file, no report, no target.

Three rules that are not negotiable:
- **The findings come from `harness place review`, not from your opinion.** You split the artifact and answer the grid's questions; the command names the concepts. If a finding seems wrong, an answer is wrong: change it and say why.
- **Nothing is written in the repository.** No `.harness/` file, no report, no fix. The pieces file goes in a temporary folder outside the repository.
- **Concepts, not numbers.** Never show a level, a layer (L1…L4), a medal, a verdict code or a grid id, unless the user asks for them. Do not run `status`.

## Steps

### 1. Read the artifact
Read the whole file the user names (a SKILL.md, an agent, an AGENTS.md, a rule, a hook) and what it calls: the scripts, the workflow, the settings it cites. Say in one sentence what the artifact is for. If the user asked a question and named no artifact, go to "A question, no artifact".

### 2. Split and answer
`python3 "${CLAUDE_PLUGIN_ROOT}/cli/harness.py" place grid` gives the kinds of pieces and the closed questions. Split the artifact into pieces of a single kind: a step followed by a condition, "and check that", "without ever" are signs of a piece to cut out. For each piece, answer the questions from the repository, and note:
- `current`: where the piece is held **today**, not where the sentence is written. A rule the text states and nothing checks is held by the text (`skill`, `agents_md`, `subagent`); a rule that cites a check you opened and found blocking is held by that check.
- `evidence`: the `path:line` that shows it.

Two answers are decisions and not facts: what it costs when a rule is not respected, and who must not be able to go around it. Propose an answer from what the artifact says, and tell the user which ones you assumed. Ask only when the review would change with the answer.

### 3. Run the review
Write the pieces in a JSON file in a temporary folder outside the repository:

```json
[{"piece": "Refuse to release with uncommitted files",
  "answers": {"nature": "rule", "incident": "forget", "checkable": "yes", "bypass_rule": "agent"},
  "current": "skill", "evidence": ["SKILL.md:19"]}]
```

Then `python3 "${CLAUDE_PLUGIN_ROOT}/cli/harness.py" place review <file>`. Exit code 3: an answer is missing, the output says which question in plain words; answer it or ask the user. Exit code 2: invalid input, fix the file.

### 4. Tell the user
In the language of the conversation, in this order:
1. **What is good**, first: the pieces the review lists as well placed, and why each holds.
2. **What is weak**, one concept at a time, in the review's own order and with its own names. For each: the concept explained in one or two sentences with the user's own line as the example, where the piece is held today, and where it would hold.
3. **What you assumed**: the answers you gave for the user, and what would change the review.
4. **What the review does not say**: a sentence that is unclear, a step that is missing, a tool an agent lacks are your reading, not the command's. Give them apart, as remarks.

A weakness is not a fault of the author: say what the text cannot guarantee, not that it is wrong. If everything is well placed, say so and stop.

### 5. Offer, then stop
Offer once, and do nothing without a yes:
- to put it right, piece by piece: that is harness-design;
- to explain one of the concepts further.

## A question, no artifact
"Why should this be code?", "skill or rule?", "what is a determinism problem?": answer the question itself, with an example taken from the user's repository when there is one. The concepts and their definitions are in `python3 "${CLAUDE_PLUGIN_ROOT}/cli/harness.py" place grid --format json`, under `concepts`: use those names and those definitions, do not invent others. To help write a new skill, ask what it is for, then walk through the same concepts as questions to the author: what must hold whatever happens, what is a computation, what the agent may not do, what is left to its judgement.

## Common pitfalls
- **Opening with the repository's level.** The user asked about one skill. Where the repository stands is another question (harness-step).
- **Listing only defects.** What is well placed is half of the answer: it is what the author must keep.
- **Getting `current` wrong.** A sentence in a SKILL.md that cites a check which exists and blocks is held by the check: open the workflow before saying the text is all there is.
- **Showing the grid's ids.** `bypass_rule`, `ci_check`, `PUSH_DOWN` belong to the pieces file. Say "who must not be able to skip it?", "a check in the CI that blocks merging".
- **Fixing while reviewing.** The review explains. The change is another request, with its own agreement.
- **Turning a remark into a finding.** Only what the command lists is a finding; your own reading is given apart and named as such.
