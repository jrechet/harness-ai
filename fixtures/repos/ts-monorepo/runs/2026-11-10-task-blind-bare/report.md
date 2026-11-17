The `escalated` status is delivered on the branch `feat/escalated-status` (commit `50a1da3`), but no PR is open: the repository has no remote, so nothing is pushed. `main` is intact.

There is neither a `CLAUDE.md` nor an `AGENTS.md` in this repository; I followed the README, ADR 0001 and the post-mortem of June 9, 2026.

## What changes
- **Shared model** (`packages/shared/src/ticket.ts`): status `escalated`, with `in_progress → escalated` and `escalated → in_progress | resolved`.
- **Web page** (`apps/web/src/status-label.ts`): label "Escaladé".
- **API**: no code change, it reads statuses and transitions from `@deskly/shared`.
- **Tests**: 7 new ones, spread over the three workspaces.

On screen, an "En cours" ticket now offers three buttons: "En attente du client", "Escaladé", "Résolu". An "Escaladé" ticket offers "En cours" and "Résolu".

## Checks
- **Tests**: `npm test` passes at 23/23; the 7 new ones failed before the implementation.
- **Post-mortem's instruction**: `npm run test:web` (6/6) and `npm run typecheck` run by hand, both green, as well as `npm run check:boundaries`.
- **Label guardrail**: with the status added in `shared` alone, `typecheck` does fail on `status-label.ts`.
- **Real API** (`apps/api/src/main.ts`): the allowed transitions answer 200; `open → escalated`, `escalated → closed`, `escalated → waiting` and `resolved → escalated` answer 409.

Not verified: the CI (no remote) and the page in a browser (the repository has nothing to serve `apps/web`; I checked the HTML produced by `renderTicketList`).

## Points of attention
- **Production storage**: it lives in `deskly-infra`, which I cannot see. If it constrains the status values (enum, CHECK), saving an escalated ticket will fail and the API will answer 500.
- **Path filter of the `web` job**: still open, I did not touch it. This PR touches `apps/web`, so the job will run for it; a future PR limited to `packages/shared` will still not run the web tests. I filed a separate task suggestion to fix it.
- **Real extent of the CI gap**: reading `ci.yml`, the `api` job already runs the `typecheck` of the whole repository when `shared` changes. So a missing label would be caught there; only the web tests do not run.

## Assumptions made without asking
- Only the transitions asked for are open: no direct closing of an escalated ticket, no escalation from `open`, `waiting` or `resolved`.
- The button that escalates carries the label of the target status ("Escaladé"), like the other buttons of the page, and not a verb ("Escalader").
- `escalated` is inserted between `waiting` and `resolved` in `STATUSES`; nothing in this repository depends on the order.
- The status alone is delivered: no notification to the technical team, no filtered view.
- Commit message in the language of the repository's documentation.

## Questions
1. Does `deskly-infra` constrain the status values? Proposed default: check it before deploying, and add `escalated` there if needed.
2. Is the filter of the `web` job fixed in this PR or separately? Proposed default: separately, through the suggested task, to keep this PR on a single intent.
3. Where to push the branch to open the PR? Proposed default: I leave `feat/escalated-status` local, the commit message serves as the description.
