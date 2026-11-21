# How a Rust orchestrator drives the vendor coding agents, and what to fork

Research note filling a gap in this study. Data collected on 2026-11-21.

## Summary in five lines

1. Every vendor agent can be driven as a child process over a line-per-message JSON stream, and each has two levels: a simple one-shot command (`claude -p`, `codex exec`, `goose run`) and a richer two-way protocol (Claude's `stream-json` input, Codex's App Server, ACP). The simple level is documented and enough for a ticket workflow; the rich level is where things break on upgrade.
2. The safest thing to build a Rust harness on is the **documented one-shot CLI of each agent, behind your own small adapter trait**, with the agent version pinned. Claude Code's documented surface now covers the hard cases: JSON result, schema-validated output, resume by session ID, a `defer` decision that pauses a run for a human, and a flag that denies instead of prompting. ACP is the only neutral protocol, but its Rust crate had four major versions in five months and v2 of the protocol is in Preview since 20 November 2026.
3. Codex's App Server is documented for third parties and has a stable/experimental split, but it has no version number you can negotiate: the schema is generated per binary. Its Rust protocol crates are not on crates.io; you can depend on them by git tag (vibe-kanban does), at the price of pulling OpenAI's dependency tree and a release every five days.
4. Billing: the "June 2026 change" for subscription use of the Claude Agent SDK was **announced, then paused on 15 June 2026**. As of today `claude -p` on a subscription still draws from the plan's limits, but Anthropic's terms say plan limits "assume ordinary, individual usage" and that products should use API keys. Both vendors say: for unattended automation, use an API key.
5. Prior art in Rust: **BloopAI/vibe-kanban** (28,772 stars, Rust, Apache-2.0) is the largest code base that drives ten agents from Rust, but its company shut down in April 2026 and it is a human-driven board, not a ticket daemon. The closest thing to "a Rust feature/bug ticket workflow" is the **OpenAI Symphony spec** plus one of its small Rust ports (the most active, `anantjain-xyz/symphony-rust`, has 14 stars and two contributors). None of the projects inspected supports Forgejo or Gitea out of the box. Verdict: borrow the spec and the adapter code, do not adopt a product.

## How to read this note

Tags, same convention as the other notes:

- **[measured]**: read by me on 2026-11-21 from the GitHub API, the crates.io API, a file in a repository, or the text of a documentation page.
- **[vendor]**: stated by the organisation that ships the product. True as a statement, not independently checked. A sentence quoted from vendor documentation is tagged [vendor] even though I read it myself; a number I counted is [measured].
- **[secondary]**: reported by a third party.
- **[inference]**: my conclusion from the facts above it.

Terms:

- **Headless** (or non-interactive): the agent runs without its terminal interface, takes a prompt, works, prints a result and exits.
- **JSONL / NDJSON**: one JSON object per line. A parent process reads the agent's standard output line by line.
- **JSON-RPC**: a small convention for requests, responses and notifications in JSON. It allows both sides to send requests, which is what an approval prompt needs.
- **ACP** (Agent Client Protocol): an open JSON-RPC protocol between a client (originally an editor) and a coding agent, started by Zed. Not to be confused with IBM's Agent Communication Protocol.
- **Adapter**: a small program that translates one agent's native protocol into ACP.
- **Forge**: the server that hosts git repositories and merge requests (GitHub, GitLab, Forgejo, Gitea).
- **Worktree**: a second checkout of the same git repository in another directory, so that several agents can edit in parallel without stepping on each other.
- **microVM**: a very small virtual machine started in well under a second, giving stronger isolation than a container. Firecracker is the best-known engine.

**Limit of this research.** The session's shared web-search budget was already used up when this note started: no web search was run. Everything below comes from pages fetched directly (vendor documentation, repositories, pricing pages), the GitHub API and the crates.io API. GitHub repository search was used to look for Rust ports. Discovery is therefore weaker than verification: I may have missed projects that a web search would have surfaced. The gaps are listed in "Not found".

---

## 1. The headless interface of each agent

### 1.1 Claude Code: `claude -p`

Version at the time of reading: v2.1.330, released 2026-11-20 [measured, GitHub releases]. Source of this section, unless stated: the page "Run Claude Code programmatically", the CLI reference and the hooks reference on code.claude.com [vendor].

**The documented surface.**

| Need | How | Notes |
|---|---|---|
| Run once, get text | `claude -p "prompt"` | Exit code 0 on success, non-zero on failure. A failure inside the run (for example missing authentication) is printed as the result on standard output. |
| Machine-readable result | `--output-format json` | One JSON object with `result`, `session_id`, usage, and `total_cost_usd`. The cost is a "client-side estimate" and "can differ from your actual bill". |
| Result matching a schema | `--json-schema '<JSON Schema>'` | Result arrives in `structured_output`. The field is absent if the run ended without valid output: check before use. |
| Event stream | `--output-format stream-json --verbose` | One event per line. First event `system/init` (model, tools, MCP servers, plugins, a `capabilities` list). Last event `result`. Retries appear as `system/api_retry` with an `error` category such as `rate_limit` or `billing_error`. |
| Send several messages into a live process | `--input-format stream-json` (with `--replay-user-messages` to get acknowledgements) | The flags are in the CLI reference. The message format on standard input is documented through the Agent SDK types, not as a standalone wire specification [measured: absent from the headless page and the CLI reference]. |
| Continue a run | `--resume <session-id>`, `--continue`, `--fork-session`, `--session-id <uuid>` | Resume accepts an ID or the path of a `.jsonl` transcript. The session file is on local disk. |
| Cap a run | `--max-turns N`, `--max-budget-usd X` | Budget is checked against the client-side estimate. |
| Permissions | `--permission-mode` with `default`/`manual`, `acceptEdits`, `plan`, `auto`, `dontAsk`, `bypassPermissions`; `--allowedTools`, `--disallowedTools` | In `dontAsk`, anything that would prompt is denied. |
| Nobody is there to answer | `--permission-prompts none` | Denies instead of waiting, and tells the model not to retry. Requires v2.1.259 or later. Denials are listed in `permission_denials` in the final result. |
| An external approver | `--permission-prompt-tool mcp__<server>__<tool>` | An MCP tool you provide decides each permission request. |
| Clean, reproducible start | `--bare` | Skips hooks, skills, plugins, MCP servers, memory and `CLAUDE.md` discovery. Does not read subscription credentials: needs `ANTHROPIC_API_KEY` or an `apiKeyHelper`. |
| Stop a run | SIGINT ends the turn cleanly; SIGTERM exits with code 143 and leaves the turn unfinished | |

**The pause-for-a-human path (`defer`).** A `PreToolUse` hook (your script, run before each tool call) can return `permissionDecision: "defer"`. The tool does not run, the process exits, and the JSON result carries `stop_reason: "tool_deferred"` and a `deferred_tool_use` object with the tool's `id`, `name` and `input`. Your orchestrator stores that, asks a human by its own means, then runs `claude -p --resume <id>`; the hook fires again and returns `allow` or `deny` [vendor, hooks reference]. Limits stated in the same page: it works only with `-p`; it is ignored (with a warning) if the model made several tool calls in the same turn; on resume the permission mode is not restored, so pass it again; if the deferred tool is no longer available the result is `tool_deferred_unavailable` and the run exits with code 1. This is the one documented way to hold an approval for hours without keeping a process alive, and it fits a Rust daemon well [inference].

**What is not documented.** Reading the Rust source of vibe-kanban shows what a real orchestrator ends up using: `-p --verbose --output-format=stream-json --input-format=stream-json --include-partial-messages --replay-user-messages`, plus `--permission-prompt-tool=stdio` and `--resume-session-at` [measured, `crates/executors/src/executors/claude.rs`]. The value `stdio` for the permission tool and the flag `--resume-session-at` do not appear in the CLI reference [measured: zero matches]. They are the internal control channel that the official Python and TypeScript SDKs use. Building on them means building on something Anthropic can change without notice [inference].

**Stability signals.**

- Release pace: 100 releases between 2026-07-17 and 2026-11-20, close to one per working day [measured].
- No semantic-versioning promise for the CLI stream was found. The documentation does tell clients to "feature-detect" through the `capabilities` array "instead of comparing version strings" and to ignore unknown values [vendor]. That is a forward-compatibility convention, not a guarantee.
- Documented behaviour changes that would have broken a pinned script in 2026: from v2.1.302 a `-p` run with no mode set starts in Manual mode (calls needing approval are denied); `--enable-auto-mode` was removed in v2.1.111; `--bare` "will become the default for `-p` in a future release", which will stop loading hooks, skills and `CLAUDE.md` unless you ask for them [vendor]. The last one matters most for a harness built on skills and hooks.
- A security note for orchestrators: without `--bare`, a `-p` run executes the hooks and MCP servers configured in the repository it runs in, "even in a folder you've never trusted", with no trust prompt [vendor]. An agent working on an untrusted branch can therefore run code from that branch's `.claude/` folder at start-up.

### 1.2 OpenAI Codex: `codex exec` and the App Server

Version at the time of reading: `rust-v0.171.0`, 2026-11-20; 14 stable releases since 2026-10-08, about one every five days [measured]. Repository: 136,052 stars, Rust, Apache-2.0 [measured]. The repository "doesn't accept external code contributions or pull requests" [vendor, Open Source page].

**`codex exec`** [vendor, "Non-interactive mode"]:

- Progress goes to standard error, the final message to standard output. `--json` turns standard output into a JSONL stream with events `thread.started`, `turn.started`, `turn.completed`, `turn.failed`, `item.*`, `error`.
- `--output-schema <file>` forces the final answer to match a JSON Schema; `-o <path>` writes the last message to a file.
- `codex exec resume <SESSION_ID>` or `resume --last` continues a run. `--ephemeral` does not persist the session.
- Sandbox is built in and is **read-only by default**: `--sandbox workspace-write` allows edits, `danger-full-access` removes the limits.
- It refuses to run outside a git repository unless `--skip-git-repo-check` is passed. Project configuration and project MCP servers load only for trusted projects (`--trust`).
- No interactive approval in this mode: you choose the sandbox up front, or route approvals to an automatic reviewer with `--approve-for-me`.
- Breaking change already visible in the page: "`--full-auto` is no longer supported".

**The App Server** is the two-way protocol behind the Codex editor extension and desktop app: JSON-RPC over standard input and output (`codex app-server`, default transport `stdio://`), with threads, turns, streamed items, approval requests sent from server to client, `thread/resume`, `thread/fork`, `turn/interrupt` [vendor, App Server page].

- **Is it documented for third parties?** Yes. The page is titled "Embed Codex into your product with the app-server protocol" and gives client examples in several languages. But it also says: "If you are automating jobs or running Codex in CI, use the Codex SDK instead" [vendor]. The SDK is TypeScript (`@openai/codex-sdk`) and Python [measured, `sdk/` directory]. There is no Rust SDK.
- **Is it versioned?** Not with a protocol version. Clients send their own name and version in `initialize`; the server's schema is obtained with `codex app-server generate-ts` or `generate-json-schema`, and "each output is specific to the Codex version you ran" [vendor]. So the contract is "the schema of the binary you pinned".
- **Stable versus experimental.** Methods and fields are split. Without `capabilities.experimentalApi: true` the server rejects experimental ones with "`<descriptor> requires experimentalApi capability`" [vendor]. The stable surface still moves: full-history `thread/resume` and `thread/fork` "are deprecated and emit `deprecationNotice`" [vendor]. The WebSocket transport is "experimental and unsupported" [vendor].
- **Removed interface.** "The `codex mcp-server` command and standalone `codex-mcp-server` binary have been removed. Use the Codex app server for existing integrations" [vendor, SDK page]. Anyone who integrated Codex as an MCP server had to migrate.

**Can the Rust crates be used as a dependency?**

- The workspace declares `version = "0.0.0"` and `license = "Apache-2.0"`; crates such as `codex-core`, `codex-protocol`, `codex-app-server-protocol`, `codex-app-server-client` are path members of that workspace [measured, `codex-rs/Cargo.toml`].
- `codex-core` and `codex-app-server-client` are not on crates.io. The crates named `codex-protocol` and `codex-app-server-protocol` that are on crates.io (0.63.0, December 2025) point to `github.com/namastexlabs/codex`, a third party, not OpenAI [measured, crates.io API]. Do not use them.
- A git dependency works in practice: vibe-kanban depends on `codex-protocol` and `codex-app-server-protocol` with `git = "https://github.com/openai/codex.git", tag = "rust-v0.132.0"` [measured, its `crates/executors/Cargo.toml`]. Two lessons from that file: the pin is from 2026-05-20 and upstream is now at 0.171, 39 minor versions later [measured]; and a comment in the same file notes that the crate pulls in `reqwest` and `native-tls` transitively. You get the types, and with them OpenAI's dependency tree and build time [inference].
- A lighter route: generate the JSON Schema from the pinned binary and generate Rust types from it, or hand-write the dozen messages a ticket workflow needs [inference].

### 1.3 goose

Repository `aaif-goose/goose` (formerly `block/goose`): 56,851 stars, Rust, Apache-2.0, release v1.60.2 on 2026-11-20 [measured].

- **Headless**: `goose run -t "<instructions>"`, with `--no-session`, `--resume`, `--max-turns` (default 1000), and the environment variable `GOOSE_MODE=auto` for runs without prompts [vendor, headless tutorial and CLI reference].
- **Recipes**: `goose run --recipe <file> --params KEY=VALUE --sub-recipe <file>` [vendor]. A recipe is a parameterised task file; sub-recipes give a simple form of composition.
- **As a protocol server**: `goose acp` speaks ACP over standard input and output; `goose serve` exposes ACP over HTTP and WebSocket. The documentation says this "is also how goose Desktop talks to its backend" [vendor]. So ACP is goose's first-class driver interface, not an add-on.
- **As a Rust library**: the core is the crate `goose` in the workspace, and the project now documents "oi-kit" (Open Intelligence Kit), "the set of reusable agent-runtime components used to build goose": model integrations, a state machine, tools, context management [vendor]. The workspace has crates named `oi-kit-agent`, `oi-kit-providers` and others [measured]. **Warning**: the crate called `goose` on crates.io is Tag1's load-testing tool, not this project [measured]. Use a git dependency.
- goose is model-agnostic: you bring an API key for a provider. It has no subscription of its own.

### 1.4 GitHub Copilot SDK for Rust

- Crate `github-copilot-sdk` 1.0.35 (2026-11-19) on crates.io; the repository (now under `microsoft/copilot-sdk`, 10,700 stars, MIT) shows release v2.0.1 on 2026-11-18 [measured]. The README says the SDK "is generally available and follows semantic versioning" [vendor]. The gap between the crate number and the release tag was not resolved.
- **What it gives**: the Copilot agent runtime itself. "SDK v2 hosts the native Rust runtime in-process by default", talking JSON-RPC through a C interface; it can also spawn the runtime as a child process or connect to an external one. The README warns that "in-process hosting provides neither crash isolation nor a sandbox" [vendor]. It is the only vendor agent loop you can link into a Rust binary.
- **Billing**: "a GitHub Copilot subscription is required … unless you are using BYOK"; billing "is based on the same model as the Copilot CLI, with each prompt being counted towards your usage allowance". BYOK (bring your own key) lets you point it at OpenAI, Anthropic or Microsoft Foundry keys with no GitHub login [vendor].
- **Practical notes** from the README: Rust 1.94 or later; on Linux the default build needs OpenSSL 3 development files; static musl builds cannot load the runtime and must use the child-process mode [vendor].

### 1.5 ACP as a neutral driver interface

- **Who speaks it.** The official list has about fifty agents [measured, agents page]. Natively: goose, Gemini CLI, Cursor, OpenCode, OpenHands, Kiro CLI, Junie, Cline, Mistral Vibe, Qwen Code, GitHub Copilot ("in public preview", announced 2026-01-28). **Through an adapter**: Claude ("via Zed's SDK adapter", `claude-agent-acp`, TypeScript, 2,800 stars, v0.109.1) and Codex CLI ("via ACP's adapter", `codex-acp`, TypeScript, 590 stars, v2.9.0) [measured]. So the two agents most teams want are reached through a Node.js adapter maintained by the ACP project, not by Anthropic or OpenAI.
- **Protocol maturity.** v1 is the stable line. "ACP v2 is available in Preview", published 20 November 2026, four months after the first Draft and "17 alpha releases of the v2 schema"; the post says "the design is settled enough to build on" [vendor]. v2 changes the prompt lifecycle (a prompt no longer owns the turn) and adds background work and subagents; a migration guide lists breaking changes [vendor].
- **Rust crate maturity.** `agent-client-protocol`: 6.5 million downloads, 5.5.1 released today [measured]. Version history: 71 releases in the 0.x line until June 2026, then 1.0.0 on 2026-06-24, 2.0.0 on 2026-07-23, 3.0.0 on 2026-10-06, 5.0.0 on 2026-11-02 [measured, crates.io]. Four major versions in five months. Evidence of the cost: goose pins `agent-client-protocol` 2.2.0 and the schema crate with an exact `=1.9.1`; vibe-kanban carries two versions at once (`0.8` with the `unstable` feature, and `=3.4.0`) [measured, their `Cargo.toml`].
- **What it buys an orchestrator**: one client implementation for many agents, with permission requests and tool-call events in a common shape. **What it costs**: an extra process and a Node.js runtime for Claude and Codex, and features that lag the native interfaces (for example Claude's `defer`, schema-validated output and budget cap have no ACP equivalent that I found) [inference].

### 1.6 Table: interface × stability × what breaks on upgrade

| Interface | Documented for outside use | Stability statement | What breaks on upgrade (seen or announced) | Verdict for a Rust harness |
|---|---|---|---|---|
| `claude -p` + `--output-format json` / `--json-schema` | Yes | None formal; daily releases | Default permission mode changed (v2.1.302); `--bare` to become default; flags removed (`--enable-auto-mode`) | **Build on it.** Pin the version, always pass the permission mode and `--bare` or not explicitly, parse only the fields you need. |
| `claude -p` + `stream-json` output | Yes (event types, `capabilities` list) | "Feature-detect, ignore unknown values" | New event types; minimum versions per feature | Build on it for progress and cost; tolerate unknown events. |
| `claude` + `stream-json` input and `--permission-prompt-tool=stdio` | Flags yes; wire format and `stdio` value no | None | Internal SDK control channel; can change silently | Avoid. Use `defer` or an MCP permission tool instead. |
| PreToolUse `defer` + `--resume` | Yes | None formal | Requires v2.1.246+ for plan mode; ignored on parallel tool calls | Build on it for human approval; handle the "ignored" case. |
| `codex exec --json` / `--output-schema` | Yes | None formal; release every ~5 days | `--full-auto` removed; trust rules for project config | **Build on it.** Same discipline: pin, pass sandbox explicitly. |
| Codex App Server (stable surface, stdio) | Yes, "embed in your product"; not recommended for CI | Stable/experimental split; schema per binary; no protocol version | Deprecations on `thread/resume`/`thread/fork` history; `codex mcp-server` removed | Use only if you need live approvals or steering. Regenerate the schema at each bump. |
| Codex App Server (experimental surface, WebSocket) | Yes, flagged | "Experimental and unsupported" | Anything | Avoid. |
| `codex-rs` crates by git tag | Possible, not offered | Workspace version 0.0.0; no API promise | Any refactor; heavy transitive dependencies | Avoid as a library; acceptable for protocol types only. |
| `goose run` / recipes | Yes | Project at 1.x | Not inspected in detail | Fine as a second agent. |
| `goose acp` / `goose serve` | Yes, first-class | Tied to ACP versions (pinned 2.2.0) | ACP major bumps | Fine if you go the ACP route. |
| ACP v1 through `agent-client-protocol` | Yes | Protocol v1 stable; crate at 5.x after four majors in five months | Crate API on each major; v2 migration ahead | Viable as an optional second driver. Not as the only one today. |
| `github-copilot-sdk` (Rust) | Yes | "Generally available", semantic versioning | v1 to v2 moved to in-process hosting | The most stable contract on paper; ties you to the Copilot runtime. |

---

## 2. Authentication, terms and billing for unattended use

### 2.1 Claude

**Credentials a child process can use** [vendor, Authentication page]:

- `ANTHROPIC_API_KEY`: a Console key, billed per token. In `-p` mode "the key is always used when present".
- `apiKeyHelper`: a script that returns a key, for rotation.
- `CLAUDE_CODE_OAUTH_TOKEN`: a one-year token created by `claude setup-token`, "for CI pipelines and scripts where browser login isn't available". It authenticates as your subscription. `--bare` does not read it.
- Cloud providers (Bedrock, Google Cloud, Microsoft Foundry) with their own credentials.

**The "June 2026 billing change", resolved.** The support article "Use the Claude Agent SDK with your Claude plan" now contains only two dated updates [vendor, read 2026-11-21]:

- "Update June 15, 2026: We've paused the previously-announced changes to Claude Agent SDK usage. For now, nothing has changed: Claude Agent SDK, `claude -p`, and third-party app usage still draw from your subscription limits."
- "Update October 7, 2026: Claude Max, Ultra, and Team plans now include monthly API credits. They cover the Claude API, Claude Managed Agents, and the Claude Agent SDK and `claude -p` when you run them with an API key from your linked Claude Console organization. Nothing changes for your plan: when you're signed in with your Claude plan, the Claude Agent SDK and `claude -p` still draw from your subscription limits."

So: a change to how subscription plans cover programmatic use was announced in spring 2026 and paused on the day it was due. The article no longer describes what the change was; the original announcement was **not found**. The amounts of the monthly API credits were not read.

**What the terms say** [vendor, "Legal and compliance"]:

- "Advertised usage limits for Pro, Max, and Ultra plans assume ordinary, individual usage of Claude Code and the Agent SDK."
- OAuth (subscription) login "is intended exclusively for purchasers of Claude … subscription plans and is designed to support ordinary use of Claude Code and other native Anthropic applications."
- "Developers building products or services that interact with Claude's capabilities, including those using the Agent SDK, should use API key authentication." Anthropic "does not permit third-party developers to offer Claude.ai login into their own applications, or to route requests through Free, Pro, Max, or Ultra plan credentials on behalf of their users."
- Not restricted: provisioning your own API keys in CI or a secrets manager for your own users; and an end user signing in "to the unmodified Claude Code binary with their own Claude subscription".

**Reading for a small team** [inference]: an internal daemon that runs the unmodified `claude` binary with one developer's own token is technically supported (the token exists for scripts) and currently billed to the plan. A shared team bot running tickets around the clock on one person's subscription is hard to call "ordinary, individual usage", and the paused change shows Anthropic intends to separate this traffic. Design for an API key from the start; treat subscription use as a convenience for local trials. Note that `open-inspect/background-agents` advertises "a connected Claude subscription" as a model option [measured, README]: an open-source project doing it is not evidence that it is within the terms.

### 2.2 Codex

[vendor, Authentication, CI/CD auth and Pricing pages]

- "Use API key authentication for programmatic Codex CLI workflows, such as CI/CD." With an API key, "Codex uses standard API pricing instead of included ChatGPT plan credits." The pricing page lists an "API Key" option described as "great for automation in shared environments like CI".
- `CODEX_API_KEY` can be set for a single `codex exec` invocation. The docs warn not to export it at job level where repository-controlled code (build scripts, tests) can read it.
- Running automation on a ChatGPT plan is documented as an advanced path: create `~/.codex/auth.json` on a trusted machine, copy it to the runner, let Codex refresh it (about every 8 days), and persist the refreshed file. Conditions stated: trusted private infrastructure, one machine or one serialised job stream per file, never for public repositories. "The right way to authenticate automation is with an API key."
- A third option, "Codex access tokens for enterprise automation", exists for "trusted scripts, schedulers, and private CI runners".
- An equivalent of Anthropic's announced-then-paused billing change for Codex: **not found**. The current state is as above: plan credits and five-hour limits for ChatGPT login, API rates for keys.

### 2.3 Others

- Copilot SDK: Copilot subscription, per-prompt allowance, or BYOK [vendor]. See 1.4.
- goose, OpenCode, OpenHands: no subscription of their own; you pay the model provider [vendor].

---

## 3. Existing open-source orchestrators

Stars and dates measured on 2026-11-21 from the GitHub API.

### 3.1 Comparison

| Project | Language, licence | Stars; last release | What it is | State, retries, approval | Agents driven | Forge and tracker |
|---|---|---|---|---|---|---|
| **openai/symphony** | Elixir reference + `SPEC.md` (2,312 lines), Apache-2.0 | 28,121; v0.0.3 on 2026-09-15; last push same day | Polling daemon: ticket in, PR out. "Engineering preview". | No database by design: state rebuilt from the tracker and workspaces. Exponential backoff, turn limit, stall timeout. Approval = a human moves the ticket (see ticket_to_prod_orchestration.md). | Codex only: the spec says the launched process "MUST speak a compatible app-server protocol over stdio", default command `codex app-server` [measured, SPEC.md]. | Tracker is a pluggable adapter (`tracker.kind`); the reference ships Linear. The forge is whatever the agent's skills call. |
| **BloopAI/vibe-kanban** | Rust (+ TypeScript UI), Apache-2.0 | 28,772; v0.1.46 on 2026-11-15 | Local board where a human creates tasks, launches agents in worktrees, reviews diffs, opens PRs. | SQLite. A human drives each step; no ticket polling, no automatic retries found. | Claude Code, Codex, Gemini CLI, Copilot, Amp, Cursor, OpenCode, Droid, Qwen, plus a generic ACP executor [measured, `crates/executors`]. | `crates/git-host` contains GitHub and Azure only [measured]. GitLab self-hosted request open since 2025-12-31 (#1697); Forgejo/Gitea PR #3428 closed unmerged on 2026-06-05 [measured]. |
| **Shopify/roast** | Ruby, MIT | 1,258; v1.4.1 on 2026-11-10 | A Ruby DSL for workflows made of "cogs": `chat` (model call), `agent` (local coding agent), `cmd` (shell), `map`, `repeat`, `call`. | In-process, one run; control flow and iteration in Ruby. Persistence, resume and approval were not found in the README. | "Pi CLI, Claude Code CLI, etc." through the `agent` cog. | None: it is a workflow library, not a ticket service. |
| **strongdm/attractor** | No code: three natural-language specs, Apache-2.0 | 1,349; no release; last push 2026-03-17 | Specification of a pipeline runner where the workflow is a Graphviz DOT graph. | Checkpoint after each node, resume after crash; per-node `max_retries` and `retry_target`; `goal_gate` nodes that must succeed before exit; `wait.human` nodes for approval [measured, attractor-spec.md]. | Any: a `CodergenBackend` interface you implement. | None specified. |
| **open-inspect/background-agents** | TypeScript, MIT | 3,507; no release; pushed 2026-11-21 | Open clone of Ramp's Inspect: web, Slack, GitHub PR and Linear triggers; one cloud sandbox per session. | Cloudflare Durable Objects with SQLite per session, D1 database for secrets [measured, README]. "Single-tenant only". | OpenCode or Claude in the sandbox; Codex, Grok via subscriptions. | GitHub App; the README mentions GitLab credentials. Needs Cloudflare plus a sandbox provider: not a self-hosted-only stack. |
| **bitrise-io/bitclaw-public** | Python, MIT | 18; last push 2026-07-07 | Reference Slack bot that delegates coding to disposable cloud machines running Claude Code. | A persistent conversation per Slack thread. Explicitly "educational — not a supported product, and not maintained". | Claude Code. | GitHub, Jira, Slack; Bitrise remote machines. Value is its documented security model. |
| **OpenHands/OpenHands** | TypeScript/Python, MIT | 93,961; v1.43.0 on 2026-11-20 | A full agent product with its own agent, a UI ("Agent Canvas"), a Python SDK, and Docker sandboxes per conversation. | Its own server and conversation store. | Its own agent, or Claude Code, Codex, Gemini, Pi, OpenCode "or any agent with ACP". | GitHub; GitLab and Bitbucket integrations documented for Cloud and Enterprise; Azure DevOps for Enterprise. Forgejo/Gitea: not in the documentation index [measured]. |
| **anantjain-xyz/symphony-rust** | Rust + Tauri desktop app, MIT | 14; v0.1.31 on 2026-11-16; created 2026-05-31; 2 contributors | Symphony-style daemon as a macOS app: polls Linear, clones a workspace per issue, dispatches an agent, retries with backoff. | Local SQLite for events, token counts, retries. Retry prompt includes the previous error. | Codex, Claude Code, Cursor, OpenCode "natively over their structured event streams", behind one `AgentDriver` trait [measured, `docs/AGENT-ADAPTER-CONTRACT.md`]. | Linear only; macOS only ("other platforms are untested"). |
| **mikeyobrien/ralph-orchestrator** | Rust, MIT | 3,206; pushed 2026-11-13 | A loop runner: keeps an agent iterating on a spec until it prints a completion marker or hits a limit. `cargo install ralph-cli`. | Files under `.ralph/`; iteration cap. Not a ticket workflow. | Several backends (`ralph init --backend claude`). | None. |

Other Rust ports of the Symphony spec found by repository search, all with 0 to 9 stars: `lightcap/symphony-rust`, `hlky/symphony-rs`, `jadenmaciel/symphony-rs`, `howardpen9/symphony-rs`, `cnidrs/symphony`, `bubbleptr/concerto`, `KB01111/OpenAI-Symphony-Rust`, `pedrocid/SymphonyMac` [measured]. The spec's invitation to port was taken up, but no port has a community.

A Rust implementation of StrongDM's Attractor spec: one repository search returned nothing; **not found** (the search was shallow).

### 3.2 What each is worth to a small team

- **vibe-kanban is the best Rust code to read, and a risky product to adopt.** Its `crates/executors` directory is a working, Apache-licensed answer to "how do I spawn and parse ten agents from Rust", including worktree management (`crates/worktree-manager`). But the company announced on 10 April 2026: "Today we're shutting down bloop … The Vibe Kanban project will live on, open source and community maintained" [vendor]. Releases continue (v0.1.46 on 2026-11-15) [measured]. It relies on undocumented Claude flags (section 1.1), pins Codex crates 39 versions back, and has refused or left open every self-hosted forge request. It also solves a different problem: a human at a board, not a daemon on a tracker.
- **Symphony is the right design to copy for a ticket workflow, and the wrong code to run.** The spec is precise on the parts that are hard to get right (claim states, single authority, backoff, stall detection, restart recovery without a database, tracker as the stop button). But the reference is Elixir, a "preview", untouched since September, and bound to the Codex App Server.
- **`anantjain-xyz/symphony-rust` is the closest existing thing to the target** (Rust, Symphony semantics, four agents behind one trait, SQLite, MIT). It is also six months old, written by two people, tied to Linear and to a macOS desktop shell. Its crate layout (`symphony-core`, `-agents`, `-tracker`, `-worker`, `-storage`, `-contracts`) and its adapter contract document are a useful template; depending on it is not reasonable yet [inference].
- **Attractor is the best source for the approval and retry vocabulary** (goal gates, retry targets, human gates, checkpoint per node). It is a spec, so it costs nothing to borrow from.
- **Roast shows the "workflow as code in the host language" style.** For a Rust team it is an existence proof that a few primitives (model call, agent call, shell, map, repeat) cover most workflows, not something to depend on.
- **OpenHands is what to pick if the team decides not to build.** It is the only large project here that documents GitLab and runs any ACP agent. It is a Python and TypeScript product, not a Rust library.
- **bitclaw and background-agents are worth reading for their security models**, not for their code: both document the incidents behind each guardrail.

### 3.3 Self-hosted forge support, in one place

| Project | GitHub | GitLab | Forgejo / Gitea |
|---|---|---|---|
| Claude Code itself | Action and app [vendor] | Documented GitLab CI/CD page; `--worktree` accepts a GitLab merge request URL [vendor] | Not found |
| Codex | Action, app [vendor] | "GitLab (Beta)" in the documentation menu [vendor] | Not found |
| Symphony (spec) | Through agent skills | Through agent skills | Through agent skills; nothing built in |
| vibe-kanban | Yes | No (open request) | No (PR closed unmerged) |
| OpenHands | Yes | Cloud and Enterprise | Not found |
| background-agents | Yes (GitHub App) | Partial mention | Not found |
| symphony-rust | Via the agent's own tools | Not found | Not found |

Consequence [inference]: a team on Forgejo or Gitea will write the forge adapter itself whatever it forks. The honest shortcut is the Symphony one: keep forge operations in the agent's skills and a small CLI (`tea`, `fj`, or the REST API), and keep the orchestrator ignorant of the forge except for reading CI status.

---

## 4. Sandboxes a small self-hosting team can run under such an orchestrator

"Sandbox" here means: what stops an agent that runs shell commands from reading secrets, reaching the network, or damaging the host.

| Option | What it isolates | Cost | Effort and limits | Source |
|---|---|---|---|---|
| **Git worktree only** | Nothing. It separates working copies, not processes. | Free | One command per run. Agents share the host, its credentials and its network. Fine for trusted repositories on a dedicated machine. Claude Code has `--worktree`; vibe-kanban has a `worktree-manager` crate. | [vendor] CLI reference; [measured] vibe-kanban |
| **The agent's own OS sandbox** | Files and network of shell commands. Codex: built in, read-only by default. Claude Code: opt-in "sandboxed Bash tool" using Seatbelt on macOS and `bubblewrap` + `socat` on Linux. | Free | Claude's sandbox "covers shell commands only. Claude's file tools, MCP servers, and hooks run outside it". Not available on native Windows. `bubblewrap` can fail inside a container. | [vendor] Sandboxing page, Codex non-interactive page |
| **Anthropic sandbox-runtime (`srt`)** | Any process: wrap the whole agent, an MCP server, or a command. File allow/deny lists; network denied by default and forced through a proxy with a domain allowlist. | Free, Apache-2.0 | `npm install -g @anthropic-ai/sandbox-runtime`, so it needs Node.js. Labelled "Beta Research Preview". 7,210 stars, v0.0.83 on 2026-11-13. Works with any agent, not only Claude. | [measured] repo; [vendor] README |
| **Container per run (Docker or Podman)** | File system and process tree; network if you configure it. Shares the host kernel. | Free on your own server | The default of OpenHands ("each new conversation in its own Docker container") and of most CI runners. Needs an image per stack and a way to pass a short-lived credential. | [vendor] OpenHands README |
| **Firecracker or another microVM** | A separate kernel per run: the strongest isolation here. | Free software; needs hardware virtualisation (KVM) on the host | You build images, networking and snapshots yourself. Reasonable only with someone to own it. Not researched today. | [secondary, general knowledge, not re-checked] |
| **E2B** (hosted microVMs) | Separate VM per sandbox | Per second: $0.000014 per vCPU-second and $0.0000045 per GiB-second of memory. The default 2 vCPU + 4 GiB is about $0.17 per hour. | Hosted; a "BYOC" (your own cloud) deployment exists through sales. | [vendor] pricing page; hourly figure computed |
| **Modal Sandboxes** | Container-based sandbox | Per second: $0.00003942 per physical core (2 vCPU) and $0.00000667 per GiB of memory. 2 vCPU + 4 GiB is about $0.24 per hour. Billed on actual use, not on reservation. | Hosted only. | [vendor] pricing page; hourly figure computed |
| **Daytona** | Sandbox with snapshots | Per hour: $0.0504 per vCPU, $0.0162 per GiB of memory, storage $0.000108 per GiB after 5 free. 2 vCPU + 4 GiB is about $0.17 per hour. | Hosted; the project is also open source (self-hosting not checked today). | [vendor] pricing page; hourly figure computed |

How to read the prices [inference]: a 30-minute ticket run costs about 10 US cents of sandbox on any of the three hosted services. The model tokens for the same run cost more by one or two orders of magnitude. Sandbox price is not the deciding factor; data location and who operates it are.

A reasonable ladder for a small team that hosts its own forge [inference]:

1. Start: a dedicated runner user on the server, one worktree per ticket, the agent's own sandbox turned on, no production credentials on that machine.
2. Next: wrap the agent in `srt` or a rootless container with a network allowlist (model API, forge, package registries).
3. Only if agents run untrusted code or several teams share the host: microVMs, hosted or self-run.

At every level the rule from the other notes holds: the orchestrator keeps the forge token and the tracker token; the agent gets a short-lived, repository-scoped credential or none.

---

## 5. Verdict

**Which interface is safe to build a Rust harness on.**

1. Define your own trait, about the size of symphony-rust's `AgentDriver`: workspace path, rendered prompt, permission and sandbox settings, timeout, cancellation; out come normalised events and a result with a session ID, an outcome and an error class.
2. First implementation: `claude -p --output-format json` (or `stream-json` for progress), with `--json-schema` for step results, `--resume` for multi-step tickets, `--permission-prompts none` for unattended steps, and the `defer` hook for the human gates. Every one of these is documented.
3. Second implementation: `codex exec --json --output-schema`, with `--sandbox workspace-write` and `codex exec resume`.
4. Optional third: an ACP client, when a team wants goose, Gemini CLI, Copilot or OpenCode. Wait for the Rust crate to settle after the v2 Preview before making it the main path.
5. Do not link vendor Rust crates into the orchestrator. Do not use undocumented flags. Do not use the Codex App Server unless a concrete need (live approval dialogue, mid-turn steering) appears.
6. Pin the agent binary version per environment, record it with each run, and keep a small contract test per adapter (start, result parsing, resume, deny path) that runs before any version bump. With one Claude Code release a day and one Codex release every five days, the bump is a routine, not an event.
7. Authenticate with API keys. Keep subscription tokens for local trials.

**Which existing project is closest.** For a ticket-driven feature and bug workflow in Rust: the Symphony `SPEC.md` as the design, with `anantjain-xyz/symphony-rust` as the nearest implementation and vibe-kanban's `crates/executors` as the reference for agent adapters. None is fit to adopt as a dependency: the first is a spec bound to Codex, the second is six months old and Linear-and-macOS only, the third lost its company and targets a different workflow. For a small team the realistic plan is a new, small Rust daemon (a state table in SQLite, a tracker adapter, a forge adapter, two agent adapters) that copies Symphony's state machine and Attractor's gate vocabulary. The existing notes estimated this shape; this note confirms that the agent side of it rests on documented interfaces, and that there is no shortcut to fork for the Forgejo side.

---

## 6. Not found, or not verified

- The original text and date of Anthropic's spring 2026 announcement about Agent SDK usage on subscription plans, and what exactly it would have changed. Only the pause notice of 15 June 2026 and the 7 October 2026 update remain in the support article. The amounts of the monthly API credits were not read.
- Any formal stability or versioning promise for Claude Code's `stream-json` event format or for `claude -p` flags. Only the "feature-detect with `capabilities`" guidance was found.
- A standalone wire specification of Claude Code's `--input-format stream-json` messages and of the SDK control channel (`--permission-prompt-tool=stdio`). I checked the headless page, the CLI reference and the hooks reference, not every SDK page.
- An equivalent for Codex of the announced-then-paused billing change. Per-plan limits for `codex exec` under ChatGPT login were not read in detail.
- A protocol version number for the Codex App Server, or a compatibility policy between Codex releases. The documentation only says the schema is specific to each version.
- Why the `github-copilot-sdk` crate is at 1.0.35 while the repository's latest release is v2.0.1; whether Copilot's ACP support has left public preview.
- A Rust implementation of StrongDM Attractor (one shallow repository search). A Rust ticket-to-PR orchestrator with built-in GitLab, Forgejo or Gitea support. GitHub's search rate limit cut this part short.
- How Shopify Roast holds state across a crash, retries a failed cog, or waits for a human: not in the README; source not read.
- Whether OpenHands' open-source edition (as opposed to Cloud and Enterprise) can be pointed at a self-hosted GitLab, and any Forgejo support.
- The roadmap of community-maintained vibe-kanban promised in the shutdown post; who maintains it now.
- Gemini CLI's headless interface (not inspected). Cursor's and OpenCode's (not inspected; symphony-rust drives both).
- Firecracker operating cost and effort for a small team; self-hosting status of Daytona and E2B. Prices of container hosting were not collected.
- Independent reports of teams running `claude -p` or `codex exec` under a Rust daemon in production, with failure rates. All adapter evidence here comes from reading two code bases.
- No web search was possible in this pass (budget exhausted). Secondary sources, issue-tracker discussions and blog posts about upgrade breakages were therefore not surveyed.

---

## Sources

Anthropic (read 2026-11-21):

- Run Claude Code programmatically (headless): https://code.claude.com/docs/en/headless
- CLI reference: https://code.claude.com/docs/en/cli-reference
- Hooks reference, "Defer a tool call for later": https://code.claude.com/docs/en/hooks
- Permission modes: https://code.claude.com/docs/en/permission-modes
- Authentication: https://code.claude.com/docs/en/authentication
- Legal and compliance: https://code.claude.com/docs/en/legal-and-compliance
- Agent SDK overview: https://code.claude.com/docs/en/agent-sdk/overview
- Agent SDK sessions: https://code.claude.com/docs/en/agent-sdk/sessions
- Manage costs: https://code.claude.com/docs/en/costs
- Sandboxed Bash tool: https://code.claude.com/docs/en/sandboxing
- Support article, "Use the Claude Agent SDK with your Claude plan": https://support.claude.com/en/articles/15036540-use-the-claude-agent-sdk-with-your-claude-plan
- Claude Code releases: https://github.com/anthropics/claude-code/releases
- sandbox-runtime: https://github.com/anthropics/sandbox-runtime

OpenAI (read 2026-11-21):

- Non-interactive mode: https://developers.openai.com/codex/noninteractive
- Codex App Server: https://developers.openai.com/codex/app-server
- Codex SDK: https://developers.openai.com/codex/sdk
- Authentication: https://developers.openai.com/codex/auth
- Maintain Codex account auth in CI/CD: https://developers.openai.com/codex/auth/ci-cd-auth
- Pricing: https://developers.openai.com/codex/pricing
- Open Source: https://developers.openai.com/codex/open-source
- Repository, workspace manifest and app-server README: https://github.com/openai/codex , https://github.com/openai/codex/blob/main/codex-rs/Cargo.toml , https://github.com/openai/codex/blob/main/codex-rs/app-server/README.md
- Symphony and its spec: https://github.com/openai/symphony , https://raw.githubusercontent.com/openai/symphony/main/SPEC.md

goose, Copilot, ACP:

- goose repository: https://github.com/aaif-goose/goose
- goose headless tutorial: https://github.com/aaif-goose/goose/blob/main/documentation/docs/tutorials/headless-goose.md
- goose CLI commands: https://github.com/aaif-goose/goose/blob/main/documentation/docs/guides/goose-cli-commands.md
- goose, "Build an app over ACP": https://github.com/aaif-goose/goose/blob/main/documentation/docs/oi-kit/acp/index.md
- goose oi-kit: https://github.com/aaif-goose/goose/blob/main/documentation/docs/oi-kit/index.md
- goose custom distributions: https://github.com/aaif-goose/goose/blob/main/CUSTOM_DISTROS.md
- Copilot SDK repository and Rust README: https://github.com/github/copilot-sdk , https://github.com/github/copilot-sdk/blob/main/rust/README.md
- ACP agents list: https://agentclientprotocol.com/get-started/agents
- ACP Rust library: https://agentclientprotocol.com/libraries/rust
- ACP v2 Preview announcement (2026-11-20): https://agentclientprotocol.com/announcements/acp-v2-preview
- ACP Rust SDK: https://github.com/agentclientprotocol/rust-sdk
- ACP adapters: https://github.com/agentclientprotocol/claude-agent-acp , https://github.com/agentclientprotocol/codex-acp
- Copilot ACP public preview (linked from the agents list): https://github.blog/changelog/2026-01-28-acp-support-in-copilot-cli-is-now-in-public-preview/

crates.io API (read 2026-11-21):

- https://crates.io/crates/agent-client-protocol
- https://crates.io/crates/github-copilot-sdk
- https://crates.io/crates/codex-protocol and https://crates.io/crates/codex-app-server-protocol (third-party publications)
- https://crates.io/crates/goose (unrelated load-testing tool)

Orchestrators:

- vibe-kanban: https://github.com/BloopAI/vibe-kanban
- vibe-kanban Claude executor: https://github.com/BloopAI/vibe-kanban/blob/main/crates/executors/src/executors/claude.rs
- vibe-kanban executors manifest: https://github.com/BloopAI/vibe-kanban/blob/main/crates/executors/Cargo.toml
- vibe-kanban shutdown post (2026-04-10): https://www.vibekanban.com/blog/shutdown
- vibe-kanban forge requests: https://github.com/BloopAI/vibe-kanban/issues/1697 , https://github.com/BloopAI/vibe-kanban/pull/3428
- Shopify Roast: https://github.com/Shopify/roast
- StrongDM Attractor: https://github.com/strongdm/attractor , https://github.com/strongdm/attractor/blob/main/attractor-spec.md
- background-agents: https://github.com/open-inspect/background-agents
- bitclaw: https://github.com/bitrise-io/bitclaw-public
- OpenHands: https://github.com/OpenHands/OpenHands , documentation index https://docs.openhands.dev/llms.txt
- symphony-rust: https://github.com/anantjain-xyz/symphony-rust , https://github.com/anantjain-xyz/symphony-rust/blob/main/docs/AGENT-ADAPTER-CONTRACT.md
- ralph-orchestrator: https://github.com/mikeyobrien/ralph-orchestrator
- Other Rust Symphony ports: https://github.com/lightcap/symphony-rust , https://github.com/hlky/symphony-rs , https://github.com/jadenmaciel/symphony-rs , https://github.com/howardpen9/symphony-rs , https://github.com/cnidrs/symphony , https://github.com/bubbleptr/concerto

Sandbox pricing (read 2026-11-21):

- E2B: https://e2b.dev/pricing
- Modal: https://modal.com/pricing
- Daytona: https://www.daytona.io/pricing

Repository statistics measured through the GitHub API on 2026-11-21:

- openai/codex: 136,052 stars, Rust, Apache-2.0, release rust-v0.171.0 (2026-11-20)
- anthropics/claude-code: 156,548 stars, release v2.1.330 (2026-11-20)
- aaif-goose/goose: 56,851 stars, Rust, Apache-2.0, v1.60.2 (2026-11-20)
- microsoft/copilot-sdk (redirect from github/copilot-sdk): 10,700 stars, MIT, v2.0.1 (2026-11-18)
- agentclientprotocol/agent-client-protocol: 4,706 stars; agentclientprotocol/rust-sdk: 248 stars, v5.5.1 (2026-11-21)
- agentclientprotocol/claude-agent-acp: 2,800 stars, v0.109.1 (2026-11-21); agentclientprotocol/codex-acp: 590 stars, v2.9.0 (2026-11-21)
- openai/symphony: 28,121 stars, Elixir, v0.0.3 (2026-09-15)
- BloopAI/vibe-kanban: 28,772 stars, Rust, Apache-2.0, v0.1.46 (2026-11-15)
- Shopify/roast: 1,258 stars, Ruby, MIT, v1.4.1 (2026-11-10)
- strongdm/attractor: 1,349 stars, no code, last push 2026-03-17
- open-inspect/background-agents: 3,507 stars, TypeScript, MIT, no release
- bitrise-io/bitclaw-public: 18 stars, Python, MIT, last push 2026-07-07
- OpenHands/OpenHands: 93,961 stars, MIT, v1.43.0 (2026-11-20)
- anantjain-xyz/symphony-rust: 14 stars, Rust, MIT, v0.1.31 (2026-11-16), created 2026-05-31, 2 contributors
- mikeyobrien/ralph-orchestrator: 3,206 stars, Rust, MIT, last push 2026-11-13
- anthropics/sandbox-runtime: 7,210 stars, Apache-2.0, v0.0.83 (2026-11-13)
