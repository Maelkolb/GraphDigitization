"""Lenient parsing of historical axis/date labels (German-language sources)."""

from __future__ import annotations

import calendar
import re
from datetime import date

GERMAN_MONTHS = {
    "januar": 1, "jänner": 1, "februar": 2, "märz": 3, "maerz": 3, "april": 4,
    "mai": 5, "juni": 6, "juli": 7, "august": 8, "september": 9, "oktober": 10,
    "november": 11, "dezember": 12,
    # English fallbacks
    "january": 1, "february": 2, "march": 3, "may": 5, "june": 6, "july": 7,
    "october": 10, "december": 12,
}

_ISO = re.compile(r"^(\d{4})-(\d{2})-(\d{2})$")
_MONTH_YEAR = re.compile(r"^([A-Za-zäöüÄÖÜ]+\.?)\s+(\d{4})$")
_DAY_MONTH_YEAR = re.compile(r"^(\d{1,2})\.?\s*([A-Za-zäöüÄÖÜ]+\.?)\s*(\d{4})?$")


def month_from_name(name: str) -> int | None:
    key = name.strip().rstrip(".").lower()
    if key in GERMAN_MONTHS:
        return GERMAN_MONTHS[key]
    # abbreviations: "Jan", "Feb", "Sept", ...
    for full, num in GERMAN_MONTHS.items():
        if len(key) >= 3 and full.startswith(key):
            return num
    return None


def parse_date_label(label: str, default_year: int | None = None) -> date | None:
    """Best-effort parse of a printed date label; None when not confidently parseable."""
    text = label.strip()
    if not text:
        return None
    m = _ISO.match(text)
    if m:
        try:
            return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            return None
    m = _MONTH_YEAR.match(text)
    if m:
        month = month_from_name(m.group(1))
        if month:
            return date(int(m.group(2)), month, 1)
    m = _DAY_MONTH_YEAR.match(text)
    if m:
        month = month_from_name(m.group(2))
        year = int(m.group(3)) if m.group(3) else default_year
        if month and year:
            try:
                return date(year, month, int(m.group(1)))
            except ValueError:
                return None
    return None


def days_in_month(year: int, month: int) -> int:
    return calendar.monthrange(year, month)[1]


def month_span(year: int, month: int) -> tuple[date, date]:
    return date(year, month, 1), date(year, month, days_in_month(year, month))
