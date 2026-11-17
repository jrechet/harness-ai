I added the `escalated` status on the branch `feat/ticket-escalated` (commit `824d1b1`). No PR is open: the local repository has no remote configured, so I could push nothing. The PR description is below, ready to paste.

All the tests and checks pass: the three `test:*` (shared 7, api 7, web 5, no failure), the three `typecheck:*` and `check:boundaries`. I ran the web's by hand, as `AGENTS.md` and the postmortem of June 9 ask.

## What I modified
- **`packages/shared/src/ticket.ts`**: new status `escalated`. An `in_progress` ticket can now move to `escalated`, and an `escalated` ticket can go back to `in_progress` or move to `resolved`.
- **`apps/web/src/status-label.ts`**: label "Escaladé". The file is typed `Record<Status, string>`, so the web no longer compiles if a status has no label.
- **`packages/shared/package.json`**: version moved from 1.4.0 to 1.5.0. It is the repository's rule, so that `deskly-infra` redeploys the storage. `package-lock.json` is updated accordingly.
- **Tests**:
  - on the shared side, only an `in_progress` ticket can move to `escalated`, and an `escalated` ticket can only go to `in_progress` or `resolved`;
  - on the web side, an escalated ticket shows its label and offers exactly these two buttons.

## Points to check
- **CI**: the `web` job still does not trigger when only `packages/shared` changes. This PR also modifies `apps/web`, so it will run here. The problem remains open for the next changes to the model; I did not touch it because it was not in the ticket.
- **Version**: I chose a minor bump (1.5.0) because a status is added. The repository sets no rule on this.
- **`deskly-infra`**: I did not modify it, it is forbidden. If its storage must accept the new status, that remains to be done on their side.
- **Label**: "Escaladé" is my proposal, to be validated by support.

---

**PR description:**

> **feat(shared): `escalated` status to escalate a ticket to the technical team**
>
> - New status `escalated`. Transitions: `in_progress → escalated`, `escalated → in_progress | resolved`.
> - Web label "Escaladé".
> - `@deskly/shared` 1.4.0 → 1.5.0 (redeployment of the storage by `deskly-infra`).
> - Tests in shared and web for the new transitions.
>
> Checked locally: `test:shared`, `test:api`, `test:web`, `typecheck:shared`, `typecheck:api`, `typecheck:web`, `check:boundaries`.
>
> 🤖 Generated with [Claude Code](https://claude.com/claude-code)
>
> (private session link removed)
