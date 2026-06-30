from importlib.metadata import version, PackageNotFoundError

from zenmaster import runner, smu
from zenmaster.hardware import CpuInfo, detect
from zenmaster.apply import apply, ApplyResult
from zenmaster.update import check_update
from zenmaster.smu import SmuStatus
from zenmaster.errors import (
    ZenMasterError, BackendUnavailable, SMUNotInitialized, UnsupportedCPU,
)

try:
    __version__ = version("zenmaster")
except PackageNotFoundError:
    __version__ = "0.0.0"

__all__ = [
    "CpuInfo", "detect", "apply", "ApplyResult", "runner", "smu", "SmuStatus",
    "check_update", "ZenMasterError", "BackendUnavailable", "SMUNotInitialized",
    "UnsupportedCPU", "__version__",
]
