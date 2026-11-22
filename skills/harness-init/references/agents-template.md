# Templates, step by step

Each step adds its block, and only its own. The `<…>` brackets are to fill in; a section about which there is nothing non-discoverable to say is **removed**, not filled.

Budget: AGENTS.md under 60 lines, all steps included. If a section overflows, its content becomes a skill in `.claude/skills/` or a file in `docs/agents/`, and AGENTS.md keeps a pointer line.

Language: the blocks are in English. In a repository written in French, write the same sections in French; `harness status` reads both: `Mode : **délégation**` / `**assistance**`, `## Règles`, `## Interdits`, `Pourquoi :`, `Vérifiée par :`, `(non vérifiée)`, `## Maintenance de ce fichier`, `## Processus de travail`, `## Tâches déléguées`.

---

## Step 1 — Framed (harness-init)

```markdown
# <repo name> — instructions for agents

Mode: **delegation**. An agent can receive a whole task and open a PR without intermediate review. What is mandatory here is enforced by the CI; this file explains, it does not guarantee.

## What this repo does
<Two lines max: what, for whom, where the decisions and incidents are. Not the stack, not the tree.>

## What changes → what to run
| If you touch… | Run… | Enforced in CI by |
|---|---|---|
| <area> | `<confirmed command>` | <job that blocks, or "nothing"> |

## Rules
- <Rule in one sentence.> Why: <incident or reason, or "no known incident">. Enforced by: `<path of the guardrail that blocks>` | (unverified) [<YYYY-MM>]

## Forbidden
- <What an agent never does, even if the task seems to ask for it.> Why: <…>. Enforced by: <permission deny, PreToolUse hook, branch protection> | (unverified) [<YYYY-MM>]
```

Assistance variant, mode line: `Mode: **assistance**. A person drives and reviews every diff; this file avoids back-and-forth, it is not a guardrail.`

### Stubs

`CLAUDE.md` (a single line):
```
@AGENTS.md
```

`.github/copilot-instructions.md` (Copilot cannot include a file):
```markdown
This repository's instructions live in `AGENTS.md` at the root. Read it before any change and apply it; no rule is defined here.
```

`.cursor/rules/agents.mdc`:
```markdown
---
description: Repository instructions
alwaysApply: true
---
This repository's instructions live in `AGENTS.md` at the root. Read it and apply it; no rule is defined here.
```

---

## Step 2 — Looped (harness-step)

At the end of AGENTS.md:

```markdown
## Maintaining this file
- A review comment that starts with `rule:` is a candidate rule. It is added here in the same PR, dated, with the link to the comment, or collected by harness-harvest.
- Before adding a sentence, look for a linter, a test or a CI check that can carry the rule: an enforced rule is shortened, a narrated rule is a debt.
- A rule with no incident for six months, or written for a past generation of models, is a candidate for removal at the next relevance review.

<!-- harvest: last=<YYYY-MM-DD of the step> ref=init -->
```

The `ref=init` marker is only set on a file that had none: resetting a stale marker to today would fake a harvest that did not happen.

### The `rule:` convention

In a review comment, on a line or on the PR:

```
rule: <the rule in one sentence, in the present tense, checkable>
```

Examples:
- `rule: outgoing HTTP calls go through the client in src/http, never fetch directly`
- `rule: a migration never drops a column in the same release as the code that stops reading it`

What is done with it, in order:
1. Look for a guardrail: lint rule, architecture test, PR check script. If possible, the rule goes into CI and AGENTS.md keeps only an "Enforced by" line.
2. Otherwise, add it under "Rules" with the comment's link as justification, the `(unverified)` mention and the date.
3. Never without justification: a `rule:` without context is sent back to its author.

---

## Step 4 — Delegated (harness-step)

Before "Maintaining this file":

```markdown
## Working process
- Stop and ask when: <e.g. the task involves an architecture choice, touches a forbidden item, or the CI fails for a reason unrelated to the task>.
- A task is done when: <e.g. CI green, a test covers the change, the PR explains why, no TODO left>.
- Red CI: <e.g. fix it if the cause is in your diff; otherwise report it in the PR and do not touch it>.
- Flaky test: <e.g. rerun once; if it stays unstable, open an issue, do not disable it>.

## Delegated tasks
- `<skill-name>` (`.claude/skills/<skill-name>`) — <one line>.
```

A "Delegated tasks" line is only written in the step that creates the contract: `harness status` reports a contract cited without a `SKILL.md`.

In assistance, these two sections do not exist, unless a specific task is already delegated.
