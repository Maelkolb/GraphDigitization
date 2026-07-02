"""Response schemas for every Gemini task (passed as `response_schema`).

All coordinates Gemini reports are integers normalized to 0-1000 on the image it was shown
(x from left edge, y from top edge); conversion to pixels happens in graphdig.geometry.
Field descriptions double as inline instructions - Gemini sees them via the JSON schema.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class GBox(BaseModel):
    x0: int = Field(description="left edge, 0-1000")
    y0: int = Field(description="top edge, 0-1000")
    x1: int = Field(description="right edge, 0-1000")
    y1: int = Field(description="bottom edge, 0-1000")


class GPanel(BaseModel):
    box: GBox = Field(description="outer bounding box of the whole panel incl. axis labels")
    plot_area: GBox = Field(description="inner data region strictly inside the axes, "
                                        "excluding tick labels and titles")
    label: str = Field(default="", description="panel title/label text if any, verbatim")
    x_start_label: str = Field(default="", description="leftmost x-axis tick label, verbatim")
    x_end_label: str = Field(default="", description="rightmost x-axis tick label, verbatim")
    confidence: float = Field(description="0-1 confidence this is a data-bearing chart panel")


class PanelsResponse(BaseModel):
    rotation_deg: Literal[0, 90, 180, 270] = Field(
        description="clockwise rotation needed so axis labels read horizontally; 0 if upright")
    page_kind: str = Field(default="", description="short free-text page characterization, "
                                                   "e.g. 'annual sheet with 12 monthly panels'")
    panels: list[GPanel]


class GTick(BaseModel):
    pos_1000: int = Field(description="tick position along the axis in image coords 0-1000 "
                                      "(y for the vertical axis, x for the horizontal axis)")
    value: float = Field(description="numeric value of the tick label")
    label_text: str = Field(default="", description="the label exactly as printed")
    legible: bool = Field(default=True, description="false if partially cut off or uncertain")


class AxisCalResponse(BaseModel):
    y_unit_text: str = Field(default="", description="unit of the vertical axis exactly as "
                                                     "printed (e.g. 'Fuss', 'mm'); '' if absent")
    y_scale: Literal["linear", "log"] = "linear"
    y_ticks: list[GTick] = Field(description="EVERY legible numeric tick on the vertical axis")
    x_kind: Literal["date", "numeric", "unknown"] = Field(
        description="whether the horizontal axis encodes calendar time or plain numbers")
    x_start_label: str = Field(default="", description="label at the left end of the x axis")
    x_end_label: str = Field(default="", description="label at the right end of the x axis")
    x_ticks: list[GTick] = Field(default_factory=list,
                                 description="numeric x-axis ticks if present (else empty)")
    notes: str = Field(default="", description="anything unusual: overwriting, damage, "
                                               "multiple scales, unit changes")
    confidence: float = Field(description="0-1 overall confidence in the readings")


class MetadataResponse(BaseModel):
    title: str = ""
    station: str = Field(default="", description="measurement station / place name if stated")
    year: int = Field(default=0, description="calendar year of the data; 0 if unknown")
    date_range: str = Field(default="", description="covered period as printed, verbatim")
    y_unit: str = Field(default="", description="declared measurement unit")
    unit_transition_present: bool = Field(
        default=False, description="true if the unit system changes within this chart")
    unit_transition_date: str = Field(
        default="", description="ISO date of the unit change if visible, else ''")
    language: str = ""
    handwritten_annotations: bool = False
    notes: str = ""
    confidence: float = 0.0


class GPoint(BaseModel):
    x_1000: int
    y_1000: int


class BaselinePointsResponse(BaseModel):
    line_visible: bool = Field(description="false if no printed zero/reference line exists")
    points: list[GPoint] = Field(description="y position of the printed zero/reference line "
                                             "at each requested x position, same order")
    confidence: float = 0.0


QC_ISSUES = ["vertical_offset", "wrong_line_followed", "missing_segment", "extra_segment",
             "time_shift", "axis_mismatch", "peak_missed", "noise", "other"]


class QcResponse(BaseModel):
    verdict: Literal["ok", "minor", "major"] = Field(
        description="ok: overlay follows the drawn curve within one grid tick; "
                    "minor: deviations within one tick; major: larger deviations or wrong line")
    issues: list[str] = Field(default_factory=list,
                              description=f"applicable issue tags from: {QC_ISSUES}")
    reason: str = Field(default="", description="one-sentence justification")
    confidence: float = 0.0


class PickResponse(BaseModel):
    best_cand_id: int = Field(description="id of the candidate polyline that best follows "
                                          "the actually drawn data curve")
    reason: str = ""
    confidence: float = 0.0
