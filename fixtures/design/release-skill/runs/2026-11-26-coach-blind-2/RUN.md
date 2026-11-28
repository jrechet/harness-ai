# 2026-11-26 — harness-coach blind on release-skill, second run

A fresh agent, on a kit outside the repository holding the artifact, the skill and its CLI at commit dc357c0, without the answer key. Asked by the owner after the example of the skill stopped giving trap T7 away (plan row N16). The owner's answers were not given in advance, as they were on 2026-11-25: the agent could ask the user, and asked nothing. Two other agents, which had not seen it work, then read the records: one against the promises of the skill, one against what the owner would have answered (`request.md`). About 108,000 tokens for the run, 207,000 for the two readers. A single run.

**Result: 6 traps graded found out of 7, no healthy item moved** (`check.md`; `place check` exits 1).
- **T7 is graded found, on a premise and a destination the owner would not give.** The run of 2026-11-25 had been handed this trap by the skill's example; this one was not. But the agent called uncommitted files an incident nobody may go around at delivery, where the owner says lost time that only the agent must not forget. The answer key accepts the delivery step among five destinations; the owner would want the hook, and a delivery workflow starts from a clean checkout, so it cannot see uncommitted files on a workstation. The lure `traps.md` describes (leaving it in the skill because it is not an incident) was never met.
- **T1 is missed**: "Never publish from a branch other than `main`" is read as a rule checked at delivery, not as a limit nobody may override, and sent to a blocking step of the delivery workflow where the answer key expects a protection on the forge or a managed setting. No answer to "who must not go around it" reaches that place from a rule: only reading the piece as a limit does. On 2026-11-25 the prompt carried the owner's sentence "Nobody, developers included, must be able to publish outside main", and the piece was read as a limit: this miss is plausibly a cost of not asking. `runs/2026-11-15-blind-4` already noted that the sentence reads both ways.

## What the first reader found: the promises of the skill

Held: nothing written in the repository (`git status` empty, no `.harness`); no level, layer, medal, verdict code or grid id; weaknesses told as what the text cannot guarantee; one offer, nothing fixed; in French; `place review` run again gives `review.md` byte for byte.

Held with reservations:
- **Findings only from the review, nothing dropped**: the 12 pieces and the 6 concepts are all told, but the reason given for the rule on commits is the agent's, not the review's; a few of its own readings sit inside findings; parts of the review are left out without saying so (the hook and the settings path for the permission, the warning on injection).
- **Each `current` right**: 11 of 12. The rule on commits is given as held by a CI check that nothing shows to be required: the job runs on pull requests only, the kit has no remote. The reply says it as an assumption.
- **Understandable**: 1,075 words; "MCP server", "protected environment", "dry run" are not explained.

Not held:
- **What is good first**: a line "En bref" announces the weaknesses and their count before the section on what is good, as on 2026-11-25. "Where it is held today" is said for one concept of six.

It also saw what neither the agent nor the review says: the artifact has no `package.json`, so the commit check could not run as written, and none of the folders the dead-weight line names exists.

## What the second reader found: the answers the agent assumed

The agent gave nine decision answers (what it costs, who must not go around it) without asking. Against the owner's:
- Six hold: told to the user, and either the owner's answer or one that changes nothing. Two of the six are cost answers that are the reverse of the owner's (changelog, uncommitted files): an incident and lost time lead to the same question, so the review is the same. One of the six (who, for the changelog) holds on consistency only: the owner's words do not say it, and another answer would move the piece.
- **One is wrong and changes the review**: for "no release with uncommitted files" the agent assumed nobody may go around it at delivery; the owner means the agent only. The concept stays, the destination moves from a blocking step of the delivery workflow to a check run by a hook. The reply states the assumption for three rules at once and does not say what another answer would change. The grader accepts both destinations for T7, so the grade does not show it.
- **Two are not told to the user at all**, both on the rule about commits. The cost changes nothing. The who does: with "at delivery" or "the agent only" the piece leaves what is well placed, and `place check` then counts a healthy item moved. The owner's words do not settle it.

The tally counts only those two questions. How a piece is read (a rule or a limit) is not among them, and it is what missed T1.

Its reading of the cause: "Ask only when the review would change with the answer" cannot be applied, since the agent does not know the answer; it judged from the wording of the sentence. Its proposal: try the other options through `place review`, assume when they all give the same result, ask in one grouped question when they do not. By that test the cost can usually be assumed and "who must not go around it" asked.

## What it shows, and what it does not show

Two runs, two grades, and three things changed between them: the skill's example no longer gives T7, the owner's answers were not given in advance, and the prompt no longer restated that nothing is written. So 7 then 6 is not the price of the example alone: on 2026-11-25 T7 was given by the example and T1 helped by an owner's sentence in the prompt. Both times the skill was followed to the end by an agent that has never seen it, in one pass of `place review`, without leaking the grid's vocabulary, and both times with a line announcing the weaknesses first. This agent, free to ask, did not ask.

It does not measure how often:
- One run more, on the artifact the grid and `place review` were built against. No held-out artifact exists for the coach.
- The prompt named the three things to review, said which skill matched and told the agent to read it first: finding the skill was not put to the test.
- The two readers give a judgement, not a grade. The second one judged two answers on consistency: the owner's words do not say who for the changelog nor for the commits.
- `reply.md` is the one file of the run not in English: the reply, filed as evidence. It was typed again by the agent after the run from the message it had sent; it was compared with that message by reading, not byte for byte.

Not verified by anyone but the session that started the run: that the kit held no answer key and sat outside the repository (`bench` was not used), the token counts, that the records are what the agent wrote.

## Feedback (`notes.md`)

- No list of the values `current` accepts: guessed from the destinations of `place grid` (second time).
- No value for "the check exists, whether it is required cannot be seen from the repository" (second time).
- The skill speaks of one artifact; the user named three, and the note "Two things in one" speaks of the skill only.
- No `current` for a limit held by a subagent's own tool list.
- The description of the skill lists five concepts; the review names "An action without a guard" and "Two things in one" as well.
- The agent read step 2 as "assume and say so", and the pitfall "open the workflow before saying the text is all there is" as a push to credit a check that exists.
