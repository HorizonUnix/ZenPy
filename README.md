# ZenMaster

[![PyPI](https://img.shields.io/pypi/v/zenmaster?style=flat-square&color=blue)](https://pypi.org/project/zenmaster/)
[![Python](https://img.shields.io/pypi/pyversions/zenmaster?style=flat-square&color=yellow)](https://pypi.org/project/zenmaster/)
[![License](https://img.shields.io/badge/License-GPLv3-blue?style=flat-square)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-Linux%20%7C%20Windows-lightgrey?style=flat-square)](https://pypi.org/project/zenmaster/)

## Overview

ZenMaster adjusts power management settings for AMD Ryzen CPUs and APUs on Linux and Windows. It uses the same CLI as [RyzenAdj](https://github.com/FlyGoat/RyzenAdj), so your existing commands and presets keep working, but you install it with `pip` and never need a compiler. Set power limits, temperature limits, VRM currents, clocks, voltages and Curve Optimiser offsets without touching the BIOS.

```bash
pip install zenmaster
```

Reasons to use it over RyzenAdj:

- Installs with `pip` — no cmake, libpci, or building from source
- Same `--name=value` syntax, so scripts and presets carry over unchanged
- Uses [PawnIO](https://github.com/namazso/PawnIO) on Windows instead of WinRing0, which has known CVEs
- `--help` lists only the arguments your CPU supports, not every possible option
- `--table` shows a labeled sensor table; `--json` makes the output scriptable
- `--reapply=N` keeps your settings applied so other software can't undo them
- Works as a Python library — `import zenmaster` — on both Linux and Windows
- No mandatory third-party dependencies on either platform

---

## Compatibility

| Platform | Status |
|----------|--------|
| Linux, Python 3.10+, root | Supported — `ryzen_smu` module or PCI direct access |
| Windows, Python 3.10+, Administrator | Supported — PawnIO driver |
| Intel | Not supported |

> [!NOTE]
> On Linux, PCI direct access works on most systems without any kernel module. **`ryzen_smu` is only required when Secure Boot is enabled**, because kernel lockdown blocks raw PCI access. Install [ryzen_smu](https://github.com/amkillam/ryzen_smu) ≥ 0.1.7 and enroll the signing key in that case.

> [!WARNING]
> This tool writes directly to the CPU's System Management Unit. Wrong values can cause instability, throttling, or a hard lock. Use at your own risk.

---

## How it compares to RyzenAdj

ZenMaster keeps RyzenAdj's argument names and SMU opcode semantics, so it is a drop-in replacement for most use cases, while removing the build step and the WinRing0 driver.

| | RyzenAdj | ZenMaster |
|---|---|---|
| Install | Build from source (cmake, pkg-config, libpci) | `pip install zenmaster` |
| Language | C | Pure Python 3.10+ |
| Windows driver | WinRing0 ⚠️ | PawnIO ✅ |
| `--help` | Static — lists every argument | Dynamic — only your CPU's arguments |
| Output | Plain text | Plain text or `--json` |
| PM table | Raw float dump | Labeled fields with units (`--table`) |
| Use as a library | Link the C `libryzenadj` / shell out | `import zenmaster` |
| Build dependencies | cmake, make, libpci | None |
| Focus | "Ryzen Mobile Processors" | Ryzen mobile **and** desktop |

### On WinRing0

RyzenAdj's Windows backend uses WinRing0 (`OlsApi` / OpenLibSys), a driver with well-documented vulnerabilities ([CVE-2020-14979](https://nvd.nist.gov/vuln/detail/CVE-2020-14979), [CVE-2021-41285](https://nvd.nist.gov/vuln/detail/CVE-2021-41285)). It grants any unprivileged process full read/write access to physical memory, PCI config space, and I/O ports, and several AV vendors flag it outright.

ZenMaster uses [PawnIO](https://github.com/namazso/PawnIO) instead — a purpose-built, Microsoft-signed kernel driver that exposes a narrow IOCTL interface. No raw physical-memory access, no known CVEs.

---

## Installation

### Linux

```bash
pip install zenmaster
```

Requires root, and either the `ryzen_smu` kernel module or PCI direct access (used automatically when available).

Install `ryzen_smu` (only needed when Secure Boot is on):

```bash
git clone https://github.com/amkillam/ryzen_smu
cd ryzen_smu && make && sudo make install
sudo modprobe ryzen_smu
```

Apply a preset:

```bash
sudo zenmaster --stapm-limit=15000 --fast-limit=20000 --tctl-temp=90
```

Re-apply every 30 seconds:

```bash
sudo zenmaster --stapm-limit=15000 --reapply=30
```

### Windows

1. Install [PawnIO](https://github.com/namazso/PawnIO.Setup/releases/latest/download/PawnIO_setup.exe) and reboot.
2. Open an **Administrator** terminal.

```bat
pip install zenmaster
zenmaster --stapm-limit=15000 --fast-limit=20000 --tctl-temp=90
```

---

## CLI

```
zenmaster [OPTIONS] [TUNING ARGS...]
```

| Option | Description |
|---|---|
| `--help` | Show the tuning arguments supported by your CPU |
| `--info` | Detected CPU name, family, socket, and active backend |
| `--table` | Live PM table with labeled values |
| `--dump-table` | Raw PM table floats with hex offsets |
| `--json` | Machine-readable JSON output |
| `--reapply=N` | Re-apply settings every N seconds |

Tuning arguments use the same `--name=value` form as RyzenAdj. Arguments that take no value (`--enable-oc`, `--power-saving`, `--get-*`, …) are passed as bare flags.

**Check what your CPU supports:**

```
$ zenmaster --help

ZenMaster — Ryzen Power Management Tool

Usage: zenmaster [OPTIONS] [TUNING ARGS...]

Tuning arguments for AMD Ryzen 9 7950X (Raphael, AM5_V1):

  Power limits:
    --stapm-limit=<mW>                 Sustained Power Limit — STAPM LIMIT
    --fast-limit=<mW>                  Actual Power Limit — PPT LIMIT FAST
    --slow-limit=<mW>                  Average Power Limit — PPT LIMIT SLOW
    ...
```

**Live PM table (APU / mobile):**

```
$ sudo zenmaster --table

PM Table Version: 0x00450005
+-------------------------+-----------+------------------------+
| STAPM LIMIT             |    15.000 | stapm-limit            |
| STAPM VALUE             |    12.441 |                        |
| PPT LIMIT FAST          |    20.000 | fast-limit             |
| THM LIMIT CORE          |    90.000 | tctl-temp              |
| THM VALUE CORE          |    67.125 |                        |
+-------------------------+-----------+------------------------+
```

---

## Library usage

ZenMaster is built to be embedded in tuning utilities, dashboards, and automation tools — including from non-Python apps via the `--json` CLI.

```python
import zenmaster
from zenmaster import detect, apply, smu

print(zenmaster.__version__)

info = detect()
print(info.name, info.family)

try:
    backend = smu.init()
    print(backend)
except RuntimeError as e:
    print(f"SMU unavailable: {e}")
    raise SystemExit(1)

results, rejected = apply("--stapm-limit=15000 --tctl-temp=90", info.family)
for r in results:
    print(r["arg"], smu.status_name(r["status"]))

apply("--enable-oc", info.family)

if smu.pm_table_supported(info.family):
    data = smu.read_pm_table(info.family)
    ver  = smu.read_pm_table_version(info.family)

smu.send_mp1(info.family, 0x05, 15000)
smu.send_rsmu(info.family, 0x31, 90)
```

**Look up supported args for a CPU (no privileges needed):**

```python
from zenmaster import runner

print(runner.get_supported_args("Renoir"))
print(runner.lookup("Renoir", "stapm-limit"))
print(runner.is_flag_arg("enable-oc"))
print(runner.is_flag_arg("stapm-limit"))
```

A full runnable example lives in [`examples/demo.py`](examples/demo.py).

**Install with dev dependencies:**

```bash
pip install "zenmaster[dev]"
pytest
```

---

## Supported CPUs

Covers first-gen Ryzen (Summit Ridge / Zen 1) through Ryzen 9000 and Strix Halo. Run `zenmaster --info` to confirm detection and socket mapping.

PM table support (`--table`): Renoir, Lucienne, Cezanne/Barcelo, Rembrandt, Phoenix Point, Hawk Point, Strix Point, Krackan Point, Strix Halo.

---

## Requirements

| | Linux | Windows |
|---|---|---|
| Python | 3.10+ | 3.10+ |
| Privileges | root | Administrator |
| Driver | `ryzen_smu` module or PCI direct | [PawnIO](https://github.com/namazso/PawnIO.Setup) |
| Extra deps | None | None |

---

## Acknowledgments

| Project | Contribution |
|---------|-------------|
| [RyzenAdj](https://github.com/FlyGoat/RyzenAdj) | Canonical argument names and SMU opcode semantics |
| [UXTU4Linux](https://github.com/HorizonUnix/UXTU4Linux) | SMU opcode tables and Linux backend reference |
| [Universal x86 Tuning Utility](https://github.com/JamesCJ60/Universal-x86-Tuning-Utility) | Windows PawnIO path and CPU detection approach |
| [ryzen_smu](https://github.com/amkillam/ryzen_smu) | Linux kernel module for SMU access |
| [PawnIO](https://github.com/namazso/PawnIO) | Modern signed Windows kernel driver |
