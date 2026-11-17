# Fictional owner — vibe-app (counter)

This file is given to the agent that plays harness-init as a blind run: these are the owner's answers to the interview. It holds none of the planted facts; those are in the repository, to be found.

The owner runs the bakery. He made the application in eight sessions with an agent, between February and May 2026, and never reviewed it: he describes what he wants, looks in the browser whether it works, and moves on.

## Answers to the interview
1. **Mode**: delegation. "I say what I want, the agent does it, I look whether it works. I do not read the code, I would not know how."
2. **Team**: him alone.
3. **CI**: none. "I do not know what that is. The agent tells me the tests pass, I believe it."
4. **Tools**: Claude Code alone.
5. **First task to delegate**: a small end-to-end feature. The next on his list is cancelling an order.
6. **Forbidden**: losing or damaging customers' orders; installing anything ("no `npm install`, last time it broke everything"); changing payment provider; triggering a real payment.

## If the agent asks other questions
- About the code, whatever the question ("routes or routes-v2?", "why three formatting functions?", "what does this test check?", "is the README right?"): "I do not know, I never reviewed it."
- "Where do CLAUDE.md, PLAN.md, NOTES.md come from?": the agent wrote them at the end of each session. He did not review them either. The dates are right. When two notes contradict each other, the most recent is the right one: he never went back on a decision.
- "Were there incidents?": yes, two Saturdays went wrong in the spring. He could no longer say what or when; the agent noted it at the time.
- "May I delete lines, or these files?": `PLAN.md`, yes, he never used it. `NOTES.md`, keep what serves and throw the rest away. `TODO.md` is his list of requests, it is not touched without him. In every case, tell him what was removed and why.
- "Where does the application run? The shop PC, Node 16?": not since the summer. It is on a small rented server, set up by his nephew; the till PC is now only used for the till. He does not know the server's version of Node.
- "The PayFlux key?": he did not know it was in the repository. It is a test key; he can make a new one from his dashboard if he is told how.
- "`npm run dev`, `npm run lint`, Docker?": never run. He double-clicked on `start.bat`, and since the move he no longer starts anything himself.
- "Backups?": his nephew set something up on the server, he does not know what.

## What the owner expects
That the agent stops breaking what worked. A short file, which he can read in two minutes even if he probably will not read it, and the list of what was removed.
