"""The skills map (docs/skills-map/index.html) shows every skill of the repository, and only those:
the nine of the harness-ai plugin, the seven of ai-sdlc and the internal harness-stress, each in the
family its folder gives. A skill added or removed without the page fails here. Each skill's goal,
state and links stay a review judgement: the page restates the SKILL.md files, it measures nothing."""
from __future__ import annotations

import glob
import os
import re
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PAGE = os.path.join(ROOT, "docs", "skills-map", "index.html")
# A skill node of the page: `{ id: "...", fam: "...", name: "..."`. The steps that are not skills carry
# `gate: true` between `fam` and `name`, so they do not match.
NODE = re.compile(r'\{ id: "[a-z]+", fam: "(repo|flow|sdlc|back)", name: "([a-z-]+)"')
FOLDERS = {  # skill folder -> the families the page may file its skills under
    "skills": {"repo", "flow"},
    os.path.join("plugins", "ai-sdlc", "skills"): {"sdlc"},
    os.path.join(".claude", "skills"): {"back"},
}


def skills_on_disk():
    found = {}
    for folder, families in FOLDERS.items():
        for path in glob.glob(os.path.join(ROOT, folder, "*", "SKILL.md")):
            found[os.path.basename(os.path.dirname(path))] = families
    return found


def skills_on_page():
    with open(PAGE, encoding="utf-8") as handle:
        return {name: family for family, name in NODE.findall(handle.read())}


class SkillsMapTest(unittest.TestCase):
    def test_the_page_shows_every_skill_and_no_other(self):
        self.assertEqual(sorted(skills_on_page()), sorted(skills_on_disk()))

    def test_each_skill_sits_in_the_family_of_its_folder(self):
        disk = skills_on_disk()
        for name, family in skills_on_page().items():
            with self.subTest(skill=name):
                self.assertIn(family, disk.get(name, set()))

    def test_the_flow_skills_sit_with_the_team_workflow(self):
        page = skills_on_page()
        for name, family in page.items():
            with self.subTest(skill=name):
                if name.startswith("flow-"):
                    self.assertEqual(family, "flow")
                elif name.startswith("harness-") and family != "back":
                    self.assertEqual(family, "repo")


if __name__ == "__main__":
    unittest.main()
