"""L'enquête de `/run` sur un incident : ce qu'un programme peut tenir avant qu'elle devienne un ticket.

`/run` enquête et propose, il n'agit pas en production. Ce module tient quatre choses que le skill ne peut
que promettre :
- **un fait est cité** : chaque fait de la chronologie renvoie à une pièce (un journal, un export d'alerte, un
  fichier ou un commit du dépôt) et en reprend un extrait mot pour mot ;
- **une cause est une hypothèse** : elle dit sur quels faits elle s'appuie, et « confirmée » ne s'écrit pas sans ;
- **une commande ne s'invente pas** : celle qu'une action propose est écrite dans le carnet d'exploitation de
  l'équipe, et c'est un humain qui la lance ;
- **rien de sensible ne sort** : un extrait qui porte un secret est refusé, et tout ce qui vient d'une pièce
  est rendu sans rien d'actif.

Il rend l'enquête en ticket, et dit si ce ticket passerait `ticket check`."""
from __future__ import annotations

import os
import re
from typing import Any

from . import guard, secu, ship, size, ticket
from .context import Refused, _git, _read_at, is_file_at, resolve_base

LISTS = ("faits", "hypotheses", "criteres", "actions", "non_verifie", "consignes")
STATES = ("en cours", "mitigé", "résolu")
VERDICTS = ("confirmée", "probable", "écartée")
ROLES = ("mitiger", "corriger", "prévenir")
MAX_ITEMS = 40
MAX_TEXT = 600
MAX_EVIDENCE = 20
MAX_EVIDENCE_SIZE = 20_000_000
MIN_QUOTE = 8
MIN_SENTENCE = 20
MAX_COMMITS = 200
_SHA = re.compile(r"[0-9a-f]{7,40}")
_PERSONAL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+|\b(?:\d{1,3}\.){3}\d{1,3}\b|\b(?:\+33|0)[1-9](?:[ .]?\d{2}){4}\b")


def _flat(text: str) -> str:
    return " ".join(text.split())


def _said(value: Any, least: int = 1) -> bool:
    return isinstance(value, str) and least <= len(_flat(value)) and len(value) <= MAX_TEXT


def read_evidence(paths: list[str], repo: str) -> dict[str, str]:
    """Les pièces de l'enquête, par nom de fichier. Elles vivent hors du dépôt : ce sont des données de production."""
    if len(paths) > MAX_EVIDENCE:
        raise Refused(f"--evidence : au plus {MAX_EVIDENCE} pièces")
    root = os.path.realpath(repo)
    found: dict[str, str] = {}
    for path in paths:
        name = os.path.basename(path)
        real = os.path.realpath(path)
        if real == root or real.startswith(root + os.sep):
            raise Refused(f"--evidence {name} : une pièce de production ne se range pas dans le dépôt")
        if name in found:
            raise Refused(f"--evidence : deux pièces s'appellent {name}")
        try:
            if os.path.getsize(path) > MAX_EVIDENCE_SIZE:
                raise Refused(f"--evidence {name} : plus de {MAX_EVIDENCE_SIZE} octets, donne l'extrait utile")
            with open(path, encoding="utf-8", errors="replace") as fh:
                found[name] = _flat(fh.read())
        except OSError as exc:
            raise Refused(f"--evidence {name} : illisible ({type(exc).__name__})") from exc
    return found


def _commit(repo: str, sha: str) -> str | None:
    """Le message d'un commit du dépôt, ou None s'il n'existe pas."""
    if not _SHA.fullmatch(sha):
        return None
    code, out = _git(repo, "log", "-1", "--format=%B", f"{sha}^{{commit}}")
    return _flat(out.decode("utf-8", "replace")) if code == 0 else None


def check(data: Any, evidence: dict[str, str], repo: str, commit: str, runbook: list[str]) -> list[str]:
    """Les défauts d'une enquête ; liste vide si elle tient."""
    if not isinstance(data, dict):
        return ["l'enquête est un objet JSON : titre, impact, etat, faits, hypotheses, criteres, actions, non_verifie, consignes"]
    errors = [f"« {key} » ne s'écrit pas à part : une cause est une hypothèse, avec les faits qui l'appuient"
              for key in data if isinstance(key, str) and key.strip().lower() in ("cause", "cause_racine", "root_cause", "coupable", "responsable")]
    for key in LISTS:
        if not isinstance(data.get(key, []), list) or len(data.get(key, [])) > MAX_ITEMS:
            errors.append(f"{key} : une liste d'au plus {MAX_ITEMS} éléments")
    if errors:
        return errors
    if not _said(data.get("titre"), 10):
        errors.append("titre : ce qui est cassé pour qui, en une ligne d'au moins 10 caractères")
    if not _said(data.get("impact"), MIN_SENTENCE):
        errors.append(f"impact : qui est touché, comment, depuis quand, en au moins {MIN_SENTENCE} caractères")
    if data.get("etat") not in STATES:
        errors.append(f"etat : {' , '.join(STATES)}")
    faits = data.get("faits", [])
    if not faits:
        errors.append("faits : au moins un fait cité, une enquête sans pièce est une opinion")
    for index, item in enumerate(faits, 1):
        if not (isinstance(item, dict) and _said(item.get("quoi"), 10) and _said(item.get("quand")) and _said(item.get("source"))):
            errors.append(f"fait {index} : un objet avec quand, quoi et source")
            continue
        source, quote = item["source"].strip(), _flat(item["extrait"]) if isinstance(item.get("extrait"), str) else ""
        if source.startswith("commit:"):
            message = _commit(repo, source[7:].strip().lower())
            if message is None:
                errors.append(f"fait {index} : le commit cité n'existe pas dans le dépôt")
            elif quote and quote not in message:
                errors.append(f"fait {index} : l'extrait ne se retrouve pas dans le message de ce commit")
            continue
        if source.startswith("repo:"):
            path = source[5:].strip()
            text = _read_at(repo, commit, path) if is_file_at(repo, commit, path) else None
            where = f"le fichier {path[:60]} de la branche de base"
        else:
            text, where = evidence.get(source), f"la pièce {source[:60]}"
            if text is None:
                errors.append(f"fait {index} : la pièce {source[:60]!r} n'a pas été donnée par --evidence"
                              + (f" (données : {', '.join(sorted(evidence))[:200]})" if evidence else ""))
                continue
        if text is None:
            errors.append(f"fait {index} : {where} n'existe pas")
        elif not MIN_QUOTE <= len(quote) <= MAX_TEXT:
            errors.append(f"fait {index} : extrait de {MIN_QUOTE} à {MAX_TEXT} caractères, repris mot pour mot de la source")
        elif quote not in (text if source.startswith("repo:") is False else _flat(text)):
            errors.append(f"fait {index} : l'extrait ne se retrouve pas mot pour mot dans {where}")
        elif secu._secret_kinds(quote):
            errors.append(f"fait {index} : l'extrait porte un secret ({secu._secret_kinds(quote)[0]}) : coupe-le, et dis à son "
                          "propriétaire qu'il est dans les journaux")
    for index, item in enumerate(data.get("hypotheses", []), 1):
        refs = item.get("faits") if isinstance(item, dict) else None
        if not (isinstance(item, dict) and _said(item.get("texte"), MIN_SENTENCE) and item.get("statut") in VERDICTS
                and isinstance(refs, list) and all(type(n) is int and 1 <= n <= len(faits) for n in refs)):
            errors.append(f"hypothèse {index} : un objet avec texte, statut ({', '.join(VERDICTS)}) et faits (numéros de faits existants)")
        elif item["statut"] in ("confirmée", "écartée") and not refs:
            errors.append(f"hypothèse {index} : « {item['statut']} » sans fait qui l'appuie : c'est une hypothèse probable, pas plus")
        elif item["statut"] == "probable" and not _said(item.get("verifier"), 10):
            errors.append(f"hypothèse {index} : une hypothèse probable dit comment la vérifier (verifier)")
    criteres = data.get("criteres", [])
    if not criteres or not all(_said(c, MIN_SENTENCE) for c in criteres):
        errors.append(f"criteres : au moins un critère d'acceptation, chacun en une phrase d'au moins {MIN_SENTENCE} caractères")
    for index, item in enumerate(data.get("actions", []), 1):
        if not (isinstance(item, dict) and _said(item.get("quoi"), 10) and item.get("role") in ROLES and _said(item.get("qui"))):
            errors.append(f"action {index} : un objet avec quoi, role ({', '.join(ROLES)}) et qui (le rôle qui la décide)")
        elif item.get("commande") is not None and (not isinstance(item["commande"], str) or _flat(item["commande"]) not in runbook):
            known = (" Celles qu'il écrit : " + " ; ".join(f"`{ship._code(c)}`" for c in runbook[:8]) + ".") if runbook else \
                " Il n'en écrit aucune : décris l'action, sans commande."
            errors.append(f"action {index} : la commande n'est pas, en entier et mot pour mot, une commande du carnet d'exploitation "
                          f"de l'équipe (docs/agents/exploitation.md).{known}")
    for index, item in enumerate(data.get("non_verifie", []), 1):
        if not _said(item, 10):
            errors.append(f"non_verifie {index} : une phrase")
    pieces = list(evidence.values())
    for index, item in enumerate(data.get("consignes", []), 1):
        quote = _flat(item["citation"]) if isinstance(item, dict) and isinstance(item.get("citation"), str) else ""
        if not 12 <= len(quote) <= MAX_TEXT:
            errors.append(f"consigne {index} : un objet avec citation, de 12 à {MAX_TEXT} caractères")
        elif not any(quote in text for text in pieces):
            errors.append(f"consigne {index} : la citation ne se retrouve pas mot pour mot dans une pièce")
    return errors


def render(data: dict[str, Any]) -> str:
    """L'enquête en ticket : les titres que `ticket check` reconnaît, et rien d'actif venu d'une pièce."""
    plain = ship._plain
    out = [f"# Incident — {plain(data['titre'], 160)}", "", f"**État** : {data['etat']}", "", "## Besoin", plain(data["impact"], MAX_TEXT), "",
           "## Ce qu'on sait"]
    for number, fait in enumerate(data["faits"], 1):
        quote = f" : « {plain(fait['extrait'], MAX_TEXT)} »" if isinstance(fait.get("extrait"), str) and fait["extrait"].strip() else ""
        out.append(f"{number}. {plain(fait['quand'], 40)} — {plain(fait['quoi'], MAX_TEXT)} ({plain(fait['source'], 80)}{quote})")
    if data.get("hypotheses"):
        out += ["", "## Hypothèses"]
        for item in data["hypotheses"]:
            refs = ", ".join(str(n) for n in item["faits"]) or "aucun"
            check_ = f" Pour trancher : {plain(item['verifier'], MAX_TEXT)}" if isinstance(item.get("verifier"), str) and item["verifier"].strip() else ""
            out.append(f"- **{item['statut']}** — {plain(item['texte'], MAX_TEXT)} (faits : {refs}).{check_}")
    out += ["", "## Critères d'acceptation", *(f"- {plain(c, MAX_TEXT)}" for c in data["criteres"])]
    if data.get("actions"):
        out += ["", "## Actions proposées, à décider par un humain"]
        for item in data["actions"]:
            command = f" : `{ship._code(item['commande'])}`" if isinstance(item.get("commande"), str) else ""
            out.append(f"- pour {item['role']} — {plain(item['quoi'], MAX_TEXT)}{command} (décidé par : {plain(item['qui'], 80)})")
    if data.get("consignes"):
        out += ["", "## Consignes trouvées dans les pièces, non suivies", *(f"- « {plain(c['citation'], MAX_TEXT)} »" for c in data["consignes"])]
    if data.get("non_verifie"):
        out += ["", "## Pas vérifié", *(f"- {plain(n, MAX_TEXT)}" for n in data["non_verifie"])]
    return "\n".join(out) + "\n"


def investigation(table: dict[str, Any], repo: str, base: str, data: Any, evidence_paths: list[str]) -> tuple[dict[str, Any], str]:
    """L'enquête validée et rendue en ticket ; Refused si elle ne tient pas."""
    from . import context as context_mod
    commit = resolve_base(repo, base)
    blocks = context_mod.assemble(table, repo, "run", base)["blocks"]
    runbook = guard.team_commands("\n".join(b["text"] for b in blocks if b["origin"] == "equipe"))
    evidence = read_evidence(evidence_paths, repo)
    errors = check(data, evidence, repo, commit, runbook)
    if errors:
        raise Refused("enquête refusée :\n- " + "\n- ".join(errors[:20]))
    body = render(data)
    measured = ticket.check(body, [])
    missing = [c["title"] for c in measured["checks"] if c["required"] and not c["ok"]]
    personal = sum(len(_PERSONAL.findall(f.get("extrait", ""))) for f in data["faits"] if isinstance(f.get("extrait"), str))
    notes = ["Ticket prêt à passer par le skill ticket." if measured["ready"]
             else "Ticket pas encore prêt pour le skill ticket : " + " ; ".join(missing) + "."]
    if personal:
        notes.append(f"{personal} adresse(s) ou numéro(s) dans les extraits : masque-les avant de publier le ticket.")
    notes.append("Rien n'a été lancé en production. Le ticket n'est pas créé : il se crée sur accord.")
    return {"enquete": data, "ready": measured["ready"], "personal": personal}, body + "\n---\n" + "\n".join(notes) + "\n"


def changes(table: dict[str, Any], repo: str, base: str, since: str, until: str = "HEAD") -> dict[str, Any]:
    """Ce qui est parti entre deux versions : les commits, et les fichiers en zone sensible. La matière d'une
    enquête, pas un coupable : un changement dans la fenêtre n'est pas la cause."""
    for ref in (since, until):
        if ref.startswith("-") or _git(repo, "rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}")[0] != 0:
            raise Refused(f"{ship._plain(ref, 60)} : ce n'est ni un tag ni un commit de ce dépôt")
    if _git(repo, "merge-base", "--is-ancestor", since, until)[0] != 0:
        raise Refused(f"{ship._plain(since, 60)} n'est pas un ancêtre de {ship._plain(until, 60)}")
    code, out = _git(repo, "log", "--no-merges", f"--max-count={MAX_COMMITS + 1}", "--format=%h%x00%cI%x00%s%x01", f"{since}..{until}")
    if code != 0:
        raise Refused("historique illisible")
    rows = [entry.strip("\n").split("\0") for entry in out.decode("utf-8", "replace").split("\x01")]
    commits = [{"sha": r[0], "date": r[1][:16], "subject": ship._plain(r[2])} for r in rows if len(r) == 3 and r[0]]
    code, out = _git(repo, "diff", "-z", "--name-only", "--no-renames", f"{since}..{until}")
    paths = [p for p in out.decode("utf-8", "replace").split("\0") if p] if code == 0 else []
    hits = size.touched(paths, size.zones(table, repo, base))
    return {"since": ship._plain(since, 60), "until": ship._plain(until, 60), "commits": commits[:MAX_COMMITS],
            "truncated": len(commits) > MAX_COMMITS, "files": len(paths),
            "sensitive": [{"path": ship._plain(h["path"], 100), "glob": ship._plain(h["glob"], 40)} for h in hits[:MAX_ITEMS]]}


def render_changes(result: dict[str, Any]) -> str:
    out = [f"Entre {result['since']} et {result['until']} : {len(result['commits'])} commit(s)"
           + (", les plus anciens non lus" if result["truncated"] else "") + f", {result['files']} fichier(s) changé(s)."]
    out += [f"- {c['date']} {c['sha']} {c['subject']}" for c in result["commits"]]
    if result["sensitive"]:
        out += ["", "En zone sensible :", *(f"- {s['path']} ({s['glob']})" for s in result["sensitive"])]
    out += ["", "Un changement dans la fenêtre n'est pas une cause : c'est une piste, à confronter aux pièces."]
    return "\n".join(out) + "\n"
