# piloto — instructions for agents

Mode: **delegation**. An agent can be handed a whole task and open a PR without intermediate review. What is mandatory is enforced by CI; this file explains, it does not guarantee.

## What this repo does
Python 3.12 CLI (`src/piloto`) that pushes configuration files to servers over SSH, with a `diff` mode. Published on PyPI on every `v*` tag. Reference: `docs/agents/`.

## What changes → what to run
| If you touch… | Run… | Enforced in CI by |
|---|---|---|
| `src/` | `ruff check . && pytest` | `ci.yml` jobs lint, tests |
| `pyproject.toml` | `pytest tests/test_version_single_source.py` | `ci.yml` job tests |
| the release | `.claude/skills/release` | `release.yml` on tag |

## Rules
Each rule says why and what enforces it.
- Style follows ruff (`ruff.toml`). Why: formatting diffs were drowning the reviews. Enforced by: `ruff check` in `ci.yml`.
- All code is typed and passes mypy in strict mode. Why: an unhandled `None` wiped a server's config (#23). Enforced by: `mypy` in `.pre-commit-config.yaml`.
- The version exists in one place only, `pyproject.toml`; the code reads it through `importlib.metadata`. Why: two diverging versions published on PyPI (#31). Enforced by: `tests/test_version_single_source.py`.
- Every PR updates `CHANGELOG.md`. Why: release 1.4 shipped with an empty changelog. (unverified)
- A task is done when `pytest` passes. Enforced by: `ci.yml` job tests.
- Public functions have a docstring in English and type annotations.
- Network calls go through `piloto.net` and never through a direct `subprocess`. Why: an `ssh` without a timeout blocked CI for forty minutes (#38). (unverified)

## Forbidden
- Publishing to PyPI other than through `release.yml` on a tag.
- Changing a version already published.
- Pushing to `main` without a PR.

## Working process
- Stop and ask when: the task touches publication, changes a command interface, or CI is red for a cause unrelated to your diff.
- A task is done when: lint and tests green, a test covers the change, `CHANGELOG.md` up to date, the PR explains the why.
- CI red: fix it if the cause is in your diff; otherwise report it and leave it alone.

## Delegated tasks
- `release` (`.claude/skills/release`) — prepare and publish a version.

## Maintaining this file
- A review comment that starts with `rule:` is a candidate rule, added here in the same PR with the link, or collected by harness-harvest.
- Before adding a sentence, look for a guardrail: an enforced rule is shortened, a rule that is only told is a debt.

<!-- harvest: last=2026-11-02 ref=https://github.com/acme/piloto/pull/41 -->
