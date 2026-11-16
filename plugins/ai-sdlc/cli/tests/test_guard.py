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
    "git commit -m 'feat: x\n\ngit tag v1 reste à faire par un humain'", "printf 'a\nb\n' | sort", "timeout 60 make test", "xargs -n1 echo < f", "curl https://example.com/health", "aws s3 ls", "gcloud config list", "",
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
    "git commit -m \"docs: `git tag v7`\"", "ssh prod 'kubectl apply -f k8s/'", "ls | xargs -I{} make deploy", "if true; then git tag v1; fi", "git tag v1 \\\n  -m 'x'",
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
        team = ["./bin/go-live now", "scripts/promouvoir.sh <version>", "make livraison-express VERSION=<v>", "fabric"]
        self.assertTrue(guard.reasons("./bin/go-live now", team))
        self.assertTrue(guard.reasons("cd x && bin/go-live now --force", team))
        self.assertEqual(guard.reasons("./bin/go-live status", team), [])
        self.assertEqual(guard.reasons("scripts/promouvoir.sh v2", team), [])   # un seul mot fixe : trop peu pour reconnaître la commande
        self.assertEqual(guard.reasons("fabric --help", team), [])

    def test_hostile_or_odd_input_does_not_crash(self):
        for command in ("git tag 'v1", "echo \"", "$(" * 3000, "a" * 30_000, "git tag v1 " + "x" * 30_000, "\x00\x1b[31m", "`" * 501,
                        "sh -c " * 50 + "'git tag v1'", None, 3, ["git", "tag"]):
            with self.subTest(command=str(command)[:20]):
                self.assertIsInstance(guard.reasons(command), list)   # type: ignore[arg-type]
        self.assertTrue(guard.reasons("git tag 'v1"))                  # indécoupable : jugée sur son texte
        self.assertTrue(guard.reasons("git tag v1 " + "x" * 30_000))   # trop longue : ni lue ni lancée
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
        self.assertIn('"${CLAUDE_PLUGIN_ROOT}/cli/ai_sdlc.py" guard hook', command)   # entre guillemets : le dossier peut porter des espaces
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

    def test_check_from_the_command_line(self):
        ran = subprocess.run([sys.executable, CLI, "guard", "check", "cd x && npm publish"], capture_output=True)
        self.assertEqual(ran.returncode, 1)
        self.assertEqual(subprocess.run([sys.executable, CLI, "guard", "check", "npm", "test"], capture_output=True).returncode, 0)


if __name__ == "__main__":
    unittest.main()
