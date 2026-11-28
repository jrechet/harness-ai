"""Tests of `harness game`, the video-game profile: the data it ships holds together, the engine and its
version are read from the project files, each piece of the loop gets the state its files give, the judge
fails a run that exits 0 with an error line or never says it is ready, publishing is never recorded, the
instruction lines are filled from what is measured, and the level ladder measures the same with or without
the profile."""
from __future__ import annotations

import io
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from datetime import date

CLI_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, CLI_DIR)
from harness import main as harness_main  # noqa: E402
from harnesslib import facts, game, game_run, maturity  # noqa: E402

TODAY = date(2026, 11, 28)
GODOT = 'config_version=5\n[application]\nconfig/name="T"\nconfig/features=PackedStringArray("4.3", "Forward Plus")\n'
AGENTS = "# demo\n\nMode: **assistance**. A person drives every task.\n\n## Rules\n- Tests pass.\n\n## Forbidden\n- Force push.\n"
PY = sys.executable


def run_cli(*argv: str) -> tuple[int, str, str]:
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = harness_main(list(argv))
    return code, out.getvalue(), err.getvalue()


class Repo(unittest.TestCase):
    """A temporary repository, and helpers to write files and read the loop."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.repo = os.path.realpath(self._tmp.name)
        self.profile = game.load_profile()

    def write(self, rel: str, content: str = "") -> str:
        path = os.path.join(self.repo, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(content)
        return path

    def config(self) -> dict:
        with open(os.path.join(self.repo, ".harness", "config.json"), encoding="utf-8") as fh:
            return json.load(fh)

    def set_game(self, **block) -> None:
        self.write(".harness/config.json", json.dumps({"schema": "harness-config/1", "game": block}))

    def loop(self, scale: str | None = None) -> dict:
        return game.loop(self.repo, self.profile, scale, TODAY)

    def piece(self, pid: str, scale: str | None = "weeks") -> dict:
        return next(p for p in self.loop(scale)["pieces"] if p["id"] == pid)

    def judge(self, piece: str, **spec) -> dict:
        return game_run.judge(piece, spec, self.repo)


class ProfileDataTests(unittest.TestCase):
    def setUp(self) -> None:
        self.profile = game.load_profile()
        self.ids = [p["id"] for p in self.profile["pieces"]]

    def test_every_piece_has_its_words_and_its_cost(self):
        for piece in self.profile["pieces"]:
            with self.subTest(piece=piece["id"]):
                for key in ("label", "gives", "why", "kind"):
                    self.assertTrue(piece[key].strip())
                self.assertIsInstance(piece["minutes"], int)
        self.assertEqual(len(self.ids), len(set(self.ids)))

    def test_each_scale_lists_known_pieces_in_the_loop_order_and_contains_the_smaller_one(self):
        previous: set[str] = set()
        for sid in ("hour", "jam", "weeks"):
            pieces = self.profile["scales"][sid]["pieces"]
            with self.subTest(scale=sid):
                self.assertEqual(pieces, [p for p in self.ids if p in pieces])
                self.assertTrue(previous <= set(pieces))
                self.assertIn(self.profile["scales"][sid]["suggested_target"], (1, 2, 3, 4))
            previous = set(pieces)
        self.assertEqual(self.profile["scales"]["weeks"]["pieces"], self.ids)

    def test_the_hour_scale_stays_small(self):
        hour = self.profile["scales"]["hour"]["pieces"]
        self.assertLessEqual(sum(p["minutes"] for p in self.profile["pieces"] if p["id"] in hour), 15)

    def test_every_piece_is_handled_by_the_loop(self):
        handled = set(game.COMMAND_PIECES) | {"version", "runner", "instructions", "owned_files", "playtest",
                                              "scope", "assets", "ci"}
        self.assertEqual(set(self.ids), handled)
        self.assertEqual(set(game_run.ORDER) | {"run"}, set(game.COMMAND_PIECES))

    def test_every_engine_has_what_the_loop_reads_and_its_patterns_compile(self):
        for eid, engine in self.profile["engines"].items():
            with self.subTest(engine=eid):
                for key in ("name", "detect", "version", "owned", "owned_rule", "exit_code_trusted", "errors",
                            "candidates", "notes", "owner_actions", "commands_checked"):
                    self.assertIn(key, engine)
                self.assertEqual(set(engine["candidates"]), set(game.COMMAND_PIECES))
                self.assertEqual(bool(engine["owned"]), bool(engine["owned_rule"]))
                for pattern in engine["errors"] + engine["version"].get("patterns", []):
                    re.compile(pattern)
                for spec in (engine.get("outputs") or {}).values():
                    for pattern in spec.get("output_errors", []):
                        re.compile(pattern)

    def test_no_candidate_command_is_one_the_profile_refuses_to_record(self):
        patterns = [re.compile(p, re.I) for p in self.profile["never_record"]["patterns"]]
        for eid, engine in self.profile["engines"].items():
            for piece, command in engine["candidates"].items():
                with self.subTest(engine=eid, piece=piece):
                    self.assertFalse(any(p.search(command) for p in patterns))

    def test_the_engines_whose_exit_code_lies_are_the_ones_the_sources_name(self):
        lying = {eid for eid, e in self.profile["engines"].items() if e["exit_code_trusted"] is False}
        self.assertTrue({"godot", "unity", "love"} <= lying)

    def test_every_instruction_line_names_a_known_condition_and_carries_why_and_date(self):
        known = {"engine", "commands", "run_no_smoke", "capture", "untrusted_exit", "owned", "always",
                 "prototype", "production", "scope", "assets"}
        data = self.profile["instructions"]
        for line in data["lines"] + data["forbidden"]:
            with self.subTest(line=line["id"]):
                self.assertIn(line["when"], known)
                self.assertIn("Why:", line["text"])
                self.assertIn("[{month}]", line["text"])
        for question in data["questions"]:
            self.assertTrue(question["ask"].endswith("?"))
            self.assertTrue(set(question.get("scales", [])) <= set(self.profile["scales"]))

    def test_the_jam_question_on_generated_code_and_assets_is_asked(self):
        asks = " ".join(q["ask"] for q in self.profile["instructions"]["questions"])
        self.assertIn("AI-generated", asks)


class DetectTests(Repo):
    def found(self) -> dict:
        return game.detect(self.repo, self.profile)

    def test_godot_and_its_version_are_read_from_project_godot(self):
        self.write("project.godot", GODOT)
        found = self.found()
        self.assertEqual((found["id"], found["version"], found["version_file"]), ("godot", "4.3", "project.godot"))

    def test_a_godot_3_project_says_so(self):
        self.write("project.godot", "config_version=4\n[application]\n")
        self.assertEqual(self.found()["version"], "3.x")

    def test_a_godot_project_in_a_subfolder_is_found_with_its_path(self):
        self.write("game/project.godot", GODOT)
        found = self.found()
        self.assertEqual((found["id"], found["version_file"]), ("godot", "game/project.godot"))

    def test_unity_unreal_love_pygame_and_bevy(self):
        cases = {
            "unity": ("ProjectSettings/ProjectVersion.txt", "m_EditorVersion: 2022.3.10f1\n", "2022.3.10f1"),
            "unreal": ("Shooter.uproject", '{"EngineAssociation": "5.3"}', "5.3"),
            "love": ("main.lua", "function love.draw() end\n", None),
            "pygame": ("requirements.txt", "pygame==2.5.2\n", "2.5.2"),
            "bevy": ("Cargo.toml", '[dependencies]\nbevy = "0.14"\n', "0.14"),
        }
        for eid, (rel, text, version) in cases.items():
            with self.subTest(engine=eid):
                with tempfile.TemporaryDirectory() as tmp:
                    path = os.path.join(tmp, rel)
                    os.makedirs(os.path.dirname(path), exist_ok=True)
                    with open(path, "w", encoding="utf-8") as fh:
                        fh.write(text)
                    found = game.detect(tmp, self.profile)
                    self.assertEqual((found["id"], found["version"]), (eid, version))

    def test_a_main_lua_that_is_not_love_is_not_love(self):
        self.write("main.lua", "print('a script')\n")
        self.assertIsNone(self.found()["id"])

    def test_the_love_version_comes_from_conf_lua(self):
        self.write("main.lua", "function love.load() end\n")
        self.write("conf.lua", 'function love.conf(t) t.version = "11.5" end\n')
        self.assertEqual(self.found()["version"], "11.5")

    def test_a_web_game_names_its_library_and_its_version(self):
        self.write("package.json", json.dumps({"dependencies": {"phaser": "^3.80.1"}, "devDependencies": {"vite": "5"}}))
        found = self.found()
        self.assertEqual((found["id"], found["engine_name"], found["version"]), ("web", "Phaser", "^3.80.1"))

    def test_a_library_on_latest_is_not_pinned(self):
        self.write("package.json", json.dumps({"dependencies": {"three": "latest"}}))
        self.assertIsNone(self.found()["version"])
        self.assertEqual(self.piece("version")["state"], "missing")

    def test_a_plain_canvas_page_has_no_engine_to_pin(self):
        self.write("index.html", "<html><body><canvas id=c></canvas></body></html>")
        self.assertEqual(self.found()["engine_name"], "plain canvas")
        self.assertEqual(self.piece("version")["state"], "n/a")

    def test_an_empty_repository_has_no_engine_and_says_how_to_choose_one(self):
        version = self.piece("version")
        self.assertEqual(version["state"], "missing")
        self.assertIn("harness game set --engine", version["how"])

    def test_the_engine_the_owner_chose_wins_and_the_others_are_listed(self):
        self.write("project.godot", GODOT)
        self.write("package.json", json.dumps({"dependencies": {"phaser": "3.80.1"}}))
        self.assertEqual((self.found()["id"], self.found()["others"]), ("godot", ["web"]))
        self.assertEqual(game.detect(self.repo, self.profile, "web")["id"], "web")

    def test_dependency_folders_are_not_read(self):
        self.write("node_modules/x/project.godot", GODOT)
        self.assertIsNone(self.found()["id"])


class LoopTests(Repo):
    def test_without_a_scale_every_piece_is_shown_and_the_next_step_is_to_choose_one(self):
        result = self.loop()
        self.assertIsNone(result["scale"])
        self.assertEqual(len(result["pieces"]), len(self.profile["pieces"]))
        self.assertNotIn("later", {p["state"] for p in result["pieces"]})
        self.assertEqual(result["next"]["id"], "scale")

    def test_a_scale_puts_the_pieces_beyond_it_later(self):
        self.write("project.godot", GODOT)
        result = self.loop("hour")
        later = {p["id"] for p in result["pieces"] if p["state"] == "later"}
        self.assertEqual(later, set(self.profile["scales"]["weeks"]["pieces"]) - set(self.profile["scales"]["hour"]["pieces"]))
        self.assertEqual(result["counted"], len(self.profile["scales"]["hour"]["pieces"]))
        self.assertEqual(result["next"]["id"], "run")
        self.assertIn('harness game command run "godot --path ."', result["next"]["how"])

    def test_the_scale_written_in_the_config_is_read(self):
        self.set_game(scale="jam")
        self.assertEqual(self.loop()["scale"], "jam")

    def test_an_unknown_scale_is_refused(self):
        with self.assertRaises(ValueError):
            self.loop("month")

    def test_a_smoke_run_without_ready_line_on_godot_is_weak(self):
        self.write("project.godot", GODOT)
        self.set_game(commands={"smoke": {"run": "godot --headless", "exit_code_trusted": False}})
        self.assertEqual(self.piece("smoke")["state"], "weak")
        self.set_game(commands={"smoke": {"run": "godot --headless", "exit_code_trusted": False, "ready": "READY"}})
        self.assertEqual(self.piece("smoke")["state"], "ok")

    def test_a_capture_without_an_output_file_is_weak(self):
        self.set_game(commands={"capture": {"run": "x"}})
        self.assertEqual(self.piece("capture")["state"], "weak")
        self.set_game(commands={"capture": {"run": "x", "output": "shots/a.png"}})
        self.assertEqual(self.piece("capture")["state"], "ok")

    def test_the_playtest_is_fresh_stale_or_undated(self):
        self.set_game(scale="jam")
        self.assertEqual(self.piece("playtest", None)["state"], "missing")
        self.write("docs/playtests.md", "# Playtests\n- 2026-11-28 Sam played build 3, stopped at the boss.\n")
        self.assertEqual(self.piece("playtest", None)["state"], "ok")
        self.write("docs/playtests.md", "# Playtests\n- 2026-11-20 Sam played build 1.\n")
        stale = self.piece("playtest", None)
        self.assertEqual(stale["state"], "stale")
        self.assertIn("8 days ago", stale["detail"])
        self.write("docs/playtests.md", "# Playtests\n- Sam played it.\n")
        self.assertEqual(self.piece("playtest", None)["state"], "weak")

    def test_the_owner_sets_how_old_a_playtest_may_be(self):
        self.set_game(scale="jam", playtest_days=10)
        self.write("docs/playtests.md", "- 2026-11-20 Sam\n")
        self.assertEqual(self.piece("playtest", None)["state"], "ok")

    def test_at_the_hour_scale_any_dated_playtest_is_enough(self):
        self.set_game(scale="hour")
        self.write("PLAYTESTS.md", "- 2025-01-01 me\n")
        self.assertEqual(self.piece("playtest", None)["state"], "ok")

    def test_the_playtests_of_a_design_workshop_count(self):
        self.write("design/game.json", json.dumps({"playtests": [{"tester": "Sam", "date": "2026-11-27"}]}))
        playtest = self.piece("playtest", "jam")
        self.assertEqual(playtest["state"], "ok")
        self.assertIn("design/game.json", playtest["detail"])

    def test_the_scope_needs_a_cut_list_in_english_or_in_french(self):
        self.write("docs/design.md", "# Design\n## Core loop\nJump.\n")
        self.assertEqual(self.piece("scope")["state"], "weak")
        self.write("docs/design.md", "# Design\n## Cut\n- multiplayer\n")
        self.assertEqual(self.piece("scope")["state"], "ok")
        os.remove(os.path.join(self.repo, "docs/design.md"))
        self.write("design/GDD.md", "# Jeu — GDD une page\n## Coupé (distractions)\n- rien\n")
        self.assertEqual(self.piece("scope")["state"], "ok")

    def test_assets_are_not_needed_until_there_is_one(self):
        self.assertEqual(self.piece("assets")["state"], "n/a")
        self.write("art/hero.png")
        self.write("art/kenney_pack/tile.png")
        self.assertEqual(self.piece("assets")["state"], "missing")
        self.write("CREDITS.md", "- hero.png: drawn by me, CC0\n")
        weak = self.piece("assets")
        self.assertEqual(weak["state"], "weak")
        self.assertIn("art/kenney_pack/tile.png", weak["detail"])
        self.write("CREDITS.md", "- hero.png: drawn by me, CC0\n- kenney_pack: Kenney, CC0\n")
        self.assertEqual(self.piece("assets")["state"], "ok")

    def test_a_generic_folder_name_does_not_credit_its_files(self):
        self.write("assets/hero.png")
        self.write("CREDITS.md", "Everything under assets is ours.\n")
        self.assertEqual(self.piece("assets")["state"], "weak")

    def test_screenshots_and_build_output_are_not_assets(self):
        self.write("shots/frame.png")
        self.write("build/web/icon.png")
        self.write("out/cap.png")
        self.set_game(commands={"capture": {"run": "x", "output": "out/cap.png"}})
        self.assertEqual(self.piece("assets")["state"], "n/a")

    def test_the_runner_is_missing_written_or_out_of_date(self):
        self.assertEqual(self.piece("runner")["state"], "missing")
        self.assertEqual(run_cli("game", "runner", self.repo, "--write")[0], 0)
        self.assertEqual(self.piece("runner")["state"], "ok")
        with open(os.path.join(self.repo, ".harness", "game_loop.py"), "a", encoding="utf-8") as fh:
            fh.write("# edited\n")
        self.assertEqual(self.piece("runner")["state"], "weak")

    def test_the_instructions_name_what_they_do_not_say(self):
        self.write("project.godot", GODOT)
        self.assertEqual(self.piece("instructions")["state"], "missing")
        self.write("AGENTS.md", AGENTS)
        self.set_game(commands={"smoke": {"run": "godot --headless --quit-after 300"}})
        weak = self.piece("instructions")
        self.assertEqual(weak["state"], "weak")
        for gap in ("the engine (Godot)", "its version (4.3)", "the smoke command"):
            self.assertIn(gap, weak["detail"])
        self.write("AGENTS.md", AGENTS + "- Godot 4.3. Run `python3 .harness/game_loop.py all` after each change.\n")
        self.assertEqual(self.piece("instructions")["state"], "ok")

    def test_the_run_command_must_be_said_even_when_the_runner_is(self):
        self.write("AGENTS.md", AGENTS + "- Run `python3 .harness/game_loop.py all`.\n")
        self.set_game(commands={"run": {"run": "npm run dev"}})
        self.assertIn("the run command", self.piece("instructions")["detail"])

    def test_the_engine_files_are_named_for_godot_and_not_needed_for_the_web(self):
        self.write("project.godot", GODOT)
        self.write("AGENTS.md", AGENTS)
        self.assertEqual(self.piece("owned_files")["state"], "missing")
        self.write("AGENTS.md", AGENTS + "- Never hand-edit `.tscn` files.\n")
        self.assertEqual(self.piece("owned_files")["state"], "ok")
        os.remove(os.path.join(self.repo, "project.godot"))
        self.write("package.json", json.dumps({"dependencies": {"phaser": "3.80.1"}}))
        self.assertEqual(self.piece("owned_files")["state"], "n/a")

    def test_the_ci_counts_when_a_workflow_runs_the_loop(self):
        self.assertEqual(self.piece("ci")["state"], "missing")
        self.write(".github/workflows/ci.yml", "jobs:\n  t:\n    steps:\n      - run: npm test\n")
        self.assertIn("none of the loop", self.piece("ci")["detail"])
        self.write(".github/workflows/ci.yml", "jobs:\n  t:\n    steps:\n      - run: python3 .harness/game_loop.py all\n")
        ci = self.piece("ci")
        self.assertEqual((ci["state"], ci["file"]), ("ok", ".github/workflows/ci.yml"))

    def test_the_next_piece_is_the_first_one_not_in_place(self):
        self.write("project.godot", GODOT)
        self.set_game(scale="hour", commands={"run": {"run": "godot --path ."}})
        self.assertEqual(self.loop()["next"]["id"], "instructions")

    def test_the_rendered_loop_says_the_scale_the_engine_and_the_next_step(self):
        self.write("project.godot", GODOT)
        self.set_game(scale="jam")
        text = game.render_loop(self.loop())
        self.assertIn("scale: a jam or a weekend; engine: Godot 4.3", text)
        self.assertIn("Next: A command starts the game for a person", text)
        self.assertIn("Only the owner can: install the export templates", text)

    def test_unverified_engine_commands_are_said_to_be_unverified(self):
        self.write("Shooter.uproject", '{"EngineAssociation": "5.3"}')
        self.assertIn("not checked on a primary source", game.render_loop(self.loop("jam")))


class LadderUntouchedTests(Repo):
    def test_the_profile_never_moves_the_level(self):
        self.write("AGENTS.md", AGENTS)
        self.write("project.godot", GODOT)
        before = maturity.evaluate(facts.collect(self.repo, today=TODAY))
        self.assertEqual(run_cli("game", "set", "--repo", self.repo, "--scale", "weeks")[0], 0)
        self.assertEqual(run_cli("game", "command", "smoke", "godot --headless", "--repo", self.repo,
                                 "--ready", "READY")[0], 0)
        after = maturity.evaluate(facts.collect(self.repo, today=TODAY))
        self.assertEqual(before["levels"], after["levels"])
        self.assertEqual(before["level"], after["level"])

    def test_writing_the_game_block_keeps_the_owner_s_other_choices(self):
        self.write(".harness/config.json", json.dumps({"schema": "harness-config/1", "target_level": 2,
                                                       "ignored_checks": {"L1.forbidden": {"reason": "r", "date": "2026-11-01"}}}))
        run_cli("game", "set", "--repo", self.repo, "--scale", "jam")
        config = self.config()
        self.assertEqual((config["target_level"], config["game"]["scale"]), (2, "jam"))
        self.assertIn("L1.forbidden", config["ignored_checks"])

    def test_a_config_that_is_not_an_object_is_refused_and_left_as_it_is(self):
        self.write(".harness/config.json", "[1, 2]")
        code, _, err = run_cli("game", "set", "--repo", self.repo, "--scale", "jam")
        self.assertEqual(code, 2)
        self.assertIn("is not a JSON object", err)
        with open(os.path.join(self.repo, ".harness", "config.json"), encoding="utf-8") as fh:
            self.assertEqual(fh.read(), "[1, 2]")


class CommandTests(Repo):
    def record(self, piece: str, command: str | None, **opts) -> dict:
        config = game.read_config(game.config_path(self.repo))
        return game.record_command(config, self.profile, opts.pop("engine", "godot"), piece, command,
                                   opts.get("ready"), opts.get("output"), opts.get("timeout"),
                                   opts.get("remove", False), TODAY)

    def test_the_engine_s_error_lines_and_exit_code_are_recorded_with_the_command(self):
        spec = self.record("smoke", "godot --headless --quit-after 300", ready="GAME READY")["game"]["commands"]["smoke"]
        self.assertEqual(spec["run"], "godot --headless --quit-after 300")
        self.assertIn("SCRIPT ERROR", spec["errors"])
        self.assertIs(spec["exit_code_trusted"], False)
        self.assertEqual((spec["ready"], spec["date"]), ("GAME READY", "2026-11-28"))

    def test_the_run_command_is_recorded_without_a_judge(self):
        spec = self.record("run", "godot --path .")["game"]["commands"]["run"]
        self.assertNotIn("errors", spec)

    def test_publishing_is_never_recorded_whatever_the_piece(self):
        for command in ("butler push build user/game:web", "git push origin main", "npm publish",
                        "steamcmd +login x", "gh release create v1", "netlify deploy --prod"):
            with self.subTest(command=command):
                with self.assertRaises(ValueError) as caught:
                    self.record("export", command)
                self.assertIn("owner's release", str(caught.exception))

    def test_an_unknown_piece_an_empty_command_a_bad_pattern_and_a_bad_timeout_are_refused(self):
        for piece, command, opts in (("deploy", "x", {}), ("smoke", "  ", {}), ("smoke", "x", {"ready": "("}),
                                     ("smoke", "x", {"timeout": 0})):
            with self.subTest(piece=piece, command=command, opts=opts):
                with self.assertRaises(ValueError):
                    self.record(piece, command, **opts)

    def test_unity_tests_are_judged_by_their_results_file(self):
        command = self.profile["engines"]["unity"]["candidates"]["test"]
        spec = self.record("test", command, engine="unity")["game"]["commands"]["test"]
        self.assertEqual(spec["output"], "results.xml")
        self.assertTrue(spec["output_errors"])

    def test_a_command_is_removed_and_the_others_stay(self):
        self.write(".harness/config.json", json.dumps(self.record("smoke", "a")))
        self.write(".harness/config.json", json.dumps(self.record("check", "b")))
        commands = self.record("smoke", None, remove=True)["game"]["commands"]
        self.assertEqual(list(commands), ["check"])
        with self.assertRaises(ValueError):
            self.record("export", None, remove=True)

    def test_the_command_line_records_and_says_what_judges_it(self):
        self.write("project.godot", GODOT)
        code, out, _ = run_cli("game", "command", "smoke", "godot --headless", "--repo", self.repo, "--ready", "R")
        self.assertEqual(code, 0)
        self.assertIn("judged with Godot's error lines", out)
        self.assertEqual(self.config()["game"]["commands"]["smoke"]["ready"], "R")
        code, _, err = run_cli("game", "command", "export", "butler push . u/g:web", "--repo", self.repo)
        self.assertEqual(code, 2)
        self.assertIn("refused", err)


class JudgeTests(Repo):
    def py(self, code: str) -> str:
        return f'"{PY}" -c "{code}"'

    def test_a_clean_run_passes(self):
        verdict = self.judge("smoke", run=self.py("print('GAME READY')"), ready="GAME READY")
        self.assertTrue(verdict["passed"], verdict)

    def test_a_non_zero_exit_fails(self):
        verdict = self.judge("check", run=self.py("raise SystemExit(3)"))
        self.assertEqual((verdict["passed"], verdict["exit_code"]), (False, 3))

    def test_an_error_line_fails_a_run_that_exits_zero(self):
        verdict = self.judge("smoke", run=self.py("print('SCRIPT ERROR: x'); print('GAME READY')"),
                             errors=["SCRIPT ERROR"], ready="GAME READY", exit_code_trusted=False)
        self.assertFalse(verdict["passed"])
        self.assertEqual(verdict["error_lines"], ["SCRIPT ERROR: x"])

    def test_a_missing_ready_line_fails(self):
        verdict = self.judge("smoke", run=self.py("print('hello')"), ready="GAME READY")
        self.assertIn("the ready line never appeared", " ".join(verdict["failed"]))

    def test_a_smoke_run_on_a_lying_engine_without_a_ready_line_fails_and_a_check_only_gets_a_note(self):
        smoke = self.judge("smoke", run=self.py("pass"), exit_code_trusted=False)
        self.assertFalse(smoke["passed"])
        self.assertIn("a pass would prove nothing", " ".join(smoke["failed"]))
        check = self.judge("check", run=self.py("pass"), exit_code_trusted=False)
        self.assertTrue(check["passed"])
        self.assertTrue(check["notes"])

    def test_an_output_must_be_written_by_this_run(self):
        self.assertIn("shots/a.png was not written",
                      self.judge("capture", run=self.py("pass"), output="shots/a.png")["failed"])
        old = self.write("shots/a.png", "x")
        os.utime(old, (1_000_000_000, 1_000_000_000))
        self.assertIn("older than this run", " ".join(self.judge("capture", run=self.py("pass"), output="shots/a.png")["failed"]))
        verdict = self.judge("capture", run=self.py("open('shots/a.png','w').write('png')"), output="shots/a.png")
        self.assertTrue(verdict["passed"], verdict)
        self.assertIn("open shots/a.png", verdict["notes"][0])

    def test_a_results_file_that_reports_failures_fails_the_run(self):
        write = "open('results.xml','w').write('<test-run failed=\\\"2\\\">')"
        verdict = self.judge("test", run=self.py(write), output="results.xml", output_errors=['failed="[1-9]'])
        self.assertIn("results.xml reports failures", " ".join(verdict["failed"]))

    def test_a_run_that_never_ends_is_stopped_and_fails(self):
        verdict = game_run.judge("smoke", {"run": self.py("import time; time.sleep(5)")}, self.repo, timeout=1)
        self.assertIn("did not finish in 1 s", verdict["failed"][0])

    def test_a_binary_that_is_not_installed_is_named(self):
        verdict = self.judge("smoke", run="SDL_VIDEODRIVER=dummy no-such-engine-binary-xyz --headless")
        self.assertIn("no-such-engine-binary-xyz was not found", verdict["failed"][0])

    def test_the_run_piece_is_never_judged_and_all_runs_the_recorded_pieces_in_order(self):
        self.set_game(commands={"run": {"run": "x"}, "export": {"run": self.py("pass")}, "check": {"run": self.py("pass")}})
        with self.assertRaises(ValueError):
            game_run.selected(game_run.load_commands(self.repo), "run")
        self.assertEqual(game_run.selected(game_run.load_commands(self.repo), "all"), ["check", "export"])
        out = io.StringIO()
        self.assertEqual(game_run.run("all", self.repo, stream=out), 0)
        self.assertIn("2 of 2 passed", out.getvalue())

    def test_nothing_recorded_or_an_unknown_piece_is_a_usage_error(self):
        with redirect_stderr(io.StringIO()):
            self.assertEqual(game_run.run("all", self.repo, stream=io.StringIO()), 2)
            self.assertEqual(game_run.run("deploy", self.repo, stream=io.StringIO()), 2)

    def test_harness_game_run_returns_one_on_a_failure(self):
        self.set_game(commands={"check": {"run": self.py("raise SystemExit(1)")}})
        self.assertEqual(run_cli("game", "run", "check", "--repo", self.repo)[0], 1)

    def test_the_copied_runner_is_the_shipped_file_and_runs_on_its_own(self):
        self.set_game(commands={"smoke": {"run": self.py("print('GAME READY')"), "ready": "GAME READY"}})
        run_cli("game", "runner", self.repo, "--write")
        copied = os.path.join(self.repo, ".harness", "game_loop.py")
        with open(copied, encoding="utf-8") as a, open(game.RUNNER_SOURCE, encoding="utf-8") as b:
            self.assertEqual(a.read(), b.read())
        elsewhere = tempfile.mkdtemp()
        self.addCleanup(lambda: os.rmdir(elsewhere))
        proc = subprocess.run([PY, "-I", copied, "smoke"], cwd=elsewhere, capture_output=True, text=True, check=False)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("PASS smoke", proc.stdout)

    def test_the_runner_imports_only_the_standard_library(self):
        with open(game.RUNNER_SOURCE, encoding="utf-8") as fh:
            imports = set(re.findall(r"^(?:import|from) (\w+)", fh.read(), re.M))
        self.assertEqual(imports - {"__future__", "argparse", "json", "os", "re", "subprocess", "sys", "time"}, set())


class InstructionsTests(Repo):
    def lines(self) -> dict:
        return game.instructions(self.repo, self.profile, TODAY)

    def ids(self) -> list[str]:
        return [line["id"] for line in self.lines()["lines"]]

    def test_every_line_is_filled_whatever_the_engine(self):
        placeholder = re.compile(r"\{[a-z_]+\}")
        for eid in self.profile["engines"]:
            with self.subTest(engine=eid):
                self.set_game(scale="weeks", engine=eid, commands={
                    "run": {"run": "r"}, "smoke": {"run": "s"}, "test": {"run": "t"},
                    "capture": {"run": "c", "output": "shots/a.png"}})
                result = self.lines()
                for line in result["lines"] + result["forbidden"]:
                    self.assertIsNone(placeholder.search(line["text"]), line["text"])
                    self.assertIn("[2026-11]", line["text"])

    def test_a_godot_jam_gets_the_lines_of_its_engine_and_its_scale(self):
        self.write("project.godot", GODOT)
        self.set_game(scale="jam", commands={"smoke": {"run": "s", "ready": "R"}})
        ids = self.ids()
        for expected in ("engine", "loop", "exit_code", "owned", "feel", "prototype", "scope", "assets"):
            self.assertIn(expected, ids)
        self.assertNotIn("logic", ids)
        self.assertIn("Godot 4.3, pinned in `project.godot`", self.lines()["lines"][0]["text"])

    def test_weeks_with_tests_asks_for_logic_apart_from_rendering_and_drops_the_prototype_line(self):
        self.set_game(scale="weeks", commands={"smoke": {"run": "s"}, "test": {"run": "t"}})
        ids = self.ids()
        self.assertIn("logic", ids)
        self.assertNotIn("prototype", ids)

    def test_at_the_hour_scale_the_owner_playing_is_the_loop(self):
        self.write("project.godot", GODOT)
        self.set_game(scale="hour", commands={"run": {"run": "godot --path ."}})
        result = self.lines()
        handoff = next(line for line in result["lines"] if line["id"] == "handoff")
        self.assertIn("`godot --path .`", handoff["text"])
        self.assertNotIn("loop", [line["id"] for line in result["lines"]])
        self.assertTrue(any("record the smoke command first" in note for note in result["notes"]))

    def test_enforced_by_is_claimed_only_for_what_is_in_place(self):
        self.write("project.godot", GODOT)
        self.set_game(scale="jam", commands={"smoke": {"run": "s", "ready": "R"}})
        texts = {line["id"]: line["text"] for line in self.lines()["lines"]}
        self.assertIn("(unverified)", texts["exit_code"])
        self.assertIn("(unverified)", texts["loop"])
        run_cli("game", "runner", self.repo, "--write")
        self.write(".github/workflows/ci.yml", "steps:\n  - run: python3 .harness/game_loop.py all\n")
        texts = {line["id"]: line["text"] for line in self.lines()["lines"]}
        self.assertIn("Enforced by: `.harness/game_loop.py`", texts["exit_code"])
        self.assertIn("Enforced by: `.github/workflows/ci.yml`", texts["loop"])

    def test_the_share_of_enforced_rules_is_shown_before_and_after(self):
        self.write("AGENTS.md", AGENTS.replace("- Tests pass.", "- Tests pass. Why: x. Enforced by: `ci.yml`"))
        self.set_game(scale="jam")
        share = self.lines()["enforced_share"]
        self.assertEqual(share["before"], [1, 2])
        self.assertTrue(share["half_before"])
        self.assertFalse(share["half_after"])
        self.assertIn("these lines take the file under it", game.render_instructions(self.lines()))

    def test_the_jam_question_is_not_asked_of_a_game_built_over_weeks(self):
        self.set_game(scale="weeks")
        self.assertNotIn("jam_rules", [q["id"] for q in self.lines()["questions"]])
        self.set_game(scale="jam")
        self.assertIn("jam_rules", [q["id"] for q in self.lines()["questions"]])

    def test_the_lines_fit_the_budget_of_a_short_file(self):
        self.write("project.godot", GODOT)
        self.write("AGENTS.md", AGENTS)
        self.set_game(scale="weeks", commands={"smoke": {"run": "s"}, "test": {"run": "t"},
                                               "capture": {"run": "c", "output": "o.png"}})
        result = self.lines()
        self.assertLessEqual(result["lines_after"], result["limit"])


class CommandLineTests(Repo):
    def test_every_action_answers_and_json_parses(self):
        self.write("project.godot", GODOT)
        for argv in (("loop", self.repo), ("detect", self.repo), ("instructions", self.repo), ("profile",),
                     ("runner", self.repo)):
            with self.subTest(argv=argv):
                code, out, err = run_cli("game", *argv)
                self.assertEqual(code, 0, err)
                self.assertTrue(out.strip())
        for argv in (("loop", self.repo), ("detect", self.repo), ("instructions", self.repo), ("profile",)):
            with self.subTest(argv=argv, format="json"):
                json.loads(run_cli("game", *argv, "--format", "json")[1])

    def test_wrong_input_exits_two_with_a_reason(self):
        for argv, said in ((("loop", "/no/such/dir"), "is not a directory"),
                           (("loop", self.repo, "--scale", "month"), "is not a scale"),
                           (("set", "--repo", self.repo), "nothing to set"),
                           (("set", "--repo", self.repo, "--engine", "gamemaker"), "is not an engine"),
                           (("loop", self.repo, "--today", "soon"), "is not a date")):
            with self.subTest(argv=argv):
                code, _, err = run_cli("game", *argv)
                self.assertEqual(code, 2)
                self.assertIn(said, err)

    def test_set_suggests_a_target_level_and_does_not_write_one(self):
        code, out, _ = run_cli("game", "set", "--repo", self.repo, "--scale", "weeks")
        self.assertEqual(code, 0)
        self.assertIn("harness target 3", out)
        self.assertNotIn("target_level", self.config())

    def test_the_profile_lists_every_scale_and_engine(self):
        out = run_cli("game", "profile")[1]
        for name in list(self.profile["scales"]) + list(self.profile["engines"]):
            self.assertIn(name, out)
        self.assertIn("judged by the log", out)

    def test_the_cli_help_names_the_game_command(self):
        self.assertIn("harness game", sys.modules["harness"].__doc__)


if __name__ == "__main__":
    unittest.main()
