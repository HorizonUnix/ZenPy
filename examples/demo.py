import sys
from zenmaster import __version__, detect, apply, smu, runner

print(f"ZenMaster {__version__}")

# CPU detection never needs root
info = detect()
print(info.name, info.family, runner.get_socket(info.family))

# Which args this CPU supports, and their SMU opcodes
print(runner.get_supported_args(info.family))
print(runner.lookup(info.family, "stapm-limit"))

# Flag args (enable-oc, power-saving, get-* etc.) take no value
print(runner.is_flag_arg("enable-oc"))
print(runner.is_flag_arg("stapm-limit"))

# SMU init — raises RuntimeError with a clear message on any failure
try:
    backend = smu.init()
    print("backend:", backend)
except RuntimeError as e:
    print(f"SMU unavailable: {e}", file=sys.stderr)
    sys.exit(1)

# Apply a preset string — same syntax as the CLI
results, rejected = apply("--stapm-limit=15000 --tctl-temp=90", info.family)
for r in results:
    if r["error"]:
        print(r["arg"], "->", r["error"])
    else:
        print(r["arg"], r["mailbox"], hex(r["opcode"]), "->", smu.status_name(r["status"]))

# Flag-only args: pass without =value
apply("--enable-oc", info.family)
apply("--power-saving", info.family)

# PM table — APU/mobile only (Renoir, Cezanne, Phoenix, etc.)
if smu.pm_table_supported(info.family):
    data = smu.read_pm_table(info.family)
    ver = smu.read_pm_table_version(info.family)
    print(f"pm table: version=0x{ver:08X} size={len(data)}")

# Raw SMU send — look up the opcode first, then send
for is_mp1, op in runner.lookup(info.family, "stapm-limit"):
    if is_mp1:
        rc = smu.send_mp1(info.family, op, 15000)
    else:
        rc = smu.send_rsmu(info.family, op, 15000)
    print(f"{'MP1' if is_mp1 else 'RSMU'} 0x{op:02X} ->", smu.status_name(rc))
