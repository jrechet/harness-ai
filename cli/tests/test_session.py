"""Tests of `harness session`: the numbers of one Claude Code session, read by code and kept on the
machine, and the user's own words noted when something does not suit them. Nothing is sent anywhere.

The transcripts below are synthetic: they carry the keys the measure reads, and private-looking values
(a path, an account, a prompt) that must never come out."""
from __future__ import annotations

import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout

CLI_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, CLI_DIR)
from harness import main as harness_main  # noqa: E402
from harnesslib import session  # noqa: E402

SESSION = "11111111-2222-3333-4444-555555555555"
NOW = "2026-11-26T10:00:00Z"
PRIVATE_PATH = "/Users/someone/private-client"
PRIVATE_PROMPT = "please fix the billing of ACME"
PRIVATE_ACCOUNT = "acct-9f8e7d"


def assistant(message_id, output, skill=None, plugin=None, tools=(), model="claude-x", version="9.9.1",
              cache_read=0, input_tokens=0, cache_creation=0):
    content = [{"type": "text", "text": "some answer about " + PRIVATE_PATH}]
    content += [{"type": "tool_use", "id": tool_id, "name": name, "input": {"command": "cat " + PRIVATE_PATH}}
                for tool_id, name in tools]
    return {"type": "assistant", "sessionId": SESSION, "version": version, "cwd": PRIVATE_PATH,
            "gitBranch": "secret-branch", "timestamp": "2026-11-26T09:00:00Z", "attributionSkill": skill,
            "attributionPlugin": plugin, "isSidechain": False,
            "message": {"id": message_id, "model": model, "content": content,
                        "usage": {"input_tokens": input_tokens, "output_tokens": output,
                                  "cache_read_input_tokens": cache_read,
                                  "cache_creation_input_tokens": cache_creation}}}


def human(text=PRIVATE_PROMPT, timestamp="2026-11-26T08:59:00Z"):
    return {"type": "user", "sessionId": SESSION, "origin": {"kind": "human"}, "promptSource": "typed",
            "cwd": PRIVATE_PATH, "timestamp": timestamp, "entrypoint": "cli",
            "message": {"role": "user", "content": text}}


def tool_result(tool_id, error=False, denial=None):
    return {"type": "user", "sessionId": SESSION, "timestamp": "2026-11-26T09:00:30Z", "toolDenialKind": denial,
            "message": {"role": "user", "content": [{"type": "tool_result", "tool_use_id": tool_id,
                                                     "is_error": error, "content": "output with " + PRIVATE_PATH}]}}


def cost_state(cost=1.25, output=900):
    return {"type": "cost-state", "sessionId": SESSION, "totalCostUSD": cost, "totalDuration": 600000,
            "totalAPIDuration": 120000, "totalToolDuration": 30000, "totalLinesAdded": 40, "totalLinesRemoved": 5,
            "hasUnknownModelCost": False,
            "modelUsage": {"claude-x": {"inputTokens": 10, "outputTokens": output, "cacheReadInputTokens": 5000,
                                        "cacheCreationInputTokens": 200, "costUSD": cost}}}


FULL = [
    {"type": "bridge-session", "sessionId": SESSION, "ownerAccountUuid": PRIVATE_ACCOUNT},
    human(),
    assistant("m1", 100, tools=[("t1", "Bash"), ("t2", "Read")]),
    assistant("m1", 100, tools=[("t1", "Bash"), ("t2", "Read")]),        # the same message written twice
    tool_result("t1"),
    tool_result("t2", error=True),
    assistant("m2", 300, skill="harness-ai:harness-step", plugin="harness-ai", tools=[("t3", "Bash")], cache_read=4000),
    tool_result("t3", error=True, denial="user-rejected"),
    {"type": "user", "sessionId": SESSION, "origin": {"kind": "task-notification"}, "message": {"content": "done"}},
    {"type": "user", "sessionId": SESSION, "isMeta": True, "message": {"content": "a reminder"}},
    {"type": "system", "subtype": "compact_boundary", "sessionId": SESSION},
    {"type": "system", "subtype": "api_error", "sessionId": SESSION},
    cost_state(cost=0.5, output=400),
    human("second prompt", "2026-11-26T09:20:00Z"),
    assistant("m3", 200, skill="harness-ai:harness-step", plugin="harness-ai", version="9.9.2"),
    cost_state(),
    "this line is not JSON",
]
SUBAGENT = [assistant("s1", 250, skill="harness-ai:harness-audit", plugin="harness-ai", cache_read=1000),
            assistant("m3", 200, skill="harness-ai:harness-step", plugin="harness-ai")]      # already counted


class SessionCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = os.path.realpath(self._tmp.name)
        self.repo = os.path.join(self.root, "repo")
        self.projects = os.path.join(self.root, "projects")
        os.makedirs(self.repo)

    def transcript(self, rows, session_id=SESSION, project="-some-project", subagents=()):
        folder = os.path.join(self.projects, project)
        os.makedirs(folder, exist_ok=True)
        path = os.path.join(folder, session_id + ".jsonl")
        if session_id != SESSION:                 # the rows of a session carry its own id
            rows = [{**row, "sessionId": session_id} if isinstance(row, dict) else row for row in rows]
        self.write_rows(path, rows)
        for index, sub_rows in enumerate(subagents):
            sub = os.path.join(folder, session_id, "subagents", "workflows", "wf_1" if index else "")
            os.makedirs(sub, exist_ok=True)
            self.write_rows(os.path.join(sub, f"agent-a{index}.jsonl"), sub_rows)
        return path

    @staticmethod
    def write_rows(path, rows):
        with open(path, "w", encoding="utf-8") as fh:
            for row in rows:
                fh.write((row if isinstance(row, str) else json.dumps(row)) + "\n")

    def run_cli(self, *argv, env=None):
        out, err = io.StringIO(), io.StringIO()
        old = os.environ.get(session.SESSION_ENV)
        os.environ.pop(session.SESSION_ENV, None)
        if env:
            os.environ[session.SESSION_ENV] = env
        try:
            with redirect_stdout(out), redirect_stderr(err):
                code = harness_main(["session", *argv])
        finally:
            os.environ.pop(session.SESSION_ENV, None)
            if old is not None:
                os.environ[session.SESSION_ENV] = old
        return code, out.getvalue(), err.getvalue()

    def measure(self, *extra, env=None):
        return self.run_cli("measure", "--repo", self.repo, "--projects-dir", self.projects, "--now", NOW, *extra, env=env)

    def stored(self, session_id=SESSION):
        with open(os.path.join(self.repo, ".harness", "session", session_id + ".json"), encoding="utf-8") as fh:
            return json.load(fh)


class MeasureTests(SessionCase):
    def test_the_measure_counts_what_the_session_holds(self):
        self.transcript(FULL, subagents=[SUBAGENT])
        code, out, err = self.measure("--session", SESSION)
        self.assertEqual(code, 0, err)
        data = self.stored()
        self.assertEqual(data["schema"], "harness-session/1")
        self.assertEqual(data["status"], "measured")
        self.assertEqual(data["session"], SESSION)
        self.assertEqual(data["measured_at"], NOW)
        self.assertEqual(data["claude_code_versions"], ["9.9.1", "9.9.2"])
        self.assertEqual(data["counts"], {"human_prompts": 2, "assistant_messages": 4, "tool_calls": 3,
                                          "tool_errors": 2, "denials": {"user-rejected": 1}, "compactions": 1,
                                          "api_errors": 1, "subagent_files": 1})

    def test_a_message_written_twice_or_in_two_files_is_counted_once(self):
        self.transcript(FULL, subagents=[SUBAGENT])
        self.measure("--session", SESSION)
        skills = {row["skill"]: row for row in self.stored()["by_skill"]}
        self.assertEqual(skills["harness-ai:harness-step"]["output_tokens"], 500)
        self.assertEqual(skills["harness-ai:harness-step"]["messages"], 2)
        self.assertEqual(skills["harness-ai:harness-audit"]["output_tokens"], 250)
        self.assertEqual(skills[None]["output_tokens"], 100)
        self.assertEqual(self.stored()["rows"]["output_tokens"], 850)

    def test_the_skills_are_listed_costliest_first_with_their_plugin(self):
        self.transcript(FULL, subagents=[SUBAGENT])
        self.measure("--session", SESSION)
        listed = self.stored()["by_skill"]
        self.assertEqual([row["skill"] for row in listed], ["harness-ai:harness-step", "harness-ai:harness-audit", None])
        self.assertEqual(listed[0]["plugin"], "harness-ai")
        self.assertEqual(listed[0]["cache_read_tokens"], 4000)
        self.assertEqual(listed[0]["tool_calls"], 1)

    def test_the_totals_are_the_last_ones_claude_code_recorded(self):
        self.transcript(FULL)
        self.measure("--session", SESSION)
        totals = self.stored()["totals"]
        self.assertEqual(totals["source"], "claude-code")
        self.assertEqual(totals["cost_usd_estimate"], 1.25)
        self.assertEqual(totals["output_tokens"], 900)
        self.assertEqual(totals["cache_read_tokens"], 5000)
        self.assertEqual(totals["duration_s"], 600)
        self.assertEqual(totals["api_duration_s"], 120)
        self.assertEqual(totals["lines_added"], 40)
        self.assertEqual(totals["by_model"], {"claude-x": {"output_tokens": 900, "cost_usd_estimate": 1.25}})

    def test_without_recorded_totals_the_measure_is_partial_and_gives_no_cost(self):
        self.transcript([row for row in FULL if not (isinstance(row, dict) and row.get("type") == "cost-state")])
        code, out, _ = self.measure("--session", SESSION)
        self.assertEqual(code, 0)
        data = self.stored()
        self.assertEqual(data["status"], "partial")
        self.assertEqual(data["totals"]["source"], "rows")
        self.assertIsNone(data["totals"]["cost_usd_estimate"])
        self.assertEqual(data["totals"]["output_tokens"], 600)
        self.assertIn("partial", out)

    def test_nothing_private_comes_out(self):
        self.transcript(FULL, subagents=[SUBAGENT])
        _, out, _ = self.measure("--session", SESSION)
        with open(os.path.join(self.repo, ".harness", "session", SESSION + ".json"), encoding="utf-8") as fh:
            written = fh.read()
        for private in (PRIVATE_PATH, PRIVATE_PROMPT, PRIVATE_ACCOUNT, "secret-branch", "second prompt", self.root):
            self.assertNotIn(private, written)
            self.assertNotIn(private, out)

    def test_only_the_keys_of_the_allowlist_are_written(self):
        self.transcript(FULL, subagents=[SUBAGENT])
        self.measure("--session", SESSION)
        data = self.stored()
        self.assertEqual(set(data), session.REPORT_KEYS)
        for row in data["by_skill"]:
            self.assertEqual(set(row), session.SKILL_KEYS)

    def test_the_session_folder_is_ignored_by_git(self):
        self.transcript(FULL)
        self.measure("--session", SESSION)
        with open(os.path.join(self.repo, ".harness", "session", ".gitignore"), encoding="utf-8") as fh:
            self.assertEqual(fh.read().split(), ["*"])

    def test_the_text_says_the_numbers_and_that_dollars_are_an_estimate(self):
        self.transcript(FULL, subagents=[SUBAGENT])
        _, out, _ = self.measure("--session", SESSION)
        self.assertIn("2 prompts from you", out)
        self.assertIn("harness-ai:harness-step", out)
        self.assertIn("estimate", out)
        self.assertIn(".harness/session/" + SESSION + ".json", out)
        self.assertNotIn(self.repo, out)

    def test_json_format_prints_what_is_stored(self):
        self.transcript(FULL)
        _, out, _ = self.measure("--session", SESSION, "--format", "json")
        self.assertEqual(json.loads(out), self.stored())

    def test_measuring_again_replaces_the_file_of_that_session_only(self):
        self.transcript(FULL)
        other = "99999999-2222-3333-4444-555555555555"
        self.transcript([human(), assistant("o1", 7)], session_id=other)
        self.measure("--session", SESSION)
        self.measure("--session", other)
        self.measure("--session", SESSION)
        self.assertEqual(self.stored(other)["rows"]["output_tokens"], 7)
        self.assertEqual(self.stored()["rows"]["output_tokens"], 600)


class WhichSessionTests(SessionCase):
    def test_the_running_session_is_taken_from_the_environment(self):
        self.transcript(FULL)
        code, _, err = self.measure(env=SESSION)
        self.assertEqual(code, 0, err)
        self.assertEqual(self.stored()["session"], SESSION)

    def test_no_session_named_and_none_running_is_refused_without_a_guess(self):
        self.transcript(FULL)
        code, out, err = self.measure()
        self.assertEqual(code, 2)
        self.assertIn("--session", err)
        self.assertFalse(os.path.exists(os.path.join(self.repo, ".harness")))

    def test_an_unknown_session_is_refused_in_one_sentence(self):
        code, _, err = self.measure("--session", "00000000-0000-0000-0000-000000000000")
        self.assertEqual(code, 2)
        self.assertEqual(len(err.strip().splitlines()), 1)
        self.assertNotIn("Traceback", err)

    def test_a_session_id_that_is_a_path_is_refused(self):
        code, _, err = self.measure("--session", "../../etc/passwd")
        self.assertEqual(code, 2)
        self.assertIn("not a session id", err)

    def test_a_transcript_can_be_given_by_its_path(self):
        path = self.transcript(FULL)
        code, _, err = self.measure("--transcript", path)
        self.assertEqual(code, 0, err)
        self.assertEqual(self.stored()["counts"]["human_prompts"], 2)

    def test_the_same_id_in_two_projects_is_refused(self):
        self.transcript(FULL)
        self.transcript(FULL, project="-another-project")
        code, _, err = self.measure("--session", SESSION)
        self.assertEqual(code, 2)
        self.assertIn("--transcript", err)

    def test_a_repo_that_is_not_a_directory_is_refused(self):
        code, _, err = self.run_cli("measure", "--repo", os.path.join(self.root, "nope"), "--session", SESSION)
        self.assertEqual(code, 2)


class DriftTests(SessionCase):
    """The transcript format is internal to Claude Code and changes: a wrong number is worse than none."""

    def test_messages_without_usage_are_unmeasured_not_zero(self):
        rows = [human(), {"type": "assistant", "sessionId": SESSION, "message": {"id": "m1", "content": []}}]
        self.transcript(rows)
        code, out, _ = self.measure("--session", SESSION)
        self.assertEqual(code, 1)
        data = self.stored()
        self.assertEqual(data["status"], "unmeasured")
        self.assertIn("usage", data["reason"])
        self.assertIsNone(data["totals"])
        self.assertEqual(data["by_skill"], [])
        self.assertIn("unmeasured", out)

    def test_a_file_with_no_assistant_message_is_unmeasured(self):
        self.transcript([human()])
        code, _, _ = self.measure("--session", SESSION)
        self.assertEqual(code, 1)
        self.assertEqual(self.stored()["status"], "unmeasured")

    def test_prompts_with_no_origin_are_not_counted_as_zero(self):
        rows = [{"type": "user", "sessionId": SESSION, "message": {"content": "hello"}}, assistant("m1", 5)]
        self.transcript(rows)
        self.measure("--session", SESSION)
        data = self.stored()
        self.assertIsNone(data["counts"]["human_prompts"])
        self.assertEqual(data["status"], "partial")
        self.assertIn("human", data["reason"])

    def test_recorded_totals_of_another_shape_are_not_trusted(self):
        rows = [human(), assistant("m1", 5), {"type": "cost-state", "sessionId": SESSION, "totalCostUSD": "a lot"}]
        self.transcript(rows)
        self.measure("--session", SESSION)
        data = self.stored()
        self.assertEqual(data["totals"]["source"], "rows")
        self.assertEqual(data["status"], "partial")

    def test_an_empty_or_binary_file_does_not_crash(self):
        path = self.transcript([])
        with open(path, "wb") as fh:
            fh.write(b"\xff\xfe\x00\x00not json\n[1, 2]\n\"text\"\n")
        code, _, err = self.measure("--session", SESSION)
        self.assertEqual(code, 1)
        self.assertNotIn("Traceback", err)

    def test_the_rows_and_the_recorded_totals_are_both_kept_to_compare(self):
        self.transcript(FULL)
        self.measure("--session", SESSION)
        data = self.stored()
        self.assertEqual(data["rows"]["output_tokens"], 600)
        self.assertEqual(data["totals"]["output_tokens"], 900)


class ForkAndLateTotalsTests(SessionCase):
    """Seen on real sessions: a fork starts with a copy of its parent, and the totals may start late."""
    FORK = "77777777-2222-3333-4444-555555555555"

    def fork(self):
        own = [{**human("in the fork"), "sessionId": self.FORK}, {**assistant("f1", 40), "sessionId": self.FORK},
               {**cost_state(cost=9.0, output=5000), "sessionId": self.FORK}]
        folder = os.path.join(self.projects, "-some-project")
        os.makedirs(folder, exist_ok=True)
        path = os.path.join(folder, self.FORK + ".jsonl")
        self.write_rows(path, [row for row in FULL if isinstance(row, dict)] + own)
        copied = os.path.join(folder, self.FORK, "subagents")
        os.makedirs(copied)
        self.write_rows(os.path.join(copied, "agent-parent.jsonl"), SUBAGENT)          # the parent's, copied
        self.write_rows(os.path.join(copied, "agent-own.jsonl"), [{**assistant("f2", 60), "sessionId": self.FORK}])
        return path

    def test_a_fork_counts_its_own_rows_only(self):
        self.fork()
        code, out, _ = self.measure("--session", self.FORK)
        self.assertEqual(code, 0)
        data = self.stored(self.FORK)
        self.assertEqual(data["counts"]["human_prompts"], 1)
        self.assertEqual(data["rows"]["output_tokens"], 100)          # 40 of its own, 60 of its own sub-agent
        self.assertEqual(data["counts"]["subagent_files"], 1)
        self.assertEqual(data["status"], "partial")
        self.assertIn("forked", data["reason"])

    def test_a_fork_does_not_take_the_totals_that_count_its_parent(self):
        self.fork()
        self.measure("--session", self.FORK)
        totals = self.stored(self.FORK)["totals"]
        self.assertEqual(totals["source"], "rows")
        self.assertIsNone(totals["cost_usd_estimate"])
        self.assertEqual(totals["output_tokens"], 100)

    def test_totals_that_started_late_are_said_to_be_a_minimum(self):
        self.transcript([human(), assistant("m1", 5000), assistant("m2", 5000), cost_state(cost=0.4, output=900)])
        _, out, _ = self.measure("--session", SESSION)
        data = self.stored()
        self.assertEqual(data["status"], "partial")
        self.assertIn("minimum", data["reason"])
        self.assertEqual(data["totals"]["cost_usd_estimate"], 0.4)

    def test_rows_below_the_totals_are_not_a_fault(self):
        self.transcript(FULL)                      # 600 in the rows, 900 recorded: calls the rows do not show
        self.measure("--session", SESSION)
        self.assertEqual(self.stored()["status"], "measured")

    def test_long_durations_are_told_in_hours(self):
        rows = [human(), assistant("m1", 5), {**cost_state(), "totalDuration": 9 * 3600 * 1000}]
        self.transcript(rows)
        _, out, _ = self.measure("--session", SESSION)
        self.assertIn("open for 9.0 h", out)


class NoteTests(SessionCase):
    def notes(self):
        with open(os.path.join(self.repo, ".harness", "session", "notes.jsonl"), encoding="utf-8") as fh:
            return [json.loads(line) for line in fh]

    def test_a_note_keeps_the_words_as_given_with_the_time_and_the_session(self):
        code, out, err = self.run_cli("note", "the step asked me twice — pas clair", "--repo", self.repo, "--now", NOW, env=SESSION)
        self.assertEqual(code, 0, err)
        self.assertEqual(self.notes(), [{"at": NOW, "session": SESSION, "note": "the step asked me twice — pas clair"}])
        self.assertIn("kept on this machine", out)

    def test_notes_add_up_and_never_replace(self):
        for text in ("first", "second"):
            self.run_cli("note", text, "--repo", self.repo, "--now", NOW)
        self.assertEqual([n["note"] for n in self.notes()], ["first", "second"])
        self.assertIsNone(self.notes()[0]["session"])

    def test_an_empty_note_is_refused(self):
        code, _, err = self.run_cli("note", "   ", "--repo", self.repo)
        self.assertEqual(code, 2)
        self.assertFalse(os.path.exists(os.path.join(self.repo, ".harness")))

    def test_the_notes_folder_is_ignored_by_git(self):
        self.run_cli("note", "x", "--repo", self.repo, "--now", NOW)
        self.assertTrue(os.path.exists(os.path.join(self.repo, ".harness", "session", ".gitignore")))

    def test_the_measure_shows_the_notes_of_its_session(self):
        self.transcript(FULL)
        self.run_cli("note", "too many questions", "--repo", self.repo, "--now", NOW, env=SESSION)
        self.run_cli("note", "another session", "--repo", self.repo, "--now", NOW, env="99999999-2222-3333-4444-555555555555")
        _, out, _ = self.measure("--session", SESSION)
        self.assertIn("too many questions", out)
        self.assertNotIn("another session", out)
        self.assertNotIn("notes", self.stored())


class ListTests(SessionCase):
    def test_the_list_shows_one_line_per_measured_session(self):
        self.transcript(FULL)
        other = "99999999-2222-3333-4444-555555555555"
        self.transcript([human(), assistant("o1", 7)], session_id=other)
        self.measure("--session", SESSION)
        self.measure("--session", other)
        code, out, _ = self.run_cli("list", "--repo", self.repo)
        self.assertEqual(code, 0)
        self.assertIn(SESSION[:8], out)
        self.assertIn(other[:8], out)
        self.assertIn("2 sessions measured", out)

    def test_an_empty_list_says_how_to_start(self):
        code, out, _ = self.run_cli("list", "--repo", self.repo)
        self.assertEqual(code, 0)
        self.assertIn("harness session measure", out)

    def test_a_broken_file_is_named_and_does_not_hide_the_others(self):
        self.transcript(FULL)
        self.measure("--session", SESSION)
        with open(os.path.join(self.repo, ".harness", "session", "broken.json"), "w", encoding="utf-8") as fh:
            fh.write("{")
        code, out, _ = self.run_cli("list", "--repo", self.repo)
        self.assertEqual(code, 0)
        self.assertIn("broken.json", out)
        self.assertIn(SESSION[:8], out)


if __name__ == "__main__":
    unittest.main()
