"""Full annual sheets: month assignment, panel reconciliation, shared y-fit,
annual stitching - unit tests plus the synthetic 12-panel year page end-to-end."""

from __future__ import annotations

import calendar
import csv
import json
from datetime import date

import numpy as np
import pytest
from PIL import Image, ImageDraw

from conftest import GERMAN_MONTH_NAMES, FakeGeminiClient
from graphdig.artifacts import (
    CalibrationArtifact,
    FitModel,
    ImageRef,
    Panel,
    PanelCalibration,
    PanelsArtifact,
    SeriesArtifact,
    XAxisCal,
    YAxisCal,
    load_artifact,
)
from graphdig.config import RunConfig
from graphdig.gemini.schemas import AxisCalResponse, GBox, GPanel, GTick, TriageResponse
from graphdig.geometry import Box1000, BoxPx, bbox_1000_to_px
from graphdig.pipeline import Context, Runner
from graphdig.runs import create_run_dir, init_manifest
from graphdig.stages.calibrate import _prefer_month_hint, _share_y_fit, crop_box_for
from graphdig.stages.triage import (
    _assign_month_spans,
    _reconcile_panel_count,
    _validate_month_widths,
)


def _ctx(tmp_path, profile="danube") -> Context:
    run_dir = create_run_dir(tmp_path, "unit")
    cfg = RunConfig(profile_name=profile, workers=1)
    manifest = init_manifest(run_dir, profile, {}, [ImageRef(path="x", width=1, height=1)])
    return Context(cfg, run_dir, manifest)


def _panel(pid: str, x: int, w: int, label: str = "", month: int | None = None) -> Panel:
    return Panel(panel_id=pid, label=label, month=month,
                 bbox_px=BoxPx(x=x, y=10, w=w, h=100),
                 plot_area_px=BoxPx(x=x + 2, y=12, w=w - 4, h=96))


# ------------------------------------------------------------------ month assignment

def test_assign_months_from_labels(tmp_path):
    ctx = _ctx(tmp_path)
    panels = [_panel(f"p{i + 1:02d}", 100 * i, 90, label=name)
              for i, name in enumerate(GERMAN_MONTH_NAMES)]
    _assign_month_spans(panels, 1849, ctx)
    assert [p.month for p in panels] == list(range(1, 13))
    assert panels[1].x_extent_hint.kind == "date"
    assert panels[1].x_extent_hint.start_label == "1849-02-01"
    assert panels[1].x_extent_hint.end_label == "1849-02-28"


def test_assign_months_positional_fallback(tmp_path):
    ctx = _ctx(tmp_path)
    panels = [_panel(f"p{i + 1:02d}", 100 * i, 90, label="???") for i in range(12)]
    _assign_month_spans(panels, 1849, ctx)
    assert [p.month for p in panels] == list(range(1, 13))
    flags = json.loads((ctx.run_dir / "review" / "flags.json").read_text("utf-8"))
    assert any("month_assignment:positional" in f["reason"] for f in flags["flags"])


def test_single_panel_keeps_hint_month(tmp_path):
    ctx = _ctx(tmp_path)
    panels = [_panel("p01", 0, 90, month=6)]
    _assign_month_spans(panels, 1849, ctx)
    assert panels[0].month == 6  # no positional overwrite for single tiles
    assert panels[0].x_extent_hint.start_label == "1849-06-01"


def test_reading_order_bottom_aligned_heights(tmp_path):
    """Bottom-aligned panels with very different heights are ONE row, x-ordered.

    Regression guard for the pseudo-page scramble: top-edge banding put tall panels
    into different 'rows' and shuffled the calendar order.
    """
    from graphdig.stages.triage import _reading_order

    # real failure case: heights from the 210018 pseudo-page incl. the extremes
    # (February's tile spans the full height, November's barely a third)
    heights = [454, 947, 592, 548, 754, 394, 359, 457, 335, 371, 359, 273]
    panels = []
    for i, h in enumerate(heights):
        p = _panel(f"x{i}", 700 * (11 - i), 690)  # reversed x on purpose
        p.bbox_px = BoxPx(x=700 * (11 - i), y=947 - h, w=690, h=h)
        panels.append(p)
    ordered = _reading_order(panels)
    assert [p.bbox_px.x for p in ordered] == sorted(p.bbox_px.x for p in panels)

    # genuinely stacked panels (forestry A382 layout) stay two rows, top first
    top = _panel("a", 10, 900)
    top.bbox_px = BoxPx(x=10, y=58, w=901, h=751)
    bottom = _panel("b", 10, 900)
    bottom.bbox_px = BoxPx(x=10, y=809, w=901, h=760)
    assert [p.bbox_px.y for p in _reading_order([bottom, top])] == [58, 809]


def test_month_hint_label_mismatch_flag(tmp_path):
    ctx = _ctx(tmp_path)
    p = _panel("p04", 300, 90, label="September", month=4)  # hint says April
    _assign_month_spans([p], 1849, ctx)
    assert p.month == 4  # hint stays authoritative
    assert "month_hint_label_mismatch" in p.flags


# ------------------------------------------------------------- panel reconciliation

def test_reconcile_splits_double_month_box(tmp_path):
    ctx = _ctx(tmp_path)
    img = Image.new("RGB", (460, 120), (250, 250, 250))
    d = ImageDraw.Draw(img)
    for x in (20, 120, 130, 230, 240, 340, 440):  # panel borders
        d.line([(x, 10), (x, 110)], fill=(20, 20, 20), width=2)
    panels = [_panel("p01", 20, 100), _panel("p02", 130, 100),
              _panel("p03", 240, 200)]  # p03 spans two months; seam drawn at 340
    out = _reconcile_panel_count(img, panels, expected=4, ctx=ctx)
    assert len(out) == 4
    widths = sorted(p.bbox_px.w for p in out)
    assert widths[-1] <= 110  # the double box was split near its interior seam
    assert any("split_from_multimonth_box" in p.flags for p in out)


def test_reconcile_drops_slivers(tmp_path):
    ctx = _ctx(tmp_path)
    img = Image.new("RGB", (400, 120), (250, 250, 250))
    panels = [_panel("p01", 0, 100), _panel("p02", 110, 100),
              _panel("p03", 220, 100), _panel("p04", 330, 12)]  # sliver
    out = _reconcile_panel_count(img, panels, expected=3, ctx=ctx)
    assert len(out) == 3


def test_month_width_outlier_flagged(tmp_path):
    ctx = _ctx(tmp_path)
    panels = []
    for m in range(1, 13):
        days = calendar.monthrange(1849, m)[1]
        w = round(days * 6.0)
        if m == 5:
            w -= 8  # > half a day too narrow
        p = _panel(f"p{m:02d}", 200 * m, w, month=m)
        p.plot_area_px = BoxPx(x=200 * m, y=12, w=w, h=96)
        panels.append(p)
    _validate_month_widths(panels, 1849, ctx)
    assert "month_width_outlier" in panels[4].flags
    assert all("month_width_outlier" not in p.flags for p in panels if p.month != 5)


# ------------------------------------------------------------------- calibration

def test_prefer_month_hint_beats_numeric_days():
    p = _panel("p01", 0, 180, month=2)
    p.x_extent_hint.kind = "date"
    p.x_extent_hint.start_label = "1849-02-01"
    p.x_extent_hint.end_label = "1849-02-28"
    numeric = XAxisCal(kind="numeric", start="1", end="28", n_samples=28)
    out = _prefer_month_hint(numeric, p)
    assert out.kind == "date"
    assert out.n_samples == 28
    assert "x_from_month_hint" in out.flags
    # an existing full date reading is kept
    dated = XAxisCal(kind="date", start="1849-02-01", end="1849-02-28", n_samples=28)
    assert _prefer_month_hint(dated, p) is dated


def test_share_y_fit_propagates_donor(tmp_path):
    ctx = _ctx(tmp_path)
    good = PanelCalibration(y_axis=YAxisCal(
        fit=FitModel(method="irls_mad", slope=-0.1, intercept=36.0, r2=0.9999,
                     n_ticks=7, n_used=7)))
    bad = PanelCalibration(y_axis=YAxisCal(flags=["unusable"]), review_required=True)
    drift = PanelCalibration(y_axis=YAxisCal(
        fit=FitModel(method="irls_mad", slope=-0.12, intercept=30.0, r2=0.999,
                     n_ticks=4, n_used=4)))
    art = CalibrationArtifact(panels={"p01": good, "p02": bad, "p03": drift})
    _share_y_fit(art, ctx)
    assert art.panels["p02"].y_axis.fit.slope == -0.1
    assert any(f.startswith("y_fit_shared_from:p01") for f in art.panels["p02"].y_axis.flags)
    assert not art.panels["p02"].review_required
    assert "y_fit_inconsistent" in art.panels["p03"].y_axis.flags


# ------------------------------------------------------- synthetic year page e2e

def _to_1000(v: float, dim: int) -> int:
    return round(v / dim * 1000)


def _year_page_responses(spec):
    W, H = spec.width, spec.height
    gpanels = []
    for m, (x0, y0, x1, y1) in enumerate(spec.panel_boxes(), start=1):
        gbox = GBox(x0=_to_1000(x0 - 3, W), y0=_to_1000(y0 - 6, H),
                    x1=_to_1000(x1 + 3, W), y1=_to_1000(y1 + 6, H))
        gplot = GBox(x0=_to_1000(x0, W), y0=_to_1000(y0, H),
                     x1=_to_1000(x1, W), y1=_to_1000(y1, H))
        gpanels.append(GPanel(box=gbox, plot_area=gplot,
                              label=GERMAN_MONTH_NAMES[m - 1],
                              x_start_label="1",
                              x_end_label=str(calendar.monthrange(spec.year, m)[1]),
                              confidence=0.95))
    triage = TriageResponse(
        rotation_deg=0, chart_kind="multi_panel_line_chart",
        page_kind="annual sheet with 12 monthly panels",
        y_axis_labels_present=True, value_labels_on_curve=False, y_scale_guess="linear",
        panels=gpanels, title=f"Pegel Synthetic {spec.year}", station="Synthetic",
        year=spec.year, y_unit="mm", language="de", confidence=0.9)

    # only the JANUARY panel's crop shows readable ticks; the rest come back empty and
    # must inherit the calibration via the shared-scale donor mechanism
    p01_px = bbox_1000_to_px(Box1000(**gpanels[0].box.model_dump()), W, H)
    crop = crop_box_for(Panel(panel_id="p01", bbox_px=p01_px), W, H)
    ticks = [GTick(pos_1000=round((spec.pixel_at(v) - crop.y) / crop.h * 1000),
                   value=float(v), label_text=str(v)) for v in range(0, 31, 5)]
    cal_full = AxisCalResponse(y_unit_text="mm", y_scale="linear", y_ticks=ticks,
                               x_kind="numeric", x_start_label="1", x_end_label="31",
                               confidence=0.9)
    cal_empty = AxisCalResponse(y_unit_text="", y_scale="linear", y_ticks=[],
                                x_kind="numeric", x_start_label="1", x_end_label="30",
                                confidence=0.2)
    return {
        "TRIAGE_V2_DANUBE": triage,
        "CALIB_V1": [cal_full, cal_empty],  # last repeats for p02..p12 + edge retries
        "CALIB_V1_RETRY": cal_empty,
    }


def test_year_page_end_to_end(tmp_path, synth_year_page):
    input_path, spec = synth_year_page
    fake = FakeGeminiClient(_year_page_responses(spec))
    cfg1 = RunConfig(input=input_path, out_parent=tmp_path / "runs", workers=1,
                     profile_name="danube", baseline_enabled=False, extractor="stub",
                     stages=["ingest", "triage", "calibrate", "preprocess"])
    assert Runner(cfg1, gemini_client=fake).run() == 0
    run_dir = next((tmp_path / "runs").iterdir())

    panels = load_artifact(PanelsArtifact, run_dir / "panels.json")
    assert len(panels.panels) == 12
    assert [p.month for p in panels.panels] == list(range(1, 13))

    cal = load_artifact(CalibrationArtifact, run_dir / "calibration.json")
    assert cal.panels["p01"].y_axis.fit.slope == pytest.approx(spec.y_slope, rel=0.02)
    shared = [pid for pid, pc in cal.panels.items()
              if any(f.startswith("y_fit_shared_from:") for f in pc.y_axis.flags)]
    assert len(shared) == 11  # p02..p12 inherited January's scale
    assert cal.panels["p07"].x_axis.kind == "date"
    assert cal.panels["p07"].x_axis.n_samples == 31

    # stub candidates from the analytic curves, mapped via each tile's transform
    from graphdig.artifacts import TilesArtifact

    tiles = load_artifact(TilesArtifact, run_dir / "tiles.json")
    months = {p.panel_id: p.month for p in panels.panels}
    areas = {p.panel_id: p.plot_area_px for p in panels.panels}
    for tile in tiles.tiles:
        m = months[tile.panel_id]
        area = areas[tile.panel_id]
        xs = np.arange(area.x, area.right, 0.5)
        ts = (xs - area.x) / area.w
        ys = spec.pixel_at(spec.month_value(m, ts))
        pts = tile.transform.page_to_tile(np.column_stack([xs, ys]))
        (run_dir / tile.path).with_name(f"{tile.tile_id}.png.lines.json").write_text(
            json.dumps([{"confidence": 0.9, "points": pts.tolist()}]), encoding="utf-8")
    for tile in tiles.tiles:  # sidecars live next to the tile files
        src = run_dir / "tiles" / f"{tile.tile_id}.png.lines.json"
        assert src.exists()

    cfg2 = cfg1.model_copy(update={"input": None, "run_dir": run_dir,
                                   "stages": ["extract", "select", "series", "report"]})
    assert Runner(cfg2, gemini_client=fake).run() == 0

    series = load_artifact(SeriesArtifact, run_dir / "series.json")
    assert "annual" in series.panels
    annual = series.panels["annual"]
    assert annual.n == 365  # 1849 is not a leap year
    assert len(annual.gaps) == 0

    with open(run_dir / annual.csv_path, encoding="utf-8") as fh:
        by_date = {r["x_key"]: float(r["value_native"])
                   for r in csv.DictReader(fh) if r["value_native"]}
    assert len(by_date) == 365
    for probe in ("1849-01-15", "1849-04-10", "1849-07-31", "1849-12-01"):
        d = date.fromisoformat(probe)
        days = calendar.monthrange(1849, d.month)[1]
        expected = spec.month_value(d.month, d.day / days)
        assert by_date[probe] == pytest.approx(expected, abs=0.5), probe
    assert (run_dir / "overlays" / "reconstruction_annual.png").exists()
