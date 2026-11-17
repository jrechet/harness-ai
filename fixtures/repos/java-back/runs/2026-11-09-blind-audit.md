# Harness audit — Release of billing-api (+ AI instrumentation of the repository)

**Scope**: `fixtures/repos/java-back/repo/` — `CLAUDE.md`, `.claude/skills/release/`, `scripts/`, `.github/workflows/`, `config/checkstyle/`, `build.gradle`, `VERSION`, architecture tests · **Date**: 2026-11-09 · **Items inventoried**: 11

## 1. Summary

- **Health score**: 0 — The agent is a pillar, not an accelerator: all the release preconditions, the detection of success and the handling of failure live only in prompts; the only existing code (two untested scripts) directly triggers the prod deployment with no dry-run and no human stopping point. Computation: 100 − 4 × 25 (P1) − 2 × 8 (P2) = −16, floored at 0 (and capped at 60 anyway by the failure of the "cut the agent" test).
- **Result of the "cut the agent" test**: FAILED — 5 step(s) of the process exist only in prompts (CI green, Flyway migrations applied, branch up to date, detection of success, what to do on failure), and one mandatory step (updating `VERSION`) exists nowhere.
- **Blocking points (P1)**: 4
- **The three actions that change the most**:
  1. Protect `release.yml`: `environment: production` with required reviewers, a `dry_run` input, a check in the workflow that CI is green on the SHA and that `ref` is an allowed branch, tag *after* a successful deployment, structured output (job outputs) instead of `echo "SUCCESS"`.
  2. Replace `scripts/release.mjs` + `scripts/hotfix.mjs` with a tested CLI of three subcommands (`release check` / `release plan --type` / `release run --plan`) that encodes the preconditions as `exit 1`, hands the choice of the kind of version back to the agent and produces JSON; then rewrite the SKILL.md to be only the sequence that calls them.
  3. Remove `scripts/old-deploy.sh` (prod deployment from a workstation, with no CI and no tag) and fix `CLAUDE.md` (example that contradicts its own rule, release procedure duplicated and already diverging, mandatory rules without a guardrail → ArchUnit/Checkstyle/PR gate).

## 2. Map of the harness

| # | Item | Path | Declared layer | Actual layer | Called by | Calls |
|---|---|---|---|---|---|---|
| 1 | Instruction file | `CLAUDE.md` | L2 | L2 (also contains the release procedure, a duplicate of the skill) | Loaded automatically by Claude Code in every session | `release-skill`, `release-mjs`, `hotfix-mjs`, `ci-yml`, `release-yml`, `checkstyle`, `archunit-test` |
| 2 | Release skill | `.claude/skills/release/SKILL.md` | L2 | MIXED (procedure + L3 preconditions told + reading logs instead of a structured L1 return) | `claude-md:46`, triggered by keywords (`SKILL.md:3`) | `release-mjs`, `hotfix-mjs`, `release-yml` (via `gh run watch`), `ci-yml` (reading the Actions tab) |
| 3 | Release script | `scripts/release.mjs` | L3 | MIXED (hardcoded L1 judgment: kind of version inferred from the branch; direct L4 trigger) | `release-skill:14`, `claude-md:97` | `version-file`, `release-yml` (`gh workflow run`) |
| 4 | Hotfix script | `scripts/hotfix.mjs` | L3 | L3 (duplicate of `release.mjs`, direct L4 trigger) | `release-skill:19`, `claude-md:101` | `version-file`, `release-yml` |
| 5 | Old manual deployment | `scripts/old-deploy.sh` | L3 | L4 (build + push + ssh prod from a workstation) | Nobody (`old-deploy.sh:2`) | Registry + prod host directly |
| 6 | Release workflow | `.github/workflows/release.yml` | L4 | L4 | `release-mjs:23`, `hotfix-mjs:16` | `build-gradle` (bootJar), registry, tag, ssh prod |
| 7 | CI workflow | `.github/workflows/ci.yml` | L4 | L4 | Push events on `develop`/`main`, pull_request | `build-gradle` (checkstyle, test) → `checkstyle`, `archunit-test` |
| 8 | Checkstyle | `config/checkstyle/checkstyle.xml` | L3 | L3 | `build-gradle:26`, `ci-yml:13` | — |
| 9 | Architecture test | `src/test/java/com/acme/billing/ArchitectureTest.java` | L3 | L3 | `ci-yml:14` (via `gradlew test`) | — |
| 10 | Build | `build.gradle` | L3 | L3 | `ci-yml:13-14`, `release-yml:23` | `checkstyle`, `version-file` |
| 11 | Version source of truth | `VERSION` | L3 | L3 (data never updated by the process) | `release-mjs:7`, `hotfix-mjs:11`, `build-gradle:9` | — |

Absent from the inventory (checked): no agent or sub-agent definition, no `.cursor/rules`, no hook, no PR template, no `CODEOWNERS`, no `.harness/`.

Nominal process, step by step:

| Process step | Carried by | Enforced by code? | Dry-run? |
|---|---|---|---|
| 1. Make sure the CI of `develop` is green | `SKILL.md:9`, `CLAUDE.md:96` (L2, "open the Actions tab") | No — neither `release.mjs` nor `release.yml` queries the CI status | — |
| 2. Check that no Flyway migration is pending in prod | `SKILL.md:10` (L2, "ask the owner for a dump") | No — depends on a human, not reproducible | — |
| 3. Be on an up-to-date `develop` | `SKILL.md:11` (L2) | No — `release.mjs:11` checks the *name* of the branch, not the synchronisation nor the cleanliness of the tree | — |
| 4. Compute the next version | `release.mjs:10-20`, `hotfix.mjs:13` (untested L3, coded judgment) | Partly — `exit 1` on an unexpected branch (`release.mjs:18-19`, `hotfix.mjs:8-9`) | No — prints the plan and triggers right away (`release.mjs:22-23`) |
| 5. Update `VERSION` and commit | **Nobody** | No — `VERSION` is read (`release.mjs:7`) but never written; the next release recomputes the same version | — |
| 6. Trigger `release.yml` | `release.mjs:23`, `hotfix.mjs:16` (L3→L4) | No precondition checked before the call | No |
| 7. Build jar, Docker image, push to registry | `release.yml:23-26` (L4) | Yes (exit codes of the steps) | No — no `dry_run` input (`release.yml:3-14`) |
| 8. Git tag `vX.Y.Z` | `release.yml:27` (L4) | Yes, but **before** the deployment: a failed deploy leaves an orphan tag | No |
| 9. Prod deployment over SSH | `release.yml:28-31` (L4) | No protected `environment`, no human validation, no control of `ref` | No |
| 10. Confirm the success | `SKILL.md:15`, `CLAUDE.md:98` (L2: look for `SUCCESS` in the log) | No — `echo "SUCCESS"` (`release.yml:32`) is free text, not a job output | — |
| 11. What to do on failure | `SKILL.md:16` (L2) | No | — |
| 12. Announce in #releases with the list of PRs | `SKILL.md:22`, `CLAUDE.md:99` (L1/L2, human) | No — acceptable: it is communication, hence L1 | — |

## 3. Leaks: rules and steps told without enforcement

**Steps of the release process that live only in a prompt**

| Rule / step | Told where | If the agent skips it | Must live in | Target tool |
|---|---|---|---|---|
| "Never release on a red develop" | `SKILL.md:9`, `CLAUDE.md:96` | An untested image goes to prod; the agent can read the wrong run or hallucinate a green | L3 + L4 | `release check` subcommand (`gh api repos/:o/:r/commits/<sha>/check-runs` → `exit 1`) **and** a guard step in `release.yml` before `bootJar` |
| No Flyway migration pending in prod | `SKILL.md:10` | Deployment of an unvalidated schema; the step depends on a dump asked from a human | L3 | `release check --migrations` comparing `db/migration` with `flyway_schema_history` through a read-only connection, or a Testcontainers `flyway.validate()` test in CI |
| On an up-to-date `develop`, clean tree | `SKILL.md:11` | `ref=develop` is sent to the workflow: unpushed local commits are silently left out of the release | L3 | `release check`: `git status --porcelain` empty, `git rev-parse HEAD == origin/develop`, tag `v<next>` does not exist |
| Updating `VERSION` after the release | Nowhere (`release.mjs:7` reads, nobody writes) | The next release recomputes `1.5.0`, `git tag` fails (`release.yml:27`) **after** the image push | L3/L4 | `release run` bump + commit + push of `VERSION`, or a `release.yml` step that commits |
| Success = `SUCCESS` in the log | `SKILL.md:15`, `CLAUDE.md:98`, produced by `release.yml:32` | Hallucinated success (string present elsewhere, run partly green) | L4 → L1 | `outputs:` of the job (`version`, `image`, `deployed_sha`, `health_url`) + `gh run view --json conclusion` read by the CLI |
| If `ERROR`/`FAILED`: warn, do not run again | `SKILL.md:16` | A prod deploy re-run in a loop | L3 | `release run` refuses if a `release.yml` run is in progress or has failed on the same version; `concurrency:` in the workflow |
| The kind of version is decided by the branch name | `release.mjs:11-16`, `SKILL.md:14`, `CLAUDE.md:97` | Cannot be skipped, but an L1 judgment is frozen in L3: a *major* release from `develop` is impossible without bypassing the script | L1 | `release plan --type minor|major|patch`: the CLI exposes the options, the agent/human chooses |

**Rules of CLAUDE.md told without a guardrail**

| Rule | Told where | If the agent skips it | Must live in | Target tool |
|---|---|---|---|---|
| Constructor injection, never `@Autowired` on a field | `CLAUDE.md:51` | Already broken in the code (`InvoiceService.java:10-11`) **and** in the example of the file itself (`CLAUDE.md:74-75`) | L3 | ArchUnit: `noFields().should().beAnnotatedWith(Autowired.class)` in `ArchitectureTest.java` |
| Every endpoint has an authorization test (403 with the wrong role) | `CLAUDE.md:57` | No test of this kind exists (`InvoiceControllerTest.java:8`); a billing API with no tested access control | L3 | Generic JUnit test enumerating `RequestMappingHandlerMapping` and calling each route with `@WithMockUser(roles="NONE")` → 403, run by `ci.yml` |
| Never modify an applied Flyway migration | `CLAUDE.md:63` | `FlywayValidateException` discovered at the prod deployment (`CLAUDE.md:104`) | L3 (PR gate) | `ci.yml` step: `git diff --diff-filter=MD --name-only origin/develop... -- src/main/resources/db/migration` must be empty |
| No `@MockBean` in unit tests | `CLAUDE.md:92` | Slow suite, Spring context started | L3 | Checkstyle `IllegalImport` on `org.springframework.boot.test.mock.mockito.MockBean` in `checkstyleTest`, or an ArchUnit rule on the `*Test` classes |
| 4 spaces, no tabs | `CLAUDE.md:84` | Noisy diff | L3 | Checkstyle `FileTabCharacter` (absent from `checkstyle.xml`) |
| Imports grouped java / javax / org / com | `CLAUDE.md:85` | Noisy diff | L3 | Checkstyle `CustomImportOrder` (absent) |
| Classes in PascalCase, fields in camelCase | `CLAUDE.md:66` | Naming inconsistency | L3 | Checkstyle `TypeName`, `MemberName`, `ParameterName` (only `ConstantName` and `MethodName` exist, `checkstyle.xml:8-9`) |
| Tests named `<Class>Test` / `<Class>IT` | `CLAUDE.md:67` | Tests not picked up by a future Gradle filter | L3 | ArchUnit on `src/test` (`classes().that().areAnnotatedWith(SpringBootTest).should().haveSimpleNameEndingWith("IT")`) — P3 |
| DTOs as `record` | `CLAUDE.md:87` | Hygiene | L3 | ArchUnit `classes().that().resideInAPackage("..dto..").should().beRecords()` — P3 |
| `given / when / then` comments | `CLAUDE.md:91` | Hygiene | — | Noise: a recent model does it; remove or keep as one line |
| Try-with-resources | `CLAUDE.md:60` | Hygiene | — | Noise: default behaviour of a recent model; remove |

**Rules that have their guardrail (healthy part, to be shortened in CLAUDE.md)**

- "A controller that touches a repository is a bug" (`CLAUDE.md:27`, `CLAUDE.md:54`) → `ArchitectureTest.java:14-16`, with the *why* in the Javadoc (`ArchitectureTest.java:12`). Partial guard: covers the dependency on the repository, not "no business logic".
- Line length 120 (`CLAUDE.md:84`) → `checkstyle.xml:4`.
- No wildcard import (`CLAUDE.md:85`) → `checkstyle.xml:6`.
- One public class per file (`CLAUDE.md:68`) → `checkstyle.xml:7`.
- Constants `UPPER_SNAKE_CASE`, methods `camelCase` (`CLAUDE.md:66`) → `checkstyle.xml:8-9`.
- "Run the full suite before opening a PR" (`CLAUDE.md:93`) → `ci.yml:5,14` (`pull_request` + `gradlew test`).
- Checkstyle on every push (`CLAUDE.md:45`) → `ci.yml:13`.
- A hotfix starts from a `hotfix/*` branch (`SKILL.md:19`) → `hotfix.mjs:7-10` (`exit 1`).

## 3b. Context cost

| File | Lines loaded (with includes) | Share instruction / reference / noise | Loaded when |
|---|---|---|---|
| `CLAUDE.md` | 111 (no `@include`) | ≈ 40 % instruction (Conventions, Code style, Testing: l. 48-69, 83-93) / ≈ 45 % reference (Build & Run l. 5-13, Stack l. 15-19, Package structure and Key files l. 31-46, Release l. 95-101, Troubleshooting l. 103-111) / ≈ 15 % noise (standard naming l. 66, try-with-resources l. 60, wrong example l. 70-81) | Every Claude Code session |
| `.claude/skills/release/SKILL.md` | 22 | ≈ 90 % procedure / 10 % header | On demand (keywords release / production rollout / deployment / hotfix, `SKILL.md:3`) |

Justification of the rules: three rules say *why* (`CLAUDE.md:51` "hides dependencies and breaks unit tests", `CLAUDE.md:92` "it starts the context", `CLAUDE.md:104` cause of `FlywayValidateException`); all the others are bare MUSTs, and no incident or issue is cited. **No maintenance clause** (how a rule enters or leaves the file). No description of the working process (when to stop and ask, criterion of "done", flaky test) although the repository does delegate a whole task to the agent (the release).

Internal consistency: the example "a well-formed service" (`CLAUDE.md:70-81`) uses `@Autowired` on a field, exactly what the rule of `CLAUDE.md:51` forbids, and references `Invoice.from(command)` / `CreateInvoiceCommand`, which do not exist; it has probably already been copied (`InvoiceService.java:10-11`). The release procedure of `CLAUDE.md:95-101` has already diverged from the skill (it omits the Flyway check and what to do on failure of `SKILL.md:10,16`). Several references point to files that do not exist: `InvoiceServiceTest` (`CLAUDE.md:9`), `docker compose` (`CLAUDE.md:12,105`, no compose file), packages `customer/payment/config/security` (`CLAUDE.md:33-37`), `gradle.properties` (`CLAUDE.md:109`).

## 4. Findings by item

### [SPLIT] [P1] Release script — `scripts/release.mjs`
- **Does today**: reads the current branch and `VERSION`, infers the kind of version from the branch name (`develop` → minor, `feat/breaking-*` → major, `release/x.y.z` → literal version), prints one line and immediately triggers `gh workflow run release.yml` (`release.mjs:6-24`).
- **Problem**: (a) L1 judgment frozen in L3 — the kind of release is decided by a naming convention, not by a human or the agent (`release.mjs:11-16`); (b) irreversible L4 action triggered with no precondition checked and no dry-run — no check of a clean tree, of synchronisation with `origin`, of CI status, of the tag's existence (`release.mjs:22-23`); (c) `VERSION` is never updated nor committed (`release.mjs:7`, `build.gradle:9`), so the next release recomputes the same version and the `git tag` of `release.yml:27` fails after the image has been pushed; (d) `ref=${branch}` sends a branch name, not the local SHA — any unpushed commit is silently left out; (e) unstructured output (`console.log`, `release.mjs:22,24`), no run URL; (f) no test, no `package.json`.
- **Must become**: a tested CLI (`scripts/release/` or a `release` package) of three subcommands: `check` (preconditions → typed `exit 1`), `plan --type minor|major|patch` (JSON: `current`, `next`, `sha`, `ref`, no side effect), `run --plan plan.json [--dry-run]` (bump + commit of `VERSION`, triggers, returns `{run_url, version}`). The choice of the kind is an argument given by the agent (L1).
- **Verification criterion**: `release plan --type minor` on a dirty or out-of-sync tree exits with a code ≠ 0 and a typed message; `release run --dry-run` triggers no workflow; unit tests of the version computation and of the preconditions green in CI; `scripts/release.mjs` removed.

### [BLOCK] [P1] Old manual deployment — `scripts/old-deploy.sh`
- **Does today**: build, push to registry and `ssh deploy@prod.acme.io … docker compose up -d` from the operator's workstation (`old-deploy.sh:5-7`).
- **Problem**: dead script (`old-deploy.sh:2` "No longer called anywhere") that stays executable: it deploys to prod with no CI, no tag, no trace in Actions, duplicating `release.yml:24-31`. An agent that explores `scripts/` can find it and run it; the presence of local credentials (docker login, SSH key) cannot be checked in the repository.
- **Must become**: removed (or, during the transition, neutralised by an `exit 1` at the top with a message pointing to `release run`).
- **Verification criterion**: file absent from the repository; `grep -r old-deploy` returns nothing; explicit approval from the owner before removal.

### [PUSH_DOWN] [P1] Release workflow — `.github/workflows/release.yml`
- **Does today**: `workflow_dispatch` with inputs `version`, `ref`, `hotfix`; checkout of `ref`, `bootJar -Pversion`, image build/push, tag, SSH prod, `echo "SUCCESS"` (`release.yml:3-32`).
- **Problem**: (a) no `environment: production`, hence no required reviewer, no human stopping point between plan and deployment (`release.yml:16-17`); (b) no `dry_run` input (`release.yml:4-14`); (c) free `ref`: any branch or commit can be deployed to prod (`release.yml:8-10,20`), and the workflow neither checks that CI is green on this SHA nor re-runs `gradlew test` itself (`release.yml:23`); (d) the tag is pushed before the deployment (`release.yml:27` then `28-31`): a failed deploy leaves `vX.Y.Z` on a commit never delivered; (e) `-Pversion=${{ inputs.version }}` is overwritten by `build.gradle:9` (`version = file('VERSION')…`): the image `1.5.0` contains a `1.4.2` jar; (f) `inputs.hotfix` is never used (`release.yml:11-14` vs `hotfix.mjs:16`); (g) the only success signal is `echo "SUCCESS"` (`release.yml:32`), no `outputs`, no post-deploy healthcheck, no `concurrency`. On the positive side: the secrets stay in L4 (`release.yml:25,30`), no secret in the scripts.
- **Must become**: `plan` job (validates `version` against `VERSION`, validates `ref ∈ {develop, release/*, hotfix/*}`, checks green `check-runs` on the SHA, publishes a summary) → `deploy` job with `environment: production` (required reviewers) skipped if `dry_run=true`, tests or CI guard before `bootJar`, tag after a successful healthcheck, `outputs: version, image, sha, run_url`, `concurrency: release-prod`.
- **Verification criterion**: a dispatch with `dry_run=true` ends without touching registry/prod/tags; a dispatch on a `feat/*` branch fails at the `plan` job; the `deploy` job shows "Waiting for review" in Actions; `gh run view --json jobs` exposes the outputs; `-Pversion` honoured (`build.gradle` reads `project.hasProperty('version') ? … : VERSION`).

### [PUSH_DOWN] [P1] Release skill — `.claude/skills/release/SKILL.md`
- **Does today**: describes 8 steps: three manual preconditions (CI green via the Actions tab, Flyway migrations via a dump asked from the owner, `git pull`), running `release.mjs`, reading `SUCCESS`/`ERROR` in `gh run watch`, hotfix, announcement (`SKILL.md:8-22`).
- **Problem**: the three mandatory preconditions are told, not enforced — the agent can skip them or misread the Actions tab (`SKILL.md:9-11`); step 10 is not reproducible without a human; the L1 decision "is it a success" rests on a log grep (`SKILL.md:15-16`), which the harness skill identifies as a source of hallucinated successes. The skill does contain what must be in it: vocabulary, sequence, abort cases (`SKILL.md:16`), communication point (`SKILL.md:22`).
- **Must become**: a SKILL.md that describes only the sequence `release check` → `release plan --type <chosen with the user>` → **stopping point: show the JSON plan and ask for confirmation** → `release run --plan` → read `gh run view --json conclusion,jobs` → announce. The abort cases stay, the preconditions become "if `release check` exits with an error, stop and report the message".
- **Verification criterion**: the SKILL.md no longer contains any instruction such as "open the tab", "compare with the table", "when the output contains SUCCESS"; every command cited exists and has a test.

### [MERGE] [P2] Hotfix script — `scripts/hotfix.mjs`
- **Does today**: same mechanics as `release.mjs` with a patch increment and a guard on `hotfix/*` (`hotfix.mjs:6-16`).
- **Problem**: duplication of the reading of `VERSION`, of the semver parsing and of the `gh workflow run` call (`hotfix.mjs:11-16` ≡ `release.mjs:7-8,23`) — an implicit untested CLI that will diverge; passes `-f hotfix=true`, which the workflow ignores (`release.yml:11-14` never referenced in the steps). Same lack of dry-run and of preconditions as `release.mjs`. The branch guard (`hotfix.mjs:7-10`) is the only coded precondition of the whole harness: to be kept in the CLI.
- **Must become**: `release plan --type patch` with, in `release check`, the rule "`--type patch` requires a `hotfix/*` branch".
- **Verification criterion**: `scripts/hotfix.mjs` removed; `release plan --type patch` from `develop` exits with an error; `SKILL.md` and `CLAUDE.md` no longer mention it.

### [SPLIT] [P2] Instruction file — `CLAUDE.md`
- **Does today**: 111 lines loaded in every session mixing commands, stack, architecture, conventions, style, tests, release procedure and troubleshooting (`CLAUDE.md:5-111`).
- **Problem**: (a) the reference example contradicts the rule it illustrates (`CLAUDE.md:51` vs `CLAUDE.md:74-75`) and will be copied as is — it probably already has been (`InvoiceService.java:10-11`); (b) the release procedure (`CLAUDE.md:95-101`) duplicates `SKILL.md` and has already diverged (omits the steps `SKILL.md:10,16`); (c) ≈ 45 % of reference (Build, Stack, Key files, Troubleshooting) loaded in every session, and references to files that do not exist (`CLAUDE.md:9,12,33-37,105,109`); (d) 11 mandatory rules without a guardrail (section 3), two of them already broken in the code; (e) noise: standard naming (`CLAUDE.md:66`), try-with-resources (`CLAUDE.md:60`); (f) no maintenance clause, little *why*, no incident cited.
- **Must become**: a CLAUDE.md ≤ 50 lines: rules with their *why* and the mention of the guardrail ("enforced by `ArchitectureTest`"), pointer to `.claude/skills/release/SKILL.md` for the release (section 95-101 removed), example fixed to constructor injection, maintenance clause ("any rule added is added in the PR that prompted the review comment; a rule with a guardrail can be shortened to one line"). Reference (commands, troubleshooting, structure) moved to `docs/dev.md` loaded on demand. Mandatory rules pushed down to L3 (see plan).
- **Verification criterion**: `wc -l CLAUDE.md` ≤ 50; no command or path cited is absent from the repository; the example compiles against the real code; the release procedure exists in one place only.

### [KEEP] CI workflow — `.github/workflows/ci.yml`
Right layer, right scope: checkstyle + tests (ArchUnit included) on push to `develop`/`main` and on PRs (`ci.yml:3-14`); it is what `release.yml` must rely on rather than on reading a tab. Natural host of the PR gates to add (Flyway immutability).

### [KEEP] Checkstyle — `config/checkstyle/checkstyle.xml`
Healthy L3 guardrail called by CI (`ci.yml:13`); covers 4 of the style rules of `CLAUDE.md`. To be extended (`FileTabCharacter`, `CustomImportOrder`, `TypeName`, `MemberName`, `IllegalImport`) to absorb the told rules, without changing layer.

### [KEEP] Architecture test — `src/test/java/com/acme/billing/ArchitectureTest.java`
A model of what a CLAUDE.md rule must be: one line in the file, an ArchUnit test that carries it, and a Javadoc that cites the original rule (`ArchitectureTest.java:12-16`). Natural host of the rules "no `@Autowired` on a field" and "no `@MockBean` in a unit test".

### [KEEP] Build — `build.gradle`
Right layer; a single fix, attached to the `release.yml` finding: `version = file('VERSION').text.trim()` (`build.gradle:9`) overwrites the `-Pversion` passed by `release.yml:23`.

### [KEEP] Version source of truth — `VERSION`
Good idea (a single file read by Gradle and the scripts, `build.gradle:9`, `release.mjs:7`, `hotfix.mjs:11`); the defect is that nobody writes it — handled in the `release.mjs` finding.

## 5. Remediation plan

| Order | Priority | Verdict | Item | Action | Depends on | Verification | Human approval required |
|---|---|---|---|---|---|---|---|
| 1 | P1 | BLOCK | `scripts/old-deploy.sh` | Remove the file (or an immediate `exit 1` with a message pointing to `release run`). | — | File absent; `grep -r old-deploy` empty. | Yes (removal + prod access) |
| 2 | P1 | PUSH_DOWN | `.github/workflows/release.yml` | Add `dry_run`, a `plan` job (validates `version` vs `VERSION`, allowed `ref`, green check-runs on the SHA), a `deploy` job under `environment: production` with reviewers, tag after healthcheck, `outputs`, `concurrency`, removal or use of `hotfix`. Fix `build.gradle:9` to honour `-Pversion`. | 1 | Dispatch `dry_run=true` has no effect; dispatch on `feat/*` refused at the `plan` job; "Waiting for review" visible; `gh run view --json jobs` exposes `version`/`image`/`sha`. | Yes (creation of the GitHub environment + reviewers; touches prod) |
| 3 | P1 | SPLIT | `scripts/release.mjs` | Create the `release` CLI (`check`, `plan --type`, `run --plan [--dry-run]`) with tests, JSON output, bump + commit of `VERSION`, `hotfix/*` guard for `--type patch`; then remove `release.mjs`. | 2 | Tests of the CLI green in `ci.yml`; `release check` fails on a dirty tree / red CI / existing tag; `release run --dry-run` triggers nothing; `release.mjs` absent. | Yes for the removal of the script |
| 4 | P2 | MERGE | `scripts/hotfix.mjs` | Remove, replaced by `release plan --type patch`. | 3 | File absent; `release plan --type patch` from `develop` exits with an error. | Yes (removal) |
| 5 | P1 | PUSH_DOWN | `.claude/skills/release/SKILL.md` | Rewrite: sequence `check` → `plan` → user confirmation on the JSON plan → `run` → reading `gh run view --json conclusion` → announcement; drop every manual precondition and every log grep. | 3, 4 | No occurrence of "Actions tab", "dump", "SUCCESS"; every command cited exists. | No |
| 6 | P2 | SPLIT | `CLAUDE.md` | Fix the example (constructor), remove the Release section in favour of a pointer to the skill, move Build/Stack/Troubleshooting to `docs/dev.md`, drop the references to files that do not exist, drop the noise (naming, try-with-resources), add the *why* and a maintenance clause. | 5 | ≤ 50 lines; example compiles; no cited path absent; a single release procedure in the repository. | No |
| 7 | P2 | PUSH_DOWN | `src/test/java/com/acme/billing/ArchitectureTest.java` | Add `noFields().should().beAnnotatedWith(Autowired.class)` (rule `CLAUDE.md:51`) and fix `InvoiceService.java:10-11`; add a rule forbidding `MockBean` in the `*Test` classes (`CLAUDE.md:92`). | — | `gradlew test` red if an `@Autowired` field is reintroduced; `InvoiceService` uses constructor injection. | No |
| 8 | P2 | PUSH_DOWN | `.github/workflows/ci.yml` | Add a generic authorization test (every route → 403 with an unknown role, rule `CLAUDE.md:57`) run by `gradlew test`, and a PR gate step "no Flyway migration modified/deleted" (`CLAUDE.md:63`). | — | An endpoint without security makes CI fail; a PR that modifies `V1__init.sql` is red. | No |
| 9 | P3 | PUSH_DOWN | `config/checkstyle/checkstyle.xml` | Add `FileTabCharacter`, `CustomImportOrder` (java/javax/org/com), `TypeName`, `MemberName`, `ParameterName`; optional: `IllegalImport` for `MockBean` on the `checkstyleTest` side. Shorten the matching rules in `CLAUDE.md` to one line "enforced by Checkstyle". | 6 | `gradlew checkstyleMain checkstyleTest` red on a tab or a badly grouped import. | No |

## 6. What the audit could not verify

- The GitHub settings outside the repository: branch protection of `develop`/`main` (required checks), existence of a `production` `environment`, presence and scope of the secrets `REGISTRY_PASSWORD` / `PROD_SSH_KEY` (`release.yml:25,30`). If `develop` is protected with `ci` required, step 1 of the process is partly covered at merge time, but not at release time.
- The scripts were not run (no authenticated `gh`, no `package.json`); the analysis is static.
- Files referenced but absent from the repository: `gradlew` (called by `ci.yml:13-14`, `release.yml:23`), `Dockerfile` (`release.yml:24`, `old-deploy.sh:5`), compose file (`CLAUDE.md:12,105`), `gradle.properties` (`CLAUDE.md:109`), `InvoiceServiceTest` (`CLAUDE.md:9`), packages `customer`/`payment`/`config`/`security` (`CLAUDE.md:33-37`). Assumption taken: fixture simplification; in a real repository, both workflows would fail at the first step.
- `README.md:3` points to `../traps.md`, outside the audited scope: not opened, in line with the blind evaluation instruction.
- The skill asks to write the JSON into `.harness/audit.json` of the audited repository; the instruction not to change any file of the repo prevails, the JSON is delivered next to the report (`blind-audit.json`).
- The existence of local credentials (docker login registry, SSH key `deploy@prod.acme.io`) that would make `scripts/old-deploy.sh` immediately operative from a workstation.

## 7. Machine data

```json
{
  "audit": {
    "process": "Release of billing-api (+ AI instrumentation of the repository: CLAUDE.md)",
    "scope": "fixtures/repos/java-back/repo/ — CLAUDE.md, .claude/skills/release/, scripts/, .github/workflows/, config/checkstyle/, build.gradle, VERSION, src/test (ArchUnit)",
    "date": "2026-11-09",
    "health_score": 0,
    "cut_the_agent_test": { "passed": false, "leaked_steps": 5 }
  },
  "elements": [
    {
      "id": "release-mjs",
      "path": "scripts/release.mjs",
      "declared_layer": "L3",
      "actual_layer": "MIXED",
      "called_by": ["release-skill", "claude-md"],
      "calls": ["version-file", "release-yml"],
      "verdict": "SPLIT",
      "priority": "P1",
      "finding": "Decides the kind of version on its own from the branch name (frozen L1 judgment), triggers the prod deployment with no precondition and no dry-run, never updates VERSION, unstructured output, no test.",
      "evidence": ["scripts/release.mjs:11-16", "scripts/release.mjs:22-23", "scripts/release.mjs:7", "build.gradle:9", ".github/workflows/release.yml:27"],
      "target": "Tested CLI `release check` / `release plan --type` (JSON, no effect) / `release run --plan [--dry-run]` (bump+commit of VERSION, trigger, run URL); the kind of version becomes an argument chosen by the agent.",
      "check": "`release check` exits non-zero on a dirty tree, red CI or existing tag; `release run --dry-run` triggers nothing; tests green in CI; release.mjs removed."
    },
    {
      "id": "old-deploy-sh",
      "path": "scripts/old-deploy.sh",
      "declared_layer": "L3",
      "actual_layer": "L4",
      "called_by": [],
      "calls": [],
      "verdict": "BLOCK",
      "priority": "P1",
      "finding": "Dead but executable script that builds, pushes and deploys to prod over SSH from a workstation, with no CI, no tag, duplicating release.yml.",
      "evidence": ["scripts/old-deploy.sh:2", "scripts/old-deploy.sh:5-7", ".github/workflows/release.yml:24-31"],
      "target": "Remove the file (or an immediate exit 1 pointing to `release run`).",
      "check": "File absent from the repository; `grep -r old-deploy` empty; owner's approval obtained."
    },
    {
      "id": "release-yml",
      "path": ".github/workflows/release.yml",
      "declared_layer": "L4",
      "actual_layer": "L4",
      "called_by": ["release-mjs", "hotfix-mjs"],
      "calls": ["build-gradle"],
      "verdict": "PUSH_DOWN",
      "priority": "P1",
      "finding": "workflow_dispatch with no protected environment and no dry_run, free ref deployable to prod with no check of CI or tests, tag pushed before the deployment, -Pversion overwritten by build.gradle, unused hotfix input, success signalled by echo SUCCESS instead of outputs.",
      "evidence": [".github/workflows/release.yml:3-14", ".github/workflows/release.yml:16-17", ".github/workflows/release.yml:20", ".github/workflows/release.yml:23", ".github/workflows/release.yml:27", ".github/workflows/release.yml:32", "build.gradle:9"],
      "target": "`plan` job (validation of version/ref/check-runs) then `deploy` job under `environment: production` with reviewers, dry_run input, tag after healthcheck, structured outputs, concurrency; build.gradle honours -Pversion.",
      "check": "Dispatch dry_run=true has no effect; dispatch on feat/* refused; review wait visible in Actions; `gh run view --json jobs` exposes version/image/sha."
    },
    {
      "id": "release-skill",
      "path": ".claude/skills/release/SKILL.md",
      "declared_layer": "L2",
      "actual_layer": "MIXED",
      "called_by": ["claude-md"],
      "calls": ["release-mjs", "hotfix-mjs", "release-yml", "ci-yml"],
      "verdict": "PUSH_DOWN",
      "priority": "P1",
      "finding": "The three mandatory preconditions (CI green, Flyway migrations, branch up to date) and the detection of success (grep SUCCESS) are told and not enforced; the Flyway step depends on a human dump.",
      "evidence": [".claude/skills/release/SKILL.md:9-11", ".claude/skills/release/SKILL.md:15-16"],
      "target": "Skill reduced to the sequence `release check` → `release plan` → user confirmation → `release run` → reading `gh run view --json conclusion` → announcement; the preconditions become exit codes to report.",
      "check": "No mention left of the Actions tab, of a dump or of the SUCCESS string; every command cited exists and is tested."
    },
    {
      "id": "hotfix-mjs",
      "path": "scripts/hotfix.mjs",
      "declared_layer": "L3",
      "actual_layer": "L3",
      "called_by": ["release-skill", "claude-md"],
      "calls": ["version-file", "release-yml"],
      "verdict": "MERGE",
      "priority": "P2",
      "finding": "Duplicates the reading of VERSION, the semver parsing and the gh workflow run call of release.mjs; passes a hotfix input that the workflow ignores; only the hotfix/* branch guard is a real coded precondition.",
      "evidence": ["scripts/hotfix.mjs:11-16", "scripts/release.mjs:7-8", "scripts/release.mjs:23", ".github/workflows/release.yml:11-14", "scripts/hotfix.mjs:7-10"],
      "target": "Merge into `release plan --type patch`, with the rule \"patch requires a hotfix/* branch\" in `release check`.",
      "check": "hotfix.mjs removed; `release plan --type patch` from develop exits with an error; no longer referenced by SKILL.md or CLAUDE.md."
    },
    {
      "id": "claude-md",
      "path": "CLAUDE.md",
      "declared_layer": "L2",
      "actual_layer": "L2",
      "called_by": [],
      "calls": ["release-skill", "release-mjs", "hotfix-mjs", "ci-yml", "release-yml", "checkstyle", "archunit-test"],
      "verdict": "SPLIT",
      "priority": "P2",
      "finding": "Code example that contradicts its own rule (already copied into InvoiceService), release procedure duplicated and diverging from the skill, ~45 % of reference loaded in every session, references to files that do not exist, 11 mandatory rules without a guardrail, no maintenance clause.",
      "evidence": ["CLAUDE.md:51", "CLAUDE.md:74-75", "src/main/java/com/acme/billing/invoice/InvoiceService.java:10-11", "CLAUDE.md:95-101", "CLAUDE.md:9", "CLAUDE.md:33-37", "CLAUDE.md:109", "CLAUDE.md:57", "src/test/java/com/acme/billing/InvoiceControllerTest.java:8", "CLAUDE.md:63"],
      "target": "CLAUDE.md ≤ 50 lines: rules + why + guardrail cited, pointer to the release skill, example fixed, maintenance clause; reference moved to docs/dev.md; mandatory rules pushed down into ArchUnit/Checkstyle/PR gate.",
      "check": "≤ 50 lines; example compiles; no cited path absent; a single release procedure in the repository."
    },
    {
      "id": "ci-yml",
      "path": ".github/workflows/ci.yml",
      "declared_layer": "L4",
      "actual_layer": "L4",
      "called_by": [],
      "calls": ["build-gradle", "checkstyle", "archunit-test"],
      "verdict": "KEEP",
      "priority": null,
      "finding": "Checkstyle and tests (ArchUnit included) on push to develop/main and on PRs: right layer, natural host of the PR gates to add.",
      "evidence": [".github/workflows/ci.yml:3-5", ".github/workflows/ci.yml:13-14"],
      "target": "Keep; add the generic authorization test and the Flyway immutability gate (see remediation).",
      "check": "An unsecured endpoint or a modified migration makes CI fail."
    },
    {
      "id": "checkstyle",
      "path": "config/checkstyle/checkstyle.xml",
      "declared_layer": "L3",
      "actual_layer": "L3",
      "called_by": ["build-gradle", "ci-yml"],
      "calls": [],
      "verdict": "KEEP",
      "priority": null,
      "finding": "Healthy L3 guardrail called by CI, covering 4 style rules of CLAUDE.md; to be extended to absorb the told rules (tabs, import order, TypeName/MemberName).",
      "evidence": ["config/checkstyle/checkstyle.xml:4-9", ".github/workflows/ci.yml:13"],
      "target": "Add FileTabCharacter, CustomImportOrder, TypeName, MemberName, ParameterName, IllegalImport(MockBean).",
      "check": "`gradlew checkstyleMain checkstyleTest` red on a tab or a badly grouped import."
    },
    {
      "id": "archunit-test",
      "path": "src/test/java/com/acme/billing/ArchitectureTest.java",
      "declared_layer": "L3",
      "actual_layer": "L3",
      "called_by": ["ci-yml"],
      "calls": [],
      "verdict": "KEEP",
      "priority": null,
      "finding": "Model of the pair CLAUDE.md rule / ArchUnit guardrail, with the Javadoc that cites the original rule; host of the constructor-injection and no-MockBean rules.",
      "evidence": ["src/test/java/com/acme/billing/ArchitectureTest.java:12-16"],
      "target": "Add noFields().should().beAnnotatedWith(Autowired.class) and a rule on MockBean in the *Test classes.",
      "check": "`gradlew test` red if an @Autowired field is reintroduced."
    },
    {
      "id": "build-gradle",
      "path": "build.gradle",
      "declared_layer": "L3",
      "actual_layer": "L3",
      "called_by": ["ci-yml", "release-yml"],
      "calls": ["checkstyle", "version-file"],
      "verdict": "KEEP",
      "priority": null,
      "finding": "Right layer; `version = file('VERSION')` overwrites the -Pversion passed by release.yml, fix attached to the release-yml finding.",
      "evidence": ["build.gradle:9", ".github/workflows/release.yml:23"],
      "target": "Honour -Pversion when it is given, otherwise read VERSION.",
      "check": "`gradlew bootJar -Pversion=9.9.9` produces a 9.9.9 jar."
    },
    {
      "id": "version-file",
      "path": "VERSION",
      "declared_layer": "L3",
      "actual_layer": "L3",
      "called_by": ["release-mjs", "hotfix-mjs", "build-gradle"],
      "calls": [],
      "verdict": "KEEP",
      "priority": null,
      "finding": "Correct single source of truth, but never written by the process (handled in release-mjs).",
      "evidence": ["VERSION:1", "scripts/release.mjs:7", "build.gradle:9"],
      "target": "Keep; `release run` updates it and commits it.",
      "check": "After a release, VERSION holds the tagged version."
    }
  ],
  "process_leaks": [
    { "rule": "Never release on a red develop (CI green)", "told_in": ".claude/skills/release/SKILL.md:9", "if_skipped": "Untested image deployed to prod; the agent can read the wrong run or hallucinate a green", "belongs_in": "L4", "guard_tool": "Guard step in release.yml (check-runs of the SHA) + `release check` (exit 1)" },
    { "rule": "No Flyway migration pending in prod", "told_in": ".claude/skills/release/SKILL.md:10", "if_skipped": "Unvalidated schema deployed; step not reproducible without a human dump", "belongs_in": "L3", "guard_tool": "`release check --migrations` or a Testcontainers flyway.validate() test in CI" },
    { "rule": "Be on an up-to-date develop, clean tree", "told_in": ".claude/skills/release/SKILL.md:11", "if_skipped": "Unpushed local commits silently left out (ref=branch sent to the workflow)", "belongs_in": "L3", "guard_tool": "`release check`: git status --porcelain empty, HEAD == origin/develop, tag does not exist" },
    { "rule": "Update VERSION after the release", "told_in": "scripts/release.mjs:7 (read, never written — the step is told nowhere)", "if_skipped": "The next release recomputes the same version; git tag fails after the image push", "belongs_in": "L3", "guard_tool": "`release run` bump + commit + push of VERSION" },
    { "rule": "Success is read in the SUCCESS string of the log", "told_in": ".claude/skills/release/SKILL.md:15", "if_skipped": "Hallucinated success; no structured return to decide on", "belongs_in": "L4", "guard_tool": "outputs of the release.yml job + `gh run view --json conclusion`" },
    { "rule": "If ERROR/FAILED, warn and do not run again", "told_in": ".claude/skills/release/SKILL.md:16", "if_skipped": "A prod deploy re-run in a loop", "belongs_in": "L4", "guard_tool": "`concurrency:` in release.yml + `release run` refused if a run is in progress or has failed on the same version" },
    { "rule": "Constructor injection, never @Autowired on a field", "told_in": "CLAUDE.md:51", "if_skipped": "Already broken (InvoiceService.java:10-11) and by the example CLAUDE.md:74-75", "belongs_in": "L3", "guard_tool": "ArchUnit noFields().should().beAnnotatedWith(Autowired.class) in ArchitectureTest.java" },
    { "rule": "Every endpoint has an authorization test (403 with the wrong role)", "told_in": "CLAUDE.md:57", "if_skipped": "No 403 test exists (InvoiceControllerTest.java:8); billing API with no tested access control", "belongs_in": "L3", "guard_tool": "Generic JUnit test on RequestMappingHandlerMapping run by ci.yml" },
    { "rule": "Never modify an applied Flyway migration", "told_in": "CLAUDE.md:63", "if_skipped": "FlywayValidateException discovered at the prod deployment", "belongs_in": "L3", "guard_tool": "PR gate step in ci.yml: git diff --diff-filter=MD on db/migration empty" },
    { "rule": "No @MockBean in unit tests", "told_in": "CLAUDE.md:92", "if_skipped": "Slow suite, Spring context started", "belongs_in": "L3", "guard_tool": "Checkstyle IllegalImport (checkstyleTest) or ArchUnit rule on *Test" },
    { "rule": "4 spaces, no tabs", "told_in": "CLAUDE.md:84", "if_skipped": "Noisy diff", "belongs_in": "L3", "guard_tool": "Checkstyle FileTabCharacter" },
    { "rule": "Imports grouped java / javax / org / com", "told_in": "CLAUDE.md:85", "if_skipped": "Noisy diff", "belongs_in": "L3", "guard_tool": "Checkstyle CustomImportOrder" },
    { "rule": "Classes PascalCase, fields camelCase", "told_in": "CLAUDE.md:66", "if_skipped": "Naming inconsistency", "belongs_in": "L3", "guard_tool": "Checkstyle TypeName, MemberName, ParameterName" },
    { "rule": "Tests named <Class>Test / <Class>IT", "told_in": "CLAUDE.md:67", "if_skipped": "Hygiene", "belongs_in": "L3", "guard_tool": "ArchUnit on src/test (P3)" },
    { "rule": "DTOs as records", "told_in": "CLAUDE.md:87", "if_skipped": "Hygiene", "belongs_in": "L3", "guard_tool": "ArchUnit classes().that().resideInAPackage(\"..dto..\").should().beRecords() (P3)" }
  ],
  "guarded_rules": [
    { "rule": "A controller does not touch a repository / no business logic in controllers", "told_in": "CLAUDE.md:54", "guarded_by": "src/test/java/com/acme/billing/ArchitectureTest.java:14-16" },
    { "rule": "Max line length 120", "told_in": "CLAUDE.md:84", "guarded_by": "config/checkstyle/checkstyle.xml:4" },
    { "rule": "No wildcard import", "told_in": "CLAUDE.md:85", "guarded_by": "config/checkstyle/checkstyle.xml:6" },
    { "rule": "One public class per file", "told_in": "CLAUDE.md:68", "guarded_by": "config/checkstyle/checkstyle.xml:7" },
    { "rule": "Constants UPPER_SNAKE_CASE, methods camelCase", "told_in": "CLAUDE.md:66", "guarded_by": "config/checkstyle/checkstyle.xml:8-9" },
    { "rule": "Full suite before opening a PR", "told_in": "CLAUDE.md:93", "guarded_by": ".github/workflows/ci.yml:5,14" },
    { "rule": "Checkstyle on every push", "told_in": "CLAUDE.md:45", "guarded_by": ".github/workflows/ci.yml:13" },
    { "rule": "A hotfix starts from a hotfix/* branch", "told_in": ".claude/skills/release/SKILL.md:19", "guarded_by": "scripts/hotfix.mjs:7-10" }
  ],
  "instruction_files": [
    { "path": "CLAUDE.md", "loaded_lines": 111, "instruction_pct": 40, "reference_pct": 45, "noise_pct": 15, "justified_rules": false, "maintenance_clause": false },
    { "path": ".claude/skills/release/SKILL.md", "loaded_lines": 22, "instruction_pct": 90, "reference_pct": 10, "noise_pct": 0, "justified_rules": false, "maintenance_clause": false }
  ],
  "remediation": [
    { "order": 1, "priority": "P1", "verdict": "BLOCK", "element": "old-deploy-sh", "action": "Remove scripts/old-deploy.sh (or an immediate exit 1 pointing to `release run`).", "depends_on": [], "check": "File absent; `grep -r old-deploy` empty.", "needs_human_approval": true },
    { "order": 2, "priority": "P1", "verdict": "PUSH_DOWN", "element": "release-yml", "action": "Add dry_run, a plan job (version vs VERSION, allowed ref, green check-runs), a deploy job under environment: production with reviewers, tag after healthcheck, outputs, concurrency, removal/use of the hotfix input; fix build.gradle:9 to honour -Pversion.", "depends_on": ["old-deploy-sh"], "check": "Dispatch dry_run=true has no effect; dispatch on feat/* refused; review wait visible; `gh run view --json jobs` exposes version/image/sha.", "needs_human_approval": true },
    { "order": 3, "priority": "P1", "verdict": "SPLIT", "element": "release-mjs", "action": "Create the release CLI (check, plan --type, run --plan [--dry-run]) with tests, JSON, bump+commit of VERSION, hotfix/* guard for --type patch; then remove scripts/release.mjs.", "depends_on": ["release-yml"], "check": "CLI tests green in CI; `release check` fails on a dirty tree/red CI/existing tag; `release run --dry-run` triggers nothing; release.mjs absent.", "needs_human_approval": true },
    { "order": 4, "priority": "P2", "verdict": "MERGE", "element": "hotfix-mjs", "action": "Remove scripts/hotfix.mjs, replaced by `release plan --type patch`.", "depends_on": ["release-mjs"], "check": "File absent; `release plan --type patch` from develop exits with an error.", "needs_human_approval": true },
    { "order": 5, "priority": "P1", "verdict": "PUSH_DOWN", "element": "release-skill", "action": "Rewrite SKILL.md: check → plan → user confirmation on the JSON plan → run → `gh run view --json conclusion` → announcement; drop every manual precondition and every log grep.", "depends_on": ["release-mjs", "hotfix-mjs"], "check": "No occurrence of \"Actions tab\", \"dump\", \"SUCCESS\"; every command cited exists.", "needs_human_approval": false },
    { "order": 6, "priority": "P2", "verdict": "SPLIT", "element": "claude-md", "action": "Fix the example (constructor), replace the Release section with a pointer to the skill, move Build/Stack/Troubleshooting to docs/dev.md, drop the references to files that do not exist and the noise, add the why and a maintenance clause.", "depends_on": ["release-skill"], "check": "≤ 50 lines; example compiles; no cited path absent; a single release procedure.", "needs_human_approval": false },
    { "order": 7, "priority": "P2", "verdict": "PUSH_DOWN", "element": "archunit-test", "action": "Add noFields().should().beAnnotatedWith(Autowired.class) and a rule forbidding MockBean in the *Test classes; fix InvoiceService.java:10-11.", "depends_on": [], "check": "`gradlew test` red if an @Autowired field is reintroduced; InvoiceService uses constructor injection.", "needs_human_approval": false },
    { "order": 8, "priority": "P2", "verdict": "PUSH_DOWN", "element": "ci-yml", "action": "Add a generic authorization test (every route → 403 with an unknown role) and a PR gate step \"no Flyway migration modified/deleted\".", "depends_on": [], "check": "An endpoint without security makes CI fail; a PR modifying V1__init.sql is red.", "needs_human_approval": false },
    { "order": 9, "priority": "P3", "verdict": "PUSH_DOWN", "element": "checkstyle", "action": "Add FileTabCharacter, CustomImportOrder, TypeName, MemberName, ParameterName, IllegalImport(MockBean); shorten the matching rules of CLAUDE.md to \"enforced by Checkstyle\".", "depends_on": ["claude-md"], "check": "`gradlew checkstyleMain checkstyleTest` red on a tab or a badly grouped import.", "needs_human_approval": false }
  ],
  "unverified": [
    "GitHub settings outside the repository: branch protection of develop/main, existence of a production environment, presence of the secrets REGISTRY_PASSWORD and PROD_SSH_KEY (release.yml:25,30).",
    "Scripts not run (no authenticated gh, no package.json): static analysis only.",
    "Files referenced but absent: gradlew (ci.yml:13-14, release.yml:23), Dockerfile (release.yml:24, old-deploy.sh:5), compose file (CLAUDE.md:12,105), gradle.properties (CLAUDE.md:109), InvoiceServiceTest (CLAUDE.md:9), packages customer/payment/config/security (CLAUDE.md:33-37); assumption: fixture simplification.",
    "README.md:3 points to ../traps.md, out of scope: not opened (blind evaluation).",
    ".harness/audit.json not written into the audited repository (instruction to change nothing); JSON delivered in blind-audit.json next to the report.",
    "Existence of local credentials (docker login registry, SSH key deploy@prod.acme.io) that would make scripts/old-deploy.sh immediately operative."
  ]
}
```
