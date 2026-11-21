# Maturity model

Five levels, each earned by checks **measured** on the repository, never declared. `harness status` computes them and writes `.harness/state.json`; an interface only has to read that file. The thresholds are constants of `cli/harnesslib/maturity.py`.

A level is reached when all its checks pass and the previous level is reached. Each failing check carries the next action.

**A level is a place where you can stay.** The owner declares the one they aim for with `harness target <n>`, written in `.harness/config.json`. Up to that level, the state says what to do next; beyond it, it proposes nothing, and when the target level is held it says "target reached". The `harness-step` skill then offers the next level once, as a plain choice where staying is the default. Without a target level, the state shows the whole ladder and says so. Each step is led by the `harness-step` skill, one per invocation.

`harness status --map <repo>` prints the same measurement in plain words: the ladder with "you are here", the target, what the next level still needs, and the next step. Every skill shows this map before it asks the user anything. `harness status --page <file> <repo>` writes the same measurement as one standalone HTML page: the files present, missing or only needed for a tool, layer by layer; the steps to the target, one at a time, each lighting what it adds or changes; the medals as a second tab. The remarks of the last audit appear on it apart, as opinions and not as measurements. The skills write it and give its path; none of them writes it by hand.

| Level | Name | What it means | Checks |
|---|---|---|---|
| 0 | None | The agent starts from zero at every session | none |
| 1 | Framed | The agent knows where it is | an instruction file exists: AGENTS.md, or CLAUDE.md alone when it is not a stub · "Mode" line · at most 60 lines · a single source: CLAUDE.md is an `@AGENTS.md` stub or absent, or is itself the source · Forbidden section |
| 2 | Looped | Incidents become rules | Maintenance section · `rule:` convention documented · harvest marker less than 45 days old · the last harvest found at least one real signal (S1 to S4, not S5) |
| 3 | Verified | Mandatory rules are carried by tools | a CI exists · at least 50% of the rules "Enforced by" · at least 50% say why · an audit exists with no open P1 |
| 4 | Delegated | Whole tasks come back clean | delegation mode · Working process section · at least one contract referenced · agent PRs with no after-the-fact correction (S2 = 0) in the last harvest · the audit's "cut the agent" test passes |

**The source is the file found.** `AGENTS.md` is the source when it exists; otherwise a `CLAUDE.md` that is not a stub is the source, and such a repository can hold level 1 as it is. The state, the map and the page then name `CLAUDE.md` in their labels, next actions and steps, and the single-source line reads "CLAUDE.md is the source: fine, or move it to AGENTS.md and leave a pointer". Moving to `AGENTS.md` is offered, never required.

## Why these checks and not others

- **Level 2 requires a signal, not a file.** A harvest marker set by harness-init is not enough: a harvest must have found something. Otherwise the loop is decorative. Orphan rules (S5) do not count: they say there is no signal, not that there is one.
- **Level 3 counts the rules enforced in the text**, through the mention "Enforced by:". It is a writing convention, so it can be gamed, but it forces you to name the tool; and the audit checks that the tool exists.
- **Level 4 is measured on PRs**, not on the declared mode. An agent PR corrected after the fact is a missing rule or guardrail. Zero S2 over a window with agent PRs is the only proof that delegation works.

## What the level does not measure

The level measures the **shape** of the harness: files, sections, mentions. It does not say that the agents work better. That proof comes from two places: on the user's repository, the trend of signals per agent PR from one harvest to the next; on the sample projects of `fixtures/`, the bench before and after (`harness bench`).

## What the state reports next to the levels

- **References without a target**: a contract cited under "Delegated tasks" without a `SKILL.md`, a path cited after "Enforced by" that does not exist. A step does not promise the next step, and a rule whose guardrail has disappeared is no longer enforced.
- **Rule dates**: a rule carries `[YYYY-MM]`, the date of its incident or decision. `harness rules` lists each rule with its date (failing that, git's), its age, its declared guardrail and its justification: it is the input of harness-audit's relevance review.
- **Lines to remove**: the last audit counts the proposed removals by reason: useless, harmful, outdated.

## The layer view

Next to the levels, `state.json` carries a view by layer L1 to L4: number of items per layer and number of misplaced items, taken from the last `.harness/audit.json`. Without an audit, a rough estimate from the files (contracts, lint tools, workflows) with a hint to run harness-audit.

## Files

```
<repo>/.harness/
├── config.json    # what the owner decided: the target level (`harness target`)
├── audit.json     # "Machine data" block of the last harness-audit
├── harvest.json   # evidence of the last harness-harvest (output of `harness harvest github`)
└── state.json     # written by `harness status`; schema harness-state/1
```

The `.harness/` folder is versioned: the history of `state.json` is the history of the progress.

## Run

```bash
python3 cli/harness.py status <repo-path>
```

For the graphical view and the history of committed `state.json` files:

```bash
python3 cli/harness.py serve <repo-path>
```

Options: `--format json`, `--no-write`, `--audit`, `--harvest`, `--today` for reproducible outputs.

```bash
python3 cli/harness.py target 2 <repo-path>    # the target level
python3 cli/harness.py rules <repo-path>       # the rules, their age, their guardrail
```
