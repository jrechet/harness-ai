# The steps, check by check

For each failing check of `harness status`: the step, what it costs, how you know it is done. One step per invocation. The text templates are in `skills/harness-init/references/agents-template.md`.

The check ids below are for you, not for the user: tell the user what the check means, in the words of `harness status --map`.

## Level 1 — Framed

At level 0, several checks fail together: the step is **harness-init**, in full. When only one is missing, the step is targeted:

| Check | The step | Cost | Done when |
|---|---|---|---|
| `L1.source` | harness-init | Four questions, half an hour | AGENTS.md exists |
| `L1.mode` | Ask for the mode, write the line at the top | One question | The "Mode:" line is read by `status` |
| `L1.short` | Move reference material to `docs/agents/` or remove noise, see "Removing" in harness-init | Line-by-line sorting | 60 lines at most |
| `L1.single_source` | Merge the useful content of CLAUDE.md into AGENTS.md, reduce CLAUDE.md to `@AGENTS.md` | Line-by-line sorting | CLAUDE.md is a stub |
| `L1.forbidden` | Ask what is forbidden, write the section | One question | The section exists |

## Level 2 — Looped

This level is won over time: two checks are files, two are facts.

| Check | The step | Cost | Done when |
|---|---|---|---|
| `L2.maintenance`, `L2.rule_convention` | Add the "Step 2" block of the template: Maintaining section, `rule:` convention, `ref=init` marker if the file has none. Tell the team, in two sentences, how to write a `rule:` | Ten minutes, and a habit to take | Both checks pass |
| `L2.marker_fresh` | Run harness-harvest, if there have been reviews since the marker | A harvest PR to review | The marker is less than 45 days old |
| `L2.signal` | Nothing to write. The signal comes from a `rule:` in review or a corrected agent PR. If there is none, say so: the loop is in place, it has not run yet | Time | A harvest finds a real signal |

If the marker is fresh and there is no signal, **this level has no step left**: it waits. If the target is higher, go to the first step of level 3; otherwise, say so and stop. Inventing a rule to make the check pass is the opposite of the goal.

## Level 3 — Verified

One rule at a time. Prefer the one that has an incident, then the one whose check costs least.

| Check | The step | Cost | Done when |
|---|---|---|---|
| `L3.ci` | Propose a minimal CI that runs the confirmed commands of AGENTS.md | A workflow | A workflow exists and has run green |
| `L3.guarded` | Take **one** `(unverified)` rule and have a tool enforce it: an option of a linter already there, a test, a script called by the CI. Then reduce the rule to its "Enforced by" line | Guardrail code, from one config line to a tested script | The guardrail has been **seen red** on a violation, then green |
| `L3.justified` | Ask why for the rules that do not say it. Without an answer: "no known incident", or removal | Questions | Half the rules say why |
| `L3.audit` | Run harness-audit, write its JSON to `.harness/audit.json`. If a P1 remains: the next step will be to handle it | An audit to review | An audit exists with no open P1 |

Forbidden lines count in the `L3.guarded` ratio like the rules: a repository with few rules and many forbidden items does not pass on linters alone. When the `(unverified)` line taken is a **forbidden item**, a linter or a test is the wrong tool, because the action must be refused, not detected afterwards. `python3 "${CLAUDE_PLUGIN_ROOT}/cli/harness.py" place one nature=limit` asks who must not be able to override it, then names the destination: a permission deny in `.claude/settings.json` (with a PreToolUse hook if it depends on the content of the command) when only the agent is bound, a branch protection or ruleset on the forge when nobody in the repository may do it. Cost: one settings line or one forge setting, which only an owner can set: ask, do not assume. Done when the action has been **seen refused**, and the line ends with `Enforced by: <permission deny, PreToolUse hook, branch protection>` in place of `(unverified)`.

Three things learned on real repositories:
- A guardrail only counts if it **blocks**. A job in `continue-on-error`, a path filter that does not trigger it, or a local hook skipped with `--no-verify` guarantee nothing.
- A scheduled or manually triggered workflow only runs from the **default branch**. A guardrail merged on a work branch alone is inert.
- Pushing everything into guardrails makes a repository rigid. A judgement rule stays a sentence.

## Level 4 — Delegated

| Check | The step | Cost | Done when |
|---|---|---|---|
| `L4.mode` | Ask whether the team wants to switch to delegation. In assistance, this level is not a target | One question | Mode delegation |
| `L4.process` | Three questions: when to stop and ask, when a task is done, what to do with a red CI or a flaky test. Test each stop case against the task the team wants to delegate: a case it meets every time makes it impossible to delegate. Have it made precise before writing it, for example adding a migration versus modifying one. Write the "Step 4" block | Three questions, and one more if a stop case is too broad | The section exists, and the task to delegate can go to the end without hitting a stop case |
| `L4.contracts` | Ask for the first repetitive task to hand over. Write its contract `.claude/skills/<task>/SKILL.md`: steps, checks, definition of done. Only then the "Delegated tasks" line | One question, a short file | The contract exists and is cited |
| `L4.clean_prs` | Run harness-harvest on a window that contains agent PRs. Each after-the-fact correction is a missing rule or guardrail: the step is to handle one | PRs to observe | A harvest without after-the-fact corrections |
| `L4.cut_the_agent` | In the last audit, take the first step that exists only in a prompt and push it into a script or workflow | Code | The audit's test passes |

## References without a target

`status` lists them separately. They come before any other step:
- **Contract cited, SKILL.md not found**: write the contract, or remove the line.
- **Guardrail cited, path not found**: the rule is no longer enforced. Put back `(unverified)`, or find where the guardrail went.
