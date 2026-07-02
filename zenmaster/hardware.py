from __future__ import annotations
import os
import platform
from dataclasses import dataclass
from functools import lru_cache


@dataclass
class CpuInfo:
    name: str
    arch: str
    family: str
    type: str
    cpu_family_int: int
    cpu_model_int: int
    cpu_stepping_int: int = 0


def _parse_cpuinfo() -> tuple[int, int, int, str]:
    cpu_family = cpu_model = cpu_stepping = 0
    cpu_name = ""
    seen_family = seen_model = seen_stepping = False
    try:
        with open("/proc/cpuinfo") as f:
            for line in f:
                if ":" not in line:
                    continue
                key, _, val = line.partition(":")
                key, val = key.strip(), val.strip()
                if key == "cpu family" and not seen_family:
                    cpu_family = int(val)
                    seen_family = True
                elif key == "model" and not seen_model:
                    cpu_model = int(val)
                    seen_model = True
                elif key == "stepping" and not seen_stepping:
                    cpu_stepping = int(val)
                    seen_stepping = True
                elif key == "model name" and not cpu_name:
                    cpu_name = val
                if seen_family and seen_model and seen_stepping and cpu_name:
                    break
    except OSError:
        pass
    return cpu_family, cpu_model, cpu_stepping, cpu_name


def _parse_processor_identifier() -> tuple[int, int, int, str]:
    identifier = os.environ.get("PROCESSOR_IDENTIFIER", "")
    words = identifier.split()
    cpu_family = cpu_model = cpu_stepping = 0
    try:
        fi = words.index("Family") + 1
        mi = words.index("Model") + 1
        cpu_family = int(words[fi])
        cpu_model = int(words[mi].rstrip(","))
    except (ValueError, IndexError):
        pass
    try:
        si = words.index("Stepping") + 1
        cpu_stepping = int(words[si].rstrip(","))
    except (ValueError, IndexError):
        pass

    cpu_name = ""
    try:
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            r"HARDWARE\DESCRIPTION\System\CentralProcessor\0",
        )
        cpu_name = winreg.QueryValueEx(key, "ProcessorNameString")[0].strip()
        winreg.CloseKey(key)
    except Exception:
        pass
    if not cpu_name:
        cpu_name = identifier
    return cpu_family, cpu_model, cpu_stepping, cpu_name


_libc = None


def _libSystem():
    global _libc
    if _libc is None:
        import ctypes
        _libc = ctypes.CDLL("/usr/lib/libSystem.B.dylib")
    return _libc


def _sysctl_str(name: str) -> str:
    import ctypes
    libc = _libSystem()
    size = ctypes.c_size_t(0)
    if libc.sysctlbyname(name.encode(), None, ctypes.byref(size), None, 0) != 0:
        return ""
    buf = ctypes.create_string_buffer(size.value)
    if libc.sysctlbyname(name.encode(), buf, ctypes.byref(size), None, 0) != 0:
        return ""
    return buf.value.decode(errors="replace").strip()


def _sysctl_int(name: str) -> int:
    import ctypes
    libc = _libSystem()
    val  = ctypes.c_uint64(0)
    size = ctypes.c_size_t(ctypes.sizeof(val))
    if libc.sysctlbyname(name.encode(), ctypes.byref(val), ctypes.byref(size), None, 0) != 0:
        return 0
    return int(val.value)


def _parse_sysctl() -> tuple[int, int, int, str]:
    name = _sysctl_str("machdep.cpu.brand_string")
    return (
        _sysctl_int("machdep.cpu.family"),
        _sysctl_int("machdep.cpu.model"),
        _sysctl_int("machdep.cpu.stepping"),
        name,
    )


def _resolve_codename(cpu_name: str, cpu_family: int, cpu_model: int) -> tuple[str, str]:
    if "Intel" in cpu_name:
        return "Intel", "Intel"

    arch = family = "Unknown"

    if cpu_family == 23:
        arch = "Zen 1 - Zen 2"
        match cpu_model:
            case 1:         family = "SummitRidge"
            case 8:         family = "PinnacleRidge"
            case 17 | 18:   family = "RavenRidge"
            case 24:        family = "Picasso"
            case 32:        family = "Pollock" if any(s in cpu_name for s in ("15e", "15Ce", "20e")) else "Dali"
            case 80:        family = "FireFlight"
            case 96:        family = "Renoir"
            case 104:       family = "Lucienne"
            case 113:       family = "Matisse"
            case 144 | 145: family = "VanGogh"
            case 160:       family = "Mendocino"

    elif cpu_family == 25:
        arch = "Zen 3 - Zen 4"
        match cpu_model:
            case 33:        family = "Vermeer"
            case 63 | 68:   family = "Rembrandt"
            case 80:        family = "Cezanne_Barcelo"
            case 97:        family = "DragonRange" if "HX" in cpu_name else "Raphael"
            case 116:       family = "PhoenixPoint"
            case 120:       family = "PhoenixPoint2"
            case 117:       family = "HawkPoint"
            case 124:       family = "HawkPoint2"

    elif cpu_family == 26:
        arch = "Zen 5 - Zen 6"
        match cpu_model:
            case 68:        family = "FireRange" if "HX" in cpu_name else "GraniteRidge"
            case 96:        family = "KrackanPoint"
            case 104:       family = "KrackanPoint2"
            case 32 | 36:   family = "StrixPoint"
            case 112:       family = "StrixHalo"

    return arch, family


_DESKTOP_FAMILIES = {
    "SummitRidge", "PinnacleRidge", "Matisse",
    "Vermeer", "Raphael", "GraniteRidge",
}


def _cpu_type(family: str, arch: str) -> str:
    if family in _DESKTOP_FAMILIES:
        return "Amd_Desktop_Cpu"
    if arch in ("Intel", "Unknown"):
        return arch
    return "Amd_Apu"


def resolve(name: str, cpu_family_int: int, cpu_model_int: int, cpu_stepping_int: int = 0) -> CpuInfo:
    arch, family = _resolve_codename(name, cpu_family_int, cpu_model_int)
    t = _cpu_type(family, arch)
    return CpuInfo(
        name=name,
        arch=arch,
        family=family,
        type=t,
        cpu_family_int=cpu_family_int,
        cpu_model_int=cpu_model_int,
        cpu_stepping_int=cpu_stepping_int,
    )


@lru_cache(maxsize=1)
def detect() -> CpuInfo:
    system = platform.system()
    if system == "Windows":
        cpu_family_int, cpu_model_int, cpu_stepping_int, name = _parse_processor_identifier()
    elif system == "Darwin":
        cpu_family_int, cpu_model_int, cpu_stepping_int, name = _parse_sysctl()
    else:
        cpu_family_int, cpu_model_int, cpu_stepping_int, name = _parse_cpuinfo()
    return resolve(name, cpu_family_int, cpu_model_int, cpu_stepping_int)
