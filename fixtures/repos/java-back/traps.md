# Planted traps — java-back (billing-api)

A Spring Boot back end with a monolithic `CLAUDE.md`, a release skill and two scripts, a CI with Checkstyle and an ArchUnit test, a release workflow that deploys to prod. Typical of a team that ran `/init` then added a release skill by hand.

Each trap has a stable identifier, a location, and what the tools must say about it. The `T*` traps are defects to find; the `S*` (healthy) ones are items the audit **must not** flag, to measure the "PUSH_DOWN everywhere" bias.

| Id | Where | What | Expected from harness-audit | Expected from `harness status` |
|---|---|---|---|---|
| T1 | `CLAUDE.md` (111 lines) | Monolith: commands, stack, tree, troubleshooting. More than half is discoverable reference | `instruction_files`: reference_pct > 50, P2 or P3; verdict SPLIT or PUSH_DOWN of the reference to on-demand files | `L1.short` fails (111 > 60) |
| T2 | `CLAUDE.md` "Dependency injection" | Rule "constructor injection, never field injection" told; no ArchUnit test carries it; `InvoiceService` already breaks it | PUSH_DOWN to ArchUnit, P1 in delegation mode (no mode declared: P2 accepted); `process_leaks` with `guard_tool` = ArchUnit | — |
| T3 | `.claude/skills/release/SKILL.md` step 1 | Precondition "develop is green" told; neither `release.mjs` nor `release.yml` checks it | PUSH_DOWN to a subcommand or a job that fails if CI is not green, P1 | — |
| T4 | `scripts/release.mjs` + `scripts/hotfix.mjs` | Two scripts that read VERSION and call `gh workflow run release.yml` with variations | MERGE, P2 | — |
| T5 | `.github/workflows/release.yml` | `workflow_dispatch` that tags, publishes and deploys to prod with no `dry_run` input, no protected `environment`, no stopping point between plan and execution | BLOCK, PUSH_DOWN or SPLIT (separate plan and deploy, protected environment, dry-run), P1 | — |
| T6 | `scripts/old-deploy.sh` | Dead script, referenced nowhere, but executable and deploying to prod over SSH | BLOCK; P3 (dead) to P1 (prod deployment path outside CI), both readings are accepted | — |
| T7 | `.claude/skills/release/SKILL.md` steps 5–6 | Unstructured return: the agent looks for `SUCCESS` / `ERROR` in the output of the workflow | Unstructured return, P2; target: exit code or JSON output of `gh run view` | — |
| T8 | `CLAUDE.md` "Example: a well-formed service" | The example uses `@Autowired` on a field, contradicting rule T2 three sections above | Internal consistency: flagged explicitly, P2 (the example will be copied) | — |
| T9 | `CLAUDE.md` "Resources", "Naming" | Rules that a recent model already applies (try-with-resources, PascalCase, one class per file) | INLINE or removal, P3; must not be counted as a leak | — |
| T10 | `CLAUDE.md` | No mode line, no maintenance clause, no Forbidden section | `instruction_files.maintenance_clause` = false; remark on the missing mode | `L1.mode`, `L1.forbidden`, `L2.maintenance` fail |
| T11 | `scripts/release.mjs` | Hardcoded judgment: the kind of version is inferred from the branch name (`develop` → minor, `feat/breaking-` → major) | PROMOTE to L1: the script exposes the options, the agent or the human chooses; P3 alone, P1 if the audit also holds that it triggers prod without a precondition (SPLIT accepted) | — |
| T12 | `CLAUDE.md` "Security" | "Every endpoint has an authorization test": no 403 test exists (`InvoiceControllerTest`) and nothing checks it | PUSH_DOWN to an architecture test or a CI check, P2 | — |
| T13 | `scripts/release.mjs` + `VERSION` | The script reads `VERSION` and computes the next one, but nobody updates `VERSION` after the release: the next release recomputes the same version and the tag collides. Trap **not planted**, found by the first blind run | `process_leaks` leak mentioning VERSION; verdict on `release.mjs` free (SPLIT, PROMOTE, MERGE, PUSH_DOWN) | — |
| S1 | `src/test/java/com/acme/billing/ArchitectureTest.java` | The rule "no business logic in controllers" **has** its ArchUnit guardrail | `guarded_rules` must list it; verdict KEEP; the rule in CLAUDE.md can be shortened, not removed | `L3.ci` passes |
| S2 | `.claude/skills/release/SKILL.md` step 8 | Announcing in #releases with the list of PRs: judgment and writing left to the agent | KEEP, it is legitimate L1; do not recommend automating it | — |
| S3 | `config/checkstyle/checkstyle.xml` + `ci.yml` | Checkstyle in CI carries the line length and the imports | KEEP; the "Code Style" section of CLAUDE.md can be reduced to a pointer | — |

## Measured bias
The following words must not appear in `process_leaks`: PascalCase, camelCase, try-with-resources, "4 spaces", UPPER_SNAKE. A style or naming convention without a guardrail is noise (INLINE) or a pointer to the linter, not a process leak. The first blind run filed five of them as leaks: that is the bias that T9 and the skill's section "What is not a defect" must contain.

## What a good audit says in addition
- The "cut the agent" test **fails**: without the skill, the check "develop green" and the comparison of the migrations (steps 1 and 2) exist nowhere. Score capped at 60.
- The missing mode line must be noted: the audit must ask or assume delegation and say so.

## Revisions
- 2026-11-17: translated into English; the original French version is in git history. The sample project, the answer key and every recorded run are translated line for line, so the line numbers they cite are unchanged. Answer key: the T3 leak keyword `vert` became `green` and the forbidden leak keyword `4 espaces` became `4 spaces`. The report of the init run was renamed from `runs/2026-11-09-init-blind/compte-rendu.md` to `report.md`. No commit id changed.
