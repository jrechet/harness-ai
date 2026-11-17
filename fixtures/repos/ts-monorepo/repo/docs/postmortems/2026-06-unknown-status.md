# Incident of June 9, 2026 — the ticket list empty for all of support

## What happened
A PR added the `waiting` status in `packages/shared`. The API served it as soon as it was deployed. The web page had no label for that status: rendering threw an exception at the first waiting ticket and the list stayed empty for 2 h 40.

## Cause
The PR only touched `packages/shared`. In `ci.yml`, the path filter of the `web` job only contains `apps/web/**`: the job did not run, neither its tests nor its type check. The `api` job does trigger on `packages/shared/**` too, but it only checks its own workspace. Nobody ran the web locally: there is no command that replays everything.

## Fixes
- `apps/web/src/status-label.ts` is typed `Record<Status, string>`: a status without a label no longer compiles.
- A web test checks that every shared status has a label.

## What remains open
The path filter of the `web` job has not been fixed. The two fixes above only protect if the `web` job runs, which it still does not when only `packages/shared` changes. The instruction in the meantime: run `npm run test:web` and `npm run typecheck:web` by hand.
