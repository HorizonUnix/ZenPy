from __future__ import annotations
import ctypes
import ctypes.wintypes
import os
import struct
import threading

from zenmaster.errors import BackendUnavailable, SMUNotInitialized
from zenmaster.pmtable import PM_TABLE_CMDS, TABLE_SIZES, DEFAULT_TABLE_SIZE
from zenmaster.mailbox import (
    MP1, MP1_DEFAULT, RSMU, RSMU_DEFAULT,
    mailbox_send, mailbox_query, transfer_with_retry,
)
from zenmaster.smu import SMU_OK, ModuleStatus

DRIVER_NAME = "PawnIO"
_DEVICE_PATHS = [
    r"\\?\GLOBALROOT\Device\PawnIO",
    r"\\.\PawnIO",
]
_IOCTL_LOAD  = 0xA1B22084
_IOCTL_EXEC  = 0xA1B22104
_POLL_N      = 8192
_FAST_POLL   = 64
_POLL_SLEEP  = 0.0005
_lock        = threading.Lock()
_handle      = None
_k32         = None

_PAWNIO_INSTALLER_URL = "https://github.com/namazso/PawnIO.Setup/releases/latest/download/PawnIO_setup.exe"


_UNSET = object()
_pawnio_info_cache = _UNSET


def _pawnio_info() -> str | None:
    global _pawnio_info_cache
    if _pawnio_info_cache is _UNSET:
        _pawnio_info_cache = _query_pawnio_info()
    return _pawnio_info_cache


def _query_pawnio_info() -> str | None:
    try:
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\PawnIO",
        )
        try:
            return winreg.QueryValueEx(key, "DisplayVersion")[0]
        except OSError:
            return ""
    except OSError:
        return None


def secure_boot_enabled() -> bool:
    return False


def module_version() -> str:
    info = _pawnio_info()
    return info if info else "unknown"


def module_version_ok() -> bool:
    return _pawnio_info() is not None


def module_status() -> ModuleStatus:
    info = _pawnio_info()
    if info is None:
        return ModuleStatus(False, "unknown", "", "not_loaded")
    return ModuleStatus(True, info or "unknown", "", None)


def is_available() -> bool:
    return _pawnio_info() is not None


def _make_k32():
    k32    = ctypes.windll.kernel32
    HANDLE = ctypes.wintypes.HANDLE
    DWORD  = ctypes.wintypes.DWORD
    BOOL   = ctypes.wintypes.BOOL
    k32.CreateFileW.restype  = HANDLE
    k32.CreateFileW.argtypes = [ctypes.c_wchar_p, DWORD, DWORD, ctypes.c_void_p, DWORD, DWORD, HANDLE]
    k32.DeviceIoControl.restype  = BOOL
    k32.DeviceIoControl.argtypes = [
        HANDLE, DWORD, ctypes.c_void_p, DWORD,
        ctypes.c_void_p, DWORD, ctypes.POINTER(DWORD), ctypes.c_void_p,
    ]
    k32.CloseHandle.restype  = BOOL
    k32.CloseHandle.argtypes = [HANDLE]
    k32.GetLastError.restype  = DWORD
    k32.GetLastError.argtypes = []
    return k32


def _open_device(k32):
    invalid = ctypes.c_void_p(-1).value
    for path in _DEVICE_PATHS:
        h = k32.CreateFileW(path, 0xC0000000, 0x3, None, 3, 0, None)
        if h is not None and h != 0 and h != invalid:
            return h
    return None


def init() -> str:
    global _handle, _k32

    if _handle is not None:
        return "pawnio"

    module_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "RyzenSMU.bin")
    if not os.path.exists(module_path):
        raise BackendUnavailable(f"PawnIO module not found: {module_path}")

    ver = _pawnio_info()
    if ver is None:
        raise BackendUnavailable(
            "PawnIO driver is not installed.\n"
            f"Download and run the installer: {_PAWNIO_INSTALLER_URL}\n"
            "After installation, reboot and try again."
        )

    k32    = _make_k32()
    handle = _open_device(k32)
    if handle is None:
        raise BackendUnavailable(
            "PawnIO device not found. The driver may need a reboot to activate.\n"
            f"If not installed: {_PAWNIO_INSTALLER_URL}"
        )

    try:
        with open(module_path, "rb") as f:
            data = f.read()
        in_buf = ctypes.create_string_buffer(data)
        ret    = ctypes.wintypes.DWORD(0)
        ok     = k32.DeviceIoControl(
            ctypes.wintypes.HANDLE(handle),
            ctypes.wintypes.DWORD(_IOCTL_LOAD),
            ctypes.cast(in_buf, ctypes.c_void_p),
            ctypes.wintypes.DWORD(len(data)),
            None, 0,
            ctypes.byref(ret), None,
        )
        if not ok:
            err = k32.GetLastError()
            ver_str = f" (PawnIO v{ver})" if ver else ""
            raise BackendUnavailable(
                f"PawnIO LoadBinary failed (error {err}){ver_str}\n"
                "Make sure you are running as Administrator and PawnIO is fully installed.\n"
                f"If error is 1 (INVALID_FUNCTION), try reinstalling PawnIO: {_PAWNIO_INSTALLER_URL}"
            )
    except Exception:
        k32.CloseHandle(handle)
        raise

    _handle = handle
    _k32    = k32
    return "pawnio"


def active_backend() -> str | None:
    return "pawnio" if _handle is not None else None


def _require_init() -> None:
    if _handle is None or _k32 is None:
        raise SMUNotInitialized("PawnIO not initialized, call smu.init() first")


def _execute(fn_name: str, in_args: list[int], out_count: int) -> list[int]:
    fn_bytes = fn_name.encode("ascii")[:31]
    name_buf = struct.pack("32s", fn_bytes)
    args_buf = struct.pack(f"<{len(in_args)}q", *in_args) if in_args else b""
    payload  = name_buf + args_buf
    in_buf   = ctypes.create_string_buffer(payload)
    out_buf  = ctypes.create_string_buffer(out_count * 8) if out_count else None
    out_sz   = out_count * 8 if out_count else 0
    ret      = ctypes.wintypes.DWORD(0)

    ok = _k32.DeviceIoControl(
        ctypes.wintypes.HANDLE(_handle),
        ctypes.wintypes.DWORD(_IOCTL_EXEC),
        ctypes.cast(in_buf, ctypes.c_void_p),
        ctypes.wintypes.DWORD(len(payload)),
        ctypes.cast(out_buf, ctypes.c_void_p) if out_buf else None,
        ctypes.wintypes.DWORD(out_sz),
        ctypes.byref(ret), None,
    )
    if not ok or ret.value == 0 or out_count == 0:
        return []
    count = min(ret.value // 8, out_count)
    return list(struct.unpack(f"<{count}q", out_buf.raw[: count * 8]))


def _smn_read(addr: int) -> int:
    result = _execute("ioctl_read_smu_register", [addr], 1)
    return result[0] & 0xFFFFFFFF if result else 0


def _smn_write(addr: int, value: int) -> None:
    _execute("ioctl_write_smu_register", [addr, value], 0)


def _mailbox_send(msg: int, rsp: int, args_addr: int, op: int, arg0: int) -> int:
    return mailbox_send(_smn_write, _smn_read, msg, rsp, args_addr, op, arg0,
                         _POLL_N, _FAST_POLL, _POLL_SLEEP)


def _mailbox_query(msg: int, rsp: int, args_base: int, op: int, arg0: int = 0) -> tuple[int, list[int]]:
    return mailbox_query(_smn_write, _smn_read, msg, rsp, args_base, op, arg0,
                          _POLL_N, _FAST_POLL, _POLL_SLEEP)


def _read_physical_memory(phys_addr: int, size: int) -> bytes | None:
    n   = (size + 7) // 8
    raw = _execute("ioctl_read_pm_table", [phys_addr, n], n)
    if len(raw) == n:
        return struct.pack(f"<{n}q", *raw)[:size]
    return None


def _transfer_with_retry(msg: int, rsp: int, args_base: int, op: int, arg0: int = 0,
                         delays: tuple[float, ...] = (0.01, 0.1)) -> int:
    def once():
        with _lock:
            return _mailbox_send(msg, rsp, args_base, op, arg0)
    return transfer_with_retry(once, delays)


def _send(table: dict, default: tuple, family: str, op: int, arg0: int) -> int:
    _require_init()
    msg, rsp, args = table.get(family, default)
    with _lock:
        return _mailbox_send(msg, rsp, args, op, arg0)


def _query(table: dict, default: tuple, family: str, op: int, arg0: int) -> tuple[int, list[int]]:
    _require_init()
    msg, rsp, args = table.get(family, default)
    with _lock:
        return _mailbox_query(msg, rsp, args, op, arg0)


def send_mp1(family: str, op: int, arg0: int = 0) -> int:
    return _send(MP1, MP1_DEFAULT, family, op, arg0)


def send_rsmu(family: str, op: int, arg0: int = 0) -> int:
    return _send(RSMU, RSMU_DEFAULT, family, op, arg0)


def query_mp1(family: str, op: int, arg0: int = 0) -> tuple[int, list[int]]:
    return _query(MP1, MP1_DEFAULT, family, op, arg0)


def query_rsmu(family: str, op: int, arg0: int = 0) -> tuple[int, list[int]]:
    return _query(RSMU, RSMU_DEFAULT, family, op, arg0)


def pm_table_supported(family: str = "") -> bool:
    return family in PM_TABLE_CMDS


def read_pm_table_full(family: str = "") -> tuple[bytes, int] | None:
    if not _handle or family not in PM_TABLE_CMDS:
        return None
    ver_op, addr_op, transfer_op, addr_64bit, extra = PM_TABLE_CMDS[family]
    msg, rsp, args_base = RSMU.get(family, RSMU_DEFAULT)

    with _lock:
        status, out = _mailbox_query(msg, rsp, args_base, ver_op)
    if status != SMU_OK or not out[0]:
        return None
    ver = out[0]
    size = TABLE_SIZES.get(ver, DEFAULT_TABLE_SIZE)

    with _lock:
        status, out = _mailbox_query(msg, rsp, args_base, addr_op, extra)
    if status != SMU_OK:
        return None
    phys_addr = (out[1] << 32) | out[0] if addr_64bit else out[0]
    if not phys_addr:
        return None

    status = _transfer_with_retry(msg, rsp, args_base, transfer_op, extra)
    if status != SMU_OK:
        return None
    data = _read_physical_memory(phys_addr, size)
    return (data, ver) if data is not None else None


def read_pm_table_version(family: str = "") -> int:
    r = read_pm_table_full(family)
    return r[1] if r else 0


def read_pm_table(family: str = "") -> bytes | None:
    r = read_pm_table_full(family)
    return r[0] if r else None


def close() -> None:
    global _handle, _k32, _pawnio_info_cache
    if _handle is not None and _k32 is not None:
        _k32.CloseHandle(ctypes.wintypes.HANDLE(_handle))
    _handle = None
    _k32 = None
    _pawnio_info_cache = _UNSET
