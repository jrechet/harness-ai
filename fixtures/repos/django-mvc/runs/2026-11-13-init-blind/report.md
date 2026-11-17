I laid level 1 ("Framed") on the repository. The `harness.py status` check gives 5 checks out of 5 and no reference to a missing item any more. I committed nothing and opened no PR, it was not asked.

Two actions were refused automatically, for lack of a way to approve them in this session: a combined Bash command (nothing blocking, I read the files another way) and `pip install -r requirements.txt`. Without Django installed, **I could run no test and no `manage.py` command**.

## Report

**Before and after**
- **Level**: 0 before, 1 after.
- **Lines loaded per session**: before, 21 for Claude Code (`CLAUDE.md`) and 67 for Copilot (`AGENTS.md`). After, 20 for every tool (`AGENTS.md`, which `CLAUDE.md` imports).
- **Rules**: before, 7 project rules plus about 15 instructions on style, compatibility and git, none of them dated nor verified. After, 7 rules and 3 Forbidden items, all dated.

**Files**
- `AGENTS.md`: rewritten, from 67 to 20 lines.
- `CLAUDE.md`: brought down from 21 lines to 1 (`@AGENTS.md`).
- `.github/copilot-instructions.md`: created (1 line). There is no Cursor stub, the team does not use it.
- `.harness/state.json`: written by the CLI.

**Removed**
- *Useless* (the agent finds it alone, or the model does it without being told):
  - the tree and the stack;
  - "think step by step", "do not invent APIs";
  - PEP 8, "clear names", "no print";
  - "one branch per topic" and "PR to `main`": the CI only runs on `main`;
  - `runserver` and `makemigrations`: these commands are already in the README.
- *Harmful*:
  - "Always give the complete file": in delegation, the agent modifies files and opens a PR, it does not paste an answer.
  - `test --settings=cursus.settings_ci`: this settings file does not exist, the command fails.
  - The CI job `frozen-migrations`: it does not exist, so the rule wrongly believed itself enforced. The owner confirmed the removal.
  - "Open the page with django-debug-toolbar": the tool was removed from the dependencies in June 2025 and the test that counts the queries replaces it.
  - "Every enrollment created sends its confirmation" (`CLAUDE.md`): contradicts the decision taken after the incident of March 2024 (a bulk job does not send one e-mail per row).
- *Stale*, removed after the owner's confirmation:
  - Python 3.8: production has run on 3.12 since February 2025.
  - Django 4.2 LTS: the team has followed the current versions since the change of host, Django 5.1 today.
- *Removed on my own initiative, to be confirmed*: lines of 100 characters at most, a docstring per public function, and "a test per change". No tool checks them and the repository already breaks the first two (`enrollments/views.py`, `enrollments/notifications.py`). See question 2.

**Secrets**: none found. The settings only read environment variables; the only default value is an explicit development key.

**Rules written**

| Rule | Status | Date |
|---|---|---|
| French for the answers and the commits, English for the code | unverified | 2026-11 |
| E-mails: no signal, no sending per row in a bulk job | unverified | 2024-03 |
| Capacity: every enrollment goes through `enroll()`; the add form of the admin is reported as a counter-example | unverified | 2024-09 |
| List pages: no query per row | enforced by `catalog/tests/test_queries.py` | 2025-06 |
| Cap `CURSUS_IMPORT_MAX_ROWS` (500 rows, file refused beyond), a setting that does not exist yet; told by the team | unverified | 2025-02 |
| Business logic lives in `services.py` (ADR 0001) | unverified | 2023-11 |
| `timezone.now()` | unverified | 2026-11 |

For the rule on list pages, I saw the `test` job run `manage.py test` without `continue-on-error`, and the owner confirms that this job blocks the merge. I could not run the test myself.

Forbidden:
- Modifying an existing migration [2024-01]. No CI job rejects it today.
- Sending a real e-mail outside production [2024-03].
- Taking personal data of enrolled people out of the server [2026-11].

**Commands**
- Confirmed: none.
- Not confirmed, because Django could not be installed: `python manage.py test`, `python manage.py makemigrations --check --dry-run`, `python manage.py check`. They are the ones the CI runs; so I did not make a commands table in `AGENTS.md`.

**Questions to the owner**
1. Must a future import be able to enroll without sending an e-mail? `enroll()` always sends, and the post-mortem of March 2024 leaves this point open. *Default applied:* a bulk job does not call `enroll()` as is.
2. Are the lines of 100 characters and the docstring per public function still wanted? *Default:* removed as long as no linter carries them.
3. Should the add form for enrollments in the admin, which bypasses `enroll()`, be closed? *Default:* reported in `AGENTS.md` as a counter-example, without touching it.
4. Should the frozen-migrations check be recreated in CI, which the old instructions believed in place? *Default:* the Forbidden item stays without a guardrail.

**Possible next step**: loop the file (level 2: Maintenance section, `rule:` convention) with `harness target 2` then harness-step. I did not do it.
