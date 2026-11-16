# Harvest PR format

Branch: `harvest/<YYYY-MM-DD>`. One commit per candidate, in the order PUSH_DOWN → REMOVE → SHORTEN → ADD → CONTRACT, then a last commit that updates the marker. ASKs produce no commit, only a section in the description.

Commit message: `harvest(<VERDICT>): <rule or task in one sentence>`, body with the links to the evidence.

## PR description

Written in the repository's language. Each signal code and verdict comes with its plain meaning the first time.

```markdown
# Harvest of <date> — window <start date> → <end date>

**Where this leaves the repository**: <the output of `harness status --map`, or its two key lines: you are here, next step>

**Repo mode**: delegation | assistance · **Evidence collected**: <n> (GitHub: <n>, …) · **Candidates**: <n> · **Ignored**: <n>

## Candidates

### 1. [<VERDICT>] <rule or task in one sentence>
- **Evidence**: <link>, <link> (<what it is in plain words>, signal S<n>)
- **Why this verdict**: <one sentence; for PUSH_DOWN, the tool named; for REMOVE, for how many harvests without evidence>
- **Commit**: <short sha>

## Questions for the team (ASK)
- <real signal but the rule cannot be stated: what was seen, what we propose to decide, the proposed default>

## Deliberately ignored
- <evidence> — <reason: convention guessed without incident / isolated preference / already refused at the harvest of <date> / rule already applied by the model>

## Rules confirmed by the absence of incidents
- <rule> — enforced by <guardrail>; can be shortened at the next harvest if still without evidence.

## Not collected
- <source or period not read, and why>  (or "None")
```

## Harvest marker

Last commit of the PR, in the "Maintaining this file" section of AGENTS.md:

```
<!-- harvest: last=<YYYY-MM-DD> ref=<url of this PR> -->
```

A single marker line in the file; the previous one is replaced, not stacked.
