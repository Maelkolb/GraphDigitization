"""Typed artifact schemas — the contract between pipeline stages.

Every stage reads and writes exactly these models as JSON files inside a run directory,
which is what makes stages re-runnable, inspectable, and remotely executable (the extract
stage runs on Colab against the same schemas). All models tolerate unknown fields so newer
artifacts stay loadable by older code.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Literal, TypeVar

from pydantic import BaseModel, ConfigDict, Field

from graphdig.geometry import BoxPx, Transform2D

SCHEMA_VERSION = 1


class ArtifactModel(BaseModel):
    model_config = ConfigDict(extra="ignore")
    schema_version: int = SCHEMA_VERSION


class Provenance(ArtifactModel):
    """How a Gemini-produced artifact came to be."""

    model: str = ""
    prompt_id: str = ""
    thinking_level: str = ""
    attempts: int = 1
    usage: dict[str, int] = Field(default_factory=dict)
    timestamp: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())


# --------------------------------------------------------------------------- panels

class XExtentHint(ArtifactModel):
    kind: Literal["date", "numeric", "unknown"] = "unknown"
    start_label: str = ""
    end_label: str = ""


class Panel(ArtifactModel):
    panel_id: str
    label: str = ""
    bbox_px: BoxPx
    plot_area_px: BoxPx | None = None
    x_edge_refined: bool = False
    x_extent_hint: XExtentHint = Field(default_factory=XExtentHint)
    confidence: float = 0.0
    flags: list[str] = Field(default_factory=list)


class ImageRef(ArtifactModel):
    path: str
    width: int
    height: int
    sha256: str = ""


class Orientation(ArtifactModel):
    rotation_applied_deg: int = 0
    reason: str = ""


class PageClassification(ArtifactModel):
    """Triage verdict: what the page is and which digitization path applies."""

    chart_kind: str = "line_chart"
    page_kind: str = ""
    y_axis_labels_present: bool = True
    value_labels_on_curve: bool = False
    y_scale_guess: Literal["linear", "log", "unknown"] = "unknown"
    dual_y_axis: bool = False
    n_series: int = 1
    series_labels: list[str] = Field(default_factory=list)
    confidence: float = 0.0


class PanelsArtifact(ArtifactModel):
    page_id: str
    image: ImageRef
    orientation: Orientation = Field(default_factory=Orientation)
    classification: PageClassification = Field(default_factory=PageClassification)
    panels: list[Panel] = Field(default_factory=list)
    provenance: Provenance = Field(default_factory=Provenance)


# ----------------------------------------------------------------------- calibration

class TickModel(ArtifactModel):
    pixel: float
    value: float
    label_text: str = ""
    legible: bool = True
    used: bool = True
    residual: float | None = None


class FitModel(ArtifactModel):
    method: str
    slope: float
    intercept: float
    scale: Literal["linear", "log"] = "linear"
    r2: float = 1.0
    rmse_value: float = 0.0
    n_ticks: int = 2
    n_used: int = 2
    n_rejected: int = 0


class UnitModel(ArtifactModel):
    raw: str = ""
    canonical: str = "unknown"
    to_mm: float | None = None


class AnchorEquivalent(ArtifactModel):
    """Paper-compatible two-anchor form derived from the fit (provenance + evaluation)."""

    c_low: float
    v_low: float
    c_high: float
    v_high: float


class YAxisCal(ArtifactModel):
    scale: Literal["linear", "log"] = "linear"
    unit: UnitModel = Field(default_factory=UnitModel)
    ticks: list[TickModel] = Field(default_factory=list)
    fit: FitModel | None = None
    anchor_equivalent: AnchorEquivalent | None = None
    confidence: float = 0.0
    flags: list[str] = Field(default_factory=list)


class XAxisCal(ArtifactModel):
    kind: Literal["date", "numeric", "unknown"] = "unknown"
    start: str = ""  # ISO date or number as string
    end: str = ""
    n_samples: int | None = None  # e.g. days in month for daily sampling
    ticks: list[TickModel] = Field(default_factory=list)
    fit: FitModel | None = None
    confidence: float = 0.0
    flags: list[str] = Field(default_factory=list)


class PanelCalibration(ArtifactModel):
    y_axis: YAxisCal = Field(default_factory=YAxisCal)
    x_axis: XAxisCal = Field(default_factory=XAxisCal)
    review_required: bool = False


class CalibrationArtifact(ArtifactModel):
    panels: dict[str, PanelCalibration] = Field(default_factory=dict)
    provenance: Provenance = Field(default_factory=Provenance)


# -------------------------------------------------------------------------- metadata

class UnitTransition(ArtifactModel):
    present: bool = False
    date: str | None = None


class MetadataArtifact(ArtifactModel):
    title: str = ""
    station: str = ""
    year: int | None = None
    date_range: str = ""
    y_unit_declared: str = ""
    unit_transition: UnitTransition = Field(default_factory=UnitTransition)
    language: str = ""
    handwritten_annotations: bool = False
    notes: str = ""
    confidence: float = 0.0
    provenance: Provenance = Field(default_factory=Provenance)


# -------------------------------------------------------------------------- baseline

class BaselinePoint(ArtifactModel):
    x: float
    y: float
    refined: bool = False
    residual_px: float = 0.0


class PanelBaseline(ArtifactModel):
    points: list[BaselinePoint] = Field(default_factory=list)
    interp: str = "linear"
    beta_px: float | None = None
    source: str = "gemini+cv"
    line_visible: bool = True
    confidence: float = 0.0
    flags: list[str] = Field(default_factory=list)


class BaselineArtifact(ArtifactModel):
    panels: dict[str, PanelBaseline] = Field(default_factory=dict)
    provenance: Provenance = Field(default_factory=Provenance)


# ----------------------------------------------------------------------------- tiles

class Tile(ArtifactModel):
    tile_id: str
    path: str
    panel_id: str
    transform: Transform2D = Field(default_factory=Transform2D)
    width: int = 0
    height: int = 0
    sha256: str = ""


class TilesArtifact(ArtifactModel):
    tiles: list[Tile] = Field(default_factory=list)


# ----------------------------------------------------------------------------- lines

class LineCandidate(ArtifactModel):
    cand_id: int
    confidence: float = 0.0
    n_points: int = 0
    coverage: float | None = None
    s_alpha: float | None = None
    viable: bool | None = None
    points_px_tile: list[list[float]] = Field(default_factory=list)


class Selection(ArtifactModel):
    cand_id: int
    method: str = "s_alpha"
    alpha_coverage: float = 0.69
    gemini_pick: int | None = None
    agreement: bool | None = None
    series_id: str = "s1"
    series_label: str = ""


class TileLines(ArtifactModel):
    candidates: list[LineCandidate] = Field(default_factory=list)
    selected: Selection | None = None  # first/primary selection (back-compat)
    selections: list[Selection] = Field(default_factory=list)  # one per data series
    rejected: list[int] = Field(default_factory=list)  # cand_ids vetoed by QC reselection
    error: str | None = None


class LinesArtifact(ArtifactModel):
    backend: str = ""
    backend_meta: dict[str, str] = Field(default_factory=dict)
    params: dict[str, float] = Field(default_factory=dict)
    tiles: dict[str, TileLines] = Field(default_factory=dict)


# ---------------------------------------------------------------------------- series

class PanelSeries(ArtifactModel):
    csv_path: str
    panel_id: str = ""
    series_id: str = "s1"
    series_label: str = ""
    n: int = 0
    x_kind: Literal["date", "numeric", "unknown"] = "unknown"
    gaps: list[str] = Field(default_factory=list)
    cand_id: int | None = None
    baseline_applied: bool = False
    confidence_chain: dict[str, float] = Field(default_factory=dict)


class SeriesArtifact(ArtifactModel):
    panels: dict[str, PanelSeries] = Field(default_factory=dict)


# -------------------------------------------------------------------------------- qc

QcVerdict = Literal["ok", "minor", "major"]


class PanelQc(ArtifactModel):
    verdict: QcVerdict = "ok"
    issues: list[str] = Field(default_factory=list)
    reason: str = ""
    suggested_action: Literal["accept", "review", "reextract", "recalibrate"] = "accept"
    confidence: float = 0.0
    overlay: str = ""


class QcArtifact(ArtifactModel):
    panels: dict[str, PanelQc] = Field(default_factory=dict)
    provenance: Provenance = Field(default_factory=Provenance)


# ---------------------------------------------------------------------------- review

class ReviewFlag(ArtifactModel):
    stage: str
    panel_id: str = ""
    reason: str = ""
    severity: Literal["info", "warning", "blocking"] = "warning"
    artifact_ref: str = ""


class ReviewArtifact(ArtifactModel):
    flags: list[ReviewFlag] = Field(default_factory=list)


# -------------------------------------------------------------------------- manifest

class StageStatus(ArtifactModel):
    status: Literal["pending", "running", "done", "error"] = "pending"
    started: str | None = None
    ended: str | None = None
    error: str | None = None


class Manifest(ArtifactModel):
    run_id: str
    graphdig_version: str = ""
    profile: str = "generic"
    config: dict = Field(default_factory=dict)
    inputs: list[ImageRef] = Field(default_factory=list)
    stages: dict[str, StageStatus] = Field(default_factory=dict)
    environment: dict[str, str] = Field(default_factory=dict)


# ------------------------------------------------------------------------ load/save

T = TypeVar("T", bound=BaseModel)


def save_artifact(model: BaseModel, path: Path | str) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(model.model_dump_json(indent=2), encoding="utf-8")
    return path


def load_artifact[T: BaseModel](cls: type[T], path: Path | str) -> T:
    return cls.model_validate_json(Path(path).read_text(encoding="utf-8"))
