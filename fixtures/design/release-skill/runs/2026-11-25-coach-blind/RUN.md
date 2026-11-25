# 2026-11-25 — harness-coach blind on release-skill

A fresh agent, on a kit outside the repository holding the artifact, the skill and its CLI at commit 47cf733, without the answer key. It was asked, in French, to review the `release` skill, its subagent and the rules of `AGENTS.md`. A second agent, which had not seen it work, then checked the reply against the promises of the skill. About 213,000 tokens for both agents. A single run, at the owner's request.

**Result: 7 traps found out of 7, no healthy item moved** (`check.md`): the pieces file the coach wrote for `place review` has the format `place check` grades. The reply is in `reply.md`, the command's output in `review.md`.

## What the second agent found

Nine promises checked, nine held: every finding of the reply is in the review and nothing of the review is dropped; nothing written in the repository (`git status` empty, no `.harness`); no level, layer, medal, verdict code or grid id; what is good first, then one concept at a time in the review's order, then the assumptions, then the agent's own remarks apart; one offer, no fix; in French; each `current` right. Running `place review` again on `pieces.json` gives `review.md` byte for byte.

Its reservations:
- A line "Verdict court" announces the weaknesses before the section on what is good.
- About 1,465 words for 12 pieces: the upper limit. The assumptions and the remarks are a good third of it.
- "hook", "MCP server", "forge", "protected environment" are not explained.
- Some of the review's sentences are left out or adapted (the hook for the token, the sentence on injection; "CLI subcommand" became "a script of package.json", since the owner says the repository has no CLI).

## What it shows, and what it does not show

It shows that an agent that has never seen the skill can follow it to the end, in one pass of `place review`, and say the result in concepts without leaking the grid's vocabulary.

It does not measure how often. It is one run, on a fixture that served to correct the grid and `harness-design`, so the split of this artifact is the one the grid was tuned on. The owner's answers were given at the start, where a real user would be asked. `ticket-to-pr`, held out, is a creation request and has nothing to review. The second agent's reading is a judgement, not a grade.

## Feedback (`notes.md`)

- The skill gives no list of the values `current` accepts; the agent guessed that the destination ids of `place grid` are accepted.
- No value for "the check exists, whether it is required cannot be seen from the repository": the agent wrote `ci_check` and said it as an assumption.
- The skill does not say how fine to split (tag and publish: one piece or two).
- "Never publish outside main" reads as a limit or as a rule checked at delivery: already noted on 2026-11-15.
- The "Two things in one" note lists the dead weight among the items "a sentence cannot hold".
- The review's wording for a computation says "the repository's CLI" when the repository has none; the skill does not say whether to adapt it.
