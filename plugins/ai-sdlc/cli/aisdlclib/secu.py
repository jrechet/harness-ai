"""Les portes de `/secu` : ce qu'un programme peut dire de la sécurité d'un changement.

Quatre portes, chacune `ok`, `échec`, ou `non mesuré` :
- **secrets** : aucune ligne ajoutée ne porte un secret reconnaissable, aucun fichier de clés n'est ajouté ;
- **neutralisés** : le diff ne fait taire aucun scanner (`# nosec`, `nosemgrep`, fichier d'exceptions) ;
- **scanner** : les rapports SARIF des scanners de l'équipe n'ont aucun résultat sur une ligne ajoutée ;
- **surface** : ce que le changement touche de sensible, à relire par quelqu'un : zones sensibles,
  dépendances, appels à risque. Cette porte ne passe jamais seule quand elle trouve quelque chose.

Ce module ne remplace pas un scanner : ses motifs de secrets sont peu nombreux et sûrs d'eux, et il ne
lit pas le code. Sans rapport de scanner, la porte « scanner » reste non mesurée : `/secu` ne bloque
ni n'absout seul. Le contenu des lignes n'est jamais recopié dans sa sortie : un chemin, une ligne, une
nature, et des noms (fichier, règle, outil) réduits à des caractères sans effet dans un rendu."""
from __future__ import annotations

import json
import os
import re
import time
import urllib.parse
from typing import Any

from . import qa, size
from .context import Refused, _git, resolve_base

OK, FAIL, UNKNOWN = qa.OK, qa.FAIL, qa.UNKNOWN
MAX_LINE = 20_000       # au-delà, la ligne est lue jusque-là et signalée
MAX_SHOWN = 8
MAX_RESULTS = 100_000
_HUNK = re.compile(r"^@@ -\d+(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")
MAX_COMMITS = 100      # l'historique de la branche est lu commit par commit jusque-là
SCAN_BUDGET = 60       # secondes pour lire les lignes : au-delà, la lecture s'arrête et le dit

# Des formes que rien d'autre qu'un secret ne prend. Pas de quantificateurs imbriqués : le texte vient d'un tiers.
_SECRETS = [
    ("clé privée", re.compile(r"-----BEGIN (?:RSA |EC |DSA |OPENSSH |PGP |ENCRYPTED )?PRIVATE KEY")),
    ("clé d'accès AWS", re.compile(r"(?<![A-Z0-9])(?:AKIA|ASIA)[A-Z0-9]{16}(?![A-Z0-9])")),
    ("jeton GitHub", re.compile(r"(?<![A-Za-z0-9_])(?:gh[pousr]_[A-Za-z0-9]{36,}|github_pat_[A-Za-z0-9_]{40,})")),
    ("jeton GitLab", re.compile(r"(?<![A-Za-z0-9_])glpat-[A-Za-z0-9_-]{20,}")),
    ("jeton Slack", re.compile(r"(?<![A-Za-z0-9])xox[baprs]-[A-Za-z0-9-]{10,}")),
    ("clé d'API (sk-…)", re.compile(r"(?<![A-Za-z0-9_-])sk-(?:ant-|proj-|live_)?[A-Za-z0-9_-]{24,}")),
    ("clé Stripe", re.compile(r"(?<![A-Za-z0-9_])(?:sk|rk)_live_[A-Za-z0-9]{20,}")),
    ("clé Google", re.compile(r"(?<![A-Za-z0-9_-])AIza[A-Za-z0-9_-]{35}(?![A-Za-z0-9_-])")),
    ("jeton npm ou PyPI", re.compile(r"(?<![A-Za-z0-9_])(?:npm_[A-Za-z0-9]{36}|pypi-AgEI[A-Za-z0-9_-]{40,})")),
    ("JWT", re.compile(r"(?<![A-Za-z0-9_-])eyJ[A-Za-z0-9_-]{15,}\.eyJ[A-Za-z0-9_-]{15,}\.[A-Za-z0-9_-]{10,}")),
    ("identifiants dans une URL", re.compile(r"[a-z][a-z0-9+.-]{1,20}://[^\s/:@'\"]{1,80}:([^\s/@'\"]{6,80})@[\w.-]")),
]
# nom = "valeur littérale" : le nom dit que c'est un secret, la valeur n'est ni un exemple ni une variable
_ASSIGN = re.compile(r"(?i)(?<![a-z0-9])(?:[a-z0-9_.-]{0,30})(?:passw(?:or)?d|pwd|passphrase|secret|token|api[_-]?key|apikey|"
                     r"private[_-]?key|access[_-]?key|auth[_-]?key|credential)[a-z0-9_-]{0,20}[\"']?\s{0,3}(?:=|:|=>|:=)\s{0,3}[\"']([^\"'\s]{12,200})[\"']")
# Une valeur qui n'en est pas une : un exemple, ou une variable qui occupe toute la valeur. Jugé sur la valeur
# entière : un vrai mot de passe peut contenir « $ » ou « % ».
_PLACEHOLDER = re.compile(r"(?i)(?:x+|\*+|\.+|•+|0+|changeme.*|change[_-]me.*|example.*|exemple.*|dummy.*|fake.*|test.*|todo.*|"
                          r"your[_-].*|votre[_-].*|placeholder.*|redacted.*|secret|password|motdepasse|none|null|undefined|"
                          r"\$\{[^}]*\}|\$\w+|\{\{[^}]*\}\}|\{[\w.]*\}|<[^>]*>|%\([^)]*\)s|%\w+%)")
_WORDS = re.compile(r"[a-z_]+")   # des minuscules et des soulignés : un identifiant, pas une valeur
_KEY_FILE = re.compile(r"(?:^|/)(?:\.env(?:\.(?!example$|sample$|template$|dist$)[\w.-]+)?|id_(?:rsa|dsa|ecdsa|ed25519)|"
                       r"[^/]+\.(?:pem|p12|pfx|jks|keystore|key)|credentials(?:\.json)?|\.npmrc|\.pypirc|\.netrc|"
                       r"service[_-]?account[^/]*\.json)$", re.IGNORECASE)
_MUTED = re.compile(r"(?:#|//)\s{0,3}nosec\b|noqa:[^#\n]{0,60}\bS\d|ruff:\s{0,3}noqa|\bnosemgrep\b|semgrep:\s{0,3}ignore|"
                    r"nolint:\s{0,3}gosec|NOLINT\(gosec|\bNOSONAR\b|SuppressFBWarnings|kics-scan ignore|trufflehog:ignore|"
                    r"gitleaks:allow|\bcodeql\s*\[|lgtm\s*\[|snyk:?\s*ignore|trivy:ignore|checkov:skip|tfsec:ignore|"
                    r"bandit:\s*skip|eslint-disable[\w-]{0,30}\s{1,3}security/|@SuppressWarnings\(\s*\"(?:java:S|squid:S|findsecbugs)|"
                    r"detect-secrets:\s*allowlist|pragma:\s*allowlist\s+secret|brakeman:\s*ignore", re.IGNORECASE)
_SCANNER_CONFIG = re.compile(r"(?:^|/)(?:\.gitleaksignore|\.gitleaks\.toml|gitleaks\.toml|\.semgrepignore|\.semgrep(?:\.ya?ml|/.*)|"
                             r"\.trivyignore(?:\.ya?ml)?|trivy\.ya?ml|\.snyk|\.bandit|bandit\.ya?ml|\.secrets\.baseline|"
                             r"\.checkov\.ya?ml|\.tfsec/.*|sonar-project\.properties|\.github/codeql/.*|"
                             r"\.github/dependabot\.ya?ml|renovate\.json5?|\.trufflehog[\w.-]*|\.pre-commit-config\.yaml)$")
_MANIFEST = re.compile(r"(?:^|/)(?:package\.json|package-lock\.json|npm-shrinkwrap\.json|yarn\.lock|pnpm-lock\.yaml|bun\.lockb?|"
                       r"requirements[\w.-]*\.txt|constraints[\w.-]*\.txt|pyproject\.toml|poetry\.lock|uv\.lock|Pipfile(?:\.lock)?|"
                       r"setup\.(?:py|cfg)|go\.(?:mod|sum)|Cargo\.(?:toml|lock)|pom\.xml|build\.gradle(?:\.kts)?|gradle\.lockfile|"
                       r"libs\.versions\.toml|Gemfile(?:\.lock)?|composer\.(?:json|lock)|[^/]+\.csproj|packages\.lock\.json|"
                       r"Package\.(?:swift|resolved)|pubspec\.(?:yaml|lock)|mix\.(?:exs|lock)|\.gitmodules)$")
# Des appels qu'un relecteur regarde toujours. Un signal, pas un verdict : la plupart sont légitimes.
_HOT = [
    ("code évalué à l'exécution", re.compile(r"(?<![\w.])(?:eval|exec)\s?\(|new Function\(|\bcompile\(.{0,80}['\"]exec['\"]")),
    ("commande passée à un shell", re.compile(r"shell\s?=\s?True|os\.system\(|os\.popen\(|child_process|Runtime\.getRuntime\(\)\.exec|"
                                              r"(?<![\w.])(?:execSync|spawnSync|exec)\(\s?[`'\"]|subprocess\.\w+\(\s?f?[\"']")),
    ("désérialisation", re.compile(r"pickle\.loads?\(|yaml\.load\((?!.{0,80}SafeLoader)|\bmarshal\.loads?\(|ObjectInputStream|"
                                   r"unserialize\(|Marshal\.load\(")),
    ("vérification TLS coupée", re.compile(r"verify\s?=\s?False|InsecureSkipVerify\s?:\s?true|rejectUnauthorized\s?:\s?false|"
                                           r"NODE_TLS_REJECT_UNAUTHORIZED|CURLOPT_SSL_VERIFYPEER|--insecure\b|curl\s+-k\b|"
                                           r"check_hostname\s?=\s?False|_create_unverified_context")),
    ("HTML injecté sans échappement", re.compile(r"\.innerHTML\s?=|dangerouslySetInnerHTML|v-html=|\|\s?safe\b|mark_safe\(|"
                                                 r"document\.write\(|bypassSecurityTrust\w+\(|\{@html\b")),
    ("requête SQL construite par assemblage", re.compile(
        r"(?i)(?:execute|query|raw|prepare)\w{0,30}\(\s?(?:f[\"']|[\"'][^\"']{0,200}[\"']\s?(?:%|\+|\.format\())|"
        r"[\"'](?:select|insert|update|delete)\b[^\"']{0,200}[\"']\s?(?:\+|%\s|\.format\()|\$\{[^}]{0,80}\}[^`]{0,200}\b(?:where|values)\b")),
    ("hachage ou chiffrement faible", re.compile(r"(?<![\w.])(?:md5|sha1|MD5|SHA1)\s?\(|hashlib\.(?:md5|sha1)\(|"
                                                 r"MessageDigest\.getInstance\(\s?\"(?:MD5|SHA-?1)\"|createHash\(\s?['\"](?:md5|sha1)['\"]|"
                                                 r"\bDES(?:ede)?\.new\(|['\"/](?:DES|RC4|3DES)['\"/]|MODE_ECB|/ECB/|"
                                                 r"Math\.random\(\).{0,60}(?:token|secret|password|key)")),
    ("droits ouverts", re.compile(r"chmod\s+(?:-R\s+)?(?:777|666|a\+[rwx]+)|0o?777\b|Access-Control-Allow-Origin['\"]?\s?[:=,]\s?['\"]\*|"
                                  r"cors\(\s?\)|@PermitAll|permitAll\(\)|AllowAny\b|csrf_exempt|csrf\(\)\.disable|"
                                  r"--dangerously-skip-permissions|--privileged\b|privileged:\s?true")),
    ("script téléchargé puis exécuté", re.compile(r"(?:curl|wget)\b[^|;&]{0,200}\|\s?(?:sudo\s+)?(?:ba|z|da)?sh\b")),
    ("vérification contournée", re.compile(r"--no-verify\b|--no-gpg-sign\b|--force-with-lease\b|push\s+(?:-f|--force)\b|"
                                           r"continue-on-error:\s?true|\|\|\s?true\s*$|pull_request_target")),
]
_PROSE = (".md", ".mdx", ".txt", ".rst", ".adoc")   # de la prose qui parle d'un appel n'est pas un appel
_LEVELS = ("error", "warning", "note", "none")


_NAME = re.compile(r"[^A-Za-z0-9._/-]")


def _gate(ident: str, title: str, status: str, evidence: str, action: str | None = None) -> dict[str, Any]:
    return {"id": ident, "title": title, "status": status, "evidence": evidence, "action": None if status == OK else action}


def _where(path: str, line: int | None = None) -> str:
    """Un chemin prêt à être montré. Il vient du dépôt examiné : seuls restent les lettres, les chiffres et
    `. _ / -` et l'espace, pour qu'il ne porte ni lien, ni image, ni mention, ni consigne mise en forme. Un nom
    de fichier en forme de secret n'est pas montré du tout."""
    if any(pattern.search(path) for _, pattern in _SECRETS):
        clean = "(nom de fichier masqué)"
    else:
        clean = "".join(ch if ch.isalnum() or ch in "._/- " else "?" for ch in path)[:120]
    return f"{clean}:{line}" if line else clean


def _name(text: Any, limit: int = 40) -> str:
    """Un nom de règle ou d'outil lu dans un rapport : réduit à ce qu'un identifiant contient."""
    return _NAME.sub("?", text)[:limit] if isinstance(text, str) and text else "sans nom"


def _shown(items: list[str]) -> str:
    extra = len(items) - MAX_SHOWN
    return " ; ".join(items[:MAX_SHOWN]) + (f" ; et {extra} autre(s)" if extra > 0 else "")


def parse_patch(patch: bytes) -> list[tuple[str, int, str]]:
    """Les lignes ajoutées d'un diff unifié : (chemin, numéro, texte). Découpé sur le seul saut de ligne (un
    autre séparateur ne cache pas la suite d'une ligne), et les lignes d'un bloc sont comptées d'après son
    en-tête : une ligne ajoutée qui imite un en-tête reste une ligne ajoutée."""
    out: list[tuple[str, int, str]] = []
    path, minus, plus, number = "", 0, 0, 0
    for raw in patch.split(b"\n"):
        line = raw.decode("utf-8", "replace")
        if minus or plus:
            if plus and line.startswith("+"):
                out.append((path, number, line[1:]))
                number, plus = number + 1, plus - 1
                continue
            if minus and line.startswith("-"):
                minus -= 1
                continue
            if line.startswith("\\"):
                continue
            minus = plus = 0
        match = _HUNK.match(line)
        if match:
            minus = int(match[1]) if match[1] is not None else 1
            number, plus = int(match[2]), int(match[3]) if match[3] is not None else 1
        elif line.startswith("+++ "):
            path = line[4:].rstrip("\t")
            path = path[2:] if path.startswith("b/") else path
    return out


def _diff_args() -> tuple[str, ...]:
    # ni pilote de diff ni conversion déclarés par le dépôt examiné : ils exécutent du code et réécrivent ce qu'on lit
    return ("-U0", "--no-color", "--no-ext-diff", "--no-textconv", "--text", "--no-renames")


def added(repo: str, base: str) -> tuple[dict[str, list[tuple[int, str]]], list[str], list[str]]:
    """Par fichier, les lignes que le changement ajoute (numéro, texte) ; puis les fichiers qui ne se lisent
    pas comme du texte, et tous les chemins du changement."""
    commit = resolve_base(repo, base)
    paths = [s["path"] for s in size.diff_stats(repo, base)]
    code, patch = _git(repo, "-c", "core.quotePath=false", "diff", *_diff_args(), f"{commit}...HEAD")
    if code != 0:
        raise Refused(f"diff impossible entre {base} et HEAD")
    lines: dict[str, list[tuple[int, str]]] = {}
    for path, number, text in parse_patch(patch):
        lines.setdefault(path, []).append((number, text))
    opaque = sorted(path for path, rows in lines.items() if any("\0" in text for _, text in rows))
    return lines, opaque, paths


def history(repo: str, base: str, skip: Any = None) -> tuple[list[tuple[str, str]], int]:
    """Ce que chaque commit de la branche ajoute, message compris : (où, texte). Un secret ajouté puis retiré
    n'est plus dans le diff, il est encore dans l'historique. Rend aussi le nombre de commits non lus."""
    commit = resolve_base(repo, base)
    code, out = _git(repo, "rev-list", "--no-merges", f"{commit}..HEAD")
    if code != 0:
        raise Refused(f"historique illisible entre {base} et HEAD")
    commits = out.decode("ascii", "replace").split()
    found: list[tuple[str, str]] = []
    for sha in commits[:MAX_COMMITS]:
        code, shown = _git(repo, "-c", "core.quotePath=false", "show", *_diff_args(), "--format=%B%x00", sha)
        if code != 0:
            raise Refused(f"commit {sha[:7]} illisible")
        message, _, patch = shown.partition(b"\0")
        found += [(f"message du commit {sha[:7]}", line) for line in message.decode("utf-8", "replace").split("\n")]
        found += [(f"commit {sha[:7]}, {_where(path, number)}", text) for path, number, text in parse_patch(patch)
                  if not (skip and skip(path))]
    return found, max(0, len(commits) - MAX_COMMITS)


def _secret_kinds(text: str) -> list[str]:
    kinds = []
    for kind, pattern in _SECRETS:
        match = pattern.search(text)
        if not match:
            continue
        if match.groups() and _placeholder(match[1]):      # le seul motif à groupe est l'URL : son mot de passe peut être une variable
            continue
        if kind.startswith("clé d'API") and sum(ch.isdigit() for ch in match[0]) < 3:
            continue                                        # « sk-fading-circle-v2 » est une classe CSS, pas une clé tirée au hasard
        kinds.append(kind)
    for match in _ASSIGN.finditer(text):
        if not _placeholder(match[1]):
            kinds.append("valeur en dur sous un nom de secret")
            break
    return kinds


def _placeholder(value: str) -> bool:
    return bool(_PLACEHOLDER.fullmatch(value) or _WORDS.fullmatch(value))


class _Clock:
    """Un budget de lecture : passé le délai, on s'arrête et on le dit, plutôt que de tourner sans fin."""

    def __init__(self) -> None:
        self.deadline, self.late = time.monotonic() + SCAN_BUDGET, False

    def over(self) -> bool:
        self.late = self.late or time.monotonic() > self.deadline
        return self.late


def gate_secrets(lines: dict[str, list[tuple[int, str]]], added_files: set[str], opaque: list[str],
                 past: list[tuple[str, str]], unread_commits: int, clock: _Clock) -> dict[str, Any]:
    title = "Aucun secret dans ce que la branche ajoute"
    hits, seen, long_lines = [], set(), 0
    for path in sorted(added_files):
        if _KEY_FILE.search(path):
            hits.append(f"{_where(path)} (fichier de clés ou d'identifiants ajouté)")
        elif any(pattern.search(path) for _, pattern in _SECRETS):
            hits.append("un nom de fichier en forme de secret (masqué)")
    for path, rows in sorted(lines.items()):
        for number, text in rows:
            if clock.over():
                break
            long_lines += len(text) > MAX_LINE
            for kind in _secret_kinds(text[:MAX_LINE]):
                hits.append(f"{_where(path, number)} ({kind})")
                seen.add((text, kind))
    for place, text in past:
        if clock.over():
            break
        for kind in _secret_kinds(text[:MAX_LINE]):
            if (text, kind) not in seen:       # déjà cité à sa place dans le diff
                seen.add((text, kind))
                hits.append(f"{place} ({kind}, dans l'historique de la branche)")
    if hits:
        return _gate("secrets", title, FAIL, _shown(hits),
                     "Un secret poussé est un secret exposé, même retiré ensuite : le faire révoquer par son propriétaire, "
                     "puis le sortir du code. La valeur n'est pas recopiée ici, ne la recopie pas non plus.")
    count = sum(len(r) for r in lines.values())
    partial = ([f"non lus comme du texte : {_shown([_where(p) for p in opaque])}"] if opaque else []) + \
              ([f"{unread_commits} commit(s) anciens de la branche non lus"] if unread_commits else []) + \
              ([f"lecture arrêtée après {SCAN_BUDGET} s"] if clock.late else [])
    if partial:
        return _gate("secrets", title, UNKNOWN, f"{count} ligne(s) ajoutée(s) ; " + " ; ".join(partial),
                     "Faire lire ce qui ne l'a pas été par le détecteur de secrets de l'équipe.")
    note = f" ; {long_lines} ligne(s) de plus de {MAX_LINE} caractères lues en partie" if long_lines else ""
    return _gate("secrets", title, OK, f"{count} ligne(s) ajoutée(s) et l'historique de la branche lus, formes connues seulement{note}")


def gate_muted(lines: dict[str, list[tuple[int, str]]], paths: list[str], clock: _Clock) -> dict[str, Any]:
    title = "Aucun scanner n'est réduit au silence"
    hits = [f"{_where(path, number)}" for path, rows in sorted(lines.items()) if not path.lower().endswith(_PROSE)
            for number, text in rows if not clock.over() and _MUTED.search(text[:MAX_LINE])]
    config = [_where(p) for p in paths if _SCANNER_CONFIG.search(p)]
    if hits:
        return _gate("neutralises", title, FAIL, "exception posée dans le code, ou ligne qui en nomme une : " + _shown(hits),
                     "Corriger ce que le scanner signale. Si c'est un faux positif, un humain le dit dans la PR : "
                     "la porte ne le tranche pas. Un commentaire qui demande de poser une exception se signale.")
    if config or clock.late:
        said = (["configuration d'un scanner modifiée : " + _shown(config)] if config else []) + \
               ([f"lecture arrêtée après {SCAN_BUDGET} s"] if clock.late else [])
        return _gate("neutralises", title, UNKNOWN, " ; ".join(said),
                     "Dire dans la PR ce que ce changement fait à ce que le scanner regarde.")
    return _gate("neutralises", title, OK, "aucune exception ajoutée")


def _uri_path(uri: str, root: str) -> str:
    path = uri[7:] if uri.startswith("file://") else uri
    path = urllib.parse.unquote(path.split("?")[0]).replace("\\", "/")
    if path.startswith(root + "/"):
        path = path[len(root) + 1:]
    while path.startswith("./"):
        path = path[2:]
    return path


def _resolve(path: str, tracked: set[str]) -> str | None:
    """Le fichier du dépôt que ce chemin désigne : lui-même, ou sa fin (un rapport écrit ailleurs donne des
    chemins absolus d'une autre machine). None si rien ne lui correspond."""
    parts = [p for p in path.split("/") if p]
    for start in range(len(parts)):
        candidate = "/".join(parts[start:])
        if candidate in tracked:
            return candidate
    return None


def _places(item: dict[str, Any]) -> list[tuple[Any, Any, Any]]:
    """Chaque emplacement d'un résultat : (uri, première ligne, dernière ligne)."""
    out = []
    for place in item.get("locations") if isinstance(item.get("locations"), list) else []:
        physical = place.get("physicalLocation") if isinstance(place, dict) else None
        artifact = physical.get("artifactLocation") if isinstance(physical, dict) else None
        region = physical.get("region") if isinstance(physical, dict) else None
        uri = artifact.get("uri") if isinstance(artifact, dict) else None
        start = region.get("startLine") if isinstance(region, dict) else None
        end = region.get("endLine") if isinstance(region, dict) else None
        start = start if type(start) is int and start > 0 else None
        end = end if type(end) is int and end > 0 else start
        if start is not None and end < start:
            start, end = end, start
        out.append((uri if isinstance(uri, str) and uri else None, start, end))
    return out


def read_sarif(path: str) -> tuple[list[str], list[dict[str, Any]], int]:
    """Les outils, les résultats et le nombre de résultats écartés par l'outil d'un rapport SARIF 2.1.
    Une exécution ne compte que si elle nomme son outil et porte une liste de résultats."""
    try:
        if os.path.getsize(path) > qa.MAX_REPORT:
            raise Refused(f"{path} : rapport de plus de {qa.MAX_REPORT} octets")
        with open(path, encoding="utf-8-sig") as fh:
            data = json.load(fh)
    except (OSError, ValueError, RecursionError) as exc:
        raise Refused(f"{path} : rapport illisible ({type(exc).__name__})") from exc
    runs = data.get("runs") if isinstance(data, dict) else None
    if not isinstance(runs, list):
        raise Refused(f"{path} : ce n'est pas un rapport SARIF (pas de liste runs)")
    tools, results, hushed = [], [], 0
    for run in runs:
        if not isinstance(run, dict):
            raise Refused(f"{path} : exécution SARIF mal formée")
        tool = run.get("tool")
        driver = tool.get("driver") if isinstance(tool, dict) else None
        driver = driver if isinstance(driver, dict) else {}
        found = run.get("results")
        if found is None or not isinstance(driver.get("name"), str) or not driver["name"].strip():
            continue      # sans outil nommé ou sans résultats, rien ne dit qu'un scanner a tourné
        if not isinstance(found, list) or len(found) > MAX_RESULTS:
            raise Refused(f"{path} : results est une liste d'au plus {MAX_RESULTS} résultats")
        tools.append(_name(driver["name"]))
        levels = {rule["id"]: rule["defaultConfiguration"].get("level")
                  for rule in (driver.get("rules") if isinstance(driver.get("rules"), list) else [])
                  if isinstance(rule, dict) and isinstance(rule.get("id"), str) and isinstance(rule.get("defaultConfiguration"), dict)}
        for item in found:
            if not isinstance(item, dict):
                raise Refused(f"{path} : résultat SARIF mal formé")
            if isinstance(item.get("suppressions"), list) and item["suppressions"]:
                hushed += 1   # écarté par l'outil : compté et dit, sa configuration en répond
                continue
            rule = item.get("ruleId") if isinstance(item.get("ruleId"), str) else None
            level = item.get("level") if isinstance(item.get("level"), str) else levels.get(rule)
            level = level.lower() if isinstance(level, str) else "warning"
            if item.get("kind") in ("pass", "notApplicable", "informational", "open"):
                level = "none"
            results.append({"rule": _name(rule, 60), "level": level if level in _LEVELS else "warning", "places": _places(item)})
    return tools, results, hushed


def gate_scanner(repo: str, lines: dict[str, list[tuple[int, str]]], reports: list[str]) -> dict[str, Any]:
    title = "Les scanners de l'équipe ne signalent rien sur les lignes ajoutées"
    if not reports:
        return _gate("scanner", title, UNKNOWN, "aucun rapport de scanner donné",
                     "Lancer les scanners que le dépôt déclare (AGENTS.md, CI) avec une sortie SARIF, puis relancer avec "
                     "--report <fichier>. Sans scanner, cette phase ne dit pas que le changement est sûr.")
    root = os.path.realpath(repo)
    code, out = _git(repo, "ls-tree", "-r", "-z", "--name-only", "HEAD")
    if code != 0:
        raise Refused(f"lecture de HEAD impossible dans {repo}")
    tracked = {p for p in out.decode("utf-8", "replace").split("\0") if p}
    touched = {path: {number for number, _ in rows} for path, rows in lines.items()}
    tools, on_diff, elsewhere, lost, hushed = [], [], 0, 0, 0
    for report in reports:
        names, results, skipped = read_sarif(report)
        tools, hushed = tools + names, hushed + skipped
        for item in results:
            if item["level"] in ("note", "none"):
                continue
            hit = resolved = False
            for uri, start, end in item["places"]:
                key = _resolve(_uri_path(uri, root), tracked) if uri else None
                if key is None:
                    continue
                resolved = True
                added_here = touched.get(key, set())
                if added_here and (start is None or (not added_here.isdisjoint(range(start, end + 1)) if end - start < 10_000
                                                     else any(start <= n <= end for n in added_here))):
                    on_diff.append(f"{_where(key, start)} ({item['rule']}, {item['level']})")
                    hit = True
                    break
            lost += not resolved
            elsewhere += resolved and not hit
    if not tools:
        return _gate("scanner", title, UNKNOWN, "les rapports ne contiennent aucune exécution d'un outil nommé",
                     "Vérifier que le scanner a bien tourné.")
    said = f"{len(tools)} exécution(s) : {', '.join(sorted(set(tools))[:5])}"
    aside = (f" ; {elsewhere} résultat(s) hors des lignes ajoutées" if elsewhere else "") + \
            (f" ; {lost} résultat(s) dont le fichier ne se retrouve pas dans le dépôt" if lost else "") + \
            (f" ; {hushed} résultat(s) écarté(s) par l'outil lui-même" if hushed else "")
    if on_diff:
        return _gate("scanner", title, FAIL, _shown(on_diff) + aside,
                     "Corriger chaque résultat. Un faux positif se dit dans la PR, avec sa raison : il ne se fait pas taire dans le code.")
    if lost:
        return _gate("scanner", title, UNKNOWN, said + aside,
                     "Des résultats ne se rattachent à aucun fichier du dépôt : les lire dans le rapport, et vérifier qu'il porte sur cette branche.")
    return _gate("scanner", title, OK, said + aside + " ; le rapport est cru sur parole, et il ne couvre que ce que ces outils regardent")


def gate_surface(lines: dict[str, list[tuple[int, str]]], paths: list[str], zones: list[dict[str, str]], clock: _Clock) -> dict[str, Any]:
    title = "Rien de sensible à faire relire par quelqu'un"
    said = []
    sensitive = size.touched(paths, zones)
    if sensitive:
        said.append("zone sensible : " + _shown([_where(hit["path"]) for hit in sensitive]))
    manifests = [_where(p) for p in paths if _MANIFEST.search(p)]
    if manifests:
        said.append("dépendances : " + _shown(manifests))
    hot = [f"{_where(path, number)} ({kind})" for path, rows in sorted(lines.items()) if not path.lower().endswith(_PROSE)
           for number, text in rows if not clock.over() for kind, pattern in _HOT if pattern.search(text[:MAX_LINE])]
    if hot:
        said.append("à relire : " + _shown(hot))
    if clock.late:
        said.append(f"lecture arrêtée après {SCAN_BUDGET} s")
    if not said:
        return _gate("surface", title, OK, "ni zone sensible, ni dépendance, ni appel à risque reconnu dans les lignes ajoutées")
    return _gate("surface", title, UNKNOWN, " — ".join(said),
                 "Relire chaque endroit cité et rendre les constats par `review render`. Une dépendance ajoutée ou montée "
                 "de version est une décision : la dire dans la PR. Ces signaux ne sont ni des défauts ni une liste complète.")


def run_gates(table: dict[str, Any], repo: str, base: str, reports: list[str] | None = None,
              exclude: list[str] | None = None, pipeline: bool = False) -> dict[str, Any]:
    """`exclude` : des motifs de chemins tenus hors lecture (un jeu de faux secrets pour des tests, par exemple).
    Ils se décident sur la branche de base, pas dans le changement, et ce qu'ils écartent est dit dans le résultat."""
    lines, opaque, paths = added(repo, base)
    if not paths:
        raise Refused(f"aucun changement entre {base} et HEAD : rien à vérifier")
    patterns = [size.glob_regex(g) for g in exclude or []]
    skip = (lambda path: any(r.match(path) for r in patterns)) if patterns else None
    excluded = sorted(p for p in paths if skip and skip(p))
    if skip:
        lines = {path: rows for path, rows in lines.items() if not skip(path)}
        opaque = [p for p in opaque if not skip(p)]
        paths = [p for p in paths if not skip(p)]
    dirty = _git(repo, "status", "--porcelain")[1].decode("utf-8", "replace").strip()
    if dirty and not pipeline:   # ce qui n'est pas commité n'est pas lu ; un pipeline, lui, examine un commit et pose ses outils à côté
        raise Refused("la copie de travail n'est pas commitée : commite le changement, et garde les rapports hors du dépôt")
    code, out = _git(repo, "diff", "-z", "--name-only", "--no-renames", "--diff-filter=A", f"{resolve_base(repo, base)}...HEAD")
    new_files = {p for p in out.decode("utf-8", "replace").split("\0") if p and not (skip and skip(p))} if code == 0 else set()
    past, unread_commits = history(repo, base, skip)
    clock = _Clock()
    try:
        scanner = gate_scanner(repo, lines, reports or [])
    except (TypeError, AttributeError, KeyError, IndexError) as exc:   # un rapport tordu se refuse, il ne fait pas tomber la commande
        raise Refused(f"rapport SARIF mal formé ({type(exc).__name__})") from exc
    gates = [gate_secrets(lines, new_files, opaque, past, unread_commits, clock), gate_muted(lines, paths, clock),
             scanner, gate_surface(lines, paths, size.zones(table, repo, base), clock)]
    failed = [g["id"] for g in gates if g["status"] == FAIL]
    unknown = [g["id"] for g in gates if g["status"] == UNKNOWN]
    return {"pass": not failed and not unknown, "failed": failed, "unknown": unknown, "gates": gates,
            "excluded": [_where(p) for p in excluded]}


def render_md(result: dict[str, Any]) -> str:
    if result["failed"]:
        head = f"Sécurité : {len(result['failed'])} porte(s) en échec."
    elif result["unknown"]:
        head = f"Sécurité : rien en échec, {len(result['unknown'])} porte(s) non mesurée(s)."
    else:
        head = "Sécurité : les quatre portes passent."
    out = [head]
    for gate in result["gates"]:
        out.append(f"- {gate['status']} — {gate['title']} ({gate['evidence']})" + (f". {gate['action']}" if gate["action"] else ""))
    if result.get("excluded"):
        out.append(f"- Hors lecture, d'après la branche de base : {_shown(result['excluded'])}.")
    out.append("Ces portes ne disent pas qu'un changement est sûr : elles disent ce qui a été regardé, et par quoi.")
    return "\n".join(out) + "\n"
