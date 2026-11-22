"""Tests of the facts read from a source file: the paths cited after "Enforced by:", and the task
contracts cited under "Delegated tasks"."""
from __future__ import annotations

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from harnesslib import facts, maturity  # noqa: E402


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


SOURCE_WITH_TASK = "# demo\n\n## Delegated tasks\n- `bump` — bump a dependency.\n"
REAL_CONTRACT = ("---\nname: bump\ndescription: Bump a dependency and prove nothing breaks.\n---\n"
                 "# Bump a dependency\n\n## Done when\n- The tests pass.\n")


class TaskContractTest(unittest.TestCase):
    """A task contract counts for level 4 when its front matter says what it is; whether it says when
    the task is done is measured beside it."""

    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.repo = tmp.name

    def contract(self, text: str, base: str = ".claude/skills") -> dict:
        path = os.path.join(self.repo, base, "bump", "SKILL.md")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(text)
        return facts.contract_facts(self.repo, SOURCE_WITH_TASK)["items"][0]

    def level4_check(self) -> dict:
        with open(os.path.join(self.repo, "AGENTS.md"), "w", encoding="utf-8") as handle:
            handle.write(SOURCE_WITH_TASK)
        checks = maturity.level4(facts.collect(self.repo))
        return next(c for c in checks if c["id"] == "L4.contracts")

    def test_an_empty_contract_is_not_complete(self) -> None:
        item = self.contract("")

        self.assertTrue(item["referenced"])
        self.assertFalse(item["complete"])
        self.assertEqual(item["missing"], ["front matter name", "front matter description"])
        self.assertFalse(item["done_criterion"])

    def test_a_minimal_real_contract_is_complete(self) -> None:
        item = self.contract(REAL_CONTRACT)

        self.assertTrue(item["complete"])
        self.assertEqual(item["missing"], [])
        self.assertTrue(item["done_criterion"])

    def test_an_empty_contract_fails_the_level_4_check(self) -> None:
        self.contract("")

        check = self.level4_check()

        self.assertFalse(check["passed"])
        self.assertIn(".claude/skills/bump/SKILL.md", check["next_action"])
        self.assertIn("front matter name, front matter description", check["next_action"])

    def test_a_minimal_real_contract_passes_the_level_4_check(self) -> None:
        self.contract(REAL_CONTRACT)

        self.assertTrue(self.level4_check()["passed"])

    def test_a_complete_contract_that_is_not_cited_fails_the_level_4_check(self) -> None:
        self.contract(REAL_CONTRACT.replace("name: bump", "name: other"))
        os.rename(os.path.join(self.repo, ".claude/skills/bump"), os.path.join(self.repo, ".claude/skills/other"))

        self.assertFalse(self.level4_check()["passed"])

    def test_an_incomplete_contract_still_counts_as_a_file(self) -> None:
        self.contract("# Bump\n")

        self.assertEqual(facts.contract_facts(self.repo, SOURCE_WITH_TASK)["count"], 1)

    def test_a_contract_without_front_matter_lacks_name_and_description(self) -> None:
        item = self.contract("# Bump\n\n## Done when\n- The tests pass.\n")

        self.assertEqual(item["missing"], ["front matter name", "front matter description"])
        self.assertTrue(item["done_criterion"])

    def test_an_empty_description_is_missing(self) -> None:
        item = self.contract(REAL_CONTRACT.replace("description: Bump a dependency and prove nothing breaks.",
                                                   "description:"))

        self.assertEqual(item["missing"], ["front matter description"])

    def test_a_folded_description_counts(self) -> None:
        item = self.contract(REAL_CONTRACT.replace("description: Bump a dependency and prove nothing breaks.",
                                                   "description: >\n  Bump a dependency\n  and prove nothing breaks."))

        self.assertEqual(item["missing"], [])

    def test_an_unclosed_front_matter_is_not_a_front_matter(self) -> None:
        item = self.contract("---\nname: bump\ndescription: Bump.\n\n## Done when\n- The tests pass.\n")

        self.assertEqual(item["missing"], ["front matter name", "front matter description"])

    def test_a_contract_without_a_done_criterion_is_measured_as_such(self) -> None:
        item = self.contract("---\nname: bump\ndescription: Bump a dependency.\n---\n# Bump\n\n## Steps\n1. Bump.\n")

        self.assertFalse(item["done_criterion"])

    def test_done_when_in_the_description_is_not_a_done_criterion(self) -> None:
        item = self.contract("---\nname: bump\ndescription: Says the task is done when CI is green.\n---\n# Bump\n")

        self.assertFalse(item["done_criterion"])

    def test_a_done_criterion_can_be_a_line_or_a_french_heading(self) -> None:
        head = "---\nname: bump\ndescription: Bump a dependency.\n---\n# Bump\n\n"
        for body in ("**Done when:** the tests pass.\n", "- Done when the CI is green.\n",
                     "## Definition of done\n- CI green.\n", "## Fini quand\n- La CI est verte.\n",
                     "## Terminé quand\n- La CI est verte.\n"):
            with self.subTest(body):
                self.assertTrue(self.contract(head + body)["done_criterion"])

    def test_a_contract_under_agents_skills_is_judged_the_same(self) -> None:
        path = os.path.join(self.repo, ".agents/skills/bump/SKILL.md")
        os.makedirs(os.path.dirname(path))
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(REAL_CONTRACT)

        self.assertTrue(self.level4_check()["passed"])

    def test_the_go_hexa_level_4_overlay_contract_is_complete(self) -> None:
        root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        overlay = os.path.join(root, "fixtures/repos/go-hexa/runs/2026-11-14-step-target4-step2-after/overlay")

        items = facts.contract_facts(overlay, "- `add-endpoint`")["items"]

        self.assertEqual([(i["name"], i["complete"], i["done_criterion"]) for i in items],
                         [("add-endpoint", True, True)])


if __name__ == "__main__":
    unittest.main()
