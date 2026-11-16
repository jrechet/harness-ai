An incident is investigated before it is fixed, and fixed through the ordinary path:
- **Impact first.** Who is affected, how, since when. What restores the service comes before what explains it.
- **Facts, quoted.** A log line, an alert, a commit, a time. What is not in a piece of evidence is a hypothesis.
- **A cause is a hypothesis** until someone has verified it, and a recent change is not a culprit.
- **Nobody acts in production without an order.** Restarting, rolling back, changing a configuration, purging data: that is the on-call person's decision, through the commands of the team's runbook.
- **Evidence is production data.** It is not stored in the repository, and what comes out of it (a ticket, a message) carries no secret and no personal data.
- **The investigation ends in a ticket**, with acceptance criteria, that goes back through the ordinary path.

The team's runbook is written here: where to read the logs and alerts, the read-only diagnostic commands, the mitigation commands and who decides them.
