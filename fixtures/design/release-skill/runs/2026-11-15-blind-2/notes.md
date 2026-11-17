# Notes

## What I lacked or what got in the way
- **Piece 9, `current=ci_check` cannot be demonstrated from the repository.** The skill says to open the workflow: the `commitlint` job exists (`ci.yml:12-19`), runs on PRs to `main` and fails without `continue-on-error`. But "blocking" depends on branch protection (required check), which is on the forge and which nothing in `artifact/` shows. I settled on `ci_check` / KEEP; if the check is not required, it is a PUSH_DOWN. The skill does not say what to do when the workflow opens but whether it is required stays invisible.
- **Piece 4, `bypass_rule=dev` leads to "nothing merges without it"**, whereas the requirement bears on publication, not on merge: a changelog entry for a version is checked at the time of publishing (step of the delivery workflow), not necessarily on every PR. The grid has no answer "nothing is published without it". Destination kept as is, to be wired into the release workflow.
- **Piece 5, limit or rule?** "Never publish outside main" bounds an action (limit → server protection), but concretely it is the protected environment of the delivery workflow (deployment branch = `main`) and the rights of the npm token: the destination overlaps that of pieces 6-7. Not wrong, but the plan does not link them.
- **Piece 3, "a miscomputed version is an incident"**: the owner's answer speaks of an incident, a question that exists only for `rule`. For a `compute`, it changes nothing to the destination (`cli`); I assumed the tests of the subcommand carry it. `when=on_demand` chosen rather than `repo_event`: the skill and the workflow both call it.
- **Without a CLI in the repository** (said by the owner): "Tested CLI subcommand" reads as an npm script of `package.json`; the table of step 5 says so, the grid does not.
- **Pieces 6 and 7**: tag and publication have the same nature and the same destination; nothing says whether one piece or two are needed. I made two (two steps, two pieces of evidence).
- **"Under the plan, one line per piece"** whereas `plan.md` must be the output as is: I put those lines here.

## Outside the plan (to be reworded, not pieces)
- `SKILL.md:16` asks the agent to copy the token from `.npmrc.publish` into `.npmrc`: contradicts the owner's answer (never readable by the agent) and relies on the "outside a release" exception of `AGENTS.md:6`. Sentence to remove; the token becomes a secret of the protected environment on GitHub. The token has already leaked (`AGENTS.md:6`): to be rotated.
- `release-reviewer.md:4`: tools `Read, Grep` only, whereas it must read "the commits since the last tag" (`release-reviewer.md:7`): it lacks access to `git log` (or the list of commits passed as input).
- `ci.yml`: `commitlint` only checks the commits of the PR; with a squash merge, the commit that lands on `main` (PR title) is not checked, whereas the version is derived from it.
- `SKILL.md:13` "stop and ask for it" and `SKILL.md:14` `git branch --show-current`: become calls to the commands of pieces 4 and 5, no longer sentences.
- No `.claude/settings.json` nor MCP server declared in `artifact/`: permission (8) and MCP (12) are to be created.

## What I could not place
- Nothing was left without a destination. Reservation: "three lines at most, without repeating the changelog word for word" (`SKILL.md:17`) stayed in piece 10 as the frame of the judgment (preference, free tone), not as a separate rule.
