"""Exits 0 when the URL given as argument answers, 1 otherwise. Called by verify.sh before it
replays the fixture task selftests, which install from the network.

Any answer counts, whatever the status: an error status, or a certificate this python does not
know, still shows that the network path exists. urllib follows the proxy variables, as npm and pip
do."""
from __future__ import annotations

import ssl
import sys
import urllib.error
import urllib.request

TIMEOUT_SECONDS = 10


def answers(url: str) -> bool:
    try:
        urllib.request.urlopen(url, timeout=TIMEOUT_SECONDS).close()
    except urllib.error.HTTPError:
        return True
    except urllib.error.URLError as error:
        return isinstance(error.reason, ssl.SSLCertVerificationError)
    except (OSError, ValueError):
        return False
    return True


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("usage: reachable.py <url>")
    sys.exit(0 if answers(sys.argv[1]) else 1)
