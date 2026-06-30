from unittest.mock import patch
import zenmaster
import zenmaster.linux as linux
import zenmaster.windows as windows
import zenmaster.smu as smu


def test_public_surface_reexported():
    for name in ("module_status", "module_version", "module_version_ok",
                 "secure_boot_enabled", "is_available", "ensure_backend",
                 "read_pm_sensors", "read_sensors", "PmSensors", "ModuleStatus", "table"):
        assert hasattr(zenmaster, name), name


def test_linux_module_status_ok():
    with patch("zenmaster.linux.os.path.isdir", return_value=True), \
         patch("zenmaster.linux.module_version", return_value="0.1.7"):
        st = linux.module_status()
    assert st.ok and st.reason is None and st.version == "0.1.7"
    assert st.min_version == "0.1.7"


def test_linux_module_status_too_old():
    with patch("zenmaster.linux.os.path.isdir", return_value=True), \
         patch("zenmaster.linux.module_version", return_value="0.1.5"):
        st = linux.module_status()
    assert not st.ok and st.reason == "too_old" and st.version == "0.1.5"


def test_linux_module_status_unknown():
    with patch("zenmaster.linux.os.path.isdir", return_value=True), \
         patch("zenmaster.linux.module_version", return_value="unknown"):
        st = linux.module_status()
    assert not st.ok and st.reason == "unknown"


def test_linux_module_status_not_loaded():
    with patch("zenmaster.linux.os.path.isdir", return_value=False), \
         patch("zenmaster.linux.os.path.exists", return_value=False):
        st = linux.module_status()
    assert not st.ok and st.reason == "not_loaded"


def test_windows_module_status_no_version_gate():
    with patch("zenmaster.windows._pawnio_info", return_value="3.0"):
        st = windows.module_status()
    assert st.ok and st.reason is None and st.version == "3.0"
    assert st.min_version == ""


def test_windows_module_status_not_loaded():
    with patch("zenmaster.windows._pawnio_info", return_value=None):
        st = windows.module_status()
    assert not st.ok and st.reason == "not_loaded"


def test_windows_secure_boot_is_false():
    assert windows.secure_boot_enabled() is False


def test_ensure_backend_returns_active_without_reinit():
    with patch("zenmaster.smu.active_backend", return_value="pci"), \
         patch("zenmaster.smu.init") as init:
        assert smu.ensure_backend() == "pci"
        init.assert_not_called()


def test_ensure_backend_swallows_unavailable():
    from zenmaster.errors import BackendUnavailable
    with patch("zenmaster.smu.active_backend", return_value=None), \
         patch("zenmaster.smu.init", side_effect=BackendUnavailable("no root")):
        assert smu.ensure_backend() is None


def test_read_pm_sensors_none_when_no_table():
    with patch("zenmaster.smu.ensure_backend", return_value="pci"), \
         patch("zenmaster.smu.read_pm_table", return_value=None):
        assert smu.read_pm_sensors("Renoir") is None


def test_read_pm_sensors_decodes():
    import struct
    data = bytearray(b"\x00" * 0x800)
    struct.pack_into("<f", data, 0x00, 65.0)
    with patch("zenmaster.smu.ensure_backend", return_value="ryzen_smu"), \
         patch("zenmaster.smu.read_pm_table", return_value=bytes(data)), \
         patch("zenmaster.smu.read_pm_table_version", return_value=0x00400004):
        s = smu.read_pm_sensors("Phoenix")
    assert s is not None and s.stapm_limit == 65.0


def test_send_arg_tries_every_mailbox():
    import zenmaster.runner as runner
    with patch("zenmaster.smu.ensure_backend", return_value="pci"), \
         patch.object(runner, "lookup", return_value=[(True, 0x39), (False, 0x92)]), \
         patch("zenmaster.smu.send_mp1", return_value=smu.SMU_OK) as mp1, \
         patch("zenmaster.smu.send_rsmu", return_value=smu.SMU_FAILED) as rsmu:
        out = smu.send_arg("Rembrandt", "fast-limit", 15000)
    assert out == [("MP1", 0x39, smu.SMU_OK), ("RSMU", 0x92, smu.SMU_FAILED)]
    mp1.assert_called_once_with("Rembrandt", 0x39, 15000)
    rsmu.assert_called_once_with("Rembrandt", 0x92, 15000)


def test_send_arg_unsupported_is_empty():
    import zenmaster.runner as runner
    with patch("zenmaster.smu.ensure_backend", return_value="pci"), \
         patch.object(runner, "lookup", return_value=[]):
        assert smu.send_arg("Rembrandt", "no-such-arg", 0) == []


def test_send_arg_swallows_send_exception():
    import zenmaster.runner as runner
    with patch("zenmaster.smu.ensure_backend", return_value="pci"), \
         patch.object(runner, "lookup", return_value=[(True, 0x39)]), \
         patch("zenmaster.smu.send_mp1", side_effect=RuntimeError("not init")):
        out = smu.send_arg("Rembrandt", "fast-limit", 1)
    assert out == [("MP1", 0x39, smu.SMU_FAILED)]


def test_unavailable_reason_none_when_backend_active():
    with patch("zenmaster.smu.active_backend", return_value="pci"), \
         patch("zenmaster.smu.init") as init:
        assert smu.unavailable_reason() is None
        init.assert_not_called()


def test_unavailable_reason_returns_init_message():
    from zenmaster.errors import BackendUnavailable
    with patch("zenmaster.smu.active_backend", return_value=None), \
         patch("zenmaster.smu.init", side_effect=BackendUnavailable("ryzen_smu 0.1.5 is too old")):
        assert smu.unavailable_reason() == "ryzen_smu 0.1.5 is too old"


def test_runner_is_supported():
    import zenmaster.runner as runner
    assert runner.is_supported("Rembrandt") is True
    assert runner.is_supported("NotACpu") is False
