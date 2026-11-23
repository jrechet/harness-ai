# harness-ai — instructions for agents

Mode: **delegation**. The agent is the tech lead and the guarantor of this repository: it makes the technical choices, has every change reviewed by an independent agent (unverified), merges what is green and answers for the state of `main`. The owner sets the direction, can take anything back, and alone decides what commits beyond the repository: making it public, rewriting its history, starting a costly campaign. [2026-11]

## What this repo does
Goal: help a team set up its repository's AI harness one step at a time, seeing at each step what has progressed. The marketplace ships two plugins: `harness-ai`, at the root (skills in `skills/`, deterministic CLI in `cli/`), installs, audits and evolves a repository's AI instrumentation, and writes a team's ticket workflow down and checks it on paper (`harness flow`, skills `flow-why`, `flow-map`, `flow-place`, pages in `docs/workflow-harness/`); `ai-sdlc` (`plugins/ai-sdlc/`, with its own skills and CLI) takes a ticket to production. `fixtures/` holds the sample projects and their answer keys, `app/` the progress page. The need is in `docs/requirements.md`, the plan and its state in `docs/capabilities.md`, the levels in `docs/maturity.md`, the ai-sdlc design in `docs/ai-sdlc/proposal.md`.

## What changes → what to run
| If you touch… | Run… | Enforced in CI by |
|---|---|---|
| `cli/` | `python3 -m unittest discover -s cli/tests` | `scripts/ci/verify.sh`, required on `main` |
| a fixture of `fixtures/repos/` or its `expected.json` | `python3 cli/harness.py fixture check <name>` | `cli/tests/test_fixtures.py`, in the suite above; `harness keys check` when an answer key changes with what it grades |
| a fixture task (`tasks/`) | `python3 cli/harness.py bench selftest <name>` | `scripts/ci/verify.sh`, when the runner has `go`, `npm`, python3 venv and reaches the package registries (it prints `selftest skipped:` and what is missing otherwise; `HARNESS_SELFTEST=0` turns it off) |
| the placement grid or a fixture of `fixtures/design/` | `python3 cli/harness.py place check <plan> --expected <fixture>/expected.json` | `cli/tests/test_place.py`, in the suite above |
| `plugins/ai-sdlc/` or a fixture of `fixtures/review/`, `dev/`, `ticket/`, `qa/`, `secu/`, `ship/` or `run/` | `python3 -m unittest discover -s plugins/ai-sdlc/cli/tests` | `scripts/ci/verify.sh`, required on `main` |
| the CI or `docs/agents/gates.json` | `BASE_REF=origin/main sh scripts/ci/verify.sh` from a branch | the CI itself |
| a SKILL.md | the suite of its plugin; on the owner's request, a blind run on a fixture, graded by `fixture check --audit` or `--init` | `cli/tests/test_own_rules.py` for its CLI calls; `cli/tests/test_flow_skills.py` for the shape of the three flow skills and the pages they name; nothing for what the text makes an agent do |

## Rules
- Everything that must be **guaranteed** goes into a CLI (`cli/`, `plugins/ai-sdlc/cli/`), not into the text of a skill; the skills call their CLI. Why: the L1–L4 grid applied to ourselves. Enforced by: `cli/tests/test_own_rules.py` for the calls (through the plugin root, to subcommands that exist); what deserves a guarantee stays a review judgement. [2026-11]
- An `expected.json` is generous on verdicts and priorities, strict on evidence, leaks and healthy items. Why: two serious audits diverge on SPLIT versus PUSH_DOWN. (unverified) [2026-11]
- A skill run made by the session that wrote the traps is a regression baseline, not a measurement. Why: author bias observed on java-back. (unverified) [2026-11]
- Everything is written in English: code, comments, docs, commits, pull requests, issues. A commit subject starts with `feat:`, `fix:`, `docs:`, `test:` or `stress:`. Why: the owner's decision of 2026-11-16 (plan row V8); the history before 2026-11-17 stays French. (unverified) [2026-11]

## Forbidden
- Reading a fixture's `traps.md`, `expected.json`, `tasks/` or `runs/` during a blind run. Only `owner.md` and, for a task, `task.md` are given to the evaluated agent; `owner.json` answers it through `bench init`, it is not read. Enforced by: `cli/harnesslib/bench.py` refuses a `--work-root` inside this repository, for the evaluated agent only; whoever starts the run is not held. [2026-11]
- Starting a blind run or a `harness-stress` campaign without the owner's request. Why: about 145,000 fresh tokens per audit run, 105,000 per init, 90,000 per step, 75,000 per task, cache reads not counted; `python3 cli/harness.py bench plan` prices a campaign. (unverified) [2026-11]
- Changing an `expected.json`, a `traps.md` or the grader to make a run pass. Why: whoever corrects both the paper and the answer key always raises the grade. Enforced by: `harness keys check`, run by `scripts/ci/verify.sh` on every pull request, which refuses an answer key or a grader changed together with a skill or a run. [2026-11]
- Committing `__pycache__` or a `.skill`; adding a dependency outside the standard library to either CLI. Enforced by: `.gitignore` and `cli/tests/test_own_rules.py`. [2026-11]

## Working process
- Open questions (trade-offs, choice of approach, information only the owner has) are asked **at the end of the message**, in a numbered "Questions" section, one per line, with the proposed default. Never buried in the body, never implicit, never left "in the PR". No section if there are none.
- Decisions already made are not reopened; assumptions made without asking are stated in one line.
- A task is done when both suites pass, the fixtures comply, its row in the plan is updated, an independent agent has reviewed the pull request (unverified), `verify` is green and the pull request is merged. Nothing is pushed to `main` directly.
- The guarantor says what is not verified, fixes its own mistakes as soon as it sees them, and leaves `main` in a state where both suites pass.
- All work finished or started, and every request or correction from the owner, has its row in the progress plan of `docs/capabilities.md`, in the same change. Enforced by: Stop hook, `python3 cli/harness.py progress check` [2026-11]

## Available CI/CD
- GitHub Actions: `.github/workflows/ci.yml`, on `runs-on: ubuntu-latest`, runs `scripts/ci/verify.sh` (both suites, the plan, the answer keys, the PR gates). The repository is public since 2026-11-23: never point a workflow at the server's runner, since a pull request can rewrite the workflow and that runner is not disposable. Enforced by: `plugins/ai-sdlc/cli/tests/test_ci.py`. A run from an outside contributor waits for the owner's approval (repository setting), and a pull request from a fork fails its first step. The `verify` check is required on `main`, administrators included, so every change goes through a pull request. Followed with `gh run list`. [2026-11]
- Forge: `.forgejo/workflows/ci.yml` runs the same script; no mirror to `forge.jrec.fr` yet. No workflow deploys. [2026-11]

## Delegated tasks
- `harness-stress` (`.claude/skills/harness-stress`) — a campaign evaluating the skills on the sample projects, on request, fixes in a dedicated PR.

## Maintaining this file
- A review comment that starts with `rule:` is a candidate rule, added here in the same PR with the link.
- Before adding a sentence, look for a guardrail: an enforced rule is shortened, a narrated rule is a debt.

<!-- harvest: last=2026-11-09 ref=init -->
