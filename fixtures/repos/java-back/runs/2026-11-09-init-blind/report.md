# Report — harness-init on billing-api

**Repository**: `init-eval/repo` (branch `develop`, commit `a7b8f90`) · **Date**: 2026-11-09 · **Mode chosen**: delegation

## Level reached according to `harness status`

**Level 1 — Framed: 5/5, complete.** Next: level 2.

Remaining checks:
- Level 2 (3/4): a harvest that finds a real signal (S1–S4) is missing; the loop is not running yet, harness-harvest is not installed, the collection of the `rule:` comments is manual.
- Level 3 (2/4): 17 % of the rules "Enforced by" (target 50 %); the audit has three open P1s.
- Level 4 (3/5): no harvest; the audit's "cut the agent" test fails (5 steps of the release exist only in prompts).

## Files created or modified

| File | Lines | Role |
|---|---|---|
| `AGENTS.md` | 44 | single source, delegation mode, 3 rules, 3 forbidden items, process, contract referenced, maintenance, harvest marker |
| `CLAUDE.md` | 1 | `@AGENTS.md` stub |
| `.claude/skills/release/SKILL.md` | 45 | first task contract: release / hotfix via `release.yml` |
| `.harness/state.json` | 345 | written by `harness status` |
| `.harness/audit.json` | 201 | machine output of the harness-audit (gate) |

No Copilot or Cursor stub: the team uses Claude Code only. No pre-existing instruction file, nothing was overwritten.

## Secrets found

No secret in clear text. The two occurrences (`release.yml:25`, `:30`) are references `${{ secrets.REGISTRY_PASSWORD }}` and `${{ secrets.PROD_SSH_KEY }}`, correctly kept in L4. Nothing to regenerate or purge.

## Mode chosen and why

**Delegation**, chosen by the owner (agents will open whole PRs) and consistent with the team (3 developers plus agents: the file serves everyone, not one person's memory). Consequence: the "Working process" section is mandatory, a contract exists from the first task, and each rule told without a guardrail is a P1 debt for the audit.

## Rules written and status

| Rule | Status |
|---|---|
| A controller never depends on a repository; business logic lives in the services | **enforced by** `src/test/java/com/acme/billing/ArchitectureTest.java` (`controllers_do_not_touch_repositories`), run by `ci.yml` |
| An applied Flyway migration is never modified; a `V<n+1>__*.sql` is added | **unverified**; target: checksum test of the migrations in `ci.yml` |
| A release or a hotfix goes through `release.yml` according to the `release` contract, never through `old-deploy.sh` nor `docker`/`ssh` by hand | **unverified**; target: removal of `old-deploy.sh`, `deploy` job under `environment: production` |

Forbidden items (from the owner, taken as they are): triggering `release.yml` or any prod deployment without explicit human validation; modifying an applied Flyway migration; pushing directly to `main`. None of the three has a guardrail today (no protected `environment`, no checksum test, branch protection not verifiable without a remote).

Assumptions taken without asking: a PR targets `develop` unless explicitly asked otherwise (inferred from the Forbidden item "no push to main" and from the scripts that release from `develop`); the "why" of the ArchUnit rule comes from the comment of the test ("no business logic in controllers").

## Commands confirmed and not confirmed

Confirmed (run here):
- `python3 harness.py status . --today 2026-11-09` → level 1, 5/5.
- `node --check scripts/release.mjs`, `node --check scripts/hotfix.mjs`, `bash -n scripts/old-deploy.sh` → valid syntax (no real run: they would trigger `release.yml`).

Not confirmed (no Gradle toolchain available; copied from `ci.yml`, and so kept in the table of AGENTS.md as "what CI runs"):
- `./gradlew checkstyleMain checkstyleTest`, `./gradlew test`. Number of tests unknown.
- Besides, **no `gradlew` nor `gradle/wrapper/` is versioned** on `develop`: if that is the state of the remote, `ci.yml:13-14` and `release.yml:23` fail at the first step. Same for the **`Dockerfile`**, absent although `release.yml:24` runs `docker build .`. To be confirmed before any release.

## Result of the gate (harness-audit)

Health score **0/100** (3 P1, 4 P2, 1 P3; "cut the agent" test failed, cap of 60). Full report in the appendix, JSON in `.harness/audit.json`.

Structural findings fixed during the init: the two `(unverified)` rules now name their target guardrail (a requirement of delegation mode). Length (44 lines), share of reference (~25 %), maintenance clause, consistent stub: compliant.

Substantive findings, not fixed here (they require creating code or a CI check):
1. **P1 `release.yml`**: a single job publishes and deploys to prod, with no protected `environment`, no `dry_run`, tag set after the publication, `hotfix` input ignored, end signalled by `echo SUCCESS`.
2. **P1 `scripts/old-deploy.sh`**: dead and dangerous, deploys to prod over direct ssh, bypassing Forbidden item no. 1.
3. **P1 `.claude/skills/release/SKILL.md`**: the preconditions (CI green, tag absent, increasing version, migrations not modified) are told, not imposed by code.
4. P2: `release.mjs` infers the kind of version from the branch name (a plausible cause of the release errors); `hotfix.mjs` duplicates it; Gradle wrapper absent; no guard on the Flyway migrations.
5. P3: the comment of `ArchitectureTest` points to "CLAUDE.md, Conventions", which does not exist.

Point to watch: `release.yml` is a `workflow_dispatch`, GitHub only accepts it from the default branch. Any guardrail set on it (or any scheduled job) merged into `develop` alone is inert; it must also reach `main`.

## Three next steps

1. **Push the first unverified rule into CI**: split `release.yml` into `build-publish` then `deploy` under `environment: production` with required reviewers, add `dry_run`, remove `scripts/old-deploy.sh` (owner's approval: removal and workflow change), and merge all the way to `main`. Forbidden item no. 1 becomes "Enforced by".
2. Rewrite `scripts/release.mjs` as `release plan <version> --ref <ref> [--hotfix]` / `release run`: the version is an argument decided by the human, the four preconditions exit with `exit 1`, the plan is JSON; remove `hotfix.mjs`; the `release` skill keeps only the sequence and the validation.
3. Version the Gradle wrapper (or `gradle/actions/setup-gradle`) so that `ci.yml` really runs, then add a checksum test of the Flyway migrations and turn on branch protection on `main`: the two other Forbidden items become enforced and level 3 comes within reach.

---

# Appendix — Harness audit — Release of billing-api and AI instrumentation

**Scope**: billing-api repo (`develop` branch): `AGENTS.md`, `CLAUDE.md`, `.claude/skills/release`, `scripts/`, `.github/workflows/`, `config/checkstyle`, ArchUnit test, Flyway migrations · **Date**: 2026-11-09 · **Items inventoried**: 11

## 1. Summary

- **Health score**: 0 — the agent is a pillar: without it, nobody checks anything before a prod deployment goes out (100 − 3×25 − 4×8 − 1×2 < 0, floored at 0; the "cut the agent" test caps at 60 anyway).
- **Result of the "cut the agent" test**: FAILED — 5 step(s) of the process exist only in prompts (deciding the version, checking CI green / tag absent / increasing version, human validation before deployment, verification of prod, updating `VERSION`).
- **Blocking points (P1)**: 3
- **The three actions that change the most**:
  1. Split `release.yml` and put the `deploy` job under `environment: production` with required reviewers, with `dry_run`.
  2. Remove `scripts/old-deploy.sh`.
  3. Move the release preconditions into `release plan` (exit 1) instead of the SKILL.md.

## 2. Map of the harness

| # | Item | Path | Declared layer | Actual layer | Called by | Calls |
|---|---|---|---|---|---|---|
| 1 | AGENTS.md | `AGENTS.md` | L2 | L2 | CLAUDE.md | release skill, ci.yml, ArchitectureTest |
| 2 | CLAUDE.md | `CLAUDE.md` | L2 | L2 | — (loaded by Claude Code) | AGENTS.md |
| 3 | Release contract | `.claude/skills/release/SKILL.md` | L2 | MIXED (procedure + preconditions told) | AGENTS.md | release.yml |
| 4 | Release workflow | `.github/workflows/release.yml` | L4 | L4 | release skill, release.mjs, hotfix.mjs | — |
| 5 | Old deployment | `scripts/old-deploy.sh` | L3 | L4 (deploys to prod) | nobody | — |
| 6 | release.mjs | `scripts/release.mjs` | L3 | MIXED (judgment + L4 trigger) | nobody (manual) | release.yml |
| 7 | hotfix.mjs | `scripts/hotfix.mjs` | L3 | L3 | nobody (manual) | release.yml |
| 8 | CI workflow | `.github/workflows/ci.yml` | L4 | L4 | AGENTS.md | checkstyle, tests |
| 9 | Checkstyle | `config/checkstyle/checkstyle.xml` | L3 | L3 | ci.yml | — |
| 10 | ArchUnit | `src/test/java/com/acme/billing/ArchitectureTest.java` | L3 | L3 | ci.yml | — |
| 11 | Flyway migrations | `src/main/resources/db/migration/` | L3 | L3 | — (no guardrail) | — |

Nominal process: the release.

| Process step | Carried by | Enforced by code? | Dry-run? |
|---|---|---|---|
| Decide the version x.y.z | human, via SKILL.md §1 (release.mjs wrongly infers it from the branch) | no | — |
| Check CI green on the ref | SKILL.md §2 | no | — |
| Check that the tag v<x.y.z> does not exist | SKILL.md §2 | no | — |
| Check increasing version / migrations not modified | SKILL.md §2 | no | — |
| Human validation before the prod deployment | SKILL.md §3, Forbidden item of AGENTS.md | no (no protected `environment`) | no |
| Build jar + image + push | release.yml:23-26 | yes | no |
| Tag v<x.y.z> | release.yml:27 | yes (but after the publication) | no |
| Prod deployment | release.yml:28-32 | yes | no |
| Verify prod | SKILL.md §5; `echo SUCCESS` | no (unstructured return) | — |
| Update VERSION on develop | SKILL.md §6 | no | — |

## 3. Leaks: rules and steps told without enforcement

- **Release preconditions** (CI green, tag absent, increasing version, migrations not modified) — told in `.claude/skills/release/SKILL.md:15-19`. If skipped: a version already published or a commit with red CI goes to production. Must live in L3: subcommand `release plan` with `exit 1` (rewrite of `scripts/release.mjs`).
- **Human validation before any prod deployment** — `AGENTS.md:22`, `SKILL.md:22`. If skipped: an agent deploys to prod with a single `gh workflow run`. Must live in L4: `deploy` job under `environment: production` with required reviewers.
- **An applied Flyway migration is never modified** — `AGENTS.md:18`, `AGENTS.md:23`. If skipped: Flyway refuses the checksum, the application no longer restarts. Must live in L3: checksum test of the migrations or `flyway validate` in `ci.yml`.
- **No direct push to main** — `AGENTS.md:24`. If skipped: unreviewed code in prod. Must live in L4: GitHub branch protection (cannot be verified here, no remote).
- **VERSION updated after each release** — `SKILL.md:36`. If skipped: the next release computes from a stale version. Must live in L4: step of `release.yml`.

Rules that have their guardrail:
- A controller never depends on a repository — `AGENTS.md:17` — `ArchitectureTest.controllers_do_not_touch_repositories`, run by `ci.yml`.
- Java style (120 columns, imports, one class per file, naming) — not told, on purpose — `config/checkstyle/checkstyle.xml` via `ci.yml:13`.

## 3b. Context cost

| File | Lines loaded (with includes) | Share instruction / reference / noise | Loaded when |
|---|---|---|---|
| `AGENTS.md` | 44 | 75 % / 25 % / 0 % | every session |
| `CLAUDE.md` | 44 (stub → AGENTS.md) | 0 / 100 / 0 | every session |
| `.claude/skills/release/SKILL.md` | 45 | 85 % / 15 % / 0 % | on demand (release task) |

The three rules of AGENTS.md say why (one cites the Flyway mechanism, one the incident "we often get it wrong", one testability); the maintenance clause is present with the `rule:` convention and the harvest marker.

## 4. Findings by item

### [SPLIT] [P1] Release workflow — `.github/workflows/release.yml`
- **Does today**: a `build-and-deploy` job builds, publishes the image, tags, then deploys to prod over ssh.
- **Problem**: no protected `environment` and no human stopping point, no `dry_run` input, tag set after the publication (`:27`), `hotfix` input never read (`:11-14`), end signalled by `echo SUCCESS` (`:32`). (evidence: `release.yml:16-32`)
- **Must become**: jobs `build-publish` then `deploy` under `environment: production` with required reviewers; `dry_run` input; job outputs (tag, digest, URL); `hotfix` input consumed or removed.
- **Verification criterion**: a run stops waiting for approval before `deploy`; `dry_run=true` pushes no image; `gh run view --json jobs` shows two jobs.

### [BLOCK] [P1] Old deployment — `scripts/old-deploy.sh`
- **Does today**: direct build, push and `ssh deploy@prod.acme.io … docker compose up -d`.
- **Problem**: dead ("no longer called anywhere", `:2`) and bypasses tag, trace and validation: breaks Forbidden item no. 1. (evidence: `scripts/old-deploy.sh:5-7`)
- **Must become**: removed.
- **Verification criterion**: file absent; no `ssh deploy@prod.acme.io` outside `release.yml`.

### [PUSH_DOWN] [P1] Release contract — `.claude/skills/release/SKILL.md`
- **Does today**: describes the sequence, the validation and four preconditions to check by hand with `gh` and `git`.
- **Problem**: preconditions told in L2; the agent can skip them or misread a JSON of `gh run list`. (evidence: `SKILL.md:15-19`, `:25-29`)
- **Must become**: `release plan <version> --ref <ref> [--hotfix]` that checks and exits 1, plan as JSON; `release run` after a valid plan; the skill keeps only sequence and validation.
- **Verification criterion**: `release plan` exits 1 on a ref with red CI or an existing tag; the skill no longer contains a check to interpret.

### [PROMOTE] [P2] release.mjs — `scripts/release.mjs`
- **Does today**: infers the next version from the branch name then runs `gh workflow run release.yml`.
- **Problem**: hardcoded judgment (`develop` → minor, `feat/breaking-*` → major, `:11-17`), a plausible cause of the release errors; no precondition before the trigger (`:23`).
- **Must become**: version as a mandatory argument decided by the human; becomes the base of `release plan|run`.
- **Verification criterion**: without a version argument, exit 1 with a message.

### [MERGE] [P2] hotfix.mjs — `scripts/hotfix.mjs`
- **Does today**: same mechanics as release.mjs, patch increment, `hotfix=true` flag.
- **Problem**: duplication (`:2`, `:11-16`) and flag ignored by the workflow.
- **Must become**: `release run --hotfix`.
- **Verification criterion**: file absent; `release run --hotfix` from `hotfix/*` triggers the workflow.

### [KEEP] [P2] CI workflow — `.github/workflows/ci.yml`
- **Does today**: Checkstyle and tests on PRs, `develop`, `main`.
- **Problem**: calls `./gradlew` (`:13-14`) although no wrapper is versioned; if that is the state of the remote, every run fails at the first step.
- **Must become**: wrapper versioned or `gradle/actions/setup-gradle`; a check of the migrations added.
- **Verification criterion**: `git ls-files gradlew gradle/wrapper/gradle-wrapper.properties` returns two files; a green run on `develop`.

### [PUSH_DOWN] [P2] Flyway migrations — `src/main/resources/db/migration/`
- **Does today**: one migration `V1__init.sql`, no guardrail.
- **Problem**: the rule and the Forbidden item hold only through text (`AGENTS.md:18`, `:23`).
- **Must become**: checksum test of the versioned migrations (or `flyway validate`) in `ci.yml`.
- **Verification criterion**: changing one character of `V1__init.sql` makes `ci.yml` fail.

### [KEEP] [P3] ArchUnit — `src/test/java/com/acme/billing/ArchitectureTest.java`
- **Does today**: healthy guardrail of "a controller does not depend on a repository".
- **Problem**: the comment (`:12`) points to "CLAUDE.md, Conventions", which does not exist.
- **Must become**: point to AGENTS.md, Rules section.
- **Verification criterion**: `grep CLAUDE.md` on the test returns nothing.

### [KEEP] AGENTS.md — `AGENTS.md`
44 lines, explicit mode, justified rules, Forbidden, Process, Maintenance; the two told rules name their target guardrail.

### [KEEP] CLAUDE.md — `CLAUDE.md`
`@AGENTS.md` stub, single source respected.

### [KEEP] Checkstyle — `config/checkstyle/checkstyle.xml`
Four style rules carried by the tool, nothing to tell in AGENTS.md.

## 5. Remediation plan

| Order | Priority | Verdict | Item | Action | Depends on | Verification | Human approval required |
|---|---|---|---|---|---|---|---|
| 1 | P1 | SPLIT | release.yml | Split build-publish / deploy, `environment: production` with reviewers, `dry_run`, job outputs; merge all the way to `main` | — | Run waiting for approval before deploy; dry_run pushes nothing | yes |
| 2 | P1 | BLOCK | old-deploy.sh | Remove | — | File absent | yes |
| 3 | P1 | PUSH_DOWN | release skill | `release plan|run` with preconditions as exit 1; skill reduced to the sequence | — | `release plan` exits 1 on red CI / existing tag | no |
| 4 | P2 | PROMOTE | release.mjs | Version as an argument, no more inference from the branch | 3 | Without a version, exit 1 | no |
| 5 | P2 | MERGE | hotfix.mjs | Remove, replaced by `release run --hotfix` | 3 | File absent | yes |
| 6 | P2 | KEEP | ci.yml | Version the Gradle wrapper | — | Green run on develop | no |
| 7 | P2 | PUSH_DOWN | Flyway migrations | Checksum test / `flyway validate` in ci.yml; shorten the rule | 6 | Modifying V1 breaks CI | no |
| 8 | P2 | PUSH_DOWN | AGENTS.md (Forbidden item main) | Branch protection on `main` | — | `gh api …/branches/main/protection` | yes |
| 9 | P3 | KEEP | ArchitectureTest | Fix the comment | — | grep empty | no |

## 6. What the audit could not verify

- The Gradle commands (`./gradlew checkstyleMain checkstyleTest`, `./gradlew test`): no toolchain; copied from `ci.yml`.
- Absence of `gradlew` / `gradle/wrapper/` and of a `Dockerfile`: observed locally, to be confirmed on the remote.
- Protection of the `main` branch and default branch: no remote; `workflow_dispatch` is only accepted from the default branch.
- Health endpoint of production: unknown.
- Number of tests run by `ci.yml`: unknown.
- Node scripts: syntax only (`node --check`), no real run.

## 7. Machine data

The JSON block is written as is into `repo/.harness/audit.json` (201 lines); reproduced below.

```json
{
  "audit": {
    "process": "Release of billing-api and AI instrumentation (harness-init)",
    "scope": "billing-api repo (develop branch): AGENTS.md, CLAUDE.md, .claude/skills/release, scripts/, .github/workflows/, config/checkstyle, src/test ArchUnit, Flyway migrations",
    "date": "2026-11-09",
    "health_score": 0,
    "cut_the_agent_test": { "passed": false, "leaked_steps": 5 }
  },
  "elements": [
    {
      "id": "agents-md",
      "path": "AGENTS.md",
      "declared_layer": "L2",
      "actual_layer": "L2",
      "called_by": ["claude-md"],
      "calls": ["skill-release", "ci-yml", "archunit-test"],
      "verdict": "KEEP",
      "priority": null,
      "finding": "44 lines, explicit mode, three justified rules of which one is enforced, Forbidden, Process, Maintenance; two told rules marked (unverified).",
      "evidence": ["AGENTS.md:3", "AGENTS.md:17-19", "AGENTS.md:37-42"],
      "target": "Stay under 60 lines; each (unverified) rule gets its guardrail then is shortened.",
      "check": "harness status: L1 5/5, L2.maintenance and L2.rule_convention true."
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
      "finding": "One-line @AGENTS.md stub: single source respected.",
      "evidence": ["CLAUDE.md:1"],
      "target": "Unchanged.",
      "check": "harness status: L1.single_source true."
    },
    {
      "id": "skill-release",
      "path": ".claude/skills/release/SKILL.md",
      "declared_layer": "L2",
      "actual_layer": "MIXED",
      "called_by": ["agents-md"],
      "calls": ["release-yml"],
      "verdict": "PUSH_DOWN",
      "priority": "P1",
      "finding": "The release preconditions (CI green on the ref, tag absent, increasing version, migrations not modified) are told in the skill; no code imposes them before `gh workflow run`.",
      "evidence": [".claude/skills/release/SKILL.md:15-19", ".claude/skills/release/SKILL.md:25-29"],
      "target": "A subcommand `release plan <version> --ref <ref>` (rewrite of scripts/release.mjs) that checks the four preconditions with exit 1 and prints the plan as JSON; `release run` only runs after a valid plan. The skill keeps only the sequence and the request for validation.",
      "check": "From a branch with red CI or with an existing tag, `release plan` exits 1 without triggering anything; the skill no longer contains a `gh run list`/`git ls-remote` command to interpret."
    },
    {
      "id": "release-yml",
      "path": ".github/workflows/release.yml",
      "declared_layer": "L4",
      "actual_layer": "L4",
      "called_by": ["skill-release", "script-release-mjs", "script-hotfix-mjs"],
      "calls": [],
      "verdict": "SPLIT",
      "priority": "P1",
      "finding": "A single job builds, publishes, tags and deploys to production: no protected `environment`, no human stopping point, no dry_run input, the tag is set after the image is published, the `hotfix` input is read by no step, and the end of the job is signalled by `echo SUCCESS` (unstructured).",
      "evidence": [".github/workflows/release.yml:16-32", ".github/workflows/release.yml:11-14", ".github/workflows/release.yml:27", ".github/workflows/release.yml:32"],
      "target": "Two jobs: `build-publish` (jar, image, tag) then `deploy` under `environment: production` with required reviewers; a `dry_run` input that stops after the plan; job outputs (tag, image digest, URL) instead of `echo SUCCESS`; remove or consume the `hotfix` input.",
      "check": "A `gh workflow run release.yml` stops waiting for approval before the deploy job; with `dry_run=true` no image is pushed; `gh run view --json jobs` shows both jobs."
    },
    {
      "id": "script-old-deploy",
      "path": "scripts/old-deploy.sh",
      "declared_layer": "L3",
      "actual_layer": "L4",
      "called_by": [],
      "calls": [],
      "verdict": "BLOCK",
      "priority": "P1",
      "finding": "Dead script (\"no longer called anywhere\") that deploys to production over direct ssh with no tag, no trace and no validation: bypasses Forbidden item no. 1 of AGENTS.md.",
      "evidence": ["scripts/old-deploy.sh:2", "scripts/old-deploy.sh:5-7"],
      "target": "Remove the file.",
      "check": "`ls scripts/old-deploy.sh` fails; no other file contains `ssh deploy@prod.acme.io` outside release.yml."
    },
    {
      "id": "script-release-mjs",
      "path": "scripts/release.mjs",
      "declared_layer": "L3",
      "actual_layer": "MIXED",
      "called_by": [],
      "calls": ["release-yml"],
      "verdict": "PROMOTE",
      "priority": "P2",
      "finding": "Infers the kind of version from the branch name (develop → minor, feat/breaking-* → major): hardcoded judgment, a plausible cause of the release errors reported by the team; checks no precondition (CI, tag, VERSION) before triggering the workflow.",
      "evidence": ["scripts/release.mjs:11-17", "scripts/release.mjs:23"],
      "target": "The version becomes a mandatory argument decided by the human; the script becomes `release plan|run` and carries the preconditions (see skill-release).",
      "check": "`node scripts/release.mjs` without a version argument exits 1 with an explicit message."
    },
    {
      "id": "script-hotfix-mjs",
      "path": "scripts/hotfix.mjs",
      "declared_layer": "L3",
      "actual_layer": "L3",
      "called_by": [],
      "calls": ["release-yml"],
      "verdict": "MERGE",
      "priority": "P2",
      "finding": "Same mechanics as release.mjs (reading VERSION, computation, `gh workflow run`) duplicated with a variation of increment and a `hotfix=true` flag that the workflow ignores.",
      "evidence": ["scripts/hotfix.mjs:2", "scripts/hotfix.mjs:11-16"],
      "target": "Absorbed by `release plan|run --hotfix`.",
      "check": "The file no longer exists; `release run --hotfix` from `hotfix/*` triggers the workflow with the right inputs."
    },
    {
      "id": "ci-yml",
      "path": ".github/workflows/ci.yml",
      "declared_layer": "L4",
      "actual_layer": "L4",
      "called_by": ["agents-md"],
      "calls": ["checkstyle", "archunit-test"],
      "verdict": "KEEP",
      "priority": "P2",
      "finding": "Checkstyle and tests on PRs, develop and main: right layer. But `./gradlew` is called although no wrapper (gradlew, gradle/wrapper/) is versioned: if that is the real state of the repository, every run fails at the first step and nothing is verified.",
      "evidence": [".github/workflows/ci.yml:13-14", "build.gradle:1"],
      "target": "Version the wrapper (`gradle wrapper`) or replace it with `gradle/actions/setup-gradle`; add a `flyway validate` job or a checksum test of the migrations.",
      "check": "`git ls-files gradlew gradle/wrapper/gradle-wrapper.properties` returns two files; a green ci.yml run exists on develop."
    },
    {
      "id": "checkstyle",
      "path": "config/checkstyle/checkstyle.xml",
      "declared_layer": "L3",
      "actual_layer": "L3",
      "called_by": ["ci-yml"],
      "calls": [],
      "verdict": "KEEP",
      "priority": null,
      "finding": "Four style rules (120 columns, no star import, one class per file, naming) carried by the tool: none needs to be told in AGENTS.md.",
      "evidence": ["config/checkstyle/checkstyle.xml:4-10", "build.gradle:24-27"],
      "target": "Unchanged.",
      "check": "`./gradlew checkstyleMain checkstyleTest` green in CI."
    },
    {
      "id": "archunit-test",
      "path": "src/test/java/com/acme/billing/ArchitectureTest.java",
      "declared_layer": "L3",
      "actual_layer": "L3",
      "called_by": ["ci-yml"],
      "calls": [],
      "verdict": "KEEP",
      "priority": "P3",
      "finding": "Healthy guardrail of the rule \"a controller does not depend on a repository\"; its comment points to \"CLAUDE.md, Conventions\", a file that did not exist and is now a stub.",
      "evidence": ["src/test/java/com/acme/billing/ArchitectureTest.java:12-16"],
      "target": "Point the comment to AGENTS.md, Rules section.",
      "check": "`grep -n 'CLAUDE.md' src/test/java/com/acme/billing/ArchitectureTest.java` returns nothing."
    },
    {
      "id": "flyway-migrations",
      "path": "src/main/resources/db/migration/",
      "declared_layer": "L3",
      "actual_layer": "L3",
      "called_by": [],
      "calls": [],
      "verdict": "PUSH_DOWN",
      "priority": "P2",
      "finding": "A single migration (V1__init.sql) and no test or job that freezes the applied migrations: the matching rule and Forbidden item of AGENTS.md hold only through text.",
      "evidence": ["src/main/resources/db/migration/V1__init.sql:1", "AGENTS.md:18", "AGENTS.md:23"],
      "target": "A test that compares the checksums of the versioned migrations with a frozen list (or `flyway validate` against a reference database) in ci.yml.",
      "check": "Changing one character of V1__init.sql makes ci.yml fail."
    }
  ],
  "process_leaks": [
    { "rule": "Release preconditions: CI green on the ref, tag v<version> absent, strictly increasing version, migrations not modified", "told_in": ".claude/skills/release/SKILL.md:15-19", "if_skipped": "A version already published or a commit with red CI goes to production", "belongs_in": "L3", "guard_tool": "subcommand `release plan` with exit 1 (rewrite of scripts/release.mjs)" },
    { "rule": "Explicit human validation before any deployment to production", "told_in": "AGENTS.md:22 ; .claude/skills/release/SKILL.md:22", "if_skipped": "An agent deploys to production with a single `gh workflow run`", "belongs_in": "L4", "guard_tool": "deploy job under `environment: production` with required reviewers in release.yml" },
    { "rule": "An applied Flyway migration is never modified", "told_in": "AGENTS.md:18 ; AGENTS.md:23", "if_skipped": "Flyway refuses the checksum, the application no longer restarts in production", "belongs_in": "L3", "guard_tool": "checksum test of the migrations or `flyway validate` in ci.yml" },
    { "rule": "No direct push to main", "told_in": "AGENTS.md:24", "if_skipped": "Code neither reviewed nor tested reaches the production branch", "belongs_in": "L4", "guard_tool": "GitHub branch protection on main (PR + ci.yml required) — cannot be verified here, no remote" },
    { "rule": "VERSION is updated on develop after each release", "told_in": ".claude/skills/release/SKILL.md:36", "if_skipped": "The next release computes from a stale version and republishes an existing number", "belongs_in": "L4", "guard_tool": "step of release.yml that commits VERSION or opens the PR" }
  ],
  "guarded_rules": [
    { "rule": "A controller never depends on a repository", "told_in": "AGENTS.md:17", "guarded_by": "src/test/java/com/acme/billing/ArchitectureTest.java (controllers_do_not_touch_repositories), run by ci.yml" },
    { "rule": "Java style: 120 columns, no star import, one class per file, naming of constants and methods", "told_in": "not told (on purpose)", "guarded_by": "config/checkstyle/checkstyle.xml via ci.yml:13" }
  ],
  "instruction_files": [
    { "path": "AGENTS.md", "loaded_lines": 44, "instruction_pct": 75, "reference_pct": 25, "noise_pct": 0, "justified_rules": true, "maintenance_clause": true },
    { "path": "CLAUDE.md", "loaded_lines": 44, "instruction_pct": 0, "reference_pct": 100, "noise_pct": 0, "justified_rules": true, "maintenance_clause": true },
    { "path": ".claude/skills/release/SKILL.md", "loaded_lines": 45, "instruction_pct": 85, "reference_pct": 15, "noise_pct": 0, "justified_rules": true, "maintenance_clause": false }
  ],
  "remediation": [
    { "order": 1, "priority": "P1", "verdict": "SPLIT", "element": "release-yml", "action": "Separate build-publish and deploy; put deploy under `environment: production` with required reviewers; add a dry_run input; replace `echo SUCCESS` with job outputs; also merge into main (workflow_dispatch only starts from the default branch).", "depends_on": [], "check": "A run stops waiting for approval before deploy; dry_run=true pushes no image.", "needs_human_approval": true },
    { "order": 2, "priority": "P1", "verdict": "BLOCK", "element": "script-old-deploy", "action": "Remove scripts/old-deploy.sh.", "depends_on": [], "check": "File absent; no `ssh deploy@prod.acme.io` outside release.yml.", "needs_human_approval": true },
    { "order": 3, "priority": "P1", "verdict": "PUSH_DOWN", "element": "skill-release", "action": "Rewrite scripts/release.mjs as `release plan <version> --ref <ref> [--hotfix]` (checks CI green, tag absent, increasing version, migrations not modified, exit 1; plan as JSON) and `release run`; the skill keeps only the sequence and the validation.", "depends_on": [], "check": "`release plan` exits 1 on a ref with red CI or an existing tag; the skill no longer contains a check to interpret.", "needs_human_approval": false },
    { "order": 4, "priority": "P2", "verdict": "PROMOTE", "element": "script-release-mjs", "action": "The version becomes a mandatory argument; remove the inference from the branch name.", "depends_on": [3], "check": "Without a version argument, exit 1 with a message.", "needs_human_approval": false },
    { "order": 5, "priority": "P2", "verdict": "MERGE", "element": "script-hotfix-mjs", "action": "Remove scripts/hotfix.mjs, replaced by `release run --hotfix`.", "depends_on": [3], "check": "File absent; `release run --hotfix` from hotfix/* works.", "needs_human_approval": true },
    { "order": 6, "priority": "P2", "verdict": "KEEP", "element": "ci-yml", "action": "Version the Gradle wrapper (gradlew, gradle/wrapper/) or go through gradle/actions/setup-gradle.", "depends_on": [], "check": "A green ci.yml run on develop.", "needs_human_approval": false },
    { "order": 7, "priority": "P2", "verdict": "PUSH_DOWN", "element": "flyway-migrations", "action": "Add a checksum test of the versioned migrations (or `flyway validate`) run by ci.yml; shorten the rule of AGENTS.md to \"Enforced by\".", "depends_on": [6], "check": "Modifying V1__init.sql makes ci.yml fail.", "needs_human_approval": false },
    { "order": 8, "priority": "P2", "verdict": "PUSH_DOWN", "element": "agents-md", "action": "Turn on branch protection on main (PR mandatory, ci.yml check required) and note \"Enforced by: branch protection\" on the Forbidden item.", "depends_on": [], "check": "`gh api repos/:owner/:repo/branches/main/protection` returns required_pull_request_reviews and required_status_checks.", "needs_human_approval": true },
    { "order": 9, "priority": "P3", "verdict": "KEEP", "element": "archunit-test", "action": "Replace \"CLAUDE.md, Conventions\" with \"AGENTS.md, Rules\" in the comment.", "depends_on": [], "check": "grep CLAUDE.md on the test returns nothing.", "needs_human_approval": false }
  ],
  "unverified": [
    "The Gradle commands (`./gradlew checkstyleMain checkstyleTest`, `./gradlew test`) were not run: no toolchain available during the init; they are copied from ci.yml.",
    "Absence of gradlew and of gradle/wrapper/ in the repository: observed on the local develop branch, to be confirmed on the remote.",
    "Absence of a Dockerfile although release.yml:24 runs `docker build .`: to be confirmed on the remote.",
    "Protection of the main branch and default branch of the repository: no remote configured, cannot be verified (workflow_dispatch is only accepted from the default branch).",
    "Health endpoint of production to verify a release: unknown, to be provided by the team.",
    "Number of tests really run by ci.yml: unknown.",
    "Node scripts: only the syntax was checked (`node --check`), no real run (they would trigger release.yml)."
  ]
}
```
