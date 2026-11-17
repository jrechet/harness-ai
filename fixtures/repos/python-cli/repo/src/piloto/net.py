"""Network access: a single gateway, with a timeout."""
from __future__ import annotations

import paramiko

DEFAULT_TIMEOUT = 30.0


def connect(host: str, user: str, timeout: float = DEFAULT_TIMEOUT) -> paramiko.SSHClient:
    client = paramiko.SSHClient()
    client.load_system_host_keys()
    client.connect(host, username=user, timeout=timeout)
    return client


def push(client: paramiko.SSHClient, local: str, remote: str) -> None:
    sftp = client.open_sftp()
    try:
        sftp.put(local, remote)
    finally:
        sftp.close()
