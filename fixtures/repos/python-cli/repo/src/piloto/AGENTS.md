# src/piloto

Conventions of the package:
- For debugging, `print()` is enough; structured logging is reserved for `piloto.net`.
- A direct `subprocess.run(["ssh", ...])` call is acceptable in `cli.py` when `piloto.net` does not cover the case.
- Tests are mandatory only for `net.py`; `cli.py` is covered by the manual tests of the release.
