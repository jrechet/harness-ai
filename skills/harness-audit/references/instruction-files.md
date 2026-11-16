# Auditing instruction files, and the relevance review

## Special case: auditing an AGENTS.md / CLAUDE.md

A repository instruction file is a pure L2 item. The same questions apply, with a few specifics:

- **Told rule vs enforced rule.** For each mandatory rule ("never inject through a field", "no colour outside tokens", "every route has an authorisation test"), look for the matching L3 guardrail: custom eslint/stylelint rule, Checkstyle, ArchUnit, check script in a PR gate, hook, or scheduled job for a process rule (drift between branches, pending agent PRs). A guardrail only counts if it **blocks**: open the workflow. A job in `continue-on-error`, a path filter that does not trigger it, a local hook, a job the file cites but that no longer exists guarantee nothing, and the rule becomes a leak again. A rule with a guardrail is healthy and can even be shortened in the file; a rule without a guardrail is a leak to report in the section "Rules told without enforcement" — verdict PUSH_DOWN with the target tool named.
- **Context cost.** Count the lines actually loaded per session (file + `@includes`). Separate instruction (what changes behaviour) from reference (commands, module structure, troubleshooting). Reference must be moved to files loaded on demand or to skills; report as P3 a file more than half of which is reference, as P2 if it largely exceeds what a model reads with attention (order of magnitude: several hundred lines).
- **Relevance.** Each line goes through the relevance review below: what no longer changes what the agent does is removed. `python3 "${CLAUDE_PLUGIN_ROOT}/cli/harness.py" fresh <repo>` gives its measurable input for skills and agents: those that cite a file that is gone, those whose cited files have changed since, those nobody has touched for six months.
- **Justification.** Note whether the rules explain *why* (ideally with the incident or issue at their origin) or are bare MUSTs. It is a strength to mention explicitly, because it is what makes a rule hold in unforeseen cases.
- **Maintenance.** Does the file say how it evolves (added in the same PR as a review comment, obsolete rules removed)? Without this clause, it drifts.
- **Internal consistency.** Reread the code examples and commands: an error in an example will be copied faithfully by the agent. Check that two sections do not contradict each other.
- **What is missing and the repository shows.** An audit judges what is written; an absent line is not an item, and that is how the most useful one gets missed. `python3 "${CLAUDE_PLUGIN_ROOT}/cli/harness.py" commands <repo>` lists the commands the CI runs that nothing lets you guess (a wrapper, options, a delivery script). Each unwritten candidate goes into `owner_questions`, with its source and the obvious command an agent would run instead: "the CI runs `make it` (ci.yml:14), AGENTS.md says nothing about it: is it the command to run rather than `mvn verify`?". It is a question, not a finding: only the owner knows whether the gap is intended.
- **What is often missing**: the working process (when to stop and ask, the definition of "done", what to do with a flaky test, how to split a task) and per-task-type procedures (contracts) rather than a single monolith. The absence is not a defect if the repo targets human assistance; it is one if the goal is to delegate whole tasks.

In this mode, the "cut the agent" test becomes: *if we delete the file, what does the CI let through that it did not let through before?* Each answer is a rule to push down to L3.

## Relevance review — what no longer serves

Models improve, repositories change: a line that was useful two years ago may have become a weight, or a hindrance. The question asked of each instruction file and line is not "is it true" but **"does it still change what the agent does"**. This review runs at every audit of an instruction file, and alone when the user asks for it (model change, file that grew, six months elapsed).

Start with `python3 "${CLAUDE_PLUGIN_ROOT}/cli/harness.py" rules <repo>`: one line per rule, with its date (the one it carries, `[YYYY-MM]`, otherwise git's), its age, its declared guardrail, its justification. A rule without date, without why and without guardrail is the first to examine.

Three reasons for removal, not to be confused:

| Reason | `reason` | It is | Proof to cite | Who decides |
|---|---|---|---|---|
| **Useless** | `useless` | Discoverable in the repository, or what a model does without being told: tree, stack, "clean code", "think step by step", session log | Where it is discoverable, or why it is default behaviour | The audit |
| **Harmful** | `harmful` | Degrades the work of today's agent: workaround for a tool limit that is gone, instruction that contradicts a guardrail or the declared mode, command that does not exist | The guardrail, workflow or file that contradicts it | The audit, and it reports it separately: it is more than a context cost |
| **Outdated** | `outdated` | True yesterday, not today: a version, a browser, a tool, a team constraint | What dates it in the repository, if anything does | **The owner.** The audit asks the question (`ask_owner`), it does not decide |

What is not removed:
- A line born of an incident, even if it looks obvious. It is precisely the one the repository does not say. In a generated file of a hundred lines there are often two, at the very bottom.
- A rule whose guardrail is partial: it is kept, and the leak is reported.
- A healthy, enforced rule: it is **shortened** to its "Enforced by" line, that is not a removal.

Doubt favours the question, not the removal: a line you do not know whether it still serves goes into `owner_questions`. And zeal is a measured defect: proposing to remove a line worth gold costs more than leaving ten useless ones.

In the report, removals go in the section "Lines to remove" and the JSON `removals` list, one entry per line or per homogeneous block, with the text quoted. A file to remove entirely is an item with verdict REMOVE. Questions to the owner are numbered, each with why it is asked and the proposed default.
