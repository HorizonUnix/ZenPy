from __future__ import annotations
import ctypes
import ctypes.wintypes
import os
import struct
import threading
import time

SMU_OK              = 0x01
SMU_FAILED          = 0xFF
SMU_UNKNOWN_CMD     = 0xFE
SMU_REJECTED_PREREQ = 0xFD
SMU_REJECTED_BUSY   = 0xFC

_DEVICE_PATHS = [
    r"\\?\GLOBALROOT\Device\PawnIO",
    r"\\.\PawnIO",
]
_IOCTL_LOAD  = 0xA1B22084
_IOCTL_EXEC  = 0xA1B22104
_NARGS       = 6
_POLL_N      = 8192
_FAST_POLL   = 64
_POLL_SLEEP  = 0.0005
_lock        = threading.Lock()
_handle      = None
_k32         = None

_PM_TABLE_FAMILIES = {
    "Renoir", "Lucienne", "Cezanne_Barcelo", "Rembrandt",
    "PhoenixPoint", "PhoenixPoint2", "HawkPoint", "HawkPoint2",
    "SonomaValley", "StrixPoint", "KrackanPoint", "KrackanPoint2", "StrixHalo",
}
_TABLE_ADDR_64BIT = {
    "Rembrandt", "PhoenixPoint", "PhoenixPoint2", "HawkPoint", "HawkPoint2",
    "SonomaValley", "StrixPoint", "KrackanPoint", "KrackanPoint2", "StrixHalo",
}
_TABLE_VER_OP      = {f: 0x06 for f in _PM_TABLE_FAMILIES}
_TABLE_ADDR_OP     = {f: 0x66 for f in _PM_TABLE_FAMILIES}
_TABLE_TRANSFER_OP = {f: 0x65 for f in _PM_TABLE_FAMILIES}

_TABLE_SIZES: dict[int, int] = {
    0x001E0001: 0x568, 0x001E0002: 0x580, 0x001E0003: 0x578,
    0x001E0004: 0x608, 0x001E0005: 0x608, 0x001E000A: 0x608, 0x001E0101: 0x608,
    0x00370000: 0x794, 0x00370001: 0x884, 0x00370002: 0x88C,
    0x00370003: 0x8AC, 0x00370004: 0x8AC, 0x00370005: 0x8C8,
    0x003F0000: 0x7AC,
    0x00400001: 0x910, 0x00400002: 0x928, 0x00400003: 0x94C,
    0x00400004: 0x944, 0x00400005: 0x944,
    0x00450004: 0xAA4, 0x00450005: 0xAB0,
    0x004C0003: 0xB18, 0x004C0004: 0xB1C, 0x004C0005: 0xAF8,
    0x004C0006: 0xAFC, 0x004C0007: 0xB00, 0x004C0008: 0xAF0, 0x004C0009: 0xB00,
    0x005D0008: 0xD54, 0x005D0009: 0xD54, 0x005D000B: 0xD54,
    0x0064020C: 0xE50,
}

_MP1: dict[str, tuple[int, int, int]] = {
    "SummitRidge":   (0x3B10528, 0x3B10564, 0x3B10598),
    "PinnacleRidge": (0x3B10528, 0x3B10564, 0x3B10598),
    "Matisse":       (0x3B10530, 0x3B1057C, 0x3B109C4),
    "Vermeer":       (0x3B10530, 0x3B1057C, 0x3B109C4),
    "VanGogh":       (0x3B10528, 0x3B10578, 0x3B10998),
    "Mendocino":     (0x3B10528, 0x3B10578, 0x3B10998),
    "Rembrandt":     (0x3B10528, 0x3B10578, 0x3B10998),
    "PhoenixPoint":  (0x3B10528, 0x3B10578, 0x3B10998),
    "PhoenixPoint2": (0x3B10528, 0x3B10578, 0x3B10998),
    "HawkPoint":     (0x3B10528, 0x3B10578, 0x3B10998),
    "HawkPoint2":    (0x3B10528, 0x3B10578, 0x3B10998),
    "SonomaValley":  (0x3B10528, 0x3B10578, 0x3B10998),
    "Raphael":       (0x3B10530, 0x3B1057C, 0x3B109C4),
    "DragonRange":   (0x3B10530, 0x3B1057C, 0x3B109C4),
    "GraniteRidge":  (0x3B10530, 0x3B1057C, 0x3B109C4),
    "FireRange":     (0x3B10530, 0x3B1057C, 0x3B109C4),
    "StrixPoint":    (0x3B10928, 0x3B10978, 0x3B10998),
    "KrackanPoint":  (0x3B10928, 0x3B10978, 0x3B10998),
    "KrackanPoint2": (0x3B10928, 0x3B10978, 0x3B10998),
    "StrixHalo":     (0x3B10928, 0x3B10978, 0x3B10998),
}
_MP1_DEFAULT = (0x3B10528, 0x3B10564, 0x3B10998)

_RSMU: dict[str, tuple[int, int, int]] = {
    "SummitRidge":   (0x3B1051C, 0x3B10568, 0x3B10590),
    "PinnacleRidge": (0x3B1051C, 0x3B10568, 0x3B10590),
    "Matisse":       (0x3B10524, 0x3B10570, 0x3B10A40),
    "Vermeer":       (0x3B10524, 0x3B10570, 0x3B10A40),
    "Raphael":       (0x3B10524, 0x3B10570, 0x3B10A40),
    "DragonRange":   (0x3B10524, 0x3B10570, 0x3B10A40),
    "GraniteRidge":  (0x3B10524, 0x3B10570, 0x3B10A40),
    "FireRange":     (0x3B10524, 0x3B10570, 0x3B10A40),
}
_RSMU_DEFAULT = (0x3B10A20, 0x3B10A80, 0x3B10A88)

_PAWNIO_INSTALLER_URL = "https://github.com/namazso/PawnIO.Setup/releases/latest/download/PawnIO_setup.exe"


def _assets_dir() -> str:
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")


def _pawnio_info() -> str | None:
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

    module_path = os.path.join(_assets_dir(), "AMD", "PawnIO", "RyzenSMU.bin")
    if not os.path.exists(module_path):
        raise RuntimeError(f"PawnIO module not found: {module_path}")

    ver = _pawnio_info()
    if ver is None:
        raise RuntimeError(
            "PawnIO driver is not installed.\n"
            f"Download and run the installer: {_PAWNIO_INSTALLER_URL}\n"
            "After installation, reboot and try again."
        )

    k32    = _make_k32()
    handle = _open_device(k32)
    if handle is None:
        raise RuntimeError(
            "PawnIO device not found — driver may need a reboot to activate.\n"
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
            raise RuntimeError(
                f"PawnIO LoadBinary failed (error {err}){ver_str}\n"
                "  Make sure you are running as Administrator and PawnIO is fully installed.\n"
                f"  If error is 1 (INVALID_FUNCTION), try reinstalling PawnIO: {_PAWNIO_INSTALLER_URL}"
            )
    except Exception:
        k32.CloseHandle(handle)
        raise

    _handle = handle
    _k32    = k32
    return "pawnio"


def active_backend() -> str | None:
    return "pawnio" if _handle is not None else None


def _execute(fn_name: str, in_args: list[int], out_count: int) -> list[int]:
    if _handle is None or _k32 is None:
        raise RuntimeError("PawnIO not initialised — call smu.init() first")
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
    return list(struct.unpack(f"<{count}q", out_buf.raw[: count * 8])) + [0] * (out_count - count)


def _smn_read(addr: int) -> int:
    result = _execute("ioctl_read_smu_register", [addr], 1)
    return result[0] & 0xFFFFFFFF if result else 0


def _smn_write(addr: int, value: int) -> None:
    _execute("ioctl_write_smu_register", [addr, value], 0)


def _mailbox_send(msg: int, rsp: int, args_addr: int, op: int, arg0: int) -> int:
    _smn_write(rsp, 0)
    _smn_write(args_addr, arg0)
    for i in range(1, _NARGS):
        _smn_write(args_addr + i * 4, 0)
    _smn_write(msg, op)
    for i in range(_POLL_N):
        r = _smn_read(rsp)
        if r:
            return r
        if i >= _FAST_POLL:
            time.sleep(_POLL_SLEEP)
    return SMU_FAILED


def _mailbox_query(msg: int, rsp: int, args_base: int, op: int) -> tuple[int, list[int]]:
    _smn_write(rsp, 0)
    for i in range(_NARGS):
        _smn_write(args_base + i * 4, 0)
    _smn_write(msg, op)
    for i in range(_POLL_N):
        r = _smn_read(rsp)
        if r:
            return r, [_smn_read(args_base + i * 4) for i in range(_NARGS)]
        if i >= _FAST_POLL:
            time.sleep(_POLL_SLEEP)
    return SMU_FAILED, [0] * _NARGS


def _read_physical_memory(phys_addr: int, size: int) -> bytes | None:
    n   = (size + 7) // 8
    raw = _execute("ioctl_read_pm_table", [phys_addr, n], n)
    if raw and any(raw):
        return struct.pack(f"<{len(raw)}q", *raw)[:size]
    return None


def _send(table: dict, default: tuple, family: str, op: int, arg0: int) -> int:
    msg, rsp, args = table.get(family, default)
    with _lock:
        return _mailbox_send(msg, rsp, args, op, arg0)


def send_mp1(family: str, op: int, arg0: int = 0) -> int:
    return _send(_MP1, _MP1_DEFAULT, family, op, arg0)


def send_rsmu(family: str, op: int, arg0: int = 0) -> int:
    return _send(_RSMU, _RSMU_DEFAULT, family, op, arg0)


def pm_table_supported(family: str = "") -> bool:
    return family in _PM_TABLE_FAMILIES


def read_pm_table_version(family: str = "") -> int:
    if not _handle or family not in _PM_TABLE_FAMILIES:
        return 0
    msg, rsp, args_base = _RSMU.get(family, _RSMU_DEFAULT)
    with _lock:
        status, out = _mailbox_query(msg, rsp, args_base, _TABLE_VER_OP[family])
    return out[0] if status == SMU_OK else 0


def read_pm_table(family: str = "") -> bytes | None:
    if not _handle or family not in _PM_TABLE_FAMILIES:
        return None
    msg, rsp, args_base = _RSMU.get(family, _RSMU_DEFAULT)

    with _lock:
        status, out = _mailbox_query(msg, rsp, args_base, _TABLE_VER_OP[family])
    if status != SMU_OK:
        return None
    size = _TABLE_SIZES.get(out[0], 0x1000)

    with _lock:
        status, out = _mailbox_query(msg, rsp, args_base, _TABLE_ADDR_OP[family])
    if status != SMU_OK:
        return None
    phys_addr = (out[1] << 32) | out[0] if family in _TABLE_ADDR_64BIT else out[0]

    with _lock:
        status = _mailbox_send(msg, rsp, args_base, _TABLE_TRANSFER_OP[family], 0)
    if status == SMU_REJECTED_PREREQ:
        time.sleep(0.01)
        with _lock:
            status = _mailbox_send(msg, rsp, args_base, _TABLE_TRANSFER_OP[family], 0)
        if status == SMU_REJECTED_PREREQ:
            time.sleep(0.1)
            with _lock:
                status = _mailbox_send(msg, rsp, args_base, _TABLE_TRANSFER_OP[family], 0)

    if status != SMU_OK:
        return None
    return _read_physical_memory(phys_addr, size)
