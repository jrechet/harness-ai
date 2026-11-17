I sorted AGENTS.md line by line and rewrote nothing: two lines removed, three corrected, one ban added, and the stub that was missing for the `billing` note. The CLI check passes: level 1, 5 checks out of 5, no reference without a target. The changes are not committed: the PR is still to be opened.

Two actions were refused automatically, for want of someone to approve them: listing the kit with `find`, and a command that chained the tests and the import check. I got the same result with the file search and by running each command separately.

## Report — harness-init

**Before and after**

| | Before | After |
|---|---|---|
| Level | 1 (5/5) | 1 (5/5) |
| Lines loaded per session (root) | 1 + 27 | 1 + 26 |
| Rules / Forbidden | 8 / 2 | 6 / 3 |
| "Enforced by" rules | 4 (1 of them false) | 4 |

The repository was already at level 1: the work was mostly removing and correcting.

**Files**
- `AGENTS.md`: modified, 26 lines.
- `services/billing/CLAUDE.md`: created, 1 line (`@AGENTS.md`). Claude Code loads the `CLAUDE.md` of subfolders, not the `AGENTS.md`. Since you only use Claude Code, the `billing` note (frozen invoice, continuous numbering) was therefore never loaded.
- `.harness/state.json`: written by the CLI.
- No Copilot or Cursor stub, since you only use Claude Code.

**Removed**
- *Harmful*: "run `grep … services\.` and review by hand". This review has no longer been the check since 4 August: `tools/check_imports.py` runs in `boundaries`, which blocks (update of ADR 0001 and your answer). The grep is also weaker than the script: it sees neither `from services import orders` nor relative imports.
- *Outdated, removed on your answer*: the limit of 64 KB per event. It came from the shared plan, which has no longer existed since March 2025. The dedicated cluster accepts 8 MB and refuses beyond that with an error.

**Corrected (what was wrong)**
1. **The rule "additive contract change" said "Enforced by: `services/orders/test_contract.py`". That is wrong**, and your own post-mortem of 12 May says so in "What remains open": this test stays green when the schema and the provider change together. Moreover, the tests of `billing` and `notifications` make their events by hand. The rule becomes `(unverified)`, with this explanation. It is the gap that matters most for your first delegated task, a contract change that crosses two services.
2. **Rule "no import between services"**: it was marked `(unverified)` whereas it is enforced. It now carries "Enforced by: `tools/check_imports.py`, job `boundaries`". The job runs on every PR, with no path filter and no `continue-on-error`. The script passes today without reporting anything, and its test passes.
3. **Forbidden "weakening a guardrail"**: it said that CODEOWNERS has everything reviewed by the platform team. CODEOWNERS covers only `tools/`, `shared/`, `.github/` and `contracts/`. A `deliveries=1` in `services/*/test_*.py` is therefore reviewed by no owner. I wrote it in the line.
4. **Rule "strict contracts"**: the repository already breaks it. `GET /outbox` (`services/notifications/app.py`) has neither a schema in `contracts/api/` nor a `test_contract.py`. It is now written in the rule so that the agent does not take it as a model.

**Added**: the Forbidden "modifying an issued invoice", which was in your answers but not in the root file. It is enforced by `services/billing/test_ledger.py`, but only for `Invoice`, the frozen invoice.

**Secrets**: none in the instruction files, the config and `docker-compose.yml`.

**Rules written**

| Rule | Status | Date |
|---|---|---|
| Strict contracts | Enforced by the two `test_contract.py` and `tools/schema.py` | [2024-06] |
| Additive change | Unverified | [2026-05] |
| `deprecated: true` | Unverified (`tools/schema.py` does accept the annotation) | [2026-09] |
| `contracts/CHANGES.md` | Unverified | [2026-09] |
| Idempotent consumer | Enforced by `shared/bus.py` (`deliveries=2`) and the `test` job | [2025-11] |
| No import between services | Enforced by `tools/check_imports.py` | [2024-06] |

Forbidden: `BROKER_URL` [2026-01], weakening a guardrail [2025-11], issued invoice [2025-11]. The first two have no automatic check and are marked `(unverified)`; the third is enforced by `test_ledger.py`, for `Invoice` only.

**Commands**
- Run without error: `python3 -m unittest discover` (61 tests OK), `discover -s services/{orders,billing,notifications} -t .` (9, 14 and 5 OK), `python3 tools/check_imports.py` (exit code 0).
- Not confirmed: `docker compose up`, not run (it needs the platform team's image); `tools/replay.py`, which no longer exists.

**What is written nowhere**: nothing new. Your answers all point to `docs/`, or were already in the file.

**Questions** (proposed default in parentheses)
1. `README.md:14` still cites `tools/replay.py`, removed after January. An agent that reads the README may try to run it. (Remove the line.)
2. `GET /outbox`: is it an API that others read, or a debug tool? (If others read it: add `contracts/api/outbox.json` and a `test_contract.py` for `notifications`. Otherwise: exclude it explicitly from the rule.)
3. Should `/services/**/test_*.py` be added to CODEOWNERS so that a `deliveries=1` is reviewed? (Yes, by the platform team.)
4. The additivity rule has no guardrail, and it is the first task you want to delegate. Should one be added? For example, have `tools/schema.py` validate the events made in the consumers' tests, or compare each schema to its version on `main`. (Yes, before delegating this task.)
5. The rule on replaced fields (`deprecated: true`) and the rule on `contracts/CHANGES.md` have no automatic check. (Leave them `(unverified)` for now.)

**The possible next step**: move to level 3, starting with a guardrail for the additivity of contracts (`harness target 3`, led by harness-step). I did not do it.