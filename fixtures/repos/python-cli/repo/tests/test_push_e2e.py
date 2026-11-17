import pytest

from piloto import cli


@pytest.mark.slow
def test_push_against_local_sshd(tmp_path) -> None:  # type: ignore[no-untyped-def]
    # Needs a local SSH server; deselected by addopts, so never run in CI.
    f = tmp_path / "x.conf"
    f.write_text("a=1\n")
    assert cli.main(["push", "localhost", "test", str(f), "/tmp/x.conf"]) == 0
