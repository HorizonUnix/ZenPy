import json
from unittest.mock import patch
from zenmaster import cli
from zenmaster.smu import ModuleStatus
from zenmaster.table import PmSensors
from zenmaster.hardware import CpuInfo


def test_driver_line_pci_says_direct():
    assert cli._driver_line("pci") == "PCI direct access"


def test_driver_line_ok():
    st = ModuleStatus(True, "0.1.7", "0.1.7", None)
    with patch("zenmaster.smu.module_status", return_value=st), \
         patch("zenmaster.smu.driver_name", return_value="ryzen_smu"):
        assert cli._driver_line("ryzen_smu") == "ryzen_smu 0.1.7 (OK)"


def test_driver_line_too_old():
    st = ModuleStatus(False, "0.1.5", "0.1.7", "too_old")
    with patch("zenmaster.smu.module_status", return_value=st), \
         patch("zenmaster.smu.driver_name", return_value="ryzen_smu"):
        assert cli._driver_line("ryzen_smu") == "ryzen_smu 0.1.5 — too old (need 0.1.7)"


def test_driver_line_not_loaded():
    st = ModuleStatus(False, "unknown", "0.1.7", "not_loaded")
    with patch("zenmaster.smu.module_status", return_value=st), \
         patch("zenmaster.smu.driver_name", return_value="ryzen_smu"):
        assert cli._driver_line(None) == "ryzen_smu (not loaded)"


def test_show_info_includes_driver_line(capsys):
    info = CpuInfo("AMD Ryzen 9 7950X", "Raphael", "Zen 4", "Amd_Desktop_Cpu", 25, 97)
    st = ModuleStatus(True, "0.1.7", "0.1.7", None)
    with patch("zenmaster.smu.module_status", return_value=st), \
         patch("zenmaster.smu.driver_name", return_value="ryzen_smu"):
        cli._show_info(info, "pci", json_out=False)
    assert "Driver : PCI direct access" in capsys.readouterr().out


def test_show_sensors_text_skips_none(capsys):
    s = PmSensors(tctl_temp=64.0, cclk_busy=38.5, socket_power=41.2)
    with patch("zenmaster.smu.read_pm_sensors", return_value=s):
        cli._show_sensors(json_out=False, family="Phoenix")
    out = capsys.readouterr().out
    assert "CPU Temp" in out and "64.0" in out
    assert "iGPU Clock" not in out          # gfx_clk is None → skipped


def test_show_sensors_json_is_full_dataclass(capsys):
    s = PmSensors(tctl_temp=64.0, gfx_clk=2400.0)
    with patch("zenmaster.smu.read_pm_sensors", return_value=s):
        cli._show_sensors(json_out=True, family="Phoenix")
    data = json.loads(capsys.readouterr().out)
    assert data["tctl_temp"] == 64.0 and data["gfx_clk"] == 2400.0
    assert data["mem_clk"] is None          # full shape, None preserved


def test_show_sensors_no_table_errors(capsys):
    with patch("zenmaster.smu.read_pm_sensors", return_value=None):
        try:
            cli._show_sensors(json_out=True, family="Phoenix")
        except SystemExit as e:
            assert e.code == 1
    assert "error" in capsys.readouterr().out
