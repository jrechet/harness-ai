# Harness audit — Release / production deployment of billing-api + AI instrumentation (CLAUDE.md, release skill)

**Scope**: `fixtures/repos/java-back/repo` — `CLAUDE.md`, `.claude/skills/release/`, `scripts/`, `.github/workflows/`, `config/checkstyle/`, `build.gradle`, `src/test` (ArchUnit) · **Date**: 2026-11-09 · **Items inventoried**: 10

## 1. Summary

- **Health score**: 0 — the agent is not an accelerator but the sole carrier of the release preconditions and of the stopping point before prod: 4 P1 (−100) and 2 P2 (−16) bring the score down to 0, and the "cut the agent" test fails (cap of 60 anyway).
- **Result of the "cut the agent" test**: FAILED — 4 step(s) of the process exist only in prompts (develop CI green, Flyway migrations aligned with prod, develop up to date, structured reading of the success). A fifth is missing everywhere: there is no human stopping point between the plan and the prod deployment.
- **Blocking points (P1)**: 4 — `SKILL.md` (preconditions told), `scripts/release.mjs` (hardcoded judgment + prod trigger without dry-run, VERSION never incremented), `.github/workflows/release.yml` (prod dispatch with no protected `environment` and no `dry_run`), `scripts/old-deploy.sh` (dead but executable path to prod).
- **The three actions that change the most**:
  1. Protect `release.yml`: separate `publish` and `deploy-prod`, put `deploy-prod` under `environment: production` with mandatory reviewers, add `dry_run`, validate the version and the tag, set a `concurrency` — it is the only guardrail that holds whoever the caller is (agent, human, cron).
  2. Replace `release.mjs` + `hotfix.mjs` with a tested CLI `release plan` / `release run`: preconditions as `exit 1` (CI green, tree clean and up to date, tag does not exist), kind of version chosen by the human/agent (`--type`), JSON plan without execution, bump and commit of `VERSION`, run URL and conclusion in return. Then rewrite the skill as a pure procedure around these two commands.
  3. Push the mandatory rules of `CLAUDE.md` down into guardrails (ArchUnit "no field injection", generic authorization test per endpoint, CI gate "immutable migrations"), fix the example that contradicts its own rule, de-duplicate the Release section and remove `old-deploy.sh`.

## 2. Map of the harness

| # | Item | Path | Declared layer | Actual layer | Called by | Calls |
|---|---|---|---|---|---|---|
| 1 | Repo instruction file | `CLAUDE.md` | L2 | MIXED (L2 + duplicated release procedure + 45 % of reference) | Loaded automatically by Claude Code (no explicit caller) | release skill, `release.mjs`, `hotfix.mjs`, `ci.yml`, `release.yml`, Checkstyle, ArchUnit |
| 2 | Release skill | `.claude/skills/release/SKILL.md` | L2 | MIXED (L2 + L3 preconditions told + reading logs) | `CLAUDE.md:46`, triggered by keyword (`SKILL.md:3`) | `release.mjs`, `hotfix.mjs`, `release.yml` (via `gh run watch`), `ci.yml` (reading the Actions tab) |
| 3 | Release script | `scripts/release.mjs` | L3 | MIXED (L1 coded judgment + L3 computation + L4 trigger) | `SKILL.md:14`, `CLAUDE.md:97` | `release.yml` (`gh workflow run`), reads `VERSION` |
| 4 | Hotfix script | `scripts/hotfix.mjs` | L3 | L3 (+ L4 trigger) | `SKILL.md:19`, `CLAUDE.md:101` | `release.yml`, reads `VERSION` |
| 5 | Old manual deployment | `scripts/old-deploy.sh` | L3 | L4 (build + push + ssh prod directly) | Nobody (`old-deploy.sh:2`) | registry and `prod.acme.io` directly |
| 6 | Release workflow | `.github/workflows/release.yml` | L4 | L4 | `release.mjs:23`, `hotfix.mjs:16` (`workflow_dispatch`) | Gradle, Docker, registry, SSH prod |
| 7 | CI workflow | `.github/workflows/ci.yml` | L4 | L4 | Push events on develop/main and PRs | Checkstyle, tests (ArchUnit included) |
| 8 | Checkstyle | `config/checkstyle/checkstyle.xml` | L3 | L3 | `ci.yml:13`, `build.gradle:24` | — |
| 9 | ArchUnit | `src/test/java/com/acme/billing/ArchitectureTest.java` | L3 | L3 | `ci.yml:14` | — |
| 10 | Gradle build + VERSION | `build.gradle` (+ `VERSION`) | L3 | L3 | `ci.yml`, `release.yml:23`, `release.mjs:7`, `hotfix.mjs:11` | Checkstyle |

No agent, sub-agent, hook, `.claude/settings.json`, `.cursor/rules` or `@include` was found.

Nominal process (release from `develop`):

| Process step | Carried by | Enforced by code? | Dry-run? |
|---|---|---|---|
| 1. Make sure the CI of `develop` is green | L2 — `SKILL.md:9`, `CLAUDE.md:96` (look at the Actions tab) | No — `release.mjs` does not read the status, `release.yml` does not re-run the tests | n/a |
| 2. Check the Flyway migrations vs the `flyway_schema_history` of prod | L2 — `SKILL.md:10` (ask the owner for a dump) | No — detection only at prod startup (`FlywayValidateException`, `CLAUDE.md:104`) | n/a |
| 3. Be on an up-to-date `develop` | L2 — `SKILL.md:11` | Partly — `release.mjs:11` checks the branch name, not the sync with origin nor the cleanliness of the tree | n/a |
| 4. Choose the kind of version (major / minor / patch) | L3 — `release.mjs:11-16` (inferred from the branch prefix) | Yes but wrong layer: frozen L1 judgment; patch from develop impossible, major = deploying a `feat/breaking-*` branch to prod | No |
| 5. Compute the next version | L3 — `release.mjs:7-8`, `hotfix.mjs:11-13` | Yes (untested); `VERSION` never incremented → the next release recomputes the same version | No |
| 6. Trigger `release.yml` | L3 → L4 — `release.mjs:23`, `hotfix.mjs:16` | Yes; no confirmation, no `--dry-run` | No |
| 7. Build, image, push, tag, deploy prod | L4 — `release.yml:23-31` | Yes; no protected `environment`, no validation of `version`/`ref`, no `concurrency`, `hotfix` input ignored | No (no `dry_run` input) |
| 8. Confirm the success | L2 — `SKILL.md:15`, `CLAUDE.md:98` (grep `SUCCESS` in the logs) | No — `SUCCESS` is an `echo` (`release.yml:32`), `gh workflow run` returns no run id | n/a |
| 9. On failure: warn, do not run again | L1/L2 — `SKILL.md:16` | Judgment: in its place; but no rollback exists in L4 | n/a |
| 10. Announce in #releases with the list of PRs | L1 — `SKILL.md:22`, `CLAUDE.md:99` | No (open choice, acceptable); the list of PRs could be produced by L4 (`gh release create --generate-notes`) | n/a |
| Hotfix: same chain from `hotfix/*` with a patch | L2 → L3 — `SKILL.md:19`, `hotfix.mjs:7-16` | Branch checked (`hotfix.mjs:7`); `hotfix=true` never read by `release.yml` | No |

## 3. Leaks: rules and steps told without enforcement

Release process:

1. **CI of `develop` green before the release** — told at `SKILL.md:9`, `CLAUDE.md:96`. If skipped: an image built on a red develop goes to prod, `release.yml` re-runs neither tests nor Checkstyle. Must live in **L3**: `release plan` subcommand reading `gh run list --workflow ci.yml --branch develop --json conclusion` (exit 1 otherwise), doubled in **L4** by a `./gradlew test` step in the `publish` job.
2. **No Flyway migration left unapplied in prod** — told at `SKILL.md:10` (with a request to the owner for a prod dump). If skipped: Flyway failure when the container starts, discovered after `docker compose up -d`. Must live in **L4**: `flyway info` / `flyway validate` step against the prod database in `deploy-prod`, before the `docker pull`.
3. **`develop` up to date and clean tree** — told at `SKILL.md:11`. If skipped: `release.mjs` triggers with a local `ref` and `VERSION` that do not match what will be built. Must live in **L3**: `release plan` runs `git fetch` and exits 1 if behind/ahead or dirty tree.
4. **Success = `SUCCESS` in the logs, failure = `ERROR`/`FAILED`** — told at `SKILL.md:15-16`, `CLAUDE.md:98`. If skipped or misread: hallucinated success; a half-failed run (image pushed, tag refused) cannot be told apart. Must live in **L3/L4**: `release run` returns the run URL and reads `gh run view --json conclusion,jobs`; `release.yml` exposes outputs.
5. **Human stopping point before prod** — absent: `SKILL.md:14` goes straight on to `node scripts/release.mjs`, which triggers without confirmation (`release.mjs:23`), and `release.yml:16-31` has neither a protected `environment` nor `dry_run`. Must live in **L4** (`environment: production` with reviewers) and in **L3** (`plan --dry-run` by default, `run` requiring a plan).

Rules of `CLAUDE.md` (mode "if the file is removed, what does CI let through?"):

6. **Constructor injection, never field injection** — `CLAUDE.md:51`. CI lets through `InvoiceService.java:10-11` (`@Autowired` on a field) and the example of `CLAUDE.md:74-75` recommends it. → **L3**, ArchUnit rule `noFields().should().beAnnotatedWith(Autowired.class)` in `ArchitectureTest.java`.
7. **Every endpoint has an authorization test (wrong role → 403)** — `CLAUDE.md:57`. `InvoiceControllerTest.java:8` records that none exists; no Spring Security configuration in `src/`. Security consequence. → **L3**, test parameterised on `RequestMappingHandlerMapping` with `@WithMockUser(roles="NONE")` expecting 401/403.
8. **Never modify an applied migration** — `CLAUDE.md:63`. Guardrail only at prod startup (`CLAUDE.md:104`), too late. → **L3**, CI step diffing `src/main/resources/db/migration/V*` against the target branch (exit 1 on M/D) or a Testcontainers test `migrate` + `validate`.

Hygiene rules told, P3 at most (noise or pointer to the tool): try-with-resources (`CLAUDE.md:60`, a recent model already does it → INLINE), `given / when / then` comments (`CLAUDE.md:91`), `Optional` / `record` (`CLAUDE.md:86-87`), no `@MockBean` in a unit test (`CLAUDE.md:92`, ArchUnit rule possible on `src/test`), grouping of the imports java/javax/org/com (`CLAUDE.md:85`, Checkstyle module `CustomImportOrder`), naming of classes/fields (`CLAUDE.md:66`, modules `TypeName`/`MemberName`).

Rules that **have** their guardrail (healthy part):

- No business logic and no repository access in controllers (`CLAUDE.md:27`, `CLAUDE.md:54`) → `ArchitectureTest.java:14-16`, with a javadoc that cites the rule (`ArchitectureTest.java:12`).
- Line length 120 (`CLAUDE.md:84`) → `checkstyle.xml:4`.
- No wildcard import (`CLAUDE.md:85`) → `checkstyle.xml:6`.
- One public class per file (`CLAUDE.md:68`) → `checkstyle.xml:7`.
- Constants UPPER_SNAKE_CASE / methods camelCase (`CLAUDE.md:66`) → `checkstyle.xml:8-9` (partial).
- Full suite and Checkstyle before a PR / on every push (`CLAUDE.md:93`, `CLAUDE.md:45`) → `ci.yml:5`, `ci.yml:13-14`.
- A hotfix starts from `hotfix/*` (`SKILL.md:19`) → `hotfix.mjs:7-9` (exit 1).
- A release starts from `develop`, `release/*` or `feat/breaking-*` (`CLAUDE.md:97`) → `release.mjs:17-19` (exit 1) — the allowed scope is itself debatable.

## 3b. Context cost (if instruction files are in scope)

| File | Lines loaded (with includes) | Share instruction / reference / noise | Loaded when |
|---|---|---|---|
| `CLAUDE.md` | 111 (no include) | 29 % / 45 % / 26 % — reference: Build (5-14), Stack (15-20), Packages (31-39), Key files (40-47), Release process (95-102, duplicate of the skill), Troubleshooting (103-111); noise: wrong example (70-82), standard naming (65-68), try-with-resources (59-61), header (1-4) | In every Claude Code session |
| `.claude/skills/release/SKILL.md` | 22 | 100 % procedure (including 3 preconditions that should be code) | On demand, on the keywords release / production rollout / deployment / hotfix (`SKILL.md:3`) |

Justification: three rules say *why* (`CLAUDE.md:51` "hides dependencies and breaks unit tests", `CLAUDE.md:92` "it starts the context", `CLAUDE.md:106` "do not disable the rule"), none cites an incident; the others are plain MUSTs. No maintenance clause (how a rule enters or leaves the file) in `CLAUDE.md` or in `SKILL.md`; no description of the working process (when to stop and ask, criterion of "done", flaky test). Internal inconsistencies: the "well-formed service" example (`CLAUDE.md:70-81`) breaks the rule `CLAUDE.md:51`; `CLAUDE.md:97` says the version is "picked from the branch name" whereas `release.mjs:7-16` computes it from `VERSION`; `CLAUDE.md:9` cites `InvoiceServiceTest` (does not exist), `CLAUDE.md:12` a `docker compose` with no compose file, `CLAUDE.md:33-37` four packages absent from `src/`, `CLAUDE.md:42` a `dto/` folder that is absent (the DTO is a nested record, `InvoiceController.java:19`).

## 4. Findings by item

### [PUSH_DOWN] [P1] Release skill — `.claude/skills/release/SKILL.md`
- **Does today**: tells the release sequence: three manual preconditions (look at the Actions tab, compare the migrations with a prod dump, `git checkout develop && git pull`), then `node scripts/release.mjs`, `gh run watch`, grep of `SUCCESS` / `ERROR` / `FAILED`, hotfix variant, #releases announcement.
- **Problem**: the mandatory preconditions are only told (evidence: `SKILL.md:9`, `SKILL.md:10`, `SKILL.md:11`) — the agent can skip them or believe them satisfied; the trigger of the prod deployment follows immediately with no human stopping point and no dry-run (`SKILL.md:14`); the success is read in an unstructured log (`SKILL.md:15-16`), and `gh run watch` without a run id assumes an interactive choice that `release.mjs:24` does not provide; step 2 has a dump of the production database asked for in a prompt (`SKILL.md:10`).
- **Must become**: a pure L2 skill — vocabulary, sequence `release plan --type …` → presenting the JSON plan to the human and waiting for their agreement → `release run` → reading `conclusion` and the run URL; abort cases kept (failure = warn, do not run again; plan refused = stop); #releases announcement fed by the generated release notes.
- **Verification criterion**: no manual check, tab reading or log grep left in the file; an explicit confirmation step comes before `release run`; every step points to an existing subcommand or workflow.

### [SPLIT] [P1] Release script — `scripts/release.mjs`
- **Does today**: reads the current branch and `VERSION`, infers the kind of version from the branch prefix, prints one line and runs `gh workflow run release.yml -f version=… -f ref=…`.
- **Problem**: hardcoded L1 judgment — "a release from develop is always a minor", "the branch prefix decides on a major" (evidence: `release.mjs:11-16`) — which rules out a patch from `develop` and makes a `feat/breaking-*` branch a `ref` deployed as is to prod; no precondition checked (CI, sync with origin, clean tree, existing tag, `gh auth`); no `--dry-run` and no confirmation before the irreversible L4 action (`release.mjs:23`); return in free text with no run id or URL (`release.mjs:22-24`); `VERSION` is never incremented nor committed (`release.mjs:7`, `VERSION:1`), so the next release recomputes `1.5.0`, the image is rewritten then `git push origin v1.5.0` fails (`release.yml:27`); no test.
- **Must become**: a tested CLI in two subcommands — `release plan --type major|minor|patch [--dry-run]` (preconditions as exit 1, version computation, JSON plan) and `release run --plan <file>` (bump + commit of `VERSION`, trigger, JSON return with the run URL and conclusion); the kind of version is a choice of the human/agent, the script only exposes the options.
- **Verification criterion**: `release plan --dry-run` triggers nothing and exits with a code ≠ 0 on a develop that is red, behind or dirty; `release run` refuses without a plan; unit tests of the version computation and of the preconditions green in CI; `scripts/release.mjs` removed.

### [SPLIT] [P1] Release workflow — `.github/workflows/release.yml`
- **Does today**: on `workflow_dispatch(version, ref, hotfix)`, a single job builds the jar and the image, pushes it, tags and deploys to prod over SSH, then `echo "SUCCESS"`.
- **Problem**: prod deployment with no protected `environment` or reviewers and no `dry_run` input (evidence: `release.yml:3-16`, `release.yml:28-31`) — an L4 leak independent of the agent; free `ref`, any commit or branch can go to prod (`release.yml:8-10`, `release.yml:20`); `version` not validated (format, tag already existing) and tag pushed *after* the image (`release.yml:26-27`); no tests and no reading of the CI status before the build; no `concurrency`, no explicit `permissions:` for the tag push; `hotfix` input declared but never read (`release.yml:11-14`); success signal = `echo` (`release.yml:32`); `-Pversion` overwritten by `build.gradle:9`, which re-reads `VERSION` (`release.yml:23`) → jar and image do not carry the same version; no rollback.
- **Must become**: `publish` job (regex validation `x.y.z` + `git ls-remote --tags` empty, `./gradlew test`, bootJar, image, tag, `gh release create --generate-notes`) then `deploy-prod` job under `environment: production` with mandatory approval; a `dry_run` input that stops after the plan; `concurrency: release-prod`; `permissions: contents: write`; structured outputs (version, image, URL); removal of the `echo SUCCESS` and of the unused `hotfix` input; `VERSION` committed upstream by the CLI rather than `-Pversion`.
- **Verification criterion**: dispatch `dry_run=true` → no registry push, no SSH; real dispatch → `deploy-prod` waiting for approval; `version=abc` or existing tag → failure before the build; `ls build/libs` in the job shows the tagged version.

### [BLOCK] [P1] Old manual deployment — `scripts/old-deploy.sh`
- **Does today**: `docker build`, `docker push` and `ssh deploy@prod.acme.io "docker pull … && docker compose up -d"` from the caller's workstation, for any string passed as `$1`.
- **Problem**: dead script by the file's own admission (evidence: `old-deploy.sh:2`) but still executable: it deploys to prod with no tests, no tag, no pipeline, with the local credentials (`old-deploy.sh:5-7`); no hook or `settings.json` forbids an agent to run it, for example when `release.yml` fails at the SSH step (`CLAUDE.md:108`).
- **Must become**: removed; the `deploy-prod` job of `release.yml` is the only path to `prod.acme.io`.
- **Verification criterion**: file absent; `grep -r prod.acme.io` returns only `release.yml`. Removal subject to human approval.

### [MERGE] [P2] Hotfix script — `scripts/hotfix.mjs`
- **Does today**: checks `hotfix/*`, reads `VERSION`, increments the patch, runs `gh workflow run release.yml … -f hotfix=true`.
- **Problem**: duplicates `release.mjs` but for the variation (evidence: `hotfix.mjs:11-13`, `hotfix.mjs:16` vs `release.mjs:7-8`, `release.mjs:23`) — an implicit CLI in two untested copies; `hotfix=true` is read nowhere in the workflow (`release.yml:11-14` only), so a hotfix is identical to a release; same lack of dry-run, of confirmation and of `VERSION` bump; no check that the branch starts from the prod tag.
- **Must become**: `release plan --type patch`, with the precondition "`hotfix/*` or `release/*` branch" in the CLI.
- **Verification criterion**: `scripts/hotfix.mjs` removed; `SKILL.md` no longer cites it; `release plan --type patch` outside `hotfix/*` exits with a code ≠ 0.

### [SPLIT] [P2] Repo instruction file — `CLAUDE.md`
- **Does today**: 111 lines loaded in every session: commands, stack, architecture, conventions, example, style, tests, release process, troubleshooting.
- **Problem**: the "well-formed service" example uses the field injection forbidden three sections above (evidence: `CLAUDE.md:51` vs `CLAUDE.md:74-75`) and the real code reproduces it (`InvoiceService.java:10-11`) — a mistake in an example is copied faithfully; the Release section (`CLAUDE.md:95-101`) duplicates `SKILL.md` with the same reading of `SUCCESS` (`CLAUDE.md:98`) and an inaccurate description of the version computation (`CLAUDE.md:97`); 45 % of reference and 26 % of noise for 29 % of instruction; dead references (`CLAUDE.md:9`, `CLAUDE.md:12`, `CLAUDE.md:33-37`, `CLAUDE.md:42`); two mandatory rules without a guardrail (`CLAUDE.md:57`, `CLAUDE.md:63`); no maintenance clause and no working process.
- **Must become**: ≈40 lines — rules with their why and the guardrail that carries them, working process (when to stop and ask, criterion of done, flaky test), one line pointing to `.claude/skills/release/SKILL.md`; reference (Build, Stack, Troubleshooting, Packages) moved out into `docs/dev.md` loaded on demand; example fixed; clause "a rule born from a review comment enters this file in the same PR; a rule with no violation for six months leaves it".
- **Verification criterion**: the example complies with the rule it illustrates; every command and path cited exists in the repository; Release section = one line; share of reference < 30 %; maintenance clause present.

### [KEEP] CI workflow — `.github/workflows/ci.yml`
Healthy L4 gate (Checkstyle main+test then the full suite, ArchUnit included, on push to `develop`/`main` and on PRs, `ci.yml:3-14`); it becomes the source read by `release plan`.

### [KEEP] Checkstyle — `config/checkstyle/checkstyle.xml`
Carries four rules of `CLAUDE.md` (`checkstyle.xml:4-9`); as P3, add `CustomImportOrder`, `TypeName`, `MemberName` so that the Code Style section becomes a one-line pointer.

### [KEEP] ArchUnit — `src/test/java/com/acme/billing/ArchitectureTest.java`
Exemplary guardrail — the javadoc cites the CLAUDE.md rule it carries (`ArchitectureTest.java:12-16`); this is where "constructor injection" and "no `@MockBean` in a unit test" must land.

### [KEEP] Gradle build + VERSION — `build.gradle`
Wires Checkstyle and ArchUnit and makes `VERSION` the source of truth (`build.gradle:9`, `build.gradle:21-27`); the overwriting of `-Pversion` is resolved on the CLI/workflow side (commit `VERSION`), not here.

## 5. Remediation plan

| Order | Priority | Verdict | Item | Action | Depends on | Verification | Human approval required |
|---|---|---|---|---|---|---|---|
| 1 | P1 | BLOCK | `scripts/old-deploy.sh` | Remove the script (at least drop the executable bit and take it out of the repository). | — | File absent; `grep -r prod.acme.io` returns only `release.yml`. | Yes |
| 2 | P1 | SPLIT | `.github/workflows/release.yml` | Jobs `publish` + `deploy-prod` (`environment: production`, reviewers), `dry_run` input, regex validation + tag does not exist, `./gradlew test` step, `concurrency`, `permissions: contents: write`, outputs, removal of `hotfix` and of `echo SUCCESS`, `-Pversion` dropped. | — | `dry_run=true`: neither push nor SSH; real dispatch: waiting for approval; invalid or tagged version: failure before the build. | Yes |
| 3 | P1 | SPLIT | `scripts/release.mjs` → `release` CLI | Create `release plan --type … [--dry-run]` (preconditions exit 1, JSON plan) and `release run --plan` (bump + commit of VERSION, trigger, URL + conclusion), with unit tests. | 2 | `plan --dry-run` triggers nothing and fails on a develop that is red/behind; `run` refuses without a plan; tests green in CI. | No |
| 4 | P2 | MERGE | `scripts/hotfix.mjs` | Remove `release.mjs` and `hotfix.mjs`; the hotfix becomes `plan --type patch` with a branch precondition. | 3 | Both `.mjs` absent; `plan --type patch` outside `hotfix/*` exits with a code ≠ 0. | Yes |
| 5 | P1 | PUSH_DOWN | `.claude/skills/release/SKILL.md` | Rewrite: `plan` → human agreement → `run` → reading `conclusion`; keep the abort cases and the announcement; drop the Actions tab, the prod dump, the log grep. | 3 | No manual check and no log reading; explicit confirmation before `run`. | No |
| 6 | P2 | PUSH_DOWN | `CLAUDE.md:51` (injection) | ArchUnit rule `noFields().should().beAnnotatedWith(Autowired.class)`; fix `InvoiceService.java` and the example `CLAUDE.md:70-81`. | — | Putting an `@Autowired` back on a field makes `ArchitectureTest` fail. | No |
| 7 | P2 | PUSH_DOWN | `CLAUDE.md:57` (authorization) | Generic test on `RequestMappingHandlerMapping` (`@WithMockUser(roles="NONE")` → 401/403) + explicit Spring Security configuration; the rule points to the test. | — | A new endpoint without a security rule makes CI fail. | No |
| 8 | P2 | PUSH_DOWN | `CLAUDE.md:63` (migrations) | CI step "immutable migrations" (diff `db/migration/V*` M/D against the target branch → exit 1) or a Testcontainers test `migrate` + `validate`. | — | A PR modifying `V1__init.sql` is red. | No |
| 9 | P2 | SPLIT | `CLAUDE.md` | Reduce to ≈40 lines; move the reference out into `docs/dev.md`; remove the dead references; Release section = pointer to the skill; maintenance clause; working process. | 5, 6, 7, 8 | Every path/command exists; reference < 30 %; clause present. | No |
| 10 | P3 | KEEP | `config/checkstyle/checkstyle.xml` | Add `CustomImportOrder`, `TypeName`, `MemberName`, `ParameterName`; drop `CLAUDE.md:65-66, 85` in favour of "Checkstyle is authoritative". | — | `checkstyleMain` fails on a badly grouped import or a badly named class. | No |
| 11 | P3 | KEEP | `.github/workflows/release.yml` | `gh release create v${version} --generate-notes` in `publish` to produce the list of PRs (`SKILL.md:22`) in L4. | 2 | Every tag has a GitHub Release; the skill points to its URL. | No |

## 6. What the audit could not verify

- Files referenced but absent from the repository: `gradlew` (`CLAUDE.md:6`, `ci.yml:13`), `Dockerfile` (`release.yml:24`, `old-deploy.sh:5`), docker compose file (`CLAUDE.md:12`), `gradle.properties` (`CLAUDE.md:109`). Neither Checkstyle, nor ArchUnit, nor the scripts were run: static analysis only.
- GitHub settings not readable from the repository: protected `production` environment, branch protection on `develop`, default permissions of the `GITHUB_TOKEN` (the `git push origin v…` of `release.yml:27` may fail in read-only), presence of the secrets `REGISTRY_PASSWORD` / `PROD_SSH_KEY`.
- The overwriting of `-Pversion` by `build.gradle:9` is inferred from Gradle semantics, not run.
- The packages `customer` / `payment` / `config` / `security` and the `dto/` folder (`CLAUDE.md:33-42`) do not exist in `src/`: documentation drift or truncated fixture, not settled.
- Testcontainers announced (`CLAUDE.md:17`) but absent from `build.gradle`; no `*IT` test.
- No agent, `.claude/settings.json`, hook or `.cursor/rules` found: assumed not to exist (hence no tool restriction on `ssh` or `gh workflow run`).
- `README.md:3` points to `../traps.md`, out of scope: deliberately not consulted (blind evaluation).

## 7. Machine data

```json
{
  "audit": {
    "process": "Release / production deployment of billing-api + AI instrumentation (CLAUDE.md, release skill)",
    "scope": "fixtures/repos/java-back/repo (CLAUDE.md, .claude/skills, scripts/, .github/workflows, config/checkstyle, src/test ArchUnit)",
    "date": "2026-11-09",
    "health_score": 0,
    "cut_the_agent_test": { "passed": false, "leaked_steps": 4 }
  },
  "elements": [
    {
      "id": "release-skill",
      "path": ".claude/skills/release/SKILL.md",
      "declared_layer": "L2",
      "actual_layer": "MIXED",
      "called_by": ["claude-md"],
      "calls": ["release-mjs", "hotfix-mjs", "release-yml", "ci-yml"],
      "verdict": "PUSH_DOWN",
      "priority": "P1",
      "finding": "The three release preconditions (develop CI green, Flyway migrations aligned with prod, develop up to date) and the detection of success (grep SUCCESS/ERROR in the logs) live only in the prompt; the trigger of the prod deploy (step 4) has no human stopping point and no dry-run.",
      "evidence": [".claude/skills/release/SKILL.md:9", ".claude/skills/release/SKILL.md:10", ".claude/skills/release/SKILL.md:11", ".claude/skills/release/SKILL.md:14", ".claude/skills/release/SKILL.md:15", ".claude/skills/release/SKILL.md:16"],
      "target": "Pure L2 skill: vocabulary, sequence `release plan` → human validation → `release run`, reading a JSON return (run url, conclusion), abort cases; the preconditions move down into the CLI subcommand `release plan` (exit 1) and into release.yml.",
      "check": "SKILL.md no longer contains any manual check (Actions tab, prod dump, log grep); every step points to a subcommand or a workflow, and a step \"ask for confirmation before `release run`\" is explicit."
    },
    {
      "id": "release-mjs",
      "path": "scripts/release.mjs",
      "declared_layer": "L3",
      "actual_layer": "MIXED",
      "called_by": ["release-skill", "claude-md"],
      "calls": ["release-yml", "build-gradle"],
      "verdict": "SPLIT",
      "priority": "P1",
      "finding": "Mix of hardcoded L1 judgment (kind of version inferred from the branch name: develop = always minor, feat/breaking-* = major deployed to prod), L3 logic with no precondition and no test, and an immediate L4 trigger with no dry-run and no confirmation; VERSION is never incremented so the next release recomputes the same version and the tag push fails after overwriting the image.",
      "evidence": ["scripts/release.mjs:11", "scripts/release.mjs:12", "scripts/release.mjs:15", "scripts/release.mjs:16", "scripts/release.mjs:23", "scripts/release.mjs:7", "VERSION:1", ".github/workflows/release.yml:27"],
      "target": "A tested CLI `release`: `release plan --type major|minor|patch [--dry-run]` (checks CI green, tree clean and up to date, tag does not exist, computes the version, outputs JSON) and `release run --plan <file>` (triggers the workflow, commits VERSION, returns the run URL); the kind of version is chosen by the human/agent (L1), not by the branch prefix.",
      "check": "`release plan --type minor --dry-run` outputs JSON without triggering anything and exits with a code ≠ 0 if develop is red or behind; unit tests on the version computation and the preconditions; `scripts/release.mjs` removed."
    },
    {
      "id": "release-yml",
      "path": ".github/workflows/release.yml",
      "declared_layer": "L4",
      "actual_layer": "L4",
      "called_by": ["release-mjs", "hotfix-mjs"],
      "calls": ["build-gradle"],
      "verdict": "SPLIT",
      "priority": "P1",
      "finding": "workflow_dispatch that builds, publishes, tags and deploys to prod in a single job, with no protected `environment`, no `dry_run` input, no validation of the version format or of the tag, no concurrency, accepting any `ref`; the `hotfix` input is declared but never used; the success signal is an `echo SUCCESS`; `-Pversion` is overwritten by build.gradle, which re-reads VERSION.",
      "evidence": [".github/workflows/release.yml:3", ".github/workflows/release.yml:8", ".github/workflows/release.yml:11", ".github/workflows/release.yml:16", ".github/workflows/release.yml:23", ".github/workflows/release.yml:27", ".github/workflows/release.yml:28", ".github/workflows/release.yml:32", "build.gradle:9"],
      "target": "Two jobs: `publish` (regex validation x.y.z + tag does not exist, tests, bootJar, image, tag) then `deploy-prod` with `environment: production` and mandatory reviewers, a `dry_run` input that stops after the plan, `concurrency` per environment, explicit `permissions: contents: write`, structured outputs (version, image, run url) and removal of the `hotfix` input or a real use of it.",
      "check": "A dispatch with `dry_run=true` touches neither the registry nor prod; a real dispatch stays waiting for approval on the `production` environment; a `version` that is not semver or already tagged makes the job fail before the build."
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
      "finding": "Dead script (the comment says so) but still executable: it builds, pushes and deploys to prod over SSH from a workstation, short-circuiting release.yml, the tests, the tag and any stopping point; no hook or settings.json prevents an agent from running it.",
      "evidence": ["scripts/old-deploy.sh:2", "scripts/old-deploy.sh:5", "scripts/old-deploy.sh:7"],
      "target": "Removed from the repository; the only path to prod is the `deploy-prod` job of release.yml.",
      "check": "`scripts/old-deploy.sh` absent; grep `ssh .*prod.acme.io` matches only release.yml."
    },
    {
      "id": "hotfix-mjs",
      "path": "scripts/hotfix.mjs",
      "declared_layer": "L3",
      "actual_layer": "L3",
      "called_by": ["release-skill", "claude-md"],
      "calls": ["release-yml", "build-gradle"],
      "verdict": "MERGE",
      "priority": "P2",
      "finding": "Duplicates release.mjs (reading VERSION, parsing, computation, `gh workflow run`) with a single variation (patch); the `hotfix=true` input it passes is read nowhere in release.yml, so a hotfix is strictly identical to a release; same lack of dry-run and of confirmation.",
      "evidence": ["scripts/hotfix.mjs:11", "scripts/hotfix.mjs:12", "scripts/hotfix.mjs:13", "scripts/hotfix.mjs:16", ".github/workflows/release.yml:11"],
      "target": "Absorbed by `release plan --type patch`; the check \"starts from a hotfix/* branch\" becomes a precondition of the CLI when `--type patch` is asked outside a prod tag.",
      "check": "`scripts/hotfix.mjs` removed; SKILL.md no longer mentions it; `release plan --type patch` fails (exit ≠ 0) outside a hotfix/* or release/* branch."
    },
    {
      "id": "claude-md",
      "path": "CLAUDE.md",
      "declared_layer": "L2",
      "actual_layer": "MIXED",
      "called_by": [],
      "calls": ["release-skill", "release-mjs", "hotfix-mjs", "ci-yml", "release-yml", "checkstyle-xml", "architecture-test"],
      "verdict": "SPLIT",
      "priority": "P2",
      "finding": "Mix of instruction (29 %), reference (45 %) and noise (26 %); the \"well-formed service\" example uses the field injection that the rule just above forbids (and the real code copies it); the \"Release process\" section duplicates SKILL.md with the same grep of SUCCESS; dead references (InvoiceServiceTest, docker compose, packages customer/payment/config/security, dto folder); no maintenance clause.",
      "evidence": ["CLAUDE.md:51", "CLAUDE.md:74", "CLAUDE.md:75", "src/main/java/com/acme/billing/invoice/InvoiceService.java:10", "CLAUDE.md:95", "CLAUDE.md:98", "CLAUDE.md:9", "CLAUDE.md:12", "CLAUDE.md:34", "CLAUDE.md:42", "CLAUDE.md:103"],
      "target": "A short CLAUDE.md (≈40 lines): rules with their why and the guardrail that carries them, working process, a pointer to the release skill; reference (commands, troubleshooting, stack) moved out into `docs/` loaded on demand; example fixed to constructor injection; clause \"any rule added in review goes into this file in the same PR, any rule with no violation for 6 months is removed\".",
      "check": "Service example complying with the rule it illustrates; no command or path cited is absent from the repository; Release section reduced to one line pointing to `.claude/skills/release/SKILL.md`; share of reference < 30 %."
    },
    {
      "id": "ci-yml",
      "path": ".github/workflows/ci.yml",
      "declared_layer": "L4",
      "actual_layer": "L4",
      "called_by": [],
      "calls": ["checkstyle-xml", "architecture-test", "build-gradle"],
      "verdict": "KEEP",
      "priority": null,
      "finding": "Healthy L4 gate: Checkstyle main+test and test suite (ArchUnit included) on push to develop/main and on PRs; it is the guardrail of \"run the full suite before a PR\".",
      "evidence": [".github/workflows/ci.yml:3", ".github/workflows/ci.yml:5", ".github/workflows/ci.yml:13", ".github/workflows/ci.yml:14"],
      "target": "Unchanged; its result becomes the source read by `release plan` (conclusion of the last run on develop).",
      "check": "`release plan` reads the conclusion of ci.yml via `gh run list --workflow ci.yml --branch develop --json conclusion`."
    },
    {
      "id": "checkstyle-xml",
      "path": "config/checkstyle/checkstyle.xml",
      "declared_layer": "L3",
      "actual_layer": "L3",
      "called_by": ["ci-yml", "build-gradle"],
      "calls": [],
      "verdict": "KEEP",
      "priority": null,
      "finding": "Carries four rules of CLAUDE.md (length 120, no import *, one public class per file, naming of constants/methods); desirable P3 extension: ImportOrder/CustomImportOrder, TypeName, MemberName to cover the rest of the Naming/Code Style section.",
      "evidence": ["config/checkstyle/checkstyle.xml:4", "config/checkstyle/checkstyle.xml:6", "config/checkstyle/checkstyle.xml:7", "config/checkstyle/checkstyle.xml:8", "config/checkstyle/checkstyle.xml:9"],
      "target": "Unchanged in its role; the missing modules added so that the Code Style section of CLAUDE.md becomes a one-line pointer.",
      "check": "An import not grouped java/javax/org/com or a class in camelCase makes `./gradlew checkstyleMain` fail."
    },
    {
      "id": "architecture-test",
      "path": "src/test/java/com/acme/billing/ArchitectureTest.java",
      "declared_layer": "L3",
      "actual_layer": "L3",
      "called_by": ["ci-yml"],
      "calls": [],
      "verdict": "KEEP",
      "priority": null,
      "finding": "Exemplary guardrail of \"no repository in controllers\": the javadoc cites the CLAUDE.md rule it carries; it is the right place to host the rule \"constructor injection\" and \"no @MockBean in a unit test\".",
      "evidence": ["src/test/java/com/acme/billing/ArchitectureTest.java:12", "src/test/java/com/acme/billing/ArchitectureTest.java:14"],
      "target": "Unchanged; hosts the new ArchUnit rules coming from the PUSH_DOWN of CLAUDE.md.",
      "check": "Each ArchUnit rule cites the CLAUDE.md line it guards, and each mandatory rule of CLAUDE.md points to its test."
    },
    {
      "id": "build-gradle",
      "path": "build.gradle",
      "declared_layer": "L3",
      "actual_layer": "L3",
      "called_by": ["ci-yml", "release-yml", "release-mjs", "hotfix-mjs"],
      "calls": ["checkstyle-xml"],
      "verdict": "KEEP",
      "priority": null,
      "finding": "Wires Checkstyle and ArchUnit and makes VERSION the source of truth of the version; this assignment overwrites the `-Pversion` passed by release.yml, an inconsistency to resolve on the workflow/CLI side (commit VERSION) rather than here.",
      "evidence": ["build.gradle:9", "build.gradle:21", "build.gradle:24", ".github/workflows/release.yml:23"],
      "target": "Unchanged; the CLI `release run` commits VERSION on the ref before triggering the workflow, and release.yml stops passing `-Pversion`.",
      "check": "The jar produced by release.yml carries the tagged version (`ls build/libs` in the job)."
    }
  ],
  "process_leaks": [
    { "rule": "Never release if the CI of develop is not green", "told_in": ".claude/skills/release/SKILL.md:9 ; CLAUDE.md:96", "if_skipped": "An image built on a red develop (tests or Checkstyle failing) goes to prod: release.yml does not re-run the tests and does not read the status of ci.yml", "belongs_in": "L3", "guard_tool": "Subcommand `release plan`: `gh run list --workflow ci.yml --branch develop --json conclusion` → exit 1 if ≠ success; doubled by a `./gradlew test` step in the publish job of release.yml (L4)" },
    { "rule": "Check that no Flyway migration is left unapplied in prod before releasing", "told_in": ".claude/skills/release/SKILL.md:10", "if_skipped": "Unexpected migration or FlywayValidateException when the container starts in prod, discovered after `docker compose up -d`; the step also asks the owner for a dump of the prod database", "belongs_in": "L4", "guard_tool": "`flyway info`/`flyway validate` step (or `./gradlew flywayInfo`) against the prod database in the deploy-prod job, before the `docker pull`, with exit ≠ 0 on an unexpected state" },
    { "rule": "Be on an up-to-date develop (checkout + pull) before running the release", "told_in": ".claude/skills/release/SKILL.md:11", "if_skipped": "release.mjs checks only the name of the branch: a local develop that is behind or a dirty tree produces a `ref` and a VERSION that do not match what will be deployed", "belongs_in": "L3", "guard_tool": "`release plan`: `git fetch` then exit 1 if `git status -sb` shows behind/ahead or a tree that is not clean" },
    { "rule": "The release succeeded when the output of the workflow contains SUCCESS; on ERROR/FAILED warn and do not run again", "told_in": ".claude/skills/release/SKILL.md:15 ; .claude/skills/release/SKILL.md:16 ; CLAUDE.md:98", "if_skipped": "Hallucinated or missed success: `gh workflow run` returns no run id, the SUCCESS is a plain `echo` (release.yml:32) and a partly failed run (image pushed, tag failed) cannot be told apart", "belongs_in": "L3", "guard_tool": "`release run` returns the run URL and waits for `gh run view <id> --json conclusion,jobs`; release.yml exposes outputs (version, image, step reached)" },
    { "rule": "Human stopping point between the release plan and the deployment to production", "told_in": ".claude/skills/release/SKILL.md:14 (absent: step 4 triggers directly)", "if_skipped": "An agent or a `node scripts/release.mjs` run by mistake deploys to prod with no dry-run and no validation; no protection on the workflow side", "belongs_in": "L4", "guard_tool": "`environment: production` with required reviewers on the deploy-prod job + `dry_run` input; on the L3 side, `release plan --dry-run` by default and `release run` that requires the plan" },
    { "rule": "Constructor injection, never field injection", "told_in": "CLAUDE.md:51", "if_skipped": "Hidden dependencies, services that cannot be unit-tested; already broken by InvoiceService.java:10 and by the example of CLAUDE.md:74", "belongs_in": "L3", "guard_tool": "ArchUnit rule in ArchitectureTest: `noFields().should().beAnnotatedWith(Autowired.class)` (+ `noMethods()` @Autowired setters)" },
    { "rule": "Every endpoint has an authorization test (wrong role → 403)", "told_in": "CLAUDE.md:57", "if_skipped": "A billing endpoint exposed with no role check passes CI; InvoiceControllerTest.java:8 records that no 403 test exists", "belongs_in": "L3", "guard_tool": "JUnit test parameterised on `RequestMappingHandlerMapping`: for each mapping, a request with `@WithMockUser(roles=\"NONE\")` must answer 401/403; fails when an endpoint is added without a security rule" },
    { "rule": "Never modify a Flyway migration already applied", "told_in": "CLAUDE.md:63", "if_skipped": "Detected only at startup in prod (FlywayValidateException, CLAUDE.md:104), that is, after the deployment", "belongs_in": "L3", "guard_tool": "CI check as a PR gate: `migrations check` script comparing the checksums of `src/main/resources/db/migration/V*` with the target branch (`git diff --name-status origin/develop -- db/migration` → exit 1 on M/D), or a Testcontainers test `flyway migrate` + `validate`" }
  ],
  "guarded_rules": [
    { "rule": "No business logic and no repository access in controllers", "told_in": "CLAUDE.md:27 ; CLAUDE.md:54", "guarded_by": "src/test/java/com/acme/billing/ArchitectureTest.java:14" },
    { "rule": "Max line length 120", "told_in": "CLAUDE.md:84", "guarded_by": "config/checkstyle/checkstyle.xml:4" },
    { "rule": "No wildcard import", "told_in": "CLAUDE.md:85", "guarded_by": "config/checkstyle/checkstyle.xml:6" },
    { "rule": "One public class per file", "told_in": "CLAUDE.md:68", "guarded_by": "config/checkstyle/checkstyle.xml:7" },
    { "rule": "Constants in UPPER_SNAKE_CASE, methods in camelCase (partial: no TypeName/MemberName)", "told_in": "CLAUDE.md:66", "guarded_by": "config/checkstyle/checkstyle.xml:8" },
    { "rule": "Full suite + Checkstyle before any PR / on every push", "told_in": "CLAUDE.md:93 ; CLAUDE.md:45", "guarded_by": ".github/workflows/ci.yml:13" },
    { "rule": "A hotfix starts from a hotfix/* branch", "told_in": ".claude/skills/release/SKILL.md:19", "guarded_by": "scripts/hotfix.mjs:7" },
    { "rule": "A release starts from develop, release/* or feat/breaking-* (debatable scope)", "told_in": "CLAUDE.md:97", "guarded_by": "scripts/release.mjs:17" }
  ],
  "instruction_files": [
    { "path": "CLAUDE.md", "loaded_lines": 111, "instruction_pct": 29, "reference_pct": 45, "noise_pct": 26, "justified_rules": false, "maintenance_clause": false },
    { "path": ".claude/skills/release/SKILL.md", "loaded_lines": 22, "instruction_pct": 100, "reference_pct": 0, "noise_pct": 0, "justified_rules": false, "maintenance_clause": false }
  ],
  "remediation": [
    { "order": 1, "priority": "P1", "verdict": "BLOCK", "element": "old-deploy-sh", "action": "Remove scripts/old-deploy.sh (or at least drop the executable bit and move it out of the repository); no other SSH path to prod.acme.io outside release.yml.", "depends_on": [], "check": "The file is absent; `grep -r prod.acme.io` returns only release.yml.", "needs_human_approval": true },
    { "order": 2, "priority": "P1", "verdict": "SPLIT", "element": "release-yml", "action": "Rework release.yml: jobs `publish` and `deploy-prod` (environment: production, required reviewers), `dry_run` input, regex validation x.y.z + `git ls-remote --tags` empty, `./gradlew test` step, `concurrency: release-prod`, `permissions: contents: write`, outputs version/image/run, removal of the unused `hotfix` input and of the `echo SUCCESS`, `-Pversion` dropped in favour of the committed VERSION file.", "depends_on": [], "check": "Dispatch `dry_run=true`: no registry push, no ssh; real dispatch: deploy-prod job waiting for approval; version `abc` or already tagged: failure before the build.", "needs_human_approval": true },
    { "order": 3, "priority": "P1", "verdict": "SPLIT", "element": "release-mjs", "action": "Create a tested CLI (e.g. `tools/release/` or `npm run release -- plan|run`): `plan --type major|minor|patch [--dry-run]` checks CI green, tree clean/up to date, tag does not exist, computes the version and writes a JSON plan; `run --plan` bumps + commits VERSION, triggers release.yml and returns the run URL + conclusion; unit tests of the version computation and of the preconditions.", "depends_on": [2], "check": "`plan --dry-run` triggers nothing and exits 1 on a develop that is red/behind; `run` refuses without a plan; tests green in CI.", "needs_human_approval": false },
    { "order": 4, "priority": "P2", "verdict": "MERGE", "element": "hotfix-mjs", "action": "Remove scripts/release.mjs and scripts/hotfix.mjs once the CLI is in place; the hotfix case becomes `plan --type patch` with the precondition \"hotfix/* or release/* branch\".", "depends_on": [3], "check": "Both .mjs are absent; `plan --type patch` outside hotfix/* exits with a code ≠ 0.", "needs_human_approval": true },
    { "order": 5, "priority": "P1", "verdict": "PUSH_DOWN", "element": "release-skill", "action": "Rewrite SKILL.md: sequence `plan` → show the JSON plan to the human and wait for their agreement → `run` → read `conclusion`; keep the abort cases (failure = warn, do not run again) and the #releases announcement; drop the Actions tab, the prod dump and the SUCCESS/ERROR grep.", "depends_on": [3], "check": "No manual check and no log reading in SKILL.md; an explicit confirmation step comes before `run`.", "needs_human_approval": false },
    { "order": 6, "priority": "P2", "verdict": "PUSH_DOWN", "element": "claude-md", "action": "Add to ArchitectureTest the rule `noFields().should().beAnnotatedWith(Autowired.class)` and fix InvoiceService.java to constructor injection; fix the example CLAUDE.md:70-81.", "depends_on": [], "check": "`./gradlew test --tests ArchitectureTest` fails if an `@Autowired` is put back on a field; the example of CLAUDE.md complies with the rule.", "needs_human_approval": false },
    { "order": 7, "priority": "P2", "verdict": "PUSH_DOWN", "element": "claude-md", "action": "Add a generic authorization test (iteration over RequestMappingHandlerMapping, `@WithMockUser(roles=\"NONE\")` → 401/403) and an explicit Spring Security configuration; replace CLAUDE.md:57 with a pointer to this test.", "depends_on": [], "check": "Adding a `@GetMapping` without a security rule makes CI fail.", "needs_human_approval": false },
    { "order": 8, "priority": "P2", "verdict": "PUSH_DOWN", "element": "claude-md", "action": "Add a CI step \"immutable migrations\" (diff of the `db/migration/V*` files modified/deleted against the target branch → exit 1) or a Testcontainers test `flyway validate`; CLAUDE.md:63 points to this gate.", "depends_on": [], "check": "A PR that modifies V1__init.sql is red in CI.", "needs_human_approval": false },
    { "order": 9, "priority": "P2", "verdict": "SPLIT", "element": "claude-md", "action": "Reduce CLAUDE.md to ≈40 lines: rules + why + guardrail, working process (when to stop, criterion of done), one line pointing to the release skill; move Build/Stack/Troubleshooting/Package structure out into `docs/dev.md`; remove the dead references (InvoiceServiceTest, docker compose, packages that do not exist, dto folder); add the maintenance clause.", "depends_on": [5, 6, 7, 8], "check": "Every command and path cited exists; share of reference < 30 %; maintenance clause present; Release section = 1 line.", "needs_human_approval": false },
    { "order": 10, "priority": "P3", "verdict": "KEEP", "element": "checkstyle-xml", "action": "Add CustomImportOrder (java/javax/org/com), TypeName, MemberName, ParameterName; remove lines 65-66 and 85 from CLAUDE.md in favour of a pointer \"Checkstyle is authoritative\".", "depends_on": [], "check": "`./gradlew checkstyleMain` fails on a badly grouped import or a badly named class.", "needs_human_approval": false },
    { "order": 11, "priority": "P3", "verdict": "KEEP", "element": "release-yml", "action": "Add `gh release create v${version} --generate-notes` to the publish job so that the \"list of PRs included\" (SKILL.md:22) is produced by L4 and not rebuilt by the agent.", "depends_on": [2], "check": "Every tag has a GitHub Release with generated notes; the skill points to its URL for the announcement.", "needs_human_approval": false }
  ],
  "unverified": [
    "Files referenced but absent from the repository: `gradlew` (CLAUDE.md:6, ci.yml:13), `Dockerfile` (release.yml:24, old-deploy.sh:5), docker compose file (CLAUDE.md:12), `gradle.properties` (CLAUDE.md:109); neither Checkstyle, nor ArchUnit, nor the CLI could be run — the analysis is static.",
    "GitHub settings not readable from the repository: existence of a protected `production` environment, branch protection on develop, default permissions of the GITHUB_TOKEN (the `git push origin v…` of release.yml:27 may fail in read-only), secrets REGISTRY_PASSWORD / PROD_SSH_KEY.",
    "Gradle behaviour `-Pversion` overwritten by `build.gradle:9` inferred from Gradle semantics, not run.",
    "The packages customer/payment/config/security and the dto folder described in CLAUDE.md:33-42 do not exist in src/: documentation drift or truncated fixture, not settled.",
    "Testcontainers dependency announced (CLAUDE.md:17) absent from build.gradle; no `*IT` test in the repository.",
    "No agent, `.claude/settings.json`, hook or `.cursor/rules` found: assumed not to exist (hence no tool restriction on `ssh` or `gh workflow run`).",
    "README.md:3 points to `../traps.md`, out of scope: deliberately not consulted (blind evaluation)."
  ]
}
```
