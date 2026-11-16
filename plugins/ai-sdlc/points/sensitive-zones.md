A change that touches one of these zones takes the long path: a plan written in `docs/plans/`, approved by a human before the code.
- `migrations/**`, `**/migrations/**` — schema and data: a rollback is expensive.
- `.github/workflows/**`, `.gitlab-ci.yml`, `Jenkinsfile` — the CI checks everything else.
- `AGENTS.md`, `CLAUDE.md`, `docs/agents/**`, `.claude/**` — the rules that agents and the review follow.
- `**/auth/**`, `**/security/**` — authentication and permissions.
- `**/*.tf`, `**/Dockerfile`, `**/k8s/**`, `**/helm/**` — infrastructure and delivery.
