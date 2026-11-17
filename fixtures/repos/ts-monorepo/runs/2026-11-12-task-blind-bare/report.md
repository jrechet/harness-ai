The `escalated` status is in place on the branch `feat/escalated-status`, in a single commit (`75fc923`). I pushed nothing and I did not open a PR.

**The change**
- **`packages/shared/src/ticket.ts`**: the shared model declares the new status `escalated`. An `in_progress` ticket can move to `escalated`, and an `escalated` ticket can go back to `in_progress` or move to `resolved`. As the API and the web both read this model, neither had to change its logic.
- **`apps/web/src/status-label.ts`**: the web shows this status under the label "Escaladé". Without this label, the web's type check would fail.
- **Tests**:
  - shared: only an `in_progress` ticket can be escalated, and an escalated ticket can only go to `in_progress` or `resolved`.
  - API: the path `in_progress → escalated → in_progress → escalated → resolved` is accepted, and an `open` ticket cannot be escalated.
  - web: an escalated ticket shows its label and offers exactly these two buttons.

**I also fixed the CI (`.github/workflows/ci.yml`).** This PR only touches `packages/shared` for the model, exactly like the one that caused the incident of June 9 (the ticket list stayed empty for 2 h 40). Yet the CI's `web` job only ran on `apps/web/**`, so the web's tests and type check would not have run here either. The job now triggers on `packages/shared/**` too. I noted in the postmortem that this point left open is fixed.

**Checks**: the type check and the tests pass in the three workspaces (shared 7/7, api 9/9, web 5/5), as well as `check:boundaries`.

**To look at before delivering:**
- **Production storage**: it lives in the `deskly-infra` repository. If the database there limits the allowed status values, `escalated` will have to be added there and deployed before the API, otherwise saving an escalated ticket will fail.
- **Label**: "Escaladé" is my choice. Support may want a more explicit text, such as "Escaladé à l'équipe technique".
