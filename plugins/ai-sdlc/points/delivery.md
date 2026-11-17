A delivery is prepared, proposed, and decided by a human:
- **What ships.** The head commit of the remote delivery branch, arrived through a reviewed PR (the forge enforces that, not this phase). Nothing local, nothing uncommitted.
- **The CI.** Green on that exact commit, not on a neighbouring commit nor after re-runs until green.
- **The rollback.** Before delivering, we know which version we go back to, by which command, and who decides it. A schema or infrastructure change has its own, written.
- **Breaking changes.** What breaks for those who depend on the product is announced beforehand, with the migration path.
- **The notes.** What changes for the user, in their words, not the list of commits.
- **The timing.** Not just before an absence, not during an ongoing incident.

The agent does not tag, does not publish, does not start a deployment. The team's procedure (commands, environments, who approves) is written here: the agent quotes it, it does not run it.
