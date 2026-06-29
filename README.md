# ZenMaster

[![PyPI](https://img.shields.io/pypi/v/zenmaster)](https://pypi.org/project/zenmaster/)
[![Python](https://img.shields.io/pypi/pyversions/zenmaster)](https://pypi.org/project/zenmaster/)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![Platform](https://img.shields.io/badge/platform-Linux%20%7C%20Windows-lightgrey)](https://pypi.org/project/zenmaster/)

Pure-Python AMD Ryzen power management via SMU. Works on Linux and Windows. No compiler, no build chain, no dependencies.

```bash
pip install zenmaster
```

---

## Features

- Set and read power limits, thermal limits, clock ranges, voltages, and PBO/Curve Optimiser offsets
- Live PM table — labeled power, thermal, and current sensor data
- Dynamic `--help` that shows only what your CPU supports
- JSON output for scripting and integration
- `--reapply=N` to continuously re-apply a tuning preset
- Embeddable Python library — use it as a backend in your own tuning tools
- **No WinRing0** — Windows support uses [PawnIO](https://github.com/namazso/PawnIO), a modern signed driver

---

## Why not RyzenAdj

| | RyzenAdj | ZenMaster |
|---|---|---|
| Install | Build from source | `pip install zenmaster` |
| Windows | WinRing0 ⚠️ | PawnIO ✅ |
| `--help` | Static, shows all args | Dynamic — CPU-specific only |
| Output | Plain text | Plain text or `--json` |
| PM table | Raw floats | Labeled fields with units |
| Embed / script | Shell out to binary | `import zenmaster` |
| Build deps | cmake, make, libpci | None |

### On WinRing0

RyzenAdj's Windows backend uses WinRing0, a driver with well-documented security vulnerabilities ([CVE-2020-14979](https://nvd.nist.gov/vuln/detail/CVE-2020-14979), [CVE-2021-41285](https://nvd.nist.gov/vuln/detail/CVE-2021-41285)). It grants any unprivileged process full read/write access to physical memory, PCI config space, and I/O ports. Several AV vendors flag it as malicious outright.

ZenMaster uses [PawnIO](https://github.com/namazso/PawnIO) instead — a purpose-built, Microsoft-signed kernel driver that exposes a controlled IOCTL interface. No raw memory access, no known CVEs.

---

## Installation

### Linux

```bash
pip install zenmaster
```

Requires root and either the `ryzen_smu` kernel module (recommended) or direct PCI access.

**Install ryzen_smu module:**

```bash
git clone https://github.com/amkillam/ryzen_smu
cd ryzen_smu && make && sudo make install
sudo modprobe ryzen_smu
```

**Apply a tuning preset:**

```bash
sudo zenmaster --stapm-limit=15000 --fast-limit=20000 --tctl-temp=90
```

**Re-apply every 30 seconds:**

```bash
sudo zenmaster --stapm-limit=15000 --reapply=30
```

### Windows

1. Install [PawnIO](https://github.com/namazso/PawnIO.Setup/releases/latest/download/PawnIO_setup.exe) and reboot.
2. Open an **Administrator** command prompt or terminal.

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
| `--help` | Show supported tuning args for your CPU |
| `--info` | Detected CPU name, family, socket, backend |
| `--table` | Live PM table with labeled values |
| `--dump-table` | Raw PM table floats with hex offsets |
| `--json` | Machine-readable JSON output |
| `--reapply=N` | Re-apply settings every N seconds |

**Example — check what your CPU supports:**

```
$ zenmaster --help

ZenMaster — Ryzen Power Management Tool

Usage: zenmaster [OPTIONS] [TUNING ARGS...]

Tuning arguments for AMD Ryzen 9 7950X (Raphael, AM5_V1):

  Power limits:
    --stapm-limit=<mW>                 Sustained Power Limit — STAPM LIMIT
    --fast-limit=<mW>                  Actual Power Limit — PPT LIMIT FAST
    --slow-limit=<mW>                  Average Power Limit — PPT LIMIT SLOW
    --stapm-time=<s>                   STAPM constant time
    --slow-time=<s>                    Slow PPT constant time

  Thermal:
    --tctl-temp=<°C>                   Tctl Temperature Limit — THM LIMIT CORE
    ...
```

**Example — live PM table (APU/mobile):**

```
$ sudo zenmaster --table

PM Table Version: 0x00450005
+-------------------------+-----------+------------------------+
| STAPM LIMIT             |    15.000 | stapm-limit            |
| STAPM VALUE             |    12.441 |                        |
| PPT LIMIT FAST          |    20.000 | fast-limit             |
| PPT VALUE FAST          |    18.203 |                        |
| THM LIMIT CORE          |    90.000 | tctl-temp              |
| THM VALUE CORE          |    67.125 |                        |
+-------------------------+-----------+------------------------+
```

---

## Library usage

ZenMaster is designed to be embedded in tuning utilities, dashboards, and automation tools.

```python
from zenmaster.hardware import detect
from zenmaster import smu
from zenmaster.apply import apply

# Detect CPU (no privileges needed)
info = detect()
print(info.name)    # "AMD Ryzen 9 7950X"
print(info.family)  # "Raphael"

# Initialise SMU backend — requires root/admin and a working driver.
# Always raises RuntimeError with a clear message if something is missing.
#
# Linux failure cases:
#   - ryzen_smu not loaded + Secure Boot on  → raises (lockdown blocks PCI too)
#   - ryzen_smu not loaded + no PCI config   → raises
#   - ryzen_smu loaded but /smn missing      → raises (module too old)
#
# Windows failure cases:
#   - PawnIO not installed                   → raises with installer URL
#   - PawnIO installed but not rebooted yet  → raises, says to reboot
#   - Not running as Administrator           → raises
try:
    backend = smu.init()  # "ryzen_smu", "pci", or "pawnio"
except RuntimeError as e:
    print(f"SMU unavailable: {e}")
    raise SystemExit(1)

# Apply tuning args — returns per-arg results + a rejection flag
results, rejected = apply("--stapm-limit=15000 --tctl-temp=90", info.family)
for r in results:
    print(r["arg"], r["status"])  # 0x01 = SMU_OK

# Read PM table (APU / mobile only)
if smu.pm_table_supported(info.family):
    data = smu.read_pm_table(info.family)
    ver  = smu.read_pm_table_version(info.family)

# Send raw SMU commands directly
smu.send_mp1(info.family, 0x05, 15000)
smu.send_rsmu(info.family, 0x53, 90)
```

**Look up supported args for a CPU:**

```python
from zenmaster import runner

args = runner.get_supported_args("Renoir")
print(args)
# ["stapm-limit", "fast-limit", "slow-limit", "tctl-temp", ...]

opcodes = runner.lookup("Renoir", "stapm-limit")
print(opcodes)
# [(True, 0x14), (False, 0x31)]  — (is_mp1, opcode)
```

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

## License

GPL-3.0. SMU opcode tables from [UXTU4Linux](https://github.com/JamesCJ60/Universal-x86-Tuning-Utility-Handheld) (GPL-3.0). PawnIO kernel interface from [namazso/PawnIO](https://github.com/namazso/PawnIO) (MIT).
