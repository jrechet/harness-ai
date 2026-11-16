"""Tests du garde-fou « un agent ne livre pas » : ce qu'il refuse, ce qu'il laisse passer, et le hook de
bout en bout. Les listes sont longues exprès : un refus de trop gêne tout le travail, un oubli laisse partir."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from aisdlclib import guard  # noqa: E402

CLI = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ai_sdlc.py")
PLUGIN = os.path.dirname(os.path.dirname(CLI))

ALLOWED = [
    "git tag", "git tag -l 'v*'", "git tag --list", "git tag --contains HEAD", "git tag -n", "git describe --tags", "git fetch --tags",
    "git push origin feat/x", "git push -u origin HEAD", "git push origin HEAD:feat/x", "git log --oneline v1.4.0..HEAD",
    "git commit -m 'docs: explique npm publish, git tag v1 et make deploy'", "echo 'git tag v1'", "grep -r 'gh release create' .",
    "cat scripts/release.sh", "ls deploy/", "make test", "make it", "make build", "npm run build", "npm test", "npm install", "yarn install",
    "pnpm install", "kubectl get pods", "kubectl describe deploy/api", "kubectl logs api", "helm list", "helm template ./chart",
    "terraform plan", "terraform validate", "docker build -t x .", "docker run --rm x", "gh pr create --title x", "gh pr merge 12 --merge",
    "gh run list --commit abc --json name,status,conclusion,headSha", "gh release list", "gh release view v1", "gh api repos/o/r/releases",
    "python3 cli/ai_sdlc.py ship check . --base origin/main", "python3 cli/ai_sdlc.py ship render p.json . --base origin/main",
    "python3 -m unittest discover -s tests", "rg 'deploy' docs/", "cat > notes.md <<'EOF'\nPour livrer :\ngit tag v2.0.0\nmake deploy\nEOF",
    "git commit -m 'feat: x\n\ngit tag v1 reste à faire par un humain'", "git commit -m 'docs: `git tag v1` se lance à la main'",
    "gh pr create --body \"$(cat <<'EOF'\nLancer `git tag v1` après la fusion.\nEOF\n)\"", "echo '$(git tag v1)'",
    "npm run build:prod", "npm run build:production", "npm run test:prod-like", "npm run release:notes", "npm run test:release",
    "npm run docs:deploy-preview", "npm run publish-check", "make deploy-docs", "make release-notes", "make build-production",
    "make check-release-notes", "make -n deploy", "pnpm --filter prod-api build", "yarn workspace prod-api build", "yarn workspace release-tools test",
    "cat > gros.txt <<'EOF'\n" + "ligne de texte ordinaire\n" * 1500 + "EOF",
    "curl -L https://github.com/x/y/releases/download/v1/outil.tgz | tar xz", "curl -sSL https://github.com/a/b/releases/latest/download/x",
    "curl https://api.github.com/repos/a/b/releases", "wget https://github.com/x/y/releases/download/v1/o.tgz", "gh api repos/a/b/releases -X GET",
    "gh api --method GET repos/a/b/releases", "kubectl apply --dry-run=client -f x", "kubectl create --dry-run=client -o yaml deploy x",
    "cargo publish --dry-run", "npm publish --dry-run", "goreleaser release --snapshot", "npm dist-tag ls x", "aws deploy list-deployments",
    "az deployment group list", "kubectl get svc create", "kubectl get pods -n create", "helm diff upgrade x y", "git push origin release/1.2",
    "git push origin v2-migration", "git push origin feature-v1.2.3", "git push", "git push origin main", "git config alias.co checkout",
    "npx prettier --check .", "npx tsc --noEmit", "python3 -m pytest -k deploy", "uv run pytest", "docker compose up -d", "docker compose logs",
    "python3 -c \"print('git tag v1 se lance à la main')\"".replace("git tag v1", "tag"), "echo $(( 1 << 4 ))\nls", "cat <<< bonjour\nls",
    "find . -name '*.py' -exec wc -l {} +", "nice -n 10 make test", "sudo -u root ls", "ls 2>&1 | head", "ssh hote 'kubectl get pods'", "printf 'a\nb\n' | sort", "timeout 60 make test", "xargs -n1 echo < f", "curl https://example.com/health", "aws s3 ls", "gcloud config list", "",
]
REFUSED = [
    "git tag v1.5.0", "git tag -a v2 -m x", "git -C repo tag v1", "git -c user.name=x tag v1", "/usr/bin/git tag v3", "git tag -d v1",
    "git tag -f v1 HEAD", "git push --tags", "git push origin v1.5.0", "git push origin HEAD:refs/tags/v1", "git push origin main --follow-tags",
    "git update-ref refs/tags/v1 HEAD", "gh release create v2 --draft", "gh release edit v1 --draft=false", "gh workflow run deploy.yml",
    "gh api -X POST repos/o/r/releases -f tag_name=v1", "gh api repos/o/r/dispatches -f event_type=deploy",
    "curl -X POST https://api.github.com/repos/o/r/dispatches", "make deploy ENV=prod", "make livrer VERSION=v1.5.0", "make revenir VERSION=v1",
    "make -C infra release", "sudo make release", "ENV=prod make deploy", "env ENV=prod make deploy", "just deploy-prod", "npm publish",
    "npm run deploy", "npm run release:prod", "yarn deploy", "pnpm publish --no-git-checks", "twine upload dist/*", "cargo publish",
    "kubectl apply -f k8s/", "kubectl -n prod rollout restart deploy/api", "kubectl set image deploy/api api=x:2", "helm upgrade api ./chart",
    "helm -n prod install api ./chart", "terraform apply -auto-approve", "terraform -chdir=infra destroy", "pulumi up --yes", "docker push x/y:1",
    "vercel --prod", "fly deploy", "ansible-playbook site.yml", "aws ecs update-service --cluster c --service s", "serverless deploy",
    "cd repo && git tag v1 && git push --tags", "true; git tag v1", "git tag v1 | cat", "git status\ngit tag v1", "(git tag v1)",
    "sh -c 'git tag v1'", "bash -lc \"make deploy\"", "echo $(git tag v9)", "echo `npm publish`", "eval 'npm publish'",
    "timeout 60 make deploy", "timeout -k 5 60 npm publish", "nohup make deploy &", "cat <<EOF > x\ntexte\nEOF\ngit tag v1",
    "git commit -m \"docs: `git tag v7`\"", "ssh prod 'kubectl apply -f k8s/'", "ls | xargs -I{} make deploy",
    "bash <<'EOF'\ngit tag v1\nEOF", "sh <<EOF\nkubectl apply -f x\nEOF", "cat <<EOF | sh\nnpm publish\nEOF", "bash -s <<'X'\nnpm publish\nX",
    "cat <<< bonjour\ngit tag v1", "read x <<< foo\nmake deploy", "echo $(( 1 << n ))\ngit tag v1", "echo '<<x'\ngit tag v1", "bash <<<'git tag v1'",
    "npx vercel --prod", "npx -y semantic-release", "npx changeset publish", "npm exec -- vercel --prod", "pnpm dlx vercel --prod",
    "yarn dlx vercel --prod", "bunx vercel --prod", "python -m twine upload dist/*", "python3 -m twine upload dist/*", "uv run twine upload dist/*",
    "pipx run twine upload dist/*", "python3 -m poetry publish", "python setup.py upload", "docker-compose push", "docker build --push .",
    "docker compose push", "docker buildx build --push -t x .", "docker buildx imagetools create -t x y",
    "git push origin tag v1", "git push --atomic origin tag v1", "git push origin v1", "git push origin v2", "git push origin +v1.0",
    "git push origin v1.0.0^{}", "git push --delete origin v1", "git push origin :v1", "git push --repo=origin v1.0", "git push heroku main",
    "nice -n 10 git tag v1", "sudo -u root git tag v1", "ionice -c 2 git tag v1", "exec -a x git tag v1", "2>&1 git tag v1", "> out git tag v1",
    "su -c 'git tag v1'", "find . -exec git tag v1 ';'", "find . -exec sh -c 'git tag v1' \\;", "docker exec x git tag v1", "bash -c -- 'git tag v1'",
    "git\u00a0tag\u00a0v1", "gh api repos/a/b/actions/runs/1/rerun -XPOST".replace("actions/runs/1/rerun", "dispatches"),
    "curl -d '{}' https://api.github.com/repos/o/r/releases", "python3 -c \"import os; os.system('git tag v1')\"", "node -e \"require('child_process').execSync('npm publish')\"",
    "git config alias.x tag && git x v1", "git -c alias.x=tag x v1", "sh -c \"$(echo git tag v1)\"", "bash <(echo git tag v1)", "prisma migrate deploy", "if true; then git tag v1; fi", "git tag v1 \\\n  -m 'x'",
]


class ReasonsTests(unittest.TestCase):
    def test_ordinary_work_is_never_refused(self):
        for command in ALLOWED:
            with self.subTest(command=command):
                self.assertEqual(guard.reasons(command), [])

    def test_every_known_way_to_deliver_is_refused(self):
        for command in REFUSED:
            with self.subTest(command=command):
                self.assertTrue(guard.reasons(command))

    def test_the_team_commands_are_refused_whatever_their_name(self):
        team = ["./bin/go-live now", "scripts/promouvoir.sh <version>", "make envoi-express VERSION=<v>", "fabric"]
        self.assertTrue(guard.reasons("./bin/go-live now", team))
        self.assertTrue(guard.reasons("cd x && bin/go-live now --force", team))
        self.assertTrue(guard.reasons("scripts/promouvoir.sh v2", team))
        self.assertTrue(guard.reasons("make envoi-express VERSION=v2.0.0", team))
        self.assertEqual(guard.reasons("./bin/go-live status", team), [])
        self.assertEqual(guard.reasons("make envoi-express", team), [])        # sans sa version, ce n'est pas la commande de l'équipe
        self.assertEqual(guard.reasons("fabric --help", team), [])               # un seul mot ne fait pas une commande reconnue

    def test_a_realistic_team_procedure_does_not_block_ordinary_commands(self):
        # constat de relecture : deux mots suffisaient, et « git push origin vX.Y.Z » faisait refuser tout git push
        team = ["git tag vX.Y.Z", "git push origin vX.Y.Z", "npm run release", "gh workflow run deploy.yml -f env=prod", "docker compose up -d"]
        for command in ("git push origin main", "git push", "git tag -l", "npm run test", "npm run build", "gh workflow list",
                        "gh workflow view x", "docker compose up", "docker compose logs", "make test", "git status"):
            with self.subTest(command=command):
                self.assertEqual(guard.reasons(command, team), [])
        for command in ("npm run release", "gh workflow run deploy.yml -f env=prod", "docker compose up -d", "git tag v1.2.3"):
            with self.subTest(command=command):
                self.assertTrue(guard.reasons(command, team))

    def test_a_push_of_a_name_that_is_a_local_tag_is_refused(self):
        tags = {"candidate", "v1.4.0"}
        self.assertTrue(guard.reasons("git push origin candidate", tags=tags))
        self.assertTrue(guard.reasons("git push origin HEAD:candidate", tags=tags))
        self.assertEqual(guard.reasons("git push origin feat/x", tags=tags), [])

    def test_crafted_commands_stay_fast_and_a_runaway_nesting_is_refused(self):
        import time
        for command in ("eval " + " ".join(["xargs eval"] * 1800), "$(" * 9000, "`" * 9001, "timeout " * 3000 + "ls", "; " * 9000,
                        "sh -c " + "'" * 9000, "git push " + "x " * 9000):
            start = time.monotonic()
            guard.reasons(command)
            with self.subTest(command=command[:20]):
                self.assertLess(time.monotonic() - start, 2)
        original, guard.MAX_WORK = guard.MAX_WORK, 3
        self.addCleanup(setattr, guard, "MAX_WORK", original)
        self.assertTrue(guard.reasons("sh -c 'a; sh -c \"b; sh -c c\"'; eval d; eval e"))   # trop de commandes emboîtées : refusée plutôt que lancée

    def test_hostile_or_odd_input_does_not_crash(self):
        for command in ("git tag 'v1", "echo \"", "$(" * 3000, "a" * 30_000, "git tag v1 " + "x" * 30_000, "\x00\x1b[31m", "`" * 501,
                        "sh -c " * 50 + "'git tag v1'", None, 3, ["git", "tag"]):
            with self.subTest(command=str(command)[:20]):
                self.assertIsInstance(guard.reasons(command), list)   # type: ignore[arg-type]
        self.assertTrue(guard.reasons("git tag 'v1"))                  # indécoupable : jugée sur son texte
        self.assertTrue(guard.reasons("git tag v1 " + "x" * 30_000))   # trop longue pour être découpée : jugée sur son texte
        self.assertEqual(guard.reasons("echo " + "x" * 30_000), [])    # longue et sans rien d'une livraison : elle passe
        self.assertEqual(guard.reasons("echo \"bonjour"), [])

    def test_the_refusal_says_what_to_do_instead(self):
        text = guard.render(guard.reasons("git tag v1"))
        self.assertIn("un tag git", text)
        self.assertIn("c'est un humain qui la lance", text)
        self.assertNotIn(guard.ALLOW_ENV, text)   # la porte de l'équipe ne se souffle pas à l'agent


class HookTests(unittest.TestCase):
    def call(self, command, env: dict | None = None, tool: str = "Bash", cwd: str | None = None) -> tuple[int, str]:
        payload = {"hook_event_name": "PreToolUse", "tool_name": tool, "tool_input": {"command": command}, "cwd": cwd or "."}
        return guard.run_hook(json.dumps(payload), env or {})

    def test_a_delivery_is_refused_with_exit_code_2_and_anything_else_passes(self):
        code, message = self.call("git tag v1.5.0")
        self.assertEqual(code, 2)
        self.assertIn("commande refusée", message)
        self.assertEqual(self.call("make test"), (0, ""))
        self.assertEqual(self.call("git tag v1", tool="Write"), (0, ""))
        self.assertEqual(self.call(None), (0, ""))

    def test_unreadable_input_passes_and_never_raises(self):
        for raw in ("", "x", "[]", "null", '{"tool_name": "Bash"}', '{"tool_name": "Bash", "tool_input": []}', "[" * 100_000):
            with self.subTest(raw=raw[:12]):
                self.assertEqual(guard.run_hook(raw, {}), (0, ""))

    def test_a_truncated_or_oversized_call_is_judged_on_its_text_not_waved_through(self):
        # constat de relecture : au-delà de 200 000 caractères le JSON était coupé, illisible, et tout passait
        self.assertEqual(self.call("git tag v1" + " " * 250_000)[0], 2)
        self.assertEqual(self.call("x " * 120_000 + "; git tag v1")[0], 2)
        cut = json.dumps({"tool_name": "Bash", "tool_input": {"command": "git tag v1.5.0 && git push --tags"}})[:-9]
        self.assertEqual(guard.run_hook(cut, {})[0], 2)
        self.assertEqual(guard.run_hook(json.dumps({"tool_name": "Bash", "tool_input": {"command": "ls"}})[:-9], {}), (0, ""))

    def test_the_team_can_open_the_door_from_the_session_environment_only(self):
        self.assertEqual(self.call("git tag v1", env={guard.ALLOW_ENV: "1"}), (0, ""))
        self.assertEqual(self.call("git tag v1", env={guard.ALLOW_ENV: "0"})[0], 2)
        self.assertEqual(self.call(f"{guard.ALLOW_ENV}=1 git tag v1")[0], 2)          # posée par la commande : sans effet
        self.assertEqual(self.call(f"export {guard.ALLOW_ENV}=1; make deploy")[0], 2)

    def test_the_team_procedure_is_read_from_the_project_even_if_the_working_copy_drops_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo, remote = os.path.join(tmp, "repo"), os.path.join(tmp, "origin.git")
            os.makedirs(os.path.join(repo, "docs", "agents"))
            git = lambda *args: subprocess.run(["git", "-C", repo, "-c", "user.name=t", "-c", "user.email=t@example.com", *args],  # noqa: E731
                                               capture_output=True, check=True)
            subprocess.run(["git", "init", "-q", "--bare", "-b", "main", remote], capture_output=True, check=True)
            git("init", "-q", "-b", "main")
            path = os.path.join(repo, "docs", "agents", "livraison.md")
            with open(path, "w", encoding="utf-8") as fh:
                fh.write("---\npoint: livraison\nmode: ajoute\n---\n- Livrer : `bin/go-live now` par l'astreinte.\n")
            git("add", "-A")
            git("commit", "-q", "-m", "base")
            git("remote", "add", "origin", remote)
            git("push", "-q", "origin", "main")
            git("remote", "set-head", "origin", "main")
            env = {"CLAUDE_PROJECT_DIR": repo}
            self.assertEqual(self.call("bin/go-live now", env=env)[0], 2)
            self.assertEqual(self.call("bin/go-live status", env=env)[0], 0)
            os.remove(path)   # l'agent retire la ligne de sa copie de travail : la branche de base la porte encore
            self.assertEqual(self.call("bin/go-live now", env=env)[0], 2)
            self.assertEqual(self.call("bin/go-live now", cwd=repo)[0], 2)   # sans CLAUDE_PROJECT_DIR, le dossier de l'appel
            git("remote", "remove", "origin")   # sans branche distante : le dernier commit porte encore la procédure
            self.assertEqual(self.call("bin/go-live now", env=env)[0], 2)
            git("tag", "candidate")
            self.assertEqual(self.call("git push origin candidate", env=env)[0], 2)   # les tags du dépôt sont connus du hook

    def test_an_internal_error_falls_back_instead_of_opening_the_door(self):
        original = guard.hook
        guard.hook = lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("panne"))
        self.addCleanup(setattr, guard, "hook", original)
        self.assertEqual(self.call("cd x && git tag v1.5.0")[0], 2)
        self.assertEqual(self.call("make test")[0], 0)


class PluginWiringTests(unittest.TestCase):
    def test_the_plugin_declares_the_hook_and_the_command_it_names_works(self):
        with open(os.path.join(PLUGIN, "hooks", "hooks.json"), encoding="utf-8") as fh:
            config = json.load(fh)
        entry = config["hooks"]["PreToolUse"][0]
        self.assertEqual(entry["matcher"], "Bash")
        command = entry["hooks"][0]["command"]
        self.assertIn('"${CLAUDE_PLUGIN_ROOT}/cli/guard_hook.py"', command)   # entre guillemets : le dossier peut porter des espaces
        self.assertLessEqual(entry["hooks"][0]["timeout"], 30)
        env = {"PATH": os.environ.get("PATH", ""), "CLAUDE_PLUGIN_ROOT": PLUGIN}
        payload = json.dumps({"tool_name": "Bash", "tool_input": {"command": "git push --tags"}})
        ran = subprocess.run(["sh", "-c", command], input=payload.encode(), capture_output=True, env=env, timeout=30)
        self.assertEqual(ran.returncode, 2)
        self.assertIn("commande refusée", ran.stderr.decode())
        self.assertEqual(ran.stdout, b"")
        ok = subprocess.run(["sh", "-c", command], input=json.dumps({"tool_name": "Bash", "tool_input": {"command": "ls"}}).encode(),
                            capture_output=True, env=env, timeout=30)
        self.assertEqual((ok.returncode, ok.stdout, ok.stderr), (0, b"", b""))

    def test_the_hook_entry_point_survives_a_broken_plugin_and_never_prints_a_trace(self):
        import shutil
        with tempfile.TemporaryDirectory() as tmp:
            broken = os.path.join(tmp, "cli")
            os.makedirs(os.path.join(broken, "aisdlclib"))
            shutil.copy(os.path.join(PLUGIN, "cli", "guard_hook.py"), broken)
            with open(os.path.join(broken, "aisdlclib", "guard.py"), "w", encoding="utf-8") as fh:
                fh.write("raise RuntimeError('plugin cassé')\n")
            for command, expected in (("git tag v1.5.0", 2), ("ls", 0)):
                payload = json.dumps({"tool_name": "Bash", "tool_input": {"command": command}}).encode()
                ran = subprocess.run([sys.executable, os.path.join(broken, "guard_hook.py")], input=payload, capture_output=True, timeout=30)
                self.assertEqual(ran.returncode, expected, command)
                self.assertNotIn(b"Traceback", ran.stderr)
        ran = subprocess.run([sys.executable, os.path.join(PLUGIN, "cli", "guard_hook.py")], input=b"\xff\xfe pas du json", capture_output=True, timeout=30)
        self.assertEqual((ran.returncode, ran.stderr), (0, b""))

    def test_check_from_the_command_line(self):
        ran = subprocess.run([sys.executable, CLI, "guard", "check", "cd x && npm publish"], capture_output=True)
        self.assertEqual(ran.returncode, 1)
        self.assertEqual(subprocess.run([sys.executable, CLI, "guard", "check", "npm", "test"], capture_output=True).returncode, 0)


if __name__ == "__main__":
    unittest.main()
