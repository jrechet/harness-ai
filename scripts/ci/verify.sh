#!/bin/sh
# What CI checks, called identically by GitHub Actions and by the forge: the YAML only fetches the
# repository and runs this script. Also runs by hand, from the root of the repository.
#   BASE_REF    the target branch of a pull request (origin/main); without it, the gates are not run.
#   GATES_FROM  a folder where the target branch is fetched: the gates then run with ITS code, not
#               with the pull request's, which could have weakened them. PORTES_DE, its former
#               name, is still read.
#   HARNESS_SELFTEST=0  does not replay the fixture task selftests: the way out when they break
#               on a runner for a reason that is not the change. Otherwise they are replayed
#               whenever the machine can: `go` and `npm` on the PATH (npm brings node), a python3
#               with venv and ensurepip, and the package registries within reach. When it cannot,
#               the script prints `selftest skipped:` and the first thing that is missing.
#   HARNESS_SELFTEST_PROBES  the URLs that must answer for the selftests to run, separated by
#               spaces; by default the npm registry and PyPI. Set it on a runner that installs
#               from a mirror.
# The tests necessarily run the code of the pull request: this script runs only on a runner where
# running that code is accepted.
set -eu

python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)' \
  || { echo "Python 3.10 or later is required." >&2; exit 1; }

# The selftests replay every fixture task (untouched repository red, reference solution green,
# tempted solution red) with the projects' own tools. They run with the harness suite only: the
# variable is not exported, so neither the plugin suite nor the gates' second run replays them.
# The folder of this script, which may be the target branch's copy while the tests are the pull request's.
case "$0" in */*) here="${0%/*}" ;; *) here="." ;; esac
selftest_skipped=""
if [ "${HARNESS_SELFTEST:-}" = "0" ]; then
  selftest_skipped="HARNESS_SELFTEST=0"
else
  missing=""
  for tool in go npm; do
    command -v "$tool" >/dev/null 2>&1 || missing="$missing$tool "
  done
  if [ -n "$missing" ]; then
    selftest_skipped="${missing}missing"
  elif ! python3 -c 'import venv, ensurepip' >/dev/null 2>&1; then
    selftest_skipped="python3 venv missing"
  else
    for url in ${HARNESS_SELFTEST_PROBES:-https://registry.npmjs.org/ https://pypi.org/}; do
      if ! python3 "$here/reachable.py" "$url" >/dev/null 2>&1; then
        selftest_skipped="$url unreachable"
        break
      fi
    done
  fi
fi
unset HARNESS_SELFTEST

echo "== Tests of the harness CLI"
if [ -n "$selftest_skipped" ]; then
  echo "selftest skipped: $selftest_skipped"
  python3 -m unittest discover -s cli/tests
else
  HARNESS_SELFTEST=1 python3 -m unittest discover -s cli/tests
fi

echo "== Tests of the ai-sdlc plugin"
python3 -m unittest discover -s plugins/ai-sdlc/cli/tests

if [ -n "${BASE_REF:-}" ]; then
  echo "== The progress plan follows the change"
  python3 cli/harness.py progress check --base "$BASE_REF"
  gates_from="${GATES_FROM:-${PORTES_DE:-}}"
  keys="cli/harness.py"
  if [ -n "$gates_from" ] && [ -f "$gates_from/cli/harnesslib/keys.py" ]; then
    keys="$gates_from/cli/harness.py"
  fi
  echo "== The answer keys do not change with what they grade"
  python3 "$keys" keys check . --base "$BASE_REF"
  gates="plugins/ai-sdlc/cli/ai_sdlc.py"
  if [ -n "$gates_from" ] && [ -f "$gates_from/plugins/ai-sdlc/cli/aisdlclib/ci.py" ]; then
    gates="$gates_from/plugins/ai-sdlc/cli/ai_sdlc.py"
    echo "== Gates of the pull request, run with the code of the target branch"
  else
    echo "== Gates of the pull request, run with the code of the pull request (the target branch does not carry them yet)"
  fi
  python3 "$gates" ci pr . --base "$BASE_REF"
fi
