# Notes

## What I lacked or what got in the way
- **A preference specific to a skill has no slot.** "Three lines at most, without repeating the changelog word for word" (SKILL.md:17): `rule` → `incident=no` → `scope`, and no option of `scope` says "only during this skill". `reference` would send it to `docs/agents/`, which is wrong for one sentence. I left it in piece 8 (judgment), without placing it separately: a gap in the grid.
- **"Miscomputed version = incident" has nowhere to be said.** The `compute` branch only asks `when`; severity changes nothing to the destination. I answered `on_demand` (CLI; here a `package.json` script, the repository having no CLI), the delivery workflow having to call the same script. I did not add a piece "the published version is the computed one": it does not exist in the artifact.
- **`current` of a computation or a check written in prose in a skill**: `skill` or `session`? The skill's trap only decides for "a choice left to the agent". I put `skill` (the verdict is PUSH_DOWN in both cases).
- **Publishing outside main: limit or precondition?** The sentence (SKILL.md:14) has the form of a check before continuing, and the trap "precondition = rule" pulls towards `rule`/`release_gate`. I kept `limit` + `bypass_limit=dev`: it bounds an action and the owner says "nobody, developers included". Both readings are defensible; the skill does not say how to decide.
- **Hook for "uncommitted files"**: the destination speaks of a hook "after an edit, or on stop", whereas here a hook *before* the launch of the release is needed (PreToolUse on the release command). And once publication has moved into the workflow (piece 6), the CI checkout is clean by construction: the hook only guards the local start.
- `plan.md` is the raw output of `place plan`; the "under the plan" lines the skill asks for are below, for lack of a place to put them without altering the output.

## Under the plan (one line each, not pieces)
- SKILL.md:16 has the agent copy the token: contradicts the owner's answer and AGENTS.md:6 ("outside a release" is the exception to remove). With piece 6, the token becomes an environment secret on the forge.
- SKILL.md:19: the "uncommitted files" check is in step 8, after publication; SKILL.md:14 checks the branch after the computation. Order to be reworked.
- `release-reviewer` only has `Read, Grep`: it cannot read "the commits since the last tag" (release-reviewer.md:4 and :7). Missing tool, or commits to pass to it as input.
- Piece 12 — to confirm: is the `commitlint` job a required check on `main`? It only runs on `pull_request` (ci.yml:3-4); a direct push to `main` escapes it without branch protection.
- Piece 5: a setting to be made by a forge administrator (protected environment limited to `main`, npm publication through that environment only). Nothing in the repository is enough.
- Piece 9: no MCP server nor `.claude/settings.json` in the artifact; the system behind `#releases` is not named.

## What I could not place
- The form constraint of the announcement (three lines, no copy of the changelog): see the first point.
- The `test` job of ci.yml: outside the requested scope, not placed.
