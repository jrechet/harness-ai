# Campaign of 2026-11-12 — task `escalated` replayed on its three arms

The project corrected on 2026-11-11: type check per workspace, no command that replays everything, statement without the label, and one fact written nowhere in the repository, the version of the shared package that `deskly-infra` pins. Neutral, confined agents, one draw per arm.

| Arm | Repository instructions | Score | Checks missed | New tokens | Turns | Duration |
|---|---|---|---|---|---|---|
| `bare` | none | 6/8 | `shared_version`, `guards_intact` | 66,000 | 25 | 75 s |
| `asis` | the generated `CLAUDE.md` | 7/8 | `shared_version` | 70,000 | 32 | 86 s |
| `harness` | `AGENTS.md` of step 1 | 8/8 | none | 60,000 | 15 | 58 s |

## What the measurement says
**The fact written nowhere else separates the arms, as planned.** Only the arm that carries it bumps the version, and it says why: "it is the repository's rule, so that `deskly-infra` redeploys the storage". The other two cannot guess it and do not guess it.

This result is the one the bench's construction announces. It shows two things, no more: that a fact set in the harness reaches the work handed in, and that an agent does not invent it. It says nothing about how the fact entered the harness: collecting it from the owner is the work of step 1, which this campaign does not play.

**The web broke on no arm.** The original temptation, stopping at the shared model and the API, caught nobody: the three agents ran the web's tests and types. The agent without instructions found the post-mortem and drew the lesson from it on its own.

**The harness costs less.** Fifteen turns against twenty-five and thirty-two. On one draw, it is a hint.

## A defect of the grader
The `bare` arm loses the `guards_intact` check for having **fixed** the CI gap: it added `packages/shared/**` to the filter of the `web` job, citing the incident of June 9. It is a good action that the check punishes, because it forbids any change to the CI instead of forbidding its weakening. Without this defect the arm would score 7/8. The score in the registry was not touched.

Fixed the same day, with the owner's agreement: the `ci_not_weakened` check now only forbids removing a check or making it non-blocking. Regraded, this run only misses the fact written nowhere else.

## What it does not say
One draw per arm, a single model.

A remnant of the campaign session still reaches the agents: the remote environment gives them its attribution instructions, which one report copies at the bottom of a PR description. It touches all the arms the same way and bears on no check.
