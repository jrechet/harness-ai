---
name: harness-guide
description: Answers "which skill or command of harness-ai should I use for this?" — reads the plugins' map, recommends one skill or command for what the user wants, says why and which neighbour not to use, says when nothing is needed at all, then offers to start it. Changes nothing. Use when the user has just installed the plugins and asks what they can do, describes a goal and asks which tool fits ("I want to…, what do you advise?", "skill A or skill B?", "is there a command for…?", "where do I read about…?"), or asks whether they need any of this — also in French: « je viens d'installer le plugin, je fais quoi ? », « j'ai envie de faire ça, tu me conseilles quoi ? », « quel skill pour… ? », « c'est quoi la différence entre… ? » — even without naming the skill. Do not use when the request already says what to do (start that skill directly: "audit my AGENTS.md" is harness-audit, "where am I" is harness-step), nor to place a piece of a harness (harness-design).
---

# Harness guide — the right tool, or none

Someone who has just installed the plugins sees the skills of two plugins and two command lines. This skill points to one of them, or to none, and gets out of the way.

Three rules:
- **One recommendation, from the map.** Name what `references/map.md` names, never a skill or command that is not in it. If two fit, ask the one question that separates them.
- **Nothing is a valid answer.** When the user only wants to code, fix or understand something, say that no skill is needed and answer the request itself.
- **This skill changes nothing.** It reads, it recommends, it offers to start; the recommended skill does the work.

## Steps

### 1. Where the user is
If the session is in a repository, `python3 "${CLAUDE_PLUGIN_ROOT}/cli/harness.py" status --map --no-write .` says in a few words where its AI setup stands. Use it only when the answer depends on it (init or step?); do not show it otherwise.

### 2. Read the map
Read `${CLAUDE_PLUGIN_ROOT}/skills/harness-guide/references/map.md`. Find the line of what the user wants, and its "Not this" column: the neighbour is part of the answer.

### 3. Answer
In a few lines, in the user's language:
- **Use**: the skill or command, and in one sentence why it fits what they said.
- **Not**: the neighbour they might have picked, and why not, if there is one.
- **How**: the phrase or the slash command that starts it (`/harness-ai:harness-init`, `/ai-sdlc:review`), or the command line.
- **How sure**: if they will rely on it, its state from `${CLAUDE_PLUGIN_ROOT}/docs/capabilities.md` (tooled, measured once, never played), word for word.

If the skill is in the `ai-sdlc` plugin and it is not installed, give the install line from the map. If what they want is in no line of the map, say so: neither plugin does it.

For a question about the project itself (levels, why stopping is fine, LangGraph, the course), point to the page the map's last table names, under `${CLAUDE_PLUGIN_ROOT}`, instead of summarising it: those pages ship with the plugin, not with the user's repository.

### 4. Offer, then stop
Offer to start the recommended skill now. Start it only on their yes, and from then on follow that skill.

## Common pitfalls
- Recommending three skills "to be safe": the user then has to choose, which is what they asked you to do.
- Answering from the skill descriptions alone: they say when to use a skill, the map also says which neighbour not to use.
- Pushing a skill on someone who only wanted their code fixed.
