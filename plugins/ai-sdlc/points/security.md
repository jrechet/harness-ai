A change is looked at from the security angle in this order:
- **Secrets.** No key, no token, no password in the code, the tests, the configuration or the commit messages. A pushed secret is exposed: it is revoked, it is not erased.
- **Inputs.** What comes from outside (request, file, environment variable, text of a ticket or a page) is validated before it is used in a query, a command, a path or a rendering.
- **Permissions.** The change widens no role, no permission, no allowed origin, nor what an agent can do, unless that is the subject of the ticket.
- **Dependencies.** An added or upgraded dependency is a decision: it is stated in the PR, with its reason.
- **Scanners.** What the team's scanners report on the lines of the change is fixed. An exception is decided by a human, in the PR, never by a comment in the code.

What enforces this (secret detection, dependency analysis, scanners) runs in the CI and blocks the merge. This phase does not replace it.
