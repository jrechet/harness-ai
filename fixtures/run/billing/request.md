# Request

The alert "500 error rate of the billing API" has been firing since 14:05. What is going on?

The evidence is in `evidence/`, next to the repository: the alert, the API log and the deployment history. The repository is on `main`, up to date with `origin/main`, which is what runs in production. The last known healthy version is `v2.0.3`.

You have no access to production. Write your investigation in `out/investigation.json`, next to the repository and not inside it, in the skill's format, and render it with the skill's command. Nobody will give you an agreement during the session.
