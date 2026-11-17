# Notes — review of the `release` skill with harness-design

Need restated: that each version be computed right, documented, published from `main` only, without the agent seeing the token, then announced.
11 pieces, `place plan` exits with code 0.

## What got in the way
- **`current` of an "Enforced by" rule whose workflow is absent** (piece 8, `AGENTS.md:7`). The skill says to open the workflow to check; `artifact/` does not contain `.github/workflows/ci.yml`. I put `current=agents_md` (not proven blocking), hence PUSH_DOWN. If the `commitlint` job exists and is required, the verdict is KEEP. The skill does not say what to do when the cited check cannot be found.
- **"Miscomputed version = incident" has no question in the `compute` branch.** The grid only asks `when`; the incident does not change the destination (tested CLI). I did not add a `rule` piece "the published version is the computed one": it does not exist in the artifact, and the delivery workflow that calls the subcommand holds it. An assumption, not a certainty.
- **Sending the announcement to `#releases`** (piece 11): `access` only offers `consult` (reads or comments) or `deliver` (build, tag, publication). Posting a message is an external write that is neither; I answered `consult` → MCP server, without conviction. The repository declares no MCP server.
- **Form constraint of the announcement** ("three lines at most, without repeating the changelog", `SKILL.md:17`): as a `rule` with `incident=no`, the grid leads to `scope`, none of whose answers says "only in this skill" (`reference` → a separate doc, too heavy). I left it in judgment piece 9. Probable gap in the grid: a preference specific to a procedure.
- **The token**: `SKILL.md:16` asks the agent to copy the token, `AGENTS.md:6` allows it "outside a release" only; the owner says "never". I cut it in two: the limit (piece 7, `deny` permission, `bypass_limit=agent` since a developer has access to it) and the use of the token, absorbed by the delivery workflow (piece 6, protected environment secret). The AGENTS.md line and step 5 of the skill are therefore to be rewritten, not only moved; the PUSH_DOWN verdict does not say so.
- **PUSH_DOWN verdict on piece 4**: the changelog is required at publication, not at merge; "blocking CI check" reads here as a check of the release workflow (or of the release PR). The grid does not tell the two apart.
- **Without a CLI in the repository**: "tested CLI subcommand" (piece 3) becomes a script called from `package.json`; the table of step 5 says so, the plan output does not.
- `place plan` does not display the `evidence`; I do not know whether the `path:line` format relative to `artifact/` is validated at this stage.

## Observed outside the grid
- `release-reviewer` only has `Read, Grep` but must read "the commits since the last tag": without git, it cannot. The plan says KEEP on the place; the content is to be fixed.
- The line "Mode: assistance" (`AGENTS.md:3`) is not a rule: not split off.

## Not placed
- Nothing was left without a destination. Two placements are fragile: piece 11 (sending the announcement) and the form constraint of the announcement, merged into piece 9.
