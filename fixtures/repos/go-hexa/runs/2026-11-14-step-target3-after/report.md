## Report — harness-step

**The step**: the `Idempotency-Key` rule is now held by a Go test. It is the only rule whose incident is still open: the 2026-04 postmortem says "a new write endpoint can still forget the key: the review is the only check". The test walks every HTTP route. Each route that is not a read (neither GET nor HEAD) must answer `400 idempotency_key_required` when the key is missing. It runs in the `test` job, which already blocks in CI.

**Before and after**
- Level: 1 · Framed, before as after. Target: 3.
- Level 3: 2/4 before, 2/4 after. **The targeted check did not flip.** The rules held by a tool go from 1/8 to 2/8, whereas 4/8 are needed to validate it. The step is done for this rule, but the `L3.guarded` check still fails. Two more guarded rules will be needed, each in its own step.
- The line that changed: in `harness rules`, `AGENTS.md:17` goes from "no, marked" to "yes".
- I saw the guardrail bite. I added a fake route `POST /accounts/{id}/credit` without a key: the test went red with a message that points to the postmortem. I removed the fake route: `go vet`, `go test ./...` and `archcheck` pass.

**What it changes for the agent**: if it adds a write endpoint without requiring `Idempotency-Key`, the `test` job blocks it in CI. Before, only the review could see it.

**What is not proven**
- `status` measures the shape of the harness, not whether agents work better. No agent PR has hit this guardrail yet; the proof will come from the next harvests.
- The test only checks the presence of the key. The second half of the rule, "looked up inside the transaction, never before", is still left to the review, and the rule says so.
- The test sends a `{}` body to each route. A route that refuses this body before even looking at the key will come out red, which pushes towards checking the key first. The only current write route (`POST /transfers`) passes.

**Files**
- `internal/adapters/httpapi/server.go`: the routes are now listed in a single table that the test can walk. The behaviour does not change.
- `internal/adapters/httpapi/idempotency_guard_test.go` (new): the guardrail, with a list of exemptions in which each entry must give its reason. A second test fails if an exemption no longer matches any route.
- `AGENTS.md`: the rule now carries "Enforced by" and the "(unverified)" marker is removed. The file is still under 60 lines.
- Nothing is committed nor pushed: the changes are in the working copy, and I am waiting for your go-ahead to open the PR. I did not touch the `.harness/` folder, which is not tracked by git.

**Points blocked during the session**: two grouped commands (`ls`/`cat` of the kit, `grep` in the CLI) were refused, because this session cannot approve a permission. I replaced them with direct reads, with no loss for the step.

**Questions**
1. `POST /accounts` is exempt, as AGENTS.md already said. Does this endpoint change a balance in the sense of the rule? Proposed default: yes, it will have to be aligned one day and the exemption removed, but not in this step.

**Out of scope, noted**: the `lint` job is in `continue-on-error`, so the "no float" rule has no guardrail that blocks. `internal/app/fees.go` already violates it.

**Possible next step**: guard a second narrated rule. The cheapest is probably "an applied migration is never modified again", with a PR check that refuses any modification of an existing file of `migrations/`. This check would also hold the matching line of the Forbidden section.