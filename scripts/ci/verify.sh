#!/bin/sh
# What CI checks, called identically by GitHub Actions and by the forge: the YAML only fetches the
# repository and runs this script. Also runs by hand, from the root of the repository.
#   BASE_REF    the target branch of a pull request (origin/main); without it, the gates are not run.
#   GATES_FROM  a folder where the target branch is fetched: the gates then run with ITS code, not
#               with the pull request's, which could have weakened them. PORTES_DE, its former
#               name, is still read.
# The tests necessarily run the code of the pull request: this script runs only on a runner where
# running that code is accepted.
set -eu

python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)' \
  || { echo "Python 3.10 or later is required." >&2; exit 1; }

echo "== Tests of the harness CLI"
python3 -m unittest discover -s cli/tests

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
