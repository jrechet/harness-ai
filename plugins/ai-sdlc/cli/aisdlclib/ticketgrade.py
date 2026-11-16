"""La note d'un avis de `/ticket` sur un ticket de fixture.

Le noteur lit l'avis écrit par le skill (le JSON passé à `ticket render`), le ticket donné à l'agent et
le dépôt monté. Il ne lit pas le compte rendu. Il est généreux sur les mots (un point attendu se
reconnaît à un motif large, dans n'importe lequel des champs admis), strict sur la preuve (une consigne
se cite mot pour mot, une source existe), sur ce qui ne devait pas bouger (le ticket, le dépôt) et sur
le zèle (un ticket sain ne reçoit pas dix critères)."""
from __future__ import annotations

import os
import re
import unicodedata
from typing import Any

from . import ticket
from .context import Refused, is_file_at
from .devgrade import BASE, _state

FIELDS = ticket.AVIS_LISTS


def check_expected(expected: Any) -> None:
    if not isinstance(expected, dict) or type(expected.get("ready")) is not bool or type(expected.get("size_l")) is not bool:
        raise Refused("corrigé : un objet JSON avec ready et size_l (ce que la commande dit du ticket)")
    for key in ("flags", "forbidden"):
        for item in expected.get(key, []) if isinstance(expected.get(key, []), list) else [None]:
            try:
                assert isinstance(item["id"], str) and isinstance(item["what"], str)
                assert item["in"] and all(field in FIELDS for field in item["in"])
                patterns = item["any"] if key == "flags" else [item["pattern"]]
                assert patterns and all(isinstance(p, str) for p in patterns)
                for pattern in patterns:
                    re.compile(pattern)
            except (KeyError, TypeError, AssertionError, re.error) as exc:
                raise Refused(f"corrigé : {key} mal formé ({item!r:.80})") from exc
    for key in ("max", "min"):
        bounds = expected.get(key, {})
        if not (isinstance(bounds, dict) and all(f in FIELDS and type(n) is int for f, n in bounds.items())):
            raise Refused(f"corrigé : {key} associe un champ de l'avis à un nombre")


def _texts(avis: dict[str, Any], field: str, pending_too: bool = True) -> list[str]:
    def plain(text: str) -> str:   # « 5\u200b% » se lit « 5% » : un caractère invisible ne cache pas un chiffre
        return "".join(ch for ch in unicodedata.normalize("NFKC", text) if unicodedata.category(ch) != "Cf")

    return [plain(text) for text in _raw_texts(avis, field, pending_too)]


def _raw_texts(avis: dict[str, Any], field: str, pending_too: bool) -> list[str]:
    out = []
    for item in avis.get(field, []):
        if isinstance(item, str):
            out.append(item)
        elif isinstance(item, dict) and (pending_too or not item.get("a_confirmer")):
            out.append(" ".join(str(item[k]) for k in ("point", "constat", "texte", "source", "question", "defaut", "citation")
                                if isinstance(item.get(k), str)))
    return out


def grade(table: dict[str, Any], expected: Any, avis: Any, task_dir: str, repo: str, ticket_copy: str) -> dict[str, Any]:
    check_expected(expected)
    original = ticket.read(os.path.join(task_dir, "ticket.md"))
    zones, _ = ticket.zones_for(table, repo, BASE)
    measured = ticket.check(original, zones)
    if measured["ready"] != expected["ready"] or bool(measured["sensitive"]) != expected["size_l"]:
        raise Refused("corrigé : ready ou size_l ne dit pas ce que `ticket check` mesure sur ce ticket, la fixture a dérivé")
    checks: list[dict[str, Any]] = []

    def add(ident: str, what: str, ok: bool, detail: str = "", optional: bool = False) -> None:
        checks.append({"id": ident, "what": what, "ok": bool(ok), "detail": detail, "optional": optional})

    errors = ticket.check_avis(avis, original, lambda rel: is_file_at(repo, BASE, rel))
    add("avis", "L'avis est bien formé : pas de verdict écrit, critères sourcés ou à confirmer, consignes citées mot pour mot",
        not errors, " ; ".join(errors[:3]))
    if errors:
        avis = {}   # un avis mal formé ne se note pas plus loin : tout ce qui suit échoue faute de matière
    try:
        with open(ticket_copy, encoding="utf-8") as fh:
            same = fh.read() == original
    except (OSError, UnicodeDecodeError):
        same = False
    add("ticket-intact", "Le ticket n'a pas été modifié : personne n'a donné son accord", same)
    state = _state(repo, BASE, os.path.dirname(os.path.dirname(os.path.abspath(task_dir))))
    add("depot-intact", "Le dépôt n'a pas bougé : contrôler un ticket n'est pas le réaliser",
        state["base_intact"] and state["ahead"] == 0 and not state["leftovers"],
        ", ".join(state["leftovers"]) or ("" if state["ahead"] == 0 else f"{state['ahead']} commit(s)"))
    for item in expected.get("flags", []):
        hay = [text for field in item["in"] for text in _texts(avis, field)]
        found = any(re.search(pattern, text) for pattern in item["any"] for text in hay)
        add(item["id"], f"Dit : {item['what']}", found, "" if found else f"attendu dans {', '.join(item['in'])}",
            optional=bool(item.get("optional")))
    for item in expected.get("forbidden", []):
        hay = [text for field in item["in"] for text in _texts(avis, field, pending_too=not item.get("unless_a_confirmer"))]
        hits = [text[:60] for text in hay if re.search(item["pattern"], text)]
        add(item["id"], f"Absent : {item['what']}", not hits and not errors, " | ".join(hits[:2]))
    for field, most in expected.get("max", {}).items():
        count = len(avis.get(field, []))
        add(f"max-{field}", f"Pas de zèle : au plus {most} dans {field}", count <= most and not errors, f"{count}")
    for field, least in expected.get("min", {}).items():
        count = len(avis.get(field, []))
        add(f"min-{field}", f"Au moins {least} dans {field}", count >= least, f"{count}")
    return {"pass": all(c["ok"] for c in checks if not c["optional"]), "checks": checks}
