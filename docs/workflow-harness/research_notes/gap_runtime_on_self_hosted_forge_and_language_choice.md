# Gap note: the runtime on a self-hosted forge, the bridge from an outside tracker, and the language of the small piece

Research note, written 2026-11-21. It adds to the nine notes in this folder and settles a contradiction between two of them. Web search was available in this pass.

## Summary in five lines

1. **Forgejo 17 and Gitea 28 can now serve as the workflow engine for a ticket flow**, which was not true a year ago. Both have concurrency groups with cancel-in-progress (Forgejo since v14.0, January 2026; Gitea since 1.26.0, April 2026), a dispatch API with inputs, job timeouts, schedules and a REST API to write on issues and pull requests. What they still lack against GitHub Actions: **no environment or approval gate at all**, no `repository_dispatch`, no `workflow_run` on Forgejo, no official agent action, and on Forgejo no way to narrow the automatic token and no reusable workflow from a private repository.
2. So rows 2 and 3 of the threshold table (duplicates, silent loss) are fixable on a self-hosted forge with the same cheap means as on GitHub. Row 6 (wait for a human) is fixable only one way: the wait is a ticket or pull-request state and the answer is a new event. On GitLab CE the free-tier gate is a manual job; approvals and protected environments are paid.
3. **The smallest bridge from Jira is zero lines of code**: a Jira automation rule calls the forge's dispatch API itself. From Linear a relay is needed, because Linear sends a fixed payload, signs it, and wants a 200 answer within 5 seconds. Neither path is reliable alone: Jira's rule action has no documented retry, Linear retries three times then may disable the webhook. A **scheduled sweep job in CI** that lists "ready" tickets with no run is what makes either path safe, and can be the whole bridge by itself if a few minutes of delay is acceptable.
4. **Language matters less than the two notes assumed**, because the official Claude Agent SDK is not in-process: it "spawns and supervises a `claude` CLI subprocess" and talks to it over standard input and output. TypeScript and Python get the typed wrapper for free; Rust and Go write the same wrapper by hand (a few hundred lines) and own its upkeep. The real differences are who maintains the event parser, which runtime is on the runners, and which durable library exists if one is needed later.
5. The two notes do not truly conflict: one answers "should you run a daemon" (no, not first), the other "if you write the orchestrator in Rust, on what" (the documented CLI, behind your own adapter). The combined advice: **write the guaranteed logic as a CLI with subcommands, call it from CI jobs, keep state in the ticket and the pull request, and add a long-lived process only when a named condition in section 6 appears.** No team was found that documents exactly "stateless relay plus sweep"; the nearest are Viam (Jira to `repository_dispatch` to shared workflows) and GitHub's own gateway specification, which goes the other way and demands durable storage.

## How to read this note

Tags on facts, same convention as the other notes:

- **[M] measured**: read by me on 2026-11-21 in a primary artefact (a documentation page, an API description file, a repository, an issue). A user's issue counts as measured on that user's install only.
- **[V] vendor**: stated by the organisation that ships the product, in its own documentation or blog.
- **[S] secondary**: a third party reporting.
- **[I] inference**: my conclusion. Not a source.

Words used:

- **Forge**: the server that hosts git repositories and pull requests (GitHub, GitLab, Forgejo, Gitea).
- **Tracker**: the ticket tool (Jira, Linear). It may be the forge's own issues, or a separate product.
- **Dispatch API**: an HTTP call that starts one CI workflow with named inputs.
- **Concurrency group**: a name given to a workflow run. The forge lets one run per name execute; a newer run either cancels the older one or waits.
- **Webhook**: an HTTP call a product makes to your address when something changes.
- **Relay**: a small program that receives a webhook and makes another HTTP call. **Stateless** means it keeps nothing between two calls: no database, no file.
- **Sweep** (or reconciliation): a job on a timer that compares what should be running with what is, and starts or flags the difference.
- **Daemon**: a program that runs all the time.
- **Automatic token**: the short-lived credential a CI job receives to act on its own repository.

Substrate assumed for the reader [M, from the project's own CI skill and instructions]: repositories on GitHub with self-hosted runners, mirrored or movable to a self-hosted Forgejo with one shared runner on a server with slow disks; the tracker may be outside the forge.

---

## 1. Part A: Forgejo Actions and Gitea Actions as a workflow engine

### 1.1 Versions read

| Product | Version read | Date | Support | Source |
|---|---|---|---|---|
| Forgejo | 17.0 (docs "latest" = 17.0.2) | 2026-10-15 | not long-term; ends 2027-01-28. The long-term line is 15.0 (2026-04-16, ends 2027-07-15) | [V] release post |
| Forgejo API | description file `17.0.0-121` served by Codeberg | read 2026-11-21 | | [M] |
| Gitea | 28.0.0. The "1." prefix was dropped: this is what would have been 1.28 | 2026-09-30 | | [V] release post |
| Gitea API | description file `29.0.0+dev` served by gitea.com | read 2026-11-21 | development version, one ahead of the release | [M] |

Release pace matters for a team that depends on these features: Forgejo ships a version every three months and only one in four is long-term. Concurrency arrived in 14.0, expanded reusable workflows in 15.0, run APIs in 16.0, rerun APIs and job webhooks in 17.0. A team on the 15.0 long-term line has concurrency and dispatch, but **not** the run, cancel, log and rerun endpoints [V].

### 1.2 Forgejo, capability by capability

**Concurrency.** Added in v14.0 (2026-01-15) [V]. The `concurrency` block is documented at workflow level only; `group` may use the `inputs` and `vars` contexts, so a group keyed on a ticket number passed by dispatch works; "Concurrency groups are case insensitive"; `cancel-in-progress` may be an expression [M, reference page]. Two traps:

- If a group is set and `cancel-in-progress` is omitted, it "defaults to true for push and pull_request (synchronize) events" [M]. On GitHub the default is false. A workflow copied from GitHub can start cancelling runs.
- Queueing (`cancel-in-progress: false`) had a bug where a queued run was never picked up when the previous one ended; issue #14576, closed 2026-09-27 [M]. An open issue reports database deadlocks between task update and dispatch under several runners on 16.0.5 with PostgreSQL (#14661, open since 2026-10-02) [M, one install].

**Dispatch.** `workflow_dispatch` with typed inputs (`choice`, `boolean`, `number`, `string`) [M]. API: `POST /repos/{owner}/{repo}/actions/workflows/{workflowfilename}/dispatches`, body `ref` (required), `inputs` (a map of strings), and `return_run_info`. With that flag the answer is 201 with the run `id`, `run_number` and job names; without it, 204 and nothing [M, API description]. Getting the run identifier back is what lets the caller write "run 123 started" on the ticket.

**No `repository_dispatch`.** The event list in the reference is: `push`, `issues`, `issue_comment`, `pull_request`, `pull_request_target`, `release`, `schedule`, `workflow_call`, `workflow_dispatch` [M]. A workflow cannot receive a free-form payload; everything goes through declared string inputs.

**No `workflow_run`.** The request to support it is open since 2025-04-29 (#7722) [M]. One workflow cannot start "when workflow X finished".

**Chaining is explicit.** "Changes made with this token do not trigger workflows, to avoid infinite recursion" [M, basic concepts page]. A job that opens a pull request with the automatic token will not start the pull-request CI. Chaining needs `needs:` inside one workflow, or a dispatch call made with another credential.

**Reusable workflows.** Same repository: yes. Another repository: "The target repository must be a public repository." Another Forgejo or GitHub instance by full URL: also public only [M]. The request for private sources is open (#12343, 2026-04-30, 13 comments) [M]. For a team that wants one shared set of agent workflows across private repositories, this is the largest gap. Work-arounds [I]: a public repository holding only workflow files with no secrets in them; or keep the workflow file thin and put the logic in a CLI that every repository installs.

**Approval gates.** None. The reference lists the keys `jobs.<id>.environment` in a table but documents no behaviour and no approval [M]. The only approval in Forgejo Actions is the trust decision before running a workflow from a fork's pull request ("Approve once", "Approve always") [M, security page]. That is a safety control, not a workflow gate.

**Timeouts.** `timeout-minutes` at job and step level is documented [M]. No default is stated; the runner has its own ceiling in its configuration file (not re-read in this pass).

**Schedules.** Cron syntax, optional time zone (v16), only for workflows on the default branch [M][V].

**Secrets.** Three levels: user, organisation, repository. "Once the secret is added, its value cannot be changed or displayed." No environment level, so no per-job scoping other than which secrets the job's YAML names. Pull requests from forks get none [M].

**Automatic token.** It "has write permission to the repository" and can "push commits or use API endpoints such as creating a label or merging a pull request"; on any other repository it gets a 404 [M]. The `permissions` key is ignored [M, GitHub-compatibility page]. There is no setting to make it read-only: "Cannot prevent forgejo CI from writing to repo" is open with 17 comments (#13183, 2026-06-23) [M]. For more rights, v16 added **Authorized Integrations**, described as "an alternative to implementing `permissions:` declarations" [V]. Two open issues from November 2026 say this design pushes users to grant more than needed (#15287, #15294), and one states users were told the automatic token will become read-only in the future [M for the issues; the plan itself is a user's statement, not read in a Forgejo announcement].

**Writing state on issues and pull requests.** Yes: the automatic token can call the REST API on its own repository (comments, labels, statuses) [M]. For a tracker inside the forge, this is enough to hold workflow state. Forgejo has no GraphQL API (see the fork report below).

**APIs for a sweep.** List runs, get a run, cancel, list jobs, fetch logs (v16); rerun a run or one job, job details (v17) [M, API description][V]. Since v17 a webhook can fire when a job changes status [V], so something outside can learn that a run ended without polling.

**An agent action.** Anthropic's `claude-code-action` does not run on Forgejo. An open request (#1601, 2026-08-05, no reply) lists why: it uses GraphQL, which Forgejo does not have; it checks a user `type` field Forgejo does not return; its permission check fails unless the bot token has every write scope; event names differ (`pull_request_comment`, `label_updated`) [M]. The same user reports running a fork (`codeberg.org/vtmocanu/claude-code-action`, 4 stars, updated 2026-11-08) "in production on Forgejo 15.0.3 since 7 July 2026", in mention mode and in prompt mode with `--json-schema` [M, one user]. A Gitea variant exists (`markwylde/claude-code-gitea-action`, 167 stars, last push 2026-08-07) [M]. [I] On a self-hosted forge, calling `claude -p` from a plain `run:` step is simpler and safer than depending on a four-star fork: the action's value is the GitHub comment plumbing, which is exactly the part that does not port.

**Event quirks to test on your version.** The user above found on Forgejo 15.x that `on: issues: types: [opened]` fires once for an issue created with labels and "not at all for a label added later" [M, one user, one version]. The v17 reference lists `labeled` and `unlabeled` as types [M]. A label-driven state machine must be tested on the exact version before it is trusted.

**Found on the reader's own instance** [M, recorded in the project's CI skill]: once `.forgejo/workflows/` exists Forgejo ignores `.github/workflows/`, and without it Forgejo runs the GitHub workflows, deployments included; `github.server_url` is the runner's internal address; two jobs running at once share the runner's network.

### 1.3 Gitea 28, where it differs from Forgejo

- **Concurrency** since 1.26.0 (2026-04-18), at workflow and job level; flagged as a breaking change. One running plus at most one waiting run per group, as on GitHub; a request for a longer queue is open (#39195) [V][M]. Gitea 28 fixed a case where an unapproved fork run could cancel a trusted run in the same group [V].
- **Token permissions are supported.** `permissions:` works at workflow and job level with scopes `contents`, `issues`, `pull-requests`, `actions`, `packages` and others; an owner or repository sets a maximum that workflows cannot exceed; a "restricted" default mode gives read-only [V]. This is ahead of Forgejo.
- **Reusable workflows from private repositories are supported**, through "collaborative owners" or a cross-repository access setting (read-only, chosen repositories) [V]. Also ahead of Forgejo.
- **Dispatch API**: `POST /repos/{owner}/{repo}/actions/workflows/{workflow_id}/dispatches` with `ref` and `inputs`. The request has no flag to return the run [M, API description; the response body was not checked].
- **Run APIs**: list, get, cancel, force-cancel, rerun, rerun failed jobs, approve, logs, per-attempt jobs [M].
- **Environments**: `jobs.<job_id>.environment` "is ignored" [V]. No approval gate.
- Problem matchers and error annotations "are ignored" [V]. Completed runs are deleted after 400 days by default [V].
- Not stated on the pages read: `timeout-minutes`, and whether token-made events start workflows.

### 1.4 Self-hosted GitLab CE (Free tier), short check

| Need | GitLab CE | Source |
|---|---|---|
| One run at a time per key | `resource_group` on a job, Free tier. Jobs wait; modes `unordered`, `oldest_first`, `newest_first`, `newest_ready_first`. It serialises, it does not cancel. Known race conditions in busy pipelines (issue 436988) | [V] |
| Cancel the older run | "Auto-cancel redundant pipelines" for the same branch, with `interruptible` jobs; Free tier | [V] |
| Start a run from outside with inputs | `POST /api/v4/projects/<id>/trigger/pipeline` with a trigger token, `variables[KEY]` or validated `inputs[name]`; Free tier | [V] |
| Receive a third-party webhook with no relay | A URL form `/projects/<id>/ref/<ref>/trigger/pipeline?token=<token>`; the webhook body lands in a file variable `TRIGGER_PAYLOAD`. The token sits in the URL and nothing verifies a signature | [V] |
| Approval gate | Deployment approvals: "Tier: Premium, Ultimate". Protected environments: "Tier: Premium, Ultimate". On Free the gate is a manual job (`when: manual`) on a protected branch | [V]; the manual-job page was not re-read |
| Job timeout | Project setting, default 60 minutes, from 10 minutes to under one month; the lower of project and runner values wins | [V] |
| Schedules, includes from other projects, CI components | Free tier. Cloudflare's review system is "a fully contained GitLab CI component" (see the threshold note) | not re-read in this pass |
| Agent flows (Duo Agent Platform, Custom Flows) on CE | **not checked** | |

GitLab CE is the only one of the three self-hosted forges with a free in-pipeline pause (the manual job) and a no-relay webhook entry.

### 1.5 Table: substrate × capability

"GH" is GitHub Actions, the reference. "Yes" means documented and read.

| Capability | GH | Forgejo 17 | Gitea 28 | GitLab CE |
|---|---|---|---|---|
| Concurrency group, cancel-in-progress | yes | yes, since 14.0; workflow level; **default differs** | yes, since 1.26; workflow and job | auto-cancel per branch; `resource_group` to serialise |
| Queue instead of cancel | 1 running + 1 waiting | yes; bug fixed 2026-09 | 1 running + 1 waiting | yes, with ordering modes |
| Dispatch API with inputs | yes, 25 inputs max, returns run id (API 2026-03-10) | yes, strings; returns run id on request | yes; run id not confirmed | yes; variables or typed inputs |
| Free-form external event (`repository_dispatch`) | yes | **no** | not seen | yes (`TRIGGER_PAYLOAD`) |
| Start when another workflow ends (`workflow_run`) | yes | **no** (#7722 open) | not checked | yes (downstream pipelines) |
| Reusable workflow from a private repository | yes | **no** (#12343 open) | yes | yes |
| Environment or reviewer approval | yes | **no** | **no** (key ignored) | **paid tiers only** |
| Other manual gate inside a run | no | no | no | manual job |
| Job timeout | yes | yes, job and step | not stated | yes |
| Scheduled runs | yes | yes, default branch only | yes | yes |
| Secrets per environment | yes | no; user, org, repo | no | variable scopes (not re-read) |
| Narrow the automatic token | yes | **no** (#13183); Authorized Integrations instead | yes, with owner maximum | job token scope (not re-read) |
| Token-made events start workflows | no | no | not stated | n/a |
| Write on issues and PRs by API from a job | yes | yes (REST only) | yes | yes |
| Run, cancel, rerun, log APIs | yes | yes (16.0, 17.0) | yes | yes |
| Job-status webhook out | yes | yes (17.0) | not checked | yes |
| Official coding-agent action | yes (Claude, Codex, Gemini) | **no**; one small fork | **no**; community action | vendor flows, tier not checked |

What this means for the threshold table of `gap_small_team_engine_threshold_and_cost.md` [I]:

- **Row 2** (two runs on one ticket): the "smallest fix" holds on all three self-hosted forges. On Forgejo write `cancel-in-progress` explicitly, key the group on the ticket input, and test the queue behaviour on your version.
- **Row 3** (accepted and nothing happened): holds. Job timeouts, scheduled sweeps and API writes all exist. Forgejo 16 or later is needed for the sweep to list and cancel runs through the API; on the 15.0 long-term line the sweep can still read the tracker but can only infer run state from what jobs wrote.
- **Row 6** (wait for a human): the environment-approval pause quoted there (30 days on GitHub) **does not exist on Forgejo or Gitea** and is paid on GitLab. The only portable design is the one the row already calls the smallest fix: the wait is a state on the ticket or pull request, the human's answer is a label, a comment or a transition, and that event starts a new job. This removes one argument for GitHub-specific design and makes the workflow identical on every forge.
- **Row 9** (dependence on one person or one upstream): on Forgejo, any agent action is a small fork. Prefer no action at all.

---

## 2. Part B: from an outside tracker to a CI job

### 2.1 What each tracker can send

| Source | Can it shape its own HTTP call? | Retries | Proof of origin | Duplicate handle | Label |
|---|---|---|---|---|---|
| **Jira Cloud automation rule**, action "Send web request" | **Yes**: URL, headers (values can be hidden), custom body. Only ports 80, 443, 8080, 8443 and a few others. Admins can restrict target domains | **None documented.** A timed-out call is logged as sent with "result unknown"; a fixed 30-second limit is reported in Atlassian's own issue tracker; retries are an open feature request | A secret header you choose | none | [V] for the action; [S] for retry and timeout (community threads and feature requests) |
| **Jira Cloud webhook** | No: fixed payload, optional JQL filter | Up to **five**, 5 to 15 minutes apart, on 408, 409, 425, 429, 5xx and connection failure. "Some webhooks might be delivered more than once." After 30 minutes without success, one attempt per webhook until one succeeds. A "failed webhooks" API lists what was dropped | Optional secret, `X-Hub-Signature` | `X-Atlassian-Webhook-Identifier`, "the same across retries" | [V] |
| **Jira Data Center webhook** | No | **No retry policy documented.** After 5 failures in a row the webhook is skipped with a growing delay (10 s to 2 h); it is never disabled, so failure is silent. Events are dropped when the queue (250 by default) is full, typically on bulk edits | Secret and `X-Hub-Signature` documented from version 11.0 | not found | [S], a webhook vendor's guide citing Atlassian knowledge-base pages; a retry request is open as JRASERVER-70300 |
| **Jira Data Center automation rule** | Yes, same action | not found | Secret header | none | not re-read |
| **Linear webhook** | No: fixed payload per entity type | **Three**: after 1 minute, 1 hour, 6 hours. Failure is any non-200 answer or more than 5 seconds. "the webhook might be disabled by Linear, and must be re-enabled again manually" | `Linear-Signature`, hex HMAC-SHA256 of the raw body; check the timestamp within one minute | `Linear-Delivery`, a UUID per payload. Whether a retry reuses it is not stated | [V] |

Two consequences [I]:

- **Jira needs no relay.** A rule "when the ticket moves to Ready for agent, send a web request" can call the forge's dispatch endpoint directly with a token in a hidden header and a body that carries `ref` and the ticket key as input. This is the shape OpenAI's cookbook recipe uses for Jira to GitHub Actions (Jira Automation, label trigger, `workflow_dispatch`, then the job transitions the ticket and comments the pull-request link; no server, no database, and no word on retries or duplicates; the recipe is now marked archived) [V]. The price: the forge's API must be reachable from Atlassian's addresses on an allowed port, and a failed call is not retried.
- **Linear needs a relay**, or polling. Its webhook cannot be pointed at a dispatch endpoint: the body has no `ref`, the signature must be checked, and the answer must be a 200 within 5 seconds. Pointing it at GitLab's trigger URL may also misfire, because that endpoint does not answer with a plain 200 on success [I, not tested].

### 2.2 What the forge side guarantees

- A dispatch call that returns success means "accepted", not "ran". GitHub's own gateway specification says it in so many words: a success answer "proves only that GitHub accepted the request" [V].
- GitHub's `workflow_dispatch` now returns the run identifier (API version 2026-03-10) and takes at most 25 inputs [M]. Forgejo returns it with `return_run_info` [M].
- Inputs are strings on Forgejo and Gitea [M]. [I] Pass the ticket key only and let the job read the ticket through the tracker's API. This also matches GitHub's gateway design, which forwards only a canonical URL and event types and makes the workflow fetch the rest itself [V].

### 2.3 Is a stateless relay plus a sweep enough?

The design, in plain steps [I]:

1. **Trigger.** Either the Jira rule calls dispatch directly, or a relay receives the webhook, checks the signature and timestamp, drops events that are not "became ready", calls dispatch with the ticket key, and answers 200 only if dispatch was accepted. A failed dispatch returns an error to the tracker, so the tracker's own retries (five for Jira Cloud, three for Linear) are the retry queue. The relay stores nothing.
2. **Claim, inside the job.** First step: read the ticket. If it is not in the ready state, exit green. Otherwise move it to "in progress" and write the run identifier on it. A concurrency group keyed on the ticket key makes two such jobs run one after the other, so the second one sees "in progress" and exits. **The tracker is the deduplication store and the concurrency group is the lock.**
3. **Final state by code.** The last step, run always, writes the outcome on the ticket and the pull request.
4. **Sweep.** A scheduled workflow, every 5 to 15 minutes: list tickets in "ready" older than a few minutes, and tickets "in progress" whose recorded run is finished or missing; dispatch the first kind, flag the second.

Why this is enough for a ticket-to-pull-request flow:

- A lost event (Jira rule call failed, Linear webhook disabled, Data Center queue overflow) leaves a ticket in "ready". The sweep finds it. This is the fix the threshold table gives for row 3, and it is what OpenAI Symphony's reconciliation loop does inside a daemon [M, earlier note].
- A duplicate event (Jira's "delivered more than once", a Linear retry six hours late) hits the claim step and exits.
- A dead run leaves a ticket "in progress" with a finished or missing run. The sweep finds it.
- No ordering is needed, because each event only says "look at this ticket now" and the job reads the current state.

**The sweep alone is also a valid bridge.** With no webhook at all, a scheduled job that polls the tracker gives the same guarantees with a delay equal to its period. It needs no inbound address, so it works for a Jira Data Center behind a firewall and for a forge that is not reachable from the internet. Cost: one short job per period on a self-hosted runner [I].

Where it stops being enough, that is, where a stateful service becomes hard to avoid [I, each tied to a row of the threshold table]:

| Situation | Why the stateless design fails | Row |
|---|---|---|
| One ticket spans several repositories and the steps must be joined | A concurrency group lives in one repository; nothing holds "repo A done, waiting for repo B" except the ticket, and the ticket has no compare-and-set | 8 |
| A cap across all repositories ("two agents at most on this server", "50 dollars a day") | Groups and timeouts are per workflow. A runner capacity setting caps jobs per runner, which covers the first case on one shared runner; a money cap needs a ledger | 4, 10 |
| Reaction in seconds to an event the tracker cannot push and the forge does not emit | Polling by schedule has a floor of about a minute, and scheduled jobs start late under load | 3 |
| A wait inside one computation whose intermediate result is expensive to rebuild | A new job starts cold; only a saved session or a durable engine resumes | 1, 6 |
| The claim must be atomic under real contention | Reading then writing a Jira status is not atomic; the concurrency group hides this only while all contenders are jobs of the same workflow | 2, 8 |
| Events from three or more sources must be ordered | A stateless relay cannot reorder | 8 |

**The counter-example to take seriously.** GitHub's Agentic Workflows publish a "Webhook Gateway Specification" for exactly this bridge (Jira, Linear and Azure DevOps to `repository_dispatch`). It is an "Experimental draft", ships no implementation, and it is **not** stateless: the receiver must keep durable receipts and outcomes, must not "acknowledge durable acceptance and then silently drop events", must quarantine uncertain outcomes instead of retrying them, and "process-local locks do not provide cross-dispatch replay safety" [V]. Until a receiver exists, the same documentation tells users to "use `workflow_dispatch`" [V]. [I] That specification is written for a shared, hostile, multi-tenant gateway with a threat model. A single team with one tracker and a sweep is not in that position, but the specification is a fair list of what the stateless design gives up: proof that every accepted event was acted on, without relying on the tracker's state.

### 2.4 Who documents this shape

| Who | Shape | State kept | What is missing from the account | Label |
|---|---|---|---|---|
| **Viam** (`viamrobotics/claude-ci-workflows`; created 2026-02-10, last push 2026-10-30, 0 stars: an internal repository left public) | Jira ticket arrives as `repository_dispatch` of type `jira-ticket` with ticket id, summary, description, complexity and assignee in the payload; a thin caller workflow per repository calls shared reusable workflows; the agent works on a `claude/*` branch; a second workflow fixes CI failures only if the pull request carries a consent label, the last commit is the agent's, no human has reviewed, and a re-run failed again; an organisation-level API key; a GitHub App token to open the pull request so that CI starts | None outside GitHub and Jira | How Jira sends the dispatch (rule or relay), retries, duplicates, run counts | [M] repository README and workflow file |
| **OpenAI cookbook, "Automate Jira ↔ GitHub with Codex"** | Jira automation rule on a label, `workflow_dispatch`, `codex exec` in the job, ticket transitions and a comment written back | None | Retries, duplicates, error handling; the recipe is marked archived | [V] |
| **Buildkite example** (`buildkite-agentic-examples/linear-issue-handler`, last push 2025-11-25) | Linear webhook pasted straight into a Buildkite pipeline trigger URL; the pipeline checks for a label and adds an agent step | None | Signature check, duplicates. Older than a year: outdated by date | [V] |
| **GitHub gh-aw** | `repository_dispatch` or `workflow_dispatch` from "any external system that can make an HTTP POST"; a gateway for Jira and Linear specified, not shipped | Durable receipts, in the specification | An implementation | [V] |
| **Cyrus, Open-Inspect** | Webhook service with its own session store | Database | See the threshold note for their duplicate and silent-loss issues | [M], earlier note |
| **Anthropic scheduled tasks** (formerly routines) | A saved cloud agent with a `/fire` endpoint: POST with a bearer token and free text starts a session and returns its URL. Research preview, claude.ai accounts only, GitHub repositories | Vendor's | Not a fit for a self-hosted forge | [V] |

A team that documents "stateless relay, then a reconciliation sweep, for a coding-agent flow" in those words: **not found**. Each half is documented separately: the relay or direct call by Viam, OpenAI and Buildkite; the sweep by Symphony's specification.

---

## 3. Part C: the language of the small piece

### 3.1 One fact that changes the comparison

The existing notes describe the Claude Agent SDK as "in-process". The hosting page says otherwise [V]:

- "The Agent SDK spawns and supervises a `claude` CLI subprocess that owns a shell, a working directory, and session files on disk."
- "When your code calls `query()`, the SDK spawns a separate `claude` CLI process and talks to it over stdio."
- "Both the TypeScript and Python SDKs bundle a native Claude Code binary", "pinned to the SDK package version, so updating the SDK is how you update the CLI."
- "One agent session maps to one subprocess." Starting point per agent: 1 GiB of memory, 1 CPU, 5 GiB of disk.
- "The SDK follows semver: take patch releases continuously and review the … changelog before taking a minor." Both SDKs are still at 0.x and release almost daily (TypeScript v0.3.330 and Python v0.2.187 on 2026-11-20) [M].

So the SDK is a typed wrapper around the same process a Rust or Go program would start itself. What it adds is real but narrow: message types kept in step with the binary, hooks and the permission decision as functions in your program instead of shell scripts or a tool server, a `SessionStore` interface to copy transcripts off the machine, and telemetry wiring. OpenAI's SDKs have the same shape: the Python Codex SDK "controls the local Codex app-server over JSON-RPC" with "a pinned Codex CLI runtime"; TypeScript and Python are the only languages listed [V].

Kiro's team reached the same boundary from the other side. It had three agent engines, TypeScript for the editor, **Rust for the command line "for performance"**, Python for the web, and merged them in 2026 into one harness run as a separate process that clients reach over a protocol, because "every new capability had to be built and maintained three times" and "shared libraries don't enforce a strong enough boundary" [V, Kiro blog, 2026-08-03; the language of the merged harness is not stated]. The lesson for a harness: keep the agent on the other side of a process boundary, in whatever language you write.

### 3.2 Table: language × cost

"Free" means the vendor maintains it. "Rebuild" means your team writes and keeps it working.

| | TypeScript | Python | Go | Rust |
|---|---|---|---|---|
| Vendor agent SDK | Claude Agent SDK, Codex SDK [V] | Claude Agent SDK, Codex SDK ("stable release") [V] | **None.** Five community ports of the Claude SDK; the largest has 26 stars [M] | **None** [M, earlier notes] |
| Free with the SDK | Typed events; hooks and permission callback as functions; session resume and `SessionStore`; pinned agent binary; pre-warming of sessions | Same, minus pre-warming | nothing | nothing |
| Rebuild | Nothing for one agent; your own adapter if you want two vendors behind one interface | Same | Event structs for `stream-json`; process supervision (timeouts, process groups, kill); hooks as scripts; the permission path through `--permission-prompts none` or a tool server; version pinning and a contract test | Same as Go |
| Size of the rebuilt part | 0 | 0 | a few hundred lines per agent [I, from the adapter sizes in the Rust note] | same |
| Upgrade exposure | SDK minor versions (0.x, daily releases) | Same | The CLI's flags and event format, with no stability promise found; community wrappers show drift: an Elixir port had to accept events that "omit wrapper uuid or session_id" in 2026 [S] | Same as Go |
| Durable library if needed later | DBOS, Temporal, Restate, Inngest; and the vendors' agent integrations are written for it | Same | Temporal (the oldest SDK), DBOS Go v1.9.0 (2026-11-17, 876 stars), Restate Go v1.2.0 [M] | Temporal 1.2.0 (GA); Restate 0.13; DBOS "pre-production" [M, earlier note] |
| Ships to runners as | Needs Node. Forgejo's default job image is "Debian bookworm … with just node.js" [V], so Node is the one runtime present by default there | Needs Python 3.10+ and, for the SDK, a package install per job or a prepared image. A standard-library-only script needs nothing but the interpreter | **One static binary**, simple cross-compilation | **One static binary** |
| Memory of the piece itself | A Node process, on the order of 100 MB (GitHub's figure for its own former runtime [V, earlier note]) | similar order | a few MB | a few MB; one small team reports 45 MB flat for a whole agent service [V, earlier note] |
| Who on the team can review it | most web teams | most teams | backend teams | fewer people; agents write it, humans must still review |

### 3.3 First-hand reports of unattended services, by language

| Language | Named system | What it is | Report | Label |
|---|---|---|---|---|
| TypeScript | `anthropics/claude-code-action` (10,040 stars) | The vendor's CI wrapper | Hangs, double triggers, no cost output (threshold note) | [M] |
| TypeScript | Cyrus (909 stars), Open-Inspect (3,507 stars) | Tracker daemon; webhook orchestrator | Runaway sessions, memory leak hidden by restarts, 15% silent loss on one install (threshold note) | [M] |
| TypeScript or Python, not stated | Spotify Honk | Agent SDK inside Spotify's own harness, in Kubernetes pods | 1,000 merged pull requests per 10 days (earlier notes) | [V][S] |
| Python | a named team running the Python Agent SDK in an unattended service, with a report | | **not found** | |
| Go | Gas Town (`gastownhall/gastown`, 18,862 stars, created 2025-12-16), claude-squad (8,846 stars) | Supervisors of many agent terminals, driven by a person | Products with users, not a team's account of an unattended service. `coder/agentapi` (Go, an HTTP wrapper over agent CLIs) was archived on 2026-09-13 | [M] |
| Go | a team report | | **not found** | |
| Rust | vibe-kanban (28,772 stars; company closed April 2026), Symphony ports (`anantjain-xyz/symphony-rust` 14 stars, `broomva/symphony` 11 stars, last push 2026-07-13) | A board driven by a person; small daemons | No production account. Search surfaced only personal projects | [M] |
| Rust | GitHub Copilot runtime, Codex CLI, goose, Kiro CLI engine | Agent **runtimes**, not orchestrators that drive another vendor's agent | Reasons given: one binary, low overhead, embedding (earlier note). Kiro has since folded its Rust engine into a shared harness [V] | [V] |
| Rust | Temporal Rust SDK in production, by a named user | | **not found.** Temporal's GA post and customer list name none for Rust; the only use shown is Temporal's own conference-badge demo [V] | |
| Rust | Zed, Warp: an engineering account of building agents in Rust | | **not found.** Zed 1.0 (2026-04-29) runs outside agents over a protocol in their own process; Warp opened its Rust client in April 2026; neither result is a first-party report on the language choice [S] | |
| Elixir | OpenAI Symphony (28,121 stars) | The reference tracker daemon | In-memory state by design; unmerged safety fixes (threshold note) | [M] |

Reading [I]: every failure report found is in TypeScript or Elixir, because that is where the deployed orchestrators are. Not one of those failures is a language failure. They are design failures: no idempotency key, no reaper for child processes, no lease, no sweep. A Rust daemon written without those would fail the same way; a 300-line Python script written with them would not.

### 3.4 Head to head, for a small team

- **If the piece is a CLI called from CI jobs plus, at most, a stateless relay**: the agent step is one `claude -p --output-format json --json-schema …` or `codex exec --json` call. No SDK feature is needed, because a CI job has no long-lived session to pre-warm, no in-process approval dialogue, and writes its result to the pull request. Then the choice is about distribution and review. **Rust or Go** give one binary that a workflow downloads by version, with no runtime on the runner. **Standard-library Python** gives zero build and zero install where Python is on the runner image, and is the cheapest to change. **TypeScript** only wins here if the team already ships Node tooling.
- **If the piece becomes a service that holds sessions open** (live approval inside a run, streaming to a web page, many warm agents): **TypeScript or Python with the vendor SDK** saves the most, because the control channel, the callbacks and the session store are exactly the undocumented parts a Rust or Go program must reverse out of the CLI (the Rust note found vibe-kanban doing this with flags that are not in the documentation).
- **If durability is needed today**: Go and Python have the widest choice of supported libraries. Rust has one supported option, Temporal, which is a server to run or a service to buy; DBOS for Rust is still pre-production, so the "small service with DBOS" suggested in `orchestration_alternatives.md` section 8 is, in Rust, not available yet.
- **Rust's real advantage** is not in driving the agent. It is in the guaranteed part: a state machine whose missing case is a compile error, one binary to hand to every repository, and low, flat memory if the piece must stay up. Its real cost is the smaller pool of reviewers and owning the agent adapters.

---

## 4. Reconciling the two notes

| Note | Its sentence | The question it answers | Still true? |
|---|---|---|---|
| `gap_small_team_engine_threshold_and_cost.md` | "CI and ticket state first, managed engine second, home-made daemon last" | Which runtime should hold the workflow | Yes, and now checked on Forgejo, Gitea and GitLab CE, with one change: the human gate must be a ticket state, since approvals do not exist there |
| `gap_rust_orchestrator_agent_interfaces.md` | "the realistic plan is a new small Rust daemon with a SQLite state table" | If the orchestrator is written in Rust, what can it be built on | The interface advice holds (documented one-shot CLI, own adapter trait, pinned version, contract test). The word "daemon" is the part to drop: nothing in that note showed that the process had to be long-lived |
| `orchestration_alternatives.md` section 8 | CI stops being enough "as soon as the ticket tool is outside the forge" | When a service is needed | Too strong. A tracker outside the forge needs a **bridge**, and the bridge can be a Jira rule, a stateless relay, or a scheduled sweep. A stateful service is needed for the six situations in section 2.3, not for the mere fact of an outside tracker |

The same Rust code serves both readings. The adapter trait, the typed state machine and the gate vocabulary from the Rust note become subcommands of one binary, for example `claim`, `run-step`, `report`, `sweep`, each started by a CI job and each reading and writing the ticket and the pull request. If a condition of section 6 appears later, a `serve` subcommand with a SQLite table can be added around the same code. Going the other way, from daemon to CI jobs, is a rewrite.

---

## 5. Recommended shape on a self-hosted forge [I]

1. **State**: the ticket status plus markers the job writes (run identifier, attempt count, cost) on the ticket and on the pull request.
2. **Trigger**: a Jira rule calling the forge's dispatch endpoint; or, for Linear, a relay of about one file that verifies the signature and calls dispatch; or nothing but the sweep.
3. **Lock**: a concurrency group named after the ticket key, with `cancel-in-progress` written explicitly.
4. **Steps**: short jobs with `timeout-minutes`, each calling the team's CLI, which calls the agent's one-shot command with a turn and dollar cap.
5. **Human gate**: a ticket transition, a label or a comment that starts the next job. No environment approval, so the workflow is the same on GitHub, Forgejo, Gitea and GitLab.
6. **Sweep**: a scheduled workflow on the default branch that re-dispatches stale "ready" tickets and flags "in progress" tickets with no live run.
7. **Sharing across repositories**: on Forgejo, a thin workflow file per repository and all logic in the CLI, since private reusable workflows are not available; on Gitea and GitLab, a shared workflow or component.
8. **Credentials**: an API key for the agent as a repository or organisation secret; a dedicated bot account or an Authorized Integration for anything the automatic token cannot do, including starting the next workflow.

To test on the exact forge version before trusting it: label events after issue creation; queue behaviour of a concurrency group; whether a dispatch made from inside a job, and with which credential, starts a run; behaviour under two runners.

---

## 6. When a long-lived Rust daemon is justified

**Default: a stateless relay (or none) plus CI jobs calling a Rust or Python CLI.**

Move to a long-lived process only when at least one of these is observed, not expected:

1. **A ticket must be coordinated across several repositories** with a join, and the ticket's own states cannot express it.
2. **A global budget or admission rule** is required that a runner capacity setting cannot express: money per day across all runs, fairness between teams, priorities.
3. **Live interaction inside a run**: an approval that must be answered while the agent waits with its context, mid-run steering, streaming to a page.
4. **Warm state between steps is expensive**: large checkouts, built caches or sandboxes that a fresh job would rebuild each time, and self-hosted persistent runners do not already cover it.
5. **Reaction time under about a minute** to events that cannot start a CI job directly.
6. **The measured failure rate of late, expensive runs** makes re-running whole jobs cost more than operating a service (row 1 of the threshold table; at one dollar a run this takes volume a small team may never reach).

And only if these are in place, because the evidence in the threshold note is that small daemons fail silently: an alert on restarts and on "no run started in N hours", a lease or startup lock so two copies cannot both act, child processes killed as a group, a sweep (the daemon needs it as much as CI does), and a second person able to operate it.

If the process is justified, Rust is a reasonable language for it: flat memory, one binary, a typed state machine, SQLite through a mature crate. It is the better choice over TypeScript or Python **unless** condition 3 is the reason, in which case the vendor SDK's control channel is worth more than the binary. If conditions 1 or 6 are the reason, look at a durable library before writing a scheduler by hand: in Rust that means Temporal today.

---

## 7. Not found, or not verified

- A team that documents "stateless relay plus reconciliation sweep" for a coding-agent workflow, with failure counts.
- How Viam's Jira sends the `repository_dispatch` call (automation rule or relay), and any run or failure figure from Viam.
- Whether a Linear retry reuses the same `Linear-Delivery` value. Linear's page does not say.
- An Atlassian page stating the retry and timeout behaviour of the "Send web request" action. The 30-second limit and the absence of retries come from community threads and Atlassian's public issue tracker, not from the action's documentation.
- Jira Data Center webhook retry and signing, at the source. Read only through a third-party guide that cites Atlassian's knowledge base.
- A measured rate of missed webhooks for Jira or Linear.
- On Forgejo: whether a dispatch API call made with the automatic token starts a run (the documentation says changes made with the token do not trigger workflows; the dispatch case was not tested); the token scope a personal token needs to dispatch; job-level `concurrency` (the key appears in a table with no description); the runner's default job timeout and capacity setting (in the runner's example configuration file, not re-read); an official statement that the automatic token will become read-only.
- On Gitea 28: the response body of the dispatch endpoint; `timeout-minutes` support (not on the comparison page, in either direction); whether token-made events start workflows; the `workflow_run` event.
- On GitLab CE: the manual-job, schedule, include and variable-scope pages were not re-read; whether Duo Agent Platform flows are usable on the Free self-managed tier was not checked.
- Named production users of the Temporal Rust SDK. First-party engineering accounts from Zed or Warp on building agents in Rust. The language of Kiro's merged harness.
- A team's account of running the Python Claude Agent SDK, or any Go program, as an unattended coding-agent service.
- A stability promise for `claude -p` flags or the `stream-json` event format (also open in the Rust note).
- The last 58,000 characters of the gh-aw gateway specification were not read.
- No part of this note was tested on a running Forgejo, Gitea or GitLab instance. Everything about them is from documentation, API description files, release posts and issue trackers.

---

## Sources

Read on 2026-11-21.

Forgejo
- https://forgejo.org/docs/latest/user/actions/reference/ (v17.0: concurrency, events, dispatch, reusable workflows, schedule, timeouts)
- https://forgejo.org/docs/latest/user/actions/basic-concepts/ (secrets levels, automatic token)
- https://forgejo.org/docs/latest/user/actions/security/
- https://forgejo.org/docs/latest/user/actions/security-pull-request/ (fork approval and trust)
- https://forgejo.org/docs/latest/user/actions/github-actions/ (known differences)
- https://forgejo.org/docs/latest/admin/actions/configuration/
- https://forgejo.org/2026-01-release-v14-0/ (concurrency)
- https://forgejo.org/2026-04-release-v15-0/ (long-term release, expanded reusable workflows; via search summary)
- https://forgejo.org/2026-07-release-v16-0/ (Authorized Integrations, run and log APIs)
- https://forgejo.org/2026-10-release-v17-0/ (rerun APIs, job webhooks, release schedule)
- https://codeberg.org/swagger.v1.json (Forgejo API description, 17.0.0-121)
- https://codeberg.org/forgejo/forgejo/issues/7722 (`workflow_run`, open)
- https://codeberg.org/forgejo/forgejo/issues/12343 (private reusable workflows, open)
- https://codeberg.org/forgejo/forgejo/issues/13183 (cannot make the token read-only, open)
- https://codeberg.org/forgejo/forgejo/issues/14576 (queued run never picked up, closed)
- https://codeberg.org/forgejo/forgejo/issues/14661 (deadlock under concurrent runners, open)
- https://codeberg.org/forgejo/forgejo/issues/15287 and https://codeberg.org/forgejo/forgejo/issues/15294 (Authorized Integrations)
- https://github.com/anthropics/claude-code-action/issues/1601 (Forgejo and Gitea support request, 2026-08-05)
- https://codeberg.org/vtmocanu/claude-code-action (fork; 4 stars, updated 2026-11-08)
- https://github.com/markwylde/claude-code-gitea-action (167 stars, pushed 2026-08-07)

Gitea
- https://blog.gitea.com/release-of-28.0.0/ (2026-09-30)
- https://blog.gitea.com/release-of-1.26.0/ (2026-04-18; concurrency; via search summary)
- https://docs.gitea.com/usage/actions/comparison
- https://docs.gitea.com/usage/actions/faq
- https://docs.gitea.com/usage/actions/token-permissions
- https://gitea.com/swagger.v1.json (API description, 29.0.0+dev)
- https://github.com/go-gitea/gitea/issues/39195 (longer concurrency queue, open)

GitLab
- https://docs.gitlab.com/ci/resource_groups/
- https://docs.gitlab.com/ci/triggers/
- https://docs.gitlab.com/ci/pipelines/settings/
- https://docs.gitlab.com/ci/environments/deployment_approvals/
- https://docs.gitlab.com/ci/environments/protected_environments/

GitHub
- https://docs.github.com/en/rest/actions/workflows (dispatch response, API version 2026-03-10)
- https://github.github.com/gh-aw/reference/triggers/
- https://github.github.com/gh-aw/specs/webhook-gateway-specification/ (first 100,000 characters)

Trackers
- https://developer.atlassian.com/cloud/jira/platform/webhooks/ (retry policy, identifier, signature, failed-webhooks API)
- https://support.atlassian.com/cloud-automation/docs/jira-automation-actions/ (Send web request: formats, hidden values, ports)
- https://jira.atlassian.com/browse/AUTO-2180 and https://jira.atlassian.com/browse/JIRAAUTOSERVER-66 (timeout and retry requests; via search summary)
- https://jira.atlassian.com/browse/JRASERVER-70300 (Data Center webhook retry request; via search summary)
- https://hookdeck.com/webhooks/jira/guide-duplicates-ordering-retries-timeouts (secondary; Data Center behaviour)
- https://linear.app/developers/webhooks (retries, timeout, signature, headers)
- https://hookdeck.com/webhooks/linear/guide-duplicates-ordering-retries-timeouts (secondary)

Teams and examples
- https://github.com/viamrobotics/claude-ci-workflows (README and `claude-jira.yml`)
- https://developers.openai.com/cookbook/examples/codex/jira-github (archived recipe)
- https://github.com/buildkite-agentic-examples/linear-issue-handler (pushed 2025-11-25)
- https://code.claude.com/docs/en/routines (scheduled tasks, `/fire` endpoint, research preview)

Language and SDKs
- https://code.claude.com/docs/en/agent-sdk/overview
- https://code.claude.com/docs/en/agent-sdk/hosting (subprocess model, bundled binary, resources)
- https://github.com/anthropics/claude-agent-sdk-typescript (v0.3.330, 2026-11-20) and https://github.com/anthropics/claude-agent-sdk-python (v0.2.187, 2026-11-20)
- https://learn.chatgpt.com/docs/codex-sdk (TypeScript and Python Codex SDKs)
- https://github.com/schlunsen/claude-agent-sdk-go (26 stars) and https://github.com/Roasbeef/claude-agent-sdk-go (22 stars)
- https://hexdocs.pm/claude_agent_sdk/changelog.md (community Elixir port; event drift; via search summary)
- https://kiro.dev/blog/one-agent (2026-08-03)
- https://builder.aws.com/content/3Ke2T34sBCscTltJ9Ifn3FAcvma/kiro-then-and-now-three-separately-built-engines-converging-into-one (2026-10-13)
- https://temporal.io/blog/build-durable-applications-rust-temporal-rust-sdk-now-generally-available (2026-09-23) and https://github.com/temporalio/sdk-rust (v1.2.0, 2026-11-09)
- https://github.com/dbos-inc/dbos-transact-golang (v1.9.0, 2026-11-17, 876 stars)
- https://github.com/restatedev/sdk-go (v1.2.0, 2026-10-28)
- https://github.com/gastownhall/gastown (18,862 stars), https://github.com/smtg-ai/claude-squad (8,846 stars), https://github.com/coder/agentapi (archived, last push 2026-09-13)
- https://github.com/broomva/symphony (11 stars, pushed 2026-07-13)
