# ZenMaster

[![PyPI](https://img.shields.io/pypi/v/zenmaster?style=flat-square&color=blue)](https://pypi.org/project/zenmaster/)
[![Python](https://img.shields.io/pypi/pyversions/zenmaster?style=flat-square&color=yellow)](https://pypi.org/project/zenmaster/)
[![License](https://img.shields.io/badge/License-GPLv3-blue?style=flat-square)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-Linux%20%7C%20Windows%20%7C%20macOS-lightgrey?style=flat-square)](https://pypi.org/project/zenmaster/)

## Overview

ZenMaster adjusts power limits, temperatures, VRM currents, clocks, voltages, and Curve Optimizer offsets on AMD Ryzen CPUs and APUs, no BIOS access needed. Runs on Linux, Windows, and macOS (AMD Hackintosh). Same CLI as [RyzenAdj](https://github.com/FlyGoat/RyzenAdj), so your existing scripts and presets just work, except you `pip install` it instead of building it.

```bash
pip install zenmaster
sudo zenmaster --stapm-limit=15000 --fast-limit=20000 --tctl-temp=90
```

What you get over RyzenAdj itself:

- No cmake, no libpci, no build step. `pip install` and you're done.
- Same `--name=value` args, so nothing you already have breaks.
- PawnIO on Windows, not WinRing0. WinRing0 has known CVEs, PawnIO doesn't.
- `--help` only lists what your CPU actually supports.
- `--table` for a labeled sensor readout, `--sensors` for a compact live view, `--json` when you need to parse it.
- `--reapply=N` if you want the settings to stick against other software fighting you.
- `import zenmaster` works as a library on all three platforms.
- Zero mandatory third-party dependencies, anywhere.

**Full documentation is in the [Wiki](https://github.com/HorizonUnix/ZenMaster/wiki)**, this README is just the overview. See below for what's there.

---

## Documentation

| Page | What's in it |
|---|---|
| [Installation](https://github.com/HorizonUnix/ZenMaster/wiki/Installation) | Linux, Windows, and macOS setup: `ryzen_smu`, PawnIO, DirectHW |
| [CLI Usage](https://github.com/HorizonUnix/ZenMaster/wiki/CLI-Usage) | Every option, examples, JSON output |
| [Tuning Arguments](https://github.com/HorizonUnix/ZenMaster/wiki/Tuning-Arguments) | Full argument reference with units |
| [PM Table and Monitoring](https://github.com/HorizonUnix/ZenMaster/wiki/PM-Table-and-Monitoring) | `--table` / `--sensors` / `--dump-table` |
| [Library API](https://github.com/HorizonUnix/ZenMaster/wiki/Library-API) | Embedding ZenMaster in Python |
| [How ZenMaster Talks to the SMU](https://github.com/HorizonUnix/ZenMaster/wiki/How-ZenMaster-Talks-to-the-SMU) | The mailbox protocol, and how each OS reaches it |
| [Architecture](https://github.com/HorizonUnix/ZenMaster/wiki/Architecture) | Package layout, internals, opcode tables |
| [Troubleshooting](https://github.com/HorizonUnix/ZenMaster/wiki/Troubleshooting) | Fixes for the common problems |
| [FAQ](https://github.com/HorizonUnix/ZenMaster/wiki/FAQ) | Short answers |

---

## Compatibility

| Platform | Privileges | Driver |
|----------|--------|--------|
| Linux, Python 3.10+ | root | `ryzen_smu` module, or PCI direct access |
| Windows, Python 3.10+ | Administrator | [PawnIO](https://github.com/namazso/PawnIO.Setup) |
| macOS (AMD Hackintosh), Python 3.10+ | root | [DirectHW.kext](https://github.com/joevt/directhw), or the kext-free IOPCIBridge path (tuning only) |
| Intel | n/a | Not supported |

> [!NOTE]
> On Linux, PCI direct access works on most systems without any kernel module. **`ryzen_smu` is only required when Secure Boot is enabled**, since kernel lockdown blocks raw PCI access. Install [ryzen_smu](https://github.com/amkillam/ryzen_smu) ≥ 0.1.7 and enroll the signing key in that case. Full detail on why: the [How ZenMaster Talks to the SMU](https://github.com/HorizonUnix/ZenMaster/wiki/How-ZenMaster-Talks-to-the-SMU) wiki page.

> [!WARNING]
> This tool writes directly to the CPU's System Management Unit. Wrong values can cause instability, throttling, or a hard lock. Use at your own risk.

---

## Quick start

**Linux:**
```bash
pip install zenmaster
sudo zenmaster --stapm-limit=15000 --fast-limit=20000 --tctl-temp=90
```

**Windows** (install [PawnIO](https://github.com/namazso/PawnIO.Setup/releases/latest/download/PawnIO_setup.exe) first, reboot, then open an Administrator terminal):
```bat
pip install zenmaster
zenmaster --stapm-limit=15000 --fast-limit=20000 --tctl-temp=90
```

**macOS** (AMD Hackintosh, needs DirectHW.kext or the `--iopci` fallback, see the wiki):
```bash
pip3 install zenmaster
sudo python3 -m zenmaster --stapm-limit=15000 --fast-limit=20000 --tctl-temp=90
```

Check what your CPU supports with `zenmaster --help`; it only lists arguments your family actually has. Full walkthrough for each OS, including driver setup: the [Installation](https://github.com/HorizonUnix/ZenMaster/wiki/Installation) wiki page.

---

## Library usage

Meant to be embedded, not just run standalone.

```python
import zenmaster
from zenmaster import detect, apply, smu

info = detect()
smu.init()

results, rejected = apply("--stapm-limit=15000 --tctl-temp=90", info.family)
for r in results:
    print(r["arg"], smu.status_name(r["status"]))
```

`py.typed` ships in the package, so your type checker sees real signatures. `smu.init()` raises `BackendUnavailable` on failure; any SMU call before `init()` raises `SMUNotInitialized`; both subclass `ZenMasterError` (itself a `RuntimeError`). Full API reference, including reading sensors, low-level mailbox access, and two runnable examples ported from RyzenAdj: the [Library API](https://github.com/HorizonUnix/ZenMaster/wiki/Library-API) wiki page.

---

## How it compares to RyzenAdj

Same argument names, same SMU opcode semantics. Drop-in for most use cases, minus the build step and WinRing0.

| | RyzenAdj | ZenMaster |
|---|---|---|
| Install | Build from source (cmake, pkg-config, libpci) | `pip install zenmaster` |
| Language | C | Pure Python 3.10+ |
| Windows driver | WinRing0 ⚠️ | PawnIO ✅ |
| `--help` | Static, lists every argument | Dynamic, only your CPU's arguments |
| Output | Plain text | Plain text or `--json` |
| PM table | Raw float dump | Labeled fields with units (`--table`), or a compact live view (`--sensors`) |
| Use as a library | Link the C `libryzenadj` / shell out | `import zenmaster` |
| Build dependencies | cmake, make, libpci | None |
| Platforms | Windows and Linux | Linux, Windows, and macOS (Hackintosh) |

### On WinRing0

RyzenAdj's Windows backend is WinRing0 (`OlsApi` / OpenLibSys). It has actual CVEs ([CVE-2020-14979](https://nvd.nist.gov/vuln/detail/CVE-2020-14979), [CVE-2021-41285](https://nvd.nist.gov/vuln/detail/CVE-2021-41285)) and hands any unprivileged process full read/write to physical memory, PCI config space, I/O ports. A few AV vendors just flag it outright.

ZenMaster uses [PawnIO](https://github.com/namazso/PawnIO) instead: Microsoft-signed, narrow IOCTL interface, no raw physical-memory access, no CVEs on record.

---

## Supported CPUs

First-gen Ryzen (Summit Ridge / Zen 1) through Ryzen 9000 and Strix Halo, APU and desktop. Run `zenmaster --info` to confirm detection and socket mapping. PM table support (`--table`/`--sensors`) is a narrower list, mostly APUs and mobile parts, see the [Tuning Arguments](https://github.com/HorizonUnix/ZenMaster/wiki/Tuning-Arguments) and [PM Table and Monitoring](https://github.com/HorizonUnix/ZenMaster/wiki/PM-Table-and-Monitoring) wiki pages.

---

## Updating

```bash
pip install -U zenmaster
```

`zenmaster --version` checks PyPI for a newer release without updating; `zenmaster.check_update()` does the same from code.

---

## Acknowledgments

| Project | Contribution |
|---------|-------------|
| [RyzenAdj](https://github.com/FlyGoat/RyzenAdj) | Inspiration for the tool as a whole, and canonical argument names |
| [Universal x86 Tuning Utility](https://github.com/JamesCJ60/Universal-x86-Tuning-Utility) | SMU opcode tables, Windows PawnIO path, and CPU detection approach |
| [UXTU4Linux](https://github.com/HorizonUnix/UXTU4Linux) | Core reference implementation: Linux backend logic and hardware detection |
| [ryzen_smu](https://github.com/amkillam/ryzen_smu) | Linux kernel module for SMU access |
| [PawnIO](https://github.com/namazso/PawnIO) | Modern signed Windows kernel driver |
| [DirectHW](https://github.com/joevt/directhw) | macOS kext for PCI config and physical memory access (joevt) |
| [pciutils](https://github.com/joevt/pciutils) | The `darwin2` IOPCIBridge method behind the kext-free `--iopci` path (joevt) |
