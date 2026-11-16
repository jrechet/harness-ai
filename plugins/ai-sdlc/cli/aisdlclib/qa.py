"""Les portes de `/qa` : ce qu'un programme peut dire des tests d'un changement.

Quatre portes, chacune `ok`, `échec`, ou `non mesuré` quand le dépôt ne donne pas de quoi trancher :
- **désactivés** : le diff ne saute, ne désactive ni ne supprime aucun test ;
- **répété** : la commande de test passe plusieurs fois de suite (un test instable échoue ici) ;
- **couverture** : les lignes ajoutées sont exécutées, d'après un rapport lcov ou Cobertura du dépôt ;
- **critères** : chaque critère d'acceptation du ticket a un test nommé qui existe, ou une raison écrite.

Écrire les tests est le travail de l'agent. Dire qu'ils tiennent ne l'est pas : c'est ce module."""
from __future__ import annotations

import contextlib
import os
import re
import shlex
import signal
import subprocess
import tempfile
import time
import xml.etree.ElementTree as ET
from typing import Any

from . import size, ticket
from .context import Refused, _git, resolve_base
from .devgrade import _changed_lines

OK, FAIL, UNKNOWN = "ok", "échec", "non mesuré"
RUN_TIMEOUT = 600      # par passage
RUN_BUDGET = 1800      # pour tous les passages
MAX_REPORT = 50_000_000
MIN_REASON = 15
_SKIP = re.compile(r"unittest\.skip|(?:^|\s)@skip\w*\b|\bimport\s+.*\bskip\w*\b|\bskipTest\b|\bSkipTest\b|pytest\.mark\.(?:skip|xfail)|pytest\.(?:skip|xfail)\(|importorskip|"
                   r"expectedFailure|\b(?:it|test|describe|context)\.(?:skip|todo|only|fixme|fail)\b|\b[xf](?:it|describe|test)\(|"
                   r"@Disabled\w*\b|@Ignore\b|\[Ignore\b|Skip\s*=|enabled\s*=\s*false|assumeTrue\(false\)|"
                   r"\bt\.Skip(?:f|Now)?\(|#\[ignore\b|\bpending\(|__test__\s*=\s*False|collect_ignore|--deselect")
_TEST_PATH = re.compile(r"(?:^|/)(?:tests?|__tests__|__mocks__|specs?|e2e|cypress)/|(?:^|/)tests?\.py$|(?:^|/)test_[^/]+\.\w+$|"
                        r"(?:^|/)conftest\.py$|_test\.\w+$|\.(?:test|spec)\.[cm]?[jt]sx?$|(?:Tests?|IT|Spec)\.(?:java|kt|cs|scala|php)$|"
                        r"_spec\.rb$|\.feature$", re.IGNORECASE)
_TEST_CONFIG = re.compile(r"(?:^|/)(?:pytest\.ini|tox\.ini|setup\.cfg|pyproject\.toml|conftest\.py|package\.json|phpunit\.xml(?:\.dist)?|"
                          r"jest\.config\.\w+|vitest\.config\.\w+|playwright\.config\.\w+|karma\.conf\.\w+|\.mocharc[\w.]*|"
                          r"\.rspec|noxfile\.py|build\.gradle(?:\.kts)?|pom\.xml)$")
_CODE_EXT = (".py", ".js", ".jsx", ".mjs", ".ts", ".tsx", ".go", ".java", ".kt", ".rb", ".rs", ".cs", ".php", ".c", ".cpp",
             ".cc", ".h", ".hpp", ".swift", ".scala", ".vue", ".svelte", ".dart")
_ASSERT = re.compile(r"\bassert\w*\b|\bexpect\(|\bshould\b|\brequire\.\w+\(|\bverify\(")
_TEST_NAME = re.compile(r"\bdef\s+(test\w*)|\bfunc\s+(Test\w+)|\bfn\s+(test\w*)|\b(?:it|test)\(\s*['\"`]([^'\"`]+)|\bvoid\s+(test\w+)\s*\(")
_SHELL = {"&&", "||", "|", ";", "&", ">", ">>", "<", "2>&1"}
_SECRET = re.compile(r"TOKEN|SECRET|PASSWORD|PASSWD|CREDENTIAL|API_?KEY|PRIVATE", re.IGNORECASE)
_HUNK = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@")


def _comment(line: str) -> bool:
    text = line.lstrip()
    return text.startswith(("//", "/*", "*", "--")) or (text.startswith("#") and not text.startswith(("#[", "#!")))


def skips(lines: list[str]) -> bool:
    """Une de ces lignes saute ou désactive un test. Une ligne de commentaire qui en parle ne saute rien."""
    return any(_SKIP.search(line) for line in lines if not _comment(line))


def is_test(path: str) -> bool:
    return bool(_TEST_PATH.search(path))


def _gate(ident: str, title: str, status: str, evidence: str, action: str | None = None) -> dict[str, Any]:
    return {"id": ident, "title": title, "status": status, "evidence": evidence, "action": None if status == OK else action}


def _names(lines: list[str]) -> set[str]:
    return {next(g for g in m.groups() if g) for line in lines for m in _TEST_NAME.finditer(line)}


def gate_disabled(repo: str, base: str, paths: list[str]) -> dict[str, Any]:
    """Aucun test sauté, désactivé, retiré ou supprimé par le diff. Ce qui ne se tranche pas par règle
    (la configuration des tests a changé, des affirmations ont disparu) rend la porte non mesurée."""
    title = "Aucun test désactivé, retiré ni supprimé"
    code, out = _git(repo, "diff", "-z", "--name-only", "--diff-filter=D", "-M", f"{resolve_base(repo, base)}...HEAD")
    deleted = [p for p in out.decode("utf-8", "replace").split("\0") if p and is_test(p)] if code == 0 else []
    skipped, gone, weakened = [], [], []
    config = [p for p in paths if _TEST_CONFIG.search(p)]
    for path in paths:
        if not (is_test(path) or _TEST_CONFIG.search(path)):
            continue
        added, removed = _changed_lines(repo, base, path, "+"), _changed_lines(repo, base, path, "-")
        if skips(added):
            skipped.append(path)
        lost = sorted(_names(removed) - _names(added))
        if lost and os.path.exists(os.path.join(repo, path)):
            gone.append(f"{path} ({', '.join(lost[:3])})")
        if os.path.exists(os.path.join(repo, path)) and \
                sum(bool(_ASSERT.search(line)) for line in removed) > sum(bool(_ASSERT.search(line)) for line in added):
            weakened.append(path)
    if deleted or skipped or gone:
        said = ([f"supprimé : {p}" for p in deleted[:3]] + [f"sauté ou désactivé : {p}" for p in skipped[:3]]
                + [f"test retiré ou renommé : {g}" for g in gone[:3]])
        return _gate("desactives", title, FAIL, " ; ".join(said),
                     "Remettre le test et corriger ce qui le fait échouer. Si le retrait est voulu (un test qui porte sur "
                     "le skip lui-même, un renommage), un humain le dit dans la PR : la porte ne le tranche pas.")
    if config or weakened:
        said = [f"configuration des tests modifiée : {p}" for p in config[:3]] + [f"moins d'affirmations qu'avant : {p}" for p in weakened[:3]]
        return _gate("desactives", title, UNKNOWN, " ; ".join(said),
                     "Dire dans la PR ce que ce changement fait aux tests collectés et aux affirmations.")
    return _gate("desactives", title, OK, "rien de sauté, de retiré ni de supprimé")


def _argv(command: str) -> list[str]:
    try:
        argv = shlex.split(command)
    except ValueError as exc:
        raise Refused(f"--run illisible : {exc}") from exc
    if not argv:
        raise Refused("--run est vide")
    if any(t in _SHELL for t in argv) or re.match(r"^\w+=", argv[0]) or argv[0] in ("cd", "export", "source", "."):
        raise Refused("--run est lancé sans shell : pas de &&, de tube, de redirection ni de VAR=valeur en tête. "
                      "Donne une commande du dépôt (make test, ./scripts/test.sh), ou sh -c '…'")
    return argv


def gate_repeat(repo: str, command: str | None, runs: int) -> dict[str, Any]:
    """La commande de test, lancée plusieurs fois : toutes passent, ou c'est un échec ou un test instable.
    Elle tourne dans le dépôt, sans bac à sable ; les variables qui ont l'air de secrets ne lui sont pas passées."""
    title = f"La suite passe {runs} fois de suite"
    if not command:
        return _gate("repete", title, UNKNOWN, "aucune commande de test donnée",
                     "Relancer avec --run \"<la commande de test du dépôt>\".")
    argv = _argv(command)
    env = {k: v for k, v in os.environ.items() if not _SECRET.search(k)}
    passed, last, started = 0, "", time.monotonic()
    for index in range(runs):
        if time.monotonic() - started > RUN_BUDGET:
            return _gate("repete", title, FAIL, f"{index} passage(s) en plus de {RUN_BUDGET} s : budget dépassé",
                         "Donner une commande plus ciblée : la suite entière est trop lente pour être répétée.")
        with tempfile.TemporaryFile() as log:
            try:
                proc = subprocess.Popen(argv, cwd=repo, stdout=log, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
                                        env=env, start_new_session=True)
            except OSError as exc:
                return _gate("repete", title, FAIL, f"{argv[0]} : {type(exc).__name__}",
                             "La commande ne se lance pas depuis la racine du dépôt : vérifier son nom et son chemin.")
            try:
                code = proc.wait(timeout=RUN_TIMEOUT)
            except subprocess.TimeoutExpired:
                with contextlib.suppress(OSError):
                    os.killpg(proc.pid, signal.SIGKILL)   # le groupe entier : un lanceur laisse des enfants
                proc.wait()
                return _gate("repete", title, FAIL, f"passage {index + 1} : plus de {RUN_TIMEOUT} s",
                             "La suite ne rend pas la main : chercher un test qui attend une entrée, un port ou un verrou.")
            if code != 0:
                log.seek(max(0, log.tell() - 4000))
                last = " ".join(log.read().decode("utf-8", "replace").strip().splitlines()[-1:])[:160]
            passed += code == 0
    if passed == runs:
        return _gate("repete", title, OK, f"{runs} passages sur {runs}, dans le même ordre : un test qui échoue rarement "
                                          "ou selon l'ordre peut encore passer")
    if passed:
        return _gate("repete", title, FAIL, f"instable : {passed} passages sur {runs} ({last})",
                     "Trouver ce qui rend le test instable (ordre, horloge, réseau, état partagé) : ne pas le relancer jusqu'à ce qu'il passe.")
    return _gate("repete", title, FAIL, f"0 passage sur {runs} ({last})", "Corriger le code ou le test qui échoue.")


def read_coverage(path: str) -> dict[str, dict[int, int]]:
    """Par fichier, les lignes mesurées et leur nombre de passages, lus d'un rapport lcov ou Cobertura."""
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            text = fh.read(MAX_REPORT + 1)
    except OSError as exc:
        raise Refused(f"{path} : rapport de couverture illisible ({exc})") from exc
    if len(text) > MAX_REPORT:
        raise Refused(f"{path} : rapport de plus de {MAX_REPORT} caractères, non lu")
    found: dict[str, dict[int, int]] = {}
    if text.lstrip().startswith("<"):
        if "<!DOCTYPE" in text or "<!ENTITY" in text:
            raise Refused(f"{path} : un rapport XML avec DOCTYPE ou entités n'est pas lu")
        try:
            root = ET.fromstring(text)
        except ET.ParseError as exc:
            raise Refused(f"{path} : XML illisible ({exc})") from exc
        for cls in root.iter("class"):
            lines = found.setdefault((cls.get("filename") or "").replace("\\", "/"), {})
            for line in cls.iter("line"):
                try:
                    number, hits = int(line.get("number", "")), int(float(line.get("hits", "0")))
                except ValueError:
                    continue
                lines[number] = max(lines.get(number, 0), hits)
        return found
    current: dict[int, int] | None = None
    for line in text.splitlines():
        if line.startswith("SF:"):
            current = found.setdefault(line[3:].strip().replace("\\", "/"), {})
        elif line.startswith("DA:") and current is not None:
            parts = line[3:].split(",")
            if len(parts) >= 2 and parts[0].isdigit() and parts[1].lstrip("-").isdigit():
                current[int(parts[0])] = max(current.get(int(parts[0]), 0), int(parts[1]))
    return found


def added_lines(repo: str, base: str) -> dict[str, set[int]]:
    """Par fichier, les seules lignes que le diff ajoute ou réécrit : une suppression n'en ajoute aucune."""
    commit = resolve_base(repo, base)
    code, out = _git(repo, "diff", "-z", "--name-only", "--no-renames", "--diff-filter=AM", f"{commit}...HEAD")
    if code != 0:
        raise Refused(f"diff impossible entre {base} et HEAD")
    found: dict[str, set[int]] = {}
    for raw in filter(None, out.split(b"\0")):
        path = raw.decode("utf-8", "replace")
        code, patch = _git(repo, "--literal-pathspecs", "diff", "-U0", "--no-color", "--no-ext-diff", "--no-textconv",
                           "--no-renames", f"{commit}...HEAD", "--", path)
        lines = found.setdefault(path, set())
        for line in patch.decode("utf-8", "replace").splitlines() if code == 0 else []:
            match = _HUNK.match(line)
            if match and (match[2] is None or int(match[2]) > 0):
                start, count = int(match[1]), int(match[2] or 1)
                lines.update(range(start, start + count))
    return found


def _report_key(path: str, measured: dict[str, dict[int, int]]) -> str | None:
    """L'entrée du rapport qui désigne ce fichier : le plus long suffixe commun, sur des segments entiers."""
    parts = path.split("/")
    best, score = None, 0
    for key in measured:
        other = key.split("/")
        common = 0
        while common < min(len(parts), len(other)) and parts[-1 - common] == other[-1 - common]:
            common += 1
        if common > score and (common == len(parts) or common == len(other)):
            best, score = key, common
    return best


def gate_coverage(repo: str, base: str, report: str | None, threshold: int) -> dict[str, Any]:
    """La part des lignes ajoutées, dans le code hors tests, que les tests exécutent. Le rapport est
    cru sur parole : rien n'empêche de l'écrire à la main, et la porte ne prétend pas le contraire."""
    title = f"Les lignes ajoutées sont exécutées par les tests (au moins {threshold} %)"
    if not report:
        return _gate("couverture", title, UNKNOWN, "aucun rapport de couverture donné",
                     "Produire un rapport lcov ou Cobertura avec l'outil du dépôt, puis relancer avec --coverage <fichier>.")
    measured = read_coverage(report)
    stamp = (_git(repo, "log", "-1", "--format=%ct", "HEAD")[1] or b"").decode().strip()
    if stamp.isdigit() and os.path.getmtime(report) < int(stamp):
        return _gate("couverture", title, UNKNOWN, "le rapport est plus ancien que le dernier commit",
                     "Reproduire le rapport sur cette branche, après le dernier commit.")
    changed = {p: lines for p, lines in added_lines(repo, base).items()
               if lines and p.endswith(_CODE_EXT) and not is_test(p) and not _TEST_CONFIG.search(p)}
    total = hit = 0
    missed: list[str] = []
    absent: list[str] = []
    used: dict[str, str] = {}
    for path, lines in sorted(changed.items()):
        key = _report_key(path, measured)
        if key is None:
            absent.append(path)
            continue
        if key in used:
            return _gate("couverture", title, UNKNOWN, f"chemin ambigu dans le rapport : {key} vaut pour {used[key]} et {path}",
                         "Produire le rapport avec des chemins relatifs à la racine du dépôt.")
        used[key] = path
        seen = [n for n in sorted(lines) if n in measured[key]]
        total += len(seen)
        hit += sum(measured[key][n] > 0 for n in seen)
        missed += [f"{path}:{n}" for n in seen if measured[key][n] == 0]
    share = 100 * hit // total if total else 0
    evidence = f"{hit} lignes sur {total} ({share} %), {len(changed) - len(absent)} fichier(s) sur {len(changed)} mesuré(s)"
    if missed:
        evidence += f" ; jamais exécutées : {', '.join(missed[:4])}"
    if total and share < threshold:
        return _gate("couverture", title, FAIL, evidence,
                     "Écrire le test qui passe par ces lignes, ou dire dans la PR pourquoi elles n'en ont pas.")
    if absent or not total:
        return _gate("couverture", title, UNKNOWN, evidence + (f" ; absents du rapport : {', '.join(absent[:4])}" if absent else ""),
                     "Un fichier changé absent du rapport n'est exécuté par aucun test, ou le rapport ne le suit pas : le vérifier.")
    return _gate("couverture", title, OK, evidence)


def _defined(name: str, text: str) -> bool:
    """Le nom figure comme un mot entier sur une ligne qui n'est pas un commentaire."""
    pattern = re.compile(r"(?<![\w])" + re.escape(name) + r"(?![\w])")
    return any(pattern.search(line) for line in text.splitlines() if not line.lstrip().startswith(("#", "//", "*", "/*")))


def gate_criteria(repo: str, ticket_text: str | None, mapping: Any) -> dict[str, Any]:
    """Chaque critère d'acceptation a un test nommé qui existe dans un fichier de test du dépôt, ou une
    raison écrite. Un critère laissé sans test attend un humain ; aucun critère testé est un échec."""
    title = "Chaque critère d'acceptation a son test"
    if ticket_text is None or mapping is None:
        return _gate("criteres", title, UNKNOWN, "ticket ou correspondance absents",
                     "Relancer avec --ticket <ticket.md> et --trace <correspondance.json>.")
    criteria = ticket.check(ticket_text, [])["criteria"]
    if not criteria:
        return _gate("criteres", title, UNKNOWN, "le ticket ne liste aucun critère", "Passer le ticket par le skill ticket d'abord.")
    rows = mapping.get("criteres") if isinstance(mapping, dict) else None
    spared = mapping.get("non_couverts", []) if isinstance(mapping, dict) else None
    if not isinstance(rows, list) or not isinstance(spared, list):
        raise Refused("correspondance : un objet {criteres: [{critere, tests}], non_couverts: [{critere, pourquoi}]}")
    covered: dict[int, list[str]] = {}
    for row in rows:
        if not (isinstance(row, dict) and type(row.get("critere")) is int and isinstance(row.get("tests"), list)
                and all(isinstance(t, str) and t.strip() for t in row["tests"])):
            raise Refused(f"correspondance : ligne mal formée ({row!r:.80})")
        covered.setdefault(row["critere"], []).extend(row["tests"])
    excused = {r["critere"] for r in spared if isinstance(r, dict) and type(r.get("critere")) is int
               and isinstance(r.get("pourquoi"), str) and len(r["pourquoi"].strip()) >= MIN_REASON}
    root = os.path.realpath(repo)
    problems = []
    for number in range(1, len(criteria) + 1):
        tests = covered.get(number, [])
        if not tests and number not in excused:
            problems.append(f"critère {number} sans test ni raison d'au moins {MIN_REASON} caractères")
        for ref in tests:
            path, _, name = ref.partition("::")
            path, name = path.strip(), name.split("::")[-1].strip()
            if "\0" in path or len(path) > 300:
                problems.append(f"critère {number} : chemin de test illisible")
                continue
            full = os.path.realpath(os.path.join(repo, path))
            if not name:
                problems.append(f"critère {number} : {ref} ne nomme pas de test (chemin::nom)")
            elif path.startswith("/") or os.path.commonpath([root, full]) != root or not os.path.isfile(full):
                problems.append(f"critère {number} : {path} n'existe pas dans le dépôt")
            elif not is_test(path):
                problems.append(f"critère {number} : {path} n'est pas un fichier de test")
            else:
                with open(full, encoding="utf-8", errors="replace") as fh:
                    if not _defined(name, fh.read(2_000_000)):
                        problems.append(f"critère {number} : {name} introuvable dans {path}")
    unknown = sorted((set(covered) | excused) - set(range(1, len(criteria) + 1)))
    if unknown:
        problems.append(f"critère(s) {', '.join(map(str, unknown))} : le ticket n'en a que {len(criteria)}")
    tested = [n for n in range(1, len(criteria) + 1) if covered.get(n)]
    if not problems and not tested:
        problems.append("aucun critère n'a de test : tous sont excusés")
    if problems:
        return _gate("criteres", title, FAIL, " ; ".join(problems[:5]),
                     "Écrire le test manquant, ou inscrire le critère dans non_couverts avec sa raison.")
    shared = {ref for refs in covered.values() for ref in refs if sum(ref in r for r in covered.values()) > max(1, len(criteria) // 2)}
    if excused or shared:
        said = [f"{len(tested)} critères sur {len(criteria)} testés"]
        said += [f"sans test, avec raison : {sorted(excused)}"] if excused else []
        said += [f"un même test pour plus de la moitié des critères : {', '.join(sorted(shared)[:2])}"] if shared else []
        return _gate("criteres", title, UNKNOWN, " ; ".join(said),
                     "Faire valider par un humain les critères sans test, et vérifier qu'un seul test porte bien plusieurs critères.")
    return _gate("criteres", title, OK, f"{len(criteria)} critères sur {len(criteria)}")


def run_gates(table: dict[str, Any], repo: str, base: str, command: str | None = None, runs: int | None = None,
              coverage: str | None = None, ticket_text: str | None = None, mapping: Any = None) -> dict[str, Any]:
    stats = size.diff_stats(repo, base)
    if not stats:
        raise Refused(f"aucun changement entre {base} et HEAD : rien à vérifier")
    dirty = _git(repo, "status", "--porcelain")[1].decode("utf-8", "replace").strip()
    if dirty:   # deux portes lisent HEAD, deux lisent le disque : elles doivent parler du même changement
        raise Refused("la copie de travail n'est pas commitée (" + dirty.splitlines()[0].strip() + "…) : commite les tests, "
                      "et garde le rapport de couverture et la correspondance hors du dépôt")
    settings = table["qa"]
    gates = [gate_disabled(repo, base, [s["path"] for s in stats]),
             gate_repeat(repo, command, runs or settings["runs"]),
             gate_coverage(repo, base, coverage, settings["diff_coverage"]),
             gate_criteria(repo, ticket_text, mapping)]
    failed = [g["id"] for g in gates if g["status"] == FAIL]
    unknown = [g["id"] for g in gates if g["status"] == UNKNOWN]
    return {"pass": not failed and not unknown, "failed": failed, "unknown": unknown, "gates": gates}


def render_md(result: dict[str, Any]) -> str:
    if result["failed"]:
        head = f"QA : {len(result['failed'])} porte(s) en échec."
    elif result["unknown"]:
        head = f"QA : rien en échec, {len(result['unknown'])} porte(s) non mesurée(s)."
    else:
        head = "QA : les quatre portes passent."
    out = [head]
    for gate in result["gates"]:
        out.append(f"- {gate['status']} — {gate['title']} ({gate['evidence']})" + (f". {gate['action']}" if gate["action"] else ""))
    out.append("Une porte non mesurée n'est pas une porte passée : dis-le dans la PR.")
    return "\n".join(out) + "\n"
