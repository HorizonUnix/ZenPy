from importlib.metadata import version, PackageNotFoundError

from zenmaster import runner, smu, table
from zenmaster.hardware import CpuInfo, detect, resolve
from zenmaster.apply import apply, ApplyResult
from zenmaster.update import check_update
from zenmaster.table import PmSensors, read_sensors
from zenmaster.smu import (
    SmuStatus, ModuleStatus, module_status, module_version, module_version_ok,
    secure_boot_enabled, is_available, ensure_backend, read_pm_sensors,
    send_arg, unavailable_reason, driver_name,
)
from zenmaster.errors import (
    ZenMasterError, BackendUnavailable, SMUNotInitialized, UnsupportedCPU,
)

try:
    __version__ = version("zenmaster")
except PackageNotFoundError:
    __version__ = "0.0.0"

__all__ = [
    "CpuInfo", "detect", "resolve", "apply", "ApplyResult", "runner", "smu", "table",
    "SmuStatus", "PmSensors", "read_sensors", "read_pm_sensors", "ModuleStatus",
    "module_status", "module_version", "module_version_ok", "secure_boot_enabled",
    "is_available", "ensure_backend", "send_arg", "unavailable_reason", "driver_name",
    "check_update", "ZenMasterError", "BackendUnavailable", "SMUNotInitialized",
    "UnsupportedCPU", "__version__",
]
