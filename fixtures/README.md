# Fixtures

Synthetic repositories with AI instrumentation traps planted and documented. It is the L3 of our own skills: the only way to know whether a change to a SKILL.md improves or degrades what the agent finds.

```
fixtures/repos/<name>/
├── repo/            # the synthetic repository, as a developer would have left it
├── traps.md         # each planted trap or fact: id, location, what the skill must say about it
├── expected.json    # the part the CLI can verify: role, status, audit, init blocks
├── owner.md         # sample projects: the fictional owner's answers, given in advance
├── owner.json       # optional: the same owner, who answers only what they are asked
├── tasks/<id>/      # sample projects: a typical task, its hidden tests, its solution, a tempted solution
└── runs/            # dated runs, graded by fixture check; <date>-step1-author = the author's step 1
```

Two families. The **audit fixtures** (`java-back`, `node-front`, `python-cli`) carry a damaged harness and little code: they measure what the audit finds. The **sample projects** (`go-hexa`, `ts-monorepo`, `django-mvc`, `vibe-app`, `microservices`) are real small projects, one per architecture style, whose code runs and whose tests pass: they measure the path, from level 0 upwards. `owner.md` is given to the evaluated agent; `traps.md`, `expected.json`, `owner.json` and `runs/` never are: the owner of `owner.json` answers during the session, through a command that `bench init` lays in the kit.

Runs are kept in `runs/` to compare two versions of the skill on the same fixture. A run made by the session that wrote the traps is a **regression baseline**, not a measurement: only a blind run, by an agent that has read neither `traps.md` nor `expected.json`, measures the skill.

## Two levels of verification

**Deterministic**, at every commit: `harness fixture check <name>` runs `harness status` on `repo/` and compares it with the `status` block of `expected.json` (level, checks that pass and that fail, guardrails detected). It is an ordinary unit test, it runs in `cli/tests`.

**Skill eval**, by hand or in CI with an agent: run harness-audit on `repo/`, take its JSON block in `repo/.harness/audit.json`, then `harness fixture check <name> --audit repo/.harness/audit.json` compares the verdicts with the `audit` block: each trap `T*` must appear with an accepted verdict on the right path, each healthy item `S*` must be KEEP, the expected leaks must be in `process_leaks`, the "cut the agent" test must give the expected result. The result is a simple score, found / expected, and the list of what is missing or wrong.

An audit that finds more than the traps is not penalised, unless it flags a healthy item: that is the "PUSH_DOWN everywhere" bias that the skill's "What is not a defect" section is meant to prevent.

## Available fixtures

| Name | Type | Traps | What it tests |
|---|---|---|---|
| `java-back` | Spring Boot, Gradle, Checkstyle, ArchUnit, release through workflow_dispatch | 12 + 3 healthy | Monolithic CLAUDE.md, told vs enforced rules, precondition inside a skill, duplicated scripts, prod workflow without a guardrail, dead script, unstructured return, hard-coded judgement |

| `node-front` | Vue 3, Vite, custom eslint, stylelint, size-limit, husky, scheduled agent in CI | 11 + 4 healthy | Harness that looks healthy, at level 1: declared mode contradicted by an autonomous agent, lying "Enforced by", diverging multi-tool instruction files, duplicated procedure that diverges from the contract, stale harvest marker, told coverage |

| `python-cli` | Python 3.12 CLI, uv, ruff, mypy in pre-commit, pytest, PyPI publishing on tag | 11 + 4 healthy | Harness measured at **level 2** but hollow: PyPI token inside a skill, publishing from a workstation that bypasses CI, local guardrail mistaken for a pipeline guardrail, `addopts` that deselects slow tests, `rule:` collected by harvest but never pushed into a guardrail, subfolder AGENTS.md that contradicts the root |

| `go-hexa` | **Sample project.** Go service, hexagonal architecture, standard library, ADRs, post-mortem, tested import check | 5 facts + 3 traps + 2 healthy | **Bare** start, level 0: what an init brings up from the repository (incident, destructive action, real guardrail), what it does not copy (stale command, generic principles), guardrail declared in an ADR but not blocking in CI |
| `django-mvc` | **Sample project.** Django 5.1 monolith, MVC, ORM, migrations, SQLite, two apps, three post-mortems | 4 facts + 7 noises + 5 traps + 2 healthy | **Aged** start: a careful two-year-old AGENTS.md never reread, and a copied CLAUDE.md that has diverged. Sorting a file that was right: keep the rules born of incidents, shorten the one that got its guardrail, stop believing the one whose job disappeared, ask the owner about what is outdated |
| `ts-monorepo` | **Sample project.** TypeScript npm workspaces monorepo: API, web, shared package, boundary check | 4 facts + 7 noises + 3 traps + 2 healthy | **Generated, never reread** start: a 104-line `CLAUDE.md` from `/init`. Knowing what to remove: discoverable, generic, written for older models, harmful, outdated, contradicted by a guardrail; and keeping the two lines that matter. Path filter hole in CI, and no command that replays everything |
| `vibe-app` | **Sample project.** Node 22 app without dependencies, hacked together with an agent: a bakery's orders, payment webhook, JSON file, no CI | 4 facts + 8 noises + 6 traps + 2 healthy | **Accumulated notes** start: a 133-line memory-dump `CLAUDE.md`, `PLAN.md`, `NOTES.md`, `TODO.md`, and an owner who knows nothing of the code. Keep three dated facts, remove the rest, call nothing enforced; dead implementation, hollow tests, key in clear |
| `microservices` | **Sample project, held out** (`holdout`). Three Python services on the standard library, JSON contracts, at-least-once delivered events, tested schema validator and import check | 7 facts + 3 defects + many healthy | **Healthy** start: a harness at level 1, dated, with real guardrails. Measures zeal: a good audit keeps almost everything, a good init rewrites almost nothing. Three subtle defects: a guardrail that covers only one side of the contract, a manual instruction that became redundant, a stale broker limit |

Architecture styles to come: data pipeline, infrastructure as code.

## Writing a sample project

Models to read before writing: `repos/go-hexa` (bare start) and `repos/ts-monorepo` (generated, never reread start).

- **The code runs.** The README commands pass in a bare container, with the language toolchain and at most one `install`. `traps.md` gives the exact line. A project whose tests cannot be run cannot carry a task.
- **The facts are in the repository, not in the owner's head.** An incident is planted in a dated post-mortem with figures, a decision in an ADR, a danger in an operations note. `owner.md` only answers the interview and reveals no planted fact.
- **At least one fact is written nowhere else.** A fact filed in an ADR or a post-mortem, a careful agent finds on its own: the first two campaigns showed it, the arms came out even. Each sample project therefore carries at least one fact that is read only in its instructions, or held only by its owner (`owner.md`, section "What the team adds unprompted"). It has its own identifier (a header, a setting, a path), absent from the rest of the repository, and none of its pieces is read there either: a validator that lists `deprecated` among its annotations leads to `"deprecated": true`, and the agent without instructions set it on its own (`microservices`, 2026-11-13). A standard keyword of a format or a tool does not make an oral fact: a careful agent knows it. A task check exercises it, and a tempted solution, the best one can write without that fact, fails that check and that check alone. `fixture check` verifies it.
- **An owner who says nothing unprompted.** With `owner.md`, the answers are given in advance, including what the owner adds unprompted: an interview that asks no question still collects the oral fact, and the measurement says nothing about the interview. `owner.json` carries the same answers, each behind its triggers (`any_of`, whole words, case- and accent-insensitive, `*` for a word ending). The answer that carries the oral fact says so with `fact`; its triggers are what a real owner would hear as an invitation to say it: what is written nowhere, what gets repeated in review, a trap for a newcomer, "anything else to add?", or the subject itself. Neither the mode, nor the team, nor the CI triggers it. `fixture check` verifies that the fact escapes through no other answer, nor through the greeting, nor through the default answer. `bench init` keeps the exchange in `interview.md` and says whether the fact was asked for. No model plays the owner: a question always gets the same answer.
- **Each fact has its opposite.** Next to the real incident, a generic rule without an incident; next to the guardrail that blocks, a declared guardrail that does not; next to the command that works, a stale command. It is the gap between the two that is measured.
- **The repository README** gives the bench away on a single line, "**Synthetic** repository: a fixture of the harness-ai project" (French fixtures: "Dépôt **synthétique** : une fixture du projet harness-ai"): it is removed from working copies. It never cites `traps.md`.
- **An author's step 1** in `runs/<date>-step1-author/`: `AGENTS.md`, the `CLAUDE.md` stub, the subfolder notes kept, `REMOVE.txt` if it deletes files from the repository (one path per line), and `RUN.md` which says what was removed and why. Level 1 and nothing else: no Maintenance, no marker, no Working process, no contract. Each rule carries its date `[YYYY-MM]`, that of the incident or of the decision. It is the grader's regression baseline and the bench's `harness` arm. The bench takes the last `runs/*-author` folder that holds an `AGENTS.md`, whatever the rest of its name.

### expected.json

```json
{
  "fixture": "<name>",
  "role": "tuning",            // or "holdout": held out of skill tuning, only serves to measure
  "status": { "level_reached": 0, "source_path": "CLAUDE.md", "failing_checks": [], "passing_checks": [], "guardrail_tools": [], "contracts": 0 },
  "init": {
    "min_level": 1,
    "only_level_material": true,
    "must_surface":   [{ "id": "I1", "what": "…", "any_of": ["repository-identifier"] },
                       { "id": "I6", "what": "…", "any_of": ["…"], "only_in_instructions": ["word absent from the rest of the repository"] }],
    "must_not_write": [{ "id": "N1", "what": "…", "any_of": ["noise text"] },
                       { "id": "N2", "what": "command that no longer exists", "any_of": ["make e2e"], "mention_ok": true }],   // citing it to refute it is not copying it
    "guards_cited": ["path-of-the-real-guardrail"],
    "forbidden_guards": [{ "path": "guardrail-that-does-not-block", "rule_keywords": ["…"] }],
    "never_guarded": [{ "what": "…", "rule_keywords": ["one of"], "rule_all_of": ["all"] }],   // nothing verifies it: "enforced by: the review" is false too
    "no_guard_exists": false,                                     // true: repository without CI, every "enforced" rule is false
    "must_not_remain": [{ "path": "PLAN.md", "what": "…", "max_lines": 8, "any_of": ["…"] }],  // side notes: gone or reduced
    "report_must_mention": [{ "what": "…", "any_of": ["…"] }],    // the report, graded with --report <file>
    "report_must_not_mention": [{ "what": "the value of a secret", "any_of": ["…"] }],
    "min_similarity": [{ "path": "AGENTS.md", "ratio": 0.8 }]     // already healthy harness: rewriting it is zeal
  },
  "audit": {
    "traps": [{ "id": "T1", "path": "…", "verdicts": [], "priorities": [], "leak_keywords": ["all, in one single leak"], "leak_any_of": ["or one of these"], "require_leak": true }],
    "sane": [], "guarded_rules_paths": [], "forbidden_guarded_paths": [], "forbidden_leak_keywords": [],
    "never_guarded": [], "no_guard_exists": false,
    "removals":  [{ "id": "N3", "any_of": ["text of the line"], "reasons": ["useless", "harmful", "outdated"], "ask_owner": false }],
    "must_keep": [{ "id": "I1", "any_of": ["identifier of the line to keep"] }]
  }
}
```

All keys are in English; the grader reads no other key. Each `id` of the `init` and `audit` blocks has its `| id |` line in a table of `traps.md`: a test verifies it. The words searched for are repository identifiers (`reset-db`, `archcheck`, `packages/shared`), not phrasings: the grade does not depend on the language of the report. Where a word has to be prose (a leak, a style convention), list it in both languages (`leak_any_of`, `any_of`), since the agent may write either.

A removal has a reason: `useless` (discoverable, or what a model does without being told), `harmful` (degrades the work of a current agent, or contradicts a guardrail), `outdated` (true yesterday, no longer today). `ask_owner` is true when only the owner knows the line is outdated: the audit must then ask the question, not decide.

### A task

`tasks/<id>/` carries the team's typical task, the one an agent without a harness misses in a predictable way:

```
task.md                 the statement given to the agent; it says nothing of the planted rules
task.json               the checks, see below
acceptance/             the hidden tests, copied into the repository at grading time
solution.patch          the reference solution: passes every check
tempted/<name>.patch    the solution one naturally writes: works, and fails the declared checks
```

The tempted solution must **pass the project's visible commands** and fail only the hidden tests or the diff checks. If the repository's tests catch it, an agent that runs them fixes it on its own and the task no longer measures what the instructions teach: `bench selftest` announces it with a warning. Likewise, a fact that the task statement exercises must not be found in clear in a document every careful agent reads: the 2026-11-11 campaign on `go-hexa` showed it, the agent without instructions opened the ADR on its own. To measure what the harness brings, the fact must live only in the instructions, or be drowned.

`agent_bash` lists the commands the evaluated agent is allowed to run (`"go *"`, `"git *"`): the project's toolchain and git, nothing else.

A check may carry `"exercises": "I6"`: it exercises the fact written nowhere else, it is the one that separates the arms.

Checks of `task.json`: `run` (a command, green if it exits with 0; `"acceptance": true` for those that need the hidden tests), `forbid_added` and `require_added` (a pattern in the added lines under some paths), `forbid_removed` (a pattern in the removed lines), `forbid_changed` (paths one does not touch: a guardrail, an applied migration), `max_changed_lines`. A diff check may combine several of them.

Two lessons from the campaigns. A check that protects the CI forbids **weakening** it, not touching it: an agent that fixes a path filter hole does well. A check on a secret looks for its **real value**, not everything that looks like it: an agent that gives its tests a secret of their own does well too. `setup` runs an install before the commands. The hidden tests use only the project's public surface, so that they compile whatever the solution.

```bash
python3 cli/harness.py bench selftest <name>     # untouched repository red, solution green, temptation red where it declares
```

A patch is made in a working copy: `bench prepare <name> <dir> --arm asis` (or `bare` if the repository has no instructions), the change, then `git add -A && git diff --cached HEAD > solution.patch`.

## Writing an expected.json

Verdicts and priorities are judgement: two serious audits diverge on SPLIT versus PUSH_DOWN, or P1 versus P2. The first blind runs showed it. Be **generous on verdicts and priorities** (list every defensible reading), **strict on the rest**: the trap must be found with evidence at the right path, the told rules must be in `process_leaks` (`require_leak`), the healthy items must stay KEEP, the style conventions must not be leaks (`forbidden_leak_keywords`), a lying guardrail must not be believed (`forbidden_guarded_paths`).

## Evaluating harness-init

harness-init has no traps to find: it writes. It is evaluated on a **bare** repository, a fixture from which the AI instrumentation is removed (`AGENTS.md`, `CLAUDE.md`, `.claude/`, `.cursor/`, `.agents/`, Copilot stub, `.harness/`):

```bash
python3 cli/harness.py fixture bare java-back /tmp/bare
```

On a sample project, the `init` block of `expected.json` makes the grade deterministic:

```bash
python3 cli/harness.py fixture check go-hexa --init <repository produced by the init>
```

It verifies the level reached, the non-discoverable facts surfaced (`must_surface`), the noise copied (`must_not_write`), the real guardrails cited after "Enforced by" (`guards_cited`) and the lying guardrails believed (`forbidden_guards`). The words searched for are repository identifiers (`reset-db`, `archcheck`, `packages/shared`), not phrasings: the grade does not depend on the language of the report.

A `must_not_write` word counts wherever it is, except for a `mention_ok` entry: a repository identifier that a healthy rule may have to name in order to refute it, a command the README still announces for example. The line is then only a citation if it says the thing is no longer there **and** does not take up four words in a row of an original line that holds that word. Citations are listed under the grade, not counted, to review. The list of phrasings that say "no longer there" depends on the language (French and English today): it only serves to excuse, an unknown phrasing leaves the line counted. Do not mark `mention_ok` a secret, a style preference, or an old-model instruction: those have no reason to be named.

When the target level is already reached, `bench step` expects the report to say so: "target reached" or, in French, "objectif atteint".

On an audit fixture, without an `init` block: a fresh agent receives the skill, the bare repository and the interview answers of a fictional owner. It is then graded: `harness status` on what it produced (level 1 expected, 5/5), its audit as a gate against the traps of the original fixture still present (`fixture check --audit`), and a review of the rules written: non-discoverable only, real justifications or declared absent, named guardrails. Two runs: `repos/java-back/runs/2026-11-09-init-blind/` (bare repository) and `repos/node-front/runs/2026-11-09-init-blind/` (repository already instrumented, to merge: the most frequent case).

## The before-and-after bench

A task is played on several arms of the same repository: `bare` (no instructions), `asis` (the repository as found), `harness` (after step 1, by default the author's). The gap between the arms says whether the harness helps. Replayed without a line or on a new model, it says whether that line still helps.

```bash
python3 cli/harness.py bench plan                          # the agent runs of a campaign and their cost
python3 cli/harness.py bench prepare go-hexa /tmp/w --arm harness
python3 cli/harness.py bench check go-hexa deposit /tmp/w  # after the agent's work
python3 cli/harness.py bench record --kind task --fixture go-hexa --task deposit --arm harness --score 6/6 --ok
python3 cli/harness.py bench report                        # the registry fixtures/results.jsonl
```

`bench play` chains it all for one arm: working copy at a neutral path, agent, grade, outputs filed in `runs/<date>-task-blind-<arm>/` (`diff.patch`, `report.md`, `note.md`, `usage.json`), registry. The agent is a separate process that receives only `task.md` and loads only the working repository's instructions; neither the instructions nor the tools of the session that launches the campaign reach it. It is confined to its folder, with only the commands of the task's `agent_bash` list.

```bash
python3 cli/harness.py bench play go-hexa deposit --arm harness --work-root /tmp/bench --label 2026-11
```

`bench init` likewise plays step 1: the repository as found, the skills and the CLI, the owner's answers given in advance. It grades what was written and the report, and files in `overlay/` what the step changed. That folder is given to `bench play --overlay` to play the task with the harness the skill produced: that is the whole chain, from the skill to the work handed in.

```bash
python3 cli/harness.py bench init go-hexa --work-root /tmp/bench --label 2026-11
python3 cli/harness.py bench play go-hexa deposit --arm harness --work-root /tmp/bench \
    --overlay fixtures/repos/go-hexa/runs/<date>-init-blind/overlay --out fixtures/repos/go-hexa/runs/<date>-task-blind-init
```

A run names the agent's report `report.md`, the interview `interview.md` / `interview.json` and the author's step 1 `<date>-step1-author`; the fixtures recorded in French were renamed when they were translated, and their original names are in git history. The `note` fields of the registry `results.jsonl` were translated on 2026-11-17; the paths and scores they sit beside are unchanged.

Deciding on a campaign and interpreting it remains the job of the `harness-stress` skill, on request.

## Running

```bash
python3 cli/harness.py fixture check java-back
python3 cli/harness.py fixture check java-back --audit fixtures/repos/java-back/repo/.harness/audit.json
python3 cli/harness.py fixture check go-hexa --init fixtures/repos/go-hexa/runs/2026-11-10-step1-author
```
