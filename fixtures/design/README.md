# harness-design fixtures

Misplaced artifacts, with their answer key. They measure what `harness-design` finds in review: is each misplaced piece sent to the right place, with its evidence, without touching what is healthy?

```
fixtures/design/<name>/
├── request.md       # the request and the owner's answers: given to the evaluated agent
├── artifact/        # the skill, the agent, the rules to review: given to the evaluated agent
├── traps.md         # each trap and each healthy item, and what the plan must say about it
├── expected.json    # the answer key read by the grader: file, lines, accepted destinations
└── runs/            # dated plans; <date>-author = the plan of the author of the traps; <date>-coach-* = a run of harness-coach, with its prompt and its reply
```

`traps.md`, `expected.json` and `runs/` are never given to the evaluated agent. The author's plan is a regression baseline, not a measurement: only a blind run measures the skill, and it is launched at the owner's request.

## Grading a plan

```bash
python3 cli/harness.py place check <pieces.json> --expected fixtures/design/<name>/expected.json
```

The grader is generous on the destination (several are accepted per trap), strict on the evidence (the piece cites a line of the expected range, `path:line` relative to `artifact/`) and on healthy items (none receives a verdict other than KEEP). Exit 0 if every trap is found with no healthy item moved, 1 otherwise.

`cli/tests/test_place.py` verifies at every commit that each answer key cites lines that exist and that its author's plan passes it, except the traps that `known-gaps.json` declares missed: a known gap of the grid, which the author is not allowed to hide by forcing an answer.

## Available fixtures

| Name | Artifact | Traps | What it tests |
|---|---|---|---|
| `release-skill` | A release skill, its subagent, two AGENTS.md rules | 7 + 3 healthy | Limit told as a story, computation in prose, check told as a story, delivery with a token from the workstation, tree copied out, limit of the agent written as a rule; and not touching a judgment, a justified subagent, a rule that cites its check |
| `ticket-to-pr` | **Held out** (`holdout`), in creation: a request of twelve needs for a ticket → PR tool | 12 | Giving its place to each nature of piece from a request: reading and writing through MCP, precondition in code, limit of the agent versus limit of everyone, blocking rule, subagent, judgment, folder convention, nothing to write |

A creation fixture carries `"mode": "create"` in its answer key: nothing exists, the pieces have no `current`, and the grader counts the destination returned. A `holdout` fixture never serves to correct the skill or the grid.
