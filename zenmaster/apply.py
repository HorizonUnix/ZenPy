from __future__ import annotations
import shlex
from typing import TypedDict
from zenmaster import runner, smu


class ApplyResult(TypedDict):
    arg: str
    value: int
    mailbox: str
    opcode: int
    status: int
    error: str | None
    returned: int | None


_SKIN_ARGS = {"apu-skin-temp", "dgpu-skin-temp"}


def _skin_scale(arg_name: str, value: int) -> int:
    return value * 256 if arg_name in _SKIN_ARGS else value


def _error(name: str, msg: str) -> ApplyResult:
    return {"arg": name, "value": 0, "mailbox": "", "opcode": 0,
            "status": 0, "error": msg, "returned": None}


def apply(args_str: str, family: str) -> tuple[list[ApplyResult], bool]:
    try:
        tokens = shlex.split(args_str) if args_str.strip() else []
    except ValueError:
        return [_error("", "invalid preset string (unclosed quote)")], True

    results: list[ApplyResult] = []
    had_rejection = False

    for token in tokens:
        raw_name, sep, val_str = token.lstrip("-").partition("=")
        name = raw_name.replace("_", "-").lower()
        if not name:
            continue

        if runner.is_flag_arg(name):
            value = 0
        elif not sep:
            results.append(_error(name, f"--{name} requires a value"))
            had_rejection = True
            continue
        else:
            try:
                value = int(val_str, 0)
            except ValueError:
                results.append(_error(name, f"invalid value '{val_str}'"))
                had_rejection = True
                continue

        matches = runner.lookup(family, name)
        if not matches:
            results.append(_error(name, f"not supported on {family}"))
            had_rejection = True
            continue

        is_query = name.startswith("get-")
        smu_val = _skin_scale(name, value) & 0xFFFFFFFF

        any_ok = False
        for is_mp1, op in matches:
            returned = None
            if is_query:
                if is_mp1:
                    status, out = smu.query_mp1(family, op)
                else:
                    status, out = smu.query_rsmu(family, op)
                if status == smu.SMU_OK:
                    returned = out[0]
            elif is_mp1:
                status = smu.send_mp1(family, op, smu_val)
            else:
                status = smu.send_rsmu(family, op, smu_val)
            mailbox = "MP1" if is_mp1 else "RSMU"
            if status == smu.SMU_OK:
                any_ok = True
            results.append({"arg": name, "value": value, "mailbox": mailbox,
                             "opcode": op, "status": status, "error": None, "returned": returned})

        if not any_ok:
            had_rejection = True

    return results, had_rejection
