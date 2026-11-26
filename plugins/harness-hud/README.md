# harness-hud

A small heads-up display for a repository set up with the harness-ai plugin. It shows where the
repository's AI harness stands: one quiet row above the prompt with the level reached and the next
one, and a pane (`/harness-hud`) with the ladder, what is missing for the next level, what was set
aside, and the next step.

It reads `.harness/state.json` and nothing else. It runs no command, writes no file and judges
nothing: the numbers are the ones `harness status` last wrote, with their date. In a repository
without that file it draws nothing. The row has a Hide button.
