from piloto import net


def test_default_timeout_is_bounded() -> None:
    assert 0 < net.DEFAULT_TIMEOUT <= 60
