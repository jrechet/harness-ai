"""The simulated owner of a sample project: it only answers what it is asked.

Giving the evaluated agent every answer in advance (`owner.md`) does not measure the interview: a fact
the owner volunteers is collected even by a skill that asks no question. Here the answers are in
`owner.json`, each behind trigger words, and `bench init` serves them during the session: the agent
asks its questions through a command in the kit, the bench answers and keeps the exchange. Nothing is
random, no model plays the owner: the same question always gets the same answer.

Format of `owner.json`:
    {"intro": "who they are, told to the agent up front (optional)",
     "answers": [{"id": "mode", "any_of": ["mode", "délég*", "delegat*"], "answer": "…"},
                 {"id": "oral", "fact": "I6", "any_of": ["nulle part", "nowhere", "redi*"], "answer": "…"}],
     "default": "what they answer when nothing matches"}

A trigger is a word or a sequence of words, matched as whole words, ignoring case and accents;
`délég*` accepts any word ending, so does `remarque* en revue`. Matching does not depend on the
language: a French question matches French triggers, an English question English ones, so an owner
who must hear both carries triggers in both. `fact` links an answer to a `must_surface` fact of the
answer key: that is what tells, afterwards, whether the interview went and fetched that fact.
"""
from __future__ import annotations

import json
import os
import re
import socket
import socketserver
import threading
import unicodedata
from typing import Any

FILE = "owner.json"
CLIENT_FILE = "ask_owner.py"

CLIENT = '''#!/usr/bin/env python3
"""Asks the repository owner questions and prints the answers. One question per argument."""
import json
import socket
import sys

questions = [a.strip() for a in sys.argv[1:] if a.strip()]
if not questions and not sys.stdin.isatty():
    questions = [line.strip() for line in sys.stdin if line.strip()]
if not questions:
    sys.exit('usage: ask_owner.py "first question" "second question"')
with socket.create_connection(("127.0.0.1", {port}), timeout=30) as conn:
    conn.sendall((json.dumps({{"questions": questions}}) + "\\n").encode("utf-8"))
    reply = json.loads(conn.makefile(encoding="utf-8").readline())
for question, answer in zip(questions, reply["answers"]):
    print(f"Q: {{question}}\\nA: {{answer}}\\n")
'''


def load(fixture_dir: str) -> dict[str, Any] | None:
    path = os.path.join(fixture_dir, FILE)
    if not os.path.isfile(path):
        return None
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def fold(text: str) -> str:
    """Lowercase, no accents, straight apostrophes: "Délégation" and "delegation" are equal."""
    text = unicodedata.normalize("NFD", text.replace("’", "'"))
    return "".join(c for c in text if not unicodedata.combining(c)).lower()


def _pattern(keyword: str) -> re.Pattern[str]:
    """A trigger: a word or a sequence of words, each of which may end with `*`."""
    parts = []
    for word in fold(keyword).split():
        parts.append(re.escape(word[:-1]) + r"\w*" if word.endswith("*") else re.escape(word) + r"(?!\w)")
    return re.compile(r"(?<!\w)" + r"\s+".join(parts))


def answer(owner: dict[str, Any], question: str) -> tuple[list[str], str]:
    """The answers the question triggers, in file order, and their ids.
    A question that triggers nothing gets the default answer."""
    low = fold(question)
    hits = [a for a in owner.get("answers", []) if any(_pattern(k).search(low) for k in a["any_of"])]
    if not hits:
        return [], owner.get("default", "I don't know.")
    return [a["id"] for a in hits], "\n".join(a["answer"] for a in hits)


class Interview:
    """The owner listening during a session. `port` is the one the kit's command calls;
    `log` keeps each question, the answer given and what triggered it."""

    def __init__(self, owner: dict[str, Any]):
        self.owner = owner
        self.log: list[dict[str, Any]] = []
        lock = threading.Lock()
        interview = self

        class Handler(socketserver.StreamRequestHandler):
            def handle(self) -> None:
                try:
                    questions = json.loads(self.rfile.readline().decode("utf-8")).get("questions", [])
                except (ValueError, AttributeError):
                    questions = []
                answers = []
                for question in questions:
                    ids, text = answer(interview.owner, str(question))
                    answers.append(text)
                    with lock:
                        interview.log.append({"question": str(question), "ids": ids, "answer": text})
                self.wfile.write((json.dumps({"answers": answers}, ensure_ascii=False) + "\n").encode("utf-8"))

        self._server = socketserver.ThreadingTCPServer(("127.0.0.1", 0), Handler)
        self._server.daemon_threads = True
        self.port = self._server.server_address[1]
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)

    def __enter__(self) -> "Interview":
        self._thread.start()
        return self

    def __exit__(self, *exc: Any) -> None:
        self._server.shutdown()
        self._server.server_close()

    def install(self, kit: str) -> str:
        """Puts in the kit the command that reaches this owner, and returns its path."""
        path = os.path.join(kit, CLIENT_FILE)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(CLIENT.format(port=self.port))
        return path

    def fetched(self) -> dict[str, int]:
        """The answer key's facts the interview went and fetched: fact → number of the first question."""
        facts_of = {a["id"]: a["fact"] for a in self.owner.get("answers", []) if a.get("fact")}
        found: dict[str, int] = {}
        for n, entry in enumerate(self.log, 1):
            for aid in entry["ids"]:
                if aid in facts_of:
                    found.setdefault(facts_of[aid], n)
        return found

    def render(self, name: str) -> str:
        out = [f"# Interview of {name}: {len(self.log)} question(s)", ""]
        fetched = self.fetched()
        held = sorted({a["fact"] for a in self.owner.get("answers", []) if a.get("fact")})
        for fact in held:
            out.append(f"- {fact}, held only by the owner: "
                       + (f"asked at question {fetched[fact]}" if fact in fetched else "never asked"))
        if held:
            out.append("")
        for n, entry in enumerate(self.log, 1):
            out += [f"## {n}", f"**Question**: {entry['question']}", "",
                    f"**Answer** ({', '.join(entry['ids']) or 'default'}): {entry['answer']}", ""]
        return "\n".join(out)


def ask(port: int, questions: list[str]) -> list[str]:
    """What the kit's command does, for tests and for whoever wants to question the owner by hand."""
    with socket.create_connection(("127.0.0.1", port), timeout=30) as conn:
        conn.sendall((json.dumps({"questions": questions}) + "\n").encode("utf-8"))
        return json.loads(conn.makefile(encoding="utf-8").readline())["answers"]


def check(fixture_dir: str, expected: dict[str, Any]) -> list[str]:
    """A well-posed simulated owner: each answer has its triggers, each fact held only by the owner has
    its answer, and that fact leaks through no other answer — neither the intro, nor the default answer,
    nor an answer another question triggers. Without `owner.json`, nothing to say."""
    owner = load(fixture_dir)
    if owner is None:
        return []
    problems = []
    seen: set[str] = set()
    for a in owner.get("answers", []):
        if not a.get("id") or not a.get("any_of") or not a.get("answer"):
            problems.append(f"incomplete answer (id, any_of, answer): {str(a)[:80]}")
            continue
        if a["id"] in seen:
            problems.append(f"duplicate answer id: {a['id']}")
        seen.add(a["id"])
    if not owner.get("default"):
        problems.append("no default answer (`default`)")
    repo_instructions = ""
    for root, dirs, files in os.walk(os.path.join(fixture_dir, "repo")):
        dirs[:] = [d for d in dirs if d not in {".git", "node_modules", ".venv", "__pycache__"}]
        for name in files:
            if name in ("AGENTS.md", "CLAUDE.md"):
                with open(os.path.join(root, name), encoding="utf-8", errors="ignore") as fh:
                    repo_instructions += fh.read().lower()
    for fact in expected.get("init", {}).get("must_surface", []):
        words = [w.lower() for w in fact.get("only_in_instructions", [])]
        if not words or any(w in repo_instructions for w in words):
            continue                    # the repository says it itself: the owner need not carry it
        holders = [a for a in owner.get("answers", []) if a.get("fact") == fact["id"]]
        if not holders:
            problems.append(f"{fact['id']}: no answer carries this fact (`fact`), the owner cannot say it")
        elif not any(w in a.get("answer", "").lower() for a in holders for w in words):
            problems.append(f"{fact['id']}: the answer that carries it contains none of {words}")
        leaks = [a.get("id", "?") for a in owner.get("answers", []) if a.get("fact") != fact["id"]
                 and any(w in a.get("answer", "").lower() for w in words)]
        leaks += [name for name in ("intro", "default") if any(w in (owner.get(name) or "").lower() for w in words)]
        if leaks:
            problems.append(f"{fact['id']}: the fact also leaks through {', '.join(leaks)}: it would be said without being asked")
    return problems
