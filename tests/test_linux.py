import struct
from unittest.mock import patch, mock_open
from zenmaster import linux


def _fake_pci(readback):
    state = {}
    def fake_open(path, flags):
        return 7
    def fake_lseek(fd, off, whence):
        state["off"] = off
    def fake_write(fd, data):
        state["last"] = data
        return len(data)
    def fake_read(fd, n):
        return struct.pack("<I", readback)
    def fake_close(fd):
        pass
    return fake_open, fake_lseek, fake_write, fake_read, fake_close


def test_pci_writable_true_on_roundtrip():
    o, l, w, r, c = _fake_pci(0x47)
    with patch("os.path.exists", return_value=True), \
         patch("os.open", o), patch("os.lseek", l), patch("os.write", w), \
         patch("os.read", r), patch("os.close", c):
        assert linux._pci_writable() is True


def test_pci_writable_false_on_bad_readback():
    o, l, w, r, c = _fake_pci(0x00)
    with patch("os.path.exists", return_value=True), \
         patch("os.open", o), patch("os.lseek", l), patch("os.write", w), \
         patch("os.read", r), patch("os.close", c):
        assert linux._pci_writable() is False


def test_pci_writable_false_when_missing():
    with patch("os.path.exists", return_value=False):
        assert linux._pci_writable() is False


def test_init_secure_boot_on_uses_ryzen_smu():
    linux._backend = None
    with patch("zenmaster.linux.secure_boot_enabled", return_value=True), \
         patch("os.path.isdir", return_value=True), \
         patch("os.path.exists", return_value=True), \
         patch("zenmaster.linux.module_version_ok", return_value=True):
        assert linux.init() == "ryzen_smu"
    linux._backend = None


def test_init_secure_boot_no_module_raises():
    linux._backend = None
    with patch("zenmaster.linux.secure_boot_enabled", return_value=True), \
         patch("os.path.isdir", return_value=False):
        try:
            linux.init()
            assert False, "expected RuntimeError"
        except RuntimeError as e:
            assert "Secure Boot" in str(e)
    linux._backend = None


def test_init_secure_boot_old_module_raises():
    linux._backend = None
    with patch("zenmaster.linux.secure_boot_enabled", return_value=True), \
         patch("os.path.isdir", return_value=True), \
         patch("os.path.exists", return_value=True), \
         patch("zenmaster.linux.module_version", return_value="0.1.5"), \
         patch("zenmaster.linux.module_version_ok", return_value=False):
        try:
            linux.init()
            assert False, "expected RuntimeError"
        except RuntimeError as e:
            assert "0.1.5" in str(e) and "0.1.7" in str(e)
    linux._backend = None


def test_module_version_ok_reads_drv_version():
    with patch("builtins.open", mock_open(read_data="0.1.7\n")):
        assert linux.module_version() == "0.1.7"
        assert linux.module_version_ok() is True
    with patch("builtins.open", mock_open(read_data="0.1.5")):
        assert linux.module_version_ok() is False
    with patch("builtins.open", side_effect=OSError):
        assert linux.module_version() == "unknown"
        assert linux.module_version_ok() is False


def test_init_sb_off_uses_pci_even_with_module_loaded():
    linux._backend = None
    with patch("zenmaster.linux.secure_boot_enabled", return_value=False), \
         patch("os.path.isdir", return_value=True), \
         patch("zenmaster.linux._pci_writable", return_value=True):
        assert linux.init() == "pci"
    linux._backend = None


def test_init_sb_off_pci_not_writable_raises():
    linux._backend = None
    with patch("zenmaster.linux.secure_boot_enabled", return_value=False), \
         patch("zenmaster.linux._pci_writable", return_value=False), \
         patch("os.path.exists", return_value=True):
        try:
            linux.init()
            assert False, "expected RuntimeError"
        except RuntimeError as e:
            assert "not writable" in str(e)
    linux._backend = None
