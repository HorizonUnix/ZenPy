from __future__ import annotations
import glob
import os
import struct
import subprocess
import threading
import time

DRIVER_PATH = "/sys/kernel/ryzen_smu_drv"
SMN_PATH    = DRIVER_PATH + "/smn"
PCI_CONFIG  = "/sys/bus/pci/devices/0000:00:00.0/config"
NB_ADDR     = 0xB8
NB_DATA     = 0xBC

SMU_OK              = 0x01
SMU_FAILED          = 0xFF
SMU_UNKNOWN_CMD     = 0xFE
SMU_REJECTED_PREREQ = 0xFD
SMU_REJECTED_BUSY   = 0xFC

_NARGS    = 6
_POLL_N   = 100
_SLEEP_S  = 0.0001
_DEADLINE = 1.0
_lock     = threading.Lock()
_backend: str | None = None

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


def secure_boot_enabled() -> bool:
    for path in glob.glob("/sys/firmware/efi/efivars/SecureBoot-*"):
        try:
            with open(path, "rb") as f:
                data = f.read()
            if len(data) >= 5 and data[4] == 1:
                return True
        except OSError:
            pass
    try:
        out = subprocess.run(
            ["mokutil", "--sb-state"],
            capture_output=True, text=True, timeout=3,
        ).stdout.lower()
        return "enabled" in out
    except Exception:
        pass
    return False


def init() -> str:
    global _backend
    if secure_boot_enabled():
        if not os.path.isdir(DRIVER_PATH):
            raise RuntimeError(
                "Secure Boot is enabled but ryzen_smu is not loaded.\n"
                "Install and load the ryzen_smu kernel module before running ZenPy."
            )
        if not os.path.exists(SMN_PATH):
            raise RuntimeError(
                "ryzen_smu is loaded but the /smn interface is missing. "
                "Upgrade to ryzen_smu >= 0.1.7."
            )
        _backend = "ryzen_smu"
    else:
        if not os.path.exists(PCI_CONFIG):
            raise RuntimeError(
                f"PCI config not found at {PCI_CONFIG}. Are you running as root?"
            )
        _backend = "pci"
    return _backend


def active_backend() -> str | None:
    return _backend


def _smn_read(fd: int, addr: int) -> int:
    os.lseek(fd, 0, os.SEEK_SET)
    os.write(fd, struct.pack("<I", addr))
    os.lseek(fd, 0, os.SEEK_SET)
    data = os.read(fd, 4)
    return struct.unpack("<I", data)[0] if len(data) >= 4 else 0


def _smn_write(fd: int, addr: int, value: int) -> None:
    os.lseek(fd, 0, os.SEEK_SET)
    os.write(fd, struct.pack("<II", addr, value))


def _smn_send(fd: int, msg: int, rsp: int, args: int, op: int, arg0: int) -> int:
    _smn_write(fd, rsp, 0)
    _smn_write(fd, args, arg0)
    for i in range(1, _NARGS):
        _smn_write(fd, args + i * 4, 0)
    _smn_write(fd, msg, op)
    for _ in range(_POLL_N):
        r = _smn_read(fd, rsp)
        if r:
            return r
    deadline = time.monotonic() + _DEADLINE
    while time.monotonic() < deadline:
        time.sleep(_SLEEP_S)
        r = _smn_read(fd, rsp)
        if r:
            return r
    return SMU_FAILED


def _pci_read(fd: int, addr: int) -> int:
    os.lseek(fd, NB_ADDR, os.SEEK_SET)
    os.write(fd, struct.pack("<I", addr & ~3))
    os.lseek(fd, NB_DATA, os.SEEK_SET)
    data = os.read(fd, 4)
    return struct.unpack("<I", data)[0] if len(data) >= 4 else 0


def _pci_write(fd: int, addr: int, value: int) -> None:
    os.lseek(fd, NB_ADDR, os.SEEK_SET)
    os.write(fd, struct.pack("<I", addr))
    os.lseek(fd, NB_DATA, os.SEEK_SET)
    os.write(fd, struct.pack("<I", value))


def _pci_send(fd: int, msg: int, rsp: int, args: int, op: int, arg0: int) -> int:
    _pci_write(fd, rsp, 0)
    _pci_write(fd, args, arg0)
    for i in range(1, _NARGS):
        _pci_write(fd, args + i * 4, 0)
    _pci_write(fd, msg, op)
    for _ in range(_POLL_N):
        r = _pci_read(fd, rsp)
        if r:
            return r
    deadline = time.monotonic() + _DEADLINE
    while time.monotonic() < deadline:
        time.sleep(_SLEEP_S)
        r = _pci_read(fd, rsp)
        if r:
            return r
    return SMU_FAILED


def _send(table: dict, default: tuple, family: str, op: int, arg0: int) -> int:
    msg, rsp, args = table.get(family, default)
    with _lock:
        if _backend == "ryzen_smu":
            fd = os.open(SMN_PATH, os.O_RDWR)
            try:
                return _smn_send(fd, msg, rsp, args, op, arg0)
            finally:
                os.close(fd)
        else:
            fd = os.open(PCI_CONFIG, os.O_RDWR)
            try:
                return _pci_send(fd, msg, rsp, args, op, arg0)
            finally:
                os.close(fd)


def send_mp1(family: str, op: int, arg0: int = 0) -> int:
    return _send(_MP1, _MP1_DEFAULT, family, op, arg0)


def send_rsmu(family: str, op: int, arg0: int = 0) -> int:
    return _send(_RSMU, _RSMU_DEFAULT, family, op, arg0)


def pm_table_supported(family: str = "") -> bool:
    return os.path.exists(DRIVER_PATH + "/pm_table")


def read_pm_table_version(family: str = "") -> int:
    try:
        with open(DRIVER_PATH + "/pm_table_version", "rb") as f:
            raw = f.read(4)
        return struct.unpack("<I", raw)[0] if len(raw) >= 4 else 0
    except OSError:
        return 0


def read_pm_table(family: str = "") -> bytes | None:
    size_path = DRIVER_PATH + "/pm_table_size"
    table_path = DRIVER_PATH + "/pm_table"
    try:
        with open(size_path, "rb") as f:
            raw = f.read(8)
        size = struct.unpack("<Q", raw.ljust(8, b"\x00"))[0] if raw else 0
        if not size:
            return None
        with open(table_path, "rb") as f:
            return f.read(size)
    except (OSError, ValueError):
        return None
