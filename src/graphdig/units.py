"""Unit handling for historical measurement systems.

The Danube charts switch from Bavarian feet to millimetres on 1872-04-01 (Rehbein 2026,
Sect. 4.3). The Bavarian foot constant defaults to 291.859 mm (das bayerische Fuss,
1 Fuss = 12 Zoll); confirm against the dataset descriptor and override via constants
if a different convention was used.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date

BAVARIAN_FOOT_MM = 291.859
BAVARIAN_ZOLL_MM = BAVARIAN_FOOT_MM / 12.0

DANUBE_UNIT_TRANSITION = date(1872, 4, 1)


@dataclass(frozen=True)
class Unit:
    canonical: str
    to_mm: float | None  # None: not a length unit / unknown; series stays in native units


_UNITS: dict[str, Unit] = {
    "mm": Unit("mm", 1.0),
    "cm": Unit("cm", 10.0),
    "m": Unit("m", 1000.0),
    "bavarian_foot": Unit("bavarian_foot", BAVARIAN_FOOT_MM),
    "bavarian_zoll": Unit("bavarian_zoll", BAVARIAN_ZOLL_MM),
}

# raw-label patterns -> canonical name (German-language historical sources)
_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"^m(illi)?m(eter)?s?\.?$", re.I), "mm"),
    (re.compile(r"^c(enti)?m(eter)?s?\.?$", re.I), "cm"),
    (re.compile(r"^m(eter)?s?\.?$", re.I), "m"),
    (re.compile(r"fu(ß|ss)", re.I), "bavarian_foot"),
    (re.compile(r"schuh", re.I), "bavarian_foot"),  # older synonym
    (re.compile(r"zoll", re.I), "bavarian_zoll"),
]


def canonicalize(raw: str | None) -> Unit:
    """Map a raw axis-unit label to a canonical unit. Unknown labels keep to_mm=None."""
    if not raw:
        return Unit("unknown", None)
    text = raw.strip()
    for pattern, name in _PATTERNS:
        if pattern.search(text):
            return _UNITS[name]
    key = text.lower()
    if key in _UNITS:
        return _UNITS[key]
    return Unit(text, None)


def to_mm(value: float, unit: Unit) -> float | None:
    return value * unit.to_mm if unit.to_mm is not None else None


def danube_unit_for(day: date) -> Unit:
    """Unit in force on the Danube charts at a given date (foot before 1872-04-01, mm after)."""
    if day < DANUBE_UNIT_TRANSITION:
        return _UNITS["bavarian_foot"]
    return _UNITS["mm"]
