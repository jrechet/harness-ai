# Interview of go-hexa: 2 question(s)

- I6, held only by the owner: never asked

## 1
**Question**: The next step is to write the contract of the first repetitive task you hand to an agent (.claude/skills/<task>/SKILL.md: steps, verifications, definition of done). What is this task? Default if you have no idea: none, I do not invent it.

**Answer** (first-task, done): Add an endpoint from a use case, from the handler down to the test.
A task is done when `make test` and `make arch` pass, a test covers the change, and the PR says why in two lines.

## 2
**Question**: For this task, is there a step, a verification or a stopping point specific to it that the agent cannot guess (beyond make test / make arch)?

**Answer** (default): Look in `docs/`, it is written down. The team knows nothing more than what the ADRs, the post-mortem and the operations note say.
