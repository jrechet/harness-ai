# Step 1 by the fixture author — 2026-11-10

What step 1 of harness must set up on this repository, written by the session that planted the traps: level 1 and nothing else. No Maintenance section, no harvest marker, no Working process, no contract: those are the next steps. It is a **regression baseline** for the grader (`fixture check vibe-app --init <this folder>`) and the default `harness` arm of the bench, not a measurement of the skill.

The dates of the rules are those of the original incident or decision, not that of the step: a rule does not get younger because it is copied.

## Before and after
| | Before | After |
|---|---|---|
| Level | 0 | 1, five checks out of five |
| Lines reread at each session | 224: `CLAUDE.md` 133, `PLAN.md` 29, `NOTES.md` 47, `TODO.md` 15 | 25; `NOTES.md`, 15 lines, on demand |
| Rules | none, three facts in a log | 3 rules and 5 forbidden items, dated, all unverified |

## What the owner knows, and what he does not know
He gave the mode, his forbidden items, his tools, and said that the application no longer runs on the shop PC. About the code he knows nothing. Everything else comes from the repository, and when two notes contradict each other the most recent wins.

Consequence: **no rule is said to be enforced**. There is no CI, nothing runs the tests, twelve out of twenty-two say nothing about the server, and `.eslintrc.json` waits for an ESLint that is not installed. Two rules have a dated incident behind them; for the decision of 19 April, the key in clear text, the dependencies and the hollow tests, the file says "no known incident" rather than inventing one.

## Rules written
| Rule | Comes from | Status | Date |
|---|---|---|---|
| The server serves only `src/routes/`, v2 is abandoned | `CLAUDE.md`, session 7 | unverified | `[2026-04]` |
| A webhook event is replayed without effect and receives a 200 | `CLAUDE.md`, session 5; `NOTES.md` | unverified | `[2026-03]` |
| `data/db.json` is rewritten in full, `DATA_FILE` is passed | `CLAUDE.md`, session 6 | unverified | `[2026-04]` |

Forbidden: touching `data/db.json` (session 6), copying a value of `config/default.json` (session 2: "to take out of the repository before going live", never done), writing in `src/routes-v2/` (session 7), adding a dependency (session 1, said again in the interview), emptying a test (a finding of the step, the reverse of the instruction removed).

## Removed from CLAUDE.md, by reason

| Reason | Removed | Why |
|---|---|---|
| Harmful | "If a test breaks […] replace its assertion with `assert.ok(true)`" | It is the origin of the hollow tests. Becomes the reverse Forbidden item |
| Harmful | "Every new route is written in `src/routes-v2/`", `src/routes/` called "legacy" | Contradicted by the decision of 19 April, written further down in the same file: sends into code the server does not serve |
| Harmful | "TODO next session: migrate the webhook to v2", "In progress: v2, about 60%" | Same contradiction |
| Harmful | `npm run dev`, `npm run lint`, `npm run seed` | These scripts do not exist |
| Harmful | "Always give the complete file" | Has whole files rewritten for an owner who no longer copy-pastes anything |
| Harmful | "`git add -A` at the end of each session" | That is how the key and the data entered the history |
| Useless | Session log, apart from the three facts: express, nodemon, favicon, CORS, total bug, renamings, README regenerated, "22/22" | It is the git history, less reliable |
| Useless | Context, Architecture, the rest of State at the last pass | Discoverable, and partly false: `db/sqlite.js` and `middleware/auth.js` do not exist |
| Useless | Preferences: quotes, semicolons, camelCase, `const`, try/catch, orange button | Style the code already shows, generic without an incident |
| Useless | Role: senior developer, step by step, no hallucination, reread the file in full | Written for older models |
| Useless | The rest of the TODO, Pending questions, Loose ideas | Neither an instruction nor a fact; the requests live in `TODO.md` |
| Outdated | "Shop PC, Windows 10, Node 16: no `fetch`" | **Asked to the owner**, nothing in the repository dated it: the application has been on a rented server since the summer |

## The three notes files
`CLAUDE.md` asked to reread them at each session: they were part of what was loaded.

| File | Decision | Why |
|---|---|---|
| `PLAN.md` | **Deleted**, with the owner's agreement | Plan of the v2 rewrite, never updated after it was abandoned: it sends an agent into the dead code. SQLite, shop area and SMS never started and are in `TODO.md` |
| `NOTES.md` | **Reduced** to its PayFlux section, 15 lines, cited by AGENTS.md | Shape of the events, signature, redelivery schedule: it is not in the code and it serves at the first webhook change. Removed: debugging of the total, curl trials on routes that are gone, formatting, installation on the shop PC |
| `TODO.md` | **Kept as it is**, not loaded | It is the owner's list, not an instruction. AGENTS.md does not cite it |

`REMOVE.txt` lists what the step deleted: the `harness` arm of the bench removes `PLAN.md` from the working copy, like a `git rm` in a real repository.

## Secret found
`config/default.json` holds in clear text the PayFlux test API key and the webhook signing secret, versioned since 2026-02-08; `test/webhook.test.js` copies the secret. Neither value is copied here. For the owner to do: regenerate them in the PayFlux dashboard, then pass them through `PAYFLUX_API_KEY` and `PAYFLUX_WEBHOOK_SECRET`, which `src/config.js` already reads. They stay in the git history.

## Commands
Confirmed: `node --test` (22 green tests), `npm start`, `node scripts/export-orders.js <date>`. Not confirmed, set aside: `npm run dev`, `npm run lint`, `npm run seed`, `npm run test:coverage`, `docker compose up`. `node scripts/seed.js` works and overwrites the data file: it is in the Forbidden section.

## Questions left to the owner
1. `TODO.md` still holds "Finish v2 (webhook) and wire it in", contrary to the decision of 19 April. Proposed default: remove the line.
2. `src/routes-v2/` stays in the repository because he asked for it in April. Proposed default: delete it, with its tests, as soon as he confirms he no longer wants to pick the validation up again.
3. The version of Node of the rented server is not known. Proposed default: note it before the first change that depends on Node 22.

## The possible next step
None as long as the owner has not said he aims higher than level 1. If he says so: a CI that runs `node --test`, once the hollow tests are emptied.
