A review looks for what would be expensive once merged. In this order:
- **Correctness.** Does the change do what the PR and the ticket say? Edge cases, swallowed errors, lost data.
- **Scope.** Does the diff go beyond what was asked? An off-topic change is flagged, even if it is good.
- **Tests.** Does a changed behaviour have a test that would fail without the change? A disabled or weakened test is always flagged.
- **Contracts.** Does an API, a schema, a file or message format change for those who depend on it?
- **Security.** Unvalidated input, a secret in the code, a widened permission, a query built by concatenation.
- **Repository rules.** The Forbidden items and the rules of AGENTS.md, each quoted by its line.

Not commented: style, naming, formatting, what a linter or a formatter settles. If the repository has none, say so once, outside the comments.
