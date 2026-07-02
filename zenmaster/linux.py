from __future__ import annotations
import glob
import os
import struct
import subprocess
import threading
import time

from zenmaster.errors import BackendUnavailable, SMUNotInitialized
from zenmaster.pmtable import PM_TABLE_CMDS, TABLE_SIZES, DEFAULT_TABLE_SIZE
from zenmaster.mailbox import MP1, MP1_DEFAULT, RSMU, RSMU_DEFAULT, NARGS
from zenmaster.smu import SMU_OK, SMU_FAILED, SMU_REJECTED_PREREQ, ModuleStatus

DRIVER_NAME  = "ryzen_smu"
DRIVER_PATH  = "/sys/kernel/ryzen_smu_drv"
SMN_PATH     = DRIVER_PATH + "/smn"
VERSION_PATH = DRIVER_PATH + "/drv_version"
PCI_CONFIG   = "/sys/bus/pci/devices/0000:00:00.0/config"
NB_ADDR      = 0xB8
NB_DATA      = 0xBC

MIN_VERSION = (0, 1, 7)

_POLL_N   = 100
_SLEEP_S  = 0.0001
_DEADLINE = 1.0
_lock     = threading.Lock()
_backend: str | None = None
_fd: int | None = None


def version_str(v: tuple[int, ...]) -> str:
    return ".".join(str(x) for x in v)


def _parse_version(s: str) -> tuple[int, ...]:
    s = s.strip().lstrip("v")
    try:
        return tuple(int(x) for x in s.split("."))
    except ValueError:
        return (0,)


def module_version() -> str:
    try:
        with open(VERSION_PATH) as f:
            return f.read().strip()
    except OSError:
        return "unknown"


def module_version_ok() -> bool:
    return _parse_version(module_version()) >= MIN_VERSION


def _modinfo() -> str | None:
    try:
        result = subprocess.run(
            ["modinfo", DRIVER_NAME],
            capture_output=True, text=True, timeout=5,
        )
    except Exception:
        return None
    return result.stdout if result.returncode == 0 else None


def module_status() -> ModuleStatus:
    minv = version_str(MIN_VERSION)
    if not os.path.isdir(DRIVER_PATH) and not os.path.exists(VERSION_PATH):
        out = _modinfo()
        if out is None:
            return ModuleStatus(False, "unknown", minv, "not_installed")
        if "sig_id:" not in out and "signer:" not in out:
            return ModuleStatus(False, "unknown", minv, "unsigned")
        return ModuleStatus(False, "unknown", minv, "not_loaded")
    ver = module_version()
    if module_version_ok():
        return ModuleStatus(True, ver, minv, None)
    return ModuleStatus(False, ver, minv, "unknown" if ver == "unknown" else "too_old")


def is_available() -> bool:
    return os.path.isdir(DRIVER_PATH) or active_backend() == "pci"


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


def _pci_writable() -> bool:
    if not os.path.exists(PCI_CONFIG):
        return False
    try:
        fd = os.open(PCI_CONFIG, os.O_RDWR)
        try:
            os.lseek(fd, NB_ADDR, os.SEEK_SET)
            os.write(fd, struct.pack("<I", 0x47))
            os.lseek(fd, NB_ADDR, os.SEEK_SET)
            data = os.read(fd, 4)
            return len(data) >= 4 and struct.unpack("<I", data)[0] == 0x47
        finally:
            os.close(fd)
    except OSError:
        return False


def init() -> str:
    global _backend

    if _backend is not None:
        return _backend

    if secure_boot_enabled():
        if not os.path.isdir(DRIVER_PATH):
            raise BackendUnavailable(
                "Secure Boot is enabled, so PCI direct access is blocked and the "
                "ryzen_smu module is required, but it is not loaded.\n"
                "\n"
                "Options:\n"
                "1. Install ryzen_smu, sign it with a MOK key and enroll it:\n"
                "https://github.com/amkillam/ryzen_smu\n"
                "2. Disable Secure Boot in UEFI firmware settings."
            )
        if not module_version_ok() or not os.path.exists(SMN_PATH):
            raise BackendUnavailable(
                f"ryzen_smu {module_version()} is too old, "
                f"upgrade to >= {version_str(MIN_VERSION)}.\n"
                "https://github.com/amkillam/ryzen_smu"
            )
        _backend = "ryzen_smu"
        return _backend

    if _pci_writable():
        _backend = "pci"
        return _backend

    if os.path.exists(PCI_CONFIG):
        raise BackendUnavailable(
            "Secure Boot is off, so ZenMaster uses PCI direct access, but the PCI "
            "config space is not writable.\n"
            "Run as root, and check that kernel lockdown is off."
        )

    raise BackendUnavailable(
        "PCI direct access is not available.\n"
        f"PCI config not accessible (expected: {PCI_CONFIG})\n"
        "Make sure you are running as root."
    )


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


def _send_seq(write, read, fd: int, msg: int, rsp: int, args: int, op: int, arg0: int) -> int:
    write(fd, rsp, 0)
    write(fd, args, arg0)
    for i in range(1, NARGS):
        write(fd, args + i * 4, 0)
    write(fd, msg, op)
    for _ in range(_POLL_N):
        r = read(fd, rsp)
        if r:
            return r
    deadline = time.monotonic() + _DEADLINE
    while time.monotonic() < deadline:
        time.sleep(_SLEEP_S)
        r = read(fd, rsp)
        if r:
            return r
    return SMU_FAILED


def _require_init() -> None:
    if _backend is None:
        raise SMUNotInitialized("SMU not initialized, call smu.init() first")


def _io_primitives() -> tuple:
    if _backend == "ryzen_smu":
        return _smn_write, _smn_read, SMN_PATH
    return _pci_write, _pci_read, PCI_CONFIG


def _get_fd(path: str) -> int:
    global _fd
    if _fd is None:
        _fd = os.open(path, os.O_RDWR)
    return _fd


def _send(table: dict, default: tuple, family: str, op: int, arg0: int) -> int:
    _require_init()
    msg, rsp, args = table.get(family, default)
    write, read, path = _io_primitives()
    with _lock:
        fd = _get_fd(path)
        return _send_seq(write, read, fd, msg, rsp, args, op, arg0)


def _query(table: dict, default: tuple, family: str, op: int, arg0: int) -> tuple[int, list[int]]:
    _require_init()
    msg, rsp, args = table.get(family, default)
    write, read, path = _io_primitives()
    with _lock:
        fd = _get_fd(path)
        status = _send_seq(write, read, fd, msg, rsp, args, op, arg0)
        return status, [read(fd, args + i * 4) for i in range(NARGS)]


def send_mp1(family: str, op: int, arg0: int = 0) -> int:
    return _send(MP1, MP1_DEFAULT, family, op, arg0)


def send_rsmu(family: str, op: int, arg0: int = 0) -> int:
    return _send(RSMU, RSMU_DEFAULT, family, op, arg0)


def query_mp1(family: str, op: int, arg0: int = 0) -> tuple[int, list[int]]:
    return _query(MP1, MP1_DEFAULT, family, op, arg0)


def query_rsmu(family: str, op: int, arg0: int = 0) -> tuple[int, list[int]]:
    return _query(RSMU, RSMU_DEFAULT, family, op, arg0)


def pm_table_supported(family: str = "") -> bool:
    if os.path.exists(DRIVER_PATH + "/pm_table"):
        return True
    return family in PM_TABLE_CMDS


def _read_devmem(phys: int, size: int) -> bytes | None:
    import mmap
    page = mmap.PAGESIZE
    page_off = phys & ~(page - 1)
    inner = phys - page_off
    try:
        fd = os.open("/dev/mem", os.O_RDONLY | os.O_SYNC)
    except OSError:
        return None
    try:
        mm = mmap.mmap(fd, inner + size, mmap.MAP_SHARED, mmap.PROT_READ, offset=page_off)
        try:
            mm.seek(inner)
            return mm.read(size)
        finally:
            mm.close()
    except (OSError, ValueError):
        return None
    finally:
        os.close(fd)


def _read_pm_table_pci(family: str) -> tuple[bytes, int] | None:
    cmds = PM_TABLE_CMDS.get(family)
    if cmds is None:
        return None
    ver_op, addr_op, transfer_op, addr_64bit, extra = cmds

    status, out = query_rsmu(family, ver_op, 0)
    if status != SMU_OK or not out[0]:
        return None
    ver = out[0]
    size = TABLE_SIZES.get(ver, DEFAULT_TABLE_SIZE)

    status, out = query_rsmu(family, addr_op, extra)
    if status != SMU_OK:
        return None
    phys = (out[1] << 32) | out[0] if addr_64bit else out[0]
    if not phys:
        return None

    status, _ = query_rsmu(family, transfer_op, extra)
    if status == SMU_REJECTED_PREREQ:
        time.sleep(0.01)
        status, _ = query_rsmu(family, transfer_op, extra)
    if status != SMU_OK:
        return None

    data = _read_devmem(phys, size)
    return (data, ver) if data is not None else None


def read_pm_table_full(family: str = "") -> tuple[bytes, int] | None:
    if _backend == "pci":
        return _read_pm_table_pci(family)
    data = read_pm_table(family)
    if data is None:
        return None
    return data, read_pm_table_version(family)


def read_pm_table_version(family: str = "") -> int:
    if _backend == "pci":
        r = _read_pm_table_pci(family)
        return r[1] if r else 0
    try:
        with open(DRIVER_PATH + "/pm_table_version", "rb") as f:
            raw = f.read(4)
        return struct.unpack("<I", raw)[0] if len(raw) >= 4 else 0
    except OSError:
        return 0


def read_pm_table(family: str = "") -> bytes | None:
    if _backend == "pci":
        r = _read_pm_table_pci(family)
        return r[0] if r else None
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


def close() -> None:
    global _backend, _fd
    if _fd is not None:
        try:
            os.close(_fd)
        except OSError:
            pass
        _fd = None
    _backend = None
