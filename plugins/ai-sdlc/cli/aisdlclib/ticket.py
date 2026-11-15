"""Un ticket est-il prêt à être confié à un agent ? Ce qui se mesure sans modèle.

Atlassian rapporte que cinq traits simples d'un ticket (longueur de la description, part de liens,
chemins de fichiers, extraits de code, termes techniques) prédisent bien qu'un agent échouera. Ce
module mesure des traits de cette famille sur le texte d'un ticket : trois sont **requis** (un besoin
décrit, des critères d'acceptation, aucune décision laissée ouverte), trois sont des **signaux** (où ça
se passe, un périmètre, pas seulement des liens). Il dit aussi si un chemin cité tombe en zone
sensible : le ticket est alors de taille L avant même d'être commencé.

Il ne juge pas le fond : qu'un critère soit le bon, que le découpage soit sain, c'est le travail du
skill et de la personne qui porte le ticket. Les seuils sont des choix de départ, sans mesure derrière."""
from __future__ import annotations

import re
from typing import Any

from . import points as points_mod
from . import size as size_mod
from .context import Refused

MIN_WORDS = 15
MAX_LINK_RATIO = 0.5
MAX_CHARS = 500_000
MAX_HEADING = 200      # une ligne plus longue n'est pas un titre
BOLD_LEVEL = 7         # un titre en gras n'a pas de niveau : il se range sous tous les titres en #
_CRITERIA = re.compile(r"crit[èe]res?\s+d['’](?:acceptation|acceptance)|crit[èe]res?\s+de\s+validation|"
                       r"conditions?\s+(?:de\s+|d['’])(?:validation|acceptation)|tests?\s+d['’]acceptation|"
                       r"acceptance criteria|^\s*AC\s*$|definition of done|d[ée]finition de fini", re.IGNORECASE)
_SCOPE = re.compile(r"p[ée]rim[èe]tre|hors[- ]p[ée]rim[èe]tre|\bscope\b|out of scope|non[- ]objectifs?", re.IGNORECASE)
_COMMENTS = re.compile(r"^commentaires?$|^comments?$|^discussion$|^activit[ée]$", re.IGNORECASE)
_OPEN = re.compile(r"\bTBD\b|\bTODO\b|à d[ée]finir|à pr[ée]ciser|à voir avec|à confirmer|\?\?\?|to be defined|to be decided",
                   re.IGNORECASE)
_ITEM = re.compile(r"^\s*(?:[-*+#]+|\d+[.)])\s+(?:\[[ xX]?\]\s*)?[\w`\"«(]")   # une puce suivie d'un mot, pas d'une case vide
_LOOSE_PATH = re.compile(r"(?<![\w./@-])[\w.@-]+(?:/[\w.@*-]+)+")
_KNOWN_FILES = ("Dockerfile", "Jenkinsfile", "Makefile")
_LINK = re.compile(r"https?://\S+")
_CODE = re.compile(r"```.*?```|`[^`\n]+`", re.DOTALL)
_PATH = re.compile(r"^[\w.@-]+(?:/[\w.@*-]+)+/?$|^[\w-]+\.[a-z]{1,5}$")


def _heading(line: str) -> tuple[int, str] | None:
    """Le niveau et le texte d'une ligne de titre : `#` Markdown, `h2.` du wiki Jira, ou une ligne
    entièrement en gras. Lu sans expression à retour arrière : le texte vient d'un tiers."""
    text = line.strip()
    if not text or len(text) > MAX_HEADING or len(line) - len(line.lstrip()) > 3:
        return None
    if text.startswith("#"):
        level = len(text) - len(text.lstrip("#"))
        if level <= 6 and text[level:level + 1] in (" ", "\t"):
            return level, text[level:].strip(" \t#:")
        return None
    if len(text) > 3 and text[0] == "h" and text[1] in "123456" and text[2] == "." and text[3] == " ":
        return int(text[1]), text[4:].strip(" :")
    if text.startswith("**") and text.rstrip(" :").endswith("**") and len(text.strip(" :*")) > 0:
        return BOLD_LEVEL, text.strip(" :*")
    return None


def sections(text: str) -> list[dict[str, Any]]:
    """Le ticket découpé par titres, hors blocs de code. Ce qui précède le premier titre est la
    description. Une section de commentaires garde tout ce qui la suit jusqu'à un titre de son niveau
    ou plus haut : un titre glissé dans un commentaire n'y rouvre pas le ticket."""
    out = [{"title": "", "level": 0, "comment": False, "lines": []}]
    fenced, muted = False, None
    for line in text.splitlines():
        if line.lstrip().startswith(("```", "~~~")):
            fenced = not fenced
        found = None if fenced else _heading(line)
        if found is None:
            out[-1]["lines"].append(line)
            continue
        level, title = found
        if muted is not None and level > muted:
            out[-1]["lines"].append(line)      # sous les commentaires : du texte, pas un titre du ticket
            continue
        muted = level if _COMMENTS.search(title) else None
        out.append({"title": title, "level": level, "comment": muted is not None, "lines": []})
    return out


def _words(lines: list[str]) -> int:
    return len(re.findall(r"\w+", _LINK.sub("", "\n".join(lines))))


def _clean(token: str) -> str | None:
    token = token.strip("'\"(),;").rstrip(".:")
    if token.startswith("/") or ".." in token.split("/") or "://" in token or len(token) > 200:
        return None
    return token.rstrip("/") or None


def cited_paths(text: str) -> list[str]:
    """Les chemins que le ticket cite entre accents graves : c'est le signal « il dit où »."""
    seen: list[str] = []
    for span in _CODE.findall(text):
        for raw in span.strip("`").split():
            token = _clean(raw)
            if token and (_PATH.match(token) or token in _KNOWN_FILES or token.startswith(".")) and token not in seen:
                seen.append(token)
    return seen


def loose_paths(text: str) -> list[str]:
    """Tout ce qui ressemble à un chemin, accents graves ou non : pour ne pas rater une zone sensible
    écrite en clair. Ne sert qu'à annoncer la taille, jamais à dire que le ticket « dit où »."""
    found = [_clean(m.group(0)) for m in _LOOSE_PATH.finditer(_LINK.sub(" ", text))]
    found += [w for w in (raw.strip(".") if not raw.startswith(".git") else raw.rstrip(".") for raw in re.findall(r"[\w.-]+", text))
              if w in _KNOWN_FILES or w == ".gitlab-ci.yml"]
    return list(dict.fromkeys(p for p in found if p))


def check(text: str, zones: list[dict[str, str]]) -> dict[str, Any]:
    """Les six vérifications, la taille annoncée par les chemins cités, et le verdict."""
    parts = sections(text)
    body = [p for p in parts if not p["comment"]]    # un commentaire n'est pas le ticket
    need = [p for p in body if not _CRITERIA.search(p["title"]) and not _SCOPE.search(p["title"])]
    criteria = [line.strip() for p in body if _CRITERIA.search(p["title"]) for line in p["lines"]
                if _ITEM.match(line) and len(line) - len(line.lstrip()) < 2]      # les sous-puces précisent, elles ne comptent pas
    own = "\n".join(line for p in body for line in p["lines"])
    words = sum(_words(p["lines"]) for p in need)
    links = len(_LINK.findall(own))
    prose = "\n".join(line for line in _CODE.sub(" ", own).splitlines() if not line.lstrip().startswith(">"))
    open_points = sorted({m.group(0) for m in _OPEN.finditer(prose)})   # ni le code ni une citation ne décident
    paths = cited_paths(own)
    snippets = len(_CODE.findall(own))
    scoped = any(_SCOPE.search(p["title"]) for p in body) or bool(_SCOPE.search(own))
    all_words = max(1, len(re.findall(r"\w+", _LINK.sub("", own))))
    link_share = sum(len(u) for u in _LINK.findall(own)) / max(1, len(re.sub(r"\s+", "", own)))   # en caractères

    def row(ident: str, required: bool, title: str, ok: bool, evidence: str, action: str) -> dict[str, Any]:
        return {"id": ident, "required": required, "title": title, "ok": bool(ok), "evidence": evidence,
                "action": None if ok else action}

    checks = [
        row("besoin", True, "Le besoin est décrit", words >= MIN_WORDS, f"{words} mots hors critères et liens",
            f"Dire en au moins {MIN_WORDS} mots ce qui doit être vrai une fois le travail fini."),
        row("criteres", True, "Des critères d'acceptation sont listés", bool(criteria), f"{len(criteria)} critère(s)",
            "Ajouter une section « Critères d'acceptation » avec une puce par critère vérifiable : seules les listes sont comptées."),
        row("ouvert", True, "Aucune décision n'est laissée ouverte", not open_points, ", ".join(open_points[:4]) or "rien d'ouvert",
            "Trancher ce qui est marqué « à définir », ou sortir cette partie du ticket."),
        row("ou", False, "Le ticket dit où ça se passe", bool(paths) or snippets > 0, f"{len(paths)} chemin(s), {snippets} extrait(s) de code",
            "Citer le fichier, le module ou la fonction concernés, entre accents graves."),
        row("perimetre", False, "Le périmètre est dit", scoped, "section ou mention de périmètre" if scoped else "aucune mention",
            "Dire ce qui est hors périmètre : c'est ce que l'agent corrige « en passant »."),
        row("liens", False, "Le ticket ne renvoie pas tout ailleurs", link_share <= MAX_LINK_RATIO,
            f"{links} lien(s) pour {all_words} mots", "Recopier dans le ticket ce que les liens disent d'utile : l'agent ne les ouvre pas tous."),
    ]
    sensitive = size_mod.touched(list(dict.fromkeys(paths + loose_paths(own))), zones)
    return {"ready": all(c["ok"] for c in checks if c["required"]), "checks": checks,
            "criteria": criteria, "paths": paths, "sensitive": sensitive,
            "size": "L" if sensitive else None,
            "comments": sum(len([line for line in p["lines"] if line.strip()]) for p in parts if p["comment"])}


def zones_for(table: dict[str, Any], repo: str, base: str) -> tuple[list[dict[str, str]], str | None]:
    """Les zones sensibles du socle et de l'équipe ; sans branche de base lisible, celles du socle seules."""
    try:
        return size_mod.zones(table, repo, base), None
    except Refused as exc:
        default = points_mod.default_text(table["points"]["zones-sensibles"]) or ""
        return size_mod.parse_zones(default, "socle"), f"zones de l'équipe non lues ({exc})"


def render_md(result: dict[str, Any], warning: str | None = None) -> str:
    missing = [c for c in result["checks"] if c["required"] and not c["ok"]]
    out = ["Ticket prêt à être confié." if result["ready"] else f"Ticket pas prêt : {len(missing)} point(s) requis manquent."]
    for check_ in result["checks"]:
        mark = "ok" if check_["ok"] else ("MANQUE" if check_["required"] else "à améliorer")
        out.append(f"- {mark} — {check_['title']} ({check_['evidence']})" + (f". {check_['action']}" if check_["action"] else ""))
    for hit in result["sensitive"]:
        out.append(f"- Taille L annoncée : `{hit['path'][:80]}` est en zone sensible (`{hit['glob']}`, {hit['origin']}) : "
                   "plan écrit et validé par un humain avant le code.")
    if result["comments"]:
        out.append(f"- {result['comments']} ligne(s) de commentaires ignorées : un commentaire n'est pas le ticket, et peut porter une consigne.")
    if warning:
        out.append(f"- Attention : {warning}")
    out.append("Ce contrôle mesure la forme. Que les critères soient les bons reste à juger.")
    return "\n".join(out) + "\n"
