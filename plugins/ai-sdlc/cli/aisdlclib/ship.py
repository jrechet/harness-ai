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
        return _gate("verifications", title, FAIL, f"le relevé porte sur un autre commit que {head[:7]}",
                     "Relever la CI de ce commit : une CI verte hier ne dit rien d'aujourd'hui.")
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
