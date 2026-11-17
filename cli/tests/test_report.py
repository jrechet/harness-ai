"""Tests of the common report: an assessment always has the same form — what is evaluated,
what is expected, what is observed, what is advised — and a gap without evidence is refused."""
from __future__ import annotations

import base64
import contextlib
import hashlib
import io
import json
import os
import re
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import harness  # noqa: E402
from harnesslib import place, report  # noqa: E402

GRID = place.load_grid()


def sample() -> dict:
    return {
        "subject": {"kind": "skill", "name": "release", "path": ".claude/skills/release/SKILL.md"},
        "date": "2026-11-15",
        "source": "harness-design",
        "summary": "The skill mixes a procedure and a limit.",
        "items": [
            {"scope": "Never publish outside main", "expected": "Server-side protection",
             "observed": "A sentence in the skill", "advice": "Protect the branch",
             "status": "blocker", "evidence": ["SKILL.md:12"], "tag": "PUSH_DOWN"},
            {"scope": "Chain tag and publication", "expected": "Skill", "observed": "Skill",
             "advice": "", "status": "ok"},
            {"scope": "Compute the version", "expected": "CLI subcommand", "observed": "Does not exist yet",
             "advice": "Write the subcommand and its test", "status": "todo"},
        ],
    }


def without(data: dict, *path: str) -> dict:
    copy = json.loads(json.dumps(data))
    node = copy
    for key in path[:-1]:
        node = node[int(key)] if isinstance(node, list) else node[key]
    del node[path[-1]]
    return copy


class ValidateTests(unittest.TestCase):
    def test_the_sample_is_valid(self):
        self.assertEqual(report.validate(sample()), [])

    def test_each_of_the_four_columns_is_required(self):
        for field in ("scope", "expected", "observed"):
            with self.subTest(field=field):
                self.assertTrue(any(field in e for e in report.validate(without(sample(), "items", "0", field))))

    def test_a_gap_without_advice_is_refused(self):
        data = sample()
        data["items"][0]["advice"] = " "
        self.assertTrue(any("advice" in e for e in report.validate(data)))

    def test_a_gap_without_evidence_is_refused(self):
        errors = report.validate(without(sample(), "items", "0", "evidence"))
        self.assertTrue(any("evidence" in e for e in errors))

    def test_a_conforming_item_needs_neither_advice_nor_evidence(self):
        data = sample()
        data["items"] = [data["items"][1]]
        self.assertEqual(report.validate(data), [])

    def test_an_unknown_status_or_kind_is_refused(self):
        data = sample()
        data["items"][1]["status"] = "meh"
        data["subject"]["kind"] = "wiki"
        errors = report.validate(data)
        self.assertTrue(any("meh" in e for e in errors) and any("wiki" in e for e in errors))

    def test_a_report_without_items_or_with_a_bad_date_is_refused(self):
        data = sample()
        data["items"], data["date"] = [], "15/11/2026"
        errors = report.validate(data)
        self.assertTrue(any("items" in e for e in errors) and any("date" in e for e in errors))

    def test_something_that_is_not_an_object_is_refused_without_a_crash(self):
        self.assertTrue(report.validate([]))
        self.assertTrue(report.validate({"subject": "x", "date": "2026-11-15", "source": "s", "items": ["x"]}))


class SummaryTests(unittest.TestCase):
    def test_counts_by_status_and_the_first_advices_blockers_first(self):
        data = sample()
        data["items"].append({"scope": "s", "expected": "e", "observed": "o", "advice": "Move",
                              "status": "gap", "evidence": ["a:1"]})
        data["items"].reverse()
        s = report.summarize(data)
        self.assertEqual(s["counts"], {"blocker": 1, "gap": 1, "todo": 1, "unknown": 0, "ok": 1})
        self.assertEqual([a["advice"] for a in s["first"]],
                         ["Protect the branch", "Move", "Write the subcommand and its test"])


class HtmlTests(unittest.TestCase):
    def setUp(self):
        self.html = report.render_html(sample())

    def test_same_input_same_bytes(self):
        self.assertEqual(self.html, report.render_html(sample()))

    def test_the_four_headings_and_every_text_are_there(self):
        for label in ("What is evaluated", "Expected", "Observed", "Advice"):
            self.assertIn(label, self.html)
        for item in sample()["items"]:
            self.assertIn(item["scope"].replace("'", "&#x27;"), self.html)
        self.assertIn("SKILL.md:12", self.html)
        self.assertIn("PUSH_DOWN", self.html)

    def test_text_from_the_input_is_escaped_everywhere(self):
        data = sample()
        attack = '<script>alert(1)</script><img src=x onerror=alert(2)>'
        data["subject"]["name"] = data["summary"] = data["items"][0]["observed"] = attack
        data["items"][0]["evidence"] = [attack]
        html = report.render_html(data)
        self.assertNotIn("<script>alert(1)", html)
        self.assertNotIn("<img src=x", html)

    def test_the_embedded_data_cannot_close_its_script_block(self):
        data = sample()
        data["summary"] = "</script><script>alert(1)</script><!--"
        html = report.render_html(data)
        block = re.search(r'<script type="application/json" id="report-data">(.*?)</script>', html, re.S).group(1)
        self.assertNotIn("</", block)
        self.assertNotIn("<!--", block)
        self.assertEqual(json.loads(block)["summary"], data["summary"])

    def test_the_file_is_self_contained_and_locked_by_a_csp(self):
        self.assertNotRegex(self.html, r'(src|href)="https?://')
        csp = re.search(r'http-equiv="Content-Security-Policy" content="([^"]+)"', self.html).group(1)
        self.assertIn("default-src 'none'", csp)
        self.assertNotIn("unsafe-inline", csp)
        for tag in ("style", "script"):
            body = re.search(rf"<{tag}>(.*?)</{tag}>", self.html, re.S).group(1)
            digest = base64.b64encode(hashlib.sha256(body.encode("utf-8")).digest()).decode()
            self.assertIn(f"'sha256-{digest}'", csp)

    def test_it_reads_without_javascript(self):
        # The filters only appear if the script runs; no card is hidden at the start.
        self.assertRegex(self.html, r'<nav[^>]*\bhidden\b')
        self.assertNotRegex(self.html, r'<article[^>]*\bhidden\b')

    def test_it_declares_language_viewport_and_both_themes(self):
        self.assertIn('<html lang="en">', self.html)
        self.assertIn('name="viewport"', self.html)
        self.assertIn("prefers-color-scheme: dark", self.html)
        self.assertIn("@media print", self.html)

    def test_an_invalid_report_is_not_rendered(self):
        with self.assertRaises(ValueError):
            report.render_html(without(sample(), "items", "0", "evidence"))


class FromPlaceTests(unittest.TestCase):
    def _rows(self, pieces):
        return [place.place_piece(GRID, p) for p in pieces]

    def test_a_design_plan_becomes_things_to_create(self):
        pieces = [{"piece": "Compute the version", "answers": {"nature": "compute", "when": "on_demand"}}]
        data = report.from_place(GRID, pieces, self._rows(pieces), {"kind": "skill", "name": "release"}, "2026-11-15")
        self.assertEqual(report.validate(data), [])
        item = data["items"][0]
        self.assertEqual(item["status"], "todo")
        self.assertIn(GRID["destinations"]["cli"]["name"], item["expected"])

    def test_a_review_maps_verdicts_to_statuses_and_keeps_the_evidence(self):
        pieces = [
            {"piece": "Never push to main", "answers": {"nature": "limit", "bypass_limit": "dev"},
             "current": "agents_md", "evidence": ["AGENTS.md:14"]},
            {"piece": "How to make a release", "answers": {"nature": "procedure"}, "current": "skill"},
            {"piece": "The architecture", "answers": {"nature": "knowledge", "scope": "reference"},
             "current": "agents_md", "evidence": ["AGENTS.md:30"]},
        ]
        data = report.from_place(GRID, pieces, self._rows(pieces), {"kind": "repo", "name": "x"}, "2026-11-15")
        self.assertEqual(report.validate(data), [])
        self.assertEqual([(i["status"], i.get("tag")) for i in data["items"]],
                         [("blocker", "PUSH_DOWN"), ("ok", "KEEP"), ("gap", "MOVE")])
        self.assertEqual(data["items"][0]["evidence"], ["AGENTS.md:14"])

    def test_a_reviewed_piece_out_of_place_without_evidence_makes_the_report_invalid(self):
        pieces = [{"piece": "x", "answers": {"nature": "limit", "bypass_limit": "dev"}, "current": "agents_md"}]
        data = report.from_place(GRID, pieces, self._rows(pieces), {"kind": "repo", "name": "x"}, "2026-11-15")
        self.assertTrue(any("evidence" in e for e in report.validate(data)))

    def test_an_incomplete_piece_is_reported_as_not_evaluated(self):
        pieces = [{"piece": "Write the announcement", "answers": {"nature": "judgment"}}]
        data = report.from_place(GRID, pieces, self._rows(pieces), {"kind": "skill", "name": "x"}, "2026-11-15")
        self.assertEqual(data["items"][0]["status"], "unknown")
        self.assertIn(GRID["questions"]["isolation"]["text"], data["items"][0]["advice"])


def run_cli(*argv: str) -> tuple[int, str]:
    out = io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
        try:
            code = harness.main(list(argv))
        except SystemExit as exc:
            code = exc.code
    return code, out.getvalue()


class CliTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def _write(self, name: str, data) -> str:
        path = os.path.join(self.tmp.name, name)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(data, fh)
        return path

    def test_build_writes_the_html_file(self):
        out = os.path.join(self.tmp.name, "r.html")
        code, _ = run_cli("report", "build", self._write("r.json", sample()), "-o", out)
        self.assertEqual(code, 0)
        with open(out, encoding="utf-8") as fh:
            self.assertEqual(fh.read(), report.render_html(sample()))

    def test_build_refuses_an_invalid_report_and_writes_nothing(self):
        out = os.path.join(self.tmp.name, "r.html")
        code, _ = run_cli("report", "build", self._write("r.json", without(sample(), "date")), "-o", out)
        self.assertEqual(code, 2)
        self.assertFalse(os.path.exists(out))

    def test_from_place_builds_a_report_from_the_pieces_file(self):
        pieces = [{"piece": "Compute the version", "answers": {"nature": "compute", "when": "on_demand"}}]
        code, out = run_cli("report", "from-place", self._write("p.json", pieces), "--kind", "skill",
                            "--name", "release", "--date", "2026-11-15", "--format", "json")
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)["items"][0]["status"], "todo")


if __name__ == "__main__":
    unittest.main()
