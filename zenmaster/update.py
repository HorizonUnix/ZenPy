from __future__ import annotations
import json
import urllib.request

_PYPI_URL = "https://pypi.org/pypi/zenmaster/json"


def _ver_tuple(v: str) -> tuple[int, ...]:
    out = []
    for part in v.split("."):
        digits = ""
        for ch in part:
            if not ch.isdigit():
                break
            digits += ch
        out.append(int(digits) if digits else 0)
    return tuple(out)


def latest_version(timeout: float = 3.0) -> str | None:
    try:
        with urllib.request.urlopen(_PYPI_URL, timeout=timeout) as resp:
            return json.load(resp)["info"]["version"]
    except Exception:
        return None


def check_update(timeout: float = 3.0) -> str | None:
    from zenmaster import __version__
    latest = latest_version(timeout)
    if latest and _ver_tuple(latest) > _ver_tuple(__version__):
        return latest
    return None
