# Notes on the run

KIT = the `coach-run-2` folder. All paths below are relative to it.

## Commands run, with exit codes

1. Read `plugin/skills/harness-coach/SKILL.md` (Read tool, ok).
2. `ls -la . tmp; cd repo; git ls-files | head; find . -type f -not -path './.git/*'` — exit 0.
3. `python3 plugin/cli/harness.py place grid` — exit 0.
4. `cat -n` of `repo/AGENTS.md`, `repo/.claude/agents/release-reviewer.md`, `repo/.claude/skills/release/SKILL.md`, `repo/.github/workflows/ci.yml`; `ls -la . .claude`; `git log --oneline` — exit 0.
5. `git remote -v` (empty output: no remote); heredoc writing `tmp/pieces.json`; `python3 plugin/cli/harness.py place review tmp/pieces.json` — exit 0 on the first try (12 pieces: 4 well placed, 8 to change).
6. After the run, for the record: `mkdir -p out && python3 plugin/cli/harness.py place review tmp/pieces.json > out/review.md` — exit 0.

No exit 2 or 3 was met. `place grid --format json` was not run (no concept question from the user). `status` was not run. Nothing was written in `repo/`.

## What was unclear, missing or in the way

- **Valid values of `current` are not listed anywhere I read.** The skill gives examples (`skill`, `agents_md`, `subagent`, `session`) and I inferred the rest from the "Destinations" ids of `place grid` (`ci_check`). It worked, but it was a guess.
- **"Found blocking" cannot be established from a local clone.** The skill says a rule that cites a check "you opened and found blocking" is held by the check. From the files I can see that the `commitlint` job exists and fails on a bad message; whether it is a *required* check is a forge setting, invisible here (no remote, no `gh`). The skill does not say what `current` to give in that case. I chose `ci_check` and declared the assumption.
- **Several artifacts in one request.** The skill is written for "one artifact"; the user named three (skill, subagent, AGENTS.md rules). I put them in one pieces file. Side effect: the "Two things in one" section speaks only of the skill and is silent on the others, and I had to say that by hand.
- **Pieces with no clean kind.** "Three lines at most" is a checkable preference inside a judgement; I folded it into the judgement piece. The subagent's `tools: Read, Grep` is a limit already held by the frontmatter; I did not make it a piece because I did not know which `current` value names "held by the subagent's own tool list". The line `Mode: assistance.` of AGENTS.md was left out (the user asked about the rules).
- **"Send the announcement"** is a piece I derived from "before sending it" (SKILL.md:18): no step of the release skill actually says to send. It is both a finding (action without a guard) and a remark (missing step); the border between the two is thin here.
- **Step ordering** (the uncommitted-files check placed last) is probably the most useful thing for the author, and the command cannot see it: it only appears as a remark.
- The review groups "An action without a guard" as a concept; the skill's description lists five concepts and does not mention this one nor "Two things in one". I used the review's own names, as step 4 asks.
- The review's "Better: Agent permission" text mentions `.claude/settings.json`, a tool-specific path; I paraphrased it as "shared settings of the repository".

## Why I asked the user no question

The skill, step 2: "Propose an answer from what the artifact says, and tell the user which ones you assumed. Ask only when the review would change with the answer." I read that as a default of assuming and declaring. What I assumed:

- `incident`: `yes` for "only from main" and "no uncommitted files", `forget` for the changelog entry. Whether `yes` or `forget`, the route and the finding are the same; only `no` would change it, and the skill's own wording ("Never publish", "stop") argues against `no`.
- `bypass_rule`: `release` for those three. `dev` would give a CI check instead of a delivery step, the same concept ("a condition that can be skipped"), a different destination. The lines are about the moment of publishing, so `release` followed from the text.
- `bypass_limit`: `agent` for `.npmrc.publish`, because the rule itself says "The agent never reads".
- `incident: yes`, `bypass_rule: dev` for Conventional Commits, from "the version is derived from them" and the CI citation.
- `current: ci_check` for Conventional Commits, that is: the `commitlint` job is required on `main`.

Honestly: the last one is the assumption where the review *does* change with the answer (well placed versus "a condition that can be skipped"), so by the letter of the skill it was a candidate for a question. I did not ask because (a) the "Common pitfalls" entry pushes towards crediting a cited check that exists, (b) one question about a single line out of twelve seemed a poor trade against delivering the whole review, and (c) I could state the assumption and its consequence in the reply. That is a judgement call, not something the skill settles; a stricter reading would have stopped to ask whether `commitlint` is a required check. Note also that the job runs only on `pull_request`, so a direct push to `main` escapes it unless the branch is protected, which reinforces that the answer was not knowable from the files.
