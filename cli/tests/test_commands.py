"""Tests de `harness commands` : ce que la CI lance vraiment, là où ça s'écarte de la commande que
l'écosystème laisse deviner. Ce sont des lignes candidates pour AGENTS.md, pas des lignes écrites."""
from __future__ import annotations

import contextlib
import io
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import harness  # noqa: E402
from harnesslib import commands  # noqa: E402

CI = """name: ci
on: [push]
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Dépendances
        run: mvn -B -q dependency:go-offline
      - run: mvn -B verify
      - name: Intégration
        run: |
          docker compose up -d db
          make it
      - run: SPRING_PROFILES_ACTIVE=ci ./mvnw -Pintegration verify -DskipITs=false && echo fini
"""


class RepoCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo = self.tmp.name

    def write(self, rel: str, text: str) -> None:
        path = os.path.join(self.repo, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text)

    def found(self) -> dict:
        return commands.collect(self.repo)

    def by_command(self) -> dict:
        return {c["command"]: c for c in self.found()["candidates"]}


class CiTests(RepoCase):
    def test_run_lines_and_blocks_are_read_with_their_line(self):
        self.write(".github/workflows/ci.yml", CI)
        got = {(c["command"], c["line"]) for c in commands.ci_commands(self.repo)}
        self.assertIn(("mvn -B verify", 10), got)
        self.assertIn(("make it", 14), got)
        self.assertIn(("docker compose up -d db", 13), got)

    def test_gitlab_scripts_are_read(self):
        self.write(".gitlab-ci.yml", "test:\n  stage: test\n  script:\n    - pip install -e .\n    - make check\n  only:\n    - main\n")
        got = [c["command"] for c in commands.ci_commands(self.repo)]
        self.assertEqual(got, ["pip install -e .", "make check"])


class CandidateTests(RepoCase):
    def test_a_wrapper_the_ci_runs_is_a_candidate_with_the_obvious_command_beside_it(self):
        self.write("pom.xml", "<project/>")
        self.write(".github/workflows/ci.yml", CI)
        found = self.by_command()
        self.assertEqual(found["make it"]["kind"], "enveloppe")
        self.assertEqual(found["make it"]["source"], ".github/workflows/ci.yml:14")
        self.assertIn("mvn verify", found["make it"]["obvious"])
        self.assertFalse(found["make it"]["documented"])

    def test_the_obvious_command_with_plain_flags_is_not_a_candidate(self):
        self.write("pom.xml", "<project/>")
        self.write(".github/workflows/ci.yml", CI)
        found = self.found()
        self.assertNotIn("mvn -B verify", self.by_command())
        self.assertIn("mvn verify", [c["command"] for c in found["obvious_in_ci"]])

    def test_options_that_change_what_runs_make_a_candidate(self):
        self.write("pom.xml", "<project/>")
        self.write(".github/workflows/ci.yml", CI)
        found = self.by_command()
        command = "./mvnw -Pintegration verify -DskipITs=false"
        self.assertEqual(found[command]["kind"], "options")

    def test_setup_noise_is_ignored(self):
        self.write("pom.xml", "<project/>")
        self.write(".github/workflows/ci.yml", CI)
        for command in self.by_command():
            for noise in ("docker", "echo", "dependency:go-offline"):
                self.assertNotIn(noise, command)

    def test_a_candidate_already_in_the_instructions_is_marked(self):
        self.write("pom.xml", "<project/>")
        self.write(".github/workflows/ci.yml", CI)
        self.write("AGENTS.md", "| `src/` | `make it` | ci |\n")
        self.assertTrue(self.by_command()["make it"]["documented"])

    def test_wrapper_targets_outside_the_ci_are_weaker_candidates(self):
        self.write("Makefile", ".PHONY: it lint\nVAR := 1\nit: build\n\tmvn verify -Pit\nlint:\n\t./lint.sh\nbuild:\n\tmvn package\n%.o: %.c\n\tcc $<\n")
        self.write("package.json", json.dumps({"scripts": {"test": "jest", "e2e": "playwright test", "prepare": "husky"}}))
        found = self.by_command()
        self.assertEqual(found["make it"]["kind"], "cible")
        self.assertEqual(found["make it"]["source"], "Makefile:3")
        self.assertIn("make lint", found)
        self.assertIn("npm run e2e", found)
        self.assertNotIn("npm run prepare", found)
        self.assertNotIn("make VAR", found)

    def test_node_python_and_go_know_their_obvious_command(self):
        self.write("package.json", json.dumps({"scripts": {"test": "vitest"}}))
        self.write("go.mod", "module x\n")
        self.write(".github/workflows/ci.yml",
                   "jobs:\n  t:\n    steps:\n      - run: npm ci\n      - run: npm test\n      - run: pnpm run test:int\n"
                   "      - run: go test -tags integration ./...\n      - run: go test ./...\n")
        found = self.by_command()
        self.assertIn("pnpm run test:int", found)
        self.assertEqual(found["go test -tags integration ./..."]["kind"], "options")
        self.assertNotIn("npm test", found)
        self.assertNotIn("go test ./...", found)
        self.assertNotIn("npm ci", found)

    def test_a_script_of_the_repo_is_a_wrapper_only_if_it_exists(self):
        self.write("scripts/it.sh", "#!/bin/sh\n")
        self.write(".github/workflows/ci.yml", "jobs:\n  t:\n    steps:\n      - run: ./scripts/it.sh --fast\n      - run: bash scripts/absent.sh\n")
        found = self.by_command()
        self.assertIn("./scripts/it.sh --fast", found)
        self.assertNotIn("bash scripts/absent.sh", found)

    def test_what_a_delivery_workflow_runs_is_a_candidate_for_a_ban_not_for_the_table(self):
        self.write("deploy/apply.sh", "#!/bin/sh\n")
        self.write(".github/workflows/deploy.yml",
                   'jobs:\n  d:\n    steps:\n      - run: ./deploy/apply.sh "${{ inputs.environment }}"\n')
        found = self.by_command()
        command = './deploy/apply.sh "${{ inputs.environment }}"'
        self.assertEqual(found[command]["kind"], "livraison")
        self.assertIn("Interdit", commands.render_md(self.found()))

    def wf(self, body: str, name: str = "ci.yml") -> dict:
        self.write(f".github/workflows/{name}", body)
        return self.by_command()

    def test_a_deploy_job_or_command_in_ci_yml_is_delivery_never_to_run(self):
        found = self.wf("jobs:\n  test:\n    steps:\n      - run: make it\n  deploy:\n    steps:\n      - run: make ship\n"
                        "  prod:\n    environment: production\n    steps:\n      - run: make go\n"
                        "  misc:\n    steps:\n      - run: make deploy\n      - run: ./mvnw -Prelease verify\n")
        self.write("Makefile", "deploy:\n\tx\n")
        self.assertEqual(found["make it"]["kind"], "enveloppe")
        for command in ("make ship", "make go", "make deploy"):
            self.assertEqual(found[command]["kind"], "livraison", command)
        self.assertEqual(self.by_command()["make deploy"]["kind"], "livraison")

    def test_a_command_an_ordinary_job_also_runs_is_not_delivery(self):
        self.write(".github/workflows/deploy.yml", "jobs:\n  d:\n    steps:\n      - run: npm run build\n")
        found = self.wf("jobs:\n  t:\n    steps:\n      - run: npm run build\n")
        self.assertEqual(found["npm run build"]["kind"], "enveloppe")

    def test_a_delivery_target_of_the_makefile_is_listed_as_delivery(self):
        self.write("Makefile", "test lint: deps\n\tx\npublish:\n\tx\n")
        found = self.by_command()
        self.assertEqual(found["make publish"]["kind"], "livraison")
        self.assertIn("make test", found)
        self.assertIn("make lint", found)

    def test_documented_means_the_exact_command_not_a_prefix(self):
        self.wf("jobs:\n  t:\n    steps:\n      - run: make it\n")
        self.write("AGENTS.md", "Please make it work with `make it-fast`, then make test-all.\n")
        self.assertFalse(self.by_command()["make it"]["documented"])
        self.write("AGENTS.md", "Lance `make it`.\n")
        self.assertTrue(self.by_command()["make it"]["documented"])

    def test_common_shapes_of_run_are_read(self):
        self.write("pom.xml", "<project/>")
        found = self.wf('jobs:\n  t:\n    steps:\n      - "run": make quoted\n      - run: >-\n          make\n          folded\n'
                        "      - run: |\n          mvn verify \\\n            -Pintegration\n          if [ -f x ]; then make cond; fi\n"
                        "          (cd api && make sub)\n          make it # commentaire\n          mvn -B verify | tee out.log\n"
                        "          cat <<EOF > f\n          make bogus\n          EOF\n          make ${{ matrix.t || 'x' }}\n")
        for command in ("make quoted", "make folded", "make cond", "cd api && make sub", "make it", "make ${{ matrix.t || 'x' }}"):
            self.assertIn(command, found)
        self.assertEqual(found["mvn verify -Pintegration"]["kind"], "options")
        self.assertNotIn("make bogus", found)
        self.assertIn("mvn verify", [c["command"] for c in self.found()["obvious_in_ci"]])

    def test_composite_actions_and_gitlab_blocks_are_read(self):
        self.write(".github/actions/setup/action.yml", "runs:\n  using: composite\n  steps:\n    - run: make composite\n      shell: bash\n")
        self.write(".gitlab-ci.yml", "test:\n  script:\n    - |\n      make block\n    - make plain\ndeploy_prod:\n  script:\n    - make push\n")
        found = self.by_command()
        for command in ("make composite", "make block", "make plain"):
            self.assertIn(command, found)
        self.assertEqual(found["make push"]["kind"], "livraison")

    def test_environment_runners_and_the_working_directory_are_kept(self):
        self.write("pyproject.toml", "")
        found = self.wf("jobs:\n  t:\n    steps:\n      - run: uv run pytest -m fast\n      - run: npx playwright test\n"
                        "      - run: npx playwright install\n      - run: cd web && npm run lint\n"
                        "      - name: api\n        working-directory: api\n        run: make it\n      - run: make it\n")
        for command in ("uv run pytest -m fast", "npx playwright test", "cd web && npm run lint", "cd api && make it", "make it"):
            self.assertIn(command, found)
        self.assertNotIn("npx playwright install", found)

    def test_a_script_of_the_manifest_has_its_line(self):
        self.write("package.json", '{\n  "scripts": {\n    "test": "jest",\n    "e2e": "playwright test"\n  }\n}\n')
        self.assertEqual(self.by_command()["npm run e2e"]["source"], "package.json:4")

    def test_an_empty_repo_has_no_candidate_and_does_not_crash(self):
        self.assertEqual(self.found()["candidates"], [])
        self.write(".github/workflows/casse.yml", "run: |\n\t\x00\n  run:\n")
        self.write("package.json", "{")
        self.found()


class CliTests(RepoCase):
    def test_the_command_prints_candidates_in_markdown_and_json(self):
        self.write("pom.xml", "<project/>")
        self.write(".github/workflows/ci.yml", CI)
        for fmt, needle in (("md", "`make it`"), ("json", '"candidates"')):
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                code = harness.main(["commands", self.repo, "--format", fmt])
            self.assertEqual(code, 0)
            self.assertIn(needle, out.getvalue())
        self.assertIn("mvn verify", out.getvalue())


if __name__ == "__main__":
    unittest.main()
