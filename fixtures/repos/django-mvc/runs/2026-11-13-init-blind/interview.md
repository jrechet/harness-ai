# Interview of django-mvc: 9 question(s)

- I5, held only by the owner: asked at question 4

## 1
**Question**: 1. Mode: delegation (default: the agent receives a whole task and comes back with a PR, nobody reviews on the way) or assistance (the human reviews each diff live)?

**Answer** (mode): Delegation. We want to hand over whole tickets and review the PR at the end.

## 2
**Question**: 2. Forbidden: what must an agent never touch or do (folders, secrets, shared database, prod migrations, force push...)?

**Answer** (forbidden): Modifying a migration already applied; sending a real e-mail from anything other than production; taking personal data of enrolled people out of the server.

## 3
**Question**: 3. Tools and CI: which agents do you use (Claude Code alone, or also Copilot, Cursor, Codex)? Which CI, and which checks block the merge today?

**Answer** (ci, tools): GitHub Actions, a single job, `test`. It blocks the merge into `main`.
Claude Code for two of us, Copilot for the third.

## 4
**Question**: 4. What do you say again at every review, or what does a newcomer learn by getting it wrong, that no file of the repository says?

**Answer** (oral): One thing that is written nowhere: the host cuts any request at thirty seconds. We agreed with it, in February 2025, that a job started from a page does not exceed 500 rows, and that this cap is read from the Django setting `CURSUS_IMPORT_MAX_ROWS`, so that it can lower it without us. The setting does not exist yet: no job of this kind has been written. Beyond the cap, we refuse the whole file.

## 5
**Question**: AGENTS.md and CLAUDE.md require Python 3.8 on the server. Yet requirements.txt pins Django 5.1 (which needs Python 3.10 at least), the CI runs on 3.12, and the code already uses match (enrollments/notifications.py) and 'Enrollment | None' (enrollments/services.py). Which version of Python runs in production today? Is the 3.8 rule stale?

**Answer** (ci, python, django): GitHub Actions, a single job, `test`. It blocks the merge into `main`.
No, no longer on 3.8. The server was replaced in February 2025, production runs on 3.12.
Not since the change of host, in February 2025. We follow the current versions, 5.1 today.

## 6
**Question**: AGENTS.md says to stay on Django 4.2 LTS because the host only validates LTS versions; requirements.txt pins Django>=5.1,<5.2. Is this rule stale, or is the dependency a mistake?

**Answer** (django, oral): Not since the change of host, in February 2025. We follow the current versions, 5.1 today.
One thing that is written nowhere: the host cuts any request at thirty seconds. We agreed with it, in February 2025, that a job started from a page does not exceed 500 rows, and that this cap is read from the Django setting `CURSUS_IMPORT_MAX_ROWS`, so that it can lower it without us. The setting does not exist yet: no job of this kind has been written. Beyond the cap, we refuse the whole file.

## 7
**Question**: AGENTS.md and CLAUDE.md cite a CI job 'frozen-migrations' and a command 'test --settings=cursus.settings_ci'. Neither this job nor this settings file exists in the repository. Did they exist, should they be removed from the instructions?

**Answer** (ci, forbidden, remove): GitHub Actions, a single job, `test`. It blocks the merge into `main`.
Modifying a migration already applied; sending a real e-mail from anything other than production; taking personal data of enrolled people out of the server.
Yes. Say what you remove and why.

## 8
**Question**: The post-mortem of March 2024 says a bulk job never sends one e-mail per row, but services.enroll() always sends. CLAUDE.md says "every enrollment created sends its confirmation". For a future import (for example the 500-row one capped by CURSUS_IMPORT_MAX_ROWS), which rule must the agent follow?

**Answer** (forbidden, oral): Modifying a migration already applied; sending a real e-mail from anything other than production; taking personal data of enrolled people out of the server.
One thing that is written nowhere: the host cuts any request at thirty seconds. We agreed with it, in February 2025, that a job started from a page does not exceed 500 rows, and that this cap is read from the Django setting `CURSUS_IMPORT_MAX_ROWS`, so that it can lower it without us. The setting does not exist yet: no job of this kind has been written. Beyond the cap, we refuse the whole file.

## 9
**Question**: Commit messages in French in the imperative, and lines of 100 characters at most: still current? (No linter checks them.)

**Answer** (default): Look in `docs/`, it is written. The team knows nothing more than what the post-mortems, the ADR and the operations note say.
