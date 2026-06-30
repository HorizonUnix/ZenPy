from __future__ import annotations
import argparse
import json
import os
import platform
import struct
import sys
import time
from dataclasses import asdict

from zenmaster import __version__, runner, smu
from zenmaster.apply import apply
from zenmaster.hardware import CpuInfo, detect
from zenmaster.table import read_table

_CATEGORIES: dict[str, list[str]] = {
    "Power limits":    ["stapm-limit", "fast-limit", "slow-limit", "ppt-limit",
                        "apu-slow-limit", "stapm-time", "slow-time"],
    "Thermal":         ["tctl-temp", "chtc-temp", "apu-skin-temp", "dgpu-skin-temp",
                        "skin-temp-limit"],
    "VRM & Currents":  ["tdc-limit", "edc-limit", "vrm-current", "vrmmax-current",
                        "vrmsoc-current", "vrmsocmax-current", "vrmcvip-current",
                        "vrmgfx-current", "vrmgfxmax-current", "psi0-current",
                        "psi0soc-current", "psi3cpu-current", "psi3gfx-current",
                        "prochot-deassertion-ramp"],
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
    "tdc-limit": "mA", "edc-limit": "mA",
    "vrm-current": "mA", "vrmmax-current": "mA", "vrmsoc-current": "mA",
    "vrmsocmax-current": "mA", "vrmcvip-current": "mA", "vrmgfx-current": "mA", "vrmgfxmax-current": "mA",
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
    "tdc-limit":                 "Thermal Design Current Limit — TDC LIMIT",
    "edc-limit":                 "Electrical Design Current Limit — EDC LIMIT",
    "vrm-current":               "VRM Current Limit — TDC LIMIT VDD",
    "vrmmax-current":            "VRM Maximum Current Limit — EDC LIMIT VDD",
    "vrmsoc-current":            "VRM SoC Current Limit — TDC LIMIT SOC",
    "vrmsocmax-current":         "VRM SoC Maximum Current Limit — EDC LIMIT SOC",
    "vrmcvip-current":           "VRM CVIP Current Limit — TDC LIMIT CVIP (VanGogh only)",
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
    "set-coall":                 "All-core Curve Optimizer offset",
    "set-coper":                 "Per-core Curve Optimizer offset",
    "set-cogfx":                 "iGPU Curve Optimizer offset",
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
    "get-coper-options":                "Query available per-core Curve Optimizer options",
    "get-cogfx-options":                "Query available iGPU Curve Optimizer options",
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
            import ctypes.wintypes
            k32  = ctypes.windll.kernel32
            adv  = ctypes.windll.advapi32
            tok  = ctypes.c_void_p()
            if not adv.OpenProcessToken(k32.GetCurrentProcess(), 0x0008, ctypes.byref(tok)):
                return bool(ctypes.windll.shell32.IsUserAnAdmin())
            elevation = ctypes.c_uint(0)
            size      = ctypes.c_uint(ctypes.sizeof(elevation))
            ok = adv.GetTokenInformation(tok, 20, ctypes.byref(elevation), size, ctypes.byref(size))
            k32.CloseHandle(tok)
            return bool(elevation.value) if ok else False
        except Exception:
            return False
    return os.geteuid() == 0


def _arg_help_line(arg: str) -> str:
    if runner.is_flag_arg(arg):
        left = f"--{arg}"
    else:
        unit = _ARG_UNITS.get(arg, "")
        unit_str = f"<{unit}>" if unit else "<value>"
        left = f"--{arg}={unit_str}"
    desc = _ARG_DESCS.get(arg, "Unknown command")
    return f"    {left:<38} {desc}"


def _show_help(info: CpuInfo) -> None:
    supported_list = runner.get_supported_args(info.family)
    supported = set(supported_list)
    socket = runner.get_socket(info.family) or "unknown"
    print("ZenMaster — Ryzen Power Management Tool")
    print()
    print("Usage: zenmaster [OPTIONS] [TUNING ARGS...]")
    print()
    print("Options:")
    print("  --info           Show CPU and backend info")
    print("  --json           Machine-readable JSON output")
    print("  --reapply=N      Re-apply settings every N seconds (foreground)")
    print("  --version        Show version and check PyPI for a newer release")
    if smu.pm_table_supported(info.family):
        print("  --table          Show labeled power metrics table")
        print("  --sensors        Show key live sensors (temp, load, power, clocks)")
        print("  --dump-table     Dump raw PM table floats with hex offsets")
    print()

    if not supported:
        print(f"No SMU support found for family '{info.family}'.")
    else:
        print(f"Tuning arguments for {info.name} ({info.family}, {socket}):")
        shown: set[str] = set()
        for category, args in _CATEGORIES.items():
            in_category = [a for a in args if a in supported and a not in shown]
            if not in_category:
                continue
            print(f"\n  {category}:")
            for arg in in_category:
                print(_arg_help_line(arg))
                shown.add(arg)

        uncategorised = [a for a in supported_list if a not in shown]
        if uncategorised:
            print("\n  Other:")
            for arg in uncategorised:
                print(_arg_help_line(arg))

    print()
    print("WARNING: Use at your own risk!")
    print(f"Version: {__version__} by HorizonUnix under GPL-3.0 License")


def _show_update(json_out: bool) -> None:
    from zenmaster.update import latest_version, _ver_tuple
    latest = latest_version()
    newer = latest is not None and _ver_tuple(latest) > _ver_tuple(__version__)
    if json_out:
        print(json.dumps({
            "installed": __version__,
            "latest": latest,
            "update_available": newer,
        }, indent=2))
        return
    print(f"ZenMaster {__version__} (installed)")
    if latest is None:
        print("Could not reach PyPI to check for updates.")
    elif newer:
        print(f"A newer version is available: {latest}")
        print("Update with:  pip install -U zenmaster")
    else:
        print("You are on the latest version.")


def _driver_line(backend: str | None) -> str:
    if backend == "pci":
        return "PCI direct access"
    st = smu.module_status()
    drv = smu.driver_name()
    ver = "" if st.version == "unknown" else f" {st.version}"
    if st.reason == "not_loaded":
        return f"{drv} (not loaded)"
    if st.ok:
        return f"{drv}{ver} (OK)"
    if st.reason == "too_old":
        return f"{drv}{ver} — too old (need {st.min_version})"
    return f"{drv}{ver} — version unknown"


def _show_info(info: CpuInfo, backend: str | None, json_out: bool) -> None:
    socket = runner.get_socket(info.family) or "unknown"
    if json_out:
        st = smu.module_status()
        print(json.dumps({
            "name": info.name,
            "family": info.family,
            "arch": info.arch,
            "type": info.type,
            "socket": socket,
            "backend": backend,
            "driver": {
                "name": smu.driver_name(),
                "version": st.version,
                "min_version": st.min_version,
                "ok": st.ok,
                "reason": st.reason,
            },
            "cpu_family_int": info.cpu_family_int,
            "cpu_model_int": info.cpu_model_int,
        }, indent=2))
    else:
        print(f"Name   : {info.name}")
        print(f"Family : {info.family}  ({info.arch})")
        print(f"Type   : {info.type}")
        print(f"Socket : {socket}")
        print(f"Backend: {backend or 'not initialized'}")
        print(f"Driver : {_driver_line(backend)}")


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
                    "mailbox": r["mailbox"],
                    "opcode": f"0x{r['opcode']:02X}" if r["opcode"] else "",
                    "status": r["error"] if r["error"] else smu.status_name(r["status"]),
                    "returned": r["returned"],
                }
                for r in results
            ],
            "rejected": rejected,
        }
        return json.dumps(out, indent=2)
    else:
        lines = []
        for r in results:
            if r["error"]:
                lines.append(f"{r['arg']} -> {r['error']}")
            elif r["returned"] is not None:
                status_str = smu.status_name(r["status"])
                lines.append(
                    f"{r['arg']} [{r['mailbox']} 0x{r['opcode']:02X}] -> {status_str} = {r['returned']} (0x{r['returned']:08X})"
                )
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
            print(f"ZenMaster: {msg}", file=sys.stderr)
        sys.exit(1)
    data = smu.read_pm_table(family)
    if not data:
        msg = "Failed to read PM table"
        if json_out:
            print(json.dumps({"error": msg}))
        else:
            print(f"ZenMaster: {msg}", file=sys.stderr)
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


_SENSOR_ROWS = [
    ("CPU Temp",     "tctl_temp",    "°C"),
    ("CPU Load",     "cclk_busy",    "%"),
    ("Socket Power", "socket_power", "W"),
    ("STAPM Value",  "stapm_value",  "W"),
    ("iGPU Clock",   "gfx_clk",      "MHz"),
    ("iGPU Temp",    "gfx_temp",     "°C"),
    ("Mem Clock",    "mem_clk",      "MHz"),
]


def _show_sensors(json_out: bool, family: str = "") -> None:
    sensors = smu.read_pm_sensors(family)
    if sensors is None:
        msg = "PM table not available on this platform/family"
        if json_out:
            print(json.dumps({"error": msg}))
        else:
            print(f"ZenMaster: {msg}", file=sys.stderr)
        sys.exit(1)

    if json_out:
        print(json.dumps(asdict(sensors), indent=2))
    else:
        for label, field, unit in _SENSOR_ROWS:
            value = getattr(sensors, field)
            if value is not None:
                print(f"{label:<12}: {value:8.1f} {unit}")


def _dump_pm_table(json_out: bool, family: str = "") -> None:
    data = _require_pm_table(json_out, family)
    count = len(data) // 4
    values = list(struct.unpack(f"<{count}f", data[:count * 4]))

    if json_out:
        print(json.dumps({
            "pm_table": [{"offset": f"0x{i*4:04X}", "value": v}
                         for i, v in enumerate(values)],
        }, indent=2))
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
    p.add_argument("--info",         action="store_true")
    p.add_argument("--json",         action="store_true", dest="json_out")
    p.add_argument("--reapply",      type=int, default=0, metavar="SECONDS")
    p.add_argument("--dump-table",   action="store_true", dest="dump_table")
    p.add_argument("--table",        action="store_true")
    p.add_argument("--sensors",      action="store_true")
    p.add_argument("--version",      action="store_true")
    flags, rest = p.parse_known_args(argv)

    if flags.version:
        _show_update(flags.json_out)
        sys.exit(0)

    info = detect()

    if info.type not in ("Amd_Apu", "Amd_Desktop_Cpu"):
        print(f"ZenMaster: unsupported CPU '{info.name}' (only AMD Ryzen supported)", file=sys.stderr)
        sys.exit(1)

    if rest:
        known = runner.all_known_args()
        for token in rest:
            name = token.lstrip("-").partition("=")[0].replace("_", "-").lower()
            if not name:
                continue
            if name not in known or ("=" not in token and not runner.is_flag_arg(name)):
                _show_help(info)
                sys.exit(0)

    backend: str | None = None

    if flags.info:
        if _is_root():
            try:
                backend = smu.init()
            except RuntimeError as e:
                if not flags.json_out:
                    print(f"ZenMaster: backend unavailable: {e}", file=sys.stderr)
        _show_info(info, backend, flags.json_out)
        if not rest and not flags.dump_table and not flags.table and not flags.sensors:
            sys.exit(0)

    if (flags.table or flags.dump_table or flags.sensors or rest) and backend is None:
        if not _is_root():
            print("ZenMaster: root/admin privileges required.", file=sys.stderr)
            print("Run with sudo (Linux) or as Administrator (Windows).", file=sys.stderr)
            sys.exit(1)
        try:
            backend = smu.init()
        except RuntimeError as e:
            print(f"ZenMaster: backend error: {e}", file=sys.stderr)
            sys.exit(1)

    if flags.table:
        _show_table(flags.json_out, info.family)
        if not rest and not flags.dump_table and not flags.sensors:
            sys.exit(0)

    if flags.dump_table:
        _dump_pm_table(flags.json_out, info.family)
        if not rest and not flags.sensors:
            sys.exit(0)

    if flags.sensors:
        _show_sensors(flags.json_out, info.family)
        if not rest:
            sys.exit(0)

    if rest:
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
                print("\nZenMaster: stopped.")
