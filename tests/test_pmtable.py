from unittest.mock import patch
import zenmaster.linux as linux
from zenmaster.pmtable import PM_TABLE_CMDS, TABLE_SIZES
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
