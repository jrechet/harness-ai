---
name: harness-medals
description: Says where a repository or a plugin marketplace stands as a medal (bronze, silver, gold, platinum), unlocked achievements and next steps, and opens the interactive page that shows them. Everything comes from measurements made by `harness medals` in the repository, never from an opinion. Use when the user asks "what level are we at", "why bronze" or "why not gold", "which achievements have we unlocked", "what to do to reach the next rank", "show the medals page", or wants a maturity badge — also in French: « à quel niveau on est », « pourquoi bronze », « quels succès on a débloqués », « montre la page des médailles ». Do not use to set up or move the setup forward (harness-init, harness-step) or to audit it (harness-audit): this skill shows, it changes nothing but its medals file.
---

# Harness medals — the level, and why

A medal is not a grade. It is the level `harness status` measures, given a name people remember, and split into achievements unlocked one by one. This skill evaluates nothing itself: it runs the command and reads its output.

Three rules:
- **Every figure comes from the command.** Never say "you are more or less gold": run it, then quote.
- **A medal does not say agents work better.** It says the harness has a shape. Proof of the gain is elsewhere (the bench, the signals per PR). Say so if asked what the medal is worth.
- **No gaming the rules to unlock an achievement.** An achievement is unlocked by doing what it measures. Writing "Enforced by" in front of a rule without a guardrail is cheating the audit will see.

## Guide the user

**Show the map first.** Before answering, run `python3 "${CLAUDE_PLUGIN_ROOT}/cli/harness.py" status --map --no-write <repo>` and show, in at most six short lines plus the map:
- **Goal**: tell you where this repository stands, as a medal, and why, from measurements only.
- **Plan**: 1. measure · 2. answer your question · 3. the page, if you want it.
- **Where we are**: the map; each medal is a level (bronze = 1 Framed, silver = 2 Looped, gold = 3 Verified, platinum = 4 Delegated).
- **Where we are going**: your answer, with the measured reasons; nothing in the repository changes unless you ask for the medals file.
- **Now**: what you measure (repository or marketplace), and whether you will ask something.

**Ask with context.** Say why you ask and what the answer changes; give the default. One decision per question.

**Plain words.** Each achievement is said in plain words; a signal code (S1–S4) or check id is never shown alone ("a real review remark turned into a rule", not "S1–S4"). Speak the language of the conversation.

## Steps

### 1. What is measured
A repository (`--kind repo`, the default) or the plugin marketplace it declares (`--kind marketplace`, if it has a `.claude-plugin/marketplace.json`). If the request does not say and both exist, give the repository and offer the other in one line.

### 2. Measure
`python3 "${CLAUDE_PLUGIN_ROOT}/cli/harness.py" medals <repo> [--kind marketplace]`. `--name <name>` sets the displayed name (default: the one of the medals file if it exists, otherwise the folder's), `--format json` returns the data. It gives the medal, the sentence that says why, the achievements by rank with their date, the achievements outside ranks, and the next steps.

### 3. Answer the question asked
- **"Why this level?"**: the "why" sentence, then the achievements missing for the next rank, each with what is measured, in plain words.
- **"Which achievements?"**: the unlocked list, with dates. An achievement marked "lost" is said first: it is a regression.
- **"What next?"**: the next steps, in order. A "waiting" step does not depend on the user alone (real reviews or real agent changes must happen over time): say so, do not present it as a task. To do the step, it is harness-step.

Do not copy the whole output if a precise question was asked. End with the map's last line ("Next step: …") so the user knows where to go from here.

### 4. The page
On request, or if the user wants to "see": `python3 "${CLAUDE_PLUGIN_ROOT}/cli/harness.py" medals <repo> --page <file.html>`. The page is a single file, without external resources, with its data inside. Write it outside the repository unless the user wants it inside, and open it.

### 5. The repository file
`--write` updates `.harness/medals.json` (`.harness/medals-marketplace.json` for a marketplace). It keeps the date each achievement was unlocked and the medal history. If the measurement has not changed, the file is not rewritten: its date is that of the last change. Write it only if the user asks or if the file already exists. Whether it is committed is their choice: committed, it shows in review and a badge can read it.

## Common pitfalls
- **Announcing a medal from memory.** It may have changed: a harvest older than 45 days loses a silver achievement.
- **Presenting the medal as a goal.** `harness target` says where the user wants to stop. Bronze is a place where one can stay.
- **Confusing the two measurements.** A repository's medal and its marketplace's do not measure the same thing, and can differ.
