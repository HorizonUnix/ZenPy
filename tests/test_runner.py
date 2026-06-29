from zenmaster.runner import lookup, get_supported_args, get_socket, get_socket_short, has_smu_support


def test_lookup_rembrandt_stapm():
    results = lookup("Rembrandt", "stapm-limit")
    assert len(results) >= 1
    assert any(is_mp1 and op == 0x14 for is_mp1, op in results)


def test_lookup_raphael_ppt():
    results = lookup("Raphael", "ppt-limit")
    assert len(results) >= 1


def test_lookup_unsupported_arg():
    results = lookup("Rembrandt", "nonexistent-arg")
    assert results == []


def test_lookup_unknown_family():
    results = lookup("UnknownCPU", "stapm-limit")
    assert results == []


def test_lookup_normalises_dashes_underscores():
    r1 = lookup("Rembrandt", "stapm-limit")
    r2 = lookup("Rembrandt", "stapm_limit")
    assert r1 == r2


def test_lookup_strips_leading_dashes():
    r1 = lookup("Rembrandt", "stapm-limit")
    r2 = lookup("Rembrandt", "--stapm-limit")
    assert r1 == r2


def test_get_supported_args_rembrandt():
    args = get_supported_args("Rembrandt")
    assert "stapm-limit" in args
    assert "tctl-temp" in args
    assert len(args) == len(set(args))


def test_get_socket_rembrandt():
    assert get_socket("Rembrandt") == "FT6_FP7_FP8"


def test_get_socket_raphael():
    assert get_socket("Raphael") == "AM5_V1"


def test_get_socket_unknown():
    assert get_socket("UnknownCPU") is None


def test_get_socket_short_rembrandt():
    assert get_socket_short("Rembrandt") == "FP7"


def test_has_smu_support():
    assert has_smu_support("Rembrandt") is True
    assert has_smu_support("Raphael") is True
    assert has_smu_support("UnknownCPU") is False
