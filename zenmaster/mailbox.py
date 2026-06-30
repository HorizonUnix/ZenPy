from __future__ import annotations

NARGS = 6

MP1: dict[str, tuple[int, int, int]] = {
    "SummitRidge":   (0x3B10528, 0x3B10564, 0x3B10598),
    "PinnacleRidge": (0x3B10528, 0x3B10564, 0x3B10598),
    "Matisse":       (0x3B10530, 0x3B1057C, 0x3B109C4),
    "Vermeer":       (0x3B10530, 0x3B1057C, 0x3B109C4),
    "VanGogh":       (0x3B10528, 0x3B10578, 0x3B10998),
    "Mendocino":     (0x3B10528, 0x3B10578, 0x3B10998),
    "Rembrandt":     (0x3B10528, 0x3B10578, 0x3B10998),
    "PhoenixPoint":  (0x3B10528, 0x3B10578, 0x3B10998),
    "PhoenixPoint2": (0x3B10528, 0x3B10578, 0x3B10998),
    "HawkPoint":     (0x3B10528, 0x3B10578, 0x3B10998),
    "HawkPoint2":    (0x3B10528, 0x3B10578, 0x3B10998),
    "SonomaValley":  (0x3B10528, 0x3B10578, 0x3B10998),
    "Raphael":       (0x3B10530, 0x3B1057C, 0x3B109C4),
    "DragonRange":   (0x3B10530, 0x3B1057C, 0x3B109C4),
    "GraniteRidge":  (0x3B10530, 0x3B1057C, 0x3B109C4),
    "FireRange":     (0x3B10530, 0x3B1057C, 0x3B109C4),
    "StrixPoint":    (0x3B10928, 0x3B10978, 0x3B10998),
    "KrackanPoint":  (0x3B10928, 0x3B10978, 0x3B10998),
    "KrackanPoint2": (0x3B10928, 0x3B10978, 0x3B10998),
    "StrixHalo":     (0x3B10928, 0x3B10978, 0x3B10998),
}
MP1_DEFAULT = (0x3B10528, 0x3B10564, 0x3B10998)

RSMU: dict[str, tuple[int, int, int]] = {
    "SummitRidge":   (0x3B1051C, 0x3B10568, 0x3B10590),
    "PinnacleRidge": (0x3B1051C, 0x3B10568, 0x3B10590),
    "Matisse":       (0x3B10524, 0x3B10570, 0x3B10A40),
    "Vermeer":       (0x3B10524, 0x3B10570, 0x3B10A40),
    "Raphael":       (0x3B10524, 0x3B10570, 0x3B10A40),
    "DragonRange":   (0x3B10524, 0x3B10570, 0x3B10A40),
    "GraniteRidge":  (0x3B10524, 0x3B10570, 0x3B10A40),
    "FireRange":     (0x3B10524, 0x3B10570, 0x3B10A40),
}
RSMU_DEFAULT = (0x3B10A20, 0x3B10A80, 0x3B10A88)
