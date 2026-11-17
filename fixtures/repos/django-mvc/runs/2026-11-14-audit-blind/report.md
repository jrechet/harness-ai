# Harness audit — AI-assisted contribution to Cursus

**Scope**: Cursus repository (AGENTS.md, CLAUDE.md, `.github/workflows/ci.yml`, tests that serve as guardrails, `docs/`) · **Date**: 2026-11-14 · **Items inventoried**: 12

## 1. Summary

- **Health score**: 49 — the agent remains an accelerator for lists and forgotten migrations, but three rules born of incidents hold only by the text, and one of them cites a guardrail that does not exist.
- **Result of the "cut the agent" test**: FAILED — 4 rules or steps of the process exist only in prompts.
- **Blocking points (P1)**: 1
- **The three actions that change things the most**:
  1. Create the CI job `frozen-migrations`. AGENTS.md:58 and CLAUDE.md:20 present it as existing, but `ci.yml` has only one job, `test`.
  2. Close the ways of bypassing `services.enroll()` (add form of the admin, direct writes) and add a `notify` parameter for bulk jobs.
  3. Reduce CLAUDE.md to `@AGENTS.md`. Today, Claude sees neither the incidents nor the bulk sending rule, and CLAUDE.md:18 contradicts it.

Computation: 100 − 25 (1 P1) − 24 (3 P2) − 2 (1 P3) = 49. The cap of 60 tied to the failed test changes nothing.

## 2. Map of the harness

| # | Item | Path | Declared layer | Real layer | Called by | Calls |
|---|---|---|---|---|---|---|
| 1 | AGENTS.md | `AGENTS.md` | L2 | L2 (instruction + reference) | Copilot, Cursor (auto loading) | rules 3–6, docs/ |
| 2 | CLAUDE.md | `CLAUDE.md` | L2 | L2, drifting copy | Claude Code (auto loading) | nothing (no `@AGENTS.md`) |
| 3 | Applied migrations rule | `AGENTS.md:58`, `CLAUDE.md:20` | L4 ("frozen-migrations job") | L2 only | 1, 2 | — |
| 4 | Bulk e-mails rule | `AGENTS.md:56` | L2 | L2 (the signal part is in L3) | 1 | 9 |
| 5 | Capacity rule | `AGENTS.md:57`, `CLAUDE.md:19` | L2 | L2 | 1, 2 | — |
| 6 | Dates rule | `AGENTS.md:61`, `CLAUDE.md:22` | L2 | L2 | 1, 2 | — |
| 7 | CI workflow | `.github/workflows/ci.yml` | L4 | L4 | PR and push on `main` | 8, 9 |
| 8 | Query count test | `catalog/tests/test_queries.py` | L3 | L3 | 7 | — |
| 9 | "save sends nothing" test | `enrollments/tests/test_services.py:106` | L3 | L3 | 7 | — |
| 10 | Postmortems and ADR | `docs/postmortems/`, `docs/adr/` | L2 (reference) | L2 | 1 | — |
| 11 | Operations | `docs/operations.md` | L2 (reference) | L2 | — | — |
| 12 | README | `README.md` | L2 (reference) | L2 | — | — |

No agent, skill, script, hook, Cursor rule or `.harness/` folder existed before the audit.

| Step of the process | Carried by | Verified by code? | Dry-run? |
|---|---|---|---|
| Branch, then PR to `main` | AGENTS.md:66, ci.yml:3-4 | Partly (the CI only triggers towards `main`) | — |
| Model modified → migration committed | ci.yml:18-19 | Yes | Yes (`--check --dry-run`) |
| Do not modify an applied migration | AGENTS.md:58 | **No** | — |
| Tests | ci.yml:21 | Yes | — |
| No query per row in the lists | test_queries.py | Yes | — |
| No e-mail in a signal or in `save()` | test_services.py:106 | Yes | — |
| No e-mail per row in a bulk job | AGENTS.md:56 | **No**, and the rule is already violated | — |
| Enrollment only through `enroll()` | AGENTS.md:57 | **No** (admin open, lock never tested) | — |
| Dates with `timezone.now()` | AGENTS.md:61 | **No** | — |
| Python 3.8 / Django 4.2 compatibility | AGENTS.md:51-52 | No, and contradicted by the code (Q1, Q2) | — |
| Review then merge | human, branch protection | Not verifiable in the repository | — |
| Deployment: automatic `migrate` on merge | host (docs/operations.md:13) | Outside the repository | No, and no rollback |

## 3. Leaks: rules and steps told without verification

1. **Applied migrations** (AGENTS.md:58, CLAUDE.md:20). Both files say "Enforced by the `frozen-migrations` job". This job does not exist: ci.yml:8-21 holds only one job, `test`, which docs/operations.md:27 confirms. **If the agent skips the rule**, the modified migration passes the CI, is merged, then `migrate` does not replay it: production keeps the old schema without any error (docs/operations.md:16-17). Yet the agent believes a net exists. **Target**: L4, a CI job (`git diff --diff-filter=MDR origin/main...HEAD -- '*/migrations/0*.py'` non-empty → `exit 1`).
2. **Bulk e-mails** (AGENTS.md:56, second sentence). Nothing verifies it, and it is already violated: the admin action `cancel_selected` (enrollments/admin.py:18-19) calls `services.cancel()`, which sends one promotion e-mail per row (services.py:66). Moreover, `enroll()` always sends, which has been an open point since postmortem 2024-03:21. **If the agent skips the rule**, the incident of March 2024 happens again: a suspended SMTP account. **Target**: L3, a `notify` parameter on the services and a test of the admin action on `mail.outbox`.
3. **Capacity** (AGENTS.md:57). The add form of `EnrollmentAdmin` allows creating a confirmed enrollment without going through `enroll()` (enrollments/admin.py:7-8, already reported in postmortem 2024-09:19). The lock is never tested, because SQLite ignores `select_for_update` (2024-09:18, settings.py:51-63). **If the agent skips the rule**, the incident of September 2024 happens again: an overbooked session. **Target**: L3, with `has_add_permission=False`, a test that scans the sources and a PostgreSQL job.
4. **Dates** (AGENTS.md:61). No guardrail. A naive date skews `has_started` (catalog/models.py:58-59). **Target**: L3, with ruff DTZ in CI.

Rules that have their guardrail:
- No e-mail in a signal or in `save()` (AGENTS.md:56): enforced by `enrollments/tests/test_services.py:106-112`.
- Migration committed with the model (AGENTS.md:59): enforced by `ci.yml:18-19`. The rule can be reduced to its "Enforced by" line.
- No query per row (AGENTS.md:60): enforced by `catalog/tests/test_queries.py`. It can be reduced, CLAUDE.md:21 already gives the right wording.
- The "services" rule (AGENTS.md:62) is a review convention assumed by ADR 0001:15. It is not a leak.

## 3b. Context cost

| File | Lines loaded (with includes) | Share instruction / reference / noise | Loaded when |
|---|---|---|---|
| AGENTS.md | 67 | ~55 % / ~35 % / ~10 % | Every Copilot or Cursor session (Claude Code does not load it) |
| CLAUDE.md | 24 | ~60 % / ~30 % / ~10 % | Every Claude Code session |

The volume is reasonable. The two rules born of incidents (AGENTS.md:56-57) explain their why and cite their postmortem, it is a real strong point. CLAUDE.md removes all these whys. Neither file says how it evolves.

## 3c. Lines to remove

| File:line | Text | Reason | Evidence | Question to the owner? |
|---|---|---|---|---|
| AGENTS.md:30 | `test --settings=cursus.settings_ci` | harmful | `cursus/settings_ci.py` does not exist; the CI runs `manage.py test` (ci.yml:21) | No |
| AGENTS.md:58 | "Enforced by: the CI job `frozen-migrations`" | harmful | Job absent (ci.yml:8-21). The rule stays, only the mention of the guardrail goes as long as the job does not exist | No |
| CLAUDE.md:20 | "the CI rejects it (job `frozen-migrations`)" | harmful | Same evidence | No |
| AGENTS.md:60 | "open the page with django-debug-toolbar…" | harmful | Tool removed (postmortem 2025-06:14), replaced by test_queries.py | No |
| CLAUDE.md:18 | "every enrollment created sends its confirmation" | harmful | Contradicts AGENTS.md:56 and postmortem 2024-03:17, while CLAUDE.md does not hold the bulk sending rule | No |
| AGENTS.md:3, 36, 37, 44, 46; CLAUDE.md:16 | "Read it in full", "step by step", "do not invent APIs", "clear names", "no print" | useless | Default behaviours or automatic loading | No |
| AGENTS.md:7, 9-24 | Presentation and tree | useless | Already in README.md:3 and :35-41, and visible in the repository | No |
| AGENTS.md:51; CLAUDE.md:17 | Python 3.8 | stale? | `match` (notifications.py:17) and `X \| None` (services.py:47) do not import under 3.8; the CI runs on 3.12 | **Q1** |
| AGENTS.md:52 | Django 4.2 LTS | stale? | requirements.txt:1 asks for 5.1; models.py:48 uses `condition=`, a 5.1 API | **Q2** |
| AGENTS.md:38 | "Always give the complete file…" | stale? | Workaround for a copy-paste chat usage | **Q3** |
| AGENTS.md:43 | "lines of 100 characters at most" | stale? | No linter; lines already exceed 100 characters (services.py:39, views.py:26 and :36, catalog/models.py:38) | **Q6** |

**Questions to the owner**
1. Is the production server still on Python 3.8? The current code does not import there. *Proposed default: no.* AGENTS.md:51 and CLAUDE.md:17 are removed, the real version is stated and `ci.yml` is aligned with it. If the answer is yes, it is a P1: production cannot start this code.
2. Does the host still require an LTS version of Django? 5.1 is not one. *Proposed default: AGENTS.md:52 is removed and requirements.txt is authoritative.* If the requirement holds, move to 5.2 LTS.
3. Does anyone still paste assistant answers from a chat? *Proposed default: no, AGENTS.md:38 is removed.*
4. Is the promotion e-mail sent for each row by `cancel_selected` an intended exception to the decision of 2024-03? *Proposed default: no.* The action saves without notifying, and the training department notifies itself.
5. Must staff be able to add an enrollment from the admin? *Proposed default: no, set `has_add_permission=False`.* Otherwise, the add must go through `enroll()`.
6. Is the 100-character limit still wanted? *Proposed default: yes, with ruff `line-length = 100` in CI.*
7. Does the branch protection of `main` really require the `test` job? *Proposed default: yes. It must be confirmed, then `frozen-migrations` added to it.*

AGENTS.md has 67 lines and would keep about 40 after cleaning. Two lines must absolutely be kept and not shortened: **AGENTS.md:56 and :57** (incidents of March and September 2024).

## 4. Findings per item

### [PUSH_DOWN] [P1] "Applied migrations" rule — AGENTS.md:58
- **Does today**: it announces a CI guardrail.
- **Problem**: the job does not exist (ci.yml:8-21, operations.md:27). As the deployment applies `migrate` on every merge, a modification passes silently (operations.md:13-17). `harness rules` even counts this rule as "with a guardrail", on the strength of the text alone.
- **Must become**: a `frozen-migrations` job in ci.yml, required by the branch protection.
- **Verification criterion**: a PR that modifies `catalog/migrations/0001_initial.py` is red, a PR that adds `0003_*.py` is green.

### [PUSH_DOWN] [P2] "Bulk e-mails" rule — AGENTS.md:56
- **Does today**: a test guards the "signal / `save()`" part. The "bulk" part is only told.
- **Problem**: the `cancel_selected` action already sends one e-mail per row (enrollments/admin.py:18-19, services.py:66), and `enroll()` has no way of not sending (postmortem 2024-03:21).
- **Must become**: a `notify` parameter (keyword, `True` by default) on `enroll()` and `cancel()`, which the admin and the imports pass as `False`, with a test.
- **Verification criterion**: the test of the admin action on several rows leaves `mail.outbox` empty.

### [PUSH_DOWN] [P2] "Capacity" rule — AGENTS.md:57
- **Does today**: it is told, with its why.
- **Problem**: an enrollment can be added through the admin (enrollments/admin.py:7-8), and the lock is only tested under SQLite (postmortem 2024-09:18-19).
- **Must become**: `has_add_permission=False`, a test that scans the sources to find `Enrollment.objects.create`/`bulk_create` outside the services and the tests, and a PostgreSQL CI job with a concurrency test.
- **Verification criterion**: the add page returns 403 in test, and the scan fails on a direct write added on purpose.

### [MERGE] [P2] CLAUDE.md — CLAUDE.md
- **Does today**: it summarises AGENTS.md without including it (CLAUDE.md:3).
- **Problem**: Claude sees neither the whys nor the bulk sending rule. Line 18 contradicts it and line 20 repeats the false guardrail.
- **Must become**: `@AGENTS.md`, plus only the lines specific to Claude. The wording of CLAUDE.md:21 moves up into AGENTS.md:60.
- **Verification criterion**: no rule exists in only one of the two files, and CLAUDE.md is fewer than 10 lines long.

### [PUSH_DOWN] [P3] "Dates" rule — AGENTS.md:61
- **Does today**: it is told, without a guardrail.
- **Problem**: a `datetime.now()` would pass the CI and skew `has_started` (catalog/models.py:58-59).
- **Must become**: ruff with the DTZ rules in CI.
- **Verification criterion**: an added `datetime.now()` makes the CI fail.

### [KEEP] AGENTS.md — AGENTS.md
It is the right file, with the right scope and exemplary incident rules. It is to be cleaned line by line according to section 3c.

### [KEEP] CI workflow — .github/workflows/ci.yml
A blocking job that guards forgotten migrations and runs the tests. The new guardrails are added here.

### [KEEP] Query count test — catalog/tests/test_queries.py
It is the model to follow: born of an incident that it cites, it also says what must not be done.

### [KEEP] "save sends nothing" test — enrollments/tests/test_services.py:106
It guards the absence of sending in a signal or in `save()`.

### [KEEP] Postmortems and ADR — docs/postmortems/, docs/adr/
They carry the whys and list honestly what remains open.

### [KEEP] Operations — docs/operations.md
It describes the real CI faithfully, and it is the one that reveals the false guardrail.

### [KEEP] README — README.md
Its commands are exact and aligned with the CI.

## 5. Remediation plan

| Order | Priority | Verdict | Item | Action | Depends on | Verification | Human approval required |
|---|---|---|---|---|---|---|---|
| 1 | P1 | PUSH_DOWN | Applied migrations | `frozen-migrations` job in ci.yml and in the branch protection | — | PR modifying 0001 red, PR adding 0003 green | Yes |
| 2 | P2 | PUSH_DOWN | Capacity | Close the add in the admin, source scan test, PostgreSQL job | Q5 | 403 in test, scan red on a direct write | Yes |
| 3 | P2 | PUSH_DOWN | Bulk e-mails | `notify` parameter and test of the admin action | Q4 | `mail.outbox` empty | Yes |
| 4 | P2 | REMOVE | AGENTS.md | Harmful lines :30 and :60 (2nd sentence), and the mention of the job at :58 if order 1 is refused | 1 | All the commands cited run | Yes |
| 5 | P2 | MERGE | CLAUDE.md | Reduce to `@AGENTS.md` and remove :18 | 4 | No duplicate left | Yes |
| 6 | P3 | PUSH_DOWN | Dates | ruff DTZ (and E501 at 100 depending on Q6) | Q6 | `datetime.now()` red in CI | Yes |
| 7 | P3 | REMOVE | AGENTS.md | Useless lines 3, 7, 9-24, 36, 37, 44, 46; shorten 59-60 | 5 | ~40 lines, 56-57 intact | Yes |
| 8 | P3 | REMOVE | AGENTS.md / CLAUDE.md | Stale lines 38, 43, 51, 52 and CLAUDE.md:17 according to the answers | Q1, Q2, Q3, Q6 | Versions aligned with requirements.txt and ci.yml | Yes |
| 9 | P3 | KEEP | AGENTS.md | Add a maintenance clause | 7 | Clause present | No |

## 6. What the audit could not verify

- The tests were not run, because Django is not installed in the environment.
- The branch protection of `main` (Q7).
- The host's deployment pipeline, outside the repository: neither dry-run nor stop point verifiable, and no rollback (docs/operations.md:13).
- The real versions of Python and Django in production (Q1, Q2).
- The age of the rules: the git history comes down to one import commit (3719e0e), so the ages given by `harness rules` mean nothing.

## 7. Machine data

The complete JSON block, conforming to the template's schema (12 items, 4 leaks, 3 guarded rules, 18 removals, 7 questions, 9 remediation actions), is written in `.harness/audit.json`; the syntax was validated. Its summary:

```json
{
  "audit": {
    "process": "AI-assisted contribution to Cursus (PR to main, CI, automatic deployment)",
    "scope": "Cursus repo: AGENTS.md, CLAUDE.md, .github/workflows/ci.yml, guardrail tests, docs/",
    "date": "2026-11-14",
    "health_score": 49,
    "cut_the_agent_test": { "passed": false, "leaked_steps": 4 }
  }
}
```

The complete file is here: /tmp/claude-0/-home-user/c9c9c05e-e8c6-5b39-9449-fc2d7f51c43b/scratchpad/banc/w-98numf2m/repo/.harness/audit.json

---

I modified nothing else in the repository: `.harness/audit.json` is the only file written, as the skill asks, and it is not committed.
