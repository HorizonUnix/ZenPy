from unittest.mock import patch
from zenmaster.apply import apply
from zenmaster.smu import SMU_OK, SMU_FAILED


def test_apply_single_arg_ok():
    with patch("zenmaster.smu.send_mp1", return_value=SMU_OK), \
         patch("zenmaster.smu.send_rsmu", return_value=SMU_OK):
        results, rejected = apply("--stapm-limit=15000", "Rembrandt")
    assert not rejected
    assert any(r["arg"] == "stapm-limit" and r["status"] == SMU_OK for r in results)


def test_apply_unsupported_arg():
    results, rejected = apply("--nonexistent-arg=1", "Rembrandt")
    assert any(r["arg"] == "nonexistent-arg" and r["error"] for r in results)


def test_apply_result_always_has_error_key():
    with patch("zenmaster.smu.send_mp1", return_value=SMU_OK), \
         patch("zenmaster.smu.send_rsmu", return_value=SMU_OK):
        results, _ = apply("--stapm-limit=15000", "Rembrandt")
    assert all("error" in r for r in results)
    assert all(r["error"] is None for r in results)


def test_apply_flag_arg_no_value():
    with patch("zenmaster.smu.send_mp1", return_value=SMU_OK), \
         patch("zenmaster.smu.send_rsmu", return_value=SMU_OK):
        results, rejected = apply("--enable-oc", "Rembrandt")
    assert not rejected
    assert any(r["arg"] == "enable-oc" for r in results)


def test_apply_value_arg_without_value_is_error():
    results, rejected = apply("--stapm-limit", "Rembrandt")
    assert rejected
    assert any(r["arg"] == "stapm-limit" and r["error"] for r in results)


def test_apply_flag_arg_ignores_passed_value():
    captured = []
    def fake_mp1(family, op, arg0):
        captured.append(arg0)
        return SMU_OK
    with patch("zenmaster.smu.send_mp1", side_effect=fake_mp1), \
         patch("zenmaster.smu.send_rsmu", return_value=SMU_OK):
        apply("--max-performance=5", "Rembrandt")
    assert captured and all(v == 0 for v in captured)


def test_apply_negative_value_wraps_to_uint32():
    captured = []
    def fake_mp1(family, op, arg0):
        captured.append(arg0)
        return SMU_OK
    with patch("zenmaster.smu.send_mp1", side_effect=fake_mp1), \
         patch("zenmaster.smu.send_rsmu", return_value=SMU_OK):
        apply("--set-coall=-20", "Rembrandt")
    assert captured and all(v == 0xFFFFFFEC for v in captured)


def test_apply_get_command_returns_value():
    with patch("zenmaster.smu.query_mp1", return_value=(SMU_OK, [1234, 0, 0, 0, 0, 0])), \
         patch("zenmaster.smu.query_rsmu", return_value=(SMU_OK, [1234, 0, 0, 0, 0, 0])):
        results, rejected = apply("--get-pbo-scalar", "Raphael")
    assert not rejected
    assert any(r["arg"] == "get-pbo-scalar" and r["returned"] == 1234 for r in results)


def test_apply_get_command_returned_none_on_reject():
    from zenmaster.smu import SMU_FAILED
    with patch("zenmaster.smu.query_mp1", return_value=(SMU_FAILED, [0] * 6)), \
         patch("zenmaster.smu.query_rsmu", return_value=(SMU_FAILED, [0] * 6)):
        results, rejected = apply("--get-pbo-scalar", "Raphael")
    assert rejected
    assert all(r["returned"] is None for r in results)


def test_apply_set_command_returned_is_none():
    with patch("zenmaster.smu.send_mp1", return_value=SMU_OK), \
         patch("zenmaster.smu.send_rsmu", return_value=SMU_OK):
        results, _ = apply("--stapm-limit=15000", "Rembrandt")
    assert all(r["returned"] is None for r in results)


def test_apply_hex_value():
    captured = []
    def fake_mp1(family, op, arg0):
        captured.append(arg0)
        return SMU_OK
    with patch("zenmaster.smu.send_mp1", side_effect=fake_mp1), \
         patch("zenmaster.smu.send_rsmu", return_value=SMU_OK):
        apply("--stapm-limit=0x3a98", "Rembrandt")
    assert 0x3a98 in captured


def test_apply_unknown_family():
    results, rejected = apply("--stapm-limit=15000", "UnknownCPU")
    assert any(r["arg"] == "stapm-limit" and r["status"] == 0 for r in results)


def test_apply_rejected_counts_as_rejection():
    with patch("zenmaster.smu.send_mp1", return_value=SMU_FAILED), \
         patch("zenmaster.smu.send_rsmu", return_value=SMU_FAILED):
        results, rejected = apply("--stapm-limit=15000", "Rembrandt")
    assert rejected


def test_apply_skin_temp_scale():
    captured = []
    def fake_send_mp1(family, op, arg0):
        captured.append(arg0)
        return SMU_OK
    with patch("zenmaster.smu.send_mp1", side_effect=fake_send_mp1), \
         patch("zenmaster.smu.send_rsmu", return_value=SMU_OK):
        apply("--apu-skin-temp=45", "Rembrandt")
    assert any(v == 45 * 256 for v in captured)


def test_apply_skin_temp_limit_not_scaled():
    captured = []
    def fake_send_mp1(family, op, arg0):
        captured.append(arg0)
        return SMU_OK
    with patch("zenmaster.smu.send_mp1", side_effect=fake_send_mp1), \
         patch("zenmaster.smu.send_rsmu", return_value=SMU_OK):
        apply("--skin-temp-limit=15000", "Rembrandt")
    assert captured and all(v == 15000 for v in captured)


def test_apply_multiple_args():
    with patch("zenmaster.smu.send_mp1", return_value=SMU_OK), \
         patch("zenmaster.smu.send_rsmu", return_value=SMU_OK):
        results, rejected = apply("--stapm-limit=15000 --tctl-temp=85", "Rembrandt")
    arg_names = [r["arg"] for r in results]
    assert "stapm-limit" in arg_names
    assert "tctl-temp" in arg_names


def test_apply_empty_string():
    results, rejected = apply("", "Rembrandt")
    assert results == []
    assert not rejected


def test_apply_normalises_name_in_result():
    with patch("zenmaster.smu.send_mp1", return_value=SMU_OK), \
         patch("zenmaster.smu.send_rsmu", return_value=SMU_OK):
        results, _ = apply("--STAPM_LIMIT=15000", "Rembrandt")
    assert any(r["arg"] == "stapm-limit" for r in results)


def test_apply_unclosed_quote_returns_error():
    results, rejected = apply("--stapm-limit='15000", "Rembrandt")
    assert rejected
    assert results[0]["error"]


def test_apply_strips_leading_dashes():
    with patch("zenmaster.smu.send_mp1", return_value=SMU_OK), \
         patch("zenmaster.smu.send_rsmu", return_value=SMU_OK):
        r1, _ = apply("--stapm-limit=15000", "Rembrandt")
        r2, _ = apply("stapm-limit=15000", "Rembrandt")
    assert len(r1) == len(r2)
