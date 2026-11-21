"""The state page: its data comes from what `status` measures, the audit's opinions stay apart, and the
file is standalone and inert."""
from __future__ import annotations

import base64
import hashlib
import io
import json
import os
import re
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import harness  # noqa: E402
from harnesslib import facts, maturity, page  # noqa: E402

AGENTS = """# demo — instructions for agents

Mode: **delegation**.

## Rules
- No secret in the code. Why: the March leak. (unverified) [2026-03]

## Forbidden
- Never push to main.
"""


def write(root: str, rel: str, text: str) -> None:
    path = os.path.join(root, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)


class Case(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo = os.path.join(self.tmp.name, "demo")
        os.makedirs(self.repo)

    def build(self, **kwargs):
        return page.build(self.repo, today=None, **kwargs)


class DataTests(Case):
    def test_every_check_of_the_ladder_says_what_it_touches(self):
        self.assertEqual(set(page.TOUCHES), set(maturity.CHECK_PLAIN))
        layers = {ident for ident, _, _ in page.LAYERS}
        for touch in filter(None, page.TOUCHES.values()):
            self.assertIn(touch[0], layers)
            self.assertIn(touch[2], ("add", "change"))

    def test_an_empty_repository_shows_what_is_missing_and_every_step(self):
        data = self.build()
        self.assertEqual(data["level"]["reached"], 0)
        files = {i["path"]: i["state"] for i in data["layers"][0]["items"]}
        self.assertEqual(files["AGENTS.md"], "missing")
        self.assertEqual(files[".cursor/rules"], "optional")          # only needed if the team uses the tool
        state = maturity.evaluate(facts.collect(self.repo))
        failing = [c["id"] for l in state["levels"] for c in l["checks"] if not c["passed"]]
        self.assertEqual(len(data["steps"]), len(failing))
        self.assertEqual(data["steps"][0]["touch"], {"layer": "instructions", "path": "AGENTS.md", "effect": "add"})
        self.assertEqual([s["level"] for s in data["steps"]], sorted(s["level"] for s in data["steps"]))

    def test_without_an_instruction_file_level_1_is_the_single_init_step(self):
        data = self.build()
        level1 = [s for s in data["steps"] if s["level"] == 1]
        shown = [s for s in level1 if not s["follows"]]
        self.assertEqual(len(shown), 1)
        self.assertIn("write a short AGENTS.md", shown[0]["action"])
        folded = [s for s in level1 if s["follows"]]
        self.assertEqual(len(folded), 4)
        for step in folded:
            self.assertEqual((step["missing"], step["action"], step["touch"]),
                             ("nothing to measure yet: there is no instruction file", "comes with the instruction file", None))
        text = json.dumps(data["steps"])
        for false_step in ("merge CLAUDE.md", "move reference material", "longer than"):
            self.assertNotIn(false_step, text)
        self.assertTrue(all(not s["follows"] for s in data["steps"] if s["level"] > 1))

    def test_the_page_walks_only_the_steps_that_are_not_folded_into_another(self):
        with open(page.TEMPLATE_FILE, encoding="utf-8") as fh:
            script = fh.read()
        self.assertIn("data.steps.filter((s) => !s.follows)", script)
        self.assertNotRegex(script, r"data\.steps\.filter\(\(s\) => !?s\.in_scope\)")   # every walk starts from the unfolded steps

    def test_with_an_instruction_file_no_step_is_folded(self):
        write(self.repo, "AGENTS.md", "# demo\n")
        data = self.build()
        self.assertTrue(all(not s["follows"] for s in data["steps"]))
        self.assertEqual(len([s for s in data["steps"] if s["level"] == 1]), 2)

    def test_the_files_found_are_shown_in_their_layer_and_a_stub_is_a_pointer(self):
        write(self.repo, "AGENTS.md", AGENTS)
        write(self.repo, "CLAUDE.md", "@AGENTS.md\n")
        write(self.repo, ".github/workflows/ci.yml", "on: push\njobs:\n  t:\n    runs-on: x\n    steps:\n      - run: make test\n")
        data = self.build()
        by_layer = {l["id"]: {i["path"]: i for i in l["items"]} for l in data["layers"]}
        self.assertEqual(by_layer["instructions"]["AGENTS.md"]["state"], "present")
        self.assertIn("lines", by_layer["instructions"]["AGENTS.md"]["detail"])
        self.assertEqual(by_layer["instructions"]["CLAUDE.md"]["state"], "pointer")
        self.assertIn(".github/workflows/ci.yml", by_layer["pipeline"])
        self.assertEqual(data["level"]["reached"], 1)

    def test_with_claude_md_as_the_source_the_steps_touch_claude_md(self):
        write(self.repo, "CLAUDE.md", "# Guide\n\n" + "\n".join(f"- line {i}" for i in range(80)))
        data = self.build()
        touched = {s["touch"]["path"] for s in data["steps"] if s["touch"] and s["touch"]["layer"] == "instructions"}
        self.assertEqual(touched, {"CLAUDE.md"})
        self.assertGreater(len([s for s in data["steps"] if s["touch"] and s["touch"]["path"] == "CLAUDE.md"]), 3)

    def test_with_claude_md_as_the_source_agents_md_is_not_shown_as_missing(self):
        write(self.repo, "CLAUDE.md", "# Guide\n\n" + "\n".join(f"- line {i}" for i in range(80)))
        files = {i["path"]: i for i in self.build()["layers"][0]["items"]}
        self.assertEqual(files["CLAUDE.md"]["state"], "present")
        self.assertIn("the source", files["CLAUDE.md"]["detail"])
        self.assertNotIn("should only point to AGENTS.md", files["CLAUDE.md"]["purpose"])
        self.assertEqual(files["AGENTS.md"]["state"], "optional")
        self.assertIn("CLAUDE.md is the source", files["AGENTS.md"]["purpose"])

    def test_steps_beyond_the_target_are_kept_but_out_of_scope(self):
        write(self.repo, "AGENTS.md", AGENTS)
        write(self.repo, ".harness/config.json", json.dumps({"target_level": 2}))
        data = self.build()
        self.assertEqual(data["target"]["level"], 2)
        self.assertTrue(all(s["in_scope"] == (s["level"] <= 2) for s in data["steps"]))
        self.assertTrue(any(not s["in_scope"] for s in data["steps"]))
        self.assertEqual([l["in_scope"] for l in data["ladder"]], [True, True, True, False, False])

    def test_no_check_id_reaches_what_the_page_shows(self):
        text = json.dumps({k: v for k, v in self.build().items() if k != "medals"})
        self.assertNotRegex(text, r"\bL[1-4]\.[a-z_]+")

    def test_the_audit_is_carried_apart_as_opinions_and_kept_verdicts_are_left_out(self):
        write(self.repo, "AGENTS.md", AGENTS)
        write(self.repo, ".harness/audit.json", json.dumps({"audit": {"date": "2026-11-01"}, "elements": [
            {"path": "AGENTS.md:6", "verdict": "PUSH_DOWN", "priority": "P1", "finding": "nothing checks it", "target": "a lint rule"},
            {"path": "CLAUDE.md:1", "verdict": "KEEP", "priority": "P3", "finding": "fine"},
            {"path": "docs/x.md:2", "verdict": "REMOVE", "priority": "P2", "finding": "x" * 900}, "not a row"]}))
        audit = self.build()["audit"]
        self.assertEqual(audit["date"], "2026-11-01")
        self.assertEqual([r["path"] for r in audit["rows"]], ["AGENTS.md:6", "docs/x.md:2"])       # by priority
        self.assertEqual(audit["rows"][0]["file"], "AGENTS.md")
        self.assertEqual(audit["rows"][0]["plain"], page.VERDICT_PLAIN["PUSH_DOWN"])
        self.assertLessEqual(len(audit["rows"][1]["finding"]), page.MAX_TEXT)

    def test_without_an_audit_or_with_an_unreadable_one_there_is_no_opinion(self):
        self.assertIsNone(self.build()["audit"])
        write(self.repo, ".harness/audit.json", "{not json")
        self.assertIsNone(self.build()["audit"])
        write(self.repo, ".harness/audit.json", json.dumps({"elements": "none"}))
        self.assertIsNone(self.build()["audit"])

    def test_the_medals_come_with_the_page_and_nothing_is_written(self):
        write(self.repo, "AGENTS.md", AGENTS)
        data = self.build()
        self.assertEqual(data["medals"]["kind"], "repo")
        self.assertFalse(os.path.exists(os.path.join(self.repo, ".harness")))


class RenderTests(Case):
    def test_the_page_is_standalone_and_its_policy_matches_its_own_script(self):
        html = page.render_html(self.build())
        self.assertNotIn("{{", html)
        self.assertNotRegex(html, r"<(?:script|link|img)[^>]+(?:src|href)=")          # nothing fetched
        self.assertNotIn("innerHTML", html)
        policy = re.search(r'Content-Security-Policy" content="([^"]+)"', html)[1]
        self.assertIn("default-src 'none'", policy)
        digests = re.findall(r"'sha256-([A-Za-z0-9+/=]+)'", policy)
        for tag in ("style", "script"):                                              # the digest of the body that is really served
            body = re.search(rf"<{tag}>(.*?)</{tag}>", html, re.DOTALL)[1]
            self.assertIn(base64.b64encode(hashlib.sha256(body.encode("utf-8")).digest()).decode("ascii"), digests)
        self.assertEqual(len(digests), 2)
        self.assertNotIn("unsafe", policy)

    def test_text_from_the_repository_cannot_close_the_data_block(self):
        write(self.repo, "AGENTS.md", AGENTS)
        write(self.repo, ".harness/audit.json", json.dumps({"elements": [
            {"path": "a.md:1", "verdict": "MOVE", "finding": "</script><script>alert(1)</script> & {{data}}"}]}))
        html = page.render_html(self.build())
        self.assertEqual(html.count("</script>"), 2)
        block = re.search(r'<script type="application/json" id="page-data">(.*?)</script>', html, re.DOTALL)[1]
        self.assertIn("alert(1)", json.loads(block)["audit"]["rows"][0]["finding"])


class CommandTests(Case):
    def run_status(self, *args):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = harness.main(["status", self.repo, *args])
        return code, out.getvalue(), err.getvalue()

    def test_a_hand_edited_audit_file_does_not_crash_status(self):
        write(self.repo, "AGENTS.md", AGENTS)
        for broken in ({"elements": "none"}, {"elements": ["text", 3, None]}, {"audit": "x", "removals": ["y"], "elements": [{"verdict": ["a"]}]},
                       {"elements": [{"priority": ["x"], "actual_layer": 3}]}, {"process_leaks": 5, "guarded_rules": 3, "removals": 2}):
            write(self.repo, ".harness/audit.json", json.dumps(broken))
            code, out, _ = self.run_status("--no-write")
            self.assertEqual(code, 0)
            self.assertIn("Level", out)

    def test_a_page_that_cannot_be_written_is_said_plainly(self):
        write(self.repo, "AGENTS.md", AGENTS)
        code, _, err = self.run_status("--no-write", "--page", self.repo)             # a folder, not a file
        self.assertEqual(code, 2)
        self.assertIn("could not be written", err)
        self.assertNotIn("Traceback", err)
        self.assertFalse(os.path.exists(self.repo + ".tmp"))

    def test_the_flag_writes_the_page_and_leaves_the_usual_output_alone(self):
        write(self.repo, "AGENTS.md", AGENTS)
        _, plain, _ = self.run_status("--no-write")
        target = os.path.join(self.tmp.name, "out", "state.html")
        code, out, err = self.run_status("--no-write", "--page", target)
        self.assertEqual(code, 0)
        self.assertEqual(out, plain)
        self.assertIn("page written", err)
        with open(target, encoding="utf-8") as fh:
            self.assertIn('id="page-data"', fh.read())
        self.assertFalse(os.path.exists(target + ".tmp"))


if __name__ == "__main__":
    unittest.main()
