"""Tests de `harness fresh` : un skill qui cite un fichier disparu est cassé, celui dont les fichiers ont
changé depuis est à revoir, et un chemin que git n'a jamais connu n'est pas jugé."""
from __future__ import annotations

import contextlib
import io
import os
import subprocess
import sys
import tempfile
import unittest
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import harness  # noqa: E402
from harnesslib import fresh  # noqa: E402

SKILL = """---
name: release
description: Publie une version.
---
1. Lance `python3 tools/version.py` puis lis `docs/guide.md`.
2. Écris le résultat dans `docs/agents/<point>.md` et dans `.harness/audit.json`.
3. Vérifie avec `make check` et `npm run lint`.
"""
TODAY = date(2026, 11, 15)


class RepoCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo = self.tmp.name
        self.git("init", "-q", "-b", "main")

    def git(self, *args: str, day: str = "2026-01-10") -> None:
        env = {**os.environ, "GIT_AUTHOR_DATE": f"{day}T12:00:00", "GIT_COMMITTER_DATE": f"{day}T12:00:00"}
        subprocess.run(["git", "-C", self.repo, "-c", "user.name=t", "-c", "user.email=t@example.com", *args],
                       capture_output=True, check=True, env=env)

    def write(self, rel: str, text: str) -> None:
        path = os.path.join(self.repo, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text)

    def commit(self, day: str) -> None:
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "c", day=day)

    def base(self) -> None:
        self.write(".claude/skills/release/SKILL.md", SKILL)
        self.write("tools/version.py", "x = 1\n")
        self.write("docs/guide.md", "guide\n")
        self.write("Makefile", "check:\n\ttrue\n")
        self.write("package.json", '{"scripts": {"lint": "eslint ."}}\n')
        self.commit("2026-10-20")

    def items(self) -> list[dict]:
        return fresh.collect(self.repo, TODAY)["items"]

    def signals(self) -> list[tuple[str, str]]:
        return [(i["state"], i["signal"]) for i in self.items()]


class PathTests(unittest.TestCase):
    def test_only_relative_paths_in_code_are_kept(self):
        text = "Lis `cli/harness.py:12`, `docs/agents/<point>.md`, `${ROOT}/x/y.py`, `https://a/b`, `oui/non`.\n```\npython3 ./tools/a.py --x b/c.json\n```\nPas `/etc/passwd` ni src/hors/code.py."
        self.assertEqual(fresh.cited_paths(text), ["cli/harness.py", "oui/non", "tools/a.py", "b/c.json"])


class ToolTests(RepoCase):
    def test_a_fresh_skill_has_nothing_to_say(self):
        self.base()
        self.assertEqual(self.signals(), [])

    def test_a_cited_file_that_git_knew_and_is_gone_is_broken(self):
        self.base()
        self.git("mv", "tools/version.py", "tools/semver.py")
        self.commit("2026-11-01")
        items = self.items()
        self.assertEqual([(i["state"], i["signal"]) for i in items], [("cassé", "reference")])
        self.assertIn("tools/version.py", items[0]["evidence"])
        self.assertEqual(items[0]["path"], ".claude/skills/release/SKILL.md")

    def test_a_path_git_never_knew_is_not_judged(self):
        self.base()   # docs/agents/<point>.md et .harness/audit.json n'ont jamais existé : ils parlent d'un autre dépôt
        self.assertNotIn(("cassé", "reference"), self.signals())

    def test_a_make_target_or_an_npm_script_that_disappeared_is_broken(self):
        self.base()
        self.write("Makefile", "test:\n\ttrue\n")
        self.write("package.json", '{"scripts": {"format": "prettier ."}}\n')
        self.commit("2026-11-01")
        evidence = " ".join(i["evidence"] for i in self.items() if i["signal"] == "reference")
        self.assertIn("make check", evidence)
        self.assertIn("npm run lint", evidence)

    def test_what_a_skill_cites_changed_long_after_its_last_reading(self):
        self.write(".claude/skills/release/SKILL.md", SKILL)
        self.write("tools/version.py", "x = 1\n")
        self.write("docs/guide.md", "guide\n")
        self.commit("2026-06-01")
        self.write("tools/version.py", "x = 2\n")
        self.commit("2026-06-10")           # dix jours après : dans la marge
        self.assertNotIn(("à revoir", "change"), self.signals())
        self.write("docs/guide.md", "guide refait\n")
        self.commit("2026-09-01")
        changed = [i for i in self.items() if i["signal"] == "change"]
        self.assertEqual(len(changed), 1)
        self.assertIn("docs/guide.md", changed[0]["evidence"])
        self.assertNotIn("tools/version.py", changed[0]["evidence"])

    def test_a_tool_nobody_touched_for_long_and_a_named_model_are_to_review(self):
        self.write(".claude/agents/relecteur.md", "---\nname: relecteur\n---\nUtilise claude-sonnet-4-5 pour relire.\n")
        self.commit("2026-01-10")
        self.assertEqual(sorted(self.signals()), [("à revoir", "immobile"), ("à revoir", "modele")])

    def test_skills_of_a_plugin_and_its_references_are_found_and_test_data_is_not(self):
        self.write("plugins/p/.claude-plugin/plugin.json", "{}")
        self.write("plugins/p/skills/s/SKILL.md", "Lis `references/grille.md` et `cli/outil.py`.\n")
        self.write("plugins/p/skills/s/references/grille.md", "g\n")
        self.write("plugins/p/cli/outil.py", "x\n")
        self.write("plugins/p/agents/a.md", "agent\n")
        self.write("fixtures/x/.claude/skills/faux/SKILL.md", "Lis `disparu/x.py`.\n")
        self.write("docs/agents/revue.md", "pas un agent\n")
        self.commit("2026-11-01")
        self.assertEqual(sorted(t["path"] for t in fresh.tools(self.repo)), ["plugins/p/agents/a.md", "plugins/p/skills/s/SKILL.md"])
        os.remove(os.path.join(self.repo, "plugins/p/cli/outil.py"))
        os.remove(os.path.join(self.repo, "plugins/p/skills/s/references/grille.md"))
        evidence = " ".join(i["evidence"] for i in self.items() if i["signal"] == "reference")
        self.assertIn("cli/outil.py", evidence)
        self.assertIn("references/grille.md", evidence)


class InstructionTests(RepoCase):
    AGENTS = ("# x\n\nMode : **assistance**.\n\n## Règles\n"
              "- Pas de secret. Pourquoi : fuite. (non vérifiée) [2024-03]\n"
              "- Les couleurs passent par les tokens. Pourquoi : dérive. Vérifiée par : `tools/absent.sh` [2026-10]\n\n"
              "## Interdits\n- Pousser sur main. Pourquoi : PR. [2026-01]\n")

    def test_an_old_unguarded_rule_and_a_guard_that_is_gone_are_reported(self):
        self.write("AGENTS.md", self.AGENTS)
        self.commit("2026-11-01")
        signals = self.signals()
        self.assertIn(("cassé", "garde-fou"), signals)
        self.assertIn(("à revoir", "regles"), signals)

    def test_without_git_only_the_instruction_signals_remain(self):
        plain = tempfile.TemporaryDirectory()
        self.addCleanup(plain.cleanup)
        self.repo = plain.name
        self.write("AGENTS.md", self.AGENTS)
        self.write(".claude/skills/s/SKILL.md", "Lis `tools/absent.py`. Modèle : claude-opus-4.\n")
        result = fresh.collect(self.repo, TODAY)
        self.assertFalse(result["git"])
        self.assertNotIn("reference", [i["signal"] for i in result["items"]])
        self.assertIn("modele", [i["signal"] for i in result["items"]])


class CliTests(RepoCase):
    def run_cli(self, *argv: str) -> tuple[int, str]:
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            code = harness.main(["fresh", self.repo, "--today", "2026-11-15", *argv])
        return code, out.getvalue()

    def test_the_hook_is_silent_when_nothing_presses_and_short_when_something_is_broken(self):
        self.base()
        self.assertEqual(self.run_cli("--hook"), (0, ""))
        self.git("rm", "-q", "tools/version.py")
        self.commit("2026-11-01")
        code, out = self.run_cli("--hook")
        self.assertEqual(code, 0)
        self.assertIn("tools/version.py", out)
        self.assertLessEqual(len(out.splitlines()), 4)

    def test_strict_exits_1_only_when_something_is_broken(self):
        self.base()
        self.assertEqual(self.run_cli("--strict")[0], 0)
        self.git("rm", "-q", "tools/version.py")
        self.commit("2026-11-01")
        code, out = self.run_cli("--strict")
        self.assertEqual(code, 1)
        self.assertIn("cassé", out)

    def test_a_hook_never_blocks_a_session(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(harness.main(["fresh", os.path.join(self.repo, "absent"), "--hook"]), 0)
            self.assertEqual(harness.main(["fresh", self.repo, "--today", "hier"]), 2)


if __name__ == "__main__":
    unittest.main()
