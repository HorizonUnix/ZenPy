from __future__ import annotations
import math
import struct

_VRM_V1 = {0x001E0001, 0x001E0002, 0x001E0003, 0x001E0004,
            0x001E0005, 0x001E000A, 0x001E0101}
_VRM_V2 = {0x00370000, 0x00370001, 0x00370002, 0x00370003, 0x00370004, 0x00370005,
            0x00400001, 0x00400002, 0x00400003, 0x00400004, 0x00400005,
            0x00450004, 0x00450005,
            0x004C0006, 0x004C0007, 0x004C0008, 0x004C0009}
_VRM_V3 = {0x005D0008, 0x005D0009, 0x005D000B, 0x00650005}

_TCTL_V1 = _VRM_V1 | {0x0064020C}
_TCTL_V2 = {0x00370000, 0x00370001, 0x00370002, 0x00370003, 0x00370004, 0x00370005,
             0x003F0000, 0x00400001, 0x00400002, 0x00400003, 0x00400004, 0x00400005,
             0x00450004, 0x00450005,
             0x004C0006, 0x004C0007, 0x004C0008, 0x004C0009,
             0x005D0008, 0x005D0009, 0x005D000B, 0x00650005}

_APU_SLOW_VERS = _VRM_V2 | {0x003F0000, 0x005D0008, 0x005D0009, 0x005D000B, 0x0064020C, 0x00650005}

_SKIN_APU_VERS = {0x00370000, 0x00370001, 0x00370002, 0x00370003, 0x00370004, 0x00370005,
                  0x003F0000, 0x00400001, 0x00400002, 0x00400003, 0x00400004, 0x00400005,
                  0x00450004, 0x00450005,
                  0x004C0006, 0x004C0007, 0x004C0008, 0x004C0009,
                  0x005D0008, 0x005D0009, 0x005D000B, 0x0064020C}

_SKIN_DGPU_V2 = {0x00370000, 0x00370001, 0x00370002, 0x00370003, 0x00370004, 0x00370005,
                 0x00400001, 0x00400002, 0x00400003, 0x00400004, 0x00400005,
                 0x00450004, 0x00450005,
                 0x004C0006, 0x004C0007, 0x004C0008, 0x004C0009, 0x0064020C}
_SKIN_DGPU_V3 = {0x005D0008, 0x005D0009, 0x005D000B}

_STAPM_TIME: dict[int, int] = {
    0x001E0002: 0x564, 0x001E0003: 0x55C, 0x001E0004: 0x5E0, 0x001E0005: 0x5E0,
    0x001E000A: 0x5E0, 0x001E0101: 0x5E0,
    0x00370000: 0x768, 0x00370001: 0x858, 0x00370002: 0x860,
    0x00370003: 0x880, 0x00370004: 0x880, 0x00370005: 0x89C,
    0x00400001: 0x8E4, 0x00400002: 0x8FC, 0x00400003: 0x920,
    0x00400004: 0x918, 0x00400005: 0x918,
    0x004C0006: 0x918, 0x004C0007: 0x918, 0x004C0008: 0x918, 0x004C0009: 0x918,
    0x005D0008: 0x9BC, 0x005D0009: 0x9BC, 0x005D000B: 0x9BC,
    0x00650005: 0x90C,
}
_SLOW_TIME: dict[int, int] = {
    0x001E0002: 0x568, 0x001E0003: 0x560, 0x001E0004: 0x5E4, 0x001E0005: 0x5E4,
    0x001E000A: 0x5E4, 0x001E0101: 0x5E4,
    0x00370000: 0x76C, 0x00370001: 0x85C, 0x00370002: 0x864,
    0x00370003: 0x884, 0x00370004: 0x884, 0x00370005: 0x8A0,
    0x00400001: 0x8E8, 0x00400002: 0x900, 0x00400003: 0x924,
    0x00400004: 0x91C, 0x00400005: 0x91C,
    0x004C0006: 0x91C, 0x004C0007: 0x91C, 0x004C0008: 0x91C, 0x004C0009: 0x91C,
    0x005D0008: 0x9C0, 0x005D0009: 0x9C0, 0x005D000B: 0x9C0,
    0x00650005: 0x910,
}
_CCLK_SETPOINT: dict[int, int] = {
    0x001E0001: 0x98, 0x001E0002: 0x98, 0x001E0003: 0x98, 0x001E0004: 0x98,
    0x001E0005: 0x98, 0x001E000A: 0x98, 0x001E0101: 0x98,
    0x00370000: 0xFC, 0x00370001: 0xFC, 0x00370002: 0xFC,
    0x00370003: 0xFC, 0x00370004: 0xFC, 0x00370005: 0xFC,
    0x00400001: 0x100, 0x00400002: 0x100, 0x00400003: 0x100,
    0x00400004: 0x100, 0x00400005: 0x100,
    0x005D0008: 0xD0, 0x005D0009: 0xD0, 0x005D000B: 0xD0,
}
_CCLK_BUSY: dict[int, int] = {
    0x001E0001: 0x9C, 0x001E0002: 0x9C, 0x001E0003: 0x9C, 0x001E0004: 0x9C,
    0x001E0005: 0x9C, 0x001E000A: 0x9C, 0x001E0101: 0x9C,
    0x00370000: 0x100, 0x00370001: 0x100, 0x00370002: 0x100,
    0x00370003: 0x100, 0x00370004: 0x100, 0x00370005: 0x100,
    0x00400001: 0x104, 0x00400002: 0x104, 0x00400003: 0x104,
    0x00400004: 0x104, 0x00400005: 0x104,
    0x005D0008: 0xCC, 0x005D0009: 0xCC, 0x005D000B: 0xCC,
}


def _f(data: bytes, off: int | None) -> float:
    if off is None or off + 4 > len(data):
        return math.nan
    return struct.unpack_from("<f", data, off)[0]


def read_table(data: bytes, ver: int) -> list[tuple[str, float, str]]:
    def f(off): return _f(data, off)

    if ver in _VRM_V1:
        vrm_cur, vrm_cur_val = 0x18, 0x1C
        vrmsoc_cur, vrmsoc_cur_val = 0x20, 0x24
        vrmmax_cur, vrmmax_cur_val = 0x28, 0x2C
        vrmsocmax_cur, vrmsocmax_cur_val = 0x34, 0x38
    elif ver in _VRM_V2:
        vrm_cur, vrm_cur_val = 0x20, 0x24
        vrmsoc_cur, vrmsoc_cur_val = 0x28, 0x2C
        vrmmax_cur, vrmmax_cur_val = 0x30, 0x34
        vrmsocmax_cur, vrmsocmax_cur_val = 0x38, 0x3C
    elif ver in _VRM_V3:
        vrm_cur, vrm_cur_val = 0x30, 0x34
        vrmsoc_cur, vrmsoc_cur_val = 0x38, 0x3C
        vrmmax_cur = vrmmax_cur_val = vrmsocmax_cur = vrmsocmax_cur_val = None
    else:
        vrm_cur = vrm_cur_val = vrmsoc_cur = vrmsoc_cur_val = None
        vrmmax_cur = vrmmax_cur_val = vrmsocmax_cur = vrmsocmax_cur_val = None

    if ver in _TCTL_V1:
        tctl, tctl_val = 0x58, 0x5C
    elif ver in _TCTL_V2:
        tctl, tctl_val = 0x40, 0x44
    else:
        tctl = tctl_val = None

    apu_slow_lim  = 0x18 if ver in _APU_SLOW_VERS else None
    apu_slow_val  = 0x1C if ver in _APU_SLOW_VERS else None
    skin_apu_lim  = 0x58 if ver in _SKIN_APU_VERS else None
    skin_apu_val  = 0x5C if ver in _SKIN_APU_VERS else None

    if ver in _SKIN_DGPU_V2:
        skin_dgpu_lim, skin_dgpu_val = 0x60, 0x64
    elif ver in _SKIN_DGPU_V3:
        skin_dgpu_lim, skin_dgpu_val = 0x68, 0x6C
    else:
        skin_dgpu_lim = skin_dgpu_val = None

    rows: list[tuple[str, float, str]] = [
        ("STAPM LIMIT",        f(0x00), "stapm-limit"),
        ("STAPM VALUE",        f(0x04), ""),
        ("PPT LIMIT FAST",     f(0x08), "fast-limit"),
        ("PPT VALUE FAST",     f(0x0C), ""),
        ("PPT LIMIT SLOW",     f(0x10), "slow-limit"),
        ("PPT VALUE SLOW",     f(0x14), ""),
        ("StapmTimeConst",     f(_STAPM_TIME.get(ver)), "stapm-time"),
        ("SlowPPTTimeConst",   f(_SLOW_TIME.get(ver)),  "slow-time"),
        ("PPT LIMIT APU",      f(apu_slow_lim),  "apu-slow-limit"),
        ("PPT VALUE APU",      f(apu_slow_val),  ""),
        ("TDC LIMIT VDD",      f(vrm_cur),       "vrm-current"),
        ("TDC VALUE VDD",      f(vrm_cur_val),   ""),
        ("TDC LIMIT SOC",      f(vrmsoc_cur),    "vrmsoc-current"),
        ("TDC VALUE SOC",      f(vrmsoc_cur_val),""),
        ("EDC LIMIT VDD",      f(vrmmax_cur),    "vrmmax-current"),
        ("EDC VALUE VDD",      f(vrmmax_cur_val),""),
        ("EDC LIMIT SOC",      f(vrmsocmax_cur), "vrmsocmax-current"),
        ("EDC VALUE SOC",      f(vrmsocmax_cur_val), ""),
        ("THM LIMIT CORE",     f(tctl),          "tctl-temp"),
        ("THM VALUE CORE",     f(tctl_val),      ""),
        ("STT LIMIT APU",      f(skin_apu_lim),  "apu-skin-temp"),
        ("STT VALUE APU",      f(skin_apu_val),  ""),
        ("STT LIMIT dGPU",     f(skin_dgpu_lim), "dgpu-skin-temp"),
        ("STT VALUE dGPU",     f(skin_dgpu_val), ""),
        ("CCLK Boost SETPOINT",f(_CCLK_SETPOINT.get(ver)), "power-saving /"),
        ("CCLK BUSY VALUE",    f(_CCLK_BUSY.get(ver)),     "max-performance"),
    ]
    return [(label, val, flag) for label, val, flag in rows if not math.isnan(val)]
