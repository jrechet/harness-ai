#!/usr/bin/env python3
"""The PreToolUse hook of the ai-sdlc plugin: refuses a shell command that tags, publishes or deploys, whatever
the tool that carries it, and a write that puts the variable of the guardrail's gate in `.claude/settings*.json`.

Reads the tool call as JSON on standard input. Exits 2 with the reason on standard error to refuse, 0 to let
it through. Imports only the guardrail module: it starts fast, and an error elsewhere in the plugin does not
bring it down. If it falls anyway, it judges the call on its text instead of opening the door."""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
_LAST_RESORT = re.compile(r"git\s[^\n;&|]{0,200}tag\s+v?\d|push[^\n;&|]{0,200}--tags|gh\s+release\s+create|\b(?:npm|cargo|pnpm|yarn)\s+publish|"
                          r"\b(?:kubectl|terraform)\s+apply|\bhelm\s+(?:install|upgrade)|\bmake\s+(?:deploy|release|livr)")
_ALLOW = ("AI_SDLC_ALLOW_AGENT_DELIVERY", "AI_SDLC_LIVRAISON_PAR_AGENT")   # the former name is still read


def main() -> int:
    raw = ""
    try:
        raw = sys.stdin.buffer.read(5_000_001).decode("utf-8", "replace")
        from aisdlclib import guard
        code, message = guard.run_hook(raw, dict(os.environ))
    except Exception:   # noqa: BLE001 — never a trace: a hook that crashes lets through
        opens_gate = ".claude/settings" in raw and any(name in raw for name in _ALLOW)   # the gate written into the agent's settings
        if any(os.environ.get(name) == "1" for name in _ALLOW) or not (_LAST_RESORT.search(raw) or opens_gate):
            return 0
        code, message = 2, ("ai-sdlc: the guardrail could not read this call, and its text looks like a delivery or like a write of "
                            "the guardrail's own gate. Call refused.\n")
    sys.stderr.write(message)
    return code


if __name__ == "__main__":
    sys.exit(main())
