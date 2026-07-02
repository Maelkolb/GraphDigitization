from datetime import date

import pytest

from graphdig.units import (
    BAVARIAN_FOOT_MM,
    canonicalize,
    danube_unit_for,
    to_mm,
)


@pytest.mark.parametrize("raw,canonical", [
    ("mm", "mm"),
    ("Millimeter", "mm"),
    ("Fuß", "bavarian_foot"),
    ("Fuss", "bavarian_foot"),
    ("bayer. Fuß", "bavarian_foot"),
    ("Schuh", "bavarian_foot"),
    ("Zoll", "bavarian_zoll"),
    ("cm", "cm"),
    ("Meter", "m"),
])
def test_canonicalize(raw, canonical):
    assert canonicalize(raw).canonical == canonical


def test_unknown_unit_keeps_label_no_conversion():
    u = canonicalize("Klafter")
    assert u.to_mm is None
    assert to_mm(3.0, u) is None


def test_none_unit():
    assert canonicalize(None).canonical == "unknown"


def test_bavarian_foot_conversion():
    u = canonicalize("Fuß")
    assert to_mm(1.0, u) == pytest.approx(BAVARIAN_FOOT_MM)


def test_danube_transition_rule():
    assert danube_unit_for(date(1872, 3, 31)).canonical == "bavarian_foot"
    assert danube_unit_for(date(1872, 4, 1)).canonical == "mm"
    assert danube_unit_for(date(1826, 1, 1)).canonical == "bavarian_foot"
    assert danube_unit_for(date(1894, 12, 31)).canonical == "mm"
