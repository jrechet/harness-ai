"""Point d'entrée `piloto`."""
from __future__ import annotations

import argparse
import subprocess
import sys

from piloto import __version__, net


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="piloto")
    sub = parser.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("push")
    p.add_argument("host")
    p.add_argument("user")
    p.add_argument("local")
    p.add_argument("remote")
    d = sub.add_parser("diff")
    d.add_argument("host")
    d.add_argument("user")
    d.add_argument("remote")
    sub.add_parser("version")
    args = parser.parse_args(argv)

    if args.cmd == "version":
        print(__version__)
        return 0
    if args.cmd == "push":
        client = net.connect(args.host, args.user)
        net.push(client, args.local, args.remote)
        print("ok")
        return 0
    if args.cmd == "diff":
        # Cas non couvert par piloto.net : on passe par ssh directement.
        out = subprocess.run(["ssh", f"{args.user}@{args.host}", "cat", args.remote], capture_output=True, text=True)
        print(out.stdout)
        return out.returncode
    return 1


if __name__ == "__main__":
    sys.exit(main())
