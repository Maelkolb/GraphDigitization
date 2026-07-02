"""Full pipeline offline: ingest -> ... -> report with the stub extractor.

The stub gets two candidates: the analytic curve (good) and a half-coverage decoy, so the
selection stage must prefer the good one via s_alpha. The final series must reproduce the
analytic values, closing the loop pixel -> polyline -> calibration -> physical units.
"""

from __future__ import annotations

import csv

import numpy as np
import pytest

from conftest import FakeGeminiClient
from graphdig.artifacts import LinesArtifact, SeriesArtifact, load_artifact
from graphdig.config import RunConfig
from graphdig.gemini.schemas import QcResponse
from graphdig.pipeline import Runner
from test_stages_offline import _canned_responses


def _write_sidecar(run_dir, spec):
    """Candidates in TILE coordinates (plot-area crop, x-stretch 2.0)."""
    import json

    x0, y0, x1, _ = spec.plot
    xs_page = np.arange(x0, x1, 0.5)
    ys_page = spec.curve_y(xs_page)
    good = np.column_stack([(xs_page - x0) * 2.0, ys_page - y0])
    half = good[: len(good) // 2]
    payload = [
        {"confidence": 0.55, "points": good.tolist()},
        {"confidence": 0.95, "points": half.tolist()},  # confident but half coverage
    ]
    (run_dir / "tiles" / "p01.png.lines.json").write_text(json.dumps(payload),
                                                          encoding="utf-8")


@pytest.fixture
def full_run(tmp_path, synth_chart):
    input_path, spec = synth_chart
    responses = _canned_responses(spec)
    responses["QC_V1"] = QcResponse(verdict="ok", issues=[], reason="follows the curve",
                                    confidence=0.9)
    fake = FakeGeminiClient(responses)

    cfg1 = RunConfig(input=input_path, out_parent=tmp_path / "runs",
                     profile_name="generic", baseline_enabled=True, workers=1,
                     extractor="stub",
                     stages=["ingest", "triage", "calibrate", "baseline",
                             "preprocess"])
    assert Runner(cfg1, gemini_client=fake).run() == 0
    run_dir = next((tmp_path / "runs").iterdir())
    _write_sidecar(run_dir, spec)

    cfg2 = cfg1.model_copy(update={
        "input": None, "run_dir": run_dir,
        "stages": ["extract", "select", "series", "qc", "report"]})
    assert Runner(cfg2, gemini_client=fake).run() == 0
    return run_dir, spec


def test_selection_prefers_coverage_over_confidence(full_run):
    run_dir, _ = full_run
    lines = load_artifact(LinesArtifact, run_dir / "lines.json")
    tl = lines.tiles["p01"]
    by_id = {c.cand_id: c for c in tl.candidates}
    assert by_id[0].coverage > 0.99
    assert by_id[1].coverage < 0.6
    assert tl.selected.cand_id == 0  # s_alpha: 0.31*0.55+0.69*1.0 > 0.31*0.95+0.69*0.5


def test_series_reproduces_analytic_values(full_run):
    run_dir, spec = full_run
    series = load_artifact(SeriesArtifact, run_dir / "series.json")
    ps = series.panels["p01"]
    assert ps.n == 31
    assert ps.baseline_applied
    assert len(ps.gaps) == 0

    x0, _, x1, _ = spec.plot
    with open(run_dir / ps.csv_path, encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    assert len(rows) == 31
    errors = []
    for i, row in enumerate(rows):
        # slice i covers page x in [x0 + i*w, x0 + (i+1)*w]; last point sits at its end
        slice_end = x0 + (i + 1) * (x1 - x0) / 31
        expected = spec.value_at(float(spec.curve_y(np.array([slice_end]))[0]))
        errors.append(abs(float(row["value_native"]) - expected))
    assert np.median(errors) < 0.5  # native units (analytic range 5..55)
    assert max(errors) < 1.5


def test_qc_and_report(full_run):
    run_dir, _ = full_run
    report = (run_dir / "report.md").read_text(encoding="utf-8")
    assert "## Panels" in report and "## Series" in report
    assert (run_dir / "overlays" / "curve_p01.png").exists()
    assert (run_dir / "overlays" / "reconstruction_p01.png").exists()
    assert (run_dir / "qc.json").exists()
