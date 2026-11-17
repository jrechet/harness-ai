# Harness audit — comptoir (delivery of a delegated ticket up to the PR)

**Scope**: repo (AGENTS.md, CLAUDE.md, services/billing/AGENTS.md, .github/, tools/, shared/, contracts/, services/*/test_*.py, docs/, README.md) · **Date**: 2026-11-14 · **Items inventoried**: 22

## 1. Summary

- **Health score**: 27 — on the whole the agent only speeds the work up: 5 of the 12 rules have a real guardrail in the CI. But the rule born of the last incident says it is enforced whereas it is not.
- **"Cut the agent" test result**: FAILED — 6 rules exist only in AGENTS.md, and the CI blocks none of them.
- **Blocking issues (P1)**: 1
- **The three actions that change things most**:
  1. Create `tools/check_contracts.py` and a blocking CI job `contracts`, which compares each schema to its version on the base branch. This same tool can check `contracts/CHANGES.md`.
  2. Correct AGENTS.md:17, 21 and 22. Two statements are false, and a manual procedure is worse than the check already in CI.
  3. Validate against `contracts/` the events that the tests of `notifications` and `billing` build by hand. It is the direct cause of the incident of 12 May.

Computation: 100 − 25 (1 P1) − 40 (5 P2) − 8 (4 P3) = 27. The cap of 60 due to the failed test does not apply here.

## 2. Map of the harness

| # | Item | Path | Declared layer | Actual layer | Called by | Calls |
|---|---|---|---|---|---|---|
| 1 | claude-md | CLAUDE.md | L2 | L2 | session | agents-md |
| 2 | agents-md | AGENTS.md | L2 | L2 | claude-md | ci-test, ci-boundaries, check-imports, billing-agents-md |
| 3 | billing-agents-md | services/billing/AGENTS.md | L2 | L2 | agents-md | billing-test-ledger |
| 4 | contract-additivity | AGENTS.md:17 | L3 (says it is enforced) | L2 | agents-md | orders-test-contract (wrongly) |
| 5 | agents-md-imports-lines | AGENTS.md:21-22 | L2 | L2 | agents-md | — |
| 6 | contracts-changelog | AGENTS.md:19 | L2 | L2 | agents-md | — |
| 7 | consumer-test-fixtures | services/notifications/test_app.py:9-26, services/billing/test_app.py:12 | L3 | L3 | ci-test | bus-py |
| 8 | guard-weakening | AGENTS.md:27 | L3 (via CODEOWNERS) | L2 | agents-md | codeowners |
| 9 | broker-url-guard | shared/bus.py:58-65 | L3 | L2 | services | — |
| 10 | readme-replay | README.md:14 | L2 | L2 | — | tools/replay.py (absent) |
| 11 | event-size-rule | AGENTS.md:23 | L2 | L2 | agents-md | — |
| 12 | notifications-api-contract | services/notifications/app.py:56-58 | L3 | L3 | — | — |
| 13 | ci-test | .github/workflows/ci.yml:8-19 | L4 | L4 | PR, push main | the whole unittest suite |
| 14 | ci-boundaries | .github/workflows/ci.yml:21-27 | L4 | L4 | PR, push main | check-imports |
| 15 | check-imports | tools/check_imports.py | L3 | L3 | ci-boundaries, agents-md | — |
| 16 | schema-py | tools/schema.py | L3 | L3 | test_contract × 2 | — |
| 17 | bus-py | shared/bus.py:33-55 | L3 | L3 | all the tests | — |
| 18 | orders-test-contract | services/orders/test_contract.py | L3 | L3 | ci-test | schema-py |
| 19 | billing-test-contract | services/billing/test_contract.py | L3 | L3 | ci-test | schema-py |
| 20 | billing-test-ledger | services/billing/test_ledger.py | L3 | L3 | ci-test | — |
| 21 | codeowners | .github/CODEOWNERS | L4 | L4 | GitHub | — |
| 22 | contributing-md | CONTRIBUTING.md | L2 | L2 | humans | — |

Nominal process for a delegated ticket:

| Process step | Carried by | Checked by code? | Dry-run? |
|---|---|---|---|
| Modify a service, run its tests | AGENTS.md:11 → ci-test | Yes (full suite in CI) | n/a |
| Respect the import boundaries | check_imports.py → ci-boundaries | Yes | n/a (read-only) |
| Strict contract on the provider side | test_contract.py × 2 | Yes for orders and billing, no for notifications /outbox | n/a |
| Additive contract change | AGENTS.md:17 only | **No** (the test cited does not see it) | — |
| Replaced field marked `deprecated` | AGENTS.md:18 | No (the choice is a matter of judgement) | — |
| Line in contracts/CHANGES.md | AGENTS.md:19 | **No** | — |
| Idempotent consumer | bus-py (deliveries=2) | Yes | n/a |
| Event size < 64 KB | AGENTS.md:23 | No | — |
| BROKER_URL never at preprod or prod | AGENTS.md:26 | **No** | — |
| Do not weaken a guardrail | AGENTS.md:27 + CODEOWNERS | Partial (services/ is not covered) | — |
| Deployment | platform team, outside the repository (docs/operations.md:10) | out of scope | out of scope |

## 3. Leaks: rules and steps told without enforcement

1. **Additive contract change** — AGENTS.md:17. The line states "Enforced by: services/orders/test_contract.py". Yet the post-mortem says the opposite: this test stays green when the schema and the provider change in the same PR (docs/postmortems/2026-05-renamed-field.md:11, :22-26). If the agent skips the rule, a renaming passes the CI green and breaks notifications and comptoir-export in production, as on 12 May. **To be placed in L3**: `tools/check_contracts.py`, which compares each schema to the one on the PR's base, with a CI job `contracts`.
2. **Dated line in contracts/CHANGES.md** — AGENTS.md:19. If the agent forgets it, the outside consumers do not see the change. **To be placed in L3**: the same tool exits with an error when a `contracts/**/*.json` has changed without a new line at the top of CHANGES.md.
3. **Replaced field: `"deprecated": true`** — AGENTS.md:18. Removing a field will be caught by point 1. Forgetting the annotation, however, cannot be checked, because knowing which field replaces another is a matter of judgement (L1). Partial guardrail, to be kept as is.
4. **BROKER_URL at preprod or prod** — AGENTS.md:26. `connect()` accepts any URL (shared/bus.py:58-65). If the instruction is ignored, real events leave from a workstation, like the 3,100 emails of 9 January 2026 (docs/operations.md:29). **To be placed in L3**: a refusal in `connect()`, doubled in L4 by credentials only the platform holds.
5. **Weakening a guardrail** — AGENTS.md:27. CODEOWNERS (lines 2-5) does not cover `services/`, yet that is where a `deliveries=1` would slip in. If that happens, a non-idempotent consumer passes the CI. **To be placed in L3**: a test that refuses `InMemoryBus(deliveries=` under `services/`.
6. **Event size < 64 KB** — AGENTS.md:23. No check, and the justification is dated (see 3c). **To be placed in L3**: a size check in `InMemoryBus.publish`, once the real limit is confirmed.

Rules that have their guardrail:
- Strict contracts on the provider side (AGENTS.md:16): `services/{orders,billing}/test_contract.py` and `tools/schema.py`. Partial, because `/outbox` has no contract.
- Idempotence (AGENTS.md:20): `shared/bus.py`, which delivers twice by default.
- No import between services (AGENTS.md:21): `tools/check_imports.py`, job `boundaries`. Blocking, whereas the line says "unverified".
- Invoices numbered with no gap and frozen invoice (services/billing/AGENTS.md:5-6): `services/billing/test_ledger.py`.

## 3b. Context cost

| File | Lines loaded (with includes) | Share instruction / reference / noise | Loaded when |
|---|---|---|---|
| CLAUDE.md → @AGENTS.md | 28 | 70% / 30% / 0% | every session |
| services/billing/AGENTS.md | 7 | 85% / 15% / 0% | work in services/billing |

All the rules are dated and justified by an incident or an ADR, which is the real strength of this harness. A maintenance clause is missing. Also missing, whereas the declared mode is delegation, is an indication of when to stop and ask (AGENTS.md:3).

## 3c. Lines to remove

| File:line | Text | Reason | Proof | Question to the owner? |
|---|---|---|---|---|
| AGENTS.md:22 | "Before opening a PR, run `grep -rnE …` and review each line by hand … it is the only check" | harmful | Contradicts ADR 0001:23 ("The review by hand is no longer the check") and ci.yml:21-27. The grep misses `from services import orders`, relative imports and indented imports (tools/test_check_imports.py:39-46). | No |
| AGENTS.md:21 | "(unverified)" | harmful | Enforced by check_imports.py, job boundaries, since 2026-08-04. To be replaced with "Enforced by: tools/check_imports.py, job boundaries". | No |
| AGENTS.md:17 | "Enforced by: `services/orders/test_contract.py`." | harmful | Post-mortem 2026-05:11 and :22-26. To be replaced with "(unverified)" until the contracts job arrives. | No |
| README.md:14 | `python3 tools/replay.py order.created` | harmful | The script does not exist, and replaying a queue from a workstation is reserved for the platform (operations.md:28-29). | Yes (Q2) |
| AGENTS.md:23 | "Why: … the broker's shared plan cuts the connection …" | outdated | The broker has been a dedicated cluster since March 2025 (operations.md:13). | Yes (Q1) |

**Questions to the owner**
1. AGENTS.md:23 — does the dedicated cluster still have a size limit, and which one? *Proposed default*: keep the rule "no file in an event", rewrite the why with the real limit, add the check in `InMemoryBus.publish`.
2. README.md:14 — was `tools/replay.py` removed after 9 January 2026? *Proposed default*: remove the line and point to docs/operations.md, section "Replaying events".
3. Is `GET /outbox` read outside the notifications service? *Proposed default*: yes, to be safe. Add `contracts/api/outbox.json` and `services/notifications/test_contract.py`.
4. Does the protection of `main` require the jobs `test` and `boundaries` as well as the CODEOWNERS review? *Proposed default*: assume it does not until confirmed, and add the anti-`deliveries=` test.
5. Can a workstation or an agent session obtain credentials for comptoir-preprod or comptoir-prod? *Proposed default*: add the refusal in `connect()`, with a deployment marker to be agreed with the platform.
6. For the additive rule, should the comparison be with `origin/main` or with the deployed version? *Proposed default*: the base of the PR.

AGENTS.md goes from 28 to 27 lines. Line 22 is removed and two fragments are corrected. Lines 16 to 20 and 26 to 27 must absolutely be kept: each one carries an incident.

## 4. Findings by item

### [PUSH_DOWN] [P1] contract-additivity — AGENTS.md:17
- **Does today**: the rule says it is enforced by `services/orders/test_contract.py`.
- **Problem**: this test validates the provider against the schema, not the schema against its previous version. It was green on 12 May (proof: docs/postmortems/2026-05-renamed-field.md:11, :22-26). So the agent relies on the CI for a check it does not make.
- **Must become**: `tools/check_contracts.py`, tested, with `--json` and an error exit when a property is removed, a type changed, a field made required or `additionalProperties` loosened. A blocking CI job `contracts` runs it.
- **Check criterion**: a PR that renames `customer_email` to `email` fails the `contracts` job.

### [REMOVE] [P2] agents-md-imports-lines — AGENTS.md:21-22
- **Does today**: line 21 says the rule is unverified, line 22 imposes a manual grep presented as "the only check".
- **Problem**: it has been false since 2026-08-04 (proof: docs/adr/0001-three-services-one-contract.md:23, .github/workflows/ci.yml:21-27). The grep lets three spellings of an import through (tools/test_check_imports.py:39-46).
- **Must become**: line 22 is removed, line 21 says "Enforced by: tools/check_imports.py, job boundaries".
- **Check criterion**: `harness rules` shows AGENTS.md:21 with its guardrail.

### [PUSH_DOWN] [P2] contracts-changelog — AGENTS.md:19
- **Does today**: the rule is only written, and `contracts/CHANGES.md` does not exist.
- **Problem**: the outside consumers depend on this file (proof: AGENTS.md:19, docs/operations.md:17-23).
- **Must become**: a check in `check_contracts.py` (contract modified without a CHANGES.md line → exit 1).
- **Check criterion**: adding a field without a CHANGES.md line fails the CI.

### [PUSH_DOWN] [P2] consumer-test-fixtures — services/notifications/test_app.py:9-26
- **Does today**: the tests of notifications and of billing (services/billing/test_app.py:12) build their events by hand.
- **Problem**: these events are never validated against `contracts/`, and it is the direct cause of 12 May (proof: post-mortem 2026-05:6, :24).
- **Must become**: each fixture is validated by `tools.schema.validate` against its contract.
- **Check criterion**: removing `customer_email` from the schema fails the tests of both consumers.

### [PUSH_DOWN] [P2] guard-weakening — AGENTS.md:27
- **Does today**: the rule rests on CODEOWNERS.
- **Problem**: CODEOWNERS does not cover `services/` (proof: .github/CODEOWNERS:2-5), and branch protection is not visible from the repository.
- **Must become**: a test that refuses `InMemoryBus(deliveries=` under `services/`.
- **Check criterion**: `deliveries=1` in a service test fails the `test` job.

### [PUSH_DOWN] [P2] broker-url-guard — shared/bus.py:58-65
- **Does today**: `connect()` connects to any URL given in `BROKER_URL`.
- **Problem**: the ban exists only in AGENTS.md:26, and the incident of 9 January shows what bypassing it costs (proof: docs/operations.md:29).
- **Must become**: a refusal of the hosts `comptoir-preprod` and `comptoir-prod` without a deployment marker, and credentials held in L4 by the platform.
- **Check criterion**: a test of `shared/test_bus.py` proves the refusal, and preproduction still starts.

### [REMOVE] [P3] readme-replay — README.md:14
- **Does today**: the README documents a script `tools/replay.py`.
- **Problem**: this script is absent, and the operation it describes is forbidden from a workstation (proof: docs/operations.md:28-29).
- **Must become**: the line is removed, or replaced by a pointer to docs/operations.md (Q2).
- **Check criterion**: no mention of `replay.py` left.

### [PUSH_DOWN] [P3] event-size-rule — AGENTS.md:23
- **Does today**: the 64 KB limit is written without a check.
- **Problem**: the justification points to the shared plan, abandoned in March 2025 (proof: docs/operations.md:13).
- **Must become**: after the answer to Q1, a size check in `InMemoryBus.publish`.
- **Check criterion**: publishing an event beyond the limit fails a test.

### [PUSH_DOWN] [P3] notifications-api-contract — services/notifications/app.py:56-58
- **Does today**: `/outbox` answers without a schema or a `test_contract.py`.
- **Problem**: the rule AGENTS.md:16 covers everything a service answers, and nothing obliges a service to have its contract test.
- **Must become**: a schema and a test for `/outbox`, or an exception written in the rule (Q3).
- **Check criterion**: the answers of `/outbox` are validated against a schema.

### [KEEP] [P3] agents-md — AGENTS.md
- **Does today**: a short, dated and justified file.
- **Problem**: no maintenance clause, and no indication of when to stop and ask, whereas the mode is delegation (proof: AGENTS.md:3).
- **Must become**: two more lines, one for maintenance and one for stopping.
- **Check criterion**: both clauses are present.

### [KEEP] claude-md — CLAUDE.md
A single line, `@AGENTS.md`: there is only one source of instructions.

### [KEEP] billing-agents-md — services/billing/AGENTS.md
Two legal rules, justified and guarded by `test_ledger.py`.

### [KEEP] ci-test — .github/workflows/ci.yml:8-19
The whole suite runs on every PR, with no path filter and no `continue-on-error`.

### [KEEP] ci-boundaries — .github/workflows/ci.yml:21-27
Blocking on every PR.

### [KEEP] check-imports — tools/check_imports.py
Tested CLI, with exit code and `--json`. 0 violations today.

### [KEEP] schema-py — tools/schema.py
Refuses any unknown keyword instead of letting it pass silently.

### [KEEP] bus-py — shared/bus.py:33-55
Delivers twice by default, so idempotence is tested without anyone thinking about it.

### [KEEP] orders-test-contract — services/orders/test_contract.py
The test is good. It is the line AGENTS.md:17 that cites it wrongly.

### [KEEP] billing-test-contract — services/billing/test_contract.py
Same role as the one of orders.

### [KEEP] billing-test-ledger — services/billing/test_ledger.py
Numbering with no gap and frozen invoice, tested.

### [KEEP] codeowners — .github/CODEOWNERS
Review of the guardrails by two people. Its blind spot is handled in guard-weakening.

### [KEEP] contributing-md — CONTRIBUTING.md
Style conventions meant for humans, not loaded by the agent. It is not a leak.

## 5. Remediation plan

| Order | Priority | Verdict | Item | Action | Depends on | Check | Human approval required |
|---|---|---|---|---|---|---|---|
| 1 | P1 | PUSH_DOWN | contract-additivity | Create `tools/check_contracts.py` and its tests | — | Tests of the renaming, the removal, the type change; an optional addition is accepted | Yes (tools/ belongs to the platform team) |
| 2 | P1 | PUSH_DOWN | contract-additivity | Add the `contracts` job (fetch-depth: 0) and cite this job in AGENTS.md:17 | 1 | A renaming of `customer_email` fails the CI | Yes |
| 3 | P2 | REMOVE | agents-md-imports-lines | Remove AGENTS.md:22, correct 21, set 17 to "unverified" until step 2 | — | Output of `harness rules` | Yes |
| 4 | P2 | PUSH_DOWN | consumer-test-fixtures | Validate the consumers' fixtures against `contracts/` | — | A field removed from the schema breaks the consumers' tests | No |
| 5 | P2 | PUSH_DOWN | contracts-changelog | Add the CHANGES.md check to `check_contracts.py` | 1, 2 | Adding a field without a CHANGES.md line fails | Yes |
| 6 | P2 | PUSH_DOWN | guard-weakening | Test that refuses `deliveries=` under `services/`; confirm the branch protection (Q4) | — | `deliveries=1` in a service test fails `test` | No |
| 7 | P2 | PUSH_DOWN | broker-url-guard | Refusal of the preprod and prod hosts in `connect()`, with a test (Q5) | — | Test of the refusal; preprod still starts | Yes |
| 8 | P3 | REMOVE | readme-replay | Remove README.md:14 (Q2) | — | No mention of `replay.py` left | Yes |
| 9 | P3 | PUSH_DOWN | event-size-rule | Size check and new why (Q1) | — | An event that is too big fails a test | Yes |
| 10 | P3 | PUSH_DOWN | notifications-api-contract | Schema and contract test for `/outbox` (Q3) | — | `/outbox` validated against its schema | Yes |
| 11 | P3 | KEEP | agents-md | Add the maintenance and stop clauses | 3 | Both clauses are present | Yes |

## 6. What the audit could not check

- The protection of the `main` branch (required checks, CODEOWNERS review), which is not visible from the repository.
- Whether a workstation or an agent session can obtain credentials for the preproduction or production broker.
- The real size limit of the dedicated cluster and that of the outside consumers.
- The history: a single import commit (bcfc7e4). The dates come from the `[YYYY-MM]` tags written in the text.
- The `.harness/` folder: it did not exist before this audit, so no earlier state or harvest.
- For information, outside the harness scope: `_handled` (notifications) is kept in memory, and no test covers a redelivery after a restart.
- Two shell commands were refused for want of an approval surface (a compound command, a loop with a variable). I read the same files with the reading tool. The suite (61 tests, OK) and `check_imports.py` (0 violations) ran normally.

## 7. Machine data

The full JSON (22 items, 6 leaks, 5 removals, 6 questions, 11 plan steps) is written in `.harness/audit.json`. The file was validated with `json.tool`. Here is its header; the rest is in the file:

```json
{
  "audit": {
    "process": "comptoir — delivery of a delegated ticket up to the PR",
    "scope": "repo (AGENTS.md, CLAUDE.md, services/billing/AGENTS.md, .github/, tools/, shared/, contracts/, services/*/test_*.py, docs/, README.md)",
    "date": "2026-11-14",
    "health_score": 27,
    "cut_the_agent_test": { "passed": false, "leaked_steps": 6 }
  },
  "elements": ["… 22 entries, see .harness/audit.json"],
  "process_leaks": ["… 6 entries"],
  "guarded_rules": ["… 5 entries"],
  "removals": ["… 5 entries"],
  "owner_questions": ["… 6 questions, numbered as in 3c"],
  "instruction_files": [
    { "path": "CLAUDE.md (+ @AGENTS.md)", "loaded_lines": 28, "instruction_pct": 70, "reference_pct": 30, "noise_pct": 0, "justified_rules": true, "maintenance_clause": false },
    { "path": "services/billing/AGENTS.md", "loaded_lines": 7, "instruction_pct": 85, "reference_pct": 15, "noise_pct": 0, "justified_rules": true, "maintenance_clause": false }
  ],
  "remediation": ["… 11 steps, same order as section 5"],
  "unverified": ["… 6 entries, identical to section 6"]
}
```

Apart from `.harness/audit.json`, I modified no file of the repository.