"""End-to-end offline test of the Gemini stages (ingest -> panels -> calibrate ->
metadata -> baseline) against the synthetic chart, using canned Gemini responses."""

from __future__ import annotations

import numpy as np
import pytest

from conftest import FakeGeminiClient
from graphdig.artifacts import (
    BaselineArtifact,
    CalibrationArtifact,
    MetadataArtifact,
    PanelsArtifact,
    load_artifact,
)
from graphdig.config import RunConfig
from graphdig.gemini.schemas import (
    AxisCalResponse,
    BaselinePointsResponse,
    GBox,
    GPanel,
    GPoint,
    GTick,
    TriageResponse,
)
from graphdig.geometry import Box1000, bbox_1000_to_px
from graphdig.pipeline import Runner
from graphdig.stages.baseline import N_SAMPLE_POINTS
from graphdig.stages.calibrate import crop_box_for


def _to_1000(px: float, dim: int) -> int:
    return round(px / dim * 1000)


def _canned_responses(spec):
    w, h = spec.width, spec.height
    bx0, by0, bx1, by1 = spec.bbox
    px0, py0, px1, py1 = spec.plot

    gbox = GBox(x0=_to_1000(bx0, w), y0=_to_1000(by0, h),
                x1=_to_1000(bx1, w), y1=_to_1000(by1, h))
    gplot = GBox(x0=_to_1000(px0, w), y0=_to_1000(py0, h),
                 x1=_to_1000(px1, w), y1=_to_1000(py1, h))
    triage_resp = TriageResponse(
        rotation_deg=0, chart_kind="line_chart", page_kind="single synthetic chart",
        y_axis_labels_present=True, value_labels_on_curve=False, y_scale_guess="linear",
        panels=[GPanel(box=gbox, plot_area=gplot, label="Synthetic Gauge",
                       x_start_label="1", x_end_label="31", confidence=0.95)],
        title="Synthetic Gauge 1848", station="Synthetic", year=1848, y_unit="mm",
        language="de", confidence=0.9)

    # calibration ticks are reported in CROP coordinates: replicate the stage's crop math
    from graphdig.artifacts import Panel

    panel_px = Panel(panel_id="p01",
                     bbox_px=bbox_1000_to_px(Box1000(**gbox.model_dump()), w, h))
    crop = crop_box_for(panel_px, w, h)
    ticks = []
    for value in range(0, 61, 10):
        page_y = spec.pixel_at(value)
        pos = round((page_y - crop.y) / crop.h * 1000)
        ticks.append(GTick(pos_1000=pos, value=float(value), label_text=str(value)))
    # one deliberate misreading, to be rejected by the MAD fit
    ticks.append(GTick(pos_1000=ticks[3].pos_1000, value=350.0, label_text="35O"))
    cal_resp = AxisCalResponse(y_unit_text="mm", y_scale="linear", y_ticks=ticks,
                               x_kind="numeric", x_start_label="1", x_end_label="31",
                               confidence=0.9)

    # baseline: Gemini reports the printed zero line a few px off; CV must snap it back
    xs_1000 = np.linspace(30, 970, N_SAMPLE_POINTS).astype(int)
    base_points = [GPoint(x_1000=int(x),
                          y_1000=round((spec.baseline_y + 4 - crop.y) / crop.h * 1000))
                   for x in xs_1000]
    base_resp = BaselinePointsResponse(line_visible=True, points=base_points,
                                       confidence=0.85)

    return {
        "TRIAGE_V1_GENERIC": triage_resp,
        "CALIB_V1": cal_resp,
        "BASELINE_V1": base_resp,
    }


@pytest.fixture
def offline_run(tmp_path, synth_chart):
    input_path, spec = synth_chart
    cfg = RunConfig(input=input_path, out_parent=tmp_path / "runs",
                    profile_name="generic",
                    stages=["ingest", "triage", "calibrate", "baseline"],
                    baseline_enabled=True, workers=1)
    fake = FakeGeminiClient(_canned_responses(spec))
    rc = Runner(cfg, gemini_client=fake).run()
    assert rc == 0
    run_dir = next((tmp_path / "runs").iterdir())
    return run_dir, spec, fake


def test_panels_artifact(offline_run):
    run_dir, spec, _ = offline_run
    art = load_artifact(PanelsArtifact, run_dir / "panels.json")
    assert len(art.panels) == 1
    p = art.panels[0]
    assert p.panel_id == "p01"
    bx0, _by0, bx1, _by1 = spec.bbox
    assert abs(p.bbox_px.x - bx0) <= 2 and abs(p.bbox_px.right - bx1) <= 2
    assert (run_dir / "overlays" / "panels.png").exists()


def test_calibration_fit_recovers_analytic_mapping(offline_run):
    run_dir, spec, _ = offline_run
    art = load_artifact(CalibrationArtifact, run_dir / "calibration.json")
    cal = art.panels["p01"]
    fit = cal.y_axis.fit
    assert fit is not None
    # slope in value/px must match the analytic -0.1 within 2 %
    assert fit.slope == pytest.approx(spec.y_slope, rel=0.02)
    assert fit.r2 > 0.999
    assert fit.n_rejected == 1  # the planted "35O" misreading
    assert cal.y_axis.unit.canonical == "mm"
    # zero value must map back to the zero pixel within ~1 px
    zero_px = (0.0 - fit.intercept) / fit.slope
    assert zero_px == pytest.approx(spec.y_zero_pixel, abs=1.5)
    assert not cal.review_required
    assert cal.x_axis.n_samples == 31


def test_metadata(offline_run):
    run_dir, _, _ = offline_run
    art = load_artifact(MetadataArtifact, run_dir / "metadata.json")
    assert art.year == 1848
    assert art.station == "Synthetic"


def test_baseline_cv_refinement_snaps_to_printed_line(offline_run):
    run_dir, spec, _ = offline_run
    art = load_artifact(BaselineArtifact, run_dir / "baseline.json")
    pb = art.panels["p01"]
    assert pb.line_visible
    assert pb.beta_px == pytest.approx(spec.y_zero_pixel, abs=1.5)
    # points over the plot area must have been snapped from the offset seed (~754) to ~750
    x0, _, x1, _ = spec.plot
    inner = [p for p in pb.points if x0 + 20 < p.x < x1 - 20]
    assert len(inner) >= 8
    for p in inner:
        assert p.y == pytest.approx(spec.baseline_y, abs=2.5)


def test_low_confidence_panel_flagged(tmp_path, synth_chart):
    input_path, spec = synth_chart
    responses = _canned_responses(spec)
    responses["TRIAGE_V1_GENERIC"].panels[0].confidence = 0.2
    cfg = RunConfig(input=input_path, out_parent=tmp_path / "runs2",
                    profile_name="generic", stages=["ingest", "triage"], workers=1)
    rc = Runner(cfg, gemini_client=FakeGeminiClient(responses)).run()
    assert rc == 0
    run_dir = next((tmp_path / "runs2").iterdir())
    art = load_artifact(PanelsArtifact, run_dir / "panels.json")
    assert "low_confidence" in art.panels[0].flags
    assert (run_dir / "review" / "flags.json").exists()
