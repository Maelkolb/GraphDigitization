"""gemini_points extractor, QC fallback merge, and bench utilities."""

from __future__ import annotations

import csv
import json

import numpy as np
import pytest

from conftest import FakeGeminiClient
from graphdig.artifacts import LinesArtifact, SeriesArtifact, load_artifact
from graphdig.config import RunConfig
from graphdig.eval.extractor_bench import BenchRow, comparison_table, parse_gauge_months
from graphdig.extractors import get_extractor
from graphdig.gemini.schemas import (
    GSeriesPoint,
    GSeriesTrace,
    PointsResponse,
    QcResponse,
)
from graphdig.pipeline import Runner
from test_stages_offline import _canned_responses


def _points_response(spec, run_dir, k=31, hole: range | None = None) -> PointsResponse:
    """Trace the analytic curve at the k x positions the extractor will request."""
    from graphdig.artifacts import TilesArtifact

    tile = load_artifact(TilesArtifact, run_dir / "tiles.json").tiles[0]
    xs_1000 = np.linspace(10, 990, k).astype(int)
    points = []
    for i, x1000 in enumerate(xs_1000):
        x_tile = x1000 / 1000.0 * tile.width
        x_page = tile.transform.tile_to_page(np.array([[x_tile, 0.0]]))[0, 0]
        y_page = float(spec.curve_y(np.array([x_page]))[0])
        y_tile = tile.transform.page_to_tile(np.array([[x_page, y_page]]))[0, 1]
        visible = not (hole and i in hole)
        points.append(GSeriesPoint(x_1000=int(x1000),
                                   y_1000=round(y_tile / tile.height * 1000),
                                   visible=visible))
    return PointsResponse(series=[GSeriesTrace(series_label="curve", points=points,
                                               confidence=0.9)], confidence=0.9)


def _staged_run(tmp_path, synth_chart, responses, extractor="gemini_points",
                fallback=None):
    input_path, spec = synth_chart
    fake = FakeGeminiClient(responses)
    cfg1 = RunConfig(input=input_path, out_parent=tmp_path / "runs", workers=1,
                     baseline_enabled=False, extractor=extractor,
                     extractor_fallback=fallback,
                     stages=["ingest", "triage", "calibrate", "preprocess"])
    assert Runner(cfg1, gemini_client=fake).run() == 0
    run_dir = next((tmp_path / "runs").iterdir())
    return run_dir, spec, fake, cfg1


def test_gemini_points_end_to_end(tmp_path, synth_chart):
    responses = _canned_responses(synth_chart[1])
    run_dir, spec, fake, cfg1 = _staged_run(tmp_path, synth_chart, responses)
    fake.responses["POINTS_V1"] = [_points_response(spec, run_dir)]

    cfg2 = cfg1.model_copy(update={"input": None, "run_dir": run_dir,
                                   "stages": ["extract", "select", "series"]})
    assert Runner(cfg2, gemini_client=fake).run() == 0

    lines = load_artifact(LinesArtifact, run_dir / "lines.json")
    assert lines.backend == "gemini_points"
    tl = lines.tiles["p01"]
    assert tl.selections and tl.selections[0].method == "gemini_points"
    assert "ASSIGN_V1" not in fake.calls  # pre-filled selections skip assignment
    assert tl.candidates[0].coverage is not None  # diagnostics still computed

    series = load_artifact(SeriesArtifact, run_dir / "series.json")
    ps = series.panels["p01"]
    with open(run_dir / ps.csv_path, encoding="utf-8") as fh:
        rows = [r for r in csv.DictReader(fh) if r["value_native"]]
    assert len(rows) >= 25
    for r in rows[::5]:  # calibration consistency at the candidate's own pixels
        expected = spec.value_at(float(spec.curve_y(np.array([float(r["pixel_x_page"])]))[0]))
        assert float(r["value_native"]) == pytest.approx(expected, abs=0.35)


def test_invisible_points_create_gaps(tmp_path, synth_chart):
    responses = _canned_responses(synth_chart[1])
    run_dir, spec, fake, cfg1 = _staged_run(tmp_path, synth_chart, responses)
    fake.responses["POINTS_V1"] = [_points_response(spec, run_dir, hole=range(12, 19))]
    cfg2 = cfg1.model_copy(update={"input": None, "run_dir": run_dir,
                                   "stages": ["extract", "select", "series"]})
    assert Runner(cfg2, gemini_client=fake).run() == 0
    series = load_artifact(SeriesArtifact, run_dir / "series.json")
    assert len(series.panels["p01"].gaps) >= 4  # no interpolation across the hole


def test_get_extractor_requires_ctx():
    with pytest.raises(ValueError, match="context"):
        get_extractor("gemini_points")


def test_qc_fallback_merges_and_recovers(tmp_path, synth_chart):
    spec = synth_chart[1]
    responses = _canned_responses(spec)
    responses["QC_V1"] = [
        QcResponse(verdict="major", issues=["wrong_line_followed"],
                   reason="flat artifact line", confidence=0.9),
        QcResponse(verdict="ok", issues=[], reason="follows the curve", confidence=0.9),
    ]
    run_dir, spec, fake, cfg1 = _staged_run(tmp_path, synth_chart, responses,
                                            extractor="stub",
                                            fallback="gemini_points")
    fake.responses["POINTS_V1"] = [_points_response(spec, run_dir)]

    # the stub's ONLY candidate is a wrong flat line -> reselect exhausts -> fallback
    x0, _, x1, _ = spec.plot
    from graphdig.artifacts import TilesArtifact

    transform = load_artifact(TilesArtifact, run_dir / "tiles.json").tiles[0].transform
    xs = np.arange(x0, x1, 0.5)
    flat = transform.page_to_tile(np.column_stack([xs, np.full(len(xs), spec.baseline_y - 3)]))
    (run_dir / "tiles" / "p01.png.lines.json").write_text(
        json.dumps([{"confidence": 0.95, "points": flat.tolist()}]), encoding="utf-8")

    cfg2 = cfg1.model_copy(update={"input": None, "run_dir": run_dir,
                                   "stages": ["extract", "select", "series", "qc"]})
    assert Runner(cfg2, gemini_client=fake).run() == 0

    lines = load_artifact(LinesArtifact, run_dir / "lines.json")
    tl = lines.tiles["p01"]
    assert tl.fallback_used
    assert lines.backend_meta.get("fallback:p01") == "gemini_points"
    assert tl.selected.cand_id == 1  # merged fallback candidate (offset past stub's 0)
    from graphdig.artifacts import QcArtifact

    qc = load_artifact(QcArtifact, run_dir / "qc.json")
    assert qc.panels["p01"].verdict == "ok"


def test_bench_utilities():
    gm = parse_gauge_months("210018:1839:1-3,290022:1844:6")
    assert gm == [("210018", 1839, 1), ("210018", 1839, 2), ("210018", 1839, 3),
                  ("290022", 1844, 6)]
    rows = [BenchRow(source="danube:210018:1839-02", backend="lineformer_local",
                     peak_score=0.98),
            BenchRow(source="danube:210018:1839-02", backend="gemini_points",
                     peak_score=0.95)]
    table = comparison_table(rows)
    assert "gemini_points" in table and "0.980" in table and "0.950" in table
