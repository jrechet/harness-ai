# Notes on the run

## Unclear, missing or in the way

- `current` has no documented list of allowed values. SKILL.md gives `skill`, `agents_md`, `subagent`, `session` as examples and says a rule held by a check is "held by that check"; I guessed that the destination ids of `place grid` (`ci_check`) are accepted. `place review --help` only says `list of {piece, answers, current, evidence?}`.
- "Found blocking": whether a CI job is required for merging is a forge setting, not visible in the repository. The skill does not say what to put in `current` when the job exists but its required status cannot be checked. I put `ci_check` and stated it as an assumption; no value for "exists, required status unknown".
- The skill does not say how fine to split. Cases I had to decide alone: tag+push and `npm publish` as one piece (same kind) or two; "three lines at most" as a separate preference rule or part of the writing judgement (kept in the judgement: a rule with "costs nothing" leads to the scope question, none of whose answers is "in the skill"); whether "before sending it" is an action of the agent (I made it a piece, and stated the assumption).
- A sentence that is both a limit and contradicted by another file (AGENTS.md:6 allows reading the token during a release, SKILL.md:16 makes the agent copy it, the user wants it never readable): one `current` value cannot carry "two texts disagree". Given as a remark.
- "Never publish outside main" can be read as a limit (who may not override it) or as a rule checked at delivery. Both are defensible; the grid gives different destinations (server-side protection vs blocking step of the delivery workflow). I chose limit because the user's answer is about who must not be able to.
- The "Two things in one" section of the review lists "Repository structure" and "Send the announcement" among the items "a sentence cannot hold", though one is dead weight; minor.
- The destination text for the computation says "a subcommand of the repository's CLI"; the user says the repository has no CLI. The skill gives no instruction for adapting the review's wording; I added "a script of package.json" in my own words.
- The destination "why" for the MCP server ends with "a ticket can carry an injection", which does not fit a write to a channel; I left that sentence out.
- The sample repository contains no package.json, no commitlint configuration and no .claude/settings.json, although the user says the scripts are in package.json. Said in the remarks.
- Step 2 says "ask only when the review would change with the answer": the provided answers were all decisions of that kind (cost, who must not bypass), so I used them as given.
- The task asked to write nothing in the repository: nothing was written there; pieces file in the temporary folder.

## Commands run (in order) and exit codes

Run from the coach-run folder.

1. `ls -la . plugin plugin/skills out tmp; cat plugin/skills/harness-coach/SKILL.md` — exit 0
2. `find . -type f -not -path './.git/*'` and `cat -n` of each file, in `repo/` — exit 0
3. `python3 plugin/cli/harness.py place grid` — exit 0
4. `python3 plugin/cli/harness.py place grid --format json` — exit 0
5. `python3 plugin/cli/harness.py place review --help` — exit 0
6. `ls -la repo repo/.claude repo/.github/workflows` — exit 0
7. `python3 plugin/cli/harness.py place review tmp/pieces.json` (output to tmp/review.md) — exit 0, first try, no missing answer
8. `cp tmp/pieces.json out/pieces.json; cp tmp/review.md out/review.md`, then writing out/reply.md and out/notes.md — exit 0

`status` was not run.

## User answers used

- Nobody, developers included, may publish outside main → "Never publish from a branch other than main": limit, nobody in the repository.
- A version published without a changelog entry is an incident → changelog rule: incident, checked at delivery.
- A miscomputed version is an incident → used for the cost of the Conventional Commits rule (the version derives from it) and in the reply; the computation piece itself has no cost question.
- The token must never be readable by the agent; a developer has access → token limit: the agent alone.
- The tone of the announcement is free → the announcement is judgement, not a rule.
- Uncommitted files: not an incident, but must not be forgettable → rule, lost time / must not be forgotten, the agent alone.
- GitHub with GitHub Actions, no CLI, scripts in package.json → wording of the destinations in the reply (delivery workflow on GitHub Actions, script in package.json).

All seven were used. None had to be "asked": I took them as the answers to the two decision questions of step 2.
