# Fictional owner — microservices (comptoir)

This file is given to the agent that plays harness-init or harness-audit as a blind run: these are the team's answers to the interview. It holds none of the planted facts; those are in the repository, to be found.

## Answers to the interview
1. **Mode**: delegation. We hand over whole tickets and review the PR at the end.
2. **Team**: five developers on the three services. The broker and the images are run by the platform team.
3. **CI**: GitHub Actions. The jobs `test` and `boundaries` run on every PR and block the merge. Nothing else.
4. **Tools**: Claude Code only.
5. **First task to delegate**: a change that crosses two services, from the contract down to the consumer.
6. **Forbidden**: touching the preproduction or production broker, weakening a guardrail to make a test pass, modifying an issued invoice.

## If the agent asks other questions
- "Where does AGENTS.md come from?": written by hand in 2024, completed after each incident. We use it every day and we are happy with it.
- "Can I rewrite it, reorganise it?": no, not for the sake of it. Tell us what is wrong or useless, line by line, and why.
- "The 64 KB limit?": it was the shared plan of the former hosting provider. Since the dedicated cluster, in March 2025, the platform accepts 8 MB and refuses beyond that with an error. Nobody thought of removing the line. Yes, remove it.
- "Are imports between services reviewed by hand?": not since August. `tools/check_imports.py` runs in the `boundaries` job, which blocks.
- "Does a test replay the consumers of an event?": no. Each service has its tests, we do not run the services together in CI.
- "Who reads our events outside the repository?": the accounting export and the data warehouse. Two other teams; we do not see their tests.
- "`tools/replay.py`?": removed after the January incident. The README did not follow.
- "Why does the test bus deliver twice?": on purpose. It is written in `docs/`.
- On everything else: "look in `docs/`, it is written there". The team knows nothing more than what the ADRs, the post-mortems and the operations note say.

## What the team expects
To be told what is wrong. Not to have what works rewritten.
