"""Le propriétaire simulé d'un projet type : il ne répond qu'à ce qu'on lui demande.

Donner d'avance toutes les réponses à l'agent évalué (`owner.md`) ne mesure pas l'entretien : un fait
que le propriétaire dit de lui-même est recueilli même par un skill qui ne pose aucune question. Ici
les réponses sont dans `owner.json`, chacune derrière des mots déclencheurs, et `bench init` les sert
pendant la séance : l'agent pose ses questions par une commande du kit, le banc répond et garde
l'échange. Rien n'est tiré au sort, aucun modèle ne joue le propriétaire : une même question reçoit
toujours la même réponse.

Format d'`owner.json` :
    {"intro": "qui il est, dit à l'agent d'entrée (facultatif)",
     "answers": [{"id": "mode", "any_of": ["mode", "délég*"], "answer": "…"},
                 {"id": "oral", "fact": "I6", "any_of": ["nulle part", "redi*"], "answer": "…"}],
     "default": "ce qu'il répond quand rien ne correspond"}

Un déclencheur est un mot ou une suite de mots, cherché mots entiers, sans tenir compte de la casse
ni des accents ; `délég*` accepte toute fin de mot, `remarque* en revue` aussi. `fact` relie une réponse à un fait `must_surface` du corrigé : c'est ce qui
permet de dire, après coup, si l'entretien est allé chercher ce fait.
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

CLIENT = '''#!/usr/bin/env python3
"""Pose des questions au propriétaire du dépôt et affiche ses réponses. Une question par argument."""
import json
import socket
import sys

questions = [a.strip() for a in sys.argv[1:] if a.strip()]
if not questions and not sys.stdin.isatty():
    questions = [line.strip() for line in sys.stdin if line.strip()]
if not questions:
    sys.exit('usage : proprietaire.py "première question" "deuxième question"')
with socket.create_connection(("127.0.0.1", {port}), timeout=30) as conn:
    conn.sendall((json.dumps({{"questions": questions}}) + "\\n").encode("utf-8"))
    reply = json.loads(conn.makefile(encoding="utf-8").readline())
for question, answer in zip(questions, reply["answers"]):
    print(f"Q : {{question}}\\nR : {{answer}}\\n")
'''


def load(fixture_dir: str) -> dict[str, Any] | None:
    path = os.path.join(fixture_dir, FILE)
    if not os.path.isfile(path):
        return None
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def fold(text: str) -> str:
    """Minuscules, sans accents, apostrophes droites : « Délégation » et « delegation » se valent."""
    text = unicodedata.normalize("NFD", text.replace("’", "'"))
    return "".join(c for c in text if not unicodedata.combining(c)).lower()


def _pattern(keyword: str) -> re.Pattern[str]:
    """Un déclencheur : un mot ou une suite de mots, chacun pouvant finir par `*`."""
    parts = []
    for word in fold(keyword).split():
        parts.append(re.escape(word[:-1]) + r"\w*" if word.endswith("*") else re.escape(word) + r"(?!\w)")
    return re.compile(r"(?<!\w)" + r"\s+".join(parts))


def answer(owner: dict[str, Any], question: str) -> tuple[list[str], str]:
    """Les réponses que la question déclenche, dans l'ordre du fichier, et leurs identifiants.
    Une question qui ne déclenche rien reçoit la réponse par défaut."""
    low = fold(question)
    hits = [a for a in owner.get("answers", []) if any(_pattern(k).search(low) for k in a["any_of"])]
    if not hits:
        return [], owner.get("default", "Je ne sais pas.")
    return [a["id"] for a in hits], "\n".join(a["answer"] for a in hits)


class Interview:
    """Le propriétaire à l'écoute pendant une séance. `port` est celui que la commande du kit appelle ;
    `log` garde chaque question, la réponse rendue et ce qui l'a déclenchée."""

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
        """Pose dans le kit la commande qui joint ce propriétaire, et rend son chemin."""
        path = os.path.join(kit, "proprietaire.py")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(CLIENT.format(port=self.port))
        return path

    def fetched(self) -> dict[str, int]:
        """Les faits du corrigé que l'entretien est allé chercher : fait → numéro de la première question."""
        facts_of = {a["id"]: a["fact"] for a in self.owner.get("answers", []) if a.get("fact")}
        found: dict[str, int] = {}
        for n, entry in enumerate(self.log, 1):
            for aid in entry["ids"]:
                if aid in facts_of:
                    found.setdefault(facts_of[aid], n)
        return found

    def render(self, name: str) -> str:
        out = [f"# Entretien de {name} : {len(self.log)} question(s)", ""]
        fetched = self.fetched()
        held = sorted({a["fact"] for a in self.owner.get("answers", []) if a.get("fact")})
        for fact in held:
            out.append(f"- {fact}, que seul le propriétaire détient : "
                       + (f"demandé à la question {fetched[fact]}" if fact in fetched else "jamais demandé"))
        if held:
            out.append("")
        for n, entry in enumerate(self.log, 1):
            out += [f"## {n}", f"**Question** : {entry['question']}", "",
                    f"**Réponse** ({', '.join(entry['ids']) or 'par défaut'}) : {entry['answer']}", ""]
        return "\n".join(out)


def ask(port: int, questions: list[str]) -> list[str]:
    """Ce que fait la commande du kit, pour les tests et pour qui veut interroger le propriétaire à la main."""
    with socket.create_connection(("127.0.0.1", port), timeout=30) as conn:
        conn.sendall((json.dumps({"questions": questions}) + "\n").encode("utf-8"))
        return json.loads(conn.makefile(encoding="utf-8").readline())["answers"]


def check(fixture_dir: str, expected: dict[str, Any]) -> list[str]:
    """Un propriétaire simulé bien posé : chaque réponse a ses déclencheurs, chaque fait que seul le
    propriétaire détient a sa réponse, et ce fait ne s'échappe par aucune autre réponse — ni l'accueil,
    ni la réponse par défaut, ni une réponse qu'une autre question déclenche. Sans `owner.json`, rien à dire."""
    owner = load(fixture_dir)
    if owner is None:
        return []
    problems = []
    seen: set[str] = set()
    for a in owner.get("answers", []):
        if not a.get("id") or not a.get("any_of") or not a.get("answer"):
            problems.append(f"réponse incomplète (id, any_of, answer) : {str(a)[:80]}")
            continue
        if a["id"] in seen:
            problems.append(f"identifiant de réponse en double : {a['id']}")
        seen.add(a["id"])
    if not owner.get("default"):
        problems.append("pas de réponse par défaut (`default`)")
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
            continue                    # le dépôt le dit lui-même : le propriétaire n'a pas à le porter
        holders = [a for a in owner.get("answers", []) if a.get("fact") == fact["id"]]
        if not holders:
            problems.append(f"{fact['id']} : aucune réponse ne porte ce fait (`fact`), le propriétaire ne peut pas le dire")
        elif not any(w in a.get("answer", "").lower() for a in holders for w in words):
            problems.append(f"{fact['id']} : la réponse qui le porte ne contient aucun de {words}")
        leaks = [a.get("id", "?") for a in owner.get("answers", []) if a.get("fact") != fact["id"]
                 and any(w in a.get("answer", "").lower() for w in words)]
        leaks += [name for name in ("intro", "default") if any(w in (owner.get(name) or "").lower() for w in words)]
        if leaks:
            problems.append(f"{fact['id']} : le fait s'échappe aussi par {', '.join(leaks)} : il serait dit sans être demandé")
    return problems
