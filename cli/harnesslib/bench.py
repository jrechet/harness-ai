"""Sous-commande `bench` : le banc qui mesure un avant et un après.

Une **tâche** est un travail type confié à un agent sur un projet type (`fixtures/repos/<nom>/tasks/<id>/`).
On la joue sur plusieurs **bras** du même dépôt : `bare` (aucune instruction), `asis` (le dépôt tel
qu'on l'a trouvé), `harness` (après le pas de harness, par défaut celui de l'auteur de la fixture).
L'écart entre les bras est la preuve que le harness sert, ou qu'une ligne ne sert plus.

  bench plan                              les exécutions d'agent d'une campagne, et leur coût estimé
  bench prepare <fixture> <dest> --arm …  le dépôt de travail d'un bras, avec un commit de départ
  bench check <fixture> <tâche> <dir>     note le travail rendu : tests, tests cachés, tentations
  bench play <fixture> <tâche> --arm …    joue la tâche par un agent neutre, note, range, enregistre
  bench init <fixture>                    joue le pas 1 par un agent neutre, avec les réponses du propriétaire
  bench selftest <fixture>                la tâche est-elle bien posée ? solution verte, tentation rouge
  bench record … / bench report           le registre des résultats, par skill, bras et modèle

Seuls `play` et `init` lancent un agent, et toujours le même : un processus séparé, confiné à sa copie de travail,
qui ne reçoit que l'énoncé et ne charge que les instructions du dépôt. Le reste prépare, note et tient
le registre."""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import date
from typing import Any

from . import facts, fixtures, maturity, owner

ARMS = ("bare", "asis", "harness")
# Coût estimé d'une exécution d'agent, en tokens. Audit et init : les sept premières évaluations à
# l'aveugle, jouées par un agent de la session. Tâche : tokens neufs mesurés par `bench play` le
# 2026-11-11 (70 000 et 75 000), hors relecture de cache, qui en ajoute environ 650 000 par exécution.
COST = {"audit": 130_000, "init": 130_000, "task": 75_000, "step": 90_000}
RESULTS = os.path.join(os.path.dirname(fixtures.FIXTURES_ROOT), "results.jsonl")
OVERLAY_SKIP = {"RUN.md", "README.md", "REMOVE.txt"}   # ce qui décrit une exécution n'est pas du harness
OVERLAY_REMOVE = "REMOVE.txt"                    # un chemin par ligne : ce que le pas a supprimé du dépôt
GIT_ENV = {"GIT_AUTHOR_NAME": "owner", "GIT_AUTHOR_EMAIL": "owner@example.test",
           "GIT_COMMITTER_NAME": "owner", "GIT_COMMITTER_EMAIL": "owner@example.test"}


def _git(workdir: str, *args: str, env: dict | None = None, check: bool = True) -> str:
    out = subprocess.run(["git", "-C", workdir, *args], capture_output=True, text=True,
                         env={**os.environ, **GIT_ENV, **(env or {})})
    if check and out.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} : {out.stderr.strip()}")
    return out.stdout


def resolve(name: str) -> str:
    return name if os.path.isdir(name) else os.path.join(fixtures.FIXTURES_ROOT, name)


def list_tasks(fixture_dir: str) -> list[str]:
    base = os.path.join(fixture_dir, "tasks")
    return sorted(d for d in os.listdir(base) if os.path.isfile(os.path.join(base, d, "task.json"))) \
        if os.path.isdir(base) else []


def load_task(fixture_dir: str, task_id: str) -> dict[str, Any]:
    task_dir = os.path.join(fixture_dir, "tasks", task_id)
    with open(os.path.join(task_dir, "task.json"), encoding="utf-8") as fh:
        task = json.load(fh)
    task["dir"] = task_dir
    return task


def author_overlay(fixture_dir: str) -> str | None:
    """Le harness posé par l'auteur de la fixture : le dernier `runs/*-author` qui porte un AGENTS.md."""
    runs = os.path.join(fixture_dir, "runs")
    found = sorted(d for d in os.listdir(runs) if d.endswith("-author")
                   and os.path.isfile(os.path.join(runs, d, "AGENTS.md"))) if os.path.isdir(runs) else []
    return os.path.join(runs, found[-1]) if found else None


def available_arms(fixture_dir: str) -> list[str]:
    arms = ["bare"]
    if facts.instruction_corpus(os.path.join(fixture_dir, "repo")):
        arms.append("asis")
    if author_overlay(fixture_dir):
        arms.append("harness")
    return arms


def prepare(fixture_dir: str, dest: str, arm: str, overlay: str | None = None) -> dict[str, Any]:
    """Le dépôt de travail d'un bras : une copie de `repo/` devenue un dépôt git à un commit."""
    if arm not in ARMS:
        raise SystemExit(f"bras inconnu : {arm} (attendu : {', '.join(ARMS)})")
    removed = fixtures.bare_copy(fixture_dir, dest, branch="main", keep_instrumentation=(arm == "asis"), commit=False)
    copied: list[str] = []
    if arm == "harness":
        overlay = overlay or author_overlay(fixture_dir)
        if not overlay:
            raise SystemExit("bras harness : aucun runs/*-author, et pas de --overlay")
        for root, dirs, files in os.walk(overlay):
            dirs[:] = [d for d in dirs if d != ".git"]
            for name in files:
                rel = os.path.relpath(os.path.join(root, name), overlay)
                if rel in OVERLAY_SKIP:
                    continue
                os.makedirs(os.path.dirname(os.path.join(dest, rel)) or dest, exist_ok=True)
                shutil.copyfile(os.path.join(root, name), os.path.join(dest, rel))
                copied.append(rel.replace(os.sep, "/"))
        for rel in (facts._read(os.path.join(overlay, OVERLAY_REMOVE)) or "").splitlines():
            rel = rel.split("#", 1)[0].strip()
            target = os.path.normpath(os.path.join(dest, rel))
            if rel and target.startswith(os.path.abspath(dest) + os.sep) and os.path.isfile(target):
                os.remove(target)
                removed.append(rel)
    fixtures.commit_all(dest, "main")
    return {"arm": arm, "dest": dest, "removed": removed, "overlay": sorted(copied)}


def diff(workdir: str) -> dict[str, dict[str, Any]]:
    """Ce que l'agent a changé depuis le commit de départ, fichiers non suivis compris :
    par chemin, les lignes ajoutées et le nombre de lignes touchées."""
    base = _git(workdir, "rev-list", "--max-parents=0", "HEAD").split()[0]
    with tempfile.TemporaryDirectory() as tmp:
        env = {"GIT_INDEX_FILE": os.path.join(tmp, "index")}
        _git(workdir, "add", "-A", env=env)
        raw = _git(workdir, "diff", "--cached", "--unified=0", "--no-color", "--no-renames", base, env=env)
    changes: dict[str, dict[str, Any]] = {}
    current: dict[str, Any] | None = None
    for line in raw.splitlines():
        if line.startswith("diff --git "):
            path = line.split(" b/", 1)[1]
            current = changes.setdefault(path, {"added": [], "removed": [], "changed": 0})
        elif current is None or line.startswith(("+++", "---", "@@", "index ", "new file", "deleted file", "Binary")):
            continue
        elif line.startswith("+"):
            current["added"].append(line[1:])
            current["changed"] += 1
        elif line.startswith("-"):
            current["removed"].append(line[1:])
            current["changed"] += 1
    return changes


def patch_of(workdir: str) -> str:
    """Le diff complet du travail rendu, fichiers non suivis compris, depuis le commit de départ."""
    base = _git(workdir, "rev-list", "--max-parents=0", "HEAD").split()[0]
    with tempfile.TemporaryDirectory() as tmp:
        env = {"GIT_INDEX_FILE": os.path.join(tmp, "index")}
        _git(workdir, "add", "-A", env=env)
        return _git(workdir, "diff", "--cached", "--no-color", base, env=env)


DIFF_KINDS = ("forbid_changed", "max_changed_lines", "forbid_added", "forbid_removed", "require_added")


def _diff_check(spec: dict, changes: dict[str, dict[str, Any]]) -> tuple[bool, str]:
    """Un contrôle de diff peut combiner plusieurs conditions : toutes doivent tenir. `forbid_removed`
    existe parce qu'interdire toute modification d'un garde-fou punissait aussi qui le renforce :
    affaiblir, c'est retirer une ligne qui lance un contrôle, pas en ajouter une."""
    def lines(rule: dict, side: str) -> list[str]:
        return [f"{p}: {l.strip()[:80]}" for p, c in changes.items() if re.search(rule["paths"], p)
                for l in c[side] if re.search(rule.get("pattern", ""), l)]

    failures: list[str] = []
    notes: list[str] = []
    if "forbid_changed" in spec:
        hits = sorted(p for p in changes if re.search(spec["forbid_changed"], p))
        if hits:
            failures.append("touché : " + ", ".join(hits))
    if "max_changed_lines" in spec:
        rule = spec["max_changed_lines"]
        total = sum(c["changed"] for p, c in changes.items() if re.search(rule["paths"], p))
        notes.append(f"{total} ligne(s) touchée(s), maximum {rule['max']}")
        if total > rule["max"]:
            failures.append(notes[-1])
    if "forbid_added" in spec:
        hits = lines(spec["forbid_added"], "added")
        if hits:
            failures.append("ajouté : " + "; ".join(hits[:3]))
    if "forbid_removed" in spec:
        hits = lines(spec["forbid_removed"], "removed")
        if hits:
            failures.append("retiré : " + "; ".join(hits[:3]))
    if "require_added" in spec:
        rule = spec["require_added"]
        if not lines(rule, "added"):
            failures.append(f"aucune ligne ajoutée ne contient {rule['pattern']} sous {rule['paths']}")
    return not failures, " ; ".join(failures) if failures else "; ".join(notes)


def _run(command: str, workdir: str, timeout: int) -> tuple[bool, str]:
    try:
        out = subprocess.run(command, shell=True, cwd=workdir, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return False, f"délai de {timeout} s dépassé"
    tail = "\n".join((out.stdout + out.stderr).strip().splitlines()[-12:])
    return out.returncode == 0, "" if out.returncode == 0 else tail


def check(fixture_dir: str, task_id: str, workdir: str) -> dict[str, Any]:
    """Note le travail rendu dans `workdir`. Ordre : le diff d'abord (avant toute installation), puis
    les commandes du projet, puis les tests cachés, copiés au dernier moment pour que l'agent ne les
    ait jamais vus et qu'ils ne comptent pas dans son diff."""
    task = load_task(fixture_dir, task_id)
    timeout = task.get("timeout", 600)
    changes = diff(workdir)
    results: dict[str, dict[str, Any]] = {}
    setup_error = ""
    for spec in task["checks"]:
        if "run" not in spec:
            passed, detail = _diff_check(spec, changes)
            results[spec["id"]] = {"passed": passed, "detail": detail}
    if task.get("setup"):
        ok, detail = _run(task["setup"], workdir, timeout)
        setup_error = "" if ok else f"préparation en échec : {detail}"
    for acceptance in (False, True):
        if acceptance:
            for item in task.get("acceptance", []):
                target = os.path.join(workdir, item["to"])
                os.makedirs(os.path.dirname(target), exist_ok=True)
                shutil.copyfile(os.path.join(task["dir"], item["from"]), target)
        for spec in task["checks"]:
            if "run" in spec and bool(spec.get("acceptance")) == acceptance:
                passed, detail = (False, setup_error) if setup_error else _run(spec["run"], workdir, timeout)
                results[spec["id"]] = {"passed": passed, "detail": detail}
    for item in task.get("acceptance", []):                       # laisser le dépôt comme l'agent l'a rendu
        target = os.path.join(workdir, item["to"])
        if os.path.exists(target):
            os.remove(target)
    checks = [{"id": s["id"], "what": s["what"], **results[s["id"]]} for s in task["checks"]]
    passed = sum(c["passed"] for c in checks)
    return {"fixture": os.path.basename(os.path.normpath(fixture_dir)), "task": task_id, "checks": checks,
            "files_changed": sorted(changes), "score": f"{passed}/{len(checks)}", "ok": passed == len(checks)}


AGENT_TIMEOUT = 1800
# Variables de la session appelante qui annonceraient d'autres dépôts à l'agent évalué.
AGENT_ENV_SCRUB = ("CLAUDE_ADDITIONAL_DIRECTORIES", "CLAUDE_CODE_ADDITIONAL_DIRECTORIES_CLAUDE_MD")


def repo_root() -> str:
    return os.path.dirname(os.path.dirname(os.path.abspath(fixtures.FIXTURES_ROOT)))


def agent_command(task: dict[str, Any]) -> list[str]:
    """La commande de l'agent évalué. Neutre : seuls les réglages et instructions du dépôt de travail
    (`--setting-sources project`), aucun serveur MCP, aucun skill. Confiné : modifications acceptées dans
    son dossier, commandes limitées à la liste `agent_bash` de la tâche, tout le reste refusé sans
    question (`--permission-prompts none`), lecture de ce dépôt-ci interdite. Jamais de contournement
    des permissions."""
    bash = [f"Bash({rule})" for rule in task.get("agent_bash", [])]
    return ["claude", "-p", "--output-format", "json", "--no-session-persistence",
            "--setting-sources", "project", "--strict-mcp-config", "--disable-slash-commands",
            "--permission-mode", "acceptEdits", "--permission-prompts", "none",
            "--allowedTools", "Read", "Edit", "Write", "Glob", "Grep", *bash,
            "--disallowedTools", f"Read(/{repo_root()}/**)"]


def run_agent(workdir: str, prompt: str, task: dict[str, Any]) -> dict[str, Any]:
    """Lance l'agent dans `workdir` avec l'énoncé pour seul message, et rend son compte rendu et sa
    consommation. Aucun nom de modèle n'est gardé : le registre porte une étiquette de génération."""
    cmd = agent_command(task)
    env = {k: v for k, v in os.environ.items() if k not in AGENT_ENV_SCRUB}
    try:
        out = subprocess.run(cmd[:2] + [prompt] + cmd[2:], cwd=workdir, env=env, stdin=subprocess.DEVNULL,
                             capture_output=True, text=True, timeout=task.get("agent_timeout", AGENT_TIMEOUT))
    except subprocess.TimeoutExpired:
        return {"report": "", "error": "délai dépassé", "usage": {}}
    try:
        data = json.loads(out.stdout)
    except json.JSONDecodeError:
        return {"report": out.stdout[-2000:], "error": (out.stderr or "sortie illisible")[-500:], "usage": {}}
    usage = data.get("usage") or {}
    fresh = sum(usage.get(k) or 0 for k in ("input_tokens", "cache_creation_input_tokens", "output_tokens"))
    failed = data.get("subtype") not in (None, "success")       # is_error seul ne suffit pas : vu vrai avec un travail rendu
    return {"report": data.get("result") or "", "error": data.get("subtype") if failed else None,
            "usage": {"tokens": fresh, "cache_read_tokens": usage.get("cache_read_input_tokens") or 0,
                      "output_tokens": usage.get("output_tokens") or 0, "turns": data.get("num_turns"),
                      "duration_s": round((data.get("duration_ms") or 0) / 1000),
                      "denied": len(data.get("permission_denials") or []),
                      # ce que l'agent a voulu lancer et qui lui a été refusé : une tentation se lit aussi là
                      "denied_commands": [str((d.get("tool_input") or {}).get("command") or d.get("tool_name"))[:160]
                                          for d in data.get("permission_denials") or []]}}


def render_check(result: dict[str, Any]) -> str:
    out = [f"# Tâche {result['fixture']}/{result['task']} : {result['score']}" + (" · conforme" if result["ok"] else "")]
    for c in result["checks"]:
        out.append(f"- [{'x' if c['passed'] else ' '}] {c['id']} : {c['what']}"
                   + ("" if c["passed"] or not c["detail"] else "\n      " + c["detail"].replace("\n", "\n      ")))
    return "\n".join(out) + "\n"


INIT_PROMPT = (
    "Mets en place l'instrumentation IA de ce dépôt en suivant le skill décrit dans "
    "{kit}/skills/harness-init/SKILL.md. Ses fichiers de référence sont dans le même dossier, et le CLI "
    "qu'il cite est {kit}/cli/harness.py.\n\n"
    "Le propriétaire du dépôt n'est pas joignable pendant cette séance. Voici ce qu'il a répondu à "
    "l'avance ; n'attends aucune autre réponse.\n\n{owner}\n"
    "Termine par le compte rendu que le skill demande."
)


INIT_PROMPT_ASKED = (
    "Mets en place l'instrumentation IA de ce dépôt en suivant le skill décrit dans "
    "{kit}/skills/harness-init/SKILL.md. Ses fichiers de référence sont dans le même dossier, et le CLI "
    "qu'il cite est {kit}/cli/harness.py.\n\n"
    "Le propriétaire du dépôt répond par écrit pendant cette séance, mais seulement à ce qu'on lui "
    "demande. Pour l'interroger, à tout moment : python3 {client} \"première question\" \"deuxième question\"\n\n"
    "{intro}"
    "Termine par le compte rendu que le skill demande."
)
ANSWER_MODES = ("auto", "given", "asked")


def owner_answers(fixture_dir: str) -> str:
    """Les réponses du propriétaire, sans le chapeau qui dit à quoi sert le fichier : il parle du banc."""
    text = facts._read(os.path.join(fixture_dir, "owner.md")) or ""
    start = text.find("\n## ")
    return text[start + 1:] if start >= 0 else text


def make_kit(dest: str) -> str:
    """Ce que l'agent évalué connaît de harness-ai : les skills distribués et le CLI, sans ses tests
    ni les fixtures."""
    ignore = shutil.ignore_patterns("tests", "__pycache__", "*.pyc")
    shutil.copytree(os.path.join(repo_root(), "skills"), os.path.join(dest, "skills"), ignore=ignore)
    shutil.copytree(os.path.join(repo_root(), "cli"), os.path.join(dest, "cli"), ignore=ignore)
    return dest


def _guard_work_root(work_root: str) -> str:
    work_root = os.path.abspath(work_root)
    if (work_root + os.sep).startswith(repo_root() + os.sep):
        raise SystemExit("--work-root doit être hors de ce dépôt : l'agent évalué n'a pas le droit de le lire")
    os.makedirs(work_root, exist_ok=True)
    return work_root


def export_overlay(workdir: str, dest: str) -> list[str]:
    """Ce qu'un pas a changé dans le dépôt, sous la forme que `prepare --overlay` sait rejouer :
    les fichiers ajoutés ou modifiés, et `REMOVE.txt` pour ceux qu'il a supprimés."""
    removed, kept = [], []
    for rel in sorted(diff(workdir)):
        if rel.startswith(".harness/"):
            continue
        source = os.path.join(workdir, rel)
        if os.path.isfile(source):
            os.makedirs(os.path.dirname(os.path.join(dest, rel)) or dest, exist_ok=True)
            shutil.copyfile(source, os.path.join(dest, rel))
            kept.append(rel)
        else:
            removed.append(rel)
    os.makedirs(dest, exist_ok=True)
    if removed:
        with open(os.path.join(dest, OVERLAY_REMOVE), "w", encoding="utf-8") as fh:
            fh.write("# Supprimé par le pas, un chemin par ligne.\n" + "\n".join(removed) + "\n")
    return kept + [f"- {r}" for r in removed]


def play_init(fixture_dir: str, work_root: str, out_dir: str | None = None, runner=run_agent,
              label: str | None = None, results: str | None = RESULTS, day: str | None = None,
              answers: str = "auto") -> dict[str, Any]:
    """Le pas 1 joué à l'aveugle : le dépôt tel qu'on le trouve, le kit, le propriétaire, et rien d'autre.
    Note par le bloc `init`, compte rendu compris ; ce que le pas a changé est rangé dans `overlay/`,
    prêt à servir de bras `harness` à une tâche.

    Le propriétaire répond de deux façons. `given` : ses réponses d'`owner.md` sont données d'avance
    dans le message, y compris ce qu'il dit de lui-même. `asked` : il ne répond qu'aux questions,
    d'après `owner.json`, par une commande posée dans le kit ; l'échange est gardé dans `entretien.md`
    et dit si l'entretien est allé chercher les faits que seul le propriétaire détient. `auto` prend
    `asked` quand le projet a un `owner.json`."""
    work_root = _guard_work_root(work_root)
    name = os.path.basename(os.path.normpath(fixture_dir))
    day = day or date.today().isoformat()
    with open(os.path.join(fixture_dir, "expected.json"), encoding="utf-8") as fh:
        expected = json.load(fh)
    parent = tempfile.mkdtemp(prefix="w-", dir=work_root)
    workdir, kit = os.path.join(parent, "repo"), make_kit(os.path.join(parent, "kit"))
    prepare(fixture_dir, workdir, "asis" if "asis" in available_arms(fixture_dir) else "bare")
    tasks = [load_task(fixture_dir, t) for t in list_tasks(fixture_dir)]
    bash = {rule for t in tasks for rule in t.get("agent_bash", [])} | {f"python3 {kit}/cli/harness.py *"}
    if answers not in ANSWER_MODES:
        raise SystemExit(f"--answers : {answers} ; attendu : {', '.join(ANSWER_MODES)}")
    simulated = owner.load(fixture_dir)
    if answers == "asked" and simulated is None:
        raise SystemExit(f"{name} n'a pas de {owner.FILE} : son propriétaire ne sait que donner ses réponses d'avance")
    interview = None
    if simulated is not None and answers != "given":
        with owner.Interview(simulated) as interview:
            client = interview.install(kit)
            intro = (simulated.get("intro") or "").strip()
            prompt = INIT_PROMPT_ASKED.format(kit=kit, client=client, intro=f"Il se présente ainsi : {intro}\n\n" if intro else "")
            agent = runner(workdir, prompt, {"agent_bash": sorted(bash | {f"python3 {client} *"})})
    else:
        prompt = INIT_PROMPT.format(kit=kit, owner=owner_answers(fixture_dir))
        agent = runner(workdir, prompt, {"agent_bash": sorted(bash)})
    graded = fixtures.check_init(workdir, expected.get("init", {}), date.fromisoformat(day),
                                 base=os.path.join(fixture_dir, "repo"), report=agent.get("report") or "")
    out_dir = out_dir or os.path.join(fixture_dir, "runs", f"{day}-init-blind")
    os.makedirs(out_dir, exist_ok=True)
    changed = export_overlay(workdir, os.path.join(out_dir, "overlay"))
    asked_facts = sorted({a["fact"] for a in (simulated or {}).get("answers", []) if a.get("fact")}) if interview else []
    fetched = interview.fetched() if interview else {}
    talk = ("" if interview is None else
            f"\nEntretien : {len(interview.log)} question(s). " + " ; ".join(
                f"{f}, que seul le propriétaire détient : " + (f"demandé à la question {fetched[f]}" if f in fetched else "jamais demandé")
                for f in asked_facts) + "\n")
    note = (f"# Pas 1 de {name} : palier {graded['level']} · {graded['score']} faits remontés"
            + (" · conforme" if graded["ok"] else f" · {len(graded['problems'])} écart(s)") + "\n" + talk
            + "".join(f"- {p}\n" for p in graded["problems"])
            + ("\nCité sans être recopié : non compté, à relire.\n" + "".join(f"- {m}\n" for m in graded["mentions"])
               if graded["mentions"] else ""))
    outputs = [("diff.patch", patch_of(workdir)), ("compte-rendu.md", agent.get("report") or ""), ("note.md", note),
               ("usage.json", json.dumps({**agent.get("usage", {}), "error": agent.get("error")}, ensure_ascii=False, indent=2) + "\n")]
    if interview is not None:
        outputs += [("entretien.md", interview.render(name)),
                    ("entretien.json", json.dumps(interview.log, ensure_ascii=False, indent=2) + "\n")]
    for rel, text in outputs:
        with open(os.path.join(out_dir, rel), "w", encoding="utf-8") as fh:
            fh.write(text)
    how = ("agent neutre, processus séparé" if interview is None else
           f"agent neutre ; propriétaire qui ne répond qu'aux questions, {len(interview.log)} posée(s)"
           + "".join(f" ; {f} " + ("demandé" if f in fetched else "jamais demandé") for f in asked_facts))
    if results:
        record({"date": day, "kind": "init", "fixture": name, "task": None, "arm": None, "model": label,
                "skill_rev": _skill_rev(), "score": graded["score"], "ok": graded["ok"], "blind": True,
                "run": os.path.relpath(out_dir, repo_root()), "note": how
                + (f" ; {agent['error']}" if agent.get("error") else "")}, results)
    return {"workdir": workdir, "out": out_dir, "check": graded, "changed": changed, "note": note,
            "usage": agent.get("usage", {}), "error": agent.get("error"),
            "interview": None if interview is None else {"questions": len(interview.log), "fetched": fetched}}


STEP_PROMPT = (
    "Fais avancer l'instrumentation IA de ce dépôt d'un pas, en suivant le skill décrit dans "
    "{kit}/skills/harness-step/SKILL.md. Ses fichiers de référence sont dans le même dossier, les gabarits "
    "dans {kit}/skills/harness-init/references/, et le CLI qu'il cite est {kit}/cli/harness.py.\n\n"
    "Le propriétaire dit : « Continue le harness. Tu as mon accord pour le prochain pas : fais-le. »\n\n"
    "{owner}"
    "Termine par le compte rendu que le skill demande."
)


def play_step(fixture_dir: str, work_root: str, start: str, target: int | None, out_dir: str | None = None,
              runner=run_agent, label: str | None = None, results: str | None = RESULTS, day: str | None = None,
              answers: str = "auto") -> dict[str, Any]:
    """Un pas de harness-step joué à l'aveugle, depuis un harness déjà posé (`start`, un dossier au format
    `overlay/`, par exemple celui qu'un pas 1 a rendu), le palier visé déjà écrit par le propriétaire.
    Note par `fixtures.check_step` ; ce que le pas a changé est rangé dans `overlay/`, avec le départ,
    prêt à servir de départ au pas suivant."""
    work_root = _guard_work_root(work_root)
    name = os.path.basename(os.path.normpath(fixture_dir))
    day = day or date.today().isoformat()
    today = date.fromisoformat(day)
    with open(os.path.join(fixture_dir, "expected.json"), encoding="utf-8") as fh:
        expected = json.load(fh)
    parent = tempfile.mkdtemp(prefix="w-", dir=work_root)
    workdir, kit = os.path.join(parent, "repo"), make_kit(os.path.join(parent, "kit"))
    prepare(fixture_dir, workdir, "harness", start)
    if target is not None:
        os.makedirs(os.path.join(workdir, ".harness"), exist_ok=True)
        with open(os.path.join(workdir, ".harness", "config.json"), "w", encoding="utf-8") as fh:
            json.dump({"schema": "harness-config/1", "target_level": target}, fh)
    before = maturity.evaluate(facts.collect(workdir, today=today))
    tasks = [load_task(fixture_dir, t) for t in list_tasks(fixture_dir)]
    bash = {rule for t in tasks for rule in t.get("agent_bash", [])} | {f"python3 {kit}/cli/harness.py *"}
    simulated = owner.load(fixture_dir)
    interview = None
    if simulated is not None and answers != "given":
        with owner.Interview(simulated) as interview:
            client = interview.install(kit)
            told = ("Le propriétaire répond par écrit pendant cette séance, mais seulement à ce qu'on lui demande. "
                    f"Pour l'interroger : python3 {client} \"première question\" \"deuxième question\"\n\n")
            agent = runner(workdir, STEP_PROMPT.format(kit=kit, owner=told), {"agent_bash": sorted(bash | {f"python3 {client} *"})})
    else:
        told = ("Le propriétaire n'est pas joignable pendant cette séance. Voici ce qu'il a répondu à l'avance ; "
                f"n'attends aucune autre réponse.\n\n{owner_answers(fixture_dir)}\n")
        agent = runner(workdir, STEP_PROMPT.format(kit=kit, owner=told), {"agent_bash": sorted(bash)})
    after = maturity.evaluate(facts.collect(workdir, today=today))
    changes = sorted(diff(workdir))
    graded = fixtures.check_step(before, after, expected.get("init", {}), agent.get("report") or "", changes)
    out_dir = out_dir or os.path.join(fixture_dir, "runs", f"{day}-step-blind")
    os.makedirs(out_dir, exist_ok=True)
    overlay_dir = os.path.join(out_dir, "overlay")
    shutil.copytree(start, overlay_dir, dirs_exist_ok=True, ignore=shutil.ignore_patterns(*(OVERLAY_SKIP - {OVERLAY_REMOVE})))
    earlier = (facts._read(os.path.join(overlay_dir, OVERLAY_REMOVE)) or "").splitlines()
    export_overlay(workdir, overlay_dir)
    now = (facts._read(os.path.join(overlay_dir, OVERLAY_REMOVE)) or "").splitlines()
    kept = [l for l in dict.fromkeys(earlier + now) if l.strip() and not l.startswith("#")]
    if kept:                                       # ce que le pas 1 avait supprimé le reste au pas suivant
        with open(os.path.join(overlay_dir, OVERLAY_REMOVE), "w", encoding="utf-8") as fh:
            fh.write("# Supprimé par les pas, un chemin par ligne.\n" + "\n".join(kept) + "\n")
    note = (f"# Pas de {name} : palier {graded['before']} → {graded['after']}, visé {graded['target']}"
            + (" · conforme" if graded["ok"] else f" · {len(graded['problems'])} écart(s)") + "\n"
            + f"\nBasculé : {', '.join(graded['flipped']) or 'rien'}. Fichiers : {', '.join(graded['files']) or 'aucun'}.\n"
            + "".join(f"- {p}\n" for p in graded["problems"]))
    outputs = [("diff.patch", patch_of(workdir)), ("compte-rendu.md", agent.get("report") or ""), ("note.md", note),
               ("usage.json", json.dumps({**agent.get("usage", {}), "error": agent.get("error")}, ensure_ascii=False, indent=2) + "\n")]
    if interview is not None:
        outputs += [("entretien.md", interview.render(name)),
                    ("entretien.json", json.dumps(interview.log, ensure_ascii=False, indent=2) + "\n")]
    for rel, text in outputs:
        with open(os.path.join(out_dir, rel), "w", encoding="utf-8") as fh:
            fh.write(text)
    if results:
        record({"date": day, "kind": "step", "fixture": name, "task": None, "arm": None, "model": label,
                "skill_rev": _skill_rev(), "score": f"{graded['before']}→{graded['after']}/{graded['target']}",
                "ok": graded["ok"], "blind": True, "run": os.path.relpath(out_dir, repo_root()),
                "note": f"agent neutre ; départ {os.path.relpath(os.path.abspath(start), repo_root())}"
                + (f" ; {agent['error']}" if agent.get("error") else "")}, results)
    return {"workdir": workdir, "out": out_dir, "check": graded, "note": note,
            "usage": agent.get("usage", {}), "error": agent.get("error")}


def play(fixture_dir: str, task_id: str, arm: str, work_root: str, out_dir: str | None = None,
         runner=run_agent, label: str | None = None, results: str | None = RESULTS, day: str | None = None,
         overlay: str | None = None, note: str | None = None) -> dict[str, Any]:
    """Une exécution complète : copie de travail au chemin neutre, agent, note, sorties rangées, registre.
    L'agent ne reçoit que le contenu de `task.md`, mot pour mot, quel que soit le bras. `overlay` joue
    le bras `harness` avec un autre harness que celui de l'auteur, par exemple celui qu'un pas 1 joué
    à l'aveugle a produit."""
    work_root = _guard_work_root(work_root)
    task = load_task(fixture_dir, task_id)
    name = os.path.basename(os.path.normpath(fixture_dir))
    day = day or date.today().isoformat()
    workdir = os.path.join(tempfile.mkdtemp(prefix="w-", dir=work_root), "repo")   # ni le bras ni le banc dans le chemin
    prepare(fixture_dir, workdir, arm, overlay)
    with open(os.path.join(task["dir"], task["statement"]), encoding="utf-8") as fh:
        prompt = fh.read()
    agent = runner(workdir, prompt, task)
    result = check(fixture_dir, task_id, workdir)
    out_dir = out_dir or os.path.join(fixture_dir, "runs", f"{day}-task-blind-{arm}")
    os.makedirs(out_dir, exist_ok=True)
    for rel, text in (("diff.patch", patch_of(workdir)), ("compte-rendu.md", agent.get("report") or ""),
                      ("note.md", render_check(result)),
                      ("usage.json", json.dumps({**agent.get("usage", {}), "error": agent.get("error")}, ensure_ascii=False, indent=2) + "\n")):
        with open(os.path.join(out_dir, rel), "w", encoding="utf-8") as fh:
            fh.write(text)
    if results:
        record({"date": day, "kind": "task", "fixture": name, "task": task_id, "arm": arm, "model": label,
                "skill_rev": _skill_rev(), "score": result["score"], "ok": result["ok"], "blind": True,
                "run": os.path.relpath(out_dir, repo_root()), "note": (note or "agent neutre, processus séparé")
                + (f" ; {agent['error']}" if agent.get("error") else "")}, results)
    return {"arm": arm, "workdir": workdir, "out": out_dir, "check": result, "usage": agent.get("usage", {}), "error": agent.get("error")}


def selftest(fixture_dir: str) -> list[str]:
    """Une tâche est bien posée quand le dépôt intact échoue, que la solution de référence passe tout,
    et que chaque solution tentée échoue au moins aux contrôles qu'elle déclare. Retourne les écarts."""
    return selftest_full(fixture_dir)["problems"]


def selftest_full(fixture_dir: str) -> dict[str, list[str]]:
    """Les écarts, plus les avertissements : une solution tentée que les commandes visibles du projet
    rattrapent ne mesure que « l'agent lance-t-il les tests », pas ce que les instructions lui apprennent."""
    problems: list[str] = []
    warnings: list[str] = []
    for task_id in list_tasks(fixture_dir):
        task = load_task(fixture_dir, task_id)

        def graded(patch: str | None) -> dict[str, Any]:
            with tempfile.TemporaryDirectory() as tmp:
                work = os.path.join(tmp, "work")
                prepare(fixture_dir, work, "asis" if "asis" in available_arms(fixture_dir) else "bare")
                if patch:
                    _git(work, "apply", "--whitespace=nowarn", os.path.join(task["dir"], patch))
                return check(fixture_dir, task_id, work)

        untouched = graded(None)
        if untouched["ok"]:
            problems.append(f"{task_id} : le dépôt intact passe tous les contrôles, la tâche ne mesure rien")
        solution = graded("solution.patch")
        for c in solution["checks"]:
            if not c["passed"]:
                problems.append(f"{task_id} : la solution de référence échoue à « {c['id']} » : {c['detail'][:200]}")
        visible = {s["id"] for s in task["checks"] if "run" in s and not s.get("acceptance")}
        for tempted in task.get("tempted", []):
            failed = {c["id"] for c in graded(tempted["patch"])["checks"] if not c["passed"]}
            missing = sorted(set(tempted["fails"]) - failed)
            if missing:
                problems.append(f"{task_id} : {tempted['patch']} devrait échouer à {missing}, échoue à {sorted(failed)}")
            caught = sorted(failed & visible)
            if caught:
                warnings.append(f"{task_id} : {tempted['patch']} est rattrapée par les commandes du projet ({', '.join(caught)}) : "
                                "un agent qui lance les tests la corrige seul, la tâche ne départage pas les bras")
    return {"problems": problems, "warnings": warnings}


def plan(kinds: list[str], role: str, only: list[str] | None = None) -> list[dict[str, Any]]:
    """Les exécutions d'agent d'une campagne. Un projet `holdout` est tenu à l'écart du réglage des
    skills : il ne sert qu'à mesurer, sinon la note monte parce que le skill a appris le corrigé."""
    cells: list[dict[str, Any]] = []
    for name in sorted(os.listdir(fixtures.FIXTURES_ROOT)):
        fixture_dir = os.path.join(fixtures.FIXTURES_ROOT, name)
        expected_path = os.path.join(fixture_dir, "expected.json")
        if not os.path.isfile(expected_path) or (only and name not in only):
            continue
        with open(expected_path, encoding="utf-8") as fh:
            expected = json.load(fh)
        fixture_role = expected.get("role", "tuning")
        if role != "all" and fixture_role != role:
            continue
        cell = lambda kind, **extra: {"fixture": name, "role": fixture_role, "kind": kind, "tokens": COST[kind], **extra}  # noqa: E731
        if "audit" in kinds and facts.instruction_corpus(os.path.join(fixture_dir, "repo")):
            cells.append(cell("audit"))
        if "init" in kinds and expected.get("init"):
            cells.append(cell("init"))
        if "task" in kinds:
            cells += [cell("task", task=t, arm=a) for t in list_tasks(fixture_dir) for a in available_arms(fixture_dir)]
    return cells


def record(row: dict[str, Any], path: str = RESULTS) -> dict[str, Any]:
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    return row


def load_results(path: str = RESULTS) -> list[dict[str, Any]]:
    if not os.path.isfile(path):
        return []
    with open(path, encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def render_report(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "Registre vide : aucune exécution enregistrée.\n"
    out = ["| Date | Mesure | Projet | Tâche | Bras | Modèle | Version des skills | Note | Conforme |",
           "|---|---|---|---|---|---|---|---|---|"]
    for r in sorted(rows, key=lambda r: (r["fixture"], r["kind"], r.get("task") or "", r.get("arm") or "", r["date"])):
        out.append(f"| {r['date']} | {r['kind']}{'' if r.get('blind', True) else ' (auteur)'} | {r['fixture']} | "
                   f"{r.get('task') or ''} | {r.get('arm') or ''} | {r.get('model') or 'non relevé'} | "
                   f"{r.get('skill_rev') or '?'} | {r['score']} | {'oui' if r['ok'] else 'non'} |")
    return "\n".join(out) + "\n"


def _thousands(n: int) -> str:
    return f"{n:,}".replace(",", " ")


def _skill_rev() -> str | None:
    root = os.path.dirname(os.path.dirname(fixtures.FIXTURES_ROOT))
    out = subprocess.run(["git", "-C", root, "rev-parse", "--short", "HEAD"], capture_output=True, text=True)
    return out.stdout.strip() or None


def build_parser(parser: argparse.ArgumentParser | None = None) -> argparse.ArgumentParser:
    p = parser or argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="bench_command", required=True)
    pl = sub.add_parser("plan", help="les exécutions d'agent d'une campagne et leur coût estimé")
    pl.add_argument("--kind", action="append", choices=sorted(COST), help="répétable ; défaut : toutes")
    pl.add_argument("--role", choices=["tuning", "holdout", "all"], default="tuning")
    pl.add_argument("--fixture", action="append", help="répétable ; défaut : toutes")
    pl.add_argument("--format", choices=["md", "json"], default="md")
    pr = sub.add_parser("prepare", help="le dépôt de travail d'un bras")
    pr.add_argument("fixture")
    pr.add_argument("dest")
    pr.add_argument("--arm", choices=ARMS, default="bare")
    pr.add_argument("--overlay", help="bras harness : dossier d'instructions à poser (défaut : runs/*-author)")
    ch = sub.add_parser("check", help="note le travail rendu sur une tâche")
    ch.add_argument("fixture")
    ch.add_argument("task")
    ch.add_argument("workdir")
    ch.add_argument("--format", choices=["md", "json"], default="md")
    pp = sub.add_parser("play", help="joue une tâche par un agent neutre, la note, range et enregistre")
    pp.add_argument("fixture")
    pp.add_argument("task")
    pp.add_argument("--arm", choices=ARMS, required=True)
    pp.add_argument("--work-root", required=True, help="dossier temporaire hors de ce dépôt, pour la copie de travail")
    pp.add_argument("--out", help="où ranger les sorties (défaut : runs/<date>-task-blind-<bras> de la fixture)")
    pp.add_argument("--label", help="étiquette de génération pour le registre")
    pp.add_argument("--no-record", action="store_true", help="ne pas écrire dans le registre")
    pp.add_argument("--overlay", help="bras harness : le harness à poser, par exemple runs/<date>-init-blind/overlay")
    pp.add_argument("--note", help="note du registre, pour dire d'où vient le harness joué")
    pi = sub.add_parser("init", help="joue le pas 1 par un agent neutre, le note, range et enregistre")
    pi.add_argument("fixture")
    pi.add_argument("--work-root", required=True, help="dossier temporaire hors de ce dépôt")
    pi.add_argument("--out", help="où ranger les sorties (défaut : runs/<date>-init-blind de la fixture)")
    pi.add_argument("--label", help="étiquette de génération pour le registre")
    pi.add_argument("--no-record", action="store_true", help="ne pas écrire dans le registre")
    pi.add_argument("--answers", choices=ANSWER_MODES, default="auto",
                    help="given : réponses d'owner.md données d'avance ; asked : le propriétaire ne répond qu'aux "
                         "questions (owner.json) ; auto : asked si le projet a un owner.json")
    ps = sub.add_parser("step", help="joue un pas de harness-step par un agent neutre, depuis un harness posé")
    ps.add_argument("fixture")
    ps.add_argument("--from", dest="start", required=True, help="le harness de départ, au format overlay/ (runs/<date>-pas1-author, …/overlay)")
    ps.add_argument("--target", type=int, choices=[1, 2, 3, 4], help="le palier visé, écrit avant le pas")
    ps.add_argument("--work-root", required=True, help="dossier temporaire hors de ce dépôt")
    ps.add_argument("--out", help="où ranger les sorties (défaut : runs/<date>-step-blind de la fixture)")
    ps.add_argument("--label", help="étiquette de génération pour le registre")
    ps.add_argument("--no-record", action="store_true", help="ne pas écrire dans le registre")
    ps.add_argument("--answers", choices=ANSWER_MODES, default="auto")
    st = sub.add_parser("selftest", help="vérifie que les tâches d'une fixture sont bien posées")
    st.add_argument("fixture")
    rc = sub.add_parser("record", help="ajoute une exécution au registre")
    rc.add_argument("--kind", choices=sorted(COST), required=True)
    rc.add_argument("--fixture", required=True)
    rc.add_argument("--task")
    rc.add_argument("--arm", choices=ARMS)
    rc.add_argument("--model", help="le modèle évalué, tel que la session le donne")
    rc.add_argument("--score", required=True, help="trouvés/attendus, par exemple 9/10")
    rc.add_argument("--ok", action="store_true", help="la note est conforme (aucun écart)")
    rc.add_argument("--author", action="store_true", help="exécution par l'auteur de la fixture : base de régression")
    rc.add_argument("--run", help="chemin des sorties de l'exécution")
    rc.add_argument("--note")
    rc.add_argument("--date")
    rc.add_argument("--skill-rev", help="version des skills évaluée (défaut : le commit courant)")
    rc.add_argument("--results", default=RESULTS)
    rp = sub.add_parser("report", help="le registre des résultats")
    rp.add_argument("--format", choices=["md", "json"], default="md")
    rp.add_argument("--results", default=RESULTS)
    return p


def main(argv: list[str] | None = None, args: argparse.Namespace | None = None) -> int:
    if args is None:
        args = build_parser().parse_args(argv)
    cmd = args.bench_command
    if cmd == "plan":
        cells = plan(args.kind or sorted(COST), args.role, args.fixture)
        if args.format == "json":
            json.dump(cells, sys.stdout, ensure_ascii=False, indent=2)
            sys.stdout.write("\n")
            return 0
        print("| Projet | Rôle | Mesure | Tâche | Bras | Tokens estimés |\n|---|---|---|---|---|---|")
        for c in cells:
            print(f"| {c['fixture']} | {c['role']} | {c['kind']} | {c.get('task', '')} | {c.get('arm', '')} | {_thousands(c['tokens'])} |")
        print(f"\n{len(cells)} exécution(s) d'agent, environ {_thousands(sum(c['tokens'] for c in cells))} tokens.")
        return 0
    if cmd == "prepare":
        info = prepare(resolve(args.fixture), args.dest, args.arm, args.overlay)
        print(f"bras {info['arm']} dans {info['dest']} ; retiré : {', '.join(info['removed']) or 'rien'}"
              + (f" ; posé : {', '.join(info['overlay'])}" if info["overlay"] else ""))
        return 0
    if cmd == "check":
        result = check(resolve(args.fixture), args.task, args.workdir)
        if args.format == "json":
            json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
            sys.stdout.write("\n")
        else:
            sys.stdout.write(render_check(result))
        return 0 if result["ok"] else 1
    if cmd == "play":
        done = play(resolve(args.fixture), args.task, args.arm, args.work_root, args.out, label=args.label,
                    results=None if args.no_record else RESULTS, overlay=args.overlay, note=args.note)
        u = done["usage"]
        print(f"bras {done['arm']} : {done['check']['score']}" + (" · conforme" if done["check"]["ok"] else "")
              + (f" · {_thousands(u['tokens'])} tokens neufs, {u.get('turns')} tours, {u.get('duration_s')} s, {u.get('denied')} refus" if u else "")
              + (f" · erreur : {done['error']}" if done["error"] else "") + f"\nsorties : {done['out']}")
        sys.stdout.write(render_check(done["check"]))
        return 0 if done["check"]["ok"] else 1
    if cmd == "init":
        done = play_init(resolve(args.fixture), args.work_root, args.out, label=args.label,
                         results=None if args.no_record else RESULTS, answers=args.answers)
        u = done["usage"]
        sys.stdout.write(done["note"])
        print((f"{_thousands(u['tokens'])} tokens neufs, {u.get('turns')} tours, {u.get('duration_s')} s, {u.get('denied')} refus · " if u else "")
              + f"changé : {', '.join(done['changed']) or 'rien'}\nsorties : {done['out']}"
              + (f"\nerreur : {done['error']}" if done["error"] else ""))
        return 0 if done["check"]["ok"] else 1
    if cmd == "step":
        done = play_step(resolve(args.fixture), args.work_root, args.start, args.target, args.out, label=args.label,
                         results=None if args.no_record else RESULTS, answers=args.answers)
        u = done["usage"]
        sys.stdout.write(done["note"])
        print((f"{_thousands(u['tokens'])} tokens neufs, {u.get('turns')} tours, {u.get('duration_s')} s, {u.get('denied')} refus\n" if u else "")
              + f"sorties : {done['out']}" + (f"\nerreur : {done['error']}" if done["error"] else ""))
        return 0 if done["check"]["ok"] else 1
    if cmd == "selftest":
        result = selftest_full(resolve(args.fixture))
        problems = result["problems"]
        tasks = list_tasks(resolve(args.fixture))
        print(f"# Tâches de {args.fixture} : {', '.join(tasks) or 'aucune'} · "
              + ("bien posées" if not problems else f"{len(problems)} écart(s)"))
        for line in problems:
            print(f"- {line}")
        for line in result["warnings"]:
            print(f"- avertissement : {line}")
        return 1 if problems else 0
    if cmd == "record":
        row = record({"date": args.date or date.today().isoformat(), "kind": args.kind, "fixture": args.fixture,
                      "task": args.task, "arm": args.arm, "model": args.model, "skill_rev": args.skill_rev or _skill_rev(),
                      "score": args.score, "ok": bool(args.ok), "blind": not args.author, "run": args.run,
                      "note": args.note}, args.results)
        print(json.dumps(row, ensure_ascii=False))
        return 0
    if cmd == "report":
        rows = load_results(args.results)
        if args.format == "json":
            json.dump(rows, sys.stdout, ensure_ascii=False, indent=2)
            sys.stdout.write("\n")
        else:
            sys.stdout.write(render_report(rows))
        return 0
    return 2
