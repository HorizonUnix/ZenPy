from __future__ import annotations
import argparse
import json
import os
import platform
import struct
import sys
import time

from zenpy import runner, smu
from zenpy.apply import apply
from zenpy.hardware import CpuInfo, detect
from zenpy.table import read_table

_CATEGORIES: dict[str, list[str]] = {
    "Power limits":    ["stapm-limit", "fast-limit", "slow-limit", "ppt-limit",
                        "apu-slow-limit", "stapm-time", "slow-time"],
    "Thermal":         ["tctl-temp", "chtc-temp", "apu-skin-temp", "dgpu-skin-temp",
                        "skin-temp-limit"],
    "VRM & Currents":  ["vrm-current", "vrmmax-current", "vrmsoc-current",
                        "vrmsocmax-current", "vrmgfx-current", "vrmgfxmax-current",
                        "psi0-current", "psi0soc-current", "psi3cpu-current",
                        "psi3gfx-current", "prochot-deassertion-ramp"],
    "Clocks":          ["max-cpuclk", "min-cpuclk", "max-gfxclk", "min-gfxclk",
                        "gfx-clk", "max-socclk-frequency", "min-socclk-frequency",
                        "max-fclk-frequency", "min-fclk-frequency",
                        "max-vcn", "min-vcn", "max-lclk", "min-lclk",
                        "oc-clk", "per-core-oc-clk", "set-boost-limit-frequency",
                        "set-vmin-freq"],
    "Overclocking":    ["enable-oc", "disable-oc", "oc-volt", "pbo-scalar",
                        "set-coall", "set-coper", "set-cogfx",
                        "set-gpuclockoverdrive-byvid"],
    "Power states":    ["power-saving", "max-performance",
                        "enable-feature", "disable-feature"],
    "Query / get":     ["get-pbo-scalar", "get-sustained-power-and-thm-limit",
                        "get-overclocking-support", "get-max-cpu-clk",
                        "get-min-gfx-clk", "get-max-gfx-clk", "get-curr-gfx-clk",
                        "get-pbo-fused-power-limit", "get-pbo-fused-slow-limit",
                        "get-pbo-fused-fast-limit", "get-pbo-fused-apu-slow-limit",
                        "get-pbo-fused-vrmtdc-limit", "get-pbo-fused-vrmsoc-current",
                        "get-pbo-fused-tctl-temp", "get-coper-options",
                        "get-cogfx-options", "disable-prochot",
                        "set-fll-btc-enable", "set-vddoff-vid",
                        "set-ulv-vid", "setcpu-freqto-ramstate",
                        "stopcpu-freqto-ramstate"],
}

_ARG_UNITS: dict[str, str] = {
    "stapm-limit": "mW", "fast-limit": "mW", "slow-limit": "mW",
    "ppt-limit": "mW", "apu-slow-limit": "mW",
    "stapm-time": "s",  "slow-time": "s",
    "tctl-temp": "°C",  "chtc-temp": "°C", "apu-skin-temp": "°C",
    "dgpu-skin-temp": "°C", "skin-temp-limit": "°C",
    "vrm-current": "mA", "vrmmax-current": "mA", "vrmsoc-current": "mA",
    "vrmsocmax-current": "mA", "vrmgfx-current": "mA", "vrmgfxmax-current": "mA",
    "psi0-current": "mA", "psi0soc-current": "mA",
    "psi3cpu-current": "mA", "psi3gfx-current": "mA",
    "oc-clk": "MHz", "per-core-oc-clk": "MHz", "max-cpuclk": "MHz",
    "min-cpuclk": "MHz", "max-gfxclk": "MHz", "min-gfxclk": "MHz",
    "gfx-clk": "MHz", "max-socclk-frequency": "MHz", "min-socclk-frequency": "MHz",
    "max-fclk-frequency": "MHz", "min-fclk-frequency": "MHz",
    "oc-volt": "mV",
}

_ARG_DESCS: dict[str, str] = {
    "stapm-limit":               "Sustained Power Limit — STAPM LIMIT",
    "fast-limit":                "Actual Power Limit — PPT LIMIT FAST",
    "slow-limit":                "Average Power Limit — PPT LIMIT SLOW",
    "ppt-limit":                 "Platform Package Tracking power limit",
    "apu-slow-limit":            "APU PPT Slow limit for A+A dGPU platform — PPT LIMIT APU",
    "stapm-time":                "STAPM constant time",
    "slow-time":                 "Slow PPT constant time",
    "tctl-temp":                 "Tctl Temperature Limit — THM LIMIT CORE",
    "chtc-temp":                 "CHTC Temperature Limit",
    "apu-skin-temp":             "APU Skin Temperature Limit — STT LIMIT APU",
    "dgpu-skin-temp":            "dGPU Skin Temperature Limit — STT LIMIT dGPU",
    "skin-temp-limit":           "Skin Temperature Power Limit",
    "vrm-current":               "VRM Current Limit — TDC LIMIT VDD",
    "vrmmax-current":            "VRM Maximum Current Limit — EDC LIMIT VDD",
    "vrmsoc-current":            "VRM SoC Current Limit — TDC LIMIT SOC",
    "vrmsocmax-current":         "VRM SoC Maximum Current Limit — EDC LIMIT SOC",
    "vrmgfx-current":            "VRM GFX Current Limit — TDC LIMIT GFX",
    "vrmgfxmax-current":         "VRM GFX Maximum Current Limit — EDC LIMIT GFX",
    "psi0-current":              "PSI0 VDD Current Limit",
    "psi0soc-current":           "PSI0 SoC Current Limit",
    "psi3cpu-current":           "PSI3 CPU Current Limit",
    "psi3gfx-current":           "PSI3 GFX Current Limit",
    "prochot-deassertion-ramp":  "Ramp time after PROCHOT deasserts; higher = tighter post-throttle limits",
    "max-cpuclk":                "Maximum CPU clock frequency",
    "min-cpuclk":                "Minimum CPU clock frequency",
    "max-gfxclk":                "Maximum GFX clock frequency",
    "min-gfxclk":                "Minimum GFX clock frequency",
    "gfx-clk":                   "Forced GFX clock speed (Renoir only)",
    "max-socclk-frequency":      "Maximum SoC clock frequency",
    "min-socclk-frequency":      "Minimum SoC clock frequency",
    "max-fclk-frequency":        "Maximum Infinity Fabric (CPU↔GPU) frequency",
    "min-fclk-frequency":        "Minimum Infinity Fabric (CPU↔GPU) frequency",
    "max-vcn":                   "Maximum Video Core Next (VCE) frequency",
    "min-vcn":                   "Minimum Video Core Next (VCE) frequency",
    "max-lclk":                  "Maximum Data Launch Clock frequency",
    "min-lclk":                  "Minimum Data Launch Clock frequency",
    "oc-clk":                    "Forced all-core clock speed (Renoir and up)",
    "per-core-oc-clk":           "Forced per-core clock speed (Renoir and up)",
    "set-boost-limit-frequency": "Boost frequency ceiling",
    "set-vmin-freq":             "Minimum voltage frequency floor",
    "enable-oc":                 "Enable overclocking mode (Renoir and up)",
    "disable-oc":                "Disable overclocking mode (Renoir and up)",
    "oc-volt":                   "Forced core VID: (1.55 − target_V) / 0.00625 (Renoir and up)",
    "pbo-scalar":                "Precision Boost Overdrive scalar",
    "set-coall":                 "All-core Curve Optimiser offset",
    "set-coper":                 "Per-core Curve Optimiser offset",
    "set-cogfx":                 "iGPU Curve Optimiser offset",
    "set-gpuclockoverdrive-byvid": "Set GPU clock overdrive by VID",
    "power-saving":              "Apply power-saving profile (AC-unplugged behavior)",
    "max-performance":           "Apply max-performance profile (AC-plugged behavior)",
    "enable-feature":            "Enable a CPU/SMU feature by feature ID",
    "disable-feature":           "Disable a CPU/SMU feature by feature ID",
    "get-pbo-scalar":                   "Query current PBO scalar value",
    "get-sustained-power-and-thm-limit":"Query fused sustained power and thermal limit",
    "get-overclocking-support":         "Query overclocking support flags",
    "get-max-cpu-clk":                  "Query maximum CPU clock limit",
    "get-min-gfx-clk":                  "Query minimum GFX clock",
    "get-max-gfx-clk":                  "Query maximum GFX clock",
    "get-curr-gfx-clk":                 "Query current GFX clock",
    "get-pbo-fused-power-limit":        "Query PBO fused sustained power limit",
    "get-pbo-fused-slow-limit":         "Query PBO fused slow power limit",
    "get-pbo-fused-fast-limit":         "Query PBO fused fast power limit",
    "get-pbo-fused-apu-slow-limit":     "Query PBO fused APU slow power limit",
    "get-pbo-fused-vrmtdc-limit":       "Query PBO fused VRM TDC current limit",
    "get-pbo-fused-vrmsoc-current":     "Query PBO fused VRM SoC current",
    "get-pbo-fused-tctl-temp":          "Query PBO fused Tctl temperature",
    "get-coper-options":                "Query available per-core Curve Optimiser options",
    "get-cogfx-options":                "Query available iGPU Curve Optimiser options",
    "disable-prochot":                  "Disable PROCHOT thermal throttle signal",
    "set-fll-btc-enable":               "Enable FLL BTC mode",
    "set-vddoff-vid":                   "Set VDD-off VID",
    "set-ulv-vid":                      "Set Ultra-Low Voltage VID",
    "setcpu-freqto-ramstate":           "Lock CPU frequency to RAM state",
    "stopcpu-freqto-ramstate":          "Release CPU frequency from RAM state lock",
}


def _is_root() -> bool:
    if platform.system() == "Windows":
        try:
            import ctypes
            return bool(ctypes.windll.shell32.IsUserAnAdmin())
        except Exception:
            return False
    return os.geteuid() == 0


def _show_help(info: CpuInfo) -> None:
    supported = set(runner.get_supported_args(info.family))
    socket = runner.get_socket(info.family) or "unknown"
    print(f"ZenPy — AMD Ryzen power tuning")
    print(f"  CPU    : {info.name}")
    print(f"  Family : {info.family}  ({info.arch})")
    print(f"  Socket : {socket}")
    print()
    print("Usage: zenpy [OPTIONS] [TUNING ARGS...]")
    print()
    print("Options:")
    print("  --info           Show CPU and backend info (no root needed)")
    print("  --json           Machine-readable JSON output")
    print("  --reapply=N      Re-apply settings every N seconds (foreground)")
    if smu.pm_table_supported(info.family):
        print("  --table          Show labeled power metrics table (like ryzenadj --info)")
        print("  --dump-table     Dump raw PM table floats with hex offsets")
    print()

    if not supported:
        print(f"No SMU support found for family '{info.family}'.")
        return

    print("Tuning arguments (this CPU only):")
    shown: set[str] = set()
    for category, args in _CATEGORIES.items():
        in_category = [a for a in args if a in supported and a not in shown]
        if not in_category:
            continue
        print(f"\n  {category}:")
        for arg in in_category:
            unit = _ARG_UNITS.get(arg, "")
            unit_str = f"<{unit}>" if unit else "<value>"
            left = f"--{arg}={unit_str}"
            desc = _ARG_DESCS.get(arg, "Unknown command")
            print(f"    {left:<38} {desc}")
            shown.add(arg)

    uncategorised = [a for a in runner.get_supported_args(info.family) if a not in shown]
    if uncategorised:
        print("\n  Other:")
        for arg in uncategorised:
            left = f"--{arg}=<value>"
            desc = _ARG_DESCS.get(arg, "Unknown command")
            print(f"    {left:<38} {desc}")


def _show_info(info: CpuInfo, backend: str | None, json_out: bool) -> None:
    socket = runner.get_socket(info.family) or "unknown"
    if json_out:
        print(json.dumps({
            "cpu": info.name,
            "family": info.family,
            "arch": info.arch,
            "type": info.type,
            "socket": socket,
            "backend": backend,
            "cpu_family_int": info.cpu_family_int,
            "cpu_model_int": info.cpu_model_int,
        }, indent=2))
    else:
        print(f"CPU    : {info.name}")
        print(f"Family : {info.family}  ({info.arch})")
        print(f"Type   : {info.type}")
        print(f"Socket : {socket}")
        print(f"Backend: {backend or 'not initialised'}")


def _format_results(results: list[dict], info: CpuInfo, backend: str | None,
                    json_out: bool, rejected: bool) -> str:
    if json_out:
        socket = runner.get_socket(info.family) or "unknown"
        out = {
            "cpu": info.name,
            "family": info.family,
            "socket": socket,
            "backend": backend,
            "results": [
                {
                    "arg": r["arg"],
                    "value": r["value"],
                    "mailbox": r.get("mailbox", ""),
                    "opcode": f"0x{r['opcode']:02X}" if r.get("opcode") else "",
                    "status": (smu.status_name(r["status"]) if r.get("status")
                               else r.get("error", "unsupported")),
                }
                for r in results
            ],
            "rejected": rejected,
        }
        return json.dumps(out, indent=2)
    else:
        lines = []
        for r in results:
            if "error" in r:
                lines.append(f"{r['arg']} -> {r['error']}")
            else:
                status_str = smu.status_name(r["status"])
                lines.append(
                    f"{r['arg']} [{r['mailbox']} 0x{r['opcode']:02X}] = {r['value']} -> {status_str}"
                )
        return "\n".join(lines)


def _require_pm_table(json_out: bool, family: str = "") -> bytes:
    if not smu.pm_table_supported(family):
        msg = "PM table not available on this platform/family"
        if json_out:
            print(json.dumps({"error": msg}))
        else:
            print(f"ZenPy: {msg}", file=sys.stderr)
        sys.exit(1)
    data = smu.read_pm_table(family)
    if not data:
        msg = "Failed to read PM table"
        if json_out:
            print(json.dumps({"error": msg}))
        else:
            print(f"ZenPy: {msg}", file=sys.stderr)
        sys.exit(1)
    return data


def _show_table(json_out: bool, family: str = "") -> None:
    data = _require_pm_table(json_out, family)
    ver  = smu.read_pm_table_version(family)
    rows = read_table(data, ver)

    if json_out:
        print(json.dumps({
            "pm_table_version": f"0x{ver:08X}",
            "fields": [{"name": label, "value": val, "flag": flag}
                       for label, val, flag in rows],
        }, indent=2))
    else:
        print(f"PM Table Version: 0x{ver:08X}")
        fmt = "| {:<21} | {:>9.3f} | {:<20} |"
        sep = "+" + "-" * 23 + "+" + "-" * 11 + "+" + "-" * 22 + "+"
        print(sep)
        for label, val, flag in rows:
            print(fmt.format(label, val, flag))
        print(sep)


def _dump_pm_table(json_out: bool, family: str = "") -> None:
    data = _require_pm_table(json_out, family)
    count = len(data) // 4
    values = list(struct.unpack(f"<{count}f", data[:count * 4]))

    if json_out:
        print(json.dumps({"pm_table": values}, indent=2))
    else:
        for i, v in enumerate(values):
            print(f"| 0x{i*4:04X} | {v:9.3f} |")


def main() -> None:
    argv = sys.argv[1:]

    if not argv or "--help" in argv or "-h" in argv:
        try:
            info = detect()
        except Exception:
            info = CpuInfo("Unknown", "Unknown", "Unknown", "Unknown", 0, 0)
        _show_help(info)
        sys.exit(0)

    p = argparse.ArgumentParser(add_help=False)
    p.add_argument("--info",       action="store_true")
    p.add_argument("--json",       action="store_true", dest="json_out")
    p.add_argument("--reapply",    type=int, default=0, metavar="SECONDS")
    p.add_argument("--dump-table", action="store_true", dest="dump_table")
    p.add_argument("--table",      action="store_true")
    flags, rest = p.parse_known_args(argv)

    info = detect()

    if info.type not in ("Amd_Apu", "Amd_Desktop_Cpu"):
        print(f"ZenPy: unsupported CPU '{info.name}' (only AMD Ryzen supported)", file=sys.stderr)
        sys.exit(1)

    backend: str | None = None

    if flags.info:
        try:
            backend = smu.init()
        except RuntimeError:
            pass
        _show_info(info, backend, flags.json_out)
        if not rest and not flags.dump_table and not flags.table:
            sys.exit(0)

    if flags.table:
        _show_table(flags.json_out, info.family)
        if not rest and not flags.dump_table:
            sys.exit(0)

    if flags.dump_table:
        _dump_pm_table(flags.json_out, info.family)
        if not rest:
            sys.exit(0)

    if rest:
        if not _is_root():
            print("ZenPy: root/admin privileges required.", file=sys.stderr)
            print("       Run with sudo (Linux) or as Administrator (Windows).", file=sys.stderr)
            sys.exit(1)

        if backend is None:
            try:
                backend = smu.init()
            except RuntimeError as e:
                print(f"ZenPy: backend error: {e}", file=sys.stderr)
                sys.exit(1)

    if rest:
        if flags.reapply > 0 and flags.reapply < 1:
            print("ZenPy: --reapply minimum is 1 second", file=sys.stderr)
            sys.exit(1)

        args_str = " ".join(rest)
        try:
            while True:
                results, rejected = apply(args_str, info.family)
                output = _format_results(results, info, backend, flags.json_out, rejected)
                if output:
                    print(output)
                if flags.reapply <= 0:
                    sys.exit(1 if rejected else 0)
                time.sleep(flags.reapply)
        except KeyboardInterrupt:
            if not flags.json_out:
                print("\nZenPy: stopped.")
