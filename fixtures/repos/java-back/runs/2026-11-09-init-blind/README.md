# Blind run of harness-init — 2026-11-09

Bare repository: java-back without `CLAUDE.md` or `.claude/` (`harness fixture bare java-back <dest>`), on a `develop` branch. Interview answers provided: delegation, 3 devs, GitHub Actions "I do not know what is really verified", Claude Code only, first task "the release, done by hand with scripts", forbidden: prod without human validation, applied migration, push to main.

Result: `AGENTS.md` of 44 lines, level 1 **5/5**, `CLAUDE.md` stub, `release` contract of 45 lines, `.harness/state.json` and `audit.json` committed.

What the contract produced avoids, without having seen the traps: no reading of `SUCCESS` in a log (`gh run watch --exit-status`), preconditions as commands and not as sentences, explicit human validation before the trigger, version given by the human and not inferred from the branch ("`release.mjs` does and gets it wrong"), and the update of `VERSION` after the release, the unplanted defect found by the first blind audit.

Its gate audit against the traps of java-back: 6/8, the two missing ones (T1, T2) were about the removed `CLAUDE.md`; so complete on what existed. It also noted `gradlew` absent from the repository and a comment of `ArchitectureTest` pointing to a `CLAUDE.md` that does not exist, two true facts.

Weakness noted: the rule "a controller never depends on a repository" carries an invented "Why" ("to keep the rules testable outside HTTP") although no incident is known. The skill now asks to write "architecture decision, no known incident" rather than inventing.
