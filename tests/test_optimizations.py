"""Tests for the optimization round: QC auto-reselect, curve-label calibration,
descending numeric x-axes."""

from __future__ import annotations

import json

import numpy as np
import pytest

from conftest import FakeGeminiClient
from graphdig.artifacts import (
    CalibrationArtifact,
    LinesArtifact,
    QcArtifact,
    SeriesArtifact,
    XAxisCal,
    load_artifact,
)
from graphdig.config import RunConfig
from graphdig.gemini.schemas import CurveLabelsResponse, GCurveLabel, QcResponse
from graphdig.pipeline import Runner
from graphdig.stages.calibrate import _build_x_axis
from graphdig.stages.series import _x_keys
from test_stages_offline import _canned_responses

# ---------------------------------------------------------------- QC auto-reselect

def _write_sidecar_bad_first(run_dir, spec):
    """Wrong line (fill edge) with HIGH confidence + full coverage, correct curve lower."""
    from graphdig.artifacts import TilesArtifact

    transform = load_artifact(TilesArtifact, run_dir / "tiles.json").tiles[0].transform
    x0, _, x1, _ = spec.plot
    xs_page = np.arange(x0, x1, 0.5)
    good = transform.page_to_tile(np.column_stack([xs_page, spec.curve_y(xs_page)]))
    flat = transform.page_to_tile(np.column_stack(
        [xs_page, np.full(len(xs_page), spec.baseline_y - 3)]))
    payload = [
        {"confidence": 0.95, "points": flat.tolist()},   # wrong line, wins s_alpha
        {"confidence": 0.60, "points": good.tolist()},   # correct curve
    ]
    (run_dir / "tiles" / "p01.png.lines.json").write_text(json.dumps(payload),
                                                          encoding="utf-8")


def test_qc_major_triggers_reselection(tmp_path, synth_chart):
    input_path, spec = synth_chart
    responses = _canned_responses(spec)
    responses["QC_V1"] = [
        QcResponse(verdict="major", issues=["wrong_line_followed"],
                   reason="flat line at the bottom", confidence=0.9),
        QcResponse(verdict="ok", issues=[], reason="follows the curve", confidence=0.9),
    ]
    fake = FakeGeminiClient(responses)
    cfg1 = RunConfig(input=input_path, out_parent=tmp_path / "runs", workers=1,
                     extractor="stub", baseline_enabled=False,
                     stages=["ingest", "triage", "calibrate", "preprocess"])
    assert Runner(cfg1, gemini_client=fake).run() == 0
    run_dir = next((tmp_path / "runs").iterdir())
    _write_sidecar_bad_first(run_dir, spec)
    cfg2 = cfg1.model_copy(update={"input": None, "run_dir": run_dir,
                                   "stages": ["extract", "select", "series", "qc"]})
    assert Runner(cfg2, gemini_client=fake).run() == 0

    lines = load_artifact(LinesArtifact, run_dir / "lines.json")
    tl = lines.tiles["p01"]
    assert tl.rejected == [0]  # the confident wrong line was vetoed by QC
    assert tl.selected.cand_id == 1
    assert tl.selected.method.startswith("qc_reselect")
    series = load_artifact(SeriesArtifact, run_dir / "series.json")
    assert series.panels["p01"].cand_id == 1  # series rebuilt from the good candidate
    qc = load_artifact(QcArtifact, run_dir / "qc.json")
    assert qc.panels["p01"].verdict == "ok"  # final verdict after reselection


# ---------------------------------------------------------- curve-label calibration

def test_curve_label_calibration(tmp_path, synth_chart):
    input_path, spec = synth_chart
    responses = _canned_responses(spec)
    triage = responses["TRIAGE_V1_GENERIC"]
    triage.y_axis_labels_present = False
    triage.value_labels_on_curve = True
    del responses["CALIB_V1"]  # axis path must not be used

    # labels along the analytic curve, positions in CROP coords of the panel bbox
    from graphdig.artifacts import Panel
    from graphdig.geometry import Box1000, bbox_1000_to_px
    from graphdig.stages.calibrate import crop_box_for

    panel_px = Panel(panel_id="p01", bbox_px=bbox_1000_to_px(
        Box1000(**triage.panels[0].box.model_dump()), spec.width, spec.height))
    crop = crop_box_for(panel_px, spec.width, spec.height)
    labels = []
    x0, _, x1, _ = spec.plot
    for x_page in np.linspace(x0 + 50, x1 - 50, 8):
        y_page = float(spec.curve_y(np.array([x_page]))[0])
        labels.append(GCurveLabel(
            x_1000=round((x_page - crop.x) / crop.w * 1000),
            y_1000=round((y_page - crop.y) / crop.h * 1000),
            value=round(spec.value_at(y_page), 2), label_text=""))
    responses["CURVE_LABELS_V1"] = CurveLabelsResponse(labels=labels, unit_text="Zoll",
                                                       confidence=0.85)

    cfg = RunConfig(input=input_path, out_parent=tmp_path / "runs", workers=1,
                    baseline_enabled=False,
                    stages=["ingest", "triage", "calibrate"])
    assert Runner(cfg, gemini_client=FakeGeminiClient(responses)).run() == 0
    run_dir = next((tmp_path / "runs").iterdir())
    cal = load_artifact(CalibrationArtifact, run_dir / "calibration.json").panels["p01"]
    assert "curve_labels" in cal.y_axis.flags
    assert not cal.review_required
    assert cal.y_axis.unit.canonical == "bavarian_zoll"
    fit = cal.y_axis.fit
    assert fit is not None
    # the fit must recover the analytic mapping from the on-curve labels
    assert fit.slope == pytest.approx(spec.y_slope, rel=0.03)
    assert fit.r2 > 0.995


# ------------------------------------------------------------- descending numeric x

def test_descending_numeric_x_axis():
    from graphdig.artifacts import Panel
    from graphdig.geometry import BoxPx

    panel = Panel(panel_id="p01", bbox_px=BoxPx(x=0, y=0, w=100, h=100))
    x = _build_x_axis("numeric", "34", "0", panel, 0.9)
    assert x.n_samples == 35
    assert "descending" in x.flags
    keys = _x_keys(_wrap(x), 35)
    assert keys[0] == "34" and keys[-1] == "0"
    assert keys[17] == "17"


def _wrap(x_axis: XAxisCal):
    from graphdig.artifacts import PanelCalibration

    return PanelCalibration(x_axis=x_axis)
