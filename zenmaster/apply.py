from __future__ import annotations
import shlex
from zenmaster import runner, smu

_SKIN_ARGS = {"apu-skin-temp", "dgpu-skin-temp"}


def _skin_scale(arg_name: str, value: int) -> int:
    return value * 256 if arg_name in _SKIN_ARGS else value


def apply(args_str: str, family: str) -> tuple[list[dict], bool]:
    try:
        tokens = shlex.split(args_str) if args_str.strip() else []
    except ValueError:
        return [{"arg": "", "value": 0, "mailbox": "", "opcode": 0,
                 "status": 0, "error": "invalid preset string (unclosed quote)"}], True

    results: list[dict] = []
    had_rejection = False

    for token in tokens:
        token = token.lstrip("-")
        if not token:
            continue

        if "=" in token:
            raw_name, _, val_str = token.partition("=")
            name = raw_name.replace("_", "-").lower()
            try:
                value = int(val_str, 0)
            except ValueError:
                results.append({"arg": name, "value": 0, "mailbox": "", "opcode": 0,
                                 "status": 0, "error": f"invalid value '{val_str}'"})
                continue
        else:
            name = token.replace("_", "-").lower()
            if not runner.is_flag_arg(name):
                results.append({"arg": name, "value": 0, "mailbox": "", "opcode": 0,
                                 "status": 0, "error": f"--{name} requires a value"})
                had_rejection = True
                continue
            value = 0

        if runner.is_flag_arg(name):
            value = 0

        matches = runner.lookup(family, name)
        if not matches:
            results.append({"arg": name, "value": value, "mailbox": "", "opcode": 0,
                             "status": 0, "error": f"not supported on {family}"})
            had_rejection = True
            continue

        smu_val = _skin_scale(name, value) & 0xFFFFFFFF

        any_ok = False
        for is_mp1, op in matches:
            if is_mp1:
                status = smu.send_mp1(family, op, smu_val)
                mailbox = "MP1"
            else:
                status = smu.send_rsmu(family, op, smu_val)
                mailbox = "RSMU"
            if status == smu.SMU_OK:
                any_ok = True
            results.append({"arg": name, "value": value, "mailbox": mailbox,
                             "opcode": op, "status": status, "error": None})

        if not any_ok:
            had_rejection = True

    return results, had_rejection
