# Signal catalogue

What we look for, whatever the source. Each adapter (GitHub first) only produces these signals in the common schema below. A signal that is not in this catalogue is not collected: add it here first, then in the adapter.

The codes S1–S7 are for the files and the JSON. To the user, always say what the signal is, in the words of the "Signal" column.

## The signals, strongest first

| Id | Signal | What it says | Strength | Typical verdict |
|---|---|---|---|---|
| **S1** | Explicit rule: a review comment starting with `rule:` | Someone already stated the rule and points to the incident | Strong, enough alone | PUSH_DOWN if a tool is possible, otherwise ADD |
| **S2** | After-the-fact fix: a fix commit on files touched by an agent PR within 48 h after its merge; a revert; an agent PR closed without merge; a burst of "fix review" commits | The agent lacked a piece of information or a rule | Strong if repeated, medium alone | ADD or ASK |
| **S3** | Recurring correction: the same review comment pattern (same reviewer or same area) at least twice in the window | An implicit, unwritten team rule | Medium | ADD with the links, or PUSH_DOWN |
| **S4** | Ignored guardrail: a CI check that fails repeatedly on agent PRs | The rule exists in L3 but the agent does not know it or discovers it too late | Medium | SHORTEN or ADD of a well-placed "Enforced by" line |
| **S5** | Orphan rule: an AGENTS.md rule with no linked evidence in the window | Either it is so well respected it can be shortened, or it is dead | Weak alone, strong after two harvests | SHORTEN if guardrail, REMOVE otherwise after two harvests |
| **S6** | Recurring task: at least three PRs of the same type in the window (title, label, files) | A task contract is missing | Medium | CONTRACT |
| **S7** | Non-discoverable information asked for: the agent asks the same question or makes the same assumption in several PRs | AGENTS.md does not say something that cannot be deduced from the code | Medium | ADD under "What this repo does" or "What changes → what to run" |

What we do **not** look for: conventions guessed from the diff without an incident, style, preferences expressed once without `rule:`.

## Common evidence schema

Each adapter produces a JSON array of this type, one entry per piece of evidence:

```json
{
  "id": "<source>-<n>",
  "signal": "S1|S2|S3|S4|S5|S6|S7",
  "source": "github|gitlab|jira|...",
  "url": "<permanent link to the evidence>",
  "date": "<YYYY-MM-DD>",
  "author": "<login>",
  "agent_authored": true,
  "files": ["<path>"],
  "text": "<useful raw text: the comment, the PR title, the check name>",
  "related_rule": "<excerpt of the AGENTS.md rule concerned, or null>",
  "group_key": "<grouping key proposed by the adapter: area, reviewer+pattern, task type>"
}
```

The script does not judge: it decides neither the verdict nor the wording. It only spots, dates, links and proposes a grouping key.

## GitHub adapter — `python3 "${CLAUDE_PLUGIN_ROOT}/cli/harness.py" harvest github`

Standard Python 3, no dependency; `gh api` transport (already authenticated on a dev machine and in Claude Code sessions).

```
python3 "${CLAUDE_PLUGIN_ROOT}/cli/harness.py" harvest github --repo owner/repo --agents-md AGENTS.md \
    --agent-login claude --agent-branch-prefix claude/ --agent-label agent \
    --agent-trailer "Co-Authored-By: Claude" --summary > .harness/harvest.json
```

- Window: `--since YYYY-MM-DD`, otherwise the `<!-- harvest: last=… -->` marker of `--agents-md`, otherwise 30 days (announced on stderr).
- Agent markers, all repeatable: `--agent-login`, `--agent-branch-prefix`, `--agent-label`, `--agent-trailer`. A login ending in `[bot]` is always an agent.
- Dependency bots (`--automation-branch-prefix`, default `renovate/` and `dependabot/`): neither agent nor recurring task, and their merges are not fixes. A squash-merge of another PR only counts as a fix (S2) if that PR is a fix/revert or cites the agent PR. The author's comments on their own PR never count as S3.
- Exposed thresholds: `--fix-window-hours 48`, `--min-recurrence 2` (S3, S4, S7), `--min-task-count 3` (S6), `--burst-commits 3`, `--burst-minutes 60`, `--max-prs 200`.
- Output: on stdout, an object `{source, repo, since, default_branch, prs_scanned, agent_prs, counts, errors, evidence}` where `evidence` is the array of the schema above. Errors on stderr; exit code 2 if a source could not be read, the other evidence is still produced.
- Recurrence (S3, S6, S7): greedy grouping by Jaccard similarity on keywords, thresholds 0.6 / 0.6 / 0.5 as constants of the script. `group_key` carries the words common to the group.
- Tests: `python3 -m unittest discover -s cli/tests`, without network, on a fake repository that exercises the seven signals.

| Signal | Where to find it | Detection rule |
|---|---|---|
| S1 | Review and PR comments | Body that starts with `rule:` (case-insensitive, spaces tolerated) |
| S2 | Commits on the default branch, PRs | Non-agent commit touching a file of an agent PR merged less than 48 h before; commit whose message starts with `Revert` of an agent PR; agent PR closed without merge; at least three commits within an hour after a review on an agent PR |
| S3 | Review comments | Same author and similar normalised text (same keywords after removing noise) on at least two PRs |
| S4 | Checks of agent PRs | Same check name failing on at least two distinct agent PRs |
| S5 | Current AGENTS.md | For each bullet of the file (outside the Maintaining, Tasks, Commands sections, in French or English; continuation lines joined), no S1–S4 evidence whose `related_rule` points to it; the link is made by keywords and by cited files |
| S6 | PR titles, labels and files | At least three PRs whose normalised title or label is identical, or whose touched files overlap strongly |
| S7 | Agent PR descriptions | Question or assumption sentences ("I assumed", "I could not find", or the French « j'ai supposé », « je n'ai pas trouvé ») on the same topic in at least two PRs |

The thresholds (48 h, two, three) are defaults to expose as script options, not constants.

## Next adapters
- **GitLab**: same signals, same thresholds; MR notes replace review comments.
- **Jira / Linear**: produces only S6 and S7 (recurring task types, repeated questions in tickets). A ticket never produces S1 to S5.
