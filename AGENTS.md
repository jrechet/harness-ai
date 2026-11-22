# harness-ai — instructions for agents

Mode: **delegation**. The agent is the tech lead and the guarantor of this repository: it makes the technical choices, has every change reviewed by an independent agent, merges what is green and answers for the state of `main`. The owner sets the direction, can take anything back, and alone decides what commits beyond the repository: making it public, rewriting its history, starting a costly campaign. [2026-11]

## What this repo does
Claude Code skills (`skills/`), deterministic CLI (`cli/`), evaluation fixtures (`fixtures/`) and progress app (`app/`) to install, audit and evolve a repository's AI instrumentation. Maturity model in `docs/maturity.md`, requirements and state in `docs/requirements.md`.

## What changes → what to run
| If you touch… | Run… | Enforced in CI by |
|---|---|---|
| `cli/` | `python3 -m unittest discover -s cli/tests` | `scripts/ci/verify.sh`, required on `main` |
| a fixture or its `expected.json` | `python3 cli/harness.py fixture check <name>` | nothing |
| a fixture task (`tasks/`) | `python3 cli/harness.py bench selftest <name>` | `scripts/ci/verify.sh`, when the runner has `go`, `npm`, python3 venv and reaches the package registries (it prints `selftest skipped:` and what is missing otherwise; `HARNESS_SELFTEST=0` turns it off) |
| the placement grid or a fixture of `fixtures/design/` | `python3 cli/harness.py place check <plan> --expected <fixture>/expected.json` | nothing |
| `plugins/ai-sdlc/` or a fixture of `fixtures/review/`, `dev/`, `ticket/`, `qa/`, `secu/`, `ship/` or `run/` | `python3 -m unittest discover -s plugins/ai-sdlc/cli/tests` | `scripts/ci/verify.sh`, required on `main` |
| the CI or `docs/agents/gates.json` | `BASE_REF=origin/main sh scripts/ci/verify.sh` from a branch | the CI itself |
| a SKILL.md | a blind run on a fixture, graded by `fixture check --audit` or `--init` | nothing |

## Rules
- Everything that must be **guaranteed** goes into `cli/`, not into the text of a skill; the skills call the CLI. Why: the L1–L4 grid applied to ourselves. (unverified) [2026-11]
- An `expected.json` is generous on verdicts and priorities, strict on evidence, leaks and healthy items. Why: two serious audits diverge on SPLIT versus PUSH_DOWN. (unverified) [2026-11]
- A skill run made by the session that wrote the traps is a regression baseline, not a measurement. Why: author bias observed on java-back. (unverified) [2026-11]

## Forbidden
- Reading a fixture's `traps.md`, `expected.json`, `tasks/` or `runs/` during a blind run. Only `owner.md` and, for a task, `task.md` are given to the evaluated agent; `owner.json` answers it through `bench init`, it is not read. [2026-11]
- Starting a blind run or a `harness-stress` campaign without the owner's request. Why: about 130,000 tokens per run. [2026-11]
- Changing an `expected.json`, a `traps.md` or the grader to make a run pass. Why: whoever corrects both the paper and the answer key always raises the grade. [2026-11]
- Committing `__pycache__` or a `.skill`; adding a dependency outside the standard library to the CLI. [2026-11]

## Working process
- Open questions (trade-offs, choice of approach, information only the owner has) are asked **at the end of the message**, in a numbered "Questions" section, one per line, with the proposed default. Never buried in the body, never implicit, never left "in the PR". No section if there are none.
- Decisions already made are not reopened; assumptions made without asking are stated in one line.
- A task is done when the tests pass, the fixtures comply, and the commit is pushed to `main`.
- The guarantor says what is not verified, fixes its own mistakes as soon as it sees them, and leaves `main` in a state where both suites pass.
- All work finished or started, and every request or correction from the owner, has its row in the progress plan of `docs/capabilities.md`, in the same change. Enforced by: Stop hook, `python3 cli/harness.py progress check` [2026-11]

## Available CI/CD
- GitHub Actions: `.github/workflows/ci.yml`, on `runs-on: [self-hosted, jre-server]`, runs `scripts/ci/verify.sh` (both suites, the plan, the PR gates). Runs on the server's runner, set up by the owner (variable `CI_RUNNER`); the `verify` check is required on `main`, administrators included, so every change goes through a pull request. Followed with `gh run list`. [2026-11]
- Forge: `.forgejo/workflows/ci.yml` runs the same script; no mirror to `forge.jrec.fr` yet. No workflow deploys. [2026-11]

## Delegated tasks
- `harness-stress` (`.claude/skills/harness-stress`) — a campaign evaluating the skills on the sample projects, on request, fixes in a dedicated PR.

## Maintaining this file
- A review comment that starts with `rule:` is a candidate rule, added here in the same PR with the link.
- Before adding a sentence, look for a guardrail: an enforced rule is shortened, a narrated rule is a debt.

<!-- harvest: last=2026-11-09 ref=init -->
