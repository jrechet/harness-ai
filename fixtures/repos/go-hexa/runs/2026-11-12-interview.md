# The interview of step 1, before and after — 2026-11-12

What was measured: step 1 played blind by `bench init`, with an owner who only answers what they are asked (`owner.json`). Two runs, same day, same model, same owner; only the text of the skill changes.

| | Before | After |
|---|---|---|
| Skill | `main`, three questions | branch `stress/2026-11-12`, a fourth question |
| Questions asked | 6 | 7 |
| The fact only the owner holds | never asked | asked at question 4 |
| Score of step 1 | 5/6 | 6/6, ok |
| New tokens | 83,911 | 47,769 |

For the record, the same step with the answers given in advance, the same day: 6/6 (`2026-11-12-init-blind`). The owner who says everything of their own accord masked the defect.

## What each agent asked
- **Before**: the three questions of the skill, then three about what it saw in the repository: the float of `fees.go`, the missing `make e2e` target, `POST /accounts` without an idempotency key. Nothing about what the team knows without having written it.
- **After**: the four questions of the skill, the fourth word for word, then three about the repository. The answer becomes a rule dated June 2026, "told by the team", with the counter-example `POST /transfers` flagged.

## The simulated owner, edited after the two measurements
During the two measurements, `owner.json` was the same. Read afterwards, it was too literal: three plausible ways out of eight of asking what is written nowhere got the answer, and two answers fell off topic. Its triggers were widened: seven out of eight, and a test pins both sides. Replayed against the new triggers, the two interviews keep their verdict: before, never asked; after, at question 4.

## What it does not prove
- **Author bias.** The question of the skill and the owner's triggers were written by the same session, and the agent asked the question word for word. The test of neighbouring phrasings reduces this bias without erasing it. A real owner remains the reference.
- **One draw per arm**, a single model.
- **Before, question 6 was about idempotency.** A real owner might have cited the header on that occasion; the simulated one does not.
- **Nothing outside the tuning bench.** The held-out project holds its fact in its own instructions: it cannot measure this question. No other project has a simulated owner.
