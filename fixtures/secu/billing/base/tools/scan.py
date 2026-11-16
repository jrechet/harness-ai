#!/usr/bin/env python3
"""In-house static analysis of the billing team. SARIF 2.1 output.

  python3 tools/scan.py --sarif <file>

Two rules: an SQL query built by concatenation (INV-SQL), a command passed to a shell
(INV-SHELL). A line carrying "# nosec" is ignored, as in bandit."""
import argparse
import json
import pathlib
import re

RULES = {
    "INV-SQL": re.compile(r"execute\(\s*(?:f[\"']|\"[^\"]*\"\s*(?:\+|%)|'[^']*'\s*(?:\+|%))"),
    "INV-SHELL": re.compile(r"shell\s*=\s*True|os\.system\("),
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sarif", required=True)
    args = parser.parse_args()
    results = []
    for path in sorted(pathlib.Path("billing").rglob("*.py")):
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if "# nosec" in line:
                continue
            for rule, pattern in RULES.items():
                if pattern.search(line):
                    results.append({"ruleId": rule, "level": "error", "message": {"text": rule},
                                    "locations": [{"physicalLocation": {"artifactLocation": {"uri": path.as_posix()},
                                                                        "region": {"startLine": number}}}]})
    report = {"version": "2.1.0", "runs": [{"tool": {"driver": {"name": "scan-billing"}}, "results": results}]}
    pathlib.Path(args.sarif).write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"{len(results)} result(s) written to {args.sarif}")
    return 1 if results else 0


if __name__ == "__main__":
    raise SystemExit(main())
