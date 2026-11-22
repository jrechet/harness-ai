# CI as the engine: a ticket state and short jobs

Date of the facts: 2026-11-21, from [report.md](report.md).

A team flow can run on what the team already owns: the ticket or the pull request holds the state, and each event starts one short CI job.
It gives no resume inside a job, so five cheap protections do the work an engine would do. `python3 cli/harness.py flow check`, this project's command that reads a flow's JSON definition, refuses a definition without two of them and prepares a third; two wait for commands that are planned.
It is the study's default, and it rests on converging accounts, not on a measured comparison.

**Words used, defined once.**

- **Flow**: one team workflow for one kind of ticket. **Step**: what happens in one state of the flow. **Definition**: the JSON file that describes the flow. **Run**: one ticket going through it.
- **Agent**: a model that calls tools in a loop until a task is done. Here, a coding agent such as Claude Code or Codex.
- **Forge**: where the repositories live and where merges are decided (GitHub, GitLab, Forgejo). **CI**: the forge's pipelines. **Job**: one unit of a pipeline, on one machine. **Runner**: the machine that runs a job.
- **Tracker**: where the tickets live. It can be the forge itself, or an outside tool such as Jira or Linear.
- **Engine** (workflow engine): a product that records each finished step, so a run that crashes continues where it stopped ([engines.md](engines.md)).
- **Concurrency group**: a CI setting that lets one run at a time proceed under a given name.
- **Dispatch**: starting a CI run from outside, through the forge's API, with inputs.
- **Sweep**: a scheduled job that lists the tickets whose state and runs disagree.
- **Environment approval**: a forge setting that pauses a run until a named person approves. **Job token**: the credential the forge gives each job automatically.
- **Idempotent**: safe to run twice.
- **Evidence labels**, kept from the report: [M] read from a registry, a repository or a specification; [V] said by a company about itself; [S] said by a third party.

## 1. How a ticket state and short jobs make a flow

A forge event (a label, a comment, a check that finished, a schedule) starts a job. The job runs a coding agent once. The state is what the job writes on the ticket or the pull request (report §3.3). Between two jobs nothing is alive.

```
ticket state    ready ──────> coding ──────> ci ──────────> human-review ──────> merging
                  │             │             │                  │
what happens    event:        job 2         nothing runs:     nothing runs:
                label added   agent codes,  CI works          a person reads
                  │           code pushes     │               the pull request
                job 1         and writes    event:               │
                claims the    the new       check finished    event:
                ticket        state           │               approval
                                            job 3                │
                                            reads the         job 4
                                            result            checks the branch,
                                                              merges
```

Three things make this work.

- **Every wait is between two states.** In both reference flows of the study ([flows.md](flows.md)), plan review, CI, human review, merge and the closure check are waits during which nothing needs to stay alive. No step holds an expensive computation that must resume in its middle. So, on paper, neither flow needs an engine. The note that first drew this conclusion calls it "a hypothesis to test on real team workflows, not a result" (report §6.3).
- **A human gate is a state only a person may set.** The change of state is the event that starts the next job. It is the one form of gate that exists on every forge compared here (report §3.3, §6.3).
- **The ticket is the place people steer from.** OpenAI's Symphony keeps no database: the ticket status is the state, and a person moves the ticket to `Merging` before the agent may land the change [M] (report §5.1, patterns 5 and 6).

The shape of one job, as the study recommends it (note gap_runtime_on_self_hosted_forge_and_language_choice.md, section 2.3, and section 5 for the work step). It is a design, marked as the note's own inference. What starts the job (a rule in the tracker, a relay, or the sweep alone) is in section 4 of this page, last item.

1. **Claim.** Read the ticket. If it is not ready, end green. Otherwise mark it in progress and write the run identifier on it.
2. **Work.** One short step, with a timeout, calling the agent once with a cap on turns and on dollars.
3. **Final status by code.** The last step, always run, writes the outcome on the ticket and the pull request.
4. **Sweep, on a schedule.** Every 5 to 15 minutes: start again the "ready" tickets with no run, flag the "in progress" tickets with no live run.

**Evidence that CI carries load.** Cloudflare runs its code review as "a fully contained GitLab CI component" that starts a coding agent as a child process: 131,246 review runs in 30 days, median 3 min 39 s [V, self-reported with sample sizes]. It is a large company and a review step, not a ticket flow (note gap_small_team_engine_threshold_and_cost.md, section 1.3).

**Evidence that is missing.** No first-hand account exists of a team of 5 to 50 running a ticket flow on any runtime, CI included [M: searched and not found]. No team documents this exact shape with failure counts (report §9.1).

## 2. The limits

Read from GitHub's documentation [M] (report §3.3; note orchestration_alternatives.md, section 5.3).

| Limit on GitHub Actions | Value |
|---|---|
| One job on a hosted runner | 6 hours |
| One job on a self-hosted runner | 5 days |
| One run, waits and approvals included | 35 days |
| Waiting for an environment approval | 30 days |
| Jobs in one fan-out (a matrix) | 256 |
| Re-runs of one run | 50 |

A "59 minutes" limit is sometimes quoted. It is a different thing: the cap of one Copilot cloud-agent session (report §3.3).

On other forges: GitLab's job timeout is a project setting, 60 minutes by default. Forgejo documents a timeout per job and per step, and states no default [V][M] (note gap_runtime_on_self_hosted_forge_and_language_choice.md, sections 1.2 and 1.4).

What follows from these limits. The first three are the note's reading of them, not quoted facts (note orchestration_alternatives.md, section 5.3).

| Consequence | What it means for a flow |
|---|---|
| No memory between runs | A run leaves only what it wrote: a comment, a label, a commit. The next job rebuilds its context from the ticket |
| No resume inside a job | A failed job starts again from its first line and pays its tokens again |
| A human answer is a new event, not a pause | Only an environment approval pauses a run. A question asked in a comment is answered by a new run |
| The cost is double | Runner minutes plus model tokens, on every event [M] |

## 3. The five cheap protections

The first failures a small team meets are duplicates, silent losses, loops that burn tokens and an unknown cost. None needs an engine. They need five protections (report §5.3, marked "my reading"; note gap_small_team_engine_threshold_and_cost.md, section 5). Each was missing in at least one open-source orchestrator, and the cases below come from their issue trackers. Those trackers over-represent failures, and the team size of the reporters is not stated (report §5.3).

| # | Protection | The failure it prevents | A case where it was missing |
|---|---|---|---|
| 1 | **A key derived from the ticket**, never a random one, on every write to the outside | A retry repeats a write: a second comment, a second session | A completion message posted twice, because each retry got a fresh random identifier [M] |
| 2 | **One run at a time per ticket**: a concurrency group named after the ticket, plus the claim step | Two runs work on one ticket at once | 9 review sessions on one pull request, 3 at once [M]; one issue that started 16 sessions in 45 minutes [M] |
| 3 | **A budget cap per run**, in dollars or tokens, with a cap on every loop and empty turns counted as failures | An agent loops and burns tokens while it looks healthy | "This bug cost me 15M tokens" [M] |
| 4 | **A scheduled sweep**, with a job timeout far under the platform limit and a final status written by code | An event is accepted, nothing happens, nobody is told | 20 of 135 review sessions (about 15%) silently lost on one install, one reporter's count, since fixed [M] |
| 5 | **A cost line**: the step writes tokens and dollars on the pull request | Nobody can say what a ticket cost | No supported way to read the cost of a run from Anthropic's CI action [M] |

Sources for the cases: report §5.3; note gap_small_team_engine_threshold_and_cost.md, section 5 (rows 2, 3, 4 and 10).

Two remarks.

- The third failure has no fix in any engine: an engine retries a looping agent faithfully. The cap is yours to write on every runtime (report §7).
- Protections 2 and 4 work together. The study's wording: the tracker is the store that removes duplicates, and the concurrency group is the lock. A duplicate event meets the claim step and ends. A lost event leaves a "ready" ticket that the sweep finds (note gap_runtime_on_self_hosted_forge_and_language_choice.md, section 2.3).

### What `harness flow` already refuses on paper, and what waits

`python3 cli/harness.py flow check <file>` reads a definition and runs nothing: no job, no forge call, no clock. So it can refuse a flow that was designed without a protection. It cannot show that the protection holds on a real run. The refusal codes are those of [flow-spec.md](flow-spec.md), section 2.

| # | Protection | Refused by `flow check` today | Waits for |
|---|---|---|---|
| 1 | Key derived from the ticket | **Yes.** `write_without_key`: a write whose key is missing or does not contain `{ticket}`, or a key already used for another write | A command that performs the write: `flow run-step` (planned, not built) |
| 2 | One run at a time per ticket | **No.** Nothing in a definition says it, and no rule checks it | `flow claim`, which marks the ticket, and `flow render`, which writes the concurrency group in the CI file (both planned, not built) |
| 3 | Budget cap | **Yes, as a design rule.** `no_budget`: no budget in dollars and minutes for one ticket. `loop_without_cap`: a circle of steps that no cap bounds | Enforcement inside a real job: `flow run-step`, with its turn cap and dollar cap (planned, not built) |
| 4 | Scheduled sweep | **In part.** `wait_without_deadline` and `gate_without_deadline`: every wait and every gate must carry a deadline in hours. That is the number a sweep needs. Nothing reads a clock yet | `flow sweep`, and the job timeout written by `flow render` (both planned, not built) |
| 5 | Cost line | **No.** `flow check` has no rule for it | `flow report`, the last step of every job (planned, not built) |

So, of the five: two are refused on paper today (1 and 3), one is prepared (4), and two wait entirely for planned commands (2 and 5).

`flow next` lets you try by hand what is behind three of them, one event at a time, still with nothing run ([flow-spec.md](flow-spec.md), section 3). Near protection 1, a delivery made twice: an event whose identifier was already seen changes nothing (`already_seen`). Protection 3, the budget and the caps: a run stops when its spending passes the budget (`budget_exceeded`) or when a step reaches its cap (`cap_reached`). Protection 5, the cost: an event that ends a program step or an agent step without its cost is refused (`cost_missing`). It tries neither the lock (2) nor the sweep (4). Two limits to keep in mind: the caller must pass one run at a time, which is the queue per ticket that comes with `flow claim` (planned, not built); and the costs are numbers you type, not numbers read from a job.

`flow check` also refuses a step that follows a wait without checking that its facts still hold (`wait_without_premise_check`). That is not one of the five. It answers the stale facts that an engine does not remove either ([engines.md](engines.md), section 2).

## 4. What stays fragile

The protections remove the first failures. These remain.

- **A job that fails late is paid twice.** Short jobs limit it; nothing on CI removes it. GitHub Agentic Workflows, GitHub's product for agent jobs, has by design "no automatic retries" [V] (report §3.3).
- **How fragile CI is, is not known.** GitHub's own repository shows 25 failures in a sample of 100 runs over one day [M]. The sample is very likely capped at 100, covers 55 workflows with smoke tests and experiments, and is not a failure rate of the product (report §5.3; §11, claim C11).
- **Jobs that hang or die at once.** On Anthropic's CI action, a 2025 issue reports about 20% of runs that never answered, the job held until the 6-hour limit; a 2026 issue reports exits in about 150 ms at no cost, now and then, on the same configuration [M, each on the reporter's install] (note gap_small_team_engine_threshold_and_cost.md, section 1.3).
- **"Accepted" does not mean "ran".** A dispatch call that returns success proves only that the forge accepted the request [V] (note gap_runtime_on_self_hosted_forge_and_language_choice.md, section 2.2). This is why the sweep is not optional.
- **A change made with the job's own token starts no pipeline.** On GitHub a pull request created with the default token does not start CI; Forgejo states the same rule [M]. Chaining needs another credential (note orchestration_alternatives.md, section 5.3; note gap_runtime_on_self_hosted_forge_and_language_choice.md, section 1.2).
- **Text from a ticket ends up in a prompt.** One vendor showed untrusted text (an issue title, a pull request body) inserted into an agent prompt in CI with a privileged token, confirmed on one Google repository [V]. A paper ran 11 attack scenarios on live workflows across four AI providers; each provider fell to at least one [M] (note ticket_to_prod_orchestration.md, section 6). GitHub Agentic Workflows answers with an agent job that is read-only and writes that pass through checked "safe outputs" [V] (report §3.3). Whether a self-hosted runner can be made as safe is not known (report §9.1).
- **A tracker outside the forge needs a bridge.** A Jira rule can call the forge's dispatch endpoint with no code, with no documented retry, and only if the forge is reachable from Atlassian's addresses on an allowed port. Linear needs a small relay [V][S] (report §3.3). The sweep alone can be the whole bridge if a few minutes of delay is acceptable.

Where the design stops being enough, by the study's own list (note gap_runtime_on_self_hosted_forge_and_language_choice.md, section 2.3, marked as inference): one ticket joined across several repositories; a money cap across all repositories; a reaction in seconds; a claim that must be atomic under real contention; events from three or more sources that must be ordered.

## 5. GitHub, GitLab, Forgejo: the differences

Everything about GitLab CE and Forgejo below was read from documentation and API files, not tested on a running instance (report §3.3, §9.1). The GitLab column is the free self-hosted edition and was not re-opened by the fact-check (report §11).

| Need | GitHub | GitLab CE (free) | Forgejo 17 |
|---|---|---|---|
| One run at a time per ticket | Concurrency group | `resource_group`: jobs wait in turn, nothing is cancelled | Concurrency group since 14.0. It **cancels the running job by default** on push and pull request events, so write the choice explicitly. "Best-effort", queue order not guaranteed |
| Start a run from outside with inputs | Yes | Yes, with a trigger token | Yes, typed inputs; no free-form event |
| Approval gate inside a pipeline | Environment reviewers | Paid tiers; on the free tier, a manual job | **None** |
| Shared workflow from a private repository | Yes | Yes | **No**; a contributor's branch of 2026-11-19 is not merged |
| Narrow the job's own token | Yes | Not re-read | **No**, except on pull requests from forks, where it is already read-only; a read-only token is "on the roadmap" |
| Official coding-agent action | Yes | Not checked | **No**; one small fork |
| Vendor agent flows | Agentic Workflows, generally available since 2026-10-28 [V] | Custom Flows, generally available since 2026-07-16 [V]; no user account was read, and their use on the free edition was not checked | None |

Sources: report §3.3; note gap_runtime_on_self_hosted_forge_and_language_choice.md, sections 1.2 to 1.5. Gitea 28 sits between GitHub and Forgejo: no approval gate, but a narrowed token and private shared workflows (report §3.3).

A concurrency group is not a full queue. GitHub and Gitea keep one running and at most one waiting run per group; a request for a longer queue is open on Gitea [V][M]. Forgejo queues when told not to cancel, and a bug where a queued run was never picked up was closed in September 2026 [M]. So write `cancel-in-progress` explicitly on every forge, and rely on the claim step and the sweep for what the group lets through or drops (note gap_runtime_on_self_hosted_forge_and_language_choice.md, sections 1.2, 1.3, 1.5 and 5).

Two consequences (report §3.3).

- The only human gate that exists on all of them is a ticket or pull request state whose change starts a new job. A flow built on it is the same on every forge.
- On Forgejo, sharing across private repositories means a thin workflow file per repository, with all the logic in one versioned command-line tool.

To test on your exact version before trusting it: label events after an issue is created, the queue of a concurrency group, whether a dispatch made from inside a job starts a run, and the behaviour under two runners (report §9.1). One user found on Forgejo 15 that a label added after the issue was created started nothing [M, one user, one version] (note gap_runtime_on_self_hosted_forge_and_language_choice.md, section 1.2).

## The symptom that would make you need it

**You need more than chaining by hand, that is, this design, when you can count one of these.**

- A person relays CI failures or review comments to the agent by hand. Atlassian reported exactly this in March 2026 [V] (note ticket_to_prod_orchestration.md, section 6).
- Agent sessions sit open for hours waiting for CI. Dropbox moved CI handling out of the agent for this reason [V] (report §5.1, pattern 2).
- The same ticket was picked up twice, or a ticket marked ready was never picked up, and nobody was told.
- Nobody can say what the last ten tickets cost.

**You need more than this design when one of these stays after its cheap fix** (report §7, last table; [decide.md](decide.md), section 3).

- More than about one run in ten dies far in and pays its tokens twice, with jobs already short.
- A wait must resume inside an expensive computation and cannot be made a ticket state.
- Many steps each need their own retry and timeout rule, and shared CI workflows no longer express them.
- First real runs lose or duplicate work at the rates of the worst issues above, with the five protections in place (report §9.2).

Then read [engines.md](engines.md). Until then: the ticket's state, a short job per step, and the five protections. Counting these symptoms on real runs is the work of `flow exits`, which is planned, not built.
