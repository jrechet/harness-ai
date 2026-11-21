# Assessing a team's AI SDLC

Date: 2026-11-21. State: a study and a proposal, revised after two reviews (section 10). Nothing described in sections 4 to 8 is built.

The need, in the owner's words: a team says "we built an AI SDLC, we think it is great". We want to look at it with everything this repository knows, tell the team where it stands, and show a road. The result must help to **build** and help to **understand**, equally.

Words used in this document and in the code. The outputs shown to a team use the team's own words instead (section 5.5).

- **Team workflow**: the path a change takes in a team, from the ticket to production and to the incident, with agents working on it. It is what the team calls its "AI SDLC".
- **Piece**: one thing that carries part of that path. A prompt, an agent definition, a script, a pipeline job, a required approval.
- **Gate**: a piece whose job is to stop a bad change.
- **Forge**: the server that hosts the repositories and decides what may be merged (GitHub, GitLab, Forgejo).
- **Pointer**: a line that says "this piece of our workflow is here", as `repository:path:line` or `repository:path#job`.
- **Hold**: how a piece is carried. Four values, from weakest to strongest:
  - **asked**: a sentence asks for it, nothing checks it;
  - **runs, ignored**: a program runs, but its result changes nothing (a job allowed to fail);
  - **checked**: a program runs and can say no, but nothing forces anyone to listen;
  - **enforced**: the forge refuses the merge without it, and the change it judges cannot alter it.
- **Could not read**: the program could not establish the fact. Always printed with its reason and with what would make it readable. It is neither a pass nor a failure.

## 1. The answer in ten lines

1. **Partly.** No skill we have takes a team workflow as its subject.
2. `harness-audit` can be pointed at it and gives a useful expert critique. But it is an opinion, on one repository at a time, with no road.
3. The measured ladder (`harness status`, the medals, the page) reads one repository and looks for our own writing conventions. On a team that built its own workflow, its first screen says "level 0, write an AGENTS.md". That is false and it is insulting.
4. The `ai-sdlc` plugin holds about forty criteria of a sound workflow, as code. Each judges one ticket, one change or one release. None judges a team.
5. Missing: reading several repositories at once, reading a pipeline's whole effective definition, following a gate from one repository to another, reading the forge settings, a road for a workflow, and a way to keep apart what is measured, what the team says and what a reviewer thinks.
6. Proposal: one new skill, `harness-team`, and one command family, `harness team`, in the existing CLI.
7. The command draws the team's workflow across repositories before any question, with no model reading. The team's own claims are answered first, each with a file and a line.
8. The road has four levels: **Drawn, Guarded, Locked, Proven**. The headline is the team's own target; the four medals are a secondary mark.
9. One rule carries the design: a level rises only on **positive evidence a program read**. A sentence, an answer, an export, a file name or an absence of evidence never raises it.
10. About half is reuse. The largest new piece is a reader of a pipeline's effective definition. The first slice gives the drawing and the Drawn level on two sample teams, in two to three weeks.

## 2. What exists and how far it goes

"Our dialect" below means our file names and writing conventions: `AGENTS.md`, the "Mode" line, "Enforced by:", `docs/agents/<point>.md`.

| What exists | What it can say about a team workflow | Where it stops |
|---|---|---|
| Skill `harness-audit` (`skills/harness-audit/SKILL.md`) | Judges each piece with a vocabulary that fits any setup: four layers, eight verdicts, three priorities (`SKILL.md:25-41`, `66-82`). Walks a process step by step and lists the steps only a prompt carries (`SKILL.md:52-53`). | Everything is the model's judgement, including the score out of 100. One repository per run (`SKILL.md:12`). No road. About 140,000 tokens for one small repository. |
| `harness status`, `--map`, `--page`, skill `harness-step` (`cli/harnesslib/facts.py`, `maturity.py`, `page.py`) | Measures one repository at a time, read-only, with a plain map, a target and a next step. | Reads a fixed list of files (`facts.py:21-24`) in our dialect (`facts.py:50-69`). 18 checks, none about a phase or a gate. A team with strong gates and no `AGENTS.md` reads "level 0", with two false sentences (`maturity.py:50-54`). |
| Skill `harness-medals`, `harness medals` (`cli/harnesslib/medals.py`) | Shows a level as a medal with dated achievements that can be lost, for two kinds of subject (`medals.py:35`, `191-257`). | No kind for a workflow. An achievement is a boolean (`medals.py:44-47`): no "could not read". Writes inside the one repository it reads (`medals.py:383`). |
| Skill `harness-design`, `harness place` (`cli/harnesslib/place.py`, `placement.json`) | Says by code where a piece should live among 20 places, and gives a verdict when told where it lives today (`place.py:182-190`). | Someone must first name the place, as one of its 20 identifiers. Its layers do not say whether a job can fail or is required. It judges a wrong place, never a missing piece. |
| `harness report build` (`cli/harnesslib/report.py`) | Renders an assessment as one page with a status per finding, with paths from several repositories. | Checks that evidence is present, not that it exists (`report.py:63-67`). No kind for a workflow. |
| Skill `harness-harvest`, `harness harvest github` (`cli/harnesslib/github.py`) | Counts agent changes fixed after the merge, from real pull requests. | GitHub only. Never played. Agent changes are found from markers someone declares (`github.py:179-202`), and "fixed after" from a title and file-overlap heuristic (`382-405`). |
| `harness rules`, `commands`, `fresh` | Per repository: the rules, the commands of the pipeline, what cites a deleted file. | The pipeline reader is line patterns, not YAML (`commands.py:124-235`): no events, no "allowed to fail", no include, no inheritance. Delivery jobs are found by their name (`commands.py:47`). A gate in another repository is reported "broken" (`facts.py:221-258`). |
| The phase gates of `plugins/ai-sdlc/cli/aisdlclib/` | About forty criteria as code, each with three results: ok, failed, unmeasured. Some need only git: a disabled test (`qa.py:76-107`), a secret (`secu.py:234-270`), a silenced scanner (`secu.py:273-287`), a command that delivers (`guard.py:439`). | Each judges one change, as a diff against the working tree. None reads a past change at a commit. No loop, no aggregation. |
| The template `plugins/ai-sdlc/ci/gates.yml` | States what a sound gate job has: code fetched at a fixed version, read-only permissions, settings read on the target branch. Says itself that without a required check a change can remove it and pass (`gates.yml:5-8`). | It is our template, not a checker of someone else's file. Nothing reads the forge. |
| `harness fixture`, `harness bench` | Grades a skill against planted defects, by program. | Every sample is one repository, bound to `fixtures/repos/<name>/repo` (`fixtures.py:22-27`, `69-79`). |

One fact sums up the gap. On a made-up team of three repositories ("Atlas": an orchestrator service, shared pipeline templates, one product), the existing commands answered "level 0" for two repositories and reported the product's real cross-repository gate as a broken reference. The gate job itself was allowed to fail. No command saw it.

## 3. What a team's AI SDLC is made of

| Part | Examples | Where it lives | How it is found |
|---|---|---|---|
| The trigger | A label on a ticket, a webhook, a comment that calls a bot | Tracker settings, pipeline events, an orchestrator's code | Pipeline events by the scan. Tracker settings: could not read, a question. |
| The stops on the path | By default our seven: ticket, development, review, tests, security, delivery, incident | Spread over the pieces below | See the three passes. The team may rename, merge or add stops. |
| Agents and prompts | Instruction files, agent definitions and their tool lists, prompts, connectors | Product repositories, an orchestrator, sometimes a database | The scan reads known folders and formats. A home-made format is listed, its content not judged. A prompt in a database: could not read. |
| Code and checks | Scripts, linters, hooks, permission lists | Any repository | The scan lists them and which job calls them. |
| The pipeline | Jobs, shared templates, the flags that let a job fail | Pipeline files, often in a shared repository | Read as a whole effective definition (section 4.3). Jenkins is listed, not read. |
| Human approvals | Who must approve a merge, who starts a delivery, who may skip a check | Forge settings | Read live from the forge. An export is shown as declared. |
| The measures | Time from ticket to merge, changes fixed after the fact, rollbacks, cost | Forge history, deployment tool, model gateway | The first two from the forge. The others: could not read. |
| The platform | Tokens kept from the agent, sandboxes, network limits | Outside every repository | Always could not read. A question, shown as declared. |

**How the pieces are found without the team describing everything.** Three passes, from cheapest to dearest.

1. **The scan, by program.** The team gives clones. The scan reads each clone's remote address to learn which forge project it is, and prints that mapping so the team can correct it. It sorts a piece onto a stop only by a **content rule** written as data: a known test runner for tests, a known scanner binary or action for security, a command the delivery detector recognises for delivery, a known agent file format for agents. The matching line is the evidence. A match on a name alone is marked "proposed", not "found". Ticket, review and incident have no content rule: the scan never sorts into them. An include of another project is resolved only when that project's identity matches a given clone, and is read at the included version with `git show`; if that version is absent, could not read. A moving version (a branch) is recorded as moving.
2. **The reading, by an agent.** For what the scan could not sort, an agent proposes pointers, one repository per fresh sub-agent. It writes them as data. The program checks that every cited line exists, that the quote is word for word, and that the pointer has the type its piece requires (section 4.3). Before the reading, the skill prints an estimate ("14 files not sorted in 3 repositories, about N tokens; it would place the 2 stops where nothing was found") and waits.
3. **The questions, to the team.** At most three in a session. The rest goes to a visible "open questions" list, answerable later or never.

Pointers found by the scan are accepted without asking. Only the agent's proposals are confirmed by the team. The team's own names are kept: review rules held in `REVIEW.md` are pointed at `REVIEW.md`.

## 4. The proposal

### 4.1 The skill: `harness-team`

- **It triggers** on: "assess our AI SDLC", "we built our own agent workflow, is it good", "look at how agents work across these repositories". In French: « analyse notre AI SDLC », « on a fait notre harness, il vaut quoi ». Not for one repository's instruction files (`harness-step`, `harness-medals`), a deep critique (`harness-audit`), or placing one piece (`harness-design`).
- **Its first line, before the scan:** "Read-only. Nothing in your repositories is run or changed. Nothing leaves this machine. Results are written in `<folder>`. Reading your merge rules later needs a token with this scope: `<scope>`." Secret values are masked in every output; only file, line and commit are shown.
- **It shows first** the drawing and the answer to the team's claims (section 5.5), from `harness team scan` then `harness team map`. If the team stated claims in its request, they are used; otherwise the first question asks for them.
- **It asks at most three questions**, each with its reason and a default:
  1. *What do you count on most in your workflow? Up to three things.* Why: these are answered first.
  2. *Are these all the repositories, and is `<branch read>` the branch that ships?* Why: the drawing covers only what is named. Default: yes.
  3. *How far do you want to go?* Asked **after** the findings, with one line per level: what it would change for this team, how many steps remain, where the work is (repository, forge settings, history). It can be changed later with `team target`. With no target, exactly one next step is shown, towards the next level, and the page says why: "no target set; this is the smallest step".
- **It measures nothing itself.** Every figure and level comes from the command. It writes its reading as data and the command checks it, as `ticket check` does with an agent's opinion (`plugins/ai-sdlc/cli/aisdlclib/ticket.py:218-268`).
- **It writes** only in a folder given as an argument, by default `.harness-team/` where the command runs. Never in an assessed repository.
- **It ends** with a fixed report: the sentence on the claims, what a program carries, what is only asked, what would break first, the next step as a change, what could not be read, the open questions. Then it stops.
- **The next step is the change itself** when it lives in the team's files: file and line, the line before and after, what starts to happen ("merges go red when the review job fails"), the effort, how to undo. The skill applies nothing unless asked. It hands off to another skill only when that skill works on the team's own names; otherwise it says "no skill of ours does this; here is the change".

### 4.2 The commands behind it

All under `python3 cli/harness.py team`, standard library only, all taking `--out <folder>`.

| Command | What it does | What it measures by program | What it writes |
|---|---|---|---|
| `scan <path>…` | Reads each clone at a named commit. Lists pieces, links and the forge identity of each clone. | Effective pipeline definitions, typed pieces sorted by content rule, links resolved, what could not be read and why. | `inventory.json`, with the commits read |
| `map`, `status` | Prints the drawing in plain words, or the state as data. `--page` writes the page. | The level, each achievement in three states, the hold of each piece, "would break first" in a fixed order, the difference since the last run. | `state.json`, `team.html` |
| `point <piece> <pointer>` | Records where a piece is. | That the line exists at the read commit **and has the type the piece requires**. Refuses otherwise. | `team.json` |
| `stops` | Renames, merges or adds stops on the path. | Nothing. | `team.json` |
| `answer`, `choose` | Records a team answer, or a deliberate choice with who, when and the control that compensates. | Nothing. Neither is ever a measure. | `answers.json` |
| `check <reading.json>` | Validates the agent's reading. | Paths, lines, quotes word for word, pointer types. No verdict or level key present. | accepted or refused whole |
| `forge <repository>` | Reads live what the forge enforces on the branch that ships. `--print-calls` prints the exact read-only calls. `--from <file>` stores an export. | Required checks, approvals, who may bypass, protection of pipeline files, of environments, default token rights. | `forge.json`, with origin: read live, or export with hash and date |
| `replay <repository>` | Reads past merged changes at their commits. | Section 5.2, Proven, and the facts of section 5.3. | `replay.json` |
| `target <n>` | Declares the level the team aims for. | Nothing. | `team.json` |

**The reference list.** A new data file lists about 25 pieces a sound workflow has, drawn from the eight rule files of `plugins/ai-sdlc/points/`. Each piece carries: what it is, why it matters, one real case from `docs/ai-sdlc/`, the smallest step, **the pointer type it requires, and the minimum a program must find there**. A piece the team does not have appears as "to create".

### 4.3 The reading rule: positive evidence only

This rule replaces "the pointer resolves" and "no flag was found". It applies to every achievement.

1. **A pointer has a type, checked by code.** A gate must point to a pipeline job. An agent must point to an agent definition in a known format, whose tool list was parsed. A check must point to an executable file that a job calls. A sentence in an instruction file is a valid pointer too, of type "sentence": its hold is "asked", and it counts for no level.
2. **A named piece must show a minimum, or it is "could not establish".** A gate job: triggered by proposed changes, and at least one command that is not a no-op (`echo`, `true`, `exit 0`). A review gate, in addition: it invokes an agent definition or a model command or action that the scan resolved, from a list held as data. An agent definition: a job or an orchestrator entry refers to it. So a linter named as the review gate is drawn with its name, and the review achievement stays unestablished.
3. **A job is judged on its whole effective definition.** Every include, inheritance, anchor and default is resolved in the given repositories. The known forms that swallow a failure are data: "allowed to fail" on the job, in a rule, inherited or included; a manual job on GitLab; step-level "continue on error"; `|| true`, `|| echo`, `; exit 0`, `set +e`; a condition that always runs. A construct or a shell wrapper the reader does not recognise makes the job "could not read". It never reads as "no flag".
4. **A known format is a closed list.** Today: Claude Code agent front matter, Claude Code settings permissions, GitHub job `permissions:`. A missing tool list means "inherits everything", not "no write tool". A home-made format is listed and drawn; its content is "could not read".
5. **Three origins of a fact.** Read by the program (measured). Given as an export file (declared, with its hash and date). Answered (declared). Only the first raises a level.

**Where a piece should live, and how it is held, are two computations.** A fixed table maps a pointer type to one of the grid's 20 places (pipeline job to `ci_check`, forge rule to `server_protection`, sentence to `agents_md`, hook to `hook_check`), applied by code; a type that maps to none is refused. The grid then says where the piece should live. The hold is computed apart, by rule 3 and the forge. The hold decides the status shown. The grid's "keep" is printed only when the hold is at least "checked".

### 4.4 Two things shown to the team, no more

The team sees two axes: **how a piece is held** (the four holds, or "nothing found", or "could not read" with its reason inline) and **who says so**.

| Who says so | Where it comes from | How it is shown | Raises a level? |
|---|---|---|---|
| **Measured** | A program read a file, the git history or the live forge. | With the file and line or the call, and the commit read. | Yes. Only this. |
| **Declared** | A team answer, a choice, an export, a pointer of type "sentence". | "Declared by Ana, 2026-11-21", in its own column. Never rephrased as a fact. | No. |
| **Opinion** | The reviewing agent, or an audit. | In its own tab, with evidence the program checked to exist. | No. |

Under the drawing, a three-line legend gives the holds. Pointer origins and grid verdicts stay in the data file and behind a click. Every count on the page says its origin: "4 found by the scan, 2 pointed by you".

### 4.5 What stays a human answer

No program settles these. They are listed, asked within the cap of three, and shown as declared: who owns a ticket; whether a large plan was approved before the code; whether the reviewer is really a different session from the author; who decides a scanner exception and whether a found secret was revoked; the way back after a bad delivery; who is on call and what an agent may do in production; which account is the agent's; which repositories are "product"; everything about the platform.

These stay opinions for ever: whether the acceptance criteria are the right ones, whether a review comment is useful, whether a test would really fail without the change (`ticket.py:10`, `secu.py:489`).

## 5. The road and the game

### 5.1 The ladder

| Level | Label | Medal | What it means | Hold it needs | The work is in |
|---|---|---|---|---|---|
| 0 | Read | none | We read the repositories; the reason the drawing is not complete is printed. | none | nothing |
| 1 | **Drawn** | Bronze | Your workflow is drawn across repositories, from pieces a program found and typed. It measures the drawing, not the workflow. | none | Looking. No change to the workflow. |
| 2 | **Guarded** | Silver | A program checks what must not happen, and says no. Nothing yet forces anyone to listen. | checked | The repositories. |
| 3 | **Locked** | Gold | The forge refuses the merge, and the one a gate stops cannot switch the gate off. | enforced | The forge settings. |
| 4 | **Proven** | Platinum | It held on real changes, over at least 60 days of history. | enforced, plus history | Nothing new: your history already counts at the first run. |

- **Level 0 never says "nobody looked".** It reads, for example: "Read. Not drawn yet: the only pipeline is a Jenkinsfile, which we do not read."
- **An achievement that could not be read blocks its level and is not a failure.** The line reads "Level not measurable beyond Drawn: cannot read `<file>`, because `<reason>`".
- **The headline is the team's target.** "Target reached: Guarded, measured 2026-11-21." The metal is a secondary mark. Levels beyond the target are shown as "not aimed for", not as missing. A small product may well stop at Guarded.
- **A deliberate choice is not a defect.** `team choose` records it. It is drawn in its own colour, with who and why. It does not grant the metal; the headline reads "Guarded but for 1 choice of the team", with the choice listed.

### 5.2 The achievements

Each is recomputed at every run and has three states: passed, failed, could not read. "Passes on" is the positive evidence required. Anything short of it is "could not read", with the access or the file that would settle it.

| Level | Achievement | Passes on |
|---|---|---|
| Drawn | Every named repository was read | A git repository, with the commit read recorded. |
| Drawn | Each pipeline was read whole | Every pipeline file met is resolved into an effective definition. Jenkins, or an include whose project was not given: could not read. |
| Drawn | Every link that carries the workflow resolves | Includes, scripts called by jobs, cited jobs. A link into a given repository that leads nowhere fails. Ordinary documentation links are not counted. |
| Drawn | Tests and delivery are on the drawing | A job found by content rule on each of these two stops. Stops the team pointed or declared are drawn, marked declared, and not counted. |
| Guarded | The tests run on every proposed change, and can fail | In each repository declared "product": a job with a recognised test command (`commands.classify`), triggered by proposed changes, no path or branch filter that leaves the shipping branch out, no failure swallowed. |
| Guarded | A review gate runs on every proposed change, and can fail | The minimum of 4.3 rule 2, and no failure swallowed. |
| Guarded | A secret scanner runs on every proposed change, and can fail | A known scanner command or action in such a job, with file and line. A configuration file that no job runs counts for nothing. |
| Guarded | The reviewing agent cannot write | An explicit tool or permission list in a known format, with no write tool and no shell; or a shell plus a deny hook the scan resolved. |
| Guarded | No written command delivers, and an agent with a shell is behind a delivery guard | Every command written in agent files, skills and scripts passes the delivery detector, which reports the target it found (production, staging, unknown). The guard's hook or deny entry is the positive evidence. |
| Locked | The forge requires the gate jobs on the shipping branch | Read live. The required names are those of the named gates. |
| Locked | The change cannot rewrite its own gate | Read live: a required workflow or ruleset, or code owners on the pipeline files with owner review required, or a pipeline configuration held outside the repository. |
| Locked | A required job cannot be skipped | No path filter and no condition on it in the effective definition. |
| Locked | The gate's code comes from a fixed version | Included at a 40-character commit, or at a tag the forge reports as protected. |
| Locked | A human approval is required, and the agent's account cannot give it | Read live. Which account is the agent's is declared, and shown so. |
| Locked | The gate job cannot write | Job permissions in the file **and** the default token rights and pipeline variables read live. |
| Locked | A delivery needs a human | Environment protection read live. A manual step alone is not evidence: any developer token can play it. |
| Proven | No merged change switched off a test | Replay: zero failed, at most 3 could-not-read, each listed. |
| Proven | No merged change added a secret | Same replay, same rule. |
| Proven | A gate was seen red, then the change was fixed, not the gate | A proposed change where a named, required gate failed on commit A and passed on commit B, and the difference A to B touches no pipeline file, no test-skip marker and no scanner configuration. |

**Access.** Each Locked line prints the right it needs. On GitHub, rulesets are readable with repository read access; classic branch protection and bypass lists need administrator rights. On GitLab the roles are to be confirmed when the reader is built. Without the right, the line is "could not read" and names the right.

**The replay, specified.** Merged changes come from the forge (merge commit and base per proposed change). Without forge access they are the first-parent commits of the shipping branch, and the output says so. The window is the last 30 merged changes **and** at least 60 days between the first and the last, read from commit dates; below either, "could not read: not enough history". Three counts are always printed: failed, could not read, clean. GitLab history is "could not read" until its adapter exists.

**Losses.** A lost achievement is an event with its cause: "review gate set to allowed-to-fail between commit `abc` and commit `def`", from the commits recorded at the two runs. The first failing commit is named when the check reads only files.

### 5.3 Facts shown beside the path, outside the game

These are measures a team is proud of or curious about. They raise no level, because they rest on a heuristic or a declared marker, and each says so.

- Time from ticket to merge, over the replay window.
- Share of agent changes fixed after the merge. Shown only above 10 identified agent changes; the markers that identify them are declared.
- Lines that silence a scanner, added in the window: a count, with the lines.
- Review remarks that became a rule: only the mechanical case, a `rule:` comment whose change also edits an instruction or check file.
- Per repository, levels 1 and 2 of the repository ladder. Levels 3 and 4 are not shown here: today they come from an audit's declared results (`maturity.py:96`, `119`).

### 5.4 The page

One standalone file, built from the existing template.

- **Today.** The path of a change as a line with the team's stops, each piece a dot in its repository's lane, coloured by hold. A click gives what the piece is, why it matters with its real case, the file and line, and who says so. Stops "outside our workflow" are grey, with who said so.
- **The target**, and "not aimed for" beyond it. **The steps**, as a slider: each lights the piece it changes and shows the level after it, with effort, effect tomorrow and how to undo.
- **Could not read**, always visible, with the reason and what would settle it. **Open questions**, beside it.
- **The medals** as a second tab, **the opinions** as a third.
- **The label:** "Workflow of atlas: Guarded, measured 2026-11-21 at these commits." After 45 days it reads as stale and carries the command to rerun. A second run opens with the difference: "gained 2, lost 1, with the change that caused each".

### 5.5 The first screen

The team says its workflow is great. The first screen answers with one measured sentence built from the team's own claims, then the idea to remember, then the drawing. Outputs name the real product and branch ("GitLab protects `main`"), the thing itself (job, prompt, script) instead of "piece", and "where it is" instead of "pointer".

A claim comes back with the hold of the piece it points to, or **contradicted** when a measured fact says the opposite. The claim column and the stop row always use the same word for the same piece; a sample assertion checks it.

Sketch for the Atlas team (made-up line numbers, not a real output):

```
Read-only. Nothing was run. Nothing left this machine. Results: ./.harness-team/
Workflow of "atlas": 3 repositories read on 2026-11-21.

Of the three things you count on: one is checked by a program, one runs but
blocks nothing, one is contradicted by a file.
A sentence asks. A program stops. This page shows which is which.

What you count on                          What we read
  "Tests run on every merge request"       Checked. Job `unit` runs pytest: shop-api/.gitlab-ci.yml:22
                                           Not enforced yet: GitLab's merge rules were not read.
  "Every change is reviewed by an agent"   Runs, ignored. The review job is allowed to fail:
                                           platform-ci/templates/ai-review.yml:9
  "Agents never touch production"          Contradicted. A command that deploys to production is written
                                           in the dev agent's file: sdlc-orchestrator/agents/dev.yaml:14
                                           Why it matters: nothing stands between the agent and a release.

Stop      ticket          dev     review          tests     security   delivery   incident
Held      could not read  asked   runs, ignored   checked   asked      checked    nothing found
          (tracker)
Legend    asked: a sentence, nothing checks it.  runs, ignored: its result changes nothing.
          checked: can say no.  enforced: GitLab refuses the merge without it.
Counts    7 found by the scan, 2 pointed by you, 3 could not be read (listed below).

Level: Drawn (it measures this drawing, not your workflow). Target: not set, so one step is shown.
Next step, towards Guarded:
  platform-ci/templates/ai-review.yml:9    - allow_failure: true    + allow_failure: false
  Effect: a merge request goes red when the review fails. Effort: one line. Undo: revert the line.
```

What keeps this fair: the team's claims come first, each with a file it can open; what a program carries is counted before what is missing; no score out of 100 (the audit's score falls to zero at four serious defects, `skills/harness-audit/references/report-template.md:25`); no comparison between teams; causes are in the mechanism ("a job allowed to fail often dates from a day it was unstable"); every failed line carries its "why it matters"; "could not read" is not "false".

### 5.6 Understand as much as build

| To understand | To build |
|---|---|
| One sentence on the team's own claims, and "a sentence asks, a program stops", on the first screen. | One next step as a change: file, before, after, effect, undo. |
| The drawn path: the team sees its workflow across repositories, often for the first time. | The slider shows the level after each step, so the team picks its stopping point. |
| Each piece carries "why it matters" with one real case from `docs/ai-sdlc/`. | The "to create" rows list missing pieces, each with its right place from the grid. |
| "Cut the agent" as a count per stop: what still stops a bad change if the agent ignores its instructions. | A lost achievement names the change that caused it. |
| The facts of 5.3: what the workflow already delivers. | The second run opens with what changed. |

## 6. How it cannot be gamed, and what it must never claim

- **An answer, a choice or an export never raises a level.** Only a fact the program read does.
- **A name proves nothing.** A stop is filled by a content rule, a pointer by its type and its minimum (4.3).
- **Absence proves nothing.** What the reader did not fully read is "could not read".
- **Writing a convention is not enough.** "Enforced by" counts only if the cited job exists and can fail; "stopped" is said only at Locked.
- **Nothing rewards volume.** No achievement counts skills, agents, pull requests or tokens (`docs/ai-sdlc/proposal.md:151`).
- **History is a share over a window with a minimum span**, so thirty trivial merges do not flush it.
- **Achievements are recomputed and can be lost.** The state names the commits read.
- **Cheating teams are among the samples** (section 7).

What stays weak, said plainly. A team can still write a real job that invokes a model with an empty prompt: the minimum is a floor, not a proof of review. The unlock dates live in a file a person can edit. The identity of the agent's account and the "product" label are declared. The thresholds (30 changes, 60 days, 45 days, 3 unreadable, 10 agent changes) are starting choices with no measurement behind them.

It must never claim that the workflow is **safe**, **good** or **compliant**; that agents **work better**; that a medal is a **certificate** or compares two teams; that an opinion is a fact or a declared answer was verified. One short sentence closes the page: "This says what was read and what stood there, not that the workflow is safe."

## 7. How to measure that the skill itself works

Samples with planted defects, graded by program, blind runs kept apart from the author's runs. A new family `fixtures/teams/<name>/`: several repositories in `repos/`, `traps.md`, `expected.json`, the fictional team's answers in `owner.md` and `owner.json`, `runs/`.

| Sample | What it holds | What it tests |
|---|---|---|
| `atlas` | Three GitLab repositories. A review gate allowed to fail through an included template. A deploy command written in a home-made agent file. A real gate across repositories. Ticket automation outside every file. Three claims: one checked, one runs-ignored, one contradicted. | Cross-repository links at the included version, the two defects, the home-made tool list read as "could not read", claims and stops using the same word. |
| `jenkins-only` | One repository with a Jenkinsfile and sound agent files. | Level 0 reads "Read, not drawn: Jenkinsfile", never a failure. The expected first screen is part of the sample. |
| `tidy` | One GitHub repository with our `ai-sdlc` plugin set up properly. | No false alarm. Must read Guarded. |
| `mirage` | Every stop pointed at a README. "Enforced by" on a job allowed to fail through `extends`. A linter named as the review gate. A job `review` that runs `echo ok`. A stub `reviewer` definition nothing refers to. A scanner configuration no job runs. A hand-written forge export. | The level stays 0, and each decoy is drawn with its name. |
| One held-out sample | Another dialect: Cursor rules, a second forge. Not opened while the skill is written. | That the unread stays unread. |

1. **The code, with no model.** The grader runs `team scan` and `team status` on the sample and compares with `expected.json`: the level, each achievement's state, each resolved link, the first-screen sentences, claim and stop agreement. It runs in the test suite.
2. **The skill, blind.** A fresh agent plays the skill with only `owner.md`. The program grades: each trap at the right path; each sound piece left alone; each outside part in "could not read"; each claim in the right class; no declared answer shown as measured; every citation exists; **the next step names a file that exists and a change that applies**. Generous on the verdict, strict on the evidence and the sound pieces.

A blind run on three repositories costs more than the 140,000 tokens of a single-repository audit. None is started without the owner's request. Until one is played, the skill is "tooled", not "measured".

## 8. What is reused, what is new, in what order

**Reused as is.** The page template and the medal drawing. The grid data (`placement.json`, `place.walk`). The one-page report. Safe reading of a repository at a commit (`context.py:32-37`, `63-77`). The delivery detector on one command string (`guard.py:439`). The patterns of the git-only detectors, as data. The skill text blocks and the blind-run harness.

**Reused after a change, counted as work.**

- The achievement engine: a third state with its reason, the rank rule of 5.1, the output folder as an argument, the commits read in the file (`medals.py:44-47`, `262-306`, `383`). The `repo` and `marketplace` kinds must still pass their tests.
- `maturity.evaluate` and `render_map` take a ladder as an argument (`maturity.py:197-242`, `337-370`); the level-0 sentences are fixed (`maturity.py:50-54`), a defect today whatever we decide.
- The disabled-test and secret detectors, rewritten to take two commits and read with `git show` instead of the working tree (`qa.py:76-107`, `devgrade.py:86-97`).
- The grid verdict, fed by the type-to-place table and combined with the hold (4.3).
- The fixture grader: a new root, a new expected schema, a reader over several repositories (`fixtures.py:22-27`, `69-79`).
- `report.KINDS`, `medals.KINDS`, two sentences of `state_template.html`.

**New code.**

- **The effective-pipeline reader**, the largest piece: a YAML subset in the standard library (mappings, lists, scalars, block text, anchors), GitLab `include`, `extends` and `default`, GitHub jobs, events and permissions. Anything outside the subset makes the file "could not read".
- `cli/harnesslib/team.py`: the scan, forge identity of clones, content rules as data, typed pointers, the hold of each piece.
- The reference list with types and minimums; the failure-swallowing forms; the known formats.
- The ladder of section 5 as a table of checks; the checker of the agent's reading.
- The forge reader, per forge; the replay.
- The page data builder and the drawn path; the skill text; the samples.

**Order.**

| Slice | What it delivers | What it proves |
|---|---|---|
| 1, two to three weeks, half of it the reader | The reader for GitLab (`include`, `extends`) and plain GitHub files; reusable GitHub workflows are "could not read". `team scan`, `map`, `point`, `stops`. The three-state engine. Level Drawn and the first screen without claims. Samples `atlas` and `jenkins-only` graded by code. | That the drawing across repositories is true on Atlas, where today's commands are wrong, and that an unreadable pipeline is said, not failed. |
| 2 | The reference list with minimums, the Guarded level, claims, `answer`, `choose`, `target`, the next step as a change, `team check`, the grid verdicts, the page. Samples `tidy` and `mirage`. A first skill text. | That decoys do not raise the level and sound pieces are not flagged. |
| 3 | `team forge` for GitHub, then GitLab. The Locked level. | That the real locks are read live, or said unread with the right needed. |
| 4 | `team replay`, the Proven level, the facts of 5.3, the difference between two runs. | That existing history counts from the first run. |
| 5 | Blind runs, then the held-out sample, on the owner's request. Fixes to the skill text only. | That the skill is measured, not only tooled. |

Assumptions taken without asking: the work belongs to the `harness-ai` plugin, since the game layer lives there; a hand-written YAML subset is acceptable, since the CLI takes no dependency.

Not verified in this study: nothing was prototyped; the skill was not played; the estimate of slice 1 has no prototype behind it; the code lines cited by the reviewers were not all reopened; the forge access rights are from memory.

## 9. Questions

1. **The name.** Code names `harness-team` and `harness team`, while every text shown to a team says "workflow" ("Workflow of atlas"), so that nobody reads it as grading people? Default: yes.
2. **Where the code lives.** In the `harness-ai` CLI, reading the plugin's detectors through one adapter and reporting "could not read" when the `ai-sdlc` plugin is absent? Default: yes, nothing is copied or moved yet.
3. **Exports.** A forge export given by the team never raises the level, even when nobody can get a token; it is shown as declared, with hash and date. The other choice is a distinct label "Locked, from an export". Default: never raises.
4. **A team's deliberate choice.** It does not grant the medal; the headline reads "Guarded but for 1 choice of the team". The other choice is to let a recorded choice pass the achievement. Default: no medal.
5. **The ladder.** Drawn, Guarded, Locked, Proven, with a first level earned by looking alone and the team's target as the headline? Default: yes.
6. **Slice 1.** GitLab first, because Atlas and cross-repository templates are the case today's commands get wrong, at the price of two to three weeks before the Guarded level exists? Default: yes.
7. **Which forge first** for Locked? Default: GitHub, where we have a transport, then GitLab.
8. **Blind runs.** Default: none until you ask, and not before slice 2 is done.
9. **The audit's own levels.** The audit's declared results decide levels 3 and 4 of the repository ladder, against "a level is measured". Default: fixed apart, as its own row in the plan; meanwhile the team page shows only levels 1 and 2.

## 10. Objections considered

All blocking and serious points of the two reviews are taken into the text above. Where the choice differs from the fix proposed:

- **Slice 1 restricted to GitHub files.** Kept GitLab in slice 1: the Atlas shape is the reason for this work. The estimate is raised instead, and Guarded moves to slice 2.
- **"Locked, from an export" as a lower-trust label.** Refused: one more label that looks like gold is one more thing to explain. An export is declared, and question 3 lets the owner reverse this.
- **Three holds on the page.** Kept four: "runs, ignored" is exactly the Atlas defect, and folding it into "asked" or "checked" is the mislabel the review caught.
- **Rename the level Locked to Sealed.** Renamed the hold instead (asked, checked, enforced), and Mapped became Drawn, so no word serves twice.
- **Bisect to find the commit that lost an achievement.** Kept to "between these two commits", plus the first failing commit for file-only checks: enough to act on, far less code.
- **A phase declared "out" completes or blocks Drawn.** Neither: Drawn is measured on tests and delivery only, which every workflow that ships has; the other stops are drawn and never counted.
- **Drop the medals for a team that stops at Guarded.** Kept the four metals, as the owner asked for a game and a label; the target became the headline and the metal the secondary mark.
- **Remark-to-rule and agent-fix share as Proven achievements.** Moved outside the ranks rather than redefined: both rest on a declared marker or a heuristic, and a threshold on them would be an opinion.
