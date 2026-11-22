# Traps of the flow `library_upgrade`

A believable flow: a ticket asks to move a shared library to its next major version, across its call sites, with a rewrite of the stored records after the merge. The file passes `flow check`. Two things are planted, and three steps are there to tempt a wrong answer.

## What is planted

| Step | What the definition says | Where it must land | Why |
|---|---|---|---|
| `backfill` | `survives: midway`: it rewrites three years of records in batches over several days, and no batch may be applied twice | "this would need an engine" (`durable_engine`) | It is the only step whose work lives for days inside one computation and must go on from the middle after a cut. A ticket state and a later event cannot hold that: started again from its beginning, it would apply batches twice |
| `backfill_sign_off` | `can_judge: no`: the product owner is shown a log of forty thousand lines of record identifiers | "no gate here" (`no_gate`) | The gate has a judge, a deadline, something shown and a way to refuse, so `flow check` accepts it. But nobody could tell a good log from a bad one by reading it: the approval would only be a signature. The placement refuses it and the flow fails `flow place` |

`backfill` must be the only name in the list of steps that need an engine, and `backfill_sign_off` the only refused gate. The verdict is "one step would need an engine", and the placement does not pass, because of the gate, not because of the engine: needing an engine is an answer, a gate nobody can judge is a failure.

## What only looks like a trap

| Step | Why it tempts | Where it must land | Why |
|---|---|---|---|
| `merge_wait` | It lasts up to ten days | "the ticket holds this" (`ticket_state`) | Nothing runs while it waits. A long wait between two steps is a state on the pull request and a later event, never an engine |
| `adapter_rewrite` | An agent works for up to four hours and has a deadline of six | "a skill is enough" (`skill`) | `survives: restart`: cut, it starts again from its beginning and only time is lost. Long is not the same as "must resume in the middle" |
| `plan_approval` | Its deadline is two weeks | "this is a human gate" (`human_gate`) | The tech lead is shown a plan they can read and refuse (`can_judge: yes`). A long deadline changes nothing: the ticket holds the wait |

## The other places the flow visits

| Step | What the definition says | Where it must land |
|---|---|---|
| `compat_check` | `repositories: several`: every service repository runs the same check | "this is a shared CI workflow" (`reusable_workflow`) |
| `planning` | `weak_model: yes`: the step is cut in small pieces because today's model drops items of a long changelog | "a skill is enough, with its date" (`dated_skill`) |
| `call_sites` | `units: many`: forty independent changes | "this is a fan-out by script" (`campaign`) |
| `intake`, `publish_plan`, `open_pr`, `closing` | Programs whose output is determined by their inputs | "this is code" (`code`) |

`call_sites` is asked "does the work split into many independent units" before "how many repositories", and `backfill` is stopped at "how long does it live, and what must survive" before any other question: the order of the grid decides, and the answer key follows it.
