"""User-hints: schema, precedence, calibration from anchors, wiring."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from conftest import FakeGeminiClient
from graphdig.artifacts import (
    CalibrationArtifact,
    MetadataArtifact,
    PanelsArtifact,
    ReviewArtifact,
    load_artifact,
)
from graphdig.config import RunConfig
from graphdig.hints import Hints, PanelHint, YAnchorHint, hint_ticks, load_hints, save_hints
from graphdig.pipeline import Runner
from test_stages_offline import _canned_responses


def test_schema_roundtrip_and_typo_rejection(tmp_path):
    hints = Hints(station="Neu-Ulm", year=1848, unit="Fuss",
                  y_anchors=[YAnchorHint(pixel=750.0, value=0.0)],
                  panels=[PanelHint(index=1, month=1)])
    path = save_hints(hints, tmp_path / "hints.json")
    assert load_hints(path) == hints
    # extra="forbid": a typo in a hand-written file must error, not vanish
    raw = json.loads(path.read_text(encoding="utf-8"))
    raw["staton"] = "typo"
    path.write_text(json.dumps(raw), encoding="utf-8")
    with pytest.raises(Exception, match="staton"):
        load_hints(path)


def test_hint_ticks_panel_overrides_global():
    hints = Hints(y_anchors=[YAnchorHint(pixel=100, value=1.0)],
                  panels=[PanelHint(index=2,
                                    y_anchors=[YAnchorHint(pixel=200, value=2.0),
                                               YAnchorHint(pixel=300, value=3.0)])])
    assert [t.pixel for t in hint_ticks(hints, "p01")] == [100]
    assert [t.pixel for t in hint_ticks(hints, "p02")] == [200, 300]
    assert hint_ticks(None, "p01") == []


def _run_with_hints(tmp_path, synth_chart, hints: Hints, responses,
                    stages=("ingest", "triage", "calibrate")):
    input_path, spec = synth_chart
    hints_path = save_hints(hints, tmp_path / "hints.json")
    cfg = RunConfig(input=input_path, out_parent=tmp_path / "runs", workers=1,
                    baseline_enabled=False, hints_path=hints_path, stages=list(stages))
    fake = FakeGeminiClient(responses)
    assert Runner(cfg, gemini_client=fake).run() == 0
    return next((tmp_path / "runs").iterdir()), spec, fake


def test_triage_hint_overrides_and_mismatch_flag(tmp_path, synth_chart):
    responses = _canned_responses(synth_chart[1])
    responses["TRIAGE_V1_GENERIC"].year = 1900  # Gemini misreads the year
    hints = Hints(year=1848, station="Synthetic", n_series=1, rotation_deg=0)
    run_dir, _, fake = _run_with_hints(tmp_path, synth_chart, hints, responses,
                                       stages=("ingest", "triage"))
    meta = load_artifact(MetadataArtifact, run_dir / "metadata.json")
    assert meta.year == 1848  # hint wins
    review = load_artifact(ReviewArtifact, run_dir / "review" / "flags.json")
    assert any("hint_mismatch:year" in f.reason for f in review.flags)
    # rotation hint skips the 4-way orientation composite entirely
    assert "ORIENT_V1" not in fake.calls


def test_calibrate_from_user_anchors_only(tmp_path, synth_chart):
    spec = synth_chart[1]
    responses = _canned_responses(spec)
    responses["TRIAGE_V1_GENERIC"].y_axis_labels_present = False  # no cross-check call
    del responses["CALIB_V1"]
    hints = Hints(unit="mm", y_anchors=[
        YAnchorHint(pixel=spec.pixel_at(0.0), value=0.0),
        YAnchorHint(pixel=spec.pixel_at(60.0), value=60.0)])
    run_dir, spec, fake = _run_with_hints(tmp_path, synth_chart, hints, responses)
    cal = load_artifact(CalibrationArtifact, run_dir / "calibration.json").panels["p01"]
    assert cal.y_axis.fit.method == "user_anchors"
    assert "user_hint:y_anchors" in cal.y_axis.flags
    assert cal.y_axis.fit.slope == pytest.approx(spec.y_slope, rel=1e-6)
    assert cal.y_axis.unit.canonical == "mm"
    assert "CALIB_V1" not in fake.calls


def test_hint_gemini_mismatch_flag(tmp_path, synth_chart):
    spec = synth_chart[1]
    responses = _canned_responses(spec)  # canned Gemini ticks match the analytic axis
    # user anchors deliberately WRONG by 20%: Gemini disagrees -> flag, hint still wins
    hints = Hints(y_anchors=[
        YAnchorHint(pixel=spec.pixel_at(0.0), value=0.0),
        YAnchorHint(pixel=spec.pixel_at(60.0), value=72.0)])
    run_dir, _, _ = _run_with_hints(tmp_path, synth_chart, hints, responses)
    cal = load_artifact(CalibrationArtifact, run_dir / "calibration.json").panels["p01"]
    assert cal.y_axis.fit.method == "user_anchors"
    assert "hint_gemini_mismatch" in cal.y_axis.flags


def test_panel_bbox_hints_replace_detection(tmp_path, synth_chart):
    spec = synth_chart[1]
    responses = _canned_responses(spec)
    bx0, by0, bx1, by1 = spec.bbox
    hints = Hints(expected_panels=1,
                  panels=[PanelHint(index=1, bbox_px=[bx0, by0, bx1 - bx0, by1 - by0])])
    run_dir, _, _ = _run_with_hints(tmp_path, synth_chart, hints, responses,
                                    stages=("ingest", "triage"))
    panels = load_artifact(PanelsArtifact, run_dir / "panels.json")
    assert panels.panels[0].flags == ["user_hint:bbox"]
    assert panels.panels[0].bbox_px.x == bx0


def test_hints_copied_into_run_dir(tmp_path, synth_chart):
    responses = _canned_responses(synth_chart[1])
    hints = Hints(year=1848)
    run_dir, _, _ = _run_with_hints(tmp_path, synth_chart, hints, responses,
                                    stages=("ingest",))
    assert (run_dir / "hints.json").exists()
    assert load_hints(run_dir / "hints.json") == hints


ZENODO_READY = Path("data/zenodo/monthannotations").exists()


@pytest.mark.skipif(not ZENODO_READY, reason="Zenodo reference data not fetched")
def test_hints_from_annotations_matches_prepare_run():
    from PIL import Image

    from graphdig.data.danube_prep import hints_from_annotations, tile_anchor_rows
    from graphdig.data.gt_loaders import ZenodoPaths, load_month_yolo

    scan_id, year, month = "210018", 1839, 2
    hints = hints_from_annotations(scan_id, year, month=month)
    assert hints.expected_panels == 1
    assert hints.panels[0].x_start == "1839-02-01"
    paths = ZenodoPaths()
    ann = load_month_yolo(paths.month_yolo(scan_id))
    tile = Image.open(paths.tile(scan_id, month))
    c_low, _c_high = tile_anchor_rows(ann, month, tile.width, tile.height)
    assert hints.y_anchors[0].pixel == pytest.approx(c_low)
    assert hints.y_anchors[0].value == ann.low_value
    assert hints.unit == "bavarian_foot"
