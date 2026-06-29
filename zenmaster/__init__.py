from importlib.metadata import version, PackageNotFoundError

from zenmaster import runner, smu
from zenmaster.hardware import CpuInfo, detect
from zenmaster.apply import apply

try:
    __version__ = version("zenmaster")
except PackageNotFoundError:
    __version__ = "0.0.0"

__all__ = ["CpuInfo", "detect", "apply", "runner", "smu", "__version__"]
