class ZenMasterError(RuntimeError):
    pass


class BackendUnavailable(ZenMasterError):
    pass


class SMUNotInitialized(ZenMasterError):
    pass


class UnsupportedCPU(ZenMasterError):
    pass
