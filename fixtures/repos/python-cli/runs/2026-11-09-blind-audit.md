# Harness audit — release of piloto (Python CLI published on PyPI)

**Scope**: `fixtures/repos/python-cli/repo/` (AGENTS.md, CLAUDE.md, Copilot stub, `src/piloto/AGENTS.md`, `release` skill and its scripts, `.github/workflows/`, ruff, mypy/pre-commit, pytest, `.harness/`) · **Date**: 2026-11-09 · **Items inventoried**: 17

## 1. Summary

- **Health score**: 2 — the agent is a pillar: the fallback publication, the release preconditions, the tag/version consistency and the final check live only in `SKILL.md`, and that same file carries a PyPI token in clear text.
- **Result of the "cut the agent" test**: FAILED — 4 step(s) of the process exist only in prompts (main green, CHANGELOG filled in, tag consistent with `pyproject.toml`, check of the publication).
- **Blocking points (P1)**: 2
- **The three actions that change the most**:
  1. Revoke the PyPI token written in `.claude/skills/release/SKILL.md:13`, remove the line and `.claude/skills/release/scripts/publish.sh`: the publication path outside `release.yml` is forbidden by `AGENTS.md:26` and the skill contradicts it with a secret.
  2. Add to `release.yml` a `verify` job before `publish`: lint, mypy, tests, `tag == pyproject version`, non-empty `## <version>` section in `CHANGELOG.md`. Today a tag pushed on any commit publishes.
  3. Replace `bump_version.py` with a tested subcommand (`piloto-release plan|bump`, or `uv version`) with `--dry-run`, clean tree, tag absent; point the skill at it and fix the wrong path of `SKILL.md:12`.

Computation: 100 − 2 × 25 (P1) − 6 × 8 (P2) − 0 × 2 (P3) = 2; the cap of 60 from the failed "cut the agent" test has no effect.

## 2. Map of the harness

| # | Item | Path | Declared layer | Actual layer | Called by | Calls |
|---|---|---|---|---|---|---|
| 1 | Root AGENTS.md | `AGENTS.md` | L2 | L2 | CLAUDE.md (`@`), copilot-instructions | release skill, docs/agents, ci.yml, release.yml, pre-commit, test_version_single_source, ruff.toml |
| 2 | CLAUDE.md | `CLAUDE.md` | L2 | L2 | Claude Code (auto-loaded) | AGENTS.md |
| 3 | Copilot stub | `.github/copilot-instructions.md` | L2 | L2 | Copilot (auto-loaded) | AGENTS.md |
| 4 | Folder AGENTS.md | `src/piloto/AGENTS.md` | L2 | L2 | auto-loaded in `src/piloto/` | — |
| 5 | Build/test reference | `docs/agents/build-and-test.md` | L2 (reference) | L2 | AGENTS.md:6 (on demand) | — |
| 6 | Release skill | `.claude/skills/release/SKILL.md` | L2 | MIXED (L1 + L2 + L3 + L4 + secret) | AGENTS.md:13, :36 | bump_version.py, publish.sh, release.yml (via tag), git, PyPI web |
| 7 | Bump script | `.claude/skills/release/scripts/bump_version.py` | L3 | L3 (+ `git commit -am`) | SKILL.md:10 (and :12 under a wrong path) | git |
| 8 | Fallback publication script | `.claude/skills/release/scripts/publish.sh` | L3 | L4 (publishes to PyPI with a token) | SKILL.md:13 | build, twine → PyPI |
| 9 | CI workflow | `.github/workflows/ci.yml` | L4 | L4 | push main, pull_request | ruff.toml, pytest (pyproject) |
| 10 | Release workflow | `.github/workflows/release.yml` | L4 | L4 | push of a `v*` tag (SKILL.md:12) | uv build, pypa/gh-action-pypi-publish |
| 11 | pre-commit | `.pre-commit-config.yaml` | L3 | L3 local, opt-in | developer (if installed) | ruff, mypy --strict |
| 12 | ruff config | `ruff.toml` | L3 | L3 | ci.yml:12, pre-commit | — |
| 13 | pyproject (version, pytest, mypy) | `pyproject.toml` | L3 | L3 | ci.yml:18 (addopts), bump_version.py, test_version_single_source | — |
| 14 | Single version test | `tests/test_version_single_source.py` | L3 | L3 | ci.yml:18 | pyproject.toml, src/ |
| 15 | net test | `tests/test_net.py` | L3 | L3 | ci.yml:18 | net.py |
| 16 | E2E push test | `tests/test_push_e2e.py` | L3 | L3 never run | nobody (deselected by pyproject.toml:17) | cli.py |
| 17 | Harvest | `.harness/harvest.json` | — (data) | — | harness-harvest | — |

Nominal release process, as told in `SKILL.md`:

| Process step | Carried by | Enforced by code? | Dry-run? |
|---|---|---|---|
| 1. `main` is green | SKILL.md:8 (prompt, reading the Actions tab) | No | — |
| 2. Choose patch / minor / major with the user | SKILL.md:9 (L1, legitimate) | — | — |
| 3. Bump the version and commit | bump_version.py (L3) | Partly: regex found or `exit`, but no clean tree, no branch, no absent tag; untested | No |
| 4. Fill in `CHANGELOG.md` and amend | SKILL.md:11 (by hand) | No | — |
| 5. Tag `v<version>` and `git push --tags` | SKILL.md:12 (git command, script path that does not exist) | No: nothing checks `tag == version` | No, no stopping point between tag and publication |
| 6. PyPI publication | release.yml (L4, OIDC) | Yes for the publication; no precondition (tests, consistency) before `publish` | No |
| 6 bis. Fallback publication from the workstation | SKILL.md:13 + publish.sh (token in clear text) | No, bypasses release.yml | No |
| 7. Check that the version shows up on pypi.org | SKILL.md:14 (web page, read by a human) | No | — |

## 3. Leaks: rules and steps told without enforcement

| Rule or step | Told in | If the agent skips it | Must live in | Target tool |
|---|---|---|---|---|
| `main` must be green before releasing | `.claude/skills/release/SKILL.md:8` | a tag on a red commit publishes to PyPI, irreversible | L4 | `verify` job in `release.yml` (ruff, mypy, pytest) before `publish` |
| The tag `v<x>` matches the version of `pyproject.toml` | `.claude/skills/release/SKILL.md:12` (and the path `scripts/bump_version.py` does not exist: `$(…)` empty → `git tag v`) | tag `v` or a tag one version off; `release.yml` publishes anyway (`v*`) | L3 + L4 | `release tag` subcommand that reads the version; `verify` step in `release.yml` comparing `${GITHUB_REF_NAME#v}` with `uv version --short` |
| `CHANGELOG.md` has a non-empty section for the published version | `AGENTS.md:20`, `SKILL.md:11`; `CHANGELOG.md:9` shows `## 1.4.0` still empty | a new "release 1.4" with an empty changelog (incident cited) | L4 | `verify` job (non-empty `## <version>` section); `changelog-touched` PR gate in `ci.yml` with an exemption label |
| Publish to PyPI only through `release.yml` | `AGENTS.md:26` — contradicted by `SKILL.md:13` and `publish.sh` | publication from a workstation, with a long-lived token, outside any audit, with no protected environment | L4 | remove `publish.sh`; on the PyPI side, trusted publisher only, no active API token; `pypi` environment with required reviewers |
| The published version is confirmed | `SKILL.md:14` (reading pypi.org) | hallucinated success if the publication failed | L3/L4 | final step of `release.yml`: `pip index versions piloto` / JSON call to `pypi.org/pypi/piloto/<v>/json` with `exit 1`; URL of the run as structured return |
| All code passes mypy in strict mode (incident #23) | `AGENTS.md:18` claims "Enforced by: mypy in `.pre-commit-config.yaml`" | the hook is local and opt-in; `ci.yml:7-18` never runs mypy: a PR without the hook goes green | L4 | `types` job in `ci.yml`: `uv run mypy src` |
| Network calls go through `piloto.net`, never `subprocess` (incident #38) | `AGENTS.md:23`; contradicted by `src/piloto/AGENTS.md:5`; broken by `src/piloto/cli.py:36` (`ssh` without a timeout) | CI or workstation blocked on an `ssh` without a timeout, like #38 | L3 | ruff `flake8-tidy-imports` `banned-api` (TID251) banning `subprocess` outside `src/piloto/net.py`, or a test mirroring `test_version_single_source.py` |
| Pushing to `main` without a PR is forbidden | `AGENTS.md:28`; `SKILL.md:10-12` creates a local commit on `main` and pushes only the tags | a tag pointing to a commit absent from `main`; `main` does not carry the bump | L4 | branch protection (not visible in the repository); the bump goes through a PR, the tag is set on the merged commit |
| The "manual tests of the release" E2E tests cover `cli.py` | `src/piloto/AGENTS.md:6`; `tests/test_push_e2e.py:8` itself says "never run in CI"; `pyproject.toml:17` deselects `slow` | `cli.py` has no test run anywhere | L4 | `e2e` job in `ci.yml` with an `sshd` service, `pytest -m slow` |

Rules **with** a guardrail (healthy part, can be shortened in `AGENTS.md`):
- ruff style (`AGENTS.md:17`) — `ruff.toml` run by `ci.yml:12` on PRs and `main`.
- Version in one place only (`AGENTS.md:19`) — `tests/test_version_single_source.py:6-14`, run by `ci.yml:18`.
- "Done when pytest passes" (`AGENTS.md:21`) — `ci.yml:18` (with the caveat that `pyproject.toml:17` excludes `slow` and stops at the first error).
- Publication through OIDC with no stored secret, in an `environment` — `release.yml:5-7, 11` (the protection rules of the environment are not visible).
- Micro-guard on the default timeout — `tests/test_net.py:4-5` bounds `DEFAULT_TIMEOUT` (does not cover the `subprocess` of `cli.py:36`).

## 3b. Context cost

| File | Lines loaded (with includes) | Share instruction / reference / noise | Loaded when |
|---|---|---|---|
| `CLAUDE.md` → `AGENTS.md` | 43 (1 + 42) | ~70 % / ~20 % / ~10 % | every Claude Code session |
| `.github/copilot-instructions.md` | 1 (pointer to AGENTS.md, not resolved automatically by Copilot) | 100 % / 0 / 0 | every Copilot session |
| `src/piloto/AGENTS.md` | 6 | 0 / 0 / 100 % (three lines that contradict the root) | work in `src/piloto/` |
| `docs/agents/build-and-test.md` | 7 | 0 / 100 % / 0 | on demand (`AGENTS.md:6`) |

The rules of `AGENTS.md` are justified: six out of seven cite a why, four an incident (#23, #31, #38, release 1.4), and the file honestly says "(unverified)" for two of them. The noise fits in two lines: `AGENTS.md:22` (docstring + annotations, no why, no guardrail — ruff `D` is not selected in `ruff.toml:3`) and the duplicate definition of "done" (`AGENTS.md:21` against `:32`, which do not say the same thing). The maintenance clause exists (`AGENTS.md:38-40`) and a harvest marker is set (`AGENTS.md:42`). Two internal inconsistencies: `AGENTS.md:13` gives a skill, not a command, as "what to run" for the release; `SKILL.md:10` and `:12` call the same script by two paths, one of which does not exist.

## 4. Findings by item

### [SPLIT] [P1] Release skill — `.claude/skills/release/SKILL.md`
- **Does today**: a sequence of seven steps that mixes judgment (choice of the kind of version, :9), procedure (:8, :11, :14), local logic (script paths, :10, :12), remote execution (`git push --tags` triggers the publication, :12) and a bypass of L4 with a PyPI token written in clear text (:13).
- **Problem**: (a) a secret in clear text in a versioned file loaded into context (`SKILL.md:13`, value not copied here); (b) `SKILL.md:13` contradicts the Forbidden item `AGENTS.md:26`; (c) precondition "main green" told (`:8`); (d) `scripts/bump_version.py --show` (`:12`) does not exist — the real path is `.claude/skills/release/scripts/bump_version.py` (`:10`) — so `git tag v$(…)` produces a tag `v` that `release.yml:4` accepts; (e) no stopping point and no dry-run between the tag and the publication; (f) unstructured final return (`:14`, reading pypi.org); (g) the release commit stays local on `main` (`:10-12` push only the tags) although `AGENTS.md:28` forbids pushing `main` without a PR: the process does not say how the bump reaches `main`.
- **Must become**: a pure-procedure SKILL.md: "`release plan <kind>` (dry-run, shows version, tag, changelog section), open the bump PR, after the merge `release tag` on the merged commit, read the URL of the `release.yml` run and its exit code". The patch/minor/major choice stays with the agent (L1). Steps 6 and 7 go away in favour of the `verify` job and the confirmation step in `release.yml`.
- **Verification criterion**: `grep -c "PYPI_TOKEN\|pypi-" .claude/skills/release/SKILL.md` returns 0; every command of the skill exists (`test -f` on every path cited); a dry run `release plan patch` runs without an agent and without writing.

### [BLOCK] [P1] Fallback publication — `.claude/skills/release/scripts/publish.sh`
- **Does today**: local build then `twine upload` with `PYPI_TOKEN` (`publish.sh:4-6`), called by `SKILL.md:13` with the token given in the command.
- **Problem**: irreversible L4 action run from a workstation, with no protected `environment`, no OIDC, no run trace; breaks `AGENTS.md:26`; the script has no legitimate caller and serves as a back door around the rule "publish only through `release.yml`" (evidence: `publish.sh:2` says so itself, "when release.yml does not go through").
- **Must become**: removed. The case "`release.yml` fails" becomes: fix, re-trigger (`workflow_dispatch` with a `tag` input and `environment: pypi` with required reviewers), never publish by hand. On the PyPI side: trusted publisher only, API tokens revoked.
- **Verification criterion**: file absent; `grep -rn twine .claude/ AGENTS.md` empty; on pypi.org, no active API token for the project (checked by a human).

### [PUSH_DOWN] [P2] Root AGENTS.md — `AGENTS.md`
- **Does today**: a short, justified file, with a maintenance clause (`:38-40`), but two incident-backed rules declared "(unverified)" (`:20` CHANGELOG, `:23` network), a rule whose announced guardrail does not run in the pipeline (`:18`, mypy in pre-commit only), a noise rule (`:22`), two definitions of "done" (`:21`, `:32`) and a "Run…" entry that names a skill and not a command (`:13`).
- **Problem**: three process leaks told (evidence: `AGENTS.md:18`, `:20`, `:23`) and a guardrail wrongly claimed (`ci.yml:7-18` does not contain mypy). The folder file `src/piloto/AGENTS.md:5-6` contradicts it and nothing prevents that.
- **Must become**: `:18` → "Enforced by: `ci.yml` job types" once the job is added; `:20` → changelog PR gate + `verify` in `release.yml`; `:23` → ruff rule TID251; `:22` removed or reduced to "ruff `D`" if it is turned on; `:21` merged into `:32`; `:13` → the release CLI command.
- **Verification criterion**: no "(unverified)" left in the file, every "Enforced by" cites a file that runs in `ci.yml` or `release.yml`; `harness status` (once `.harness/audit.json` is written) no longer lists these three rules as leaks.

### [BLOCK] [P2] Folder AGENTS.md — `src/piloto/AGENTS.md`
- **Does today**: three "conventions": `print()` for debugging (`:4`), `subprocess.run(["ssh", …])` acceptable in `cli.py` (`:5`), tests mandatory only for `net.py`, `cli.py` "covered by the manual tests of the release" (`:6`).
- **Problem**: `:5` squarely contradicts `AGENTS.md:23` (a rule born from incident #38) and legitimises `src/piloto/cli.py:36`, an `ssh` without a timeout; `:6` rests on `tests/test_push_e2e.py`, deselected by `pyproject.toml:17` and never run (`test_push_e2e.py:8`). The file is loaded exactly where the agent writes the network code: it is a licence to break the rule, not a convention.
- **Must become**: removed (or reduced to a pointer to `AGENTS.md`); the network rule becomes a ruff `banned-api` rule on `subprocess` outside `net.py`; `cli.py:36` goes through `piloto.net` (outside the harness scope, to be opened as a separate task).
- **Verification criterion**: file absent or with no contradicting rule; `ruff check .` fails on `import subprocess` in `cli.py` as long as line 36 is not migrated.

### [PUSH_DOWN] [P2] Bump script — `.claude/skills/release/scripts/bump_version.py`
- **Does today**: reads the version with a regex (`:9`, `:13`), computes the next one (`:25-31`), rewrites `pyproject.toml` and runs `git commit -am` (`:32-33`), `--show` prints the version (`:22-24`).
- **Problem**: mandatory L3 logic with no test (nothing in `tests/` imports it; mypy does not see it, `docs/agents/build-and-test.md:5` limits mypy to `src`); `git commit -am` takes along every tracked change in progress (`:33`); no check for a clean tree, a branch or an existing tag, no dry-run; the knowledge "where the version is" is duplicated with `tests/test_version_single_source.py:13-14` (two regexes); called under a path that does not exist at `SKILL.md:12`.
- **Must become**: a tested subcommand (`piloto-release` in `src/`, or `uv version --bump <kind>` + a guard script) that exposes `plan` (JSON dry-run: current version, target version, tag, changelog section present) and `bump` (fails if the tree is dirty, if not on `main`, if the tag exists, if the changelog section is missing); `tomllib` instead of the regex.
- **Verification criterion**: unit tests in `tests/` covering plan/bump/failures, run by `ci.yml`; `release plan patch` writes nothing and exits 0; `.claude/skills/release/scripts/bump_version.py` removed.

### [PUSH_DOWN] [P2] Release workflow — `.github/workflows/release.yml`
- **Does today**: on a `v*` tag (`:3-4`), build then OIDC publication in the `pypi` environment (`:5-7`, `:11`, `:15-16`). It is the right layer and the right secret mechanism.
- **Problem**: no precondition before `publish`: no tests and no lint (a tag on a red commit publishes), no `tag == version` comparison (a tag `v` or `v1.4.9` would publish 1.4.2), no changelog section; no structured confirmation at the end; no `workflow_dispatch` to replay a failed publication, which pushes towards `publish.sh`. The preconditions told in `SKILL.md:8` and `:11-12` must move down here.
- **Must become**: `verify` job (`needs` of `publish`): `uv run ruff check .`, `uv run mypy src`, `uv run pytest`, `test "${GITHUB_REF_NAME#v}" = "$(uv version --short)"`, non-empty `## <version>` section; a final step that queries `https://pypi.org/pypi/piloto/<version>/json` and fails otherwise; `workflow_dispatch` with a `tag` input (and `dry_run` that stops after `verify` + `uv build`); `environment: pypi` with required reviewers (to be confirmed on the GitHub side).
- **Verification criterion**: a tag `v9.9.9` set on a commit whose `pyproject.toml` says 1.4.2 makes `verify` fail without reaching `publish`; the run publishes the URL and the version as job outputs.

### [PUSH_DOWN] [P2] pre-commit — `.pre-commit-config.yaml`
- **Does today**: ruff and `mypy --strict` hooks (`:2-7`), to be installed by each developer.
- **Problem**: presented by `AGENTS.md:18` as the guardrail of the "mypy strict" rule (incident #23), although it is local and opt-in; `ci.yml:7-18` does not run mypy. An agent in delegation (the mode announced at `AGENTS.md:3`) does not install pre-commit: nothing in the pipeline enforces the rule.
- **Must become**: the hook stays (a useful local mirror), but the guarantee moves down into `ci.yml`: `types` job = `uv run mypy src`. The mypy config of `pyproject.toml:20-21` is already in place.
- **Verification criterion**: a PR that adds `def f(x): return x` in `src/piloto/` is red in CI without pre-commit being installed.

### [PUSH_DOWN] [P2] E2E push test — `tests/test_push_e2e.py`
- **Does today**: the only test that exercises `cli.py` (`:7-11`), marked `slow`, deselected by default (`pyproject.toml:17`), and whose comment admits that it is "never run in CI" (`:8`).
- **Problem**: dead test: no caller (neither `ci.yml`, nor `release.yml`, nor the skill runs `pytest -m slow`), yet `src/piloto/AGENTS.md:6` relies on it to exempt `cli.py` from tests. Besides, `pyproject.toml:17` sets `-x --maxfail=1`: CI stops at the first error and hides the following ones (hygiene, P3, included here).
- **Must become**: `e2e` job in `ci.yml` with an `sshd` service container and `uv run pytest -m slow`, or removal of the test with the dated comment that delegation mode requires; drop `-x --maxfail=1` from `addopts`.
- **Verification criterion**: the log of a `ci.yml` run shows "1 passed" for `test_push_against_local_sshd`, or the file no longer exists; `addopts` no longer contains `-x`.

### [KEEP] CLAUDE.md — `CLAUDE.md`
One `@AGENTS.md` line: the right way to load the instructions without duplicating.

### [KEEP] Copilot stub — `.github/copilot-instructions.md`
Pointer to `AGENTS.md` with no rule of its own; Copilot does not resolve the `@include`, but the sentence is enough to send an agent to read the right file.

### [KEEP] Build/test reference — `docs/agents/build-and-test.md`
Seven lines of commands loaded on demand, consistent with `pyproject.toml` (`slow` marker, `uv`): it is the reference in the right place, outside the permanent context.

### [KEEP] CI workflow — `.github/workflows/ci.yml`
Lint and tests on PRs and `main`, in L4: this is where the `types` and `e2e` jobs recommended above must land, without changing its structure.

### [KEEP] ruff config — `ruff.toml`
Selection `E, F, I, B` run in CI; it is also the natural home of the `banned-api` rule on `subprocess` (TID251) and, if the docstring rule is kept, of the `D` set.

### [KEEP] pyproject — `pyproject.toml`
Single source of the version (`:3`), scripts, `[tool.mypy] strict` (`:20-21`): right layer; only the `addopts` block (`:17`) needs lightening, handled with the E2E test.

### [KEEP] Single version test — `tests/test_version_single_source.py`
Real guardrail of an incident-backed rule (#31), run by `ci.yml:18`; a good model for the future network rule.

### [KEEP] net test — `tests/test_net.py`
Bounds `DEFAULT_TIMEOUT` (`:4-5`): weak but run; it does not cover the `subprocess` of `cli.py:36`, which the ruff rule will cover.

### [KEEP] Harvest — `.harness/harvest.json`
Useful data: signal S1 of 2026-10-28 (`:11-23`, "explicit timeout, never a bare ssh subprocess") did produce the rule `AGENTS.md:23` (marker `AGENTS.md:42`), but `related_rule` stayed `null`, no guardrail followed, `cli.py:36` still breaks the rule and `src/piloto/AGENTS.md:5` allows it: a signal collected without a complete follow-up. The six S5 (`:24-29`) mark rules with no incident in the PRs; the docstring rule (`:29`) is the candidate for removal.

## 5. Remediation plan

| Order | Priority | Verdict | Item | Action | Depends on | Verification | Human approval required |
|---|---|---|---|---|---|---|---|
| 1 | P1 | BLOCK | publish.sh + SKILL.md:13 | Revoke the PyPI token on pypi.org, remove `SKILL.md:13` and `.claude/skills/release/scripts/publish.sh`, check that the PyPI project has only the trusted publisher | — | `grep -rn "pypi-\|twine" .claude AGENTS.md` empty; no active token on PyPI | Yes (revocation + removal) |
| 2 | P2 | PUSH_DOWN | release.yml | Add the `verify` job (ruff, mypy, pytest, `tag == version`, changelog section) in the `needs` of `publish`, a confirmation step against PyPI's JSON API, `workflow_dispatch` (`tag`, `dry_run`); confirm the required reviewers on the `pypi` environment | 1 | inconsistent tag → run red before `publish`; job output with version and URL | Yes (changes the publication pipeline) |
| 3 | P2 | PUSH_DOWN | pre-commit-config | Add the `types` job (`uv run mypy src`) to `ci.yml`; keep the local hook | — | untyped PR red in CI without pre-commit | No |
| 4 | P2 | PUSH_DOWN | bump_version.py | Create the tested subcommand `release plan|bump|tag` (tomllib, clean tree, tag absent, changelog section, `--dry-run`) with its tests in `tests/`, then remove the script | — | tests green in `ci.yml`; `release plan patch` writes nothing; script absent | Yes for the removal |
| 5 | P2 | BLOCK | src/piloto/AGENTS.md | Remove the file (or reduce it to a pointer); add to `ruff.toml` `[lint.flake8-tidy-imports.banned-api]` on `subprocess` with a `per-file-ignores` exemption for `net.py`; open a task to migrate `cli.py:36` to `piloto.net` | — | `ruff check .` reports `cli.py:5` as long as the migration is not done; file absent | Yes (removal of instructions) |
| 6 | P2 | PUSH_DOWN | test_push_e2e.py | `e2e` job in `ci.yml` with an `sshd` service and `pytest -m slow`, or dated removal; drop `-x --maxfail=1` from `pyproject.toml:17` | 3 | CI log "1 passed" for the test, or file absent; `addopts` without `-x` | Yes if removed |
| 7 | P2 | PUSH_DOWN | AGENTS.md | `changelog` job in `ci.yml` (PR gate with an exemption label); rewrite `:13` (CLI command), `:18` (ci.yml job types), `:20` and `:23` (named guardrails), merge `:21` into `:32`, remove or reduce `:22` | 2, 3, 4, 5 | no "(unverified)" left; every "Enforced by" cites a job of `ci.yml`/`release.yml` | No |
| 8 | P1 | SPLIT | SKILL.md | Rewrite the skill as a pure procedure around `release plan` / bump PR / `release tag` / reading the run; fix every path; remove steps 6 and 7 | 1, 2, 4 | every command cited exists; dry run without an agent; no secret | No (after 1) |
| 9 | P3 | KEEP | harvest.json | Link signal S1 to the rule `AGENTS.md:23` (`related_rule`) and close it when the ruff rule exists; write `.harness/audit.json` from this report | 5 | `harness status` shows the rule as guarded | No |

## 6. What the audit could not verify

- The protection rules of the GitHub `pypi` environment (required reviewers, allowed branches/tags) and the branch protection of `main` (`AGENTS.md:28`): outside the repository, not readable here.
- On the PyPI side: whether the project has active API tokens other than the trusted publisher, and whether the token of `SKILL.md:13` is valid (not tested, value not copied).
- The git history was not consulted (instruction of the audit): impossible to say since when the token has been versioned or whether the history must be purged; to be handled in remediation 1.
- No test or workflow was run; `uv run ruff check .` probably lints `.claude/` (no exclusion in `ruff.toml`), not confirmed.
- `.harness/audit.json` does not exist: first audit, no comparison possible. The JSON below was not written into the repository (instruction "change nothing"); it is provided separately.
- `CHANGELOG.md:9` (`## 1.4.0` empty) is read as the trace of the incident cited at `AGENTS.md:20`, an unconfirmed assumption.

## 7. Machine data

See the attached JSON file (`blind-python-cli.json`), reproduced identically below.

```json
{
  "audit": {
    "process": "release of piloto (Python CLI published on PyPI)",
    "scope": "fixtures/repos/python-cli/repo/: AGENTS.md, CLAUDE.md, .github/copilot-instructions.md, src/piloto/AGENTS.md, .claude/skills/release, .github/workflows, ruff.toml, .pre-commit-config.yaml, pyproject.toml, tests/, .harness/",
    "date": "2026-11-09",
    "health_score": 2,
    "cut_the_agent_test": { "passed": false, "leaked_steps": 4 }
  },
  "elements": [
    {
      "id": "release-skill",
      "path": ".claude/skills/release/SKILL.md",
      "declared_layer": "L2",
      "actual_layer": "MIXED",
      "called_by": ["agents-md"],
      "calls": ["bump-version-script", "publish-sh", "release-yml"],
      "verdict": "SPLIT",
      "priority": "P1",
      "finding": "The skill mixes judgment, procedure, script paths (one of which does not exist), an L4 trigger through git push --tags with no stopping point, and a PyPI token in clear text that contradicts the ban on publishing outside release.yml.",
      "evidence": [".claude/skills/release/SKILL.md:8", ".claude/skills/release/SKILL.md:10", ".claude/skills/release/SKILL.md:12", ".claude/skills/release/SKILL.md:13", ".claude/skills/release/SKILL.md:14", "AGENTS.md:26", "AGENTS.md:28"],
      "target": "Pure procedure: release plan (dry-run), bump PR, release tag on the merged commit, reading the URL and the exit code of the release.yml run; steps 6 and 7 removed.",
      "check": "No occurrence of PYPI_TOKEN or pypi- in the skill; every path cited exists; release plan patch runs without an agent and without writing."
    },
    {
      "id": "publish-sh",
      "path": ".claude/skills/release/scripts/publish.sh",
      "declared_layer": "L3",
      "actual_layer": "L4",
      "called_by": ["release-skill"],
      "calls": [],
      "verdict": "BLOCK",
      "priority": "P1",
      "finding": "PyPI publication from a workstation with a long-lived token, with no protected environment and no OIDC: a back door around the rule \"publish only through release.yml\".",
      "evidence": [".claude/skills/release/scripts/publish.sh:2", ".claude/skills/release/scripts/publish.sh:4", ".claude/skills/release/scripts/publish.sh:6", "AGENTS.md:26"],
      "target": "Removed; a failure of release.yml is handled by a fix and a workflow_dispatch in the pypi environment, never by a manual publication; PyPI API tokens revoked.",
      "check": "File absent; grep twine over .claude and AGENTS.md empty; no active API token on the PyPI project."
    },
    {
      "id": "agents-md",
      "path": "AGENTS.md",
      "declared_layer": "L2",
      "actual_layer": "L2",
      "called_by": ["claude-md", "copilot-instructions"],
      "calls": ["release-skill", "docs-build-and-test", "ci-yml", "release-yml", "pre-commit-config", "test-version-single-source", "ruff-toml"],
      "verdict": "PUSH_DOWN",
      "priority": "P2",
      "finding": "Two incident-backed rules told without a guardrail (CHANGELOG, network), a claimed guardrail that does not run in the pipeline (mypy in pre-commit), a noise rule (docstring), two definitions of \"done\" and a \"Run\" entry that names a skill instead of a command.",
      "evidence": ["AGENTS.md:13", "AGENTS.md:18", "AGENTS.md:20", "AGENTS.md:21", "AGENTS.md:22", "AGENTS.md:23", "AGENTS.md:32", ".github/workflows/ci.yml:7"],
      "target": "Every \"Enforced by\" cites a job of ci.yml or release.yml: types job (mypy), changelog PR gate, ruff banned-api rule on subprocess; line 22 removed, lines 21 and 32 merged, line 13 pointing to the CLI command.",
      "check": "No \"(unverified)\" left in the file and every guardrail cited is run by ci.yml or release.yml."
    },
    {
      "id": "src-piloto-agents-md",
      "path": "src/piloto/AGENTS.md",
      "declared_layer": "L2",
      "actual_layer": "L2",
      "called_by": [],
      "calls": [],
      "verdict": "BLOCK",
      "priority": "P2",
      "finding": "The folder file allows the direct ssh subprocess that the root forbids (incident #38) and exempts cli.py from tests by relying on an E2E test that is never run; cli.py:36 already breaks the rule.",
      "evidence": ["src/piloto/AGENTS.md:5", "src/piloto/AGENTS.md:6", "AGENTS.md:23", "src/piloto/cli.py:36", "tests/test_push_e2e.py:8", "pyproject.toml:17"],
      "target": "Removed or reduced to a pointer to AGENTS.md; the network rule becomes a ruff banned-api rule (TID251) on subprocess outside net.py; cli.py:36 migrated to piloto.net as a separate task.",
      "check": "File absent or with no contradicting rule; ruff check . fails on import subprocess in cli.py as long as the migration is not done."
    },
    {
      "id": "bump-version-script",
      "path": ".claude/skills/release/scripts/bump_version.py",
      "declared_layer": "L3",
      "actual_layer": "L3",
      "called_by": ["release-skill"],
      "calls": [],
      "verdict": "PUSH_DOWN",
      "priority": "P2",
      "finding": "Mandatory L3 logic (computing and writing the version, commit) with no test, no dry-run, no check for a clean tree or an existing tag; git commit -am takes everything along; regex duplicated with test_version_single_source; called under a wrong path.",
      "evidence": [".claude/skills/release/scripts/bump_version.py:9", ".claude/skills/release/scripts/bump_version.py:13", ".claude/skills/release/scripts/bump_version.py:33", "tests/test_version_single_source.py:14", ".claude/skills/release/SKILL.md:12", "docs/agents/build-and-test.md:5"],
      "target": "Tested subcommand release plan|bump|tag (tomllib, clean tree, on main, tag absent, changelog section present, --dry-run) in src/ with tests in tests/, then removal of the script.",
      "check": "Tests of plan/bump/failures green in ci.yml; release plan patch writes nothing and exits 0; script removed."
    },
    {
      "id": "release-yml",
      "path": ".github/workflows/release.yml",
      "declared_layer": "L4",
      "actual_layer": "L4",
      "called_by": ["release-skill"],
      "calls": [],
      "verdict": "PUSH_DOWN",
      "priority": "P2",
      "finding": "Correct OIDC publication but with no precondition at all: no tests, no tag/version consistency, no changelog, no structured confirmation, no workflow_dispatch to replay; the preconditions told in SKILL.md must move down here.",
      "evidence": [".github/workflows/release.yml:4", ".github/workflows/release.yml:9", ".github/workflows/release.yml:15", ".github/workflows/release.yml:16", ".claude/skills/release/SKILL.md:8", ".claude/skills/release/SKILL.md:12"],
      "target": "A verify job (ruff, mypy, pytest, tag == pyproject version, non-empty ## <version> section) in the needs of publish; a confirmation step against PyPI's JSON API; workflow_dispatch with tag and dry_run; pypi environment with required reviewers.",
      "check": "A v9.9.9 tag on a commit at 1.4.2 makes verify fail without reaching publish; the run exposes version and URL as outputs."
    },
    {
      "id": "pre-commit-config",
      "path": ".pre-commit-config.yaml",
      "declared_layer": "L3",
      "actual_layer": "L3",
      "called_by": [],
      "calls": ["ruff-toml"],
      "verdict": "PUSH_DOWN",
      "priority": "P2",
      "finding": "Presented as the guardrail of the mypy strict rule (incident #23), the hook is local and opt-in; ci.yml never runs mypy, so nothing in the pipeline enforces the rule.",
      "evidence": [".pre-commit-config.yaml:5", ".pre-commit-config.yaml:7", "AGENTS.md:18", ".github/workflows/ci.yml:7", ".github/workflows/ci.yml:18"],
      "target": "Keep the hook, add the types job (uv run mypy src) to ci.yml.",
      "check": "An untyped PR in src/piloto/ is red in CI without pre-commit installed."
    },
    {
      "id": "test-push-e2e",
      "path": "tests/test_push_e2e.py",
      "declared_layer": "L3",
      "actual_layer": "L3",
      "called_by": [],
      "calls": [],
      "verdict": "PUSH_DOWN",
      "priority": "P2",
      "finding": "The only test of cli.py, deselected by addopts and run nowhere (not in CI, not in the release, not in the skill), although src/piloto/AGENTS.md relies on it; addopts -x --maxfail=1 also hides the failures that follow.",
      "evidence": ["tests/test_push_e2e.py:6", "tests/test_push_e2e.py:8", "pyproject.toml:17", "src/piloto/AGENTS.md:6"],
      "target": "An e2e job in ci.yml with an sshd service and pytest -m slow, or a dated removal; drop -x --maxfail=1 from addopts.",
      "check": "The CI log shows 1 passed for test_push_against_local_sshd, or the file is absent; addopts without -x."
    },
    {
      "id": "claude-md",
      "path": "CLAUDE.md",
      "declared_layer": "L2",
      "actual_layer": "L2",
      "called_by": [],
      "calls": ["agents-md"],
      "verdict": "KEEP",
      "priority": null,
      "finding": "One @AGENTS.md line, no duplication.",
      "evidence": ["CLAUDE.md:1"],
      "target": "Unchanged.",
      "check": "The file remains a single include line."
    },
    {
      "id": "copilot-instructions",
      "path": ".github/copilot-instructions.md",
      "declared_layer": "L2",
      "actual_layer": "L2",
      "called_by": [],
      "calls": ["agents-md"],
      "verdict": "KEEP",
      "priority": null,
      "finding": "Pointer to AGENTS.md with no rule of its own.",
      "evidence": [".github/copilot-instructions.md:1"],
      "target": "Unchanged.",
      "check": "No rule is added to it."
    },
    {
      "id": "docs-build-and-test",
      "path": "docs/agents/build-and-test.md",
      "declared_layer": "L2",
      "actual_layer": "L2",
      "called_by": ["agents-md"],
      "calls": [],
      "verdict": "KEEP",
      "priority": null,
      "finding": "Command reference loaded on demand, consistent with pyproject.toml.",
      "evidence": ["docs/agents/build-and-test.md:3", "docs/agents/build-and-test.md:6", "AGENTS.md:6"],
      "target": "Unchanged.",
      "check": "The commands cited still exist."
    },
    {
      "id": "ci-yml",
      "path": ".github/workflows/ci.yml",
      "declared_layer": "L4",
      "actual_layer": "L4",
      "called_by": [],
      "calls": ["ruff-toml", "pyproject-toml", "test-version-single-source", "test-net"],
      "verdict": "KEEP",
      "priority": null,
      "finding": "Lint and tests on PRs and main; the home of the types, e2e and changelog jobs recommended elsewhere.",
      "evidence": [".github/workflows/ci.yml:3", ".github/workflows/ci.yml:12", ".github/workflows/ci.yml:18"],
      "target": "Structure unchanged, jobs added by remediations 2, 3, 6, 7.",
      "check": "The lint and tests jobs remain required on PRs."
    },
    {
      "id": "ruff-toml",
      "path": "ruff.toml",
      "declared_layer": "L3",
      "actual_layer": "L3",
      "called_by": ["ci-yml", "pre-commit-config"],
      "calls": [],
      "verdict": "KEEP",
      "priority": null,
      "finding": "Selection E, F, I, B run in CI; will host the banned-api rule on subprocess.",
      "evidence": ["ruff.toml:3", ".github/workflows/ci.yml:12"],
      "target": "[lint.flake8-tidy-imports.banned-api] added by remediation 5.",
      "check": "ruff check . is still run by ci.yml."
    },
    {
      "id": "pyproject-toml",
      "path": "pyproject.toml",
      "declared_layer": "L3",
      "actual_layer": "L3",
      "called_by": ["ci-yml", "bump-version-script", "test-version-single-source"],
      "calls": [],
      "verdict": "KEEP",
      "priority": null,
      "finding": "Single source of the version and mypy strict config; only addopts needs lightening, handled with test-push-e2e.",
      "evidence": ["pyproject.toml:3", "pyproject.toml:17", "pyproject.toml:21"],
      "target": "Unchanged except addopts.",
      "check": "A single version line; [tool.mypy] strict kept."
    },
    {
      "id": "test-version-single-source",
      "path": "tests/test_version_single_source.py",
      "declared_layer": "L3",
      "actual_layer": "L3",
      "called_by": ["ci-yml"],
      "calls": ["pyproject-toml"],
      "verdict": "KEEP",
      "priority": null,
      "finding": "Real guardrail of an incident-backed rule (#31), run in CI.",
      "evidence": ["tests/test_version_single_source.py:6", "tests/test_version_single_source.py:12", ".github/workflows/ci.yml:18"],
      "target": "Unchanged; a model for the network rule.",
      "check": "Still collected by uv run pytest."
    },
    {
      "id": "test-net",
      "path": "tests/test_net.py",
      "declared_layer": "L3",
      "actual_layer": "L3",
      "called_by": ["ci-yml"],
      "calls": [],
      "verdict": "KEEP",
      "priority": null,
      "finding": "Bounds DEFAULT_TIMEOUT, run in CI; does not cover the subprocess of cli.py.",
      "evidence": ["tests/test_net.py:4", "tests/test_net.py:5"],
      "target": "Unchanged.",
      "check": "Still collected by uv run pytest."
    },
    {
      "id": "harness-harvest",
      "path": ".harness/harvest.json",
      "declared_layer": "L2",
      "actual_layer": "L2",
      "called_by": [],
      "calls": [],
      "verdict": "KEEP",
      "priority": null,
      "finding": "Signal S1 (explicit timeout, never a bare ssh subprocess) produced the rule AGENTS.md:23 but related_rule stayed null, no guardrail followed and cli.py:36 still breaks the rule; six S5 mark rules with no incident, among them the docstring rule.",
      "evidence": [".harness/harvest.json:20", ".harness/harvest.json:21", ".harness/harvest.json:29", "AGENTS.md:23", "AGENTS.md:42", "src/piloto/cli.py:36"],
      "target": "Link S1 to the rule, close it when the ruff rule exists; write .harness/audit.json from this report.",
      "check": "harness status shows the network rule as guarded."
    }
  ],
  "process_leaks": [
    { "rule": "main must be green before releasing", "told_in": ".claude/skills/release/SKILL.md:8", "if_skipped": "A tag set on a red commit publishes to PyPI, irreversible.", "belongs_in": "L4", "guard_tool": "verify job (ruff, mypy, pytest) in the needs of publish in release.yml" },
    { "rule": "The tag v<x> matches the version of pyproject.toml", "told_in": ".claude/skills/release/SKILL.md:12", "if_skipped": "The path scripts/bump_version.py does not exist: git tag v (empty) or a shifted tag; release.yml publishes anyway (v*).", "belongs_in": "L4", "guard_tool": "verify step in release.yml comparing GITHUB_REF_NAME with the pyproject version; release tag subcommand" },
    { "rule": "CHANGELOG.md has a non-empty section for the published version", "told_in": "AGENTS.md:20", "if_skipped": "A new release with an empty changelog, like 1.4 (CHANGELOG.md:9 still empty).", "belongs_in": "L4", "guard_tool": "verify job in release.yml (non-empty ## <version> section) and changelog PR gate in ci.yml with an exemption label" },
    { "rule": "Publish to PyPI only through release.yml on a tag", "told_in": "AGENTS.md:26", "if_skipped": "SKILL.md:13 and publish.sh publish from a workstation with a long-lived token, outside any audit and outside the protected environment.", "belongs_in": "L4", "guard_tool": "removal of publish.sh; trusted publisher only on the PyPI side; pypi environment with required reviewers" },
    { "rule": "The published version is confirmed on PyPI", "told_in": ".claude/skills/release/SKILL.md:14", "if_skipped": "Hallucinated success if the publication failed: a human reading a web page.", "belongs_in": "L4", "guard_tool": "final step of release.yml querying https://pypi.org/pypi/piloto/<version>/json with exit 1" },
    { "rule": "All code is typed and passes mypy in strict mode", "told_in": "AGENTS.md:18", "if_skipped": "The pre-commit hook is local and opt-in; ci.yml does not run mypy: an untyped PR goes green (incident #23 reproducible).", "belongs_in": "L4", "guard_tool": "types job (uv run mypy src) in ci.yml" },
    { "rule": "Network calls go through piloto.net, never through a direct subprocess", "told_in": "AGENTS.md:23", "if_skipped": "ssh without a timeout blocks CI or the workstation (#38); cli.py:36 already does it and src/piloto/AGENTS.md:5 allows it.", "belongs_in": "L3", "guard_tool": "ruff flake8-tidy-imports banned-api (TID251) on subprocess with per-file-ignores for src/piloto/net.py, or a test mirroring test_version_single_source.py" },
    { "rule": "Pushing to main without a PR is forbidden; the release commit must reach main", "told_in": "AGENTS.md:28", "if_skipped": "SKILL.md:10-12 commits locally on main and pushes only the tags: a tag on a commit absent from main, main without the bump.", "belongs_in": "L4", "guard_tool": "branch protection on main; bump through a PR; tag set on the merged commit by release tag" },
    { "rule": "cli.py is covered by the E2E tests of the release", "told_in": "src/piloto/AGENTS.md:6", "if_skipped": "tests/test_push_e2e.py is deselected by pyproject.toml:17 and run nowhere: cli.py has no test.", "belongs_in": "L4", "guard_tool": "e2e job in ci.yml with an sshd service and pytest -m slow" }
  ],
  "guarded_rules": [
    { "rule": "Style follows ruff", "told_in": "AGENTS.md:17", "guarded_by": "ruff.toml via .github/workflows/ci.yml:12" },
    { "rule": "The version exists in one place only, pyproject.toml", "told_in": "AGENTS.md:19", "guarded_by": "tests/test_version_single_source.py via .github/workflows/ci.yml:18" },
    { "rule": "A task is done when pytest passes", "told_in": "AGENTS.md:21", "guarded_by": ".github/workflows/ci.yml:18 (with -k 'not slow' and -x from pyproject.toml:17)" },
    { "rule": "Publication goes through OIDC in an environment, with no stored secret", "told_in": "AGENTS.md:26", "guarded_by": ".github/workflows/release.yml:5-7,11 (protection rules of the environment not visible)" },
    { "rule": "The default network timeout is bounded", "told_in": "src/piloto/net.py:1", "guarded_by": "tests/test_net.py:4-5 via .github/workflows/ci.yml:18" }
  ],
  "instruction_files": [
    { "path": "AGENTS.md", "loaded_lines": 43, "instruction_pct": 70, "reference_pct": 20, "noise_pct": 10, "justified_rules": true, "maintenance_clause": true },
    { "path": "CLAUDE.md", "loaded_lines": 43, "instruction_pct": 100, "reference_pct": 0, "noise_pct": 0, "justified_rules": true, "maintenance_clause": true },
    { "path": ".github/copilot-instructions.md", "loaded_lines": 1, "instruction_pct": 100, "reference_pct": 0, "noise_pct": 0, "justified_rules": false, "maintenance_clause": false },
    { "path": "src/piloto/AGENTS.md", "loaded_lines": 6, "instruction_pct": 0, "reference_pct": 0, "noise_pct": 100, "justified_rules": false, "maintenance_clause": false },
    { "path": "docs/agents/build-and-test.md", "loaded_lines": 7, "instruction_pct": 0, "reference_pct": 100, "noise_pct": 0, "justified_rules": false, "maintenance_clause": false }
  ],
  "remediation": [
    { "order": 1, "priority": "P1", "verdict": "BLOCK", "element": "publish-sh", "action": "Revoke the PyPI token on pypi.org, remove line 13 of SKILL.md and .claude/skills/release/scripts/publish.sh, check that the PyPI project has only the trusted publisher.", "depends_on": [], "check": "grep of pypi- and twine over .claude and AGENTS.md empty; no active API token on PyPI.", "needs_human_approval": true },
    { "order": 2, "priority": "P2", "verdict": "PUSH_DOWN", "element": "release-yml", "action": "Add the verify job (ruff, mypy, pytest, tag == version, changelog section) in the needs of publish, a confirmation step against PyPI's JSON API, workflow_dispatch with tag and dry_run; confirm the required reviewers on the pypi environment.", "depends_on": [1], "check": "An inconsistent tag turns the run red before publish; the job output carries version and URL.", "needs_human_approval": true },
    { "order": 3, "priority": "P2", "verdict": "PUSH_DOWN", "element": "pre-commit-config", "action": "Add the types job (uv run mypy src) to ci.yml while keeping the local hook.", "depends_on": [], "check": "An untyped PR is red in CI without pre-commit installed.", "needs_human_approval": false },
    { "order": 4, "priority": "P2", "verdict": "PUSH_DOWN", "element": "bump-version-script", "action": "Create the tested subcommand release plan|bump|tag (tomllib, clean tree, tag absent, changelog section, --dry-run) with its tests in tests/, then remove the script.", "depends_on": [], "check": "Tests green in ci.yml; release plan patch writes nothing; script absent.", "needs_human_approval": true },
    { "order": 5, "priority": "P2", "verdict": "BLOCK", "element": "src-piloto-agents-md", "action": "Remove the file or reduce it to a pointer; add to ruff.toml the banned-api rule on subprocess with an exemption for net.py; open a task to migrate cli.py:36 to piloto.net.", "depends_on": [], "check": "ruff check . reports cli.py:5 as long as the migration is not done; file absent.", "needs_human_approval": true },
    { "order": 6, "priority": "P2", "verdict": "PUSH_DOWN", "element": "test-push-e2e", "action": "Add the e2e job to ci.yml with an sshd service and pytest -m slow, or remove the test with a dated comment; drop -x --maxfail=1 from pyproject.toml.", "depends_on": [3], "check": "CI log with 1 passed for the test, or file absent; addopts without -x.", "needs_human_approval": true },
    { "order": 7, "priority": "P2", "verdict": "PUSH_DOWN", "element": "agents-md", "action": "Add the changelog job (PR gate with an exemption label) to ci.yml; rewrite lines 13, 18, 20, 23, merge 21 into 32, remove or reduce 22.", "depends_on": [2, 3, 4, 5], "check": "No \"(unverified)\" left; every \"Enforced by\" cites a job of ci.yml or release.yml.", "needs_human_approval": false },
    { "order": 8, "priority": "P1", "verdict": "SPLIT", "element": "release-skill", "action": "Rewrite the skill as a pure procedure around release plan, bump PR, release tag and reading the run; fix every path; remove steps 6 and 7.", "depends_on": [1, 2, 4], "check": "Every command cited exists; dry run without an agent; no secret.", "needs_human_approval": false },
    { "order": 9, "priority": "P3", "verdict": "KEEP", "element": "harness-harvest", "action": "Link signal S1 to the rule AGENTS.md:23 and close it when the ruff rule exists; write .harness/audit.json from this report.", "depends_on": [5], "check": "harness status shows the network rule as guarded.", "needs_human_approval": false }
  ],
  "unverified": [
    "Protection rules of the GitHub pypi environment (required reviewers) and branch protection of main: outside the repository.",
    "On the PyPI side: existence of other active API tokens and validity of the token written at .claude/skills/release/SKILL.md:13 (value not copied, not tested).",
    "Git history not consulted: how long the token has been in the history and whether a purge is needed are not established.",
    "No test or workflow run; uv run ruff check . probably lints .claude/ (no exclusion in ruff.toml), not confirmed.",
    ".harness/audit.json absent: first audit, no comparison; the JSON was not written into the repository (instruction to change nothing).",
    "CHANGELOG.md:9 (## 1.4.0 empty) read as the trace of the incident cited at AGENTS.md:20, an unconfirmed assumption."
  ]
}
```
