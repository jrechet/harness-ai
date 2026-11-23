"""Tests of the notes of `harness flow` (docs/workflow-harness/flow-spec.md, section 12.4): what a
person reads names commands and pages they can really use from their own repository. Stdout is
the same bytes on every machine, help included; what depends on the machine is in the closing
note, on stderr, after every other note, with `--format md` only and never on exit 2."""
from __future__ import annotations

import contextlib
import io
import json
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import harness  # noqa: E402
from harnesslib import flow_notes  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
HARNESS = os.path.join(ROOT, "cli", "harness.py")
FAMILY = os.path.join(ROOT, "fixtures", "flow")
FEATURE = os.path.join(FAMILY, "definitions", "feature.json")
FIT = os.path.join(FAMILY, "fit")
CLOSING = (f"Here \"flow\" is typed: python3 {shlex.quote(HARNESS)} flow. The pages (flow-format.md, decide.md, "
           f"costs.md, report.md, flow-spec.md) are in {os.path.join(ROOT, 'docs', 'workflow-harness')}.")
HELP_LAST = ("With --format md, every flow command that exits 0 or 1 ends, on stderr, with the full command as this "
             "installation runs it and the folder of the pages.")
SUBCOMMANDS = ("fit", "new", "check", "place", "status", "next")
EVENT = {"id": "T-1:ready:1:ticket_ready", "type": "ticket_ready", "payload": {"dollars": 0, "minutes": 1}}


def call(*argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            code = harness.main(["flow", *argv])
        except SystemExit as exc:
            code = exc.code
    return code, out.getvalue(), err.getvalue()


class ClosingNoteTest(unittest.TestCase):
    def test_the_closing_note_names_the_running_copy_and_its_pages(self):
        self.assertEqual(flow_notes.closing(), CLOSING)

    def test_the_closing_note_never_names_the_current_folder(self):
        here, elsewhere = os.getcwd(), tempfile.mkdtemp()
        try:
            os.chdir(elsewhere)
            self.assertEqual(flow_notes.closing(), CLOSING)
            self.assertTrue(call("check", FEATURE)[2].endswith(CLOSING + "\n"))
            self.assertNotIn(os.path.realpath(elsewhere), flow_notes.closing())
        finally:
            os.chdir(here)
            shutil.rmtree(elsewhere)

    def test_a_copy_run_through_a_link_is_named_by_the_link(self):
        folder = tempfile.mkdtemp()
        try:
            link = os.path.join(folder, "linked copy")
            os.makedirs(link)
            os.symlink(os.path.join(ROOT, "cli"), os.path.join(link, "cli"))
            os.symlink(os.path.join(ROOT, "docs"), os.path.join(link, "docs"))
            done = subprocess.run([sys.executable, os.path.join(link, "cli", "harness.py"), "flow", "fit", "--questions"],
                                  capture_output=True, text=True, cwd=folder, check=False)
            self.assertEqual(done.returncode, 0, done.stderr)
            self.assertEqual(done.stderr.splitlines()[-1], flow_notes.closing(link))
            self.assertIn(shlex.quote(os.path.join(link, "cli", "harness.py")), done.stderr)
        finally:
            shutil.rmtree(folder)

    def test_only_the_command_is_quoted_and_a_copy_without_pages_says_so(self):
        folder = tempfile.mkdtemp(prefix="with space ")
        try:
            self.assertEqual(flow_notes.closing(folder),
                             f"Here \"flow\" is typed: python3 {shlex.quote(os.path.join(folder, 'cli', 'harness.py'))} "
                             "flow. The pages are not installed with this copy.")
            os.makedirs(os.path.join(folder, "docs", "workflow-harness"))
            self.assertTrue(flow_notes.closing(folder).endswith(
                f" The pages (flow-format.md, decide.md, costs.md, report.md, flow-spec.md) are in "
                f"{os.path.join(folder, 'docs', 'workflow-harness')}."))
            self.assertIn("'", flow_notes.closing(folder))
        finally:
            shutil.rmtree(folder)


class EveryCommandTest(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.folder)

    def write(self, name, value):
        path = os.path.join(self.folder, name)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(value, fh)
        return path

    def commands(self):
        """Every command, on an input where it exits 0 and on one where it exits 1."""
        written = os.path.join(self.folder, "new.json")
        event = self.write("event.json", EVENT)
        stray = self.write("stray.json", {**EVENT, "type": "nobody_sends_this"})
        broken = self.write("broken.json", {"format": 1})
        return [("fit", os.path.join(FIT, "symptom-fired", "answers.json")),
                ("fit", os.path.join(FIT, "refused", "answers.json")), ("fit", "--questions"),
                ("new", "bug", "--out", written), ("new", "bug", "--out", written),
                ("check", FEATURE), ("check", broken), ("place", FEATURE), ("place", written),
                ("status", FEATURE), ("status", written, "--map"),
                ("next", FEATURE, "--event", event, "--new"), ("next", FEATURE, "--event", stray, "--new")]

    def test_every_command_that_exits_0_or_1_ends_with_the_closing_note(self):
        codes = set()
        for argv in self.commands():
            with self.subTest(argv=argv):
                code, _, err = call(*argv)
                codes.add(code)
                self.assertIn(code, (0, 1))
                self.assertEqual(err.splitlines()[-1], CLOSING)
                self.assertEqual(err.count(CLOSING), 1)
                for line in err.splitlines()[:-1]:
                    self.assertNotIn("harness.py", line)
                    self.assertNotIn("docs/workflow-harness", line)
        self.assertEqual(codes, {0, 1})

    def test_json_leaves_stderr_empty_and_exit_2_has_no_closing_note(self):
        for argv in self.commands():
            if argv[0] == "new":
                call(*argv, "--format", "json")  # the file the next commands read
                continue
            if argv[-1] == "--questions":
                continue
            with self.subTest(argv=argv):
                self.assertEqual(call(*argv, "--format", "json")[2], "")
        missing = os.path.join(self.folder, "nowhere.json")
        for argv in (("check", missing), ("place", missing), ("status", missing), ("fit", missing), ("fit",)):
            with self.subTest(argv=argv):
                code, _, err = call(*argv)
                self.assertEqual(code, 2)
                self.assertNotIn(CLOSING, err)

    def test_the_next_note_of_flow_fit_names_where_flow_new_writes(self):
        _, _, err = call("fit", os.path.join(FIT, "ticket-state-and-ci", "answers.json"))
        self.assertEqual(err.splitlines(), [
            "Next: flow new feature --out .harness/flow/feature.json writes a starting definition under the current "
            f"folder, {os.path.abspath(os.getcwd())}, and never replaces a file. For a bug flow: flow new bug --out "
            ".harness/flow/bug.json.", CLOSING])
        # Since the critics of section 12: a symptom verdict says that flow place and flow status read the answers.
        fired = os.path.join(FIT, "symptom-fired", "answers.json")
        self.assertEqual(call("fit", fired)[2].splitlines(), [
            f"Next: with a flow definition, flow place <file> --answers {fired} reads these symptoms beside it; flow "
            "new feature --out .harness/flow/feature.json writes one.", CLOSING])

    def test_the_next_note_of_flow_new_names_the_page_by_its_file_name(self):
        path = os.path.join(self.folder, "f.json")
        _, _, err = call("new", "feature", "--out", path)
        self.assertIn(f"Next: edit {path} (every key is explained in the page flow-format.md), then flow check {path}, "
                      f"flow place {path}, flow status {path} --map.", err.splitlines())

    def test_the_notes_of_flow_place_come_in_the_order_of_the_contract(self):
        _, _, err = call("place", FEATURE)
        lines = err.splitlines()
        self.assertEqual(lines[-3:], [
            "Measured symptoms were not read: this answer comes from the file alone. To read them, add --answers "
            "<the answers file given to flow fit>.", f"Next: flow status {FEATURE} --map", CLOSING])


class PasteTest(unittest.TestCase):
    """Every command a note names is safe to paste: a path with a space is quoted for a shell."""

    def setUp(self):
        self.folder = tempfile.mkdtemp(prefix="with space ")
        self.addCleanup(shutil.rmtree, self.folder)

    def test_the_paths_in_the_notes_are_quoted_for_a_shell(self):
        flow_file, answers = os.path.join(self.folder, "my flow.json"), os.path.join(self.folder, "my answers.json")
        shutil.copy(os.path.join(FIT, "symptom-fired", "answers.json"), answers)
        _, _, err = call("new", "feature", "--out", flow_file)
        quoted, quoted_answers = shlex.quote(flow_file), shlex.quote(answers)
        self.assertIn(f"Next: edit {flow_file} (every key is explained in the page flow-format.md), then flow check "
                      f"{quoted}, flow place {quoted}, flow status {quoted} --map.", err.splitlines())
        shutil.copy(FEATURE, flow_file)
        _, _, err = call("place", flow_file, "--answers", answers)
        self.assertIn(f"Next: flow status {quoted} --map --answers {quoted_answers}", err.splitlines())
        self.assertIn(f"flow fit {quoted_answers} gives the smallest fix to try first for each.", err)
        _, _, err = call("check", flow_file)
        self.assertIn(f"Next: flow place {quoted} says where each step belongs. This command does not look at that.",
                      err.splitlines())

    def test_a_plain_path_is_printed_as_it_is(self):
        self.assertEqual(flow_notes.with_answers("a.json"), " --answers a.json")
        self.assertEqual(flow_notes.place_next_waiting("f.json"), "Next: flow status f.json --map shows what level 1 "
                                                                  "still needs.")


class SymptomNoteTest(unittest.TestCase):
    def test_the_smallest_fix_is_offered_only_when_a_symptom_fired(self):
        for name, offered in (("symptom-fired", True), ("ticket-state-and-ci", False), ("nothing-measured", False)):
            with self.subTest(answers=name):
                _, _, err = call("place", FEATURE, "--answers", os.path.join(FIT, name, "answers.json"))
                note = [line for line in err.splitlines() if line.startswith("Symptoms read from ")]
                self.assertEqual(len(note), 1)
                self.assertIs("gives the smallest fix" in note[0], offered, note[0])

    def test_the_level_0_note_of_flow_status_keeps_the_answers(self):
        answers = os.path.join(FIT, "symptom-fired", "answers.json")
        folder = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, folder)
        fresh = os.path.join(folder, "f.json")
        call("new", "feature", "--out", fresh)
        _, _, err = call("status", fresh, "--answers", answers)
        self.assertIn(f"Every reason, and the levels: flow status {fresh} --map --answers {answers}", err.splitlines())
        self.assertIn(f"Every reason, and the levels: flow status {fresh} --map", call("status", fresh)[2].splitlines())


class OrderTest(unittest.TestCase):
    def test_flow_check_prints_the_waiting_note_before_the_careful_note(self):
        folder = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, folder)
        with open(FEATURE, encoding="utf-8") as fh:
            definition = json.load(fh)
        del definition["states"]["merge_auth"]["can_judge"]  # a gate that waits
        definition["states"]["coding"]["weak_model"] = "maybe"  # and a step with no place
        path = os.path.join(folder, "f.json")
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(definition, fh)
        code, _, err = call("check", path)
        self.assertEqual(code, 0)
        lines = err.splitlines()
        waiting = [n for n, line in enumerate(lines) if line.startswith("1 approval waits")]
        careful = [n for n, line in enumerate(lines) if line.startswith(f"Careful: flow place {path}")]
        self.assertEqual((len(waiting), len(careful)), (1, 1), lines)
        self.assertLess(waiting[0], careful[0])


class HelpTest(unittest.TestCase):
    def help_of(self, *argv, columns="80"):
        env = {**os.environ, "COLUMNS": columns}
        done = subprocess.run([sys.executable, HARNESS, "flow", *argv, "--help"], capture_output=True, text=True,
                              env=env, cwd=ROOT, check=False)
        self.assertEqual(done.returncode, 0, done.stderr)
        return done.stdout

    def test_every_help_names_pages_by_file_name_and_ends_with_the_same_line(self):
        for sub in ("", *SUBCOMMANDS):
            with self.subTest(command=sub or "flow"):
                text = self.help_of(*([sub] if sub else []))
                self.assertNotIn("docs/workflow-harness", text)
                self.assertNotIn(ROOT, text)
                self.assertEqual(text.rstrip("\n").splitlines()[-1], HELP_LAST)

    def test_the_help_is_the_same_bytes_whatever_the_width_of_the_terminal(self):
        for sub in ("", *SUBCOMMANDS):
            with self.subTest(command=sub or "flow"):
                argv = [sub] if sub else []
                self.assertEqual(self.help_of(*argv, columns="40"), self.help_of(*argv, columns="220"))


if __name__ == "__main__":
    unittest.main()
