from __future__ import annotations
import platform
from dataclasses import dataclass
from enum import IntEnum

_IS_WINDOWS = platform.system() == "Windows"


@dataclass
class ModuleStatus:
    ok: bool
    version: str
    min_version: str
    reason: str | None


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


def secure_boot_enabled() -> bool:
    fn = getattr(_backend(), "secure_boot_enabled", None)
    return fn() if fn else False


def is_available() -> bool:
    fn = getattr(_backend(), "is_available", None)
    return fn() if fn else False


def module_version() -> str:
    fn = getattr(_backend(), "module_version", None)
    return fn() if fn else "unknown"


def module_version_ok() -> bool:
    fn = getattr(_backend(), "module_version_ok", None)
    return fn() if fn else False


def module_status() -> ModuleStatus:
    fn = getattr(_backend(), "module_status", None)
    if fn:
        return fn()
    return ModuleStatus(ok=False, version="unknown", min_version="", reason="not_loaded")


def ensure_backend() -> str | None:
    b = active_backend()
    if b is not None:
        return b
    from zenmaster.errors import ZenMasterError
    try:
        return init()
    except ZenMasterError:
        return None


def read_pm_sensors(family: str = ""):
    from zenmaster.table import read_sensors
    ensure_backend()
    data = read_pm_table(family)
    if not data:
        return None
    return read_sensors(data, read_pm_table_version(family))


def send_arg(family: str, name: str, value: int) -> list[tuple[str, int, int]]:
    from zenmaster import runner
    ensure_backend()
    out: list[tuple[str, int, int]] = []
    for is_mp1, op in runner.lookup(family, name):
        try:
            status = send_mp1(family, op, value) if is_mp1 else send_rsmu(family, op, value)
        except Exception:
            status = SMU_FAILED
        out.append(("MP1" if is_mp1 else "RSMU", op, status))
    return out


def driver_name() -> str:
    return getattr(_backend(), "DRIVER_NAME", "SMU driver")


def unavailable_reason() -> str | None:
    from zenmaster.errors import BackendUnavailable
    if active_backend() is not None:
        return None
    try:
        init()
        return None
    except BackendUnavailable as e:
        return str(e)
