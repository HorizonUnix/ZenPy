from unittest.mock import patch, mock_open
from zenmaster.hardware import detect, resolve, _parse_cpuinfo, _resolve_codename, _cpu_type

CPUINFO_REMBRANDT = """processor\t: 0
vendor_id\t: AuthenticAMD
cpu family\t: 25
model\t\t: 68
model name\t: AMD Ryzen 5 7535HS with Radeon Graphics
stepping\t: 1
"""

CPUINFO_RAPHAEL = """processor\t: 0
cpu family\t: 25
model\t\t: 97
model name\t: AMD Ryzen 9 7950X
"""

CPUINFO_GRANITE = """processor\t: 0
cpu family\t: 26
model\t\t: 68
model name\t: AMD Ryzen 9 9950X
"""


def test_parse_cpuinfo_rembrandt():
    with patch("builtins.open", mock_open(read_data=CPUINFO_REMBRANDT)):
        fam, model, name = _parse_cpuinfo()
    assert fam == 25
    assert model == 68
    assert "7535HS" in name


def test_parse_cpuinfo_raphael():
    with patch("builtins.open", mock_open(read_data=CPUINFO_RAPHAEL)):
        fam, model, name = _parse_cpuinfo()
    assert fam == 25
    assert model == 97


def test_resolve_rembrandt():
    arch, family = _resolve_codename("AMD Ryzen 5 7535HS", 25, 68)
    assert family == "Rembrandt"
    assert "Zen 3" in arch


def test_resolve_raphael():
    arch, family = _resolve_codename("AMD Ryzen 9 7950X", 25, 97)
    assert family == "Raphael"


def test_resolve_dragonrange():
    arch, family = _resolve_codename("AMD Ryzen 9 7945HX", 25, 97)
    assert family == "DragonRange"


def test_resolve_granite_ridge():
    arch, family = _resolve_codename("AMD Ryzen 9 9950X", 26, 68)
    assert family == "GraniteRidge"


def test_resolve_intel():
    arch, family = _resolve_codename("Intel Core i7", 6, 85)
    assert arch == "Intel"
    assert family == "Intel"


def test_cpu_type_apu():
    assert _cpu_type("Rembrandt", "Zen 3 - Zen 4") == "Amd_Apu"


def test_cpu_type_desktop():
    assert _cpu_type("Raphael", "Zen 3 - Zen 4") == "Amd_Desktop_Cpu"


def test_cpu_type_unknown():
    assert _cpu_type("Unknown", "Unknown") == "Unknown"


def test_detect_linux():
    with patch("platform.system", return_value="Linux"), \
         patch("builtins.open", mock_open(read_data=CPUINFO_REMBRANDT)):
        info = detect()
    assert info.family == "Rembrandt"
    assert info.type == "Amd_Apu"
    assert info.cpu_family_int == 25
    assert info.cpu_model_int == 68


def test_resolve_from_values():
    info = resolve("AMD Ryzen 9 7950X", 25, 97)
    assert info.family == "Raphael"
    assert info.type == "Amd_Desktop_Cpu"
    assert info.cpu_family_int == 25
    assert info.cpu_model_int == 97


def test_resolve_does_not_read_cpuinfo():
    with patch("builtins.open", side_effect=AssertionError("must not read /proc/cpuinfo")):
        info = resolve("AMD Ryzen 7 7840U", 25, 116)
    assert info.family == "PhoenixPoint"


def test_detect_windows():
    with patch("platform.system", return_value="Windows"), \
         patch("os.environ.get", side_effect=lambda k, d="": {
             "PROCESSOR_IDENTIFIER": "AMD64 Family 25 Model 97 Stepping 2"
         }.get(k, d)):
        info = detect()
    assert info.family == "Raphael"
    assert info.cpu_family_int == 25
    assert info.cpu_model_int == 97
