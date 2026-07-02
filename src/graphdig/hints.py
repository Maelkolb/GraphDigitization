"""User-suppliable metadata hints (`graphdig run ... --hints hints.json`).

Historical charts often come with context the scan alone cannot provide (the station, the
year, the unit system, a manually measured axis anchor). Hints let the operator inject
that knowledge without touching the pipeline:

Precedence rules:
1. A hint field that is present overrides the Gemini reading in the artifact.
2. Gemini's original value is never discarded silently: a disagreement is recorded as a
   `hint_mismatch:<field>` warning flag in review/flags.json (the hint still wins), and
   the affected artifact carries a `user_hint:<field>` flag for provenance.
3. Hint y-anchors produce the calibration fit (method="user_anchors", confidence 1.0).
   If a Gemini tick fit also exists, they are cross-validated; >5% span disagreement
   raises `hint_gemini_mismatch` (the hint still wins).
4. A `rotation_deg` hint skips the orientation check and triage rotation loop entirely.
5. Hint panel bboxes replace triage panels when given explicitly.

The schema is strict (`extra="forbid"`): a typo in a hand-written hints file must error,
not vanish.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from graphdig.calibration.fit import Tick

HINTS_FILENAME = "hints.json"


class YAnchorHint(BaseModel):
    model_config = ConfigDict(extra="forbid")
    pixel: float  # y row in PAGE pixels (post-rotation page space)
    value: float  # in native axis/grid units


class PanelHint(BaseModel):
    model_config = ConfigDict(extra="forbid")
    index: int | None = None  # 1-based reading-order position (matches p{index:02d})
    month: int | None = None  # danube: month identity 1..12
    label: str = ""
    bbox_px: list[int] | None = None  # [x, y, w, h]
    plot_area_px: list[int] | None = None
    x_start: str = ""  # ISO date or number
    x_end: str = ""
    n_series: int | None = None
    series_labels: list[str] = Field(default_factory=list)
    y_anchors: list[YAnchorHint] = Field(default_factory=list)


class Hints(BaseModel):
    model_config = ConfigDict(extra="forbid")
    station: str = ""
    year: int | None = None
    unit: str = ""  # e.g. "Fuss", "mm"
    y_scale: Literal["linear", "log"] | None = None
    n_series: int | None = None
    series_labels: list[str] = Field(default_factory=list)
    rotation_deg: int | None = None  # 0/90/180/270; skips orientation checks
    expected_panels: int | None = None
    panel_layout: Literal["single", "row", "grid"] | None = None
    y_anchors: list[YAnchorHint] = Field(default_factory=list)  # global (shared scale)
    baseline_visible: bool | None = None
    panels: list[PanelHint] = Field(default_factory=list)
    notes: str = ""


def load_hints(path: Path | str) -> Hints:
    return Hints.model_validate_json(Path(path).read_text(encoding="utf-8"))


def save_hints(hints: Hints, path: Path | str) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(hints.model_dump_json(indent=2), encoding="utf-8")
    return path


def panel_hint_for(hints: Hints, panel_id: str, month: int | None = None) -> PanelHint | None:
    """Match a panel hint by month first (danube), then by reading-order index."""
    for ph in hints.panels:
        if month is not None and ph.month == month:
            return ph
    try:
        index = int(panel_id.lstrip("p"))
    except ValueError:
        return None
    for ph in hints.panels:
        if ph.index == index:
            return ph
    return None


def hint_ticks(hints: Hints | None, panel_id: str = "",
               month: int | None = None) -> list[Tick]:
    """Anchor hints as calibration ticks; per-panel anchors beat the global set."""
    if hints is None:
        return []
    anchors = list(hints.y_anchors)
    ph = panel_hint_for(hints, panel_id, month)
    if ph and ph.y_anchors:
        anchors = ph.y_anchors
    return [Tick(pixel=a.pixel, value=a.value, label_text="user_anchor") for a in anchors]


def apply_triage_hints(hints: Hints, classification, metadata, ctx) -> None:
    """Override triage classification/metadata with hints; flag disagreements."""

    def override(obj, attr: str, hint_value, gemini_value) -> None:
        if gemini_value not in (None, "", 0, []) and gemini_value != hint_value:
            ctx.add_flag("triage",
                         f"hint_mismatch:{attr} gemini={gemini_value!r} "
                         f"hint={hint_value!r} (hint wins)", severity="warning")
        setattr(obj, attr, hint_value)

    if hints.n_series is not None:
        override(classification, "n_series", hints.n_series, classification.n_series)
    if hints.series_labels:
        override(classification, "series_labels", list(hints.series_labels),
                 classification.series_labels)
    if hints.y_scale is not None:
        override(classification, "y_scale_guess", hints.y_scale,
                 classification.y_scale_guess)
    if hints.station:
        override(metadata, "station", hints.station, metadata.station)
    if hints.year is not None:
        override(metadata, "year", hints.year, metadata.year)
    if hints.unit:
        override(metadata, "y_unit_declared", hints.unit, metadata.y_unit_declared)
