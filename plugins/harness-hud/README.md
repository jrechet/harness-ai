# harness-hud

A small heads-up display for a repository set up with the harness-ai plugin. It shows where the
repository's AI harness stands: one quiet row above the prompt with the level reached and the next
one, and a pane (`/harness-hud`) with the ladder, what is missing for the next level, what was set
aside, and the next step.

```
/plugin marketplace add jrechet/harness-ai
/plugin install harness-hud@harness-ai
```

It reads `.harness/state.json` in the folder the session starts in, and nothing else. It runs no
command, writes no file and judges nothing: the numbers are the ones `harness status` last wrote,
with the day that state last changed. Where that file is absent there is no row; the
`/harness-hud` command stays, and its pane says there is no state.

The row has a Hide button. Hide lasts for the session; `/harness-hud` brings the row back.

It is a Claude Code mod: code that runs inside Claude Code with your rights, on an interface Claude
Code marks as early access, so a later release may change or break it.
