import io
import json
from unittest.mock import patch
from zenmaster import update


def _fake_pypi(version):
    payload = json.dumps({"info": {"version": version}}).encode()
    class Resp(io.BytesIO):
        def __enter__(self): return self
        def __exit__(self, *a): self.close()
    return Resp(payload)


def test_ver_tuple():
    assert update._ver_tuple("0.2.0") == (0, 2, 0)
    assert update._ver_tuple("1.10.3") == (1, 10, 3)
    assert update._ver_tuple("0.2.0rc1") == (0, 2, 0)


def test_ver_tuple_orders_correctly():
    assert update._ver_tuple("0.3.0") > update._ver_tuple("0.2.0")
    assert update._ver_tuple("1.0.0") > update._ver_tuple("0.9.9")


def test_latest_version_parses_pypi():
    with patch("urllib.request.urlopen", return_value=_fake_pypi("9.9.9")):
        assert update.latest_version() == "9.9.9"


def test_latest_version_none_on_error():
    with patch("urllib.request.urlopen", side_effect=OSError("no network")):
        assert update.latest_version() is None


def test_check_update_returns_newer():
    with patch("zenmaster.update.latest_version", return_value="99.0.0"):
        assert update.check_update() == "99.0.0"


def test_check_update_none_when_current():
    from zenmaster import __version__
    with patch("zenmaster.update.latest_version", return_value=__version__):
        assert update.check_update() is None


def test_check_update_none_when_older():
    with patch("zenmaster.update.latest_version", return_value="0.0.1"):
        assert update.check_update() is None


def test_check_update_none_on_network_failure():
    with patch("zenmaster.update.latest_version", return_value=None):
        assert update.check_update() is None
