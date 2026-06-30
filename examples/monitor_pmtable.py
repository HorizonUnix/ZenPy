import os, sys, time, struct
import zenmaster
from zenmaster import smu

# Ported from RyzenAdj's get_table_values monitor — a live dump of every PM
# table float. ZenMaster reads the table fresh on each call, so there is no
# separate refresh step.

info = zenmaster.detect()

if smu.ensure_backend() is None:
    sys.exit("ZenMaster could not get initialized (run as root/admin)")

print("pmtable version: {:x}".format(smu.read_pm_table_version(info.family)))

input("Press any key to show all pmtable values...")

while True:
    data = smu.read_pm_table(info.family)
    if not data:
        sys.exit("PM table is not available on this platform/family")
    values = struct.unpack("<{:d}f".format(len(data) // 4), data[: (len(data) // 4) * 4])

    columns, lines = os.get_terminal_size()
    table_columns = columns // 16
    os.system("cls" if sys.platform == "win32" else "clear")
    table_rows = 0
    for index, value in enumerate(values):
        sys.stdout.write("{:3d}:{:8.2f}\t".format(index, value))
        if index % table_columns == table_columns - 1:
            sys.stdout.write("\n")
            table_rows += 1
            if table_rows >= lines - 1:
                sys.stdout.write("{:d} More entries ...".format(len(values) - 1 - index))
                break
    if index % table_columns != table_columns - 1:
        sys.stdout.write("\n")
    sys.stdout.flush()
    time.sleep(1)
