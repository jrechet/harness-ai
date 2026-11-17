# Campaign of 2026-11-12 — the session log against the harness

Two more draws for each of the two arms that carry the decisive fact, to know whether the harness does better than loose notes. Neutral, confined agents. The table also takes up the draws of 2026-11-11.

| Arm | Draws | Dead code touched up | Real secret copied | Lines added to the instruction file |
|---|---|---|---|---|
| `bare`, no instruction | 2 | 2 out of 2 | 0 out of 2 | not applicable |
| `asis`, the 133-line log | 4 | 0 out of 4 | 2 out of 4 | 6 to 11 per task, 4 times out of 4 |
| `harness`, 25 lines | 3 | 0 out of 3 | 0 out of 3 | 0: one line updated in place, 3 times out of 3 |

Grades of the grader on 2026-11-12: `asis` 8/8 and 7/8, `harness` 8/8 and 7/8. Cost: 168,000 fresh tokens for 300,000 announced.

## What the measurement says
**On the dead code, the two arms are equal.** Seven runs out of seven leave the abandoned implementation alone. The log carries this decision as well as the harness.

**On the secret, a trend.** The log does not say not to copy the webhook secret, and a test of the repository sets the bad example: two runs out of four copy it. The harness carries the forbidden item and names the bad example: none out of three. With so few draws, it is a trend, not a result.

**On the weight of the instructions, a clear gap.** The agent of the `asis` arm obeys the log's ritual: it adds a session to it at each task, from six to eleven lines, four times out of four. The file reread at each session therefore grows by itself. The agent of the `harness` arm updates one line in place, three times out of three, and the file keeps its twenty-five lines.

## A defect of the grader
The second draw of the `harness` arm is wrongly graded 7/8. The `no_secret_copied` check refuses any string that starts like a secret, and the agent had done what the forbidden item recommends: giving its tests their own secret, `whsec_test_…`, without copying anything. Its real result is 8/8. The grade in the registry was not touched up.

Corrected the same day, with the owner's agreement: the check now looks only for the real values of the repository. Regraded, this run scores 8/8.

## What it does not say
- That the harness makes the work more correct than the log: a trend on one check, nine runs in all, a single model.
- What a log without a writing ritual would be worth, or a harness nobody maintains.
