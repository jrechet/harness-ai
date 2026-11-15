Un changement qui touche une de ces zones suit le chemin long : un plan écrit dans `docs/plans/`, validé par un humain avant le code.
- `migrations/**`, `**/migrations/**` — schéma et données : un retour arrière coûte cher.
- `.github/workflows/**`, `.gitlab-ci.yml`, `Jenkinsfile` — la CI vérifie tout le reste.
- `AGENTS.md`, `CLAUDE.md`, `docs/agents/**`, `.claude/**` — les règles que suivent les agents et la revue.
- `**/auth/**`, `**/security/**` — authentification et droits.
- `**/*.tf`, `**/Dockerfile`, `**/k8s/**`, `**/helm/**` — infrastructure et livraison.
