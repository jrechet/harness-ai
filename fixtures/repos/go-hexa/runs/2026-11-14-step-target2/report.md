## Report

- **The step**: I added the "Step 2" block of the template at the end of `AGENTS.md`. It contains the "Maintaining this file" section, the `rule:` convention in review and the marker `<!-- harvest: last=2026-11-14 ref=init -->`. The file had no marker yet.

- **Before and after**: we stay at level 1 (Framed), with level 2 (Looped) as the target. Level 2 goes from **0/4 to 3/4** checks. Three lines flipped:
  - "A maintenance section says how the file evolves";
  - "The `rule:` review convention is documented";
  - "A harvest ran less than 45 days ago".

  Beware of the last one: it passes thanks to the `ref=init` marker, but no harvest has really run. The marker only starts the counter.

- **What it changes for the agent**: when a review comment starts with `rule:`, the agent knows it must add it to `AGENTS.md` in the same PR, with the date and a link to the comment. Before writing a rule, it must also look for a tool that can enforce it in its place.

- **What is not proven**: all the substance. `status` only observes that the sections are there, not that the feedback loop works. There is no proof yet: no harvest has run, no `rule:` has been written in review, no agent PR has been observed. The 4th check ("real signal") can only pass with time and real reviews. Adding a rule to make it pass would go against the goal.

- **Files**: `AGENTS.md`, which goes from 25 to 32 lines, under the limit of 60. I committed nothing, because nobody asked for it. The `.harness/` folder is still untracked by git; it already existed before this step.

- **Questions**: none. One habit remains to be passed on to the team: *"When a review remark deserves to become a rule, start your comment with `rule:` followed by the rule in one checkable sentence. The agent or the next harvest will carry it over to AGENTS.md."*

- **Possible next step**: there is nothing to do for now. The loop is in place but has not run yet. Once reviews have contained `rule:` comments or agent PRs have been corrected, harness-harvest will have to be run. If it finds a real signal, the 4th check will pass and level 2 will be reached.