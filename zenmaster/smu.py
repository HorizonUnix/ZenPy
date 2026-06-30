from __future__ import annotations
import platform
from enum import IntEnum

_IS_WINDOWS = platform.system() == "Windows"


class SmuStatus(IntEnum):
    OK              = 0x01
    FAILED          = 0xFF
    UNKNOWN_CMD     = 0xFE
    REJECTED_PREREQ = 0xFD
    REJECTED_BUSY   = 0xFC


SMU_OK              = SmuStatus.OK
SMU_FAILED          = SmuStatus.FAILED
SMU_UNKNOWN_CMD     = SmuStatus.UNKNOWN_CMD
SMU_REJECTED_PREREQ = SmuStatus.REJECTED_PREREQ
SMU_REJECTED_BUSY   = SmuStatus.REJECTED_BUSY

_STATUS_NAMES = {
    SmuStatus.OK:              "OK",
    SmuStatus.FAILED:          "Failed",
    SmuStatus.UNKNOWN_CMD:     "Unknown command",
    SmuStatus.REJECTED_PREREQ: "Rejected (prerequisite)",
    SmuStatus.REJECTED_BUSY:   "Rejected (busy)",
}


def status_name(code: int) -> str:
    return _STATUS_NAMES.get(code, f"0x{code:02X}")


def _backend():
    if _IS_WINDOWS:
        from zenmaster import windows
        return windows
    from zenmaster import linux
    return linux


def init() -> str:
    return _backend().init()


def active_backend() -> str | None:
    b = _backend()
    fn = getattr(b, "active_backend", None)
    return fn() if fn else None


def send_mp1(family: str, op: int, arg0: int = 0) -> int:
    return _backend().send_mp1(family, op, arg0)


def send_rsmu(family: str, op: int, arg0: int = 0) -> int:
    return _backend().send_rsmu(family, op, arg0)


def query_mp1(family: str, op: int, arg0: int = 0) -> tuple[int, list[int]]:
    return _backend().query_mp1(family, op, arg0)


def query_rsmu(family: str, op: int, arg0: int = 0) -> tuple[int, list[int]]:
    return _backend().query_rsmu(family, op, arg0)


def pm_table_supported(family: str = "") -> bool:
    b = _backend()
    fn = getattr(b, "pm_table_supported", None)
    return fn(family) if fn else False


def read_pm_table(family: str = "") -> bytes | None:
    b = _backend()
    fn = getattr(b, "read_pm_table", None)
    return fn(family) if fn else None


def read_pm_table_version(family: str = "") -> int:
    b = _backend()
    fn = getattr(b, "read_pm_table_version", None)
    return fn(family) if fn else 0
