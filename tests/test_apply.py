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
    assert any(r["arg"] == "nonexistent-arg" and r["status"] == 0 for r in results)


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


def test_apply_strips_leading_dashes():
    with patch("zenmaster.smu.send_mp1", return_value=SMU_OK), \
         patch("zenmaster.smu.send_rsmu", return_value=SMU_OK):
        r1, _ = apply("--stapm-limit=15000", "Rembrandt")
        r2, _ = apply("stapm-limit=15000", "Rembrandt")
    assert len(r1) == len(r2)
