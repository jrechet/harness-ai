The `escalated` status is in place and committed on the branch `feat/escalated-status` (commit `483c284`), but neither pushed nor opened as a PR: the repository has no remote. Tests (20/20), typecheck and boundary check pass, run in full by hand as `AGENTS.md` asks for a change in `packages/shared`.

## What changed
- **Shared model** (`packages/shared/src/ticket.ts`): new status `escalated`, transition `in_progress → escalated`, and `escalated → in_progress` or `resolved`.
- **Web** (`apps/web/src/status-label.ts`): label "Escaladé".
- **API**: no production code modified, it reads statuses and transitions from `@deskly/shared`.
- **Tests**: one test added in each of the four test files (shared model, service, `PATCH` route, web list). The four failed before the change.

## Point not verified
The production storage lives in `deskly-infra`, which I can neither read nor modify from here. If it constrains the status values (enum, column constraint), saving an escalated ticket will fail in production. It is to be checked before the merge.

## Assumptions made without asking
- Only `in_progress` leads to `escalated`, and an escalated ticket is not closed directly: strict reading of the request.
- The escalation button shows "Escaladé", because the existing buttons carry the label of the target status ("Résolu", "Fermé").
- The path filter of the `web` job in `ci.yml` stays as it is, out of scope. Here the job will run anyway, since `apps/web` is touched.

## Questions
1. Does the storage of `deskly-infra` accept a new status value without a change? Proposed default: do not merge until the owner has confirmed it.
2. Where to push the branch to open the PR? Proposed default: the owner adds the remote and pushes `feat/escalated-status` to `main`.
