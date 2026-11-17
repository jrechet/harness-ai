I took one step: AGENTS.md now has a "Working process" section, written with the owner's answers. The targeted check went green, but the level reached stays 1.

- **The step**: I asked the owner the three questions of `L4.process` and wrote down their answers, wording aside, before "Maintaining this file". I checked beforehand that `make test` and `make arch` do exist in the `Makefile`.

- **Before and after**:

  | | Level reached | Level 4 — Delegated |
  |---|---|---|
  | Before | 1 · Framed | 1/5 |
  | After | 1 · Framed | 2/5 |

  The line that flipped: "A "Working process" section frames the agent". Level 2 is still waiting for its first real review signal (`L2.signal`), which does not block the climb towards level 4. Level 1 still holds: AGENTS.md goes from 33 to 39 lines, the limit is 60.

- **What it changes for the agent**: on a delegated ticket, it now knows:
  - when to ask before acting: migration, API contract, `deploy.yml`, or a ticket ambiguous about an amount or a rounding;
  - when it is done: `make test` and `make arch` green, a test that covers the change, and the why in two lines in the PR;
  - what to do about a red CI or a flaky test.

- **What is not proven**: `status` only checks that the section exists, not that agents follow it. There is no proof yet on the substance. It will come from a harness-harvest on real agent PRs: fewer after-the-fact corrections, and questions asked at the right moments. Nothing in this text is held by a tool, it is written judgement.

- **Files**: `AGENTS.md` only, not committed.
  - I left `.harness/` (`config.json`, `state.json`) as it was; it was already untracked before I came.
  - My first shell command (listing the kit) was refused because nothing could approve it. I read the same files another way, with no effect on the step.

- **Questions**:
  1. The owner gave the definition of done with `make test`, which does not run `go vet`. Yet the table at the top of AGENTS.md asks for `go vet ./... && go test ./...`. Should `go vet` be added to the `test` target of the `Makefile`? Proposed default: yes, so that both say the same thing. It is outside this step, I did not touch it.
  2. The definition of done mentions neither `make test-integration` when `internal/adapters/postgres` is touched (these tests do not run in CI), nor the `migrations` job. Should they be added? Proposed default: add them to the definition of done.

- **Possible next step**: `L4.contracts`. The owner must be asked for the first repetitive task to hand over, then its contract `.claude/skills/<task>/SKILL.md` written and cited in AGENTS.md.