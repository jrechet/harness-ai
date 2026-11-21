"""Tests of the facts read from a source file: the paths cited after "Enforced by:"."""
from __future__ import annotations

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from harnesslib import facts  # noqa: E402


def agents_md(*rules: str) -> str:
    return "# demo\n\n## Rules\n" + "".join(f"- {rule}\n" for rule in rules)


class EnforcedByPathTest(unittest.TestCase):
    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.repo = tmp.name

    def touch(self, rel: str) -> None:
        path = os.path.join(self.repo, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write("")

    def guards(self, *rules: str) -> list[str]:
        dangling = facts.dangling_facts(self.repo, agents_md(*rules))
        return [d["ref"] for d in dangling if d["kind"] == "guard"]

    def test_reports_a_missing_path_cited_without_backticks(self) -> None:
        refs = self.guards("No raw SQL. Why: incident #42. Enforced by: tools/nonexistent.go [2026-11]")

        self.assertEqual(refs, ["tools/nonexistent.go"])

    def test_reports_the_line_of_a_missing_path_cited_without_backticks(self) -> None:
        text = agents_md("Never force push.", "No raw SQL. Enforced by: tools/nonexistent.go")

        dangling = facts.dangling_facts(self.repo, text)

        self.assertEqual(dangling, [{"kind": "guard", "ref": "tools/nonexistent.go", "line": 5}])

    def test_accepts_an_existing_path_cited_without_backticks(self) -> None:
        self.touch("tools/check.go")

        refs = self.guards("No raw SQL. Enforced by: tools/check.go.")

        self.assertEqual(refs, [])

    def test_finds_an_existing_dotfile_cited_in_backticks(self) -> None:
        self.touch(".golangci.yml")

        refs = self.guards("Imports are sorted. Enforced by: `.golangci.yml` [2026-11]")

        self.assertEqual(refs, [])

    def test_finds_an_existing_dotfile_cited_without_backticks(self) -> None:
        self.touch(".golangci.yml")

        refs = self.guards("Imports are sorted. Enforced by: .golangci.yml")

        self.assertEqual(refs, [])

    def test_reports_a_missing_dotfile_with_its_dot(self) -> None:
        refs = self.guards("Imports are sorted. Enforced by: `.golangci.yml`")

        self.assertEqual(refs, [".golangci.yml"])

    def test_strips_a_leading_dot_slash_only(self) -> None:
        self.touch("scripts/check.sh")

        refs = self.guards("Scripts are checked. Enforced by: `./scripts/check.sh`",
                           "Hooks are checked. Enforced by: ./.hooks/missing.sh")

        self.assertEqual(refs, [".hooks/missing.sh"])

    def test_does_not_report_a_guardrail_that_is_not_a_path(self) -> None:
        refs = self.guards("The plan is kept. Enforced by: Stop hook [2026-11]",
                           "Main is protected. Enforced by: branch protection",
                           "HTTP goes through the client. Enforced by: `eslint/no-raw-fetch`",
                           "Reviews are required. Enforced by: branch protection, e.g. two approvals.")

        self.assertEqual(refs, [])

    def test_does_not_judge_a_product_or_version_word_as_a_path(self) -> None:
        refs = self.guards("Routes are guarded. Enforced by: Next.js middleware",
                           "The runtime is pinned. Enforced by: Node.js engines check [2026-11]",
                           "Components are typed. Enforced by: Vue.js compiler.",
                           "Style is linted. Enforced by: ESLint v9.x",
                           "Queries are typed. Enforced by: the ASP.NET analyzer, socket.io excluded")

        self.assertEqual(refs, [])

    def test_reports_a_missing_path_cited_after_a_product_word(self) -> None:
        refs = self.guards("Routes are guarded. Enforced by: Next.js middleware in src/middleware.ts")

        self.assertEqual(refs, ["src/middleware.ts"])

    def test_does_not_judge_a_url_as_a_path(self) -> None:
        refs = self.guards("Main is protected. Enforced by: https://example.test/settings/rules.html")

        self.assertEqual(refs, [])

    def test_judges_only_the_first_bare_path(self) -> None:
        self.touch("tools/check.go")

        refs = self.guards("No raw SQL. Enforced by: tools/check.go, which replaced tools/old.go")

        self.assertEqual(refs, [])

    def test_still_reports_a_missing_path_cited_in_backticks(self) -> None:
        refs = self.guards("No raw SQL. Enforced by: `tools/nonexistent.go`")

        self.assertEqual(refs, ["tools/nonexistent.go"])


if __name__ == "__main__":
    unittest.main()
