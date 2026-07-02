class ZenMasterError(RuntimeError):
    pass


class BackendUnavailable(ZenMasterError):
    _INSTALL_DOCS = "https://github.com/HorizonUnix/ZenMaster/wiki/Installation"

    def __init__(self, message: str):
        super().__init__(f"{message}\n\nInstallation guide: {self._INSTALL_DOCS}")


class SMUNotInitialized(ZenMasterError):
    pass


class UnsupportedCPU(ZenMasterError):
    pass
