import struct
from unittest.mock import patch
import zenmaster.linux as linux
from zenmaster.pmtable import PM_TABLE_CMDS, TABLE_SIZES
from zenmaster.table import read_sensors
from zenmaster.smu import SMU_OK, SMU_FAILED


def test_pm_table_cmds_covers_old_and_new_apus():
    assert len(PM_TABLE_CMDS) == 19
    assert PM_TABLE_CMDS["RavenRidge"] == (0x0C, 0x0B, 0x3D, False, 3)
    assert PM_TABLE_CMDS["Renoir"] == (0x06, 0x66, 0x65, False, 0)
    assert PM_TABLE_CMDS["Rembrandt"][3] is True   # 64-bit addr


def test_table_sizes_known_versions():
    assert TABLE_SIZES[0x00370000] == 0x794
    assert TABLE_SIZES[0x001E0001] == 0x568


def test_linux_pci_reads_table():
    def q(family, op, arg0=0):
        return {0x06: (SMU_OK, [0x00370000] + [0] * 5),
                0x66: (SMU_OK, [0x1000] + [0] * 5),
                0x65: (SMU_OK, [0] * 6)}.get(op, (SMU_OK, [0] * 6))
    linux._backend = "pci"
    try:
        with patch("zenmaster.linux.query_rsmu", side_effect=q), \
             patch("zenmaster.linux._read_devmem", return_value=b"\xAA" * 0x794):
            assert linux.pm_table_supported("Renoir") is True
            assert len(linux.read_pm_table("Renoir")) == 0x794
            assert linux.read_pm_table_version("Renoir") == 0x00370000
    finally:
        linux._backend = None


def test_linux_pci_old_apu_passes_arg3():
    seen = []
    def q(family, op, arg0=0):
        seen.append((op, arg0))
        return {0x0C: (SMU_OK, [0x001E0001] + [0] * 5),
                0x0B: (SMU_OK, [0x2000] + [0] * 5)}.get(op, (SMU_OK, [0] * 6))
    linux._backend = "pci"
    try:
        with patch("zenmaster.linux.query_rsmu", side_effect=q), \
             patch("zenmaster.linux._read_devmem", return_value=b"x" * 0x568):
            linux.read_pm_table("Picasso")
    finally:
        linux._backend = None
    assert (0x0C, 0) in seen      # version op, no extra arg
    assert (0x0B, 3) in seen      # address op carries arg0=3
    assert (0x3D, 3) in seen      # transfer op carries arg0=3


def test_linux_pci_returns_none_on_reject():
    linux._backend = "pci"
    try:
        with patch("zenmaster.linux.query_rsmu", return_value=(SMU_FAILED, [0] * 6)):
            assert linux.read_pm_table("Renoir") is None
    finally:
        linux._backend = None


def _table_with(values):
    data = bytearray(b"\x00" * 0x800)
    for off, v in values.items():
        struct.pack_into("<f", data, off, v)
    return bytes(data)


def test_read_sensors_zen4_offsets():
    data = _table_with({0x00: 65.0, 0x04: 30.0, 0x44: 70.0, 0x104: 5.0,
                        0x98: 42.0, 0x648: 2400.0})
    s = read_sensors(data, 0x00400004)
    assert s.stapm_limit == 65.0
    assert s.stapm_value == 30.0
    assert s.tctl_temp == 70.0
    assert s.cclk_busy == 5.0
    assert s.socket_power == 42.0
    assert s.gfx_clk == 2400.0


def test_read_sensors_missing_field_is_none():
    s = read_sensors(b"\x00" * 0x20, 0x00400004)
    assert s.gfx_clk is None        # offset past the short buffer
    assert s.stapm_limit == 0.0     # in range, decodes to 0.0


def test_read_sensors_unknown_version_only_fixed():
    s = read_sensors(b"\x11" * 0x800, 0xDEADBEEF)
    assert s.stapm_limit is not None
    assert s.tctl_temp is None
    assert s.socket_power is None
