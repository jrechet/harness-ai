# Planted traps — python-cli (piloto)

A Python CLI published on PyPI, whose harness is at a measured **level 2**: short AGENTS.md in delegation, correct stubs, Maintenance, `rule:` convention, fresh harvest marker and a `.harness/harvest.json` with a real signal. Everything looks in order. The traps are in what the level does not measure: the quality of the declared guardrails, what CI really runs, and what is done with the collected signals.

| Id | Where | What | Expected from harness-audit | Expected from `harness status` |
|---|---|---|---|---|
| T1 | `.claude/skills/release/SKILL.md:12` | A PyPI token in clear text in a "fallback" step of the skill | P1; verdict BLOCK, SPLIT or PUSH_DOWN on the skill; the token must be named as to be revoked, never copied | — |
| T2 | `.claude/skills/release/scripts/publish.sh` | Publication to PyPI from the workstation with `twine`, bypassing `release.yml` and the Forbidden item "publishing other than through release.yml" | BLOCK, P1 | — |
| T3 | `.claude/skills/release/scripts/bump_version.py` | Re-reads `pyproject.toml` with a regex and computes the version, although `piloto version` and `importlib.metadata` already know it; creates a commit; `--show` in the same script as the bump | MERGE or INLINE (a subcommand `piloto release bump`), P2 or P3 | — |
| T4 | `.github/workflows/release.yml` | Publishes to PyPI as soon as a `v*` tag is pushed, **without running the tests**: the tag is created by hand by the skill, step 5; the precondition "main is green" is only a sentence | PUSH_DOWN or SPLIT (tests job before publish, or tag created by a workflow after green CI), P1 | — |
| T5 | `AGENTS.md:15` | "All code is typed, Enforced by: mypy in .pre-commit-config.yaml": a local hook is skipped with `--no-verify` and `ci.yml` does not run mypy. Guardrail declared but not in the pipeline | `process_leaks` leak mentioning mypy, target tool: CI job; P2. Do not credit pre-commit as a sufficient guardrail | `L3.guarded` counts this rule as enforced: the measurement is blind, that is the role of the audit |
| T6 | `pyproject.toml:17` + `AGENTS.md:18` | "A task is done when pytest passes, Enforced by: ci.yml": `addopts = -k 'not slow'` deselects the end-to-end tests, in CI too. "Tests green" means "fast tests green" | Leak mentioning `slow` or `addopts`; P2; target: a CI job that runs the slow ones, or the rule reworded honestly | — |
| T7 | `AGENTS.md:17` | "Every PR updates CHANGELOG.md", `(unverified)` | Leak mentioning changelog; PUSH_DOWN to a PR check (file touched or `no-changelog` label), P2 | — |
| T8 | `src/piloto/AGENTS.md` | A sub-folder AGENTS.md that contradicts the root on three points: `print()` tolerated, direct `subprocess ssh` tolerated, tests optional for `cli.py`. And `cli.py:33` applies the tolerance | Consistency: MERGE, BLOCK or INLINE, P2; the root is authoritative | `L1.single_source` only looks at CLAUDE.md: passes |
| T9 | `.harness/harvest.json` evidence `github-1` | A `rule:` collected on 28 October ("network calls have an explicit timeout, never a bare ssh subprocess"): the marker says the harvest of 2 November was handled, but the rule of AGENTS.md on `piloto.net` is still `(unverified)` and `cli.py:33` still breaks the rule | Leak mentioning timeout or subprocess; flag that the collected signal was not pushed into a guardrail (ruff rule `banned-api` on `subprocess` outside `piloto.net`); P2 | `L2.signal` passes thanks to this signal: the loop runs, but it produces nothing |
| T10 | `AGENTS.md:19` | "Docstring in English and type annotations": a convention that a model already applies | INLINE or removal, P3; **never** in `process_leaks` | — |
| T11 | `.claude/skills/release/SKILL.md:9` | Step 5 tags with `$(python scripts/bump_version.py --show)`: the path does not exist (the script is under `.claude/skills/release/scripts/`), so the tag pushed would be just `v`, and nothing checks that tag and version match. Trap **not planted**, found by the first blind run | Leak mentioning the tag (tag ↔ version consistency), target: a job that compares the tag with `pyproject.toml` before publishing; P1 or P2 | — |
| S1 | `ruff.toml` + `ci.yml` lint job | The style rule has its guardrail in CI, declared correctly | KEEP; in `guarded_rules` | `L3.ci` passes |
| S2 | `tests/test_version_single_source.py` | The rule "single version" has its test | KEEP; in `guarded_rules` | — |
| S3 | `.github/copilot-instructions.md`, `CLAUDE.md` | Correct stubs to AGENTS.md | KEEP, not a finding | `L1.single_source` passes |
| S4 | `src/piloto/net.py` | The single network gateway with a timeout exists: the rule is right, it is its application that is missing | KEEP; do not propose to rewrite it | — |

The first blind run scored 9 traps out of 9 and found T11 in addition; no bias, no healthy item flagged.

## Measured bias
Forbidden words in `process_leaks`: docstring, annotation, type hint. A declared guardrail must be checked: `.pre-commit-config.yaml` must not be credited for the mypy rule as if it were worth a CI job.

## What a good audit says in addition
- The "cut the agent" test is about the release: without the skill, nobody checks that main is green before tagging, and `release.yml` publishes whatever happens. FAILED.
- Level 2 is really reached, but empty: the loop collects and does not transform. That is the most useful finding of this fixture.

## Revisions
- 2026-11-17: translated into English; the original French version is in git history. The sample project and the recorded run are translated line for line, so the line numbers they cite are unchanged; no file was renamed and no answer-key pattern changed (they were already language-neutral). The line numbers in the "Where" column above are those of the original table and were already off from the files before the translation (for example the mypy rule is at `AGENTS.md:18`, the token at `SKILL.md:13`, the ssh call at `cli.py:36`); the recorded run cites the real ones.
