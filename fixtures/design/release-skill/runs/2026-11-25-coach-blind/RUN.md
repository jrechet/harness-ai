# 2026-11-25 — harness-coach blind on release-skill

A fresh agent, on a kit outside the repository holding the artifact, the skill and its CLI at commit 47cf733, without the answer key. It was asked, in French, to review the `release` skill, its subagent and the rules of `AGENTS.md`. A second agent, which had not seen it work, then checked the reply against the promises of the skill. About 213,000 tokens for both agents. A single run, at the owner's request.

**Result: 7 traps found out of 7, no healthy item moved** (`check.md`), **of which 6 unaided**: the skill's own format example (`skills/harness-coach/SKILL.md:31-33`) is trap T7 of this fixture, with its answers, its `current` and its line. The pieces file the coach wrote for `place review` has the format `place check` grades. The reply is in `reply.md`, filed verbatim in French because it is the evidence (the only file of the run not in English); the command's output is in `review.md`, the prompt in `prompt.md`.

## What the second agent found

Nine promises of the skill read against the records. Seven held: every finding of the reply is in the review; nothing written in the repository (`git status` empty, no `.harness`); no level, layer, medal, verdict code or grid id; weaknesses told as what the text cannot guarantee; one offer, no fix; in French; each `current` right. Two held with reservations:
- **Nothing of the review dropped**: every well-placed piece and every concept is told, but some of the review's sentences are left out or adapted (the reason of the computation, the hook for the token, the sentence on injection; "CLI subcommand" became "a script of package.json", since the owner says the repository has no CLI).
- **What is good first**: the sections are in the asked order, but a line "Verdict court" announces the weaknesses and their count before the section on what is good.

Running `place review` again on `pieces.json` gives `review.md` byte for byte.

Its opinion, on which the skill sets no rule: about 1,465 words for 12 pieces is long, the assumptions and the remarks being a good third of it; "hook", "MCP server", "forge", "protected environment" are not explained.

## What it shows, and what it does not show

It shows that an agent that has never seen the skill can follow it to the end, in one pass of `place review`, and say the result in concepts without leaking the grid's vocabulary.

It does not measure how often, and the 7/7 is less than it looks:
- One run.
- **T7 was handed over**: the skill's example is that trap, the one `runs/2026-11-15-blind-3` missed.
- The fixture served to correct the grid and `harness-design`, and `place review` itself is tested on this fixture's author plan (`cli/tests/test_place.py`): the sorting into well placed and concepts was built against this artifact.
- The prompt named the three things to review, so the agent did not have to find what the skill calls; it gave the owner's answers at the start, where a real user would be asked; and it restated that nothing is written outside the kit, so "nothing written in the repository" is partly prompted.
- `ticket-to-pr`, held out, is a creation request and has nothing to review: no held-out artifact exists for the coach.
- The second agent's reading is a judgement, not a grade.

Not verified by anyone but the session that started the run: that the kit held no answer key and sat outside the repository (`bench` was not used, nothing enforced it), the token count, that the filed records are what the agent wrote.

## Feedback (`notes.md`)

- The skill gives no list of the values `current` accepts; the agent guessed that the destination ids of `place grid` are accepted.
- No value for "the check exists, whether it is required cannot be seen from the repository": the agent wrote `ci_check` and said it as an assumption.
- The skill does not say how fine to split (tag and publish: one piece or two).
- "Never publish outside main" reads as a limit or as a rule checked at delivery: already noted on 2026-11-15.
- The "Two things in one" note lists the dead weight among the items "a sentence cannot hold".
- The review's wording for a computation says "the repository's CLI" when the repository has none; the skill does not say whether to adapt it.
