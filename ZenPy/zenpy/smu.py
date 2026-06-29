from __future__ import annotations
import platform

SMU_OK              = 0x01
SMU_FAILED          = 0xFF
SMU_UNKNOWN_CMD     = 0xFE
SMU_REJECTED_PREREQ = 0xFD
SMU_REJECTED_BUSY   = 0xFC

_STATUS_NAMES = {
    SMU_OK:              "OK",
    SMU_FAILED:          "Failed",
    SMU_UNKNOWN_CMD:     "Unknown command",
    SMU_REJECTED_PREREQ: "Rejected (prerequisite)",
    SMU_REJECTED_BUSY:   "Rejected (busy)",
}


def status_name(code: int) -> str:
    return _STATUS_NAMES.get(code, f"0x{code:02X}")


def _backend():
    if platform.system() == "Windows":
        from zenpy import windows
        return windows
    from zenpy import linux
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
