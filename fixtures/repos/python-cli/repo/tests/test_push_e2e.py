import pytest

from piloto import cli


@pytest.mark.slow
def test_push_against_local_sshd(tmp_path) -> None:  # type: ignore[no-untyped-def]
    # Nécessite un serveur SSH local ; déselectionné par addopts, donc jamais exécuté en CI.
    f = tmp_path / "x.conf"
    f.write_text("a=1\n")
    assert cli.main(["push", "localhost", "test", str(f), "/tmp/x.conf"]) == 0
