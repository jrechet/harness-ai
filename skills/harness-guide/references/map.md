# Map: what you want → what to use

Every skill and every top-level command of both plugins has its line here; `cli/tests/test_guide.py` fails when one is missing. Skills of the `ai-sdlc` plugin need it installed: `/plugin install ai-sdlc@harness-ai`.

## First: maybe nothing

A model reads a repository well. If the user only wants to code, fix or explain something, no skill is needed: answer the request itself. A short `AGENTS.md` (what the agent cannot discover alone, the forbidden actions) is the one thing almost every repository gains from; beyond that, each level is a choice, and stopping is fine (`${CLAUDE_PLUGIN_ROOT}/docs/maturity.md`).

Not sure which of the lines below fits: `harness-guide`, the skill that reads this map.

## The AI setup of one repository (plugin `harness-ai`)

| You want to… | Use | Not this |
|---|---|---|
| Start with Claude Code, Copilot or Cursor on a repository; write or redo `AGENTS.md` / `CLAUDE.md` | `harness-init` | `harness-step` once level 1 is reached |
| Know where the repository stands, what the next step is, go up one level, or stop at one | `harness-step` | `harness-audit` for a full review |
| Have the level told as a medal, the unlocked achievements, a badge or the medals page | `harness-medals` | it changes nothing but its medals file: to move, `harness-step` |
| Audit an existing setup: is each rule, skill, agent, script and workflow in its place, what still serves | `harness-audit` | `harness-design` for one piece only |
| Have one skill, agent or rule reviewed and explained: what is good, what is weak, which concept is behind it; nothing is written, no level is mentioned | `harness-coach` | `harness-design` to place the pieces and set up the files |
| Create one skill, agent, rule, hook or tool, or put an existing one right: "skill or agent?", "should this be code?", "where do I put this?" | `harness-design` | `harness-coach` to understand first, without changing anything |
| Turn what happened in PRs and reviews (`rule:` comments, fixes after the fact, reverts) into rules | `harness-harvest` | `harness-audit` if no change is wanted |

## A team's path from ticket to production (plugin `harness-ai`)

| You want to… | Use | Not this |
|---|---|---|
| Know whether LangChain, LangGraph, Temporal, a workflow engine or Rust is needed, before building | `flow-why` | `flow-place` once a flow is written |
| Write down how a ticket type goes from ticket to production, as one checked file | `flow-map` | `harness-step` for one repository's level |
| Know where each step of that flow belongs, and whether one needs an engine | `flow-place` | `harness-design` for a piece inside one repository |

## One ticket or one change (plugin `ai-sdlc`)

| You want to… | Use | Not this |
|---|---|---|
| Know whether a ticket is ready for an agent, and what it lacks | `ticket` | `dev` to do it |
| Have a ticket developed up to the pull request | `dev` | `review` to read someone's change |
| Have the tests derived from the acceptance criteria, and checked by a program | `qa` | `dev` writes the code |
| Have a PR or a branch reviewed | `review` | `secu` for the security angle only |
| Look at a change for secrets, scanners, sensitive places | `secu` | `review` for a general review |
| Prepare a release: what ships, is CI green on that commit, version and notes (nothing is published) | `ship` | it never deploys |
| Investigate a production incident and turn it into a ticket (nothing is touched in production) | `run` | `dev` to fix it, `ship` to deliver the fix |

## Neighbours that are often confused

- **init, step or audit?** Nothing yet, or a long file to redo: `harness-init`. Level 1 reached and you want the next thing: `harness-step`. You want a verdict on everything that exists, with removals: `harness-audit`.
- **coach or design?** Both read one piece with the same grid. `harness-coach` explains and stops: what holds, what does not, in named concepts. `harness-design` shows the plan and sets up the files.
- **design or audit?** One piece, new or existing: `harness-design`. The whole setup: `harness-audit`.
- **harvest or audit?** Evidence from real PRs, with a PR of changes: `harness-harvest`. A review of what exists today: `harness-audit`.
- **step or medals?** Both start from the same measurement; `harness-medals` only shows it, `harness-step` acts on it.
- **flow-place or harness-design?** A step of a team workflow spanning tickets and repositories: `flow-place`. A rule, script or hook inside one repository: `harness-design`.
- **review or secu?** Both only comment. `secu` runs the scanners and looks at the sensitive places; `review` reads the whole change.

## Commands without a skill

The `harness-ai` plugin installs the whole repository, so both command lines are under its folder: `python3 "${CLAUDE_PLUGIN_ROOT}/cli/harness.py" <command>` and `python3 "${CLAUDE_PLUGIN_ROOT}/plugins/ai-sdlc/cli/ai_sdlc.py" <command>` (from a clone: `cli/harness.py`, `plugins/ai-sdlc/cli/ai_sdlc.py`). `--help` on each says the rest.

| Command | What it gives |
|---|---|
| `harness status` | the level 0 to 4 and the next action; `--map` in plain words, `--page` as one HTML page |
| `harness target` | declares where you want to stop: beyond it, nothing is proposed |
| `harness ignore` | sets a check of the levels aside, with its reason: the level is then reached without it, shown as set aside; alone, lists the checks |
| `harness rules` | each rule of `AGENTS.md`, its date, its guardrail, its why |
| `harness medals` | the medal and the achievements, `--page` for the page |
| `harness commands` | the commands an agent does not guess: what the CI really runs |
| `harness fresh` | what has aged: a skill citing a vanished file, a late harvest |
| `harness place` | where a piece of a harness goes, from closed questions (`grid`, `one`, `plan`); `review` tells an existing piece as named concepts |
| `harness report` | a one-page HTML assessment, always in the same format |
| `harness serve` | a local page that follows the state (http://127.0.0.1:8787) |
| `harness flow` | a ticket workflow on paper: `fit`, `new`, `check`, `place`, `next`, `status` |
| `harness harvest` | the GitHub evidence `harness-harvest` reads |
| `harness audit` | checks the file `harness-audit` writes |
| `harness fixture`, `harness bench`, `harness keys`, `harness progress` | for this repository's own maintenance: sample projects, the task bench, answer keys, the progress plan |
| `ai_sdlc.py context`, `ai_sdlc.py status` | what the base checklists are and what the team added in its repository |
| `ai_sdlc.py review`, `ai_sdlc.py size`, `ai_sdlc.py dev`, `ai_sdlc.py ticket`, `ai_sdlc.py qa`, `ai_sdlc.py secu`, `ai_sdlc.py ship`, `ai_sdlc.py run` | the deterministic half of each `ai-sdlc` skill |
| `ai_sdlc.py ci` | the same gates in a pipeline: `ci pr` on a pull request, `ci main` on the delivery branch |
| `ai_sdlc.py measure` | a team's pull-request signals over a period, agent authors apart |
| `ai_sdlc.py guard` | says whether a shell command delivers (tag, publish, deploy); the plugin's hook refuses it |
| `ai_sdlc.py fixture` | grades the sample cases of the plugin |

## Where to read more

These pages ship with the `harness-ai` plugin, not with the user's repository: read them under the plugin folder.

| Question | Read |
|---|---|
| What the five levels are, and why stopping is fine | `${CLAUDE_PLUGIN_ROOT}/docs/maturity.md` |
| What each skill can really do today, and how it was measured | `${CLAUDE_PLUGIN_ROOT}/docs/capabilities.md` |
| How to decide where a step of a workflow goes | `${CLAUDE_PLUGIN_ROOT}/docs/workflow-harness/decide.md` |
| LangChain, LangGraph, engines, Rust, cost | `${CLAUDE_PLUGIN_ROOT}/docs/workflow-harness/` (`langchain.md`, `langgraph.md`, `engines.md`, `rust.md`, `costs.md`) |
| The ticket-to-production plugin, its design and a course | `${CLAUDE_PLUGIN_ROOT}/docs/ai-sdlc/README.md`, `${CLAUDE_PLUGIN_ROOT}/docs/ai-sdlc/course/index.html` |
| Examples of what the commands produce | `${CLAUDE_PLUGIN_ROOT}/docs/examples/` |
| Sample projects with their traps, to try a skill | `${CLAUDE_PLUGIN_ROOT}/fixtures/` |
