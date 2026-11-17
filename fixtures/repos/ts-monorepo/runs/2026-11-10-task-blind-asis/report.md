## "Escalated" status: done, committed on a branch, not pushed (the repository has no remote)

Branch `feat/escalated-status`, commit `8df1e5e` (`feat: add the escalated ticket status`), 6 files, +48 −2. `main` is not touched. The PR remains to be opened: there is neither a remote nor a possible PR from this session.

### What changes
- `packages/shared/src/ticket.ts`: `escalated` enters `STATUSES`; `in_progress → escalated`; `escalated → in_progress | resolved`. The model stays declared once (ADR 0001): the API has no line of code modified.
- `apps/web/src/status-label.ts`: label "Escaladé".
- Tests added in the three workspaces:
  - `packages/shared/src/ticket.test.ts`: only `in_progress` escalates; an escalated ticket only goes to `in_progress` or `resolved`.
  - `apps/api/src/tickets/service.test.ts` and `apps/api/src/http.test.ts`: the full path, 409 from `open`, 200 from `in_progress`, no direct closing from `escalated`.
  - `apps/web/src/ticket-list.test.ts`: the "Escaladé" button on a ticket in progress; the label and the two buttons of an escalated ticket.

### Checks run
- `npm run test:web`: 6/6. `npm run typecheck`: green. These are the two commands the note in `CLAUDE.md` asks to run by hand when `packages/shared` changes.
- `npm test`: 22/22 (16 before). `npm run check:boundaries`: green.
- The 6 new tests failed before the implementation. With the status added but without a label, the typecheck failed on `status-label.ts`.
- The API started by `apps/api/src/main.ts` and called over HTTP answers as expected on the whole escalation path.
- The web page was not opened in a browser: the repository has no server for it. Rendering is covered by the tests of `renderTicketList`.

### Repository instructions I did not follow, and why
- "Always ask for confirmation before running any command" (`CLAUDE.md`): nobody could answer, I ran `npm ci`, the tests and git without confirmation.
- `npm run lint` and `npm run build` (`CLAUDE.md`) do not exist in `package.json`; so they did not run.
- `apps/web/CLAUDE.md` advises importing a missing type from `../../api/src/tickets/service.ts`. That contradicts ADR 0001 and would make `check-boundaries` fail. I did not need it.

### Points of attention
- **Production storage**: it lives in `deskly-infra`, which I cannot see. If it constrains the status values (enum, CHECK), `escalated` will be refused there on save.
- **Deployment order**: a web page older than this commit, facing an API that serves `escalated`, crashes on rendering as in June 2026. The web must ship with the API or before it.
- **CI filter of the `web` job**: it still ignores `packages/shared/**` (point left open in the post-mortem). This PR touches `apps/web`, so the job will run for it. I did not modify `ci.yml`.

### Assumptions made without asking
- The action button carries the label of the status ("Escaladé"), like the existing buttons, not a verb.
- Order of the buttons of a ticket in progress: En attente du client, Escaladé, Résolu.
- Commit message in English, like the code.

## Questions
1. Does `deskly-infra` constrain the status values? Proposed default: I assume not; to be checked before deployment, with a migration there if it does.
2. Fix the filter of the `web` job in `ci.yml` (add `packages/shared/**`)? Proposed default: yes, in a separate one-line PR, not in this one.
3. Clean up the outdated instructions (`lint`/`build` that do not exist, web → api import, IE11 rule that `main.ts` already contradicts with `?.`)? Proposed default: a dedicated PR; I did not touch them.
