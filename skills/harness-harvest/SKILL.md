---
name: harness-harvest
description: Evolves an AGENTS.md / CLAUDE.md and the task contracts from what really happened since the last harvest — `rule:` review comments, after-the-fact fixes on agent PRs, reverts, ignored CI checks, recurring tasks — and proposes in a dedicated PR additions, removals, shortenings, push-downs into CI or new contracts, each justified by its evidence. GitHub source first, extensible (Jira, GitLab…). Use when the user wants to "update the rules", "see what we learned this month", "clean up AGENTS.md", use recent reviews or PRs to improve the setup, or when a scheduled harvest fires — also in French: « mettre à jour les règles », « ce qu'on a appris ce mois-ci », « faire le ménage dans AGENTS.md » — even without the word harvest. Do not use to create the initial file (harness-init) or for an audit without proposed changes (harness-audit).
---

# Harness harvest

An AGENTS.md does not improve by rereading it: it improves by confronting its rules with what happened. This skill looks for **signals** in recent activity, turns them into change **candidates**, and proposes them in a PR where each candidate is a separate commit, justified by links. It never writes directly to the main branch.

What matters is not the source, it is what we look for in it. The catalogue of signals, their strength and the common evidence schema are in `references/signals.md`; sources are only adapters that produce this schema. Read the catalogue before starting.

## Guide the user

**Show the map first.** Before any action or question, run `python3 "${CLAUDE_PLUGIN_ROOT}/cli/harness.py" status --map --no-write <repo>` and show, in at most six short lines plus the map:
- **Goal**: learn from what really happened in reviews and agent changes since last time, and propose rule changes in one PR you review.
- **Plan**: 1. set the time window · 2. collect the evidence (script) · 3. group it into proposals · 4. decide each one · 5. open the PR.
- **Where we are**: the map; the date of the last collection (the marker in AGENTS.md) or "never"; the mode (alone or reviewed by a person).
- **Where we are going**: a PR with one commit per proposal, nothing merged without you.
- **Now**: what you do next, and whether you will ask something (typically: how to recognise an agent's PR).

**Ask with context.** Say why you ask and what the answer changes; give the options in plain words and the proposed default. One decision per question.

**Plain words.** In what the user reads, a signal code is never alone: "a `rule:` comment in a review" (S1), "a fix pushed after an agent PR was merged" (S2), "the same review remark several times" (S3), "a CI check that keeps failing on agent PRs" (S4), "a rule nothing happened about" (S5), "a task done three times or more" (S6), "the same question asked by the agent in several PRs" (S7). Verdicts come with their meaning ("PUSH_DOWN: have a test or CI check enforce it"). The PR you write follows the repository's language.

## Steps

### 1. Frame the window
- Look for the marker `<!-- harvest: last=<date> ref=<sha or url> -->` in the "Maintaining" section of AGENTS.md. The window runs from that date to now.
- Without a marker, or with the `ref=init` marker set by harness-init (it is not a harvest): a 30-day window, and say so in the PR; the marker will be set by this PR.
- Read the "Mode" line of AGENTS.md. In delegation, a rule told without a guardrail is a defect to handle; in assistance, it is a context cost.
- Identify what counts as an **agent PR**: bot author, an agent's `Co-Authored-By` trailer, branch prefix, label. Ask if nothing is obvious; do not guess.

### 2. Collect — scripts first, reading afterwards
Each source has an adapter in the shared CLI of the harness-ai repository (`python3 "${CLAUDE_PLUGIN_ROOT}/cli/harness.py" harvest <source>`) that produces the catalogue's evidence JSON, without an LLM: `python3 "${CLAUDE_PLUGIN_ROOT}/cli/harness.py" harvest github --repo <owner/repo> --agents-md AGENTS.md > .harness/harvest.json` for GitHub (options and agent markers in `references/signals.md`). Run the adapter, write its output to `.harness/harvest.json` of the target repo (that is what `harness status` reads), do not rebuild the evidence by hand from the web interface. If the script is missing or fails, say so and limit the PR to what could be collected; evidence not collected is not invented.

Also read the current state: `python3 "${CLAUDE_PLUGIN_ROOT}/cli/harness.py" rules <repo>` gives the rules one by one with their date, age and declared guardrail; then the contracts in `.claude/skills/` and the existing CI guardrails. Without that, it is impossible to detect an orphan rule or a duplicate.

### 3. Group into candidates
A single piece of evidence is not a candidate, except an explicit `rule:`. Group by existing rule touched, by files or area, by reviewer and pattern. For each group, ask in order:

1. **Does a rule already exist?** If yes and it was broken: it is badly placed or badly worded, not absent. If yes and it has no evidence: orphan candidate.
2. **Can a guardrail carry it?** Lint rule, architecture test, PR check, hook. If yes, the proposal is PUSH_DOWN with the tool named, and AGENTS.md keeps only an "Enforced by" line.
3. **Is it a rule or a task?** Three PRs of the same type in a month is a task contract to create, not a sentence to add.
4. **Can the rule be stated in the present tense, checkable, in one sentence?** If not, it is not a rule yet: propose a question to the team in the PR rather than a text.

### 4. Decide
One verdict per candidate:

| Verdict | When | What the commit contains |
|---|---|---|
| **PUSH_DOWN** | A tool can check the rule | The guardrail (or its skeleton) + the "Enforced by" line in AGENTS.md |
| **ADD** | New rule, justified, not checkable today | The line under "Rules" with why, link, `(unverified)` and its date `[YYYY-MM]` |
| **SHORTEN** | Existing rule now covered by a guardrail | The rule reduced to a pointer line |
| **REMOVE** | Rule without evidence for two harvests or six months, or contradicted by practice | The deletion, with the reason in the commit message. If only the owner knows it is outdated: ASK, not REMOVE |
| **CONTRACT** | Recurring task without a contract | A skeleton `.claude/skills/<task>/SKILL.md` |
| **ASK** | Real signal but the rule cannot be stated | A question in the PR description, no file change |

What never becomes a candidate: a convention guessed from the code without an incident, a rule a recent model already applies, a preference of a single reviewer expressed once without `rule:`.

Rules added follow the language of the AGENTS.md they go into (`Why:` / `Pourquoi :`, `Enforced by:` / `Vérifiée par :`).

### 5. Propose
One PR, fixed format in `references/proposal-template.md`: one commit per candidate, a description that opens with the updated map and lists the candidates with verdict, evidence and what was ignored and why, a "not collected" section, and the harvest marker update as the last commit. Never a direct push, never an automatic merge. If there is no candidate, the PR contains only the marker and the list of rules confirmed by the absence of incidents: that is useful information.

Then report to the user: the map, updated after `.harness/harvest.json` is written; one line on what this changes (the level that waited for a real signal, if one was found); the PR link; what they decide next (review and merge the PR).

## Common pitfalls
- Adding a sentence because a signal exists: the first reflex is the guardrail, the second the contract, the sentence last.
- Proposing again a candidate refused at the previous harvest: reread the harvest PRs closed in the window and mark these candidates as already refused.
- Treating a corrected human PR as an agent signal: only agent PRs and explicit `rule:` comments speak about the setup.
- Forgetting removals: a harvest with only ADDs grows the file into a monolith.
- Making a rule younger by rewriting it: its date is the incident's, not the last harvest's.
- Collecting by hand from the web interface: it is slow, not reproducible, and it ends up inventing.
