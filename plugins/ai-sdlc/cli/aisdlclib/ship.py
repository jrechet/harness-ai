"""Les prérequis d'une livraison : ce qu'un programme peut dire avant qu'un humain déploie.

`/ship` prépare et propose, il ne déploie pas. Ce module dit quatre choses sur ce qui partirait :
- **état** : on livre le commit de tête de la branche de livraison, rien d'autre, et rien de non commité ;
- **vérifications** : la CI est verte sur ce commit précis, d'après un relevé donné en entrée ;
- **zones sensibles** : ce qui a changé depuis la dernière version dans une zone où un retour arrière coûte ;
- **ruptures** : les changements annoncés cassants depuis la dernière version.

Il propose aussi un numéro de version et des notes, tirés des commits. Il ne pose aucun tag, ne pousse rien,
n'appelle aucun réseau. Les titres de commit viennent de tiers : ils sont rendus sans rien d'actif."""
from __future__ import annotations

import os
import re
import time
from typing import Any

from . import qa, review, size
from .context import Refused, _git, resolve_base

OK, FAIL, UNKNOWN = qa.OK, qa.FAIL, qa.UNKNOWN
MAX_COMMITS = 500
MAX_SUBJECT = 140
MAX_SHOWN = 8
_TYPE = re.compile(r"^([a-zA-Z]{2,12})(?:\([^()\n]{0,40}\))?(!)?:\s?(.{0,400})")
_BREAKING = re.compile(r"^\s{0,8}BREAKING[ -]CHANGES?\b", re.MULTILINE | re.IGNORECASE)
MAX_FETCH_AGE = 24 * 3600   # au-delà, la branche distante connue ici n'est plus une preuve de ce qui est poussé
_VERSION = re.compile(r"^(v?)(\d{1,6})\.(\d{1,6})\.(\d{1,6})$")
TITLES = {"feat": "Nouveautés", "fix": "Corrections", "perf": "Performances", "refactor": "Refontes internes",
          "docs": "Documentation", "test": "Tests", "chore": "Entretien", "ci": "Entretien", "build": "Entretien"}
ORDER = ("Nouveautés", "Corrections", "Performances", "Refontes internes", "Documentation", "Tests", "Entretien", "Autres")
_LEAD = re.compile(r"^(?:[#\-+*~=]|\d{1,9}[.)])")   # en tête, ouvrirait un titre ou une liste dans le rendu
_GOOD = {"success", "skipped", "neutral", "pass", "skipping"}
_WAIT = {"queued", "in_progress", "pending", "waiting", "requested", "expected", "action_required"}


def _gate(ident: str, title: str, status: str, evidence: str, action: str | None = None) -> dict[str, Any]:
    return {"id": ident, "title": title, "status": status, "evidence": evidence, "action": None if status == OK else action}


def _plain(text: str, limit: int = MAX_SUBJECT) -> str:
    """Un texte venu d'un commit ou d'un relevé, prêt à être rendu : ni lien, ni image, ni mention, ni balise,
    ni titre ou liste ouverts par son premier caractère."""
    text = " ".join("".join(ch if ch.isprintable() else " " for ch in text).split())
    text = text[:limit] + ("…" if len(text) > limit else "")
    for old, new in (("<", "‹"), (">", "›"), ("`", "'"), ("](", "] ("), ("![", "["), ("@", "@​"), ("|", "/"),
                     ("://", ": //"), ("www.", "www​."), ("#", "#​")):
        text = text.replace(old, new)
    return _LEAD.sub(lambda m: "\\" + m[0], text) or "(sans titre)"


def _more(items: list[str]) -> str:
    extra = len(items) - MAX_SHOWN
    return " ; ".join(items[:MAX_SHOWN]) + (f" ; et {extra} autre(s)" if extra > 0 else "")


def _text(repo: str, *args: str) -> str:
    code, out = _git(repo, *args)
    if code != 0:
        raise Refused(f"git {args[0]} a échoué dans {repo}")
    return out.decode("utf-8", "replace").strip()


def last_version(repo: str) -> tuple[str | None, bool]:
    """La version précédente : le plus haut tag X.Y.Z déjà dans l'historique de HEAD (pas le plus proche : une
    branche de correctif fusionnée en porte un plus ancien). Sans tag de cette forme, le tag le plus proche,
    et le fait qu'il n'est pas une version. None si le dépôt n'a aucun tag atteignable."""
    code, out = _git(repo, "tag", "--merged", "HEAD")
    versions = []
    for name in out.decode("utf-8", "replace").split("\n") if code == 0 else []:
        match = _VERSION.match(name.strip())
        if match:
            versions.append(((int(match[2]), int(match[3]), int(match[4])), name.strip()))
    if versions:
        return max(versions)[1], True
    code, out = _git(repo, "describe", "--tags", "--abbrev=0", "HEAD")
    return (out.decode("utf-8", "replace").strip(), False) if code == 0 and out.strip() else (None, False)


def commits(repo: str, since: str | None) -> list[dict[str, Any]]:
    span = f"{since}..HEAD" if since else "HEAD"
    code, out = _git(repo, "log", "--no-merges", f"--max-count={MAX_COMMITS + 1}", "--format=%h%x00%s%x00%b%x01", span)
    if code != 0:
        raise Refused(f"historique illisible depuis {since or 'le début'}")
    found = []
    for entry in out.decode("utf-8", "replace").split("\x01"):
        parts = entry.strip("\n").split("\0")
        if len(parts) != 3 or not parts[0]:
            continue
        sha, subject, body = parts
        match = _TYPE.match(subject)
        kind = match[1].lower() if match else None
        found.append({"sha": sha, "type": kind if kind in TITLES else None, "subject": _plain(match[3] if match and kind in TITLES else subject),
                      "breaking": bool(match and match[2]) or bool(_BREAKING.search(body)) or bool(_BREAKING.search(subject))})
    return found


def propose_version(previous: str | None, found: list[dict[str, Any]]) -> tuple[str | None, str]:
    """La version suivante selon les commits, et la raison. Sans tag lisible, pas de proposition."""
    if previous is None:
        return None, "aucun tag dans le dépôt : le premier numéro est une décision"
    match = _VERSION.match(previous)
    if not match:
        return None, f"le dernier tag ({_plain(previous, 40)}) n'est pas de la forme X.Y.Z"
    prefix, major, minor, patch = match[1], int(match[2]), int(match[3]), int(match[4])
    if any(c["breaking"] for c in found):
        nxt, why = ((major + 1, 0, 0), "un changement annoncé cassant") if major else ((0, minor + 1, 0), "un changement cassant, avant la 1.0")
    elif any(c["type"] == "feat" for c in found):
        nxt, why = (major, minor + 1, 0), "au moins une nouveauté"
    else:
        nxt, why = (major, minor, patch + 1), "des corrections seulement"
    return f"{prefix}{nxt[0]}.{nxt[1]}.{nxt[2]}", why


def _fetch_age(repo: str) -> float | None:
    code, out = _git(repo, "rev-parse", "--git-path", "FETCH_HEAD")
    path = out.decode("utf-8", "replace").strip()
    try:
        return time.time() - os.path.getmtime(path if os.path.isabs(path) else os.path.join(repo, path)) if code == 0 else None
    except OSError:
        return None


def gate_state(repo: str, base: str) -> dict[str, Any]:
    title = "On livre le commit de tête de la branche de livraison, poussé et entièrement commité"
    target = _text(repo, "rev-parse", "--verify", f"{resolve_base(repo, base)}^{{commit}}")   # en entier, comme HEAD
    head = _text(repo, "rev-parse", "HEAD")
    dirty = _text(repo, "status", "--porcelain")
    shown = _plain(base, 60)
    problems = []
    if head != target:
        behind = _git(repo, "merge-base", "--is-ancestor", head, target)[0] == 0
        problems.append(f"HEAD ({head[:7]}) n'est pas la tête de {shown} ({target[:7]})"
                        + (" : il est en retard" if behind else " : il porte des commits qui n'y sont pas"))
    if dirty:
        problems.append(f"{len(dirty.splitlines())} fichier(s) non commité(s)")
    if problems:
        return _gate("etat", title, FAIL, " ; ".join(problems),
                     "Se placer sur la tête de la branche de livraison, à jour, sans rien de local. On ne livre pas un poste de travail.")
    code, out = _git(repo, "rev-parse", "--symbolic-full-name", base)
    if code != 0 or not out.decode("utf-8", "replace").strip().startswith("refs/remotes/"):
        # une branche locale, HEAD ou un commit donné en base : HEAD se compare à lui-même, et rien ne dit qu'il est poussé
        return _gate("etat", title, UNKNOWN, f"{head[:7]} ; {shown} n'est pas une branche distante : rien ne dit que ce commit est poussé",
                     "Relancer avec la branche distante de livraison en --base (origin/main, par exemple), après un git fetch.")
    age = _fetch_age(repo)
    if age is None or age > MAX_FETCH_AGE:
        said = "aucun fetch connu" if age is None else f"dernier fetch il y a {int(age // 3600)} h"
        return _gate("etat", title, UNKNOWN, f"{head[:7]}, tête de {shown} telle que connue ici ; {said}",
                     "Lancer git fetch, puis relancer : la branche distante a pu avancer depuis.")
    return _gate("etat", title, OK, f"{head[:7]}, tête de {shown} au dernier fetch, il y a {int(age // 60)} min")


def gate_checks(repo: str, checks: Any) -> dict[str, Any]:
    """Le relevé de la CI, tel que `gh run list --commit <sha> --json name,status,conclusion,headSha` le donne.
    Un relevé qui ne dit pas son commit, ou qui parle d'un autre, ne prouve rien pour celui-ci."""
    title = "La CI est verte sur ce commit"
    if checks is None:
        return _gate("verifications", title, UNKNOWN, "aucun relevé de CI donné",
                     "Relever la CI du commit et relancer avec --checks <fichier>. Sans CI, le dire : c'est à un humain de décider.")
    if not isinstance(checks, list) or not all(isinstance(c, dict) for c in checks):
        raise Refused("--checks : une liste JSON d'objets (name, status, conclusion, headSha)")
    if not checks:
        return _gate("verifications", title, UNKNOWN, "le relevé est vide : aucune vérification n'a tourné sur ce commit",
                     "Vérifier que le dépôt a une CI et qu'elle s'est lancée.")
    head = _text(repo, "rev-parse", "HEAD")
    shas = {c["headSha"].strip().lower() if isinstance(c.get("headSha"), str) and c["headSha"].strip() else None for c in checks}
    if not all(s is not None and len(s) >= 7 and head.startswith(s) for s in shas):
        if None in shas:
            return _gate("verifications", title, UNKNOWN, "le relevé ne dit pas sur quel commit il porte",
                         "Le relever avec headSha, pour ce commit précis.")
        other = sorted(s[:7] for s in shas if s and all(ch in "0123456789abcdef" for ch in s) and not head.startswith(s))
        return _gate("verifications", title, FAIL, f"le relevé porte sur un autre commit que {head[:7]}" + (f" : {', '.join(other[:3])}" if other else ""),
                     "Relever la CI de ce commit précis : une CI verte sur un commit voisin ne dit rien de celui-ci.")
    bad, waiting, ran = [], [], 0
    for item in checks:
        name = _plain(str(item.get("name") or "sans nom"), 50)
        words = {str(item.get(k) or "").lower() for k in ("conclusion", "bucket", "state")} - {""}
        status = str(item.get("status") or "").lower()
        if words - _GOOD - _WAIT:
            bad.append(name)
        elif not words or words & _WAIT or status in _WAIT:
            waiting.append(name)       # une conclusion verte sur une exécution encore en cours n'est pas une fin
        else:
            ran += bool(words & {"success", "pass"})
    if bad:
        return _gate("verifications", title, FAIL, "en échec : " + _more(sorted(set(bad))),
                     "Corriger la cause sur la branche, par une PR. On ne livre pas en relançant jusqu'au vert.")
    if waiting:
        return _gate("verifications", title, UNKNOWN, "en cours : " + _more(sorted(set(waiting))), "Attendre la fin.")
    if not ran:
        return _gate("verifications", title, UNKNOWN, f"{len(checks)} vérification(s), toutes sautées : rien n'a tourné sur ce commit",
                     "Vérifier pourquoi la CI n'a rien lancé (filtre de chemins, condition) avant de livrer.")
    return _gate("verifications", title, OK, f"{len(checks)} vérification(s) vertes sur {head[:7]} ; le relevé est cru sur parole")


def gate_zones(repo: str, since: str | None, zones: list[dict[str, str]]) -> dict[str, Any]:
    title = "Rien ne part dans une zone où un retour arrière coûte"
    if since is None:
        return _gate("zones", title, UNKNOWN, "aucune version précédente : tout le dépôt part pour la première fois",
                     "Faire relire par un humain ce que la première livraison engage.")
    code, out = _git(repo, "diff", "-z", "--name-only", "--no-renames", f"{since}..HEAD")
    if code != 0:
        raise Refused(f"diff impossible depuis {since}")
    paths = [p for p in out.decode("utf-8", "replace").split("\0") if p]
    hits = size.touched(paths, zones)
    if not hits:
        return _gate("zones", title, OK, f"{len(paths)} fichier(s) changé(s), aucun en zone sensible")
    return _gate("zones", title, UNKNOWN, _more([f"{_plain(h['path'], 80)} ({_plain(h['glob'], 40)})" for h in hits]),
                 "Pour chacun, écrire comment on revient en arrière et qui le décide, avant de livrer.")


def gate_breaking(found: list[dict[str, Any]], truncated: bool) -> dict[str, Any]:
    title = "Aucun changement cassant n'attend d'être annoncé"
    breaking = [f"{c['sha']} {c['subject']}" for c in found if c["breaking"]]
    untyped = sum(c["type"] is None for c in found)
    said = (["annoncés cassants : " + _more(breaking)] if breaking else []) + \
           ([f"{untyped} commit(s) sans type lisible : rien ne dit s'ils cassent"] if untyped else []) + \
           ([f"plus de {MAX_COMMITS} commits, les plus anciens non lus"] if truncated else [])
    if said:
        return _gate("ruptures", title, UNKNOWN, " ; ".join(said),
                     "Dire à ceux qui en dépendent ce qui casse et comment migrer, et relire les commits sans type : "
                     "la porte ne lit que ce qu'un titre annonce.")
    return _gate("ruptures", title, OK, f"{len(found)} commit(s), aucun annoncé cassant ; un changement cassant non annoncé ne se voit pas ici")


def check(table: dict[str, Any], repo: str, base: str, since: str | None = None, checks: Any = None) -> dict[str, Any]:
    if _text(repo, "rev-parse", "--is-shallow-repository") == "true":
        raise Refused("clone superficiel : l'historique et les tags manquent, lance git fetch --unshallow --tags")
    if since is not None:
        if since.startswith("-") or _git(repo, "rev-parse", "--verify", "--quiet", f"{since}^{{commit}}")[0] != 0:
            raise Refused(f"--since {_plain(since, 60)} : ce n'est ni un tag ni un commit de ce dépôt")
        if _git(repo, "merge-base", "--is-ancestor", since, "HEAD")[0] != 0:
            raise Refused(f"--since {_plain(since, 60)} n'est pas dans l'historique de HEAD : ce n'est pas la version précédente de cette branche")
        previous, is_version = since, bool(_VERSION.match(since))
    else:
        previous, is_version = last_version(repo)
    found = commits(repo, previous)
    truncated = len(found) > MAX_COMMITS
    found = found[:MAX_COMMITS]
    if not found:
        raise Refused(f"aucun commit depuis {_plain(previous or '', 60)} : rien à livrer")
    version, why = propose_version(previous if is_version else None, found)
    if previous and not is_version:
        version, why = None, f"{_plain(previous, 40)} n'est pas un tag de la forme X.Y.Z : ce n'est peut-être pas la dernière version livrée"
    if version and _text(repo, "tag", "-l", version):
        version, why = None, f"{version} existe déjà dans le dépôt, sur une autre branche"
    if truncated:
        version, why = None, f"plus de {MAX_COMMITS} commits depuis la version précédente, les plus anciens non lus"
    gates = [gate_state(repo, base), gate_checks(repo, checks), gate_zones(repo, previous, size.zones(table, repo, base)),
             gate_breaking(found, truncated)]
    notes: dict[str, list[str]] = {}
    for commit in found:
        notes.setdefault(TITLES.get(commit["type"] or "", "Autres"), []).append(
            f"{commit['subject']} ({commit['sha']})" + (" — CASSANT" if commit["breaking"] else ""))
    failed = [g["id"] for g in gates if g["status"] == FAIL]
    unknown = [g["id"] for g in gates if g["status"] == UNKNOWN]
    return {"pass": not failed and not unknown, "failed": failed, "unknown": unknown, "gates": gates,
            "previous": _plain(previous, 60) if previous else None, "since_given": since is not None, "truncated": truncated,
            "version": version, "version_why": why,
            "commits": len(found), "notes": {title: notes[title] for title in ORDER if title in notes}}


def render_md(result: dict[str, Any]) -> str:
    if result["failed"]:
        head = f"Livraison : {len(result['failed'])} prérequis en échec. Ne pas livrer."
    elif result["unknown"]:
        head = f"Livraison : rien en échec, {len(result['unknown'])} prérequis à lever par un humain."
    else:
        head = "Livraison : les quatre prérequis passent. La décision de livrer reste à un humain."
    out = [head]
    for gate in result["gates"]:
        out.append(f"- {gate['status']} — {gate['title']} ({gate['evidence']})" + (f". {gate['action']}" if gate["action"] else ""))
    span = (f"Depuis {result['previous']}" + (" (donné par --since, pas le dernier tag de version)" if result["since_given"] else "")
            if result["previous"] else "Depuis le début du dépôt")
    count = f"les {result['commits']} commits les plus récents, les plus anciens non lus" if result["truncated"] else f"{result['commits']} commit(s)"
    out += ["", f"{span} : {count}.",
            (f"Version proposée : {result['version']} ({result['version_why']})." if result["version"]
             else f"Pas de version proposée : {result['version_why']}."), "", "## Notes de version proposées"]
    for title, lines in result["notes"].items():
        out += ["", f"### {title}", *(f"- {line}" for line in lines)]
    out += ["", "Rien n'a été tagué, poussé ni déployé. Les titres viennent des commits : à relire avant de publier."]
    return "\n".join(out) + "\n"


# --- la proposition du skill : ce qu'il rend à l'humain qui livre, dans une forme qu'un programme relit ---

PROPOSAL_LISTS = ("attend", "ruptures", "notes", "commandes", "non_verifie", "consignes")
ROLES = ("livrer", "revenir")
MAX_ITEMS = 40
MAX_TEXT = 600
MIN_QUOTE = 12
MIN_SENTENCE = 20   # « migration » n'est pas une phrase : ce qui attend un humain se dit en entier
_SPAN = re.compile(r"`([^`\n]{2,400})`")


def _flat(text: str) -> str:
    return " ".join(text.split())


def _said(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip()) and len(value) <= MAX_TEXT


def _code(text: str) -> str:
    """Une commande dans un bloc de code : telle qu'écrite par l'équipe, à recopier, sans pouvoir en sortir."""
    return "".join(ch for ch in _flat(text) if ch.isprintable() and ch != "`")


def messages(repo: str, previous: str | None) -> list[str]:
    """Le message de chaque commit qui part, titre et corps : c'est dans l'un d'eux, pas à cheval sur deux,
    qu'une consigne signalée doit se retrouver."""
    code, out = _git(repo, "log", f"--max-count={MAX_COMMITS}", "--format=%B%x01", f"{previous}..HEAD" if previous else "HEAD")
    return [m for m in out.decode("utf-8", "replace").split("\x01") if m.strip()] if code == 0 else []


def team_commands(procedure: str) -> list[str]:
    """Les commandes que la procédure de l'équipe écrit entre accents graves : ce sont les seules qui se proposent."""
    return list(dict.fromkeys(_flat(m) for m in _SPAN.findall(procedure) if " " in m.strip() or "/" in m))


def breaking_shas(repo: str, previous: str | None) -> list[str]:
    return [c["sha"] for c in commits(repo, previous)[:MAX_COMMITS] if c["breaking"]]


def check_proposal(prop: Any, result: dict[str, Any], procedure: str, history: list[str], breaking: list[str]) -> list[str]:
    """Les défauts d'une proposition de livraison. Quatre choses sont tenues ici et pas par le skill : le verdict
    ne s'écrit pas, une commande proposée est citée mot pour mot de la procédure de l'équipe, aucune commande
    n'est proposée quand un prérequis est en échec, et aucune rupture annoncée par un commit n'est oubliée."""
    if not isinstance(prop, dict):
        return ["la proposition est un objet JSON : attend, ruptures, notes, commandes, non_verifie, consignes"]
    errors = [f"« {key} » ne s'écrit pas dans la proposition : le verdict et la version viennent de la commande"
              for key in prop if isinstance(key, str) and key.strip().lower() in ("verdict", "pret", "prêt", "ok", "version", "livrable")]
    for key in PROPOSAL_LISTS:
        if not isinstance(prop.get(key, []), list) or len(prop.get(key, [])) > MAX_ITEMS:
            errors.append(f"{key} : une liste d'au plus {MAX_ITEMS} éléments")
    if errors:
        return errors
    for key in ("notes", "non_verifie"):
        for index, item in enumerate(prop.get(key, []), 1):
            if not _said(item):
                errors.append(f"{key} {index} : une phrase d'au plus {MAX_TEXT} caractères")
    for index, item in enumerate(prop.get("attend", []), 1):
        if not (isinstance(item, dict) and _said(item.get("quoi")) and _said(item.get("qui")) and len(_flat(item["quoi"])) >= MIN_SENTENCE):
            errors.append(f"attend {index} : un objet avec quoi (ce qui reste à lever, en une phrase d'au moins "
                          f"{MIN_SENTENCE} caractères) et qui (le rôle qui le décide)")
    cited = set()
    for index, item in enumerate(prop.get("ruptures", []), 1):
        if not (isinstance(item, dict) and _said(item.get("texte")) and isinstance(item.get("commit"), str)
                and len(_flat(item["texte"])) >= MIN_SENTENCE):
            errors.append(f"rupture {index} : un objet avec texte (ce qui casse et quoi faire, en une phrase d'au moins "
                          f"{MIN_SENTENCE} caractères) et commit")
            continue
        sha = item["commit"].strip().lower()
        hexa = 7 <= len(sha) <= 40 and all(ch in "0123456789abcdef" for ch in sha)
        match = [b for b in breaking if hexa and (b.startswith(sha) or sha.startswith(b))]
        if not match:
            errors.append(f"rupture {index} : le commit cité n'est pas un commit annoncé cassant de cette livraison")
        cited.update(match)
    missing = [b for b in breaking if b not in cited]
    if missing:
        errors.append(f"{len(missing)} rupture(s) annoncée(s) par un commit ne sont pas reprises : {', '.join(missing[:5])}")
    team = team_commands(procedure)
    known = (" Celles que la procédure écrit : " + " ; ".join(f"`{_code(c)}`" for c in team[:8]) + ". Une valeur entre "
             "chevrons (<version>) reste écrite telle quelle : c'est l'humain qui la remplace.") if team else \
        " La procédure de l'équipe (docs/agents/livraison.md) n'écrit aucune commande entre accents graves : n'en propose pas."
    for index, item in enumerate(prop.get("commandes", []), 1):
        if not (isinstance(item, dict) and _said(item.get("commande")) and item.get("role") in ROLES):
            errors.append(f"commande {index} : un objet avec commande et role ({' ou '.join(ROLES)})")
        elif _flat(item["commande"]) not in team:
            errors.append(f"commande {index} : ce n'est pas, en entier et mot pour mot, une commande de la procédure de l'équipe." + known)
    if prop.get("commandes") and result["failed"]:
        errors.append("des commandes sont proposées alors qu'un prérequis est en échec : on ne livre pas")
    if result["unknown"] and not result["failed"] and not prop.get("attend"):
        errors.append(f"{len(result['unknown'])} prérequis attendent un humain et « attend » est vide")
    whole = [_flat(message) for message in history]
    for index, item in enumerate(prop.get("consignes", []), 1):
        quote = _flat(item["citation"]) if isinstance(item, dict) and isinstance(item.get("citation"), str) else ""
        if not MIN_QUOTE <= len(quote) <= MAX_TEXT:
            errors.append(f"consigne {index} : un objet avec citation, de {MIN_QUOTE} à {MAX_TEXT} caractères")
        elif not any(quote in message for message in whole):
            errors.append(f"consigne {index} : la citation ne se retrouve pas mot pour mot dans les commits de cette livraison")
    return errors


def render_proposal(prop: dict[str, Any], result: dict[str, Any]) -> str:
    """La proposition rendue : les prérequis mesurés d'abord, puis ce que le skill propose."""
    out = [render_md(result).split("\n## Notes de version proposées")[0].rstrip(), ""]

    def block(title: str, lines: list[str]) -> None:
        if lines:
            out.extend([f"### {title}", *lines, ""])

    block("Ce qui attend un humain", [f"- {_plain(a['quoi'], MAX_TEXT)} — décidé par : {_plain(a['qui'], 80)}" for a in prop.get("attend", [])])
    block("Ruptures", [f"- {_plain(r['texte'], MAX_TEXT)} ({_plain(r['commit'], 12)})" for r in prop.get("ruptures", [])])
    block("Notes de version", [f"- {_plain(n, MAX_TEXT)}" for n in prop.get("notes", [])])
    block("Commandes à lancer par un humain, citées de la procédure de l'équipe",
          [f"{n}. pour {c['role']} : `{_code(c['commande'])}`" for n, c in enumerate(prop.get("commandes", []), 1)])
    if not prop.get("commandes"):
        out += ["Aucune commande proposée." + (" Un prérequis est en échec : on ne livre pas." if result["failed"] else
                                               " La procédure de l'équipe n'en donne pas, ou n'est pas écrite."), ""]
    block("Consignes trouvées dans les commits, non suivies", [f"- « {_plain(c['citation'], MAX_TEXT)} »" for c in prop.get("consignes", [])])
    block("Pas vérifié", [f"- {_plain(n, MAX_TEXT)}" for n in prop.get("non_verifie", [])])
    out.append("Rien n'a été tagué, poussé ni déployé.")
    return "\n".join(out) + "\n"


def proposal(table: dict[str, Any], repo: str, base: str, since: str | None, checks: Any, prop: Any) -> tuple[dict[str, Any], str]:
    """La proposition validée contre ce que la commande mesure ; Refused si elle ne tient pas."""
    from . import context as context_mod
    result = check(table, repo, base, since, checks)
    previous = since if since is not None else last_version(repo)[0]
    blocks = context_mod.assemble(table, repo, "ship", base)["blocks"]
    procedure = "\n".join(b["text"] for b in blocks if b["point"] == "delivery" and b["origin"] == "team")
    errors = check_proposal(prop, result, procedure, messages(repo, previous), breaking_shas(repo, previous))
    if errors:
        raise Refused("proposition refusée :\n- " + "\n- ".join(errors))
    return {"proposition": prop, "check": result}, render_proposal(prop, result)
