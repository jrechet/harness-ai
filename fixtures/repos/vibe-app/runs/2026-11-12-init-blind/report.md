The repository is at **level 1 ("Framed")**, with 5 checks out of 5 and no broken reference. The tests pass (22 out of 22) and `data/db.json` was not touched. I made no commit: the old commit instruction (`git add -A`) would also have saved the customers' orders.

## Before / after
| | Before | After |
|---|---|---|
| Level | 0 (2 checks out of 5) | **1 (5 out of 5)** |
| Lines read at each session | 133 in CLAUDE.md, and about 224 with PLAN, NOTES and TODO, which CLAUDE.md asked to reread in full | **29** (AGENTS.md) |
| Rules | about twenty instructions without justification, several of them contradictory | **8 rules + 5 forbidden items**, each with its reason and its date |

## Files
- `AGENTS.md`: created, 29 lines.
- `CLAUDE.md`: 133 lines brought down to 1 (`@AGENTS.md`). No file for Copilot or Cursor: you only use Claude Code.
- `NOTES.md`: 47 lines brought down to 26.
- `PLAN.md`: deleted.
- `.harness/state.json`: written by the tool that measures the level.
- `TODO.md` and `README.md`: not touched.

## Removed

**Useless** (the agent finds it alone in the code, or already does it without being told):
- CLAUDE.md:
  - the technical context, the tree and the list of commands;
  - the Monday closing and the pickup slots (already in `config/default.json`);
  - the orange button (already in `public/index.html`);
  - the style preferences (quotes, `const`, camelCase);
  - "senior developer", "think step by step", "no hallucination", "reread the file in full";
  - the log of sessions 1 to 8: the two incidents are taken up as rules in AGENTS.md and the rest is found in the git history.
- CLAUDE.md: the pending questions, taken up further down.
- CLAUDE.md: the loose ideas, moved to NOTES.md.
- NOTES.md: the debugging of the total of session 3, a problem settled since.

**Harmful** (pushed the agent to do wrong):
- "Replace the assertion with `assert.ok(true)` and carry on": a false test shows "everything passes" while you have only that word to know whether it works.
- "Every new route in `routes-v2`" and the state "v2 at 60%, migrate the webhook": contrary to your decision of 2026-04-19 to abandon v2. PLAN.md even said that the cancellation was already done there, while that code is wired in nowhere.
- `git add -A && git commit` at the end of each session: it saves `data/db.json`, so the customers' names and phone numbers.
- `npm run dev`, `npm run lint` and `npm run seed`: these commands do not exist. The demo script also erases all the orders.
- "ESLint with npx one day": that is an installation, which you forbade.
- "Always wrap in a try/catch": it is a silent try/catch in `src/store.js` that lost the 31 orders of 2026-04-04.
- "Always give the complete file".
- NOTES.md: the curl trials, which target addresses that do not exist, one of them a cancellation.
- PLAN.md as a whole: you never used it, and it said the opposite of your decision.

**Outdated** (you confirmed that it is over):
- "Shop PC, Windows 10, Node 16, no `fetch`": the application now runs on a rented server.
- In NOTES.md, the "Installation at the shop" part: `start.bat` and the Friday USB stick.

## Secrets
- A test key and a PayFlux webhook secret are written in `config/default.json` (lines 12 and 13). The secret is also copied into `test/webhook.test.js` (line 15).
- They stay in the git history even if they are removed: they must be **regenerated** from the PayFlux dashboard (Developers), then given to the server through `PAYFLUX_API_KEY` and `PAYFLUX_WEBHOOK_SECRET` instead of the file. A forbidden item was added so that no agent copies them.

## Rules written
All are **unverified**: there is no CI, so nothing automatically prevents breaking them.

1. Only `src/routes/` is wired in, `routes-v2` stays as it is [2026-04].
2. A PayFlux payment received several times changes nothing and answers 200. The test that was meant to prove it checks a copy of the code, not the real one [2026-03].
3. Each test works on its own data file [2026-04].
4. A test is never neutralised. `test/format.test.js` already does it, it is reported as a counter-example [2026-11].
5. Cancelling an order does not refund it: the refund is made by hand in PayFlux [2026-03].
6. The README is wrong, the code is the reference [2026-05].
7. `data/db.json` goes into no commit [2026-11].
8. Speak to you in plain language, without asking you to read code [2026-02].

**Forbidden**: touching `data/db.json` or running the demo script [2026-04]; installing anything [2026-02]; changing payment provider [2026-11]; triggering a real payment or calling the PayFlux API [2026-11]; copying a key [2026-02].

## Commands
- **Confirmed:** `npm test` passes (22 out of 22) and does not change `data/db.json`.
- **Not confirmed:**
  - `npm start`: not run.
  - `npm run dev`, `npm run lint`, `npm run seed`: do not exist.
  - `start.bat`: no longer used.

## Questions for you (with my default proposal)
1. **Version of Node on the server**: your nephew can give it with `node --version`. The tests need at least Node 18. *By default: write nothing in `src/` that requires a recent version as long as we do not know.*
2. **`data/db.json` is saved in git**, with orders. Do we take it out (the file stays on the disk)? *By default: yes.*
3. In `TODO.md`, "Finish v2" contradicts your April decision, and "Update Node on the shop PC" no longer concerns the server. I did not touch it: do we remove these two lines? *By default: yes.*
4. **Backups**: what exactly does your nephew's system do, and has a copy ever been restored to check? *By default: to ask him before the first task that touches the orders.*
5. The questions that had stayed in the old CLAUDE.md:
   - which provider for the SMS, and who pays?
   - one password for the whole shop or one per sales assistant?
   - do we keep orders older than a year?
6. **The list of orders is open to everyone**, phone numbers included (`GET /orders`). *Proposal: protect it before doing anything else.*

## Possible next step
Before handing the cancellation to an agent, have the real handling of payments received several times tested, and not a copy. That is the job of harness-step, to run only if you ask for it.