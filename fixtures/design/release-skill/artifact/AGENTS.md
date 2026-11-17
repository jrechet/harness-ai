# demo-package — instructions for agents

Mode: assistance.

## Rules
- The agent never reads `.npmrc.publish` outside a release. Why: the token leaked into a session log in March. (unverified) [2026-03]
- Commit messages follow Conventional Commits. Why: the version is derived from them. Enforced by: `.github/workflows/ci.yml` (job `commitlint`) [2025-09]
