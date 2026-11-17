# Request: a tool that prepares a PR from a ticket

What the team wants:

- It reads the Jira ticket and its acceptance criteria.
- It refuses to start if the ticket has no acceptance criteria.
- It always follows the same steps: branch, tests first, code, then PR.
- The branch name is derived from the ticket: `type/KEY-123-short-title`.
- It never merges its own PR, and nothing merges without an approval.
- It cannot modify the files of `.github/workflows/`.
- No PR merges if its tests do not pass.
- Before opening the PR, a fresh look reviews the diff against the acceptance criteria.
- It decides by itself how to split the work into commits.
- It comments on the Jira ticket with the link to the PR.
- It knows that the project is in TypeScript, with pnpm.
- In `migrations/`, an existing migration is not modified: a new one is added.
