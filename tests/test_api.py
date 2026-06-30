from zenmaster import (
    ZenMasterError, BackendUnavailable, SMUNotInitialized, UnsupportedCPU,
    SmuStatus, ApplyResult, smu,
)


def test_exception_hierarchy():
    assert issubclass(BackendUnavailable, ZenMasterError)
    assert issubclass(SMUNotInitialized, ZenMasterError)
    assert issubclass(UnsupportedCPU, ZenMasterError)


def test_exceptions_are_runtimeerror_for_backcompat():
    assert issubclass(ZenMasterError, RuntimeError)


def test_smu_status_enum_values():
    assert SmuStatus.OK == 0x01
    assert SmuStatus.FAILED == 0xFF
    assert SmuStatus.UNKNOWN_CMD == 0xFE


def test_smu_constants_alias_enum():
    assert smu.SMU_OK is SmuStatus.OK
    assert smu.SMU_FAILED is SmuStatus.FAILED


def test_status_name_accepts_plain_int():
    assert smu.status_name(0x01) == "OK"
    assert smu.status_name(SmuStatus.OK) == "OK"
    assert smu.status_name(0x123) == "0x123"


def test_apply_result_contract_keys():
    assert set(ApplyResult.__annotations__) == {
        "arg", "value", "mailbox", "opcode", "status", "error", "returned",
    }
