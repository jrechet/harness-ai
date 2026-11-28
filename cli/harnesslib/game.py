"""`game` subcommand: the video-game profile of harness-ai.

A game needs a development loop the general harness does not know: a run that boots the game and is
judged by its log, a screenshot the agent opens, an export proven early, a person who plays and says
whether it is fun. This command says which pieces of that loop a repository has, for the scale the
owner chose (one hour, a jam, weeks), and proposes the next one. It sits beside the level ladder and
never changes a level: `harness status` measures the same as without it.

  harness game loop [repo] [--scale S]          the pieces of the loop: in place, missing, the next one
  harness game detect [repo]                    the engine, its version and where they were read
  harness game set [--scale S] [--engine E] …   writes the owner's choices in .harness/config.json
  harness game command <piece> "<cmd>" […]      records the command of a piece, with what judges it
  harness game run <piece|all> [--repo P]       runs recorded pieces and judges them (exit 1 on a failure)
  harness game runner [repo] [--write]          the judge copied into the repository, for the agent and the CI
  harness game instructions [repo]              the lines the instruction file needs for a game, as candidates
  harness game profile                          the scales, the pieces and the engines the profile knows

The knowledge is data (`game_profile.json`); its sources are in docs/game-profile.md. Commands are
candidates the owner confirms by running them; publishing commands are refused, whatever the piece.
Exit codes: 0 done, 1 a judged run failed, 2 invalid input."""
from __future__ import annotations

import argparse
import fnmatch
import json
import os
import re
import sys
import tempfile
from datetime import date
from typing import Any

from . import facts, game_run

PROFILE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "game_profile.json")
RUNNER_SOURCE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "game_run.py")
CONFIG_SCHEMA = "harness-config/1"
BLOCK = "game"
COMMAND_PIECES = ("run",) + game_run.ORDER
DATE_RE = re.compile(r"\b(\d{4}-\d{2}-\d{2})\b")
GENERIC_DIRS = {"assets", "asset", "art", "audio", "sound", "sounds", "music", "sprites", "images", "img",
                "textures", "fonts", "sfx", "gfx", "res", "resources", "data", "media", "static", "public", "src"}
MARKS = {"ok": "[x]", "weak": "[~]", "stale": "[~]", "missing": "[ ]", "later": "[-]", "n/a": "[-]"}
RUNNER_CALL = "python3 .harness/game_loop.py"


def load_profile(path: str = PROFILE_FILE) -> dict[str, Any]:
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


# --- files -------------------------------------------------------------------------------------

def _read(path: str) -> str | None:
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            return fh.read()
    except OSError:
        return None


def _walk(repo: str, skip: set[str], depth: int | None = None, limit: int = 20000) -> list[str]:
    """Files of the repository, relative and with `/`, outside the skipped folders."""
    found: list[str] = []
    for root, dirs, files in os.walk(repo):
        rel_root = os.path.relpath(root, repo).replace(os.sep, "/")
        level = 0 if rel_root == "." else rel_root.count("/") + 1
        dirs[:] = sorted(d for d in dirs if d not in skip and not (depth is not None and level >= depth))
        for name in sorted(files):
            found.append(name if rel_root == "." else f"{rel_root}/{name}")
            if len(found) >= limit:
                return found
    return found


def _first(repo: str, candidates: list[str]) -> str | None:
    return next((rel for rel in candidates if os.path.isfile(os.path.join(repo, rel))), None)


# --- detection ---------------------------------------------------------------------------------

def _version(repo: str, base: str, spec: dict[str, Any]) -> tuple[str | None, str | None]:
    """The engine version and the file it was read from, or (None, the file that should hold it)."""
    files = spec.get("files") or ([spec["file"]] if spec.get("file") else [])
    if spec.get("glob"):
        files = sorted(f for f in os.listdir(os.path.join(repo, base) or ".") if fnmatch.fnmatch(f, spec["glob"]))
    for rel in files:
        text = _read(os.path.join(repo, base, rel))
        if text is None:
            continue
        for pattern in spec.get("patterns", []):
            match = re.search(pattern, text, re.M)
            if match:
                found = match.group(1)
                if spec.get("godot3_when") and pattern.startswith("^config_version"):
                    found = "4" if int(found) >= 5 else "3.x"      # 3 and 4: Godot 3.0 and 3.x; 5: Godot 4
                return found, _join(base, rel)
    return None, _join(base, files[0]) if files else None


def _join(base: str, rel: str) -> str:
    return rel if base in ("", ".") else f"{base}/{rel}"


def _package_deps(repo: str, base: str) -> dict[str, str]:
    data = facts.load_json(os.path.join(repo, base, "package.json"))
    if not isinstance(data, dict):
        return {}
    deps: dict[str, str] = {}
    for key in ("dependencies", "devDependencies"):
        block = data.get(key)
        if isinstance(block, dict):
            deps.update({str(k): str(v) for k, v in block.items()})
    return deps


def _folders(path: str) -> int:
    return 0 if path in ("", ".") else path.count("/") + 1


def _match_engine(repo: str, eid: str, engine: dict[str, Any], files: list[str]) -> dict[str, Any] | None:
    """The engine's evidence in the repository, or None: the project file found in the fewest folders, no
    deeper than the engine's `depth`. `files` are the shallow files of the repository."""
    rule = engine["detect"]
    depth = rule.get("depth", 1)
    marker = (rule.get("files") or [None])[0]
    for rel in sorted(files, key=lambda r: (r.count("/"), r)):
        base = os.path.dirname(rel)
        name = os.path.basename(rel)
        if marker and (rel == marker or rel.endswith("/" + marker)):
            base = rel[: -len(marker)].rstrip("/")
            pattern = (rule.get("content") or {}).get(marker)
            if _folders(base) > depth or pattern and not re.search(pattern, _read(os.path.join(repo, rel)) or ""):
                continue
            return {"base": base, "evidence": rel}
        if _folders(base) > depth:
            continue
        if rule.get("globs") and any(fnmatch.fnmatch(name, g) for g in rule["globs"]):
            return {"base": base, "evidence": rel}
        if rule.get("package_deps") and name == "package.json":
            deps = _package_deps(repo, base)
            hit = next((d for d in rule["package_deps"] if d in deps), None)
            if hit:
                return {"base": base, "evidence": f"{rel}: {hit}", "flavour": rule["package_deps"][hit],
                        "version": deps[hit], "dep": hit}
        if rule.get("python_deps") and name in ("requirements.txt", "requirements-dev.txt", "pyproject.toml", "setup.cfg"):
            text = (_read(os.path.join(repo, rel)) or "").lower()
            if any(re.search(rf"(^|[\s\"'\[,]){re.escape(d)}($|[\s=<>~!;\"',\]\[])", text, re.M) for d in rule["python_deps"]):
                return {"base": base, "evidence": rel}
        if rule.get("cargo_deps") and name == "Cargo.toml":
            text = _read(os.path.join(repo, rel)) or ""
            if any(re.search(rf"^{re.escape(d)}\s*=", text, re.M) for d in rule["cargo_deps"]):
                return {"base": base, "evidence": rel}
    return None


def _canvas_page(repo: str, engine: dict[str, Any]) -> dict[str, Any] | None:
    """A page with a `<canvas>` and no engine: the last resort, since every web build of an engine has one."""
    for rel in engine["detect"].get("canvas_html", []):
        if re.search(r"<canvas\b", _read(os.path.join(repo, rel)) or "", re.I):
            return {"base": os.path.dirname(rel), "evidence": f"{rel}: <canvas>", "flavour": "plain canvas"}
    return None


def detect(repo: str, profile: dict[str, Any], chosen: str | None = None) -> dict[str, Any]:
    """The engine of the repository: `id`, `name`, `version`, `version_file`, `evidence`, and the others
    found. An engine the owner chose (`game.engine`) wins over the files; otherwise the project file in the
    fewest folders, then the profile's order. A page with a `<canvas>` counts only when nothing else does."""
    skip = set(profile["files"]["skip_dirs"])
    files = _walk(repo, skip, depth=3)
    found = []
    for order, (eid, engine) in enumerate(profile["engines"].items()):
        hit = _match_engine(repo, eid, engine, files)
        if hit:
            found.append((_folders(hit["base"]), order, eid, hit))
    found = [(eid, hit) for _, _, eid, hit in sorted(found, key=lambda f: (f[0], f[1]))]
    if not found:
        canvas = _canvas_page(repo, profile["engines"]["web"]) if "web" in profile["engines"] else None
        found = [("web", canvas)] if canvas else []
    if chosen and chosen in profile["engines"]:
        picked = next(((eid, hit) for eid, hit in found if eid == chosen), (chosen, {"base": "", "evidence": "chosen by the owner"}))
    elif found:
        picked = found[0]
    else:
        return {"id": None, "name": None, "version": None, "version_file": None, "evidence": None,
                "others": [], "base": ""}
    eid, hit = picked
    engine = profile["engines"][eid]
    if "version" in hit:
        version = hit["version"] if re.search(r"\d", hit["version"]) else None
        version_file = _join(hit["base"], "package.json")
    elif hit.get("flavour") == "plain canvas":
        version, version_file = None, None
    else:
        version, version_file = _version(repo, hit["base"], engine["version"])
    name = engine["name"] if not hit.get("flavour") else f"{hit['flavour']} ({engine['name'].lower()})"
    return {"id": eid, "name": name, "engine_name": hit.get("flavour") or engine["name"], "version": version,
            "version_file": version_file, "evidence": hit["evidence"], "base": hit["base"],
            "pinnable": hit.get("flavour") != "plain canvas",
            "others": [eid2 for eid2, _ in found if eid2 != eid]}


# --- config ------------------------------------------------------------------------------------

def config_path(repo: str, harness_dir: str = ".harness") -> str:
    return os.path.join(repo, harness_dir, "config.json")


def read_config(path: str) -> dict[str, Any]:
    """The whole file; a missing file is a new one. A file that is not a JSON object is refused."""
    if not os.path.exists(path):
        return {"schema": CONFIG_SCHEMA}
    config = facts.load_json(path)
    if not isinstance(config, dict):
        raise ValueError(f"{path} exists and is not a JSON object: fix or remove it, nothing was written")
    return config


def game_block(config: dict[str, Any]) -> dict[str, Any]:
    block = config.get(BLOCK)
    return block if isinstance(block, dict) else {}


def safe_write(repo: str, rel: str, text: str) -> None:
    """Writes `rel` inside the repository, through a new file renamed in place. A link on the way (the
    `.harness` folder or the file itself) is refused: a cloned repository could point it anywhere."""
    parts = rel.split("/")
    for i in range(1, len(parts) + 1):
        if os.path.islink(os.path.join(repo, *parts[:i])):
            raise ValueError(f"{'/'.join(parts[:i])} is a symbolic link: nothing was written, remove the link first")
    target = game_run.inside(repo, rel)
    if target is None:
        raise ValueError(f"{rel} is outside the repository: nothing was written")
    folder = os.path.dirname(target)
    try:
        os.makedirs(folder, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=folder, prefix="." + os.path.basename(target) + ".")
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(text)
        os.replace(tmp, target)
    except OSError as exc:
        raise ValueError(f"{rel}: {exc}") from exc


def write_config(path: str, config: dict[str, Any]) -> None:
    repo = os.path.dirname(os.path.dirname(path))
    safe_write(repo, os.path.relpath(path, repo).replace(os.sep, "/"),
               json.dumps(config, ensure_ascii=False, indent=2) + "\n")


def with_game(config: dict[str, Any], **changes: Any) -> dict[str, Any]:
    """A new config whose game block carries the changes; a change to None removes the key."""
    block = {**game_block(config), **changes}
    return {**config, BLOCK: {k: v for k, v in block.items() if v is not None}}


# --- the pieces --------------------------------------------------------------------------------

def _instruction_text(repo: str) -> tuple[str | None, str]:
    source = facts.instruction_facts(repo)["source"].get("path")
    if not source:
        return None, ""
    return source, facts.resolve_includes(repo, _read(os.path.join(repo, source)) or "")


def _said(text: str, needle: str) -> bool:
    return bool(needle) and needle.lower() in text.lower()


def _token(text: str, needle: str) -> bool:
    """The needle as a word of its own: `.tscn` in "edit `.tscn` files", not `.unity` in docs.unity3d.com."""
    return bool(needle) and re.search(rf"(?<![\w./-]){re.escape(needle)}(?![\w-])", text, re.I) is not None


def commands_of(block: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """The recorded commands, each an object; anything else in the block is left out."""
    commands = block.get("commands")
    return {k: v for k, v in commands.items() if isinstance(v, dict)} if isinstance(commands, dict) else {}


def results_of(repo: str, harness_dir: str = ".harness") -> dict[str, Any]:
    data = facts.load_json(os.path.join(repo, harness_dir, game_run.RESULTS))
    return data if isinstance(data, dict) else {}


def judged_with(spec: dict[str, Any], engine: dict[str, Any] | None, piece: str) -> dict[str, Any]:
    """The spec as the engine found today judges it: its error lines added, its exit code distrusted when
    the engine's is. A command recorded before the engine was known, or for another one, is judged right."""
    if not engine or piece == "run":
        return spec
    errors = list(dict.fromkeys(list(spec.get("errors") or []) + list(engine.get("errors", []))))
    trusted = spec.get("exit_code_trusted", True) is not False and engine.get("exit_code_trusted", True) is not False
    return {**spec, "errors": errors, "exit_code_trusted": trusted}


def _piece_command(piece: str, spec: dict[str, Any] | None, engine: dict[str, Any] | None,
                   candidate: str | None, result: Any) -> dict[str, Any]:
    if not isinstance(spec, dict):
        how = f'harness game command {piece} "{candidate}"' if candidate else f'harness game command {piece} "<command>"'
        return {"state": "missing", "detail": "no command recorded", "how": how + (
            f", then `harness game run {piece}`" if piece != "run" else "")}
    command = spec.get("run")
    if not isinstance(command, str) or not command.strip():
        return {"state": "weak", "detail": "recorded with no command", "how": f'harness game command {piece} "<command>"'}
    published = game_run.publishing(command)
    if published:
        return {"state": "weak", "detail": f"`{command}` publishes (`{published}`): the judge refuses to run it",
                "how": f'harness game command {piece} --remove, then record a command that does not publish'}
    judged = judged_with(spec, engine, piece)
    gaps = []
    if engine and piece != "run" and (judged.get("errors") != list(spec.get("errors") or [])
                                      or judged.get("exit_code_trusted") != spec.get("exit_code_trusted", True)):
        gaps.append(f"recorded without {engine['name']}'s error lines of today (before the engine was known, "
                    "for another engine, or by an older profile): record it again")
    if piece == "smoke" and judged.get("exit_code_trusted") is False and not spec.get("ready"):
        gaps.append("no ready line recorded, and this engine exits 0 on errors")
    if piece in ("capture", "export") and not spec.get("output"):
        gaps.append("no output file recorded: nothing says the run wrote it")
    if piece != "run" and not gaps:
        last = result if isinstance(result, dict) and result.get("command") == command else None
        if last is None:
            gaps.append(f"never judged: `harness game run {piece}`")
        elif not last.get("passed"):
            gaps.append(f"its last judged run failed ({last.get('date')}): `harness game run {piece}`")
    detail = f"`{command}`" + (f" ({'; '.join(gaps)})" if gaps else "")
    how = None
    if gaps:
        option = {"smoke": " --ready \"<line the game prints>\"", "capture": " --output <file>", "export": " --output <file>"}
        how = (f'harness game command {piece} "{command}"{option.get(piece, "")}' if "record" in gaps[0] or "recorded" in gaps[0]
               else f"harness game run {piece}")
    return {"state": "weak" if gaps else "ok", "detail": detail, "how": how}


def _playtest(repo: str, files: dict[str, Any], block: dict[str, Any], days: int | None,
              today: date) -> dict[str, Any]:
    log = block.get("playtest_log") or _first(repo, files["playtest_logs"])
    dates: list[str] = []
    where = None
    if log and os.path.isfile(os.path.join(repo, log)):
        where = log
        dates = DATE_RE.findall(_read(os.path.join(repo, log)) or "")
    state = facts.load_json(os.path.join(repo, files["design_state"]))
    tests = state.get("playtests") if isinstance(state, dict) and isinstance(state.get("playtests"), list) else []
    if tests:
        where = where or files["design_state"]
        dates += [str(t.get(k)) for t in tests if isinstance(t, dict) for k in ("date", "day", "at")
                  if isinstance(t.get(k), str) and DATE_RE.match(str(t.get(k)))]
        dates += _journal_dates(repo, files["design_journal"])
    how = "after a person plays a build, add a dated line to docs/playtests.md: the date, who played, which build, where they hesitated, where they stopped"
    if not where:
        return {"state": "missing", "detail": "no playtest written down", "how": how}
    last = max((d[:10] for d in dates), default=None)
    if not last:
        return {"state": "weak", "detail": f"{where} has no date", "how": "date each playtest (YYYY-MM-DD) in docs/playtests.md"}
    age = facts.days_since(last, today)
    if days is not None and age is not None and age > days:
        return {"state": "stale", "detail": f"last playtest {last}, {age} days ago (more than {days})", "how": how}
    return {"state": "ok", "detail": f"last playtest {last} in {where}", "how": None}


def _journal_dates(repo: str, rel: str) -> list[str]:
    """The days a design workshop's journal recorded a playtest step (`{"ts": …, "skill": "playtest"}`)."""
    out = []
    for line in (_read(os.path.join(repo, rel)) or "").splitlines():
        try:
            entry = json.loads(line)
        except ValueError:
            continue
        if isinstance(entry, dict) and "playtest" in str(entry.get("skill", "")) and re.match(r"\d{4}-\d{2}-\d{2}", str(entry.get("ts", ""))):
            out.append(str(entry["ts"])[:10])
    return out


def _scope(repo: str, files: dict[str, Any], block: dict[str, Any]) -> dict[str, Any]:
    doc = block.get("scope_file") or _first(repo, files["design_docs"])
    how = "write a one-page design with a cut list (a heading such as \"Cut\" or \"Later\") in docs/design.md"
    if not doc or not os.path.isfile(os.path.join(repo, doc)):
        return {"state": "missing", "detail": "no design file", "how": how}
    text = _read(os.path.join(repo, doc)) or ""
    heading = re.compile(rf"^#{{1,6}}\s.*\b(?:{files['cut_heading']})\b", re.I | re.M)
    if not heading.search(text):
        return {"state": "weak", "detail": f"{doc} has no cut list", "how": f"add a cut list heading to {doc}"}
    return {"state": "ok", "detail": f"cut list in {doc}", "how": None, "file": doc}


def asset_files(repo: str, profile: dict[str, Any], block: dict[str, Any]) -> list[str]:
    skip = set(profile["files"]["skip_dirs"]) | {"shots", "screenshots"}
    outputs = {os.path.dirname(str(spec.get("output") or "")) for spec in commands_of(block).values()
               if isinstance(spec.get("output"), str)}
    exts = tuple(profile["files"]["asset_extensions"])
    return [rel for rel in _walk(repo, skip) if rel.lower().endswith(exts)
            and not any(o and rel.startswith(o + "/") for o in outputs)]


def _credited(rel: str, text: str) -> bool:
    """The file's name, or one of its folders written as a folder (`enemies/`, `sprites/enemies`), as a
    word of its own: "credit the enemies later" names no folder, `superhero.png` is not `hero.png`."""
    if _token(text, os.path.basename(rel)):
        return True
    parts = rel.split("/")[:-1]
    for i in range(len(parts)):
        path = "/".join(parts[: i + 1])
        if "/" in path and _token(text, path):
            return True
        if parts[i].lower() not in GENERIC_DIRS and _token(text, parts[i] + "/"):
            return True
    return False


def _assets(repo: str, profile: dict[str, Any], block: dict[str, Any]) -> dict[str, Any]:
    found = asset_files(repo, profile, block)
    if not found:
        return {"state": "n/a", "detail": "no asset yet", "how": None}
    credits = block.get("credits_file") or _first(repo, profile["files"]["credits"])
    how = "list each asset in CREDITS.md: file or folder, source, licence, author; a placeholder says so"
    if not credits or not os.path.isfile(os.path.join(repo, credits)):
        return {"state": "missing", "detail": f"{len(found)} asset file(s), no credits file", "how": how}
    text = _read(os.path.join(repo, credits)) or ""
    missing = [rel for rel in found if not _credited(rel, text)]
    if missing:
        shown = ", ".join(missing[:5]) + (f" and {len(missing) - 5} more" if len(missing) > 5 else "")
        return {"state": "weak", "detail": f"{len(missing)} of {len(found)} asset(s) not in {credits}: {shown}",
                "how": f"add them to {credits}", "file": credits}
    return {"state": "ok", "detail": f"{len(found)} asset(s), all in {credits}", "how": None, "file": credits}


def _ci(repo: str, profile: dict[str, Any], commands: dict[str, Any]) -> dict[str, Any]:
    texts = {}
    for entry in profile["files"]["workflows"]:
        full = os.path.join(repo, entry)
        if os.path.isfile(full):
            texts[entry] = _read(full) or ""
        elif os.path.isdir(full):
            for name in sorted(os.listdir(full)):
                if name.endswith((".yml", ".yaml")):
                    texts[f"{entry}/{name}"] = _read(os.path.join(full, name)) or ""
    how = f"a CI job that runs `{RUNNER_CALL} all` on every change"
    if not texts:
        return {"state": "missing", "detail": "no CI workflow", "how": how}
    judge = re.compile(r"(?<![\w-])(?:\.harness/game_loop\.py|harness(?:\.py)?\s+game\s+run)\b")
    hit = next((path for path, text in texts.items()
                if any(judge.search(line) and not line.lstrip().startswith("#") for line in text.splitlines())), None)
    if hit:
        return {"state": "ok", "detail": f"the judge is run by {hit}", "how": None, "file": hit}
    raw = [spec["run"] for spec in commands.values() if isinstance(spec.get("run"), str)]
    step = re.compile(r"^\s*(?:-\s*)?(?:run:\s*)?(.+?)\s*$")
    direct = next((path for path, text in texts.items()
                   for line in text.splitlines() for m in [step.match(line)] if m and m.group(1) in raw), None)
    if direct:
        return {"state": "weak", "detail": f"{direct} runs a recorded command itself, not judged by its log",
                "how": f"run `{RUNNER_CALL} all` in {direct} instead"}
    return {"state": "missing", "detail": "the CI does not run the judge", "how": how}


def _runner(repo: str) -> dict[str, Any]:
    path = os.path.join(repo, ".harness", "game_loop.py")
    if not os.path.isfile(path):
        return {"state": "missing", "detail": "not in the repository", "how": "harness game runner --write"}
    if _read(path) != _read(RUNNER_SOURCE):
        return {"state": "weak", "detail": ".harness/game_loop.py differs from the plugin's (older, or edited by hand)",
                "how": "harness game runner --write"}
    return {"state": "ok", "detail": f"`{RUNNER_CALL} all`", "how": None}


def _instructions(repo: str, found: dict[str, Any], engine: dict[str, Any] | None,
                  commands: dict[str, Any], scale_pieces: list[str]) -> dict[str, Any]:
    source, text = _instruction_text(repo)
    how = "harness game instructions: the lines to add, then add them"
    if not source:
        return {"state": "missing", "detail": "no instruction file (AGENTS.md)", "how": how}
    gaps = []
    if found["id"] and not _said(text, found["engine_name"]) and not _said(text, (engine or {}).get("name", "")):
        gaps.append(f"the engine ({found['engine_name']})")
    if found.get("version") and not _said(text, found["version"]):
        gaps.append(f"its version ({found['version']})")
    told_runner = "game_loop.py" in text
    for piece in scale_pieces:
        spec = commands.get(piece)
        if piece in COMMAND_PIECES and isinstance(spec, dict) and not (
                _said(text, spec.get("run", "")) or (told_runner and piece != "run")):
            gaps.append(f"the {piece} command")
    if gaps:
        return {"state": "weak", "detail": f"{source} does not say {', '.join(gaps)}", "how": how}
    return {"state": "ok", "detail": f"{source} names the engine and the loop", "how": None}


def _owned(repo: str, engine: dict[str, Any] | None) -> dict[str, Any]:
    owned = (engine or {}).get("owned") or []
    if not owned:
        return {"state": "n/a", "detail": "this engine keeps no serialised files to protect", "how": None}
    _, text = _instruction_text(repo)
    extensions = [ext for ext in owned if ext.startswith(".")]
    if any(_token(text, ext) for ext in extensions):
        return {"state": "ok", "detail": "named in the instruction file", "how": None}
    return {"state": "missing", "detail": f"the instruction file does not name {', '.join(extensions[:4])}",
            "how": "harness game instructions gives the line"}


def _version_piece(found: dict[str, Any]) -> dict[str, Any]:
    if not found["id"]:
        return {"state": "missing", "detail": "no engine recognised",
                "how": "harness game set --engine <id> (harness game profile lists them), or start the project"}
    if not found.get("pinnable", True):
        return {"state": "n/a", "detail": f"{found['name']}: no engine to pin", "how": None}
    if not found.get("version"):
        where = found.get("version_file") or "the project files"
        return {"state": "missing", "detail": f"{found['name']} found ({found['evidence']}), no version in {where}",
                "how": f"pin the engine version in {where}"}
    return {"state": "ok", "detail": f"{found['name']} {found['version']}, in {found['version_file']}", "how": None}


def loop(repo: str, profile: dict[str, Any], scale: str | None = None, today: date | None = None,
         harness_dir: str = ".harness") -> dict[str, Any]:
    """Every piece of the loop, its state for the scale, and the next one to set up."""
    today = today or date.today()
    block = game_block(read_config(config_path(repo, harness_dir)))
    scale = scale or block.get("scale")
    if scale is not None and scale not in profile["scales"]:
        raise ValueError(f"{scale} is not a scale ({', '.join(profile['scales'])})")
    found = detect(repo, profile, block.get("engine"))
    engine = profile["engines"].get(found["id"]) if found["id"] else None
    commands = commands_of(block)
    results = results_of(repo, harness_dir)
    in_scale = profile["scales"][scale or "weeks"]["pieces"]
    days = block.get("playtest_days", profile["scales"][scale]["playtest_days"] if scale else None)
    rows = []
    for piece in profile["pieces"]:
        pid = piece["id"]
        if pid not in in_scale:
            row = {"state": "later", "detail": "not at this scale", "how": None}
        elif pid == "version":
            row = _version_piece(found)
        elif pid in COMMAND_PIECES:
            row = _piece_command(pid, commands.get(pid), engine, (engine or {}).get("candidates", {}).get(pid),
                                 results.get(pid))
        elif pid == "runner":
            row = _runner(repo)
        elif pid == "instructions":
            row = _instructions(repo, found, engine, commands, in_scale)
        elif pid == "owned_files":
            row = _owned(repo, engine)
        elif pid == "playtest":
            row = _playtest(repo, profile["files"], block, days, today)
        elif pid == "scope":
            row = _scope(repo, profile["files"], block)
        elif pid == "assets":
            row = _assets(repo, profile, block)
        else:
            row = _ci(repo, profile, commands)
        rows.append({"id": pid, "label": piece["label"], "gives": piece["gives"], **row})
    todo = [r for r in rows if r["state"] in ("missing", "weak", "stale")]
    if scale is None:
        upcoming = {"id": "scale", "label": "Choose the scale of the game",
                    "how": "harness game set --scale hour|jam|weeks",
                    "gives": "the loop asks only for what this size of game needs"}
    else:
        upcoming = todo[0] if todo else None
    counted = [r for r in rows if r["state"] not in ("later", "n/a")]
    return {"schema": "harness-game-loop/1", "scale": scale,
            "scale_label": profile["scales"][scale]["label"] if scale else None,
            "engine": found, "pieces": rows, "next": upcoming,
            "in_place": sum(1 for r in counted if r["state"] == "ok"), "counted": len(counted),
            "suggested_target": profile["scales"][scale]["suggested_target"] if scale else None,
            "owner_actions": (engine or {}).get("owner_actions", []), "notes": (engine or {}).get("notes", []),
            "commands_checked": (engine or {}).get("commands_checked", True)}


def render_loop(result: dict[str, Any]) -> str:
    found = result["engine"]
    engine = f"{found['name']} {found['version'] or '(version not pinned)'}" if found["id"] else "no engine recognised"
    scale = result["scale_label"] or "not chosen yet: every piece is shown"
    out = [f"Game loop — scale: {scale}; engine: {engine}",
           f"{result['in_place']} of {result['counted']} pieces in place.", ""]
    for row in result["pieces"]:
        out.append(f"{MARKS[row['state']]} {row['label']} — {row['detail']}")
    nxt = result["next"]
    out.append("")
    if nxt:
        out.append(f"Next: {nxt['label']}. It gives: {nxt['gives']}.")
        if nxt.get("how"):
            out.append(f"  How: {nxt['how']}")
    else:
        out.append("Every piece of this scale is in place. Feel and fun are still the owner's to judge, by playing.")
    if not result.get("commands_checked", True):
        out.append(f"The {found['name']} commands of the profile were not checked on a primary source: confirm each by running it.")
    if result["owner_actions"]:
        out.append("Only the owner can: " + "; ".join(result["owner_actions"]) + ".")
    return "\n".join(out) + "\n"


# --- instructions ------------------------------------------------------------------------------

def instructions(repo: str, profile: dict[str, Any], today: date | None = None,
                 harness_dir: str = ".harness") -> dict[str, Any]:
    """The candidate lines of the instruction file for this game, each filled from what is measured."""
    today = today or date.today()
    result = loop(repo, profile, None, today, harness_dir)
    block = game_block(read_config(config_path(repo, harness_dir)))
    scale = block.get("scale")
    found = result["engine"]
    engine = profile["engines"].get(found["id"]) if found["id"] else {}
    commands = commands_of(block)
    rows = {r["id"]: r for r in result["pieces"]}
    pieces = set(profile["scales"][scale or "weeks"]["pieces"])
    runner_written = _runner(repo)["state"] == "ok"
    ci = _ci(repo, profile, commands)
    capture = commands.get("capture") if isinstance(commands.get("capture"), dict) else {}
    values = {
        "engine": found.get("engine_name") or "the engine", "version": found.get("version") or "<pin the version first>",
        "version_file": found.get("version_file") or "<the project file>", "month": today.strftime("%Y-%m"),
        "loop_all": f"{RUNNER_CALL} all", "capture_cmd": f"{RUNNER_CALL} capture",
        "capture_output": capture.get("output") or "<the capture file>",
        "owned_rule": (engine or {}).get("owned_rule", ""),
        "test_cmd": f"{RUNNER_CALL} test",
        "run_cmd": (commands.get("run") or {}).get("run") if isinstance(commands.get("run"), dict) else "<the run command>",
        "scope_file": rows.get("scope", {}).get("file") or block.get("scope_file") or "docs/design.md",
        "credits_file": rows.get("assets", {}).get("file") or block.get("credits_file") or "CREDITS.md",
        "enforced": f"Enforced by: `{ci['file']}`" if ci["state"] == "ok" else "(unverified)",
        "judge_enforced": "Enforced by: `.harness/game_loop.py`" if runner_written else "(unverified)",
    }
    when = {
        "engine": bool(found["id"]), "commands": isinstance(commands.get("smoke"), dict),
        "run_no_smoke": isinstance(commands.get("run"), dict) and not isinstance(commands.get("smoke"), dict),
        "capture": bool(capture.get("output")) and "capture" in pieces,
        "untrusted_exit": (engine or {}).get("exit_code_trusted") is False and "smoke" in pieces,
        "owned": bool((engine or {}).get("owned_rule")), "always": True,
        "prototype": scale in ("hour", "jam"), "production": scale == "weeks" and isinstance(commands.get("test"), dict),
        "scope": scale in ("jam", "weeks"), "assets": scale in ("jam", "weeks"),
    }
    data = profile["instructions"]
    lines = [{"id": l["id"], "text": l["text"].format(**values)} for l in data["lines"] if when[l["when"]]]
    forbidden = [{"id": l["id"], "text": l["text"].format(**values)} for l in data["forbidden"] if when[l["when"]]]
    questions = [q for q in data["questions"] if scale is None or scale in q.get("scales", [scale])]
    notes = []
    if "smoke" in pieces and not when["commands"]:
        notes.append("record the smoke command first (`harness game command smoke \"…\"`): the loop line needs it")
    if "runner" in pieces and not runner_written:
        notes.append("the lines call `.harness/game_loop.py`: write it with `harness game runner --write`")
    if not found.get("version"):
        notes.append("the engine version is not pinned: the engine line says so until it is")
    if engine and engine.get("commands_checked") is False:
        notes.append(f"the {engine['name']} commands of the profile were not checked on a primary source: confirm each by running it")
    source, text = _instruction_text(repo)
    current = len(text.splitlines()) if source else 0
    added = len(lines) + len(forbidden)
    return {"schema": "harness-game-instructions/1", "section": data["section"], "lines": lines,
            "forbidden": forbidden, "questions": questions, "notes": notes, "source": source,
            "lines_now": current, "lines_after": current + added, "limit": 60,
            "enforced_share": _enforced_share(repo, lines + forbidden)}


def _enforced_share(repo: str, added: list[dict[str, str]]) -> dict[str, Any]:
    """Level 3 asks that half the rules say what enforces them: the lines proposed here move that share."""
    source = facts.instruction_facts(repo)["source"]
    total, guarded = source.get("rules_total") or 0, source.get("rules_guarded") or 0
    new_guarded = sum(1 for line in added if facts.GUARDED_RE.search(line["text"]))
    after_total, after_guarded = total + len(added), guarded + new_guarded
    return {"before": [guarded, total], "after": [after_guarded, after_total],
            "half_before": total > 0 and guarded * 2 >= total, "half_after": after_guarded * 2 >= after_total}


def render_instructions(result: dict[str, Any]) -> str:
    out = ["Candidate lines for the instruction file. Confirm each with the owner; keep the commands word for word,",
           "translate the rest into the repository's language.", "", f"Under {result['section']}:", ""]
    out += [l["text"] for l in result["lines"]]
    if result["forbidden"]:
        out += ["", "Under Forbidden:", ""] + [l["text"] for l in result["forbidden"]]
    where = result["source"] or "a new AGENTS.md"
    out += ["", f"Length: {where} has {result['lines_now']} lines; with these, about {result['lines_after']} "
                f"of the {result['limit']} a level-1 file may hold."]
    if result["lines_after"] > result["limit"]:
        out.append("Over the limit: keep the lines the agent needs at every change (engine, loop, engine files, feel) and drop the others.")
    share = result["enforced_share"]
    out.append(f"Rules that say what enforces them: {share['before'][0]} of {share['before'][1]} today, "
               f"{share['after'][0]} of {share['after'][1]} with these. Level 3 asks for half"
               + (": these lines take the file under it." if share["half_before"] and not share["half_after"] else "."))
    if result["questions"]:
        out += ["", "Questions only the owner answers (not lines of the file):"]
        out += [f"{i}. {q['ask']} — why: {q['why']}" for i, q in enumerate(result["questions"], 1)]
    out += [f"Note: {n}" for n in result["notes"]]
    return "\n".join(out) + "\n"


# --- commands ----------------------------------------------------------------------------------

def record_command(config: dict[str, Any], profile: dict[str, Any], engine_id: str | None, piece: str,
                   command: str | None, ready: str | None, output: str | None, timeout: int | None,
                   remove: bool, today: date) -> dict[str, Any]:
    """A new config with the piece's command recorded (or removed), and what judges it."""
    if piece not in COMMAND_PIECES:
        raise ValueError(f"{piece} is not a piece with a command ({', '.join(COMMAND_PIECES)})")
    block = game_block(config)
    if "commands" in block and not isinstance(block["commands"], dict):
        raise ValueError("game.commands in .harness/config.json is not an object: fix or remove it, nothing was written")
    commands = dict(block.get("commands") or {})
    if remove:
        if piece not in commands:
            raise ValueError(f"no command is recorded for {piece}")
        rest = {k: v for k, v in commands.items() if k != piece}
        return with_game(config, commands=rest or None)
    scale = block.get("scale")
    if scale in profile["scales"] and piece not in profile["scales"][scale]["pieces"]:
        raise ValueError(f"{piece} is not a piece of the {scale} scale: the loop does not ask for it "
                         "(`harness game set --scale …` widens the scale)")
    command = (command or "").strip()
    if not command:
        raise ValueError(f'give the command: harness game command {piece} "<command>"')
    published = game_run.publishing(command)
    if published:
        raise ValueError(f"refused: `{published}`: {game_run.PUBLISH_WHY}")
    if output and (os.path.isabs(output) or os.path.normpath(output).split(os.sep)[0] == ".."):
        raise ValueError(f"--output {output} is outside the repository: give a path inside it")
    for name, value in (("ready", ready),):
        if value:
            try:
                re.compile(value)
            except re.error as exc:
                raise ValueError(f"--{name} is not a valid regular expression: {exc}") from exc
    if timeout is not None and timeout <= 0:
        raise ValueError("--timeout is a number of seconds, more than 0")
    engine = profile["engines"].get(engine_id or "") or {}
    spec: dict[str, Any] = {"run": command, "date": today.isoformat()}
    if piece != "run":
        spec["errors"] = list(engine.get("errors", []))
        spec["exit_code_trusted"] = engine.get("exit_code_trusted", True)
    if ready:
        spec["ready"] = ready
    default = (engine.get("outputs") or {}).get(piece) or {}
    if default.get("output") and (not output or output == default.get("match")) \
            and (default.get("match") or default["output"]) in command:
        output = default["output"]      # Godot's movie writer numbers its frames: shots/frame.png gives frame00000000.png
    if output:
        spec["output"] = output.replace(os.sep, "/")
        if default.get("output_errors") and spec["output"] == default.get("output"):
            spec["output_errors"] = list(default["output_errors"])
    if timeout:
        spec["timeout"] = timeout
    return with_game(config, commands={**commands, piece: spec})


# --- the command line --------------------------------------------------------------------------

def build_parser(parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
    sub = parser.add_subparsers(dest="action", required=True)
    p = sub.add_parser("loop", help="the pieces of the loop: in place, missing, the next one")
    p.add_argument("repo", nargs="?", default=".")
    p.add_argument("--scale", help="hour, jam or weeks (default: the one chosen with `game set`)")
    p.add_argument("--today", help="YYYY-MM-DD, for reproducible output")
    p.add_argument("--format", choices=["md", "json"], default="md")
    p = sub.add_parser("detect", help="the engine, its version and where they were read")
    p.add_argument("repo", nargs="?", default=".")
    p.add_argument("--format", choices=["md", "json"], default="md")
    p = sub.add_parser("set", help="writes the owner's choices for the game in .harness/config.json")
    p.add_argument("--repo", default=".")
    p.add_argument("--scale", help="hour, jam or weeks")
    p.add_argument("--engine", help="an engine id of `harness game profile`, when the files do not say it")
    p.add_argument("--playtest-days", type=int, help="how old the last playtest may be, in days")
    p.add_argument("--playtest-log", help="the file where playtests are written down")
    p.add_argument("--scope-file", help="the design file that holds the cut list")
    p.add_argument("--credits-file", help="the file that lists each asset's source and licence")
    p = sub.add_parser("command", help="records the command of a piece, with what judges it")
    p.add_argument("piece", help=", ".join(COMMAND_PIECES))
    p.add_argument("cmd", nargs="?", help="the command, quoted")
    p.add_argument("--repo", default=".")
    p.add_argument("--ready", help="a line the game prints once started; the run fails without it")
    p.add_argument("--output", help="the file the run must write (a screenshot, a build), relative to the repository")
    p.add_argument("--timeout", type=int, help="seconds before the run is stopped and failed")
    p.add_argument("--remove", action="store_true", help="removes the recorded command")
    p = sub.add_parser("run", help="runs recorded pieces and judges them")
    p.add_argument("piece", help="check, test, smoke, capture, export or all")
    p.add_argument("--repo", default=".")
    p.add_argument("--timeout", type=int)
    p = sub.add_parser("runner", help="the judge copied into the repository, for the agent and the CI")
    p.add_argument("repo", nargs="?", default=".")
    p.add_argument("--write", action="store_true", help="writes .harness/game_loop.py")
    p = sub.add_parser("instructions", help="the lines the instruction file needs for a game, as candidates")
    p.add_argument("repo", nargs="?", default=".")
    p.add_argument("--today", help="YYYY-MM-DD, for reproducible output")
    p.add_argument("--format", choices=["md", "json"], default="md")
    p = sub.add_parser("profile", help="the scales, the pieces and the engines the profile knows")
    p.add_argument("--format", choices=["md", "json"], default="md")
    return parser


def _fail(message: str) -> int:
    print(f"harness game: {message}", file=sys.stderr)
    return 2


def _today(value: str | None) -> date:
    if not value:
        return date.today()
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"--today {value} is not a date (YYYY-MM-DD)") from exc


def _emit(data: Any, fmt: str, render) -> None:
    if fmt == "json":
        json.dump(data, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
    else:
        sys.stdout.write(render(data))


def render_detect(found: dict[str, Any]) -> str:
    if not found["id"]:
        return "No engine recognised. `harness game profile` lists the engines; `harness game set --engine <id>` chooses one.\n"
    out = [f"Engine: {found['name']} (id {found['id']}), found by {found['evidence']}.",
           f"Version: {found['version']} in {found['version_file']}." if found["version"]
           else f"Version: not pinned{' (' + found['version_file'] + ')' if found.get('version_file') else ''}."]
    if found["others"]:
        out.append(f"Also found: {', '.join(found['others'])} (`harness game set --engine <id>` chooses).")
    return "\n".join(out) + "\n"


def render_profile(profile: dict[str, Any]) -> str:
    labels = {p["id"]: p["label"] for p in profile["pieces"]}
    out = ["Scales:"]
    for sid, scale in profile["scales"].items():
        out.append(f"- {sid} ({scale['label']}): {scale['plain']}.")
        out.append(f"  Pieces: {', '.join(scale['pieces'])}.")
    out += ["", "Pieces:"] + [f"- {pid}: {label}" for pid, label in labels.items()]
    out += ["", "Engines:"]
    for eid, engine in profile["engines"].items():
        out.append(f"- {eid}: {engine['name']}" + ("" if engine.get("exit_code_trusted", True)
                                                     else " (exit code does not tell errors: judged by the log)"))
    return "\n".join(out) + "\n"


def _set(args: argparse.Namespace, profile: dict[str, Any], path: str) -> int:
    if args.scale and args.scale not in profile["scales"]:
        return _fail(f"{args.scale} is not a scale ({', '.join(profile['scales'])})")
    if args.engine and args.engine not in profile["engines"]:
        return _fail(f"{args.engine} is not an engine the profile knows ({', '.join(profile['engines'])})")
    if args.playtest_days is not None and args.playtest_days < 0:
        return _fail("--playtest-days is a number of days, 0 or more")
    changes = {k: v for k, v in (("scale", args.scale), ("engine", args.engine), ("playtest_days", args.playtest_days),
                                 ("playtest_log", args.playtest_log), ("scope_file", args.scope_file),
                                 ("credits_file", args.credits_file)) if v is not None}
    if not changes:
        return _fail("nothing to set: give --scale, --engine, --playtest-days, --playtest-log, --scope-file or --credits-file")
    write_config(path, with_game(read_config(path), **changes))
    said = ", ".join(f"{k} = {v}" for k, v in changes.items())
    print(f"Written to .harness/config.json: {said}. The level ladder does not change.")
    if "scale" in changes:
        scale = profile["scales"][changes["scale"]]
        print(f"At this scale ({scale['label']}) the loop has {len(scale['pieces'])} pieces; "
              f"a level-{scale['suggested_target']} target fits it (`harness target {scale['suggested_target']}`), if you want one.")
    return 0


def main(args: argparse.Namespace) -> int:
    profile = load_profile()
    action = args.action
    if action == "profile":
        _emit(profile, args.format, render_profile)
        return 0
    repo = getattr(args, "repo", ".")
    if not os.path.isdir(repo):
        return _fail(f"{repo} is not a directory")
    repo = os.path.abspath(repo)
    path = config_path(repo)
    try:
        if action == "loop":
            _emit(loop(repo, profile, args.scale, _today(args.today)), args.format, render_loop)
            return 0
        if action == "detect":
            chosen = game_block(read_config(path)).get("engine")
            _emit(detect(repo, profile, chosen), args.format, render_detect)
            return 0
        if action == "instructions":
            _emit(instructions(repo, profile, _today(args.today)), args.format, render_instructions)
            return 0
        if action == "set":
            return _set(args, profile, path)
        if action == "command":
            config = read_config(path)
            found = detect(repo, profile, game_block(config).get("engine"))
            write_config(path, record_command(config, profile, found["id"], args.piece, args.cmd, args.ready,
                                              args.output, args.timeout, args.remove, date.today()))
            print(f"{args.piece}: " + ("removed" if args.remove else f"recorded `{args.cmd.strip()}`")
                  + (f", judged with {found['name']}'s error lines" if found["id"] and args.piece != "run" and not args.remove else "")
                  + ". Written to .harness/config.json." + ("" if args.remove or args.piece == "run"
                                                            else f" Try it: harness game run {args.piece}"))
            return 0
        if action == "run":
            block = game_block(read_config(path))
            engine = profile["engines"].get(detect(repo, profile, block.get("engine"))["id"] or "")
            commands = {p: judged_with(spec, engine, p) for p, spec in commands_of(block).items()}
            return game_run.run(args.piece, repo, args.timeout, commands=commands)
        if action == "runner":
            state = _runner(repo)
            if args.write:
                safe_write(repo, ".harness/game_loop.py", _read(RUNNER_SOURCE) or "")
                print(f"Written: .harness/game_loop.py. Run it with `{RUNNER_CALL} all` (or one piece: check, test, smoke, capture, export).")
                return 0
            print(f"{MARKS[state['state']]} {state['detail']}" + (f" — {state['how']}" if state["how"] else ""))
            return 0
    except ValueError as exc:
        return _fail(str(exc))
    return _fail(f"unknown action {action}")
