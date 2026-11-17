# Fictional owner — django-mvc (cursus)

This file is given to the agent that plays harness-init or harness-audit blind: these are the team's answers. The planted facts are in the repository, to be found, except one: the one the team adds on its own below can be read nowhere else.

## Answers to the interview
1. **Mode**: delegation. We want to hand over whole tickets and review the PR at the end.
2. **Team**: three developers, none of whom was there when the project started; a training manager who uses the admin.
3. **CI**: GitHub Actions, a single job, `test`. It blocks the merge into `main`.
4. **Tools**: Claude Code for two of us, Copilot for the third.
5. **First task to delegate**: a job on enrollment data, import or export, from the view to the test.
6. **Forbidden**: modifying a migration already applied; sending a real e-mail from anything other than production; taking personal data of enrolled people out of the server.

## What the team adds on its own
"One thing that is written nowhere: the host cuts any request at thirty seconds. We agreed with it, in February 2025, that a job started from a page does not exceed 500 rows, and that this cap is read from the Django setting `CURSUS_IMPORT_MAX_ROWS`, so that it can lower it without us. The setting does not exist yet: no job of this kind has been written. Beyond the cap, we refuse the whole file."

## If the agent asks other questions
- "Where do AGENTS.md and CLAUDE.md come from?": AGENTS.md was written by hand at the end of 2024 by the developer who set up the project. She left at the beginning of 2025 and nobody has reread it since. CLAUDE.md was copied from memory by one of us when we started with Claude Code; since then, when we fix something, it is in that one.
- "Can I remove lines?": yes. Say what you remove and why.
- "Is the server still on Python 3.8?": no. It was replaced in February 2025, production runs on 3.12.
- "Are you bound to Django 4.2 LTS?": not since the change of host, at the same time. We follow the current versions, 5.1 today.
- "Has the CI changed?": yes, at the beginning of 2025, with the host. We took the tests over to GitHub Actions. Nobody made the inventory of what else the old one checked.
- "Why does nothing verify the lock?": the CI runs under SQLite and nobody has set up a PostgreSQL for the tests.
- On everything else: "look in `docs/`, it is written". The team knows nothing more than what the post-mortems, the ADR and the operations note say.

## What the team expects
To know what still holds in a file written with care two years ago, and to keep a single file.
