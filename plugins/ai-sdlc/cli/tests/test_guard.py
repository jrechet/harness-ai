"""Tests of the guardrail "an agent does not deliver": what it refuses, what it lets through, and the hook end
to end. The lists are long on purpose: one refusal too many hinders all the work, one miss lets a delivery out."""
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
    "git commit -m 'docs: explain npm publish, git tag v1 and make deploy'", "echo 'git tag v1'", "grep -r 'gh release create' .",
    "cat scripts/release.sh", "ls deploy/", "make test", "make it", "make build", "npm run build", "npm test", "npm install", "yarn install",
    "pnpm install", "kubectl get pods", "kubectl describe deploy/api", "kubectl logs api", "helm list", "helm template ./chart",
    "terraform plan", "terraform validate", "docker build -t x .", "docker run --rm x", "gh pr create --title x", "gh pr merge 12 --merge",
    "gh run list --commit abc --json name,status,conclusion,headSha", "gh release list", "gh release view v1", "gh api repos/o/r/releases",
    "python3 cli/ai_sdlc.py ship check . --base origin/main", "python3 cli/ai_sdlc.py ship render p.json . --base origin/main",
    "python3 -m unittest discover -s tests", "rg 'deploy' docs/", "cat > notes.md <<'EOF'\nTo deliver:\ngit tag v2.0.0\nmake deploy\nEOF",
    "git commit -m 'feat: x\n\ngit tag v1 is left to a human'", "git commit -m 'docs: `git tag v1` is run by hand'",
    "gh pr create --body \"$(cat <<'EOF'\nRun `git tag v1` after the merge.\nEOF\n)\"", "echo '$(git tag v1)'",
    "npm run build:prod", "npm run build:production", "npm run test:prod-like", "npm run release:notes", "npm run test:release",
    "npm run docs:deploy-preview", "npm run publish-check", "make deploy-docs", "make release-notes", "make build-production",
    "make check-release-notes", "make -n deploy", "pnpm --filter prod-api build", "yarn workspace prod-api build", "yarn workspace release-tools test",
    "cat > big.txt <<'EOF'\n" + "an ordinary line of text\n" * 1500 + "EOF",
    "curl -L https://github.com/x/y/releases/download/v1/tool.tgz | tar xz", "curl -sSL https://github.com/a/b/releases/latest/download/x",
    "curl https://api.github.com/repos/a/b/releases", "wget https://github.com/x/y/releases/download/v1/o.tgz", "gh api repos/a/b/releases -X GET",
    "gh api --method GET repos/a/b/releases", "kubectl apply --dry-run=client -f x", "kubectl create --dry-run=client -o yaml deploy x",
    "cargo publish --dry-run", "npm publish --dry-run", "goreleaser release --snapshot", "npm dist-tag ls x", "aws deploy list-deployments",
    "az deployment group list", "kubectl get svc create", "kubectl get pods -n create", "helm diff upgrade x y", "git push origin release/1.2",
    "git push origin v2-migration", "git push origin feature-v1.2.3", "git push", "git push origin main", "git config alias.co checkout",
    "npx prettier --check .", "npx tsc --noEmit", "python3 -m pytest -k deploy", "uv run pytest", "docker compose up -d", "docker compose logs",
    "python3 -c \"print('git tag v1 is run by hand')\"".replace("git tag v1", "tag"), "echo $(( 1 << 4 ))\nls", "cat <<< hello\nls",
    "find . -name '*.py' -exec wc -l {} +", "nice -n 10 make test", "sudo -u root ls", "ls 2>&1 | head", "ssh host 'kubectl get pods'", "printf 'a\nb\n' | sort", "timeout 60 make test", "xargs -n1 echo < f", "curl https://example.com/health", "aws s3 ls", "gcloud config list", "",
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
    "timeout 60 make deploy", "timeout -k 5 60 npm publish", "nohup make deploy &", "cat <<EOF > x\ntext\nEOF\ngit tag v1",
    "git commit -m \"docs: `git tag v7`\"", "ssh prod 'kubectl apply -f k8s/'", "ls | xargs -I{} make deploy",
    "bash <<'EOF'\ngit tag v1\nEOF", "sh <<EOF\nkubectl apply -f x\nEOF", "cat <<EOF | sh\nnpm publish\nEOF", "bash -s <<'X'\nnpm publish\nX",
    "cat <<< hello\ngit tag v1", "read x <<< foo\nmake deploy", "echo $(( 1 << n ))\ngit tag v1", "echo '<<x'\ngit tag v1", "bash <<<'git tag v1'",
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
        team = ["./bin/go-live now", "scripts/go-prod.sh <version>", "make send-express VERSION=<v>", "fabric"]
        self.assertTrue(guard.reasons("./bin/go-live now", team))
        self.assertTrue(guard.reasons("cd x && bin/go-live now --force", team))
        self.assertTrue(guard.reasons("scripts/go-prod.sh v2", team))
        self.assertTrue(guard.reasons("make send-express VERSION=v2.0.0", team))
        self.assertEqual(guard.reasons("./bin/go-live status", team), [])
        self.assertEqual(guard.reasons("make send-express", team), [])         # without its version, it is not the team's command
        self.assertEqual(guard.reasons("fabric --help", team), [])               # a single word does not make a recognised command

    def test_a_realistic_team_procedure_does_not_block_ordinary_commands(self):
        # review finding: two words were enough, and "git push origin vX.Y.Z" got every git push refused
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
        self.assertTrue(guard.reasons("sh -c 'a; sh -c \"b; sh -c c\"'; eval d; eval e"))   # too many nested commands: refused rather than run

    def test_hostile_or_odd_input_does_not_crash(self):
        for command in ("git tag 'v1", "echo \"", "$(" * 3000, "a" * 30_000, "git tag v1 " + "x" * 30_000, "\x00\x1b[31m", "`" * 501,
                        "sh -c " * 50 + "'git tag v1'", None, 3, ["git", "tag"]):
            with self.subTest(command=str(command)[:20]):
                self.assertIsInstance(guard.reasons(command), list)   # type: ignore[arg-type]
        self.assertTrue(guard.reasons("git tag 'v1"))                  # cannot be split: judged on its text
        self.assertTrue(guard.reasons("git tag v1 " + "x" * 30_000))   # too long to be split: judged on its text
        self.assertEqual(guard.reasons("echo " + "x" * 30_000), [])    # long and with nothing of a delivery: it passes
        self.assertEqual(guard.reasons("echo \"hello"), [])

    def test_the_refusal_says_what_to_do_instead(self):
        text = guard.render(guard.reasons("git tag v1"))
        self.assertIn("a git tag", text)
        self.assertIn("a human runs it", text)
        for name in guard.ALLOW_ENV_ALIASES:
            self.assertNotIn(name, text)   # the team's door is not whispered to the agent


class HookTests(unittest.TestCase):
    def call(self, command, env: dict | None = None, tool: str = "Bash", cwd: str | None = None) -> tuple[int, str]:
        payload = {"hook_event_name": "PreToolUse", "tool_name": tool, "tool_input": {"command": command}, "cwd": cwd or "."}
        return guard.run_hook(json.dumps(payload), env or {})

    def test_a_delivery_is_refused_with_exit_code_2_and_anything_else_passes(self):
        code, message = self.call("git tag v1.5.0")
        self.assertEqual(code, 2)
        self.assertIn("command refused", message)
        self.assertEqual(self.call("make test"), (0, ""))
        self.assertEqual(self.call("git tag v1", tool="Write"), (0, ""))
        self.assertEqual(self.call(None), (0, ""))

    def test_unreadable_input_passes_and_never_raises(self):
        for raw in ("", "x", "[]", "null", '{"tool_name": "Bash"}', '{"tool_name": "Bash", "tool_input": []}', "[" * 100_000):
            with self.subTest(raw=raw[:12]):
                self.assertEqual(guard.run_hook(raw, {}), (0, ""))

    def test_a_truncated_or_oversized_call_is_judged_on_its_text_not_waved_through(self):
        # review finding: beyond 200,000 characters the JSON was cut, unreadable, and everything passed
        self.assertEqual(self.call("git tag v1" + " " * 250_000)[0], 2)
        self.assertEqual(self.call("x " * 120_000 + "; git tag v1")[0], 2)
        cut = json.dumps({"tool_name": "Bash", "tool_input": {"command": "git tag v1.5.0 && git push --tags"}})[:-9]
        self.assertEqual(guard.run_hook(cut, {})[0], 2)
        self.assertEqual(guard.run_hook(json.dumps({"tool_name": "Bash", "tool_input": {"command": "ls"}})[:-9], {}), (0, ""))

    def test_the_team_can_open_the_door_from_the_session_environment_only(self):
        self.assertEqual(self.call("git tag v1", env={guard.ALLOW_ENV: "1"}), (0, ""))
        self.assertEqual(self.call("git tag v1", env={guard.ALLOW_ENV: "0"})[0], 2)
        self.assertEqual(self.call(f"{guard.ALLOW_ENV}=1 git tag v1")[0], 2)          # set by the command: no effect
        self.assertEqual(self.call(f"export {guard.ALLOW_ENV}=1; make deploy")[0], 2)

    def test_the_former_name_of_the_door_is_still_read(self):
        self.assertEqual(guard.ALLOW_ENV, "AI_SDLC_ALLOW_AGENT_DELIVERY")
        self.assertEqual(self.call("git tag v1", env={"AI_SDLC_LIVRAISON_PAR_AGENT": "1"}), (0, ""))
        self.assertEqual(self.call("git tag v1", env={"AI_SDLC_LIVRAISON_PAR_AGENT": "0"})[0], 2)
        self.assertEqual(self.call("AI_SDLC_LIVRAISON_PAR_AGENT=1 git tag v1")[0], 2)

    def test_the_team_procedure_is_read_from_the_project_even_if_the_working_copy_drops_it(self):
        for name, text in (("delivery.md", "---\npoint: delivery\nmode: append\n---\n- Deliver: `bin/go-live now` by the on-call person.\n"),
                           ("livraison.md", "---\npoint: livraison\nmode: ajoute\n---\n- Livrer : `bin/go-live now` par l'astreinte.\n")):
            with self.subTest(name=name):
                self.check_procedure(name, text)

    def check_procedure(self, name: str, text: str) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo, remote = os.path.join(tmp, "repo"), os.path.join(tmp, "origin.git")
            os.makedirs(os.path.join(repo, "docs", "agents"))
            git = lambda *args: subprocess.run(["git", "-C", repo, "-c", "user.name=t", "-c", "user.email=t@example.com", *args],  # noqa: E731
                                               capture_output=True, check=True)
            subprocess.run(["git", "init", "-q", "--bare", "-b", "main", remote], capture_output=True, check=True)
            git("init", "-q", "-b", "main")
            path = os.path.join(repo, "docs", "agents", name)
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(text)
            git("add", "-A")
            git("commit", "-q", "-m", "base")
            git("remote", "add", "origin", remote)
            git("push", "-q", "origin", "main")
            git("remote", "set-head", "origin", "main")
            env = {"CLAUDE_PROJECT_DIR": repo}
            self.assertEqual(self.call("bin/go-live now", env=env)[0], 2)
            self.assertEqual(self.call("bin/go-live status", env=env)[0], 0)
            os.remove(path)   # the agent removes the line from its working copy: the base branch still carries it
            self.assertEqual(self.call("bin/go-live now", env=env)[0], 2)
            self.assertEqual(self.call("bin/go-live now", cwd=repo)[0], 2)   # without CLAUDE_PROJECT_DIR, the folder of the call
            git("remote", "remove", "origin")   # without a remote branch: the last commit still carries the procedure
            self.assertEqual(self.call("bin/go-live now", env=env)[0], 2)
            git("tag", "candidate")
            self.assertEqual(self.call("git push origin candidate", env=env)[0], 2)   # the tags of the repository are known to the hook

    def test_an_internal_error_falls_back_instead_of_opening_the_door(self):
        original = guard.hook
        guard.hook = lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("failure"))
        self.addCleanup(setattr, guard, "hook", original)
        self.assertEqual(self.call("cd x && git tag v1.5.0")[0], 2)
        self.assertEqual(self.call("make test")[0], 0)


RUNBOOK = """---
point: operations
mode: append
---
- API logs: `journalctl -u api --since <start time>`, read-only.
- State: `systemctl status api` (read-only), then restart with `systemctl restart api`, decided by the on-call person.
- Read-only diagnostic: `bin/ops queue depth`.
- Mitigate: `bin/ops rollback VERSION=<previous version>`, decided and run by the on-call person.
- `bin/ops purge cache` is not read-only: the on-call person decides it.
"""
GATE = '{"env":{"AI_SDLC_ALLOW_AGENT_DELIVERY":"1"}}'
SETTINGS_WRITES = [
    "echo " + GATE + " > .claude/settings.json", "echo '{}' >> .claude/settings.local.json", "echo x >.claude/settings.json",
    "echo x | tee .claude/settings.json", "echo x | sudo tee -a /repo/.claude/settings.local.json", "sed -i 's/0/1/' .claude/settings.json",
    "sed -i.bak -e 's/0/1/' $CLAUDE_PROJECT_DIR/.claude/settings.json", "perl -pi -e 's/0/1/' .claude/settings.json",
    "cp /tmp/s.json .claude/settings.json", "mv /tmp/s.json ~/.claude/settings.json", "cat > .claude/settings.json <<'EOF'\n" + GATE + "\nEOF",
    "sh -c 'echo x > .claude/settings.json'", "cd x && echo x > ./.claude/settings.json", "jq '.env.X=1' a.json > .claude/./settings.json",
    "python3 -c \"open('.claude/settings.json','w').write('{}')\"", "echo 'x > .claude/settings.json",
    "node -e \"require('fs').writeFileSync('.claude/settings.json', '{}')\"",
]
SETTINGS_READS = [
    "cat .claude/settings.json", "jq .env .claude/settings.json", "jq . < .claude/settings.json", "grep -n hooks .claude/settings.local.json",
    "sed -n 1,20p .claude/settings.json", "echo x > notes/settings.json", "echo x > .claude/notes.md", "echo x | tee out.json",
    "sed -i 's/a/b/' src/app.py", "cp .claude/settings.json /tmp/backup.json", "git diff -- .claude/settings.json", "echo x > .vscode/settings.json",
    "python3 -c \"import json; print(json.load(open('.claude/settings.json')))\"", "ls .claude > listing.txt",
]


class RunbookTests(unittest.TestCase):
    """Issue #115, first hole: the commands of the team's runbook that are not marked read-only."""

    def test_the_runbook_commands_not_marked_read_only_are_listed(self):
        self.assertEqual(guard.runbook_commands(RUNBOOK),
                         ["systemctl restart api", "bin/ops rollback VERSION=<previous-version>", "bin/ops purge cache"])
        french = "- Journaux : `journalctl -u api`, lecture seule.\n- Relancer : `systemctl restart api`, par l'astreinte.\n"
        self.assertEqual(guard.runbook_commands(french), ["systemctl restart api"])
        self.assertEqual(guard.runbook_commands("no command here, and a `word` alone"), [])

    def test_a_mitigation_of_the_runbook_is_refused_and_a_diagnostic_passes(self):
        team = guard.runbook_commands(RUNBOOK)
        for command in ("systemctl restart api", "ssh prod systemctl restart api", "ssh prod 'sudo systemctl restart api'",
                        "sudo systemctl restart api", "cd /srv && systemctl restart api", "bin/ops rollback VERSION=v1.4.0",
                        "./bin/ops purge cache", "sh -c 'systemctl restart api'"):
            with self.subTest(command=command):
                self.assertTrue(guard.reasons(command, team))
        for command in ("systemctl status api", "journalctl -u api --since 10:00", "bin/ops queue depth", "cat docs/agents/operations.md",
                        "grep -n restart docs/agents/operations.md", "systemctl status worker",
                        "git commit -m 'docs: `systemctl restart api` is for the on-call'", "make test", "git status"):
            with self.subTest(command=command):
                self.assertEqual(guard.reasons(command, team), [])

    def write(self, repo: str, name: str, text: str) -> None:
        os.makedirs(os.path.join(repo, "docs", "agents"), exist_ok=True)
        with open(os.path.join(repo, "docs", "agents", name), "w", encoding="utf-8") as fh:
            fh.write(text)

    def test_the_runbook_is_read_from_the_project_under_both_file_names(self):
        for name in ("operations.md", "exploitation.md"):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as repo:
                self.write(repo, name, RUNBOOK)
                lines = guard.team_lines(repo)
                self.assertIn("systemctl restart api", lines)
                self.assertNotIn("systemctl status api", lines)
                for command, expected in (("systemctl restart api", 2), ("ssh prod systemctl restart api", 2), ("systemctl status api", 0),
                                          ("cat docs/agents/" + name, 0)):
                    payload = json.dumps({"tool_name": "Bash", "tool_input": {"command": command}})
                    self.assertEqual(guard.run_hook(payload, {"CLAUDE_PROJECT_DIR": repo})[0], expected, command)
                for command, expected in (("systemctl restart api", 1), ("ssh prod systemctl restart api", 1), ("systemctl status api", 0)):
                    ran = subprocess.run([sys.executable, CLI, "guard", "check", "--repo", repo, command], capture_output=True)
                    self.assertEqual(ran.returncode, expected, command)

    def test_marking_a_command_read_only_in_the_working_copy_does_not_disarm_it(self):
        with tempfile.TemporaryDirectory() as repo:
            git = lambda *args: subprocess.run(["git", "-C", repo, "-c", "user.name=t", "-c", "user.email=t@example.com", *args],  # noqa: E731
                                               capture_output=True, check=True)
            git("init", "-q", "-b", "main")
            self.write(repo, "operations.md", RUNBOOK)
            git("add", "-A")
            git("commit", "-q", "-m", "base")
            self.write(repo, "operations.md", "- Restart: `systemctl restart api`, read-only.\n")
            self.assertIn("systemctl restart api", guard.team_lines(repo))
            os.remove(os.path.join(repo, "docs", "agents", "operations.md"))
            self.assertIn("systemctl restart api", guard.team_lines(repo))

    def test_the_delivery_procedure_keeps_all_its_commands_whatever_the_words_around(self):
        with tempfile.TemporaryDirectory() as repo:
            self.write(repo, "delivery.md", "- Check: `bin/go-live now`, read-only it is not.\n")
            self.assertEqual(guard.team_lines(repo), ["bin/go-live now"])


class SettingsTests(unittest.TestCase):
    """Issue #115, second hole: the agent writes the variable that opens the gate into its own settings."""

    def test_a_shell_write_into_the_settings_is_refused(self):
        for command in SETTINGS_WRITES:
            with self.subTest(command=command):
                self.assertTrue(guard.reasons(command))

    def test_reading_the_settings_and_writing_elsewhere_pass(self):
        for command in SETTINGS_READS:
            with self.subTest(command=command):
                self.assertEqual(guard.reasons(command), [])

    def test_the_issue_reproduction_from_the_command_line(self):
        ran = subprocess.run([sys.executable, CLI, "guard", "check", "echo " + GATE + " > .claude/settings.json"], capture_output=True)
        self.assertEqual(ran.returncode, 1)
        text = guard.render(guard.reasons("echo x > .claude/settings.json"))
        for name in guard.ALLOW_ENV_ALIASES:
            self.assertNotIn(name, text)   # the name of the gate is not whispered
        self.assertEqual(subprocess.run([sys.executable, CLI, "guard", "check", "cat .claude/settings.json"], capture_output=True).returncode, 0)

    def tool(self, name: str, tool_input: dict, cwd: str = ".") -> int:
        return guard.run_hook(json.dumps({"tool_name": name, "tool_input": tool_input, "cwd": cwd}), {})[0]

    def test_a_write_of_the_settings_that_carries_the_gate_is_refused(self):
        for path in (".claude/settings.json", "/repo/.claude/settings.local.json", ".claude/./settings.json", "x/../.claude/settings.json"):
            with self.subTest(path=path):
                self.assertEqual(self.tool("Write", {"file_path": path, "content": GATE}), 2)
        self.assertEqual(self.tool("Write", {"file_path": ".claude/settings.json", "content": '{"env":{"AI_SDLC_LIVRAISON_PAR_AGENT":"1"}}'}), 2)
        escaped = '{"env":{"\\u0041I_SDLC_ALLOW_AGENT_DELIVERY":"1"}}'   # the same name once the JSON is read
        self.assertEqual(self.tool("Write", {"file_path": ".claude/settings.json", "content": escaped}), 2)
        code, message = guard.run_hook(json.dumps({"tool_name": "Write", "tool_input": {"file_path": ".claude/settings.json", "content": GATE}}), {})
        self.assertIn("refused", message)
        for name in guard.ALLOW_ENV_ALIASES:
            self.assertNotIn(name, message)

    def test_an_ordinary_write_passes(self):
        self.assertEqual(self.tool("Write", {"file_path": ".claude/settings.json", "content": '{"permissions":{"allow":["Bash(ls)"]}}'}), 0)
        self.assertEqual(self.tool("Write", {"file_path": "docs/guardrail.md", "content": "Set AI_SDLC_ALLOW_AGENT_DELIVERY=1 to open the gate."}), 0)
        self.assertEqual(self.tool("Write", {"file_path": "src/settings.json", "content": GATE}), 0)
        self.assertEqual(self.tool("Edit", {"file_path": "README.md", "old_string": "a", "new_string": "AI_SDLC_ALLOW_AGENT_DELIVERY"}), 0)
        with tempfile.TemporaryDirectory() as empty:
            self.assertEqual(self.tool("Edit", {"file_path": ".claude/settings.json", "old_string": "a", "new_string": "b"}, cwd=empty), 0)
        for odd in ({}, {"file_path": None}, {"file_path": 3, "content": GATE}, {"file_path": ".claude/settings.json"},
                    {"file_path": ".claude/settings.json", "edits": "x"}, {"file_path": ".claude/settings.json\0", "content": 4}):
            with self.subTest(odd=odd):
                self.assertEqual(self.tool("Write", odd), 0)
                self.assertEqual(self.tool("MultiEdit", odd), 0)

    def test_an_edit_of_the_settings_is_judged_on_the_file_it_leaves(self):
        with tempfile.TemporaryDirectory() as repo:
            os.makedirs(os.path.join(repo, ".claude"))
            path = os.path.join(repo, ".claude", "settings.json")
            before = '{"env": {"AI_SDLC_ALLOW_": "1", "OTHER": "0"}, "permissions": {}}'
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(before)
            edit = lambda old, new: self.tool("Edit", {"file_path": path, "old_string": old, "new_string": new}, cwd=repo)  # noqa: E731
            self.assertEqual(edit('"OTHER": "0"', '"AI_SDLC_ALLOW_AGENT_DELIVERY": "1"'), 2)
            self.assertEqual(edit('_": "1"', '_AGENT_DELIVERY": "1"'), 2)         # the name is assembled by the edit: the file left carries it
            self.assertEqual(edit('"OTHER": "0"', '"OTHER": "1"'), 0)
            relative = {"file_path": ".claude/settings.json", "old_string": '_": "1"', "new_string": '_AGENT_DELIVERY": "1"'}
            self.assertEqual(self.tool("Edit", relative, cwd=repo), 2)             # a relative path is read from the folder of the call
            edits = [{"old_string": "ALLOW_", "new_string": "ALLOW_AGENT_"}, {"old_string": 'AGENT_"', "new_string": 'AGENT_DELIVERY"'}]
            self.assertEqual(self.tool("MultiEdit", {"file_path": path, "edits": edits}, cwd=repo), 2)
            self.assertEqual(self.tool("MultiEdit", {"file_path": path, "edits": edits[:1]}, cwd=repo), 0)
            with open(path, encoding="utf-8") as fh:
                self.assertEqual(fh.read(), before)                                # the guardrail reads, it never writes

    def test_the_team_gate_still_opens_everything(self):
        payload = json.dumps({"tool_name": "Write", "tool_input": {"file_path": ".claude/settings.json", "content": GATE}})
        self.assertEqual(guard.run_hook(payload, {guard.ALLOW_ENV: "1"}), (0, ""))

    def test_a_call_that_cannot_be_read_and_writes_the_gate_into_the_settings_is_refused(self):
        payload = json.dumps({"tool_name": "Write", "tool_input": {"file_path": ".claude/settings.json", "content": GATE}})
        self.assertEqual(guard.run_hook(payload[:-3], {})[0], 2)
        self.assertEqual(guard.run_hook(json.dumps({"tool_name": "Write", "tool_input": {"file_path": "a.md", "content": "x"}})[:-3], {}), (0, ""))


class OtherToolsTests(unittest.TestCase):
    """Issue #115, third hole: a shell command sent through a tool that is not Bash."""

    def call(self, tool: str, tool_input: dict) -> int:
        return guard.run_hook(json.dumps({"hook_event_name": "PreToolUse", "tool_name": tool, "tool_input": tool_input}), {})[0]

    def test_a_delivery_through_another_tool_that_carries_a_command_is_refused(self):
        for tool in ("mcp__terminal__run_in_terminal", "mcp__shell__exec", "PowerShell", "SomeFutureShell"):
            with self.subTest(tool=tool):
                self.assertEqual(self.call(tool, {"command": "git tag v1.0.0"}), 2)
                self.assertEqual(self.call(tool, {"command": "cd x && npm publish", "cwd": "/tmp"}), 2)
                self.assertEqual(self.call(tool, {"command": "echo x > .claude/settings.json"}), 2)
                self.assertEqual(self.call(tool, {"command": "git status"}), 0)
        self.assertEqual(self.call("mcp__shell__exec", {"command": ["git", "tag", "v1.0.0"]}), 2)   # a command given word by word
        self.assertEqual(self.call("mcp__shell__exec", {"command": ["git", "status"]}), 0)

    def test_a_tool_without_a_command_passes(self):
        self.assertEqual(self.call("mcp__docs__search", {"query": "git tag v1.0.0"}), 0)
        self.assertEqual(self.call("Read", {"file_path": ".claude/settings.json"}), 0)
        self.assertEqual(self.call("mcp__shell__exec", {"command": {"git": "tag"}}), 0)
        self.assertEqual(self.call("mcp__shell__exec", {"command": ["git", 3]}), 0)
        self.assertEqual(self.call("Write", {"file_path": "notes.md", "content": "git tag v1.0.0", "command": "git tag v1.0.0"}), 0)

    def test_a_call_without_a_command_does_not_read_the_repository(self):
        """The hook fires on every tool of every MCP server: only a call that carries a command pays for git."""
        from unittest import mock
        with tempfile.TemporaryDirectory() as tmp:
            def git_calls(payload) -> int:
                with mock.patch.object(guard, "_git_out", return_value="") as git:
                    guard.run_hook(json.dumps(payload), {"CLAUDE_PROJECT_DIR": tmp})
                return git.call_count
            for tool, tool_input in (("mcp__docs__search", {"query": "git tag v1.0.0"}),
                                     ("mcp__docs__search", {}),
                                     ("mcp__shell__exec", {"command": {"git": "tag"}}),
                                     ("mcp__shell__exec", {"command": ["git", 3]}),
                                     ("mcp__shell__exec", {"command": []}),
                                     ("mcp__shell__exec", {"command": None}),
                                     ("Read", {"file_path": "a.md"}),
                                     ("Write", {"file_path": "a.md", "content": "x", "command": "git tag v1.0.0"})):
                with self.subTest(tool=tool, tool_input=tool_input):
                    self.assertEqual(git_calls({"tool_name": tool, "tool_input": tool_input, "cwd": tmp}), 0)
            for payload in ([], "text", {"tool_name": "mcp__docs__search"}, {"tool_name": "mcp__docs__search", "tool_input": "x"}):
                with self.subTest(payload=payload):
                    self.assertEqual(git_calls(payload), 0)
            # a call that carries a command still reads the procedure and the tags
            for tool, command in (("Bash", "git status"), ("mcp__shell__exec", "git status"), ("mcp__shell__exec", ["git", "status"])):
                with self.subTest(tool=tool, command=command):
                    self.assertGreater(git_calls({"tool_name": tool, "tool_input": {"command": command}, "cwd": tmp}), 0)

    def test_the_hook_entry_point_refuses_the_cases_of_the_issue(self):
        hook = os.path.join(PLUGIN, "cli", "guard_hook.py")
        env = {k: v for k, v in os.environ.items() if k not in guard.ALLOW_ENV_ALIASES and k != "CLAUDE_PROJECT_DIR"}
        cases = (({"tool_name": "mcp__terminal__run_in_terminal", "tool_input": {"command": "git tag v1.0.0"}}, 2),
                 ({"tool_name": "Write", "tool_input": {"file_path": ".claude/settings.json", "content": GATE}}, 2),
                 ({"tool_name": "mcp__terminal__run_in_terminal", "tool_input": {"command": "git status"}}, 0),
                 ({"tool_name": "Write", "tool_input": {"file_path": "notes.md", "content": "git tag v1.0.0"}}, 0))
        with tempfile.TemporaryDirectory() as tmp:
            for payload, expected in cases:
                ran = subprocess.run([sys.executable, hook], input=json.dumps({**payload, "cwd": tmp}).encode(), capture_output=True, env=env, timeout=30)
                self.assertEqual(ran.returncode, expected, payload)
                self.assertNotIn(b"Traceback", ran.stderr)

    def test_the_hook_is_declared_for_the_file_tools_and_the_tools_of_other_servers(self):
        import re
        with open(os.path.join(PLUGIN, "hooks", "hooks.json"), encoding="utf-8") as fh:
            entries = json.load(fh)["hooks"]["PreToolUse"]
        matchers = [entry["matcher"] for entry in entries]
        for tool in ("Bash", "Write", "Edit", "MultiEdit", "mcp__terminal__run_in_terminal", "mcp__shell__exec"):
            with self.subTest(tool=tool):
                self.assertTrue(any(re.fullmatch(matcher, tool) for matcher in matchers))
        for entry in entries:
            self.assertIn('"${CLAUDE_PLUGIN_ROOT}/cli/guard_hook.py"', entry["hooks"][0]["command"])
            self.assertLessEqual(entry["hooks"][0]["timeout"], 30)

    def test_the_last_resort_of_a_broken_plugin_refuses_the_gate_written_into_the_settings(self):
        import shutil
        with tempfile.TemporaryDirectory() as tmp:
            broken = os.path.join(tmp, "cli")
            os.makedirs(os.path.join(broken, "aisdlclib"))
            shutil.copy(os.path.join(PLUGIN, "cli", "guard_hook.py"), broken)
            with open(os.path.join(broken, "aisdlclib", "guard.py"), "w", encoding="utf-8") as fh:
                fh.write("raise RuntimeError('broken plugin')\n")
            env = {k: v for k, v in os.environ.items() if k not in guard.ALLOW_ENV_ALIASES}
            for payload, expected in (({"tool_name": "Write", "tool_input": {"file_path": ".claude/settings.json", "content": GATE}}, 2),
                                      ({"tool_name": "Bash", "tool_input": {"command": "echo " + GATE + " > .claude/settings.json"}}, 2),
                                      ({"tool_name": "mcp__terminal__run_in_terminal", "tool_input": {"command": "git tag v1.0.0"}}, 2),
                                      ({"tool_name": "Write", "tool_input": {"file_path": ".claude/settings.json", "content": "{}"}}, 0),
                                      ({"tool_name": "Write", "tool_input": {"file_path": "notes.md", "content": "hello"}}, 0)):
                ran = subprocess.run([sys.executable, os.path.join(broken, "guard_hook.py")], input=json.dumps(payload).encode(),
                                     capture_output=True, env=env, timeout=30)
                self.assertEqual(ran.returncode, expected, payload)
                self.assertNotIn(b"Traceback", ran.stderr)


class PluginWiringTests(unittest.TestCase):
    def test_the_plugin_declares_the_hook_and_the_command_it_names_works(self):
        with open(os.path.join(PLUGIN, "hooks", "hooks.json"), encoding="utf-8") as fh:
            config = json.load(fh)
        entry = config["hooks"]["PreToolUse"][0]
        self.assertEqual(entry["matcher"], "Bash")
        command = entry["hooks"][0]["command"]
        self.assertIn('"${CLAUDE_PLUGIN_ROOT}/cli/guard_hook.py"', command)   # between quotes: the folder may contain spaces
        self.assertLessEqual(entry["hooks"][0]["timeout"], 30)
        env = {"PATH": os.environ.get("PATH", ""), "CLAUDE_PLUGIN_ROOT": PLUGIN}
        payload = json.dumps({"tool_name": "Bash", "tool_input": {"command": "git push --tags"}})
        ran = subprocess.run(["sh", "-c", command], input=payload.encode(), capture_output=True, env=env, timeout=30)
        self.assertEqual(ran.returncode, 2)
        self.assertIn("command refused", ran.stderr.decode())
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
                fh.write("raise RuntimeError('broken plugin')\n")
            for command, expected in (("git tag v1.5.0", 2), ("ls", 0)):
                payload = json.dumps({"tool_name": "Bash", "tool_input": {"command": command}}).encode()
                ran = subprocess.run([sys.executable, os.path.join(broken, "guard_hook.py")], input=payload, capture_output=True, timeout=30)
                self.assertEqual(ran.returncode, expected, command)
                self.assertNotIn(b"Traceback", ran.stderr)
            payload = json.dumps({"tool_name": "Bash", "tool_input": {"command": "git tag v1.5.0"}}).encode()
            for name in ("AI_SDLC_ALLOW_AGENT_DELIVERY", "AI_SDLC_LIVRAISON_PAR_AGENT"):   # the door, under both names, without the module
                env = {**os.environ, name: "1"}
                ran = subprocess.run([sys.executable, os.path.join(broken, "guard_hook.py")], input=payload, capture_output=True, env=env, timeout=30)
                self.assertEqual(ran.returncode, 0, name)
        ran = subprocess.run([sys.executable, os.path.join(PLUGIN, "cli", "guard_hook.py")], input=b"\xff\xfe not json", capture_output=True, timeout=30)
        self.assertEqual((ran.returncode, ran.stderr), (0, b""))

    def test_check_from_the_command_line(self):
        ran = subprocess.run([sys.executable, CLI, "guard", "check", "cd x && npm publish"], capture_output=True)
        self.assertEqual(ran.returncode, 1)
        self.assertEqual(subprocess.run([sys.executable, CLI, "guard", "check", "npm", "test"], capture_output=True).returncode, 0)


if __name__ == "__main__":
    unittest.main()
