import sys, time
from zenmaster import apply, detect, smu

# Ported from RyzenAdj's get_fast_limit reapply loop. Watches the live fast
# limit and re-applies the whole preset whenever it drifts off 35 W.
# read_pm_sensors(...).fast_limit replaces get_fast_limit; one apply() call
# replaces the per-field set_* calls. (The CLI does the same with --reapply=3.)

info = detect()

if smu.ensure_backend() is None:
    sys.exit("ZenMaster could not get initialized (run as root/admin)")

preset = ("--fast-limit=35000 --slow-limit=22000 --slow-time=30 "
          "--tctl-temp=97 --apu-skin-temp=50 --vrmmax-current=100000 --max-performance")

print("Monitor if fast limit is not 35W")
while True:
    sensors = smu.read_pm_sensors(info.family)
    limit = round(sensors.fast_limit) if sensors and sensors.fast_limit is not None else None
    if limit != 35:
        print("reapply limits, because old limit was {}".format(limit))
        results, rejected = apply(preset, info.family)
        for r in results:
            if r["error"] or r["status"] != smu.SMU_OK:
                sys.stderr.write("{:s} -> {:s}\n".format(
                    r["arg"], r["error"] or smu.status_name(r["status"])))
    time.sleep(3)
