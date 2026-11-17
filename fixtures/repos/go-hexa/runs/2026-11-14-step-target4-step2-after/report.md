I wrote the contract of the first task to delegate and cited it in AGENTS.md. `status` confirms that the targeted check passed. Nothing is committed.

- **The step**: the owner chose the task "add an endpoint from a use case, from the handler down to the test". Its contract is now in `.claude/skills/add-endpoint/SKILL.md` and cited under a new "Delegated tasks" section of AGENTS.md.
- **Before and after**: we stay at level 1 reached (target: level 4). Level 4 goes from 2/5 to 3/5. The line that flipped: "At least one task contract exists and is referenced".
- **What it changes for the agent**: when it is handed a new route, it has a written path, from the layers up to the PR. For a route that changes a balance, the contract imposes three things: the idempotency key looked up inside the transaction, the `Idempotency-Replayed: true` header on a replay, and tests of the replay and of the conflict. It also says what is not to be used as a model (`fees.go`, the exemption of `POST /accounts`).
- **What is not proven**: `status` only checks that a file exists and that it is cited. It does not say that agent PRs on this task come back clean. That proof will come from a harness-harvest on real agent PRs (check "PRs with no after-the-fact correction", waiting). None exists for now. This step adds no guardrail that blocks.
- **Files**:
  - `.claude/skills/add-endpoint/SKILL.md` (created)
  - `AGENTS.md` ("Delegated tasks" section added, two lines)
- **Questions**:
  1. I left the `Idempotency-Replayed` header missing from `POST /transfers`: the contract asks to report it, not to fix it in passing. Proposed default: handle it separately, it is action 5 of the audit.
  2. The contract assumes that an agent cannot run `make test-integration` (the pgx driver is missing from `go.mod`) and asks it to write that in the PR. Proposed default: keep this until action 6 of the audit (PostgreSQL integration tests in CI) is done.
- **Out of scope, noted for later**: the owner's answer to my first question added three things not to do. They were already in the Forbidden section of AGENTS.md; the contract takes them up in its "Never" section.
- **Possible next step**: make the audit's "cut the agent" test pass, by moving into a script or a workflow the first step that exists only in a prompt.