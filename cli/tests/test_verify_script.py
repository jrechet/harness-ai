"""scripts/ci/verify.sh replays the fixture task selftests when the runner can: the script is run
for real, with a stand-in `python3` that records what it was asked and with which environment."""
from __future__ import annotations

import http.server
import os
import socket
import stat
import subprocess
import sys
import tempfile
import threading
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SCRIPT = os.path.join(ROOT, "scripts", "ci", "verify.sh")
SHELL = "/bin/sh"
HARNESS_SUITE = "discover -s cli/tests"
PLUGIN_SUITE = "discover -s plugins/ai-sdlc/cli/tests"
SCRIPT_TIMEOUT_SECONDS = 60
# Records one line per call, `<HARNESS_SELFTEST or "unset">|<arguments>`, with shell builtins only:
# the PATH of the script holds nothing but the stand-ins.
RECORDING_PYTHON = '#!/bin/sh\necho "${HARNESS_SELFTEST-unset}|$*" >> "$CALLS"\n'
EMPTY_TOOL = "#!/bin/sh\nexit 0\n"
# Records the suites the same way, but hands the probes of the script (`-c` and reachable.py) to
# the real interpreter, so they are run for real; NO_VENV makes the one that looks for venv and
# ensurepip fail, as on a machine without the python3-venv package.
PROBING_PYTHON = f"""#!/bin/sh
case "$1" in -c|*/reachable.py)
  case "$2" in *ensurepip*) [ -z "${{NO_VENV:-}}" ] || exit 1 ;; esac
  exec "{sys.executable}" "$@" ;;
esac
echo "${{HARNESS_SELFTEST-unset}}|$*" >> "$CALLS"
"""
LOOPBACK = "127.0.0.1"


# No way out: the CI script is a POSIX shell script; without /bin/sh these tests fail, they do not pass by not running.
class SelftestInVerifyScriptTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.bin = os.path.join(self.tmp.name, "bin")
        os.mkdir(self.bin)
        self.calls = os.path.join(self.tmp.name, "calls")
        self.tool("python3", RECORDING_PYTHON)

    def tool(self, name: str, body: str = EMPTY_TOOL) -> None:
        path = os.path.join(self.bin, name)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(body)
        os.chmod(path, os.stat(path).st_mode | stat.S_IXUSR)

    def verify(self, **env: str) -> tuple[str, dict[str, str]]:
        """Runs the script outside a pull request; returns what it printed and, for each suite, the
        HARNESS_SELFTEST it was started with."""
        done = subprocess.run([SHELL, SCRIPT], cwd=ROOT, capture_output=True, text=True, timeout=SCRIPT_TIMEOUT_SECONDS,
                              env={"PATH": self.bin, "CALLS": self.calls, **env})
        self.assertEqual(done.returncode, 0, done.stderr)
        with open(self.calls, encoding="utf-8") as fh:
            calls = [line.rstrip("\n").split("|", 1) for line in fh]
        suites = {suite: value for value, arguments in calls for suite in (HARNESS_SUITE, PLUGIN_SUITE)
                  if arguments.endswith(suite)}
        self.assertEqual(sorted(suites), sorted((HARNESS_SUITE, PLUGIN_SUITE)), calls)
        return done.stdout, suites

    def test_the_selftests_are_replayed_when_go_and_npm_are_on_the_runner(self):
        self.tool("go")
        self.tool("npm")
        out, suites = self.verify()
        self.assertEqual(suites[HARNESS_SUITE], "1")
        self.assertNotIn("selftest skipped", out)

    def test_only_the_harness_suite_replays_them(self):
        self.tool("go")
        self.tool("npm")
        _, suites = self.verify()
        self.assertEqual(suites[PLUGIN_SUITE], "unset")

    def test_a_missing_tool_is_named_and_the_selftests_are_skipped(self):
        self.tool("npm")
        out, suites = self.verify()
        self.assertIn("selftest skipped: go missing", out.splitlines())
        self.assertEqual(suites[HARNESS_SUITE], "unset")

    def test_every_missing_tool_is_named(self):
        out, suites = self.verify()
        self.assertIn("selftest skipped: go npm missing", out.splitlines())
        self.assertEqual(suites[HARNESS_SUITE], "unset")

    def test_a_missing_tool_skips_them_even_when_the_caller_asked_for_them(self):
        self.tool("go")
        out, suites = self.verify(HARNESS_SELFTEST="1")
        self.assertIn("selftest skipped: npm missing", out.splitlines())
        self.assertEqual(suites[HARNESS_SUITE], "unset")

    def test_the_caller_can_turn_them_off(self):
        self.tool("go")
        self.tool("npm")
        out, suites = self.verify(HARNESS_SELFTEST="0")
        self.assertIn("selftest skipped: HARNESS_SELFTEST=0", out.splitlines())
        self.assertEqual(suites[HARNESS_SUITE], "unset")


class _SilentHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()

    def log_message(self, *args):
        pass


def _closed_port() -> int:
    """A loopback port nothing listens on."""
    with socket.socket() as sock:
        sock.bind((LOOPBACK, 0))
        return sock.getsockname()[1]


# No way out: the CI script is a POSIX shell script; without /bin/sh these tests fail, they do not pass by not running.
class SelftestNeedsMoreThanGoAndNpmTests(unittest.TestCase):
    """go and npm on the PATH are not enough: the tasks build a venv and install from the network.
    The probes of the script are run for real, against servers of this test."""

    tool = SelftestInVerifyScriptTests.tool
    verify = SelftestInVerifyScriptTests.verify

    def setUp(self):
        SelftestInVerifyScriptTests.setUp(self)
        self.tool("python3", PROBING_PYTHON)
        self.tool("go")
        self.tool("npm")
        server = http.server.ThreadingHTTPServer((LOOPBACK, 0), _SilentHandler)
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.reachable = f"http://{LOOPBACK}:{server.server_address[1]}/"
        self.unreachable = f"http://{LOOPBACK}:{_closed_port()}/"

    def test_they_are_replayed_when_venv_and_the_registries_answer(self):
        out, suites = self.verify(HARNESS_SELFTEST_PROBES=self.reachable)
        self.assertEqual(suites[HARNESS_SUITE], "1")
        self.assertNotIn("selftest skipped", out)

    def test_a_python_without_venv_is_named_and_skips_them(self):
        out, suites = self.verify(HARNESS_SELFTEST_PROBES=self.reachable, NO_VENV="1")
        self.assertIn("selftest skipped: python3 venv missing", out.splitlines())
        self.assertEqual(suites[HARNESS_SUITE], "unset")

    def test_a_registry_out_of_reach_is_named_and_skips_them(self):
        out, suites = self.verify(HARNESS_SELFTEST_PROBES=f"{self.reachable} {self.unreachable}")
        self.assertIn(f"selftest skipped: {self.unreachable} unreachable", out.splitlines())
        self.assertEqual(suites[HARNESS_SUITE], "unset")

    def test_a_registry_that_answers_with_an_error_status_is_within_reach(self):
        out, suites = self.verify(HARNESS_SELFTEST_PROBES=self.reachable + "missing")
        self.assertEqual(suites[HARNESS_SUITE], "1")

    def test_turned_off_they_probe_nothing(self):
        out, _ = self.verify(HARNESS_SELFTEST_PROBES=self.unreachable, HARNESS_SELFTEST="0")
        self.assertIn("selftest skipped: HARNESS_SELFTEST=0", out.splitlines())


if __name__ == "__main__":
    unittest.main()
