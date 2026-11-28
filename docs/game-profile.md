# The video-game profile

What `harness game` and the `harness-game` skill set up in a game's repository, and why each piece is there. The knowledge is one data file, [`cli/harnesslib/game_profile.json`](../cli/harnesslib/game_profile.json); the command reads it, the skill calls the command. Everything below that the profile does is tooled and tested (`cli/tests/test_game.py`); none of it has been played by an agent on a game yet.

## Why a profile, and not a plugin of game skills

A game needs a development loop that the general harness does not know: a run that boots the game and is judged by its log, a screenshot the agent opens, an export proven early, a person who plays and says whether it is fun. That is the only part specific to games, and it is mostly commands a program can judge. So the profile is data and a command beside the level ladder, read by one skill. It is not a set of role agents or design templates.

What exists already, surveyed on 2026-11-27, splits into four kinds: studio templates you clone (dozens of role agents and documents), knowledge packs that teach an agent each engine's API, scaffolders with a per-engine command contract, and editor bridges over MCP. None audits an existing game repository and says which piece of its loop is missing, which is what this repository does for any other repository. The two largest projects both moved away from heavy process. One made its one-page path the default after its own comparison ranked the heavier path last; that rests on a single brief and a self-report, so it is an anecdote, not a measurement. The other deleted its planner pipeline and kept its engine traps and capture recipes. Engine knowledge stays with the packs that maintain it; the profile keeps the loop.

The game's design (the concept, the core loop, which mechanics to cut) is the owner's. If a game-design plugin is used, its one-page design with a cut list counts as the loop's scope piece (`design/GDD.md`), and its recorded playtests count when its journal dates them (`design/game.json`, `design/journal.jsonl`); a playtest with no date is shown as such.

**The ladder does not move.** The profile writes its choices under `game` in `.harness/config.json`, a key the ladder does not read; `harness status` measures the same with or without it (a test holds it). A scale suggests a target level (one hour and a jam: 1; weeks: 3) and only suggests it.

## Three scales, one dial

The same setup is wrong at two of the three sizes of a game: over-building early is how small games die, and under-building a long project is how it stops being changeable. So the owner picks a scale, and the loop asks only for its pieces.

| Scale | What it is | Pieces |
|---|---|---|
| `hour` | a toy or a one-hour jam: one mechanic, no document; the loop is a person starting the game and playing it after each change | version, run, instructions, owned_files, playtest |
| `jam` | a weekend or a game jam: a build that exports from the first hour, a cut list, a capture the agent looks at, credited assets | the hour's, plus scope, export, smoke, runner, capture, check, assets |
| `weeks` | a small game built over weeks: everything of a jam, plus the game rules tested headless and the same loop run by the CI | the jam's, plus test, ci |

The default age a playtest may reach before the loop calls it stale (none at the hour scale, 1 day for a jam, 14 days over weeks) is ours, not a source's: the owner sets it (`harness game set --playtest-days`).

## The pieces, and why each one

| Piece | Catches | How it is measured |
|---|---|---|
| version | the agent writing the API of a version the project does not run | the version read from the project files (`project.godot`, `ProjectVersion.txt`, `package.json`, `Cargo.toml`, `conf.lua`, `requirements.txt`, the `.uproject`) |
| run | no way to hand a playable build to the owner | a recorded command; the judge never runs it, it opens a window or a server |
| instructions | an agent that does not know the engine, the loop, or what done means | the instruction file names the engine, its version and each recorded command (or the judge) |
| owned_files | scenes and references broken by editing serialised files as text | the instruction file names the engine's own files (`.tscn`, `.uid`, `.prefab`, `.meta`…) |
| scope | features nobody asked for | a design file with a cut-list heading (Cut, Later, Out of scope, Coupé, Plus tard…) |
| export | the export that fails at the end of the jam | a recorded command, the file it must write, and a judged run that passed |
| smoke | a change that breaks the game's start | a recorded command, its ready line, and a judged run that passed |
| runner | a check skipped because only the text asks for it | `.harness/game_loop.py` is in the repository and is the plugin's file |
| capture | visible bugs nobody looked at | a recorded command, the image it must write, and a judged run that passed |
| check | typos found only when the game starts | a recorded command and a judged run that passed |
| playtest | the agent deciding what is fun | a dated line in a playtest log, or a playtest in `design/game.json`, recent enough |
| assets | an asset that cannot ship because its licence is unknown | every image, sound, model or font is named, by file or folder, in a credits file |
| test | rules that cannot change without breaking | a recorded command and a judged run that passed |
| ci | a loop that only runs when someone remembers | a workflow runs the judge; a workflow that runs a recorded command itself is a gap, since nothing reads its log |

**The judge.** `python3 .harness/game_loop.py <piece|all>` (the same code as `harness game run`) passes a run only when it ends in time with exit code 0, every command of a pipe included; no line matches the engine's error patterns; the game's ready line appears when one is recorded; and the output file (a screenshot, a build, a results file) is inside the repository, was written by this run and reports no failure. A run with no window on an engine whose exit code lies, without a ready line, fails: a silent log proves nothing. On a timeout, everything the run started is stopped, not only the shell. A binary that is not installed is named, looked up on the PATH rather than read from the shell's message, which is in the machine's language. Each verdict goes to `.harness/game_runs/last.json`, which ignores itself in git; a command piece is in place only when the last judged run of its current command passed. `harness game run` also judges a command recorded before the engine was known with the engine's error lines, and the loop asks to record it again.

**What it refuses to run.** A command that publishes is refused when it is recorded and again before every run, so a command written into `.harness/config.json` by hand, or run by the CI, is refused too. The check reads the command's words, segment by segment: `git push` and `git tag` (with or without `-C`), the package registries (`npm`, `pnpm`, `yarn`, `cargo`, `twine`, `docker` and others), `butler` and `steamcmd`, the hosting tools (`wrangler`, `netlify`, `vercel`, `surge`, `gh-pages`, `firebase`), a copy to a bucket or a remote host, `gh release`, and a script or an npm script whose name says it deploys, publishes or releases. A dry run passes. What it cannot see: a script whose name says nothing and that publishes inside. This is not the `ai-sdlc` delivery guardrail, which refuses deliveries in the agent's shell: the lists differ, and the guardrail sees `harness game run`, not what it runs.

Two pieces matter most, according to what practitioners report. The first is the run judged by its log: the most reported failure is an agent that declares a game working without having run it or looked at it. The second is the capture: GameDevBench (arXiv 2602.11103, current abstract) has the best agent at 53.8%, with 51.4% on gameplay tasks against 33.0% on 2D graphics, and visual feedback took one model from 41.1% to 52.0%.

## What each engine's loop proves, and the traps

| Engine | Run with no window | Screenshot | The trap the judge handles |
|---|---|---|---|
| Godot 4 | `godot --headless --quit-after N` proves the game boots and logs no script error | `--write-movie`, which needs a window: `--headless` renders nothing | exits 0 on a script that does not parse, on a failing import, on test scripts that fail to load (reproduced on 4.4 to 4.7): judged by its log and a ready line. `--import` is a prerequisite on a fresh clone, not a check; the static check is gdtoolkit's `gdlint` |
| Unity | `-batchmode -nographics -logFile -` with an `-executeMethod` the project writes | an editor method; graphics needed | no common exit code for its tools, tests judged by the results file; never `-quit` with `-runTests`; a Personal licence cannot be activated from the command line (the owner does it in Unity Hub) |
| Web (Phaser, three.js, KAPLAY, canvas…) | a headless browser that loads the build and fails on console errors | `page.screenshot` or `toHaveScreenshot`, compared only in the environment that made the reference | the game sets a ready mark after its first frame; WebGL without a GPU needs software rendering asked for explicitly in Chromium |
| Pygame | `SDL_VIDEODRIVER=dummy`, a frame count the game reads | the screen surface saved to a PNG, with no display | none beyond a Python traceback |
| Bevy | `cargo test` on an `App` with no window; `bevy_ci_testing` for a scripted run | `bevy_ci_testing` screenshot events, which need a window | none beyond a panic |
| LÖVE | no headless flag: the game reads an argument, runs a few frames and quits | a window | a Lua error shows the error screen and may not change the exit code |
| Unreal | automation tests through `UnrealEditor-Cmd` | `HighResShot` | its candidates were not checked on a primary source: the command says so |

Tried on a real engine, Godot 4.7.2 on macOS, on 2026-11-28: a one-scene project whose script does not parse gives `SCRIPT ERROR: Parse Error` and exit code 0 from `godot --headless --quit-after 120`; `harness game run smoke` fails it on its error lines and on the missing ready line, and passes the same project with the script fixed. The independent review ran the windowed capture once: `--write-movie shots/frame.png` writes `shots/frame00000000.png` and the following frames, so that is the file the profile records.

On macOS there is no `xvfb`: a screenshot opens a window, which works locally. On a Linux CI, wrap it in `xvfb-run --auto-servernum`. On macOS the Godot binary is usually inside `/Applications/Godot.app/Contents/MacOS/`.

## The lines an AGENTS.md needs for a game

`harness game instructions` proposes them, filled from what is measured, each with its why and its date, to put under Rules and Forbidden. They are candidates: the owner confirms each.

- the engine and its exact version, and "check an API against the documentation of this version";
- the loop: after each change, run the judge; a green run is not a working game;
- before saying a visible change is done, take the capture and open it;
- for an engine whose exit code lies, never judge a run by it;
- the engine's own files, and how to change them without breaking references;
- feel, difficulty and fun are the owner's call, and every report says "not yet played by a person" until the owner has played;
- at the hour and jam scales: no coverage target, no refactoring, no architecture rule on a prototype; over weeks: game rules apart from rendering, with one seeded random generator and a fixed timestep;
- from the jam scale on: a new idea goes to the cut list; every asset gets its source and licence;
- under Forbidden: publishing the game, and any publishing key or engine licence.

A line says `Enforced by:` only when what enforces it is in the repository: the judge for the exit-code line, a CI workflow that runs the judge for the loop line. Everything else is `(unverified)`. The command prints the share of rules that say what enforces them, before and after, because level 3 asks for half and these lines can take a file under it.

Questions only the owner answers are asked, not written: the core loop in one sentence, who plays and how often, a jam's rules on AI-generated code and assets (the GMTK Game Jam 2024 forbade them), a reference for the look and the feel, and where the game will be released.

## What the profile does not do

- It does not say whether the game is fun. Every serious source hands that to a person playing; the loop's last piece is a dated playtest, not a grade.
- It does not publish. Itch.io, Steam and the stores need the owner's account, keys and choices; the profile refuses to record or run those commands, as far as their words tell.
- It does not judge feel, balance or art. A screenshot is shown to the agent so it fixes what is visibly broken, not so it decides what is beautiful.
- It has not been measured. No game sample project exists in `fixtures/repos/` yet, and no agent has played the skill blind. The engines that cannot run on this repository's CI runner (Godot, Unity, Unreal, LÖVE) can only be advised on here, never measured.

## Sources

Opened between 2026-11-27 and 2026-11-28; a claim above that rests on one source says so.

- Godot command line: https://docs.godotengine.org/en/stable/tutorials/editor/command_line_tutorial.html
- Godot exits 0 when it failed, measured on 4.4 to 4.7 (a forum post, reproduced by its author only): https://forum.godotengine.org/t/things-that-exit-0-in-godot-4-headless-even-though-they-failed-measured-reproducible/145990
- Headless Godot renders nothing (gdUnit4): https://raw.githubusercontent.com/MikeSchulze/gdUnit4/master/documentation/doc/_faq/ci.md
- Godot movie maker: https://docs.godotengine.org/en/stable/tutorials/animation/creating_movies.html
- gdtoolkit: https://github.com/Scony/godot-gdscript-toolkit
- GUT command line: https://gut.readthedocs.io/en/latest/Command-Line.html
- Unity editor command line: https://docs.unity.com/en-us/engine/current/manual/unity-editor/command-line-arguments/editor
- Unity Test Framework command line: https://docs.unity3d.com/Packages/com.unity.test-framework@1.4/manual/reference-command-line.html
- Unity licence activation for CI (GameCI): https://game.ci/docs/github/activation
- Vite: https://vite.dev/guide/cli · Playwright screenshots: https://playwright.dev/docs/test-snapshots · Playwright clock: https://playwright.dev/docs/clock
- Chromium and SwiftShader: https://chromium.googlesource.com/chromium/src/+/refs/heads/main/docs/gpu/swiftshader.md
- Phaser's own test guide: https://raw.githubusercontent.com/phaserjs/phaser/master/tests/TESTING.md
- Pygame with no window: https://raw.githubusercontent.com/pygame/pygame/main/examples/headless_no_windows_needed.py
- Bevy system tests: https://raw.githubusercontent.com/bevyengine/bevy/main/tests/how_to_test_systems.rs
- LÖVE boot: https://raw.githubusercontent.com/love2d/love/main/src/modules/love/boot.lua
- Fixed timestep: https://gafferongames.com/post/fix_your_timestep/
- GameDevBench: https://arxiv.org/abs/2602.11103
- Godot CI and itch.io publishing: https://github.com/abarichello/godot-ci · https://itch.io/docs/butler/pushing.html · https://itch.io/docs/creators/html5
- GMTK Game Jam 2024 rules: https://itch.io/jam/gmtk-2024
- Prior art: https://github.com/Donchitos/Claude-Code-Game-Studios · https://github.com/htdt/godogen · https://github.com/gamedev-skills/awesome-gamedev-agent-skills · https://github.com/Er2oneousbit/claude-code-game-kit
