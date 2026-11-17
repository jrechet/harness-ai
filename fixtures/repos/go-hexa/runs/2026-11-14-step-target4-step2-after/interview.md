# Interview of go-hexa: 2 question(s)

- I6, held only by the owner: never asked

## 1
**Question**: What is the first repetitive task you want to hand over whole to an agent, with its task contract? Proposed default if you have no preference: "add an HTTP route that changes a balance" (e.g. a new type of movement), since that is where idempotency, Money and migrations come into play.

**Answer** (first-task, forbidden): Add an endpoint from a use case, from the handler down to the test.
Touching a database that is not your own, modifying a migration already applied, running `deploy.yml` without `dry_run`.

## 2
**Question**: For this task, is there a step or a verification that you always do by hand when reviewing these PRs and that should be written in the contract?

**Answer** (default): Look in `docs/`, it is written down. The team knows nothing more than what the ADRs, the post-mortem and the operations note say.
