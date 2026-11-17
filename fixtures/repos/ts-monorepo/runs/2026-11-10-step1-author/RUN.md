# Step 1 by the fixture author — 2026-11-10

What step 1 of harness must set up on this repository, written by the session that planted the traps: level 1 and nothing else. It is a **regression baseline** for the grader (`fixture check ts-monorepo --init <this folder>`) and the default `harness` arm of the bench, not a measurement of the skill.

The dates of the rules taken over from the old file are those of the original incident or decision, not that of the step: a rule does not get younger because it is copied.

## What was removed from the generated CLAUDE.md, and why
104 lines before, 22 after, 2 of them rules that came from the old file.

| Removed | Reason |
|---|---|
| Project Overview, Tech Stack, Repository Structure, Architecture | Discoverable by reading the repository |
| `npm run lint`, `npm run build` | These scripts do not exist |
| Code Style Guidelines, Git Workflow | Generic: a model does it without being told |
| "expert senior", "think step by step", "do not hallucinate", "read a file fully" | Written for old models; no longer changes anything |
| "rewrite the whole file" beyond 500 lines | Harmful: makes the agent rewrite whole files to work around a limit that is gone |
| "ask for confirmation before running any command" | Contradicts delegation mode |
| "80% code coverage" | No tool measures it |
| Web: import from `apps/api` | Contradicts `check-boundaries`, refused in CI |
| Web: IE11 | Outdated since 2024, confirmed by the owner; the code violates it everywhere |
