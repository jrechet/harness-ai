---
name: release
description: Publishes a new version of the package to the npm registry. Use when asked to "cut a version", "do a release" or "publish".
---

# Release

Repository structure: `src/` the code, `test/` the tests, `dist/` the build, `package.json` the manifest.

## Steps

1. Compute the next version from the commits since the last tag: a `feat:` commit bumps the minor, a `fix:` bumps the patch, a `!` or `BREAKING CHANGE` bumps the major. Without any of these commits, there is nothing to publish.
2. Check that `CHANGELOG.md` contains an entry for this version. If there is none, stop and ask for it.
3. Never publish from a branch other than `main`: check with `git branch --show-current` before continuing.
4. Set the version in `package.json`, create the tag `v<version>` and push it.
5. Publish with `npm publish`. The registry token is in `.npmrc.publish`: copy it into `.npmrc` for the duration of the command, then remove it.
6. Write the announcement for the `#releases` channel: what changes for a user, in three lines at most, without repeating the changelog word for word.
7. Have the announcement reviewed by the `release-reviewer` subagent before sending it.
8. Do not start a release if uncommitted files remain: check with `git status` and stop if there are any.
