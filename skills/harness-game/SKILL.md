---
name: harness-game
description: The video-game profile of harness-ai — sets up a game's development loop one piece at a time, sized to the game (one hour, a jam, weeks to months) — the engine and its version pinned, a command that starts the game, a headless run judged by its log, a screenshot the agent opens, an export proven early, the engine files never hand-edited, a dated playtest, a cut list, credited assets, then tests and CI — and proposes the lines an AGENTS.md must hold for an agent to work on a game. Every piece is measured by `harness game`, never declared. Use when the user wants to make a game with an agent, asks what to set up to build a game, "a precise development loop for my game", "AGENTS.md for Godot / Unity / Phaser / pygame", "a game in one hour", "a game jam with Claude", or why the agent says the game works when it does not — also in French: « créer un jeu vidéo », « faire un jeu en une heure », « une game jam avec Claude », « qu'est-ce que je mets en place pour développer mon jeu », « AGENTS.md pour Godot » — even without the word profile. Do not use for the game's design itself (the concept, the core loop, the mechanics to cut: that is the owner's, or a game-design skill's), to set up a repository that is not a game (harness-init), or to raise the general level of the harness (harness-step).
---

# Harness game — a game's development loop, piece by piece

An agent building a game fails in a few known ways: it says the game works without having run it, it trusts an engine that exits 0 on a script error, it edits a scene file as text and breaks its references, it writes the API of an engine version the project does not run, it adds features nobody asked for, and it declares the game fun. Each of these has a piece of the loop that catches it, and most pieces are a command a program can judge. This skill sets them up, one at a time, in the order the scale of the game calls for, and proposes the lines the instruction file must hold.

Four rules that are not negotiable:
- **The state comes from `harness game loop`, not from your reading.** A piece is in place when the command says so. If its answer seems wrong, say why and fix the input (the recorded command, the file), never the conclusion.
- **Fun is the owner's.** No run measures feel, difficulty or fun. Never say a change makes the game better; say what changed and that it is "not yet played by a person" until the owner has played it.
- **Publishing is the owner's.** The judge refuses a publishing command when it is recorded and before every run, as far as the command's words tell; never run one yourself either (itch.io, Steam, a store, a production site), never hide one in a script, and never handle a publishing key or an engine licence.
- **The scale is a place where one can stay.** A one-hour game needs five pieces, not fourteen. Never set up a piece the chosen scale puts "later".

## Guide the user

**Show the loop first.** Before any question or action, run `python3 "${CLAUDE_PLUGIN_ROOT}/cli/harness.py" game loop <repo>` and show, in at most six short lines plus its output:
- **Goal**: a development loop where every change is run, judged and shown, and the owner plays and decides.
- **Where we are**: the output of the loop (pieces in place, missing, later), and the engine found.
- **Where we are going**: the pieces of the chosen scale, nothing beyond.
- **Now**: the questions below, or the next piece the loop names.

**Ask with context.** Each question says why it is asked and what the answer changes; give the proposed default. One decision per question.

**Plain words.** Say "a run with no window that fails on errors", not "smoke"; "the program that judges each run", not "runner", unless the user uses the words first. Speak the language of the conversation; the lines written in the repository follow the repository's language, with the commands kept word for word.

## Steps

### 1. The first time: ask once, all together
When the loop says no scale is chosen, ask together, each with why and a default:
1. **Scale** — why: it decides how many pieces the loop asks for. One hour (default when the user says "quick" or names a one-hour jam), a jam or a weekend, or weeks to months?
2. **Engine**, only when the loop found none — why: an engine whose files are text and whose games can be started, tested and photographed from a shell makes the loop possible without an editor. Propose the stacks of the chosen scale from `python3 "${CLAUDE_PLUGIN_ROOT}/cli/harness.py" game profile --format json` (`scales.<scale>.stacks`, with `stacks_why`). An empty repository starts with the engine's own empty project; the first proof is that it starts.
3. **The questions only the owner answers**, from `python3 "${CLAUDE_PLUGIN_ROOT}/cli/harness.py" game instructions <repo>` ("Questions only the owner answers"): the core loop in one sentence, who plays and how often, a jam's rules on AI-generated code and assets, a reference for the look, where it will be released. If a jam forbids generated code, say so plainly before anything else: an agent-built entry would be ineligible.

Then write the answers: `python3 "${CLAUDE_PLUGIN_ROOT}/cli/harness.py" game set --repo <repo> --scale <scale>` (and `--engine`, `--playtest-days` from "how often", when given). The output suggests a target level for the general ladder; offer it once, as a plain choice, and run `harness target` only on a yes.

The design itself (the concept, the core loop, which mechanics to cut) is not this skill's work. If the session has a game-design skill, offer it for that; its one-page design with a cut list counts as the loop's scope piece.

### 2. Propose the next piece
Take the next piece the loop names. Say what it gives (its `gives`), what it costs (its `minutes` in the profile), and how: the candidate command or the file to write, from the loop's "How". Offer two choices: this piece only, or every missing piece of the scale in one go (at the hour scale, the second is often the right one: the five pieces take about ten minutes). Do nothing before the answer.

### 3. Set it up
- **A command piece** (start, run with no window, screenshot, export, static check, tests): read the engine's notes in `game profile --format json` (`engines.<id>.notes`) before you write anything: they hold the traps. Write what the game needs for the command to prove something: a frame count after which it quits, a line it prints once started (`GAME READY`), a path where it saves its screenshot. Then record the command — `python3 "${CLAUDE_PLUGIN_ROOT}/cli/harness.py" game command <piece> "<command>" --repo <repo>` with `--ready` for the run with no window and `--output` for the screenshot and the export — and judge it: `python3 "${CLAUDE_PLUGIN_ROOT}/cli/harness.py" game run <piece> --repo <repo>`. The loop counts the piece only once that judged run passed; a command recorded before the engine was found is shown as to record again. The command refuses a piece beyond the chosen scale. A command that needs what only the owner can do (export templates, a licence, a binary not installed) is a question for the owner, not something to work around.
- **The judge**: `python3 "${CLAUDE_PLUGIN_ROOT}/cli/harness.py" game runner <repo> --write` copies it to `.harness/game_loop.py`, so the agent, a person and the CI run `python3 .harness/game_loop.py all`.
- **The instruction file**: `python3 "${CLAUDE_PLUGIN_ROOT}/cli/harness.py" game instructions <repo>` gives the candidate lines, filled from what is measured, with where each goes (under Rules, under Forbidden), the file's length after, and the share of rules that say what enforces them. Show them to the owner, add the ones they confirm, keep the commands word for word. Without an instruction file, write a short `AGENTS.md` from harness-init's template (block "Step 1": the mode line, the Rules and Forbidden sections) with these lines in it, and say that harness-init would also ask what is written nowhere.
- **A capture**: after recording it, open the image it wrote and say what you see. That is the piece's whole point.
- **The playtest, the cut list, the credits**: these files are the owner's words. Propose the format the loop names, write only what the owner tells you, never a playtest that did not happen.

### 4. Measure, show, stop
Run `game loop` again and show before and after: which piece moved, the count of pieces in place, the next one. Then stop. One piece (or the batch the user chose) per invocation.

### 5. Report
- **The loop, updated**: the output of `game loop`.
- **What was set up**: the files written, the commands recorded and the result of their judged run.
- **What only the owner can do**: the loop's "Only the owner can" line, the questions left open.
- **What comes next**, without doing it: the next piece of the scale, or, when the scale is complete, the next scale as a plain choice where staying is the default. Every report ends with "not yet played by a person" until the owner says they played the build.

## Common pitfalls
- **Calling the game working because a run passed.** A run with no window proves the game starts and logs no error; the screenshot shows what it looks like; only the owner says whether it is right.
- **Trusting an engine's exit code.** Godot, Unity and LÖVE can exit 0 on an error: the judge reads the log and requires the game's ready line. Never replace `game run` with the raw command.
- **Editing scene, prefab or meta files as text.** Change them through the engine (the editor, a script it loads, a build method) unless the instruction file says how to do it safely.
- **Setting up the weeks-scale pieces for a jam.** Tests, CI and architecture rules on a prototype cost the hour they were meant to save.
- **Writing the engine's API from memory.** Check it against the documentation of the pinned version before using it.
- **A screenshot nobody opens.** Recording a capture and not looking at the image is the same as not having one.
