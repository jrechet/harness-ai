"""How `harness flow` reads the files it is given (docs/workflow-harness/flow-spec.md, sections 2
and 12.4): a definition, an event or a run that writes one key twice in an object does not say one
thing, so it is refused, exit 2, as `flow fit` refuses such answers; and `flow new` with
`--format json` answers with a document, also when it leaves an existing file as it is."""
from __future__ import annotations

import contextlib
import io
import json
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import harness  # noqa: E402
from harnesslib import flow  # noqa: E402
from tests import flow_fixture_files as files  # noqa: E402

TWICE = ('the key "{key}" is written twice in one object; JSON keeps only the last one, without a word. Write it '
         "once.")


def call(*argv: str) -> tuple[int, str, str]:
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            code = harness.main(["flow", *argv])
        except SystemExit as exc:
            code = exc.code
    return code, out.getvalue(), err.getvalue()


def merge_written_twice() -> str:
    """The text of a flow with no gate before its merge, whose merge transition is written twice: the
    copy that carries "reaches" first, the one JSON keeps last."""
    definition = files.answered_template("feature")
    for name in ("human_review", "rework", "merge_auth"):
        del definition["states"][name]
    definition["states"]["mark_ready"]["on"]["marked_ready"] = {"to": "merging", "reaches": "ready_pr"}
    text = json.dumps(definition, indent=1)
    kept = '"merged": {\n     "to": "delivery",\n     "reaches": "merged"\n    }'
    if kept not in text:
        raise AssertionError("the feature definition no longer has the merge transition this test rewrites")
    return text.replace(kept, kept + ',\n    "merged": {"to": "delivery"}')


class KeyWrittenTwiceTest(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.folder)

    def write(self, name: str, text: str) -> str:
        path = os.path.join(self.folder, name)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text)
        return path

    def test_a_definition_that_writes_a_key_twice_is_refused_by_every_command_that_reads_it(self):
        path = self.write("dup.json", merge_written_twice())
        expected = f"flow: {path}: {TWICE.format(key='merged')}\n"
        for argv in (["check", path], ["place", path], ["status", path], ["status", path, "--map"],
                     ["check", path, "--format", "json"], ["place", path, "--format", "json"]):
            with self.subTest(argv=argv[0:1] + argv[2:]):
                self.assertEqual(call(*argv), (2, "", expected))

    def test_the_same_text_without_the_repeat_is_refused_for_its_merge(self):
        text = merge_written_twice().replace(',\n    "merged": {"to": "delivery"}', "")
        code, out, _ = call("check", self.write("once.json", text))
        self.assertEqual(code, 1)
        self.assertIn("(states.merging.on.merged)", out)

    def test_an_event_that_writes_a_key_twice_is_refused_too(self):
        definition = self.write("flow.json", json.dumps(files.answered_template("feature")))
        event = self.write("event.json", '{"id": "T-1:ready:1:claimed", "type": "claimed", "type": "not_eligible", '
                                         '"payload": {"dollars": 0, "minutes": 1}}')
        self.assertEqual(call("next", definition, "--event", event, "--new"),
                         (2, "", f"flow: {event}: {TWICE.format(key='type')}\n"))

    def test_load_definition_says_which_key(self):
        path = self.write("x.json", '{"a": 1, "b": {"c": 1, "c": 2}}')
        with self.assertRaises(ValueError) as caught:
            flow.load_definition(path)
        self.assertEqual(str(caught.exception), f"{path}: {TWICE.format(key='c')}")
        self.assertEqual(flow.load_definition(self.write("y.json", '{"a": 1, "b": {"c": 1}}')), {"a": 1, "b": {"c": 1}})


class NewWithJsonTest(unittest.TestCase):
    def test_flow_new_on_an_existing_file_answers_with_a_document_and_leaves_stderr_empty(self):
        folder = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, folder)
        path = os.path.join(folder, "feature.json")
        self.assertEqual(call("new", "feature", "--out", path, "--format", "json")[0], 0)
        with open(path, encoding="utf-8") as fh:
            before = fh.read()
        code, out, err = call("new", "feature", "--out", path, "--format", "json")
        self.assertEqual((code, err), (1, ""))
        self.assertEqual(json.loads(out), {"file": path, "written": False, "reason": "exists"})
        with open(path, encoding="utf-8") as fh:
            self.assertEqual(fh.read(), before)
        code, out, err = call("new", "feature", "--out", path)
        self.assertEqual((code, out), (1, ""))
        self.assertTrue(err.startswith(f"flow: {path} already exists and was left as it is. Add --force to replace it."))


if __name__ == "__main__":
    unittest.main()
