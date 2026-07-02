"""Tests for the generalization round: multi-series selection/digitization,
dual-axis side fitting, scale auto-fallback, candidate separation."""

from __future__ import annotations

import json

import numpy as np
import pytest

from conftest import FakeGeminiClient
from graphdig.artifacts import LinesArtifact, SeriesArtifact, load_artifact
from graphdig.calibration.fit import Tick
from graphdig.config import RunConfig
from graphdig.gemini.schemas import AssignResponse, GAssignment, QcResponse
from graphdig.pipeline import Runner
from graphdig.stages.calibrate import _fit_with_scale_fallback, _pick_axis_side
from graphdig.stages.select import distinct_candidates, separation
from test_stages_offline import _canned_responses

# ------------------------------------------------------------------- separation

def test_separation_metric():
    a = np.column_stack([np.arange(100), np.full(100, 50.0)])
    b = np.column_stack([np.arange(100), np.full(100, 80.0)])
    assert separation(a, b) == pytest.approx(30.0)
    # crossing lines still register as distinct (median, not mean-signed)
    c = np.column_stack([np.arange(100), np.linspace(20, 80, 100)])
    assert separation(a, c) > 10
    # disjoint x-ranges are trivially distinct
    d = np.column_stack([np.arange(200, 300), np.full(100, 50.0)])
    assert separation(a, d) == float("inf")


def test_distinct_candidates_collapse_duplicates():
    from graphdig.artifacts import LineCandidate

    base = np.column_stack([np.arange(100), np.full(100, 50.0)])
    cands = [
        LineCandidate(cand_id=0, s_alpha=0.9, points_px_tile=base.tolist()),
        LineCandidate(cand_id=1, s_alpha=0.8,  # duplicate stroke (numpy broadcast add)
                      points_px_tile=(base + [0, 2]).tolist()),  # noqa: RUF005
        LineCandidate(cand_id=2, s_alpha=0.7,  # a second series
                      points_px_tile=(base + [0, 60]).tolist()),  # noqa: RUF005
    ]
    accepted = distinct_candidates(cands, 2, tile_height=400)
    assert [c.cand_id for c in accepted] == [0, 2]


# ------------------------------------------------------------- dual-axis fitting

def test_pick_axis_side_prefers_consistent_scale():
    # left scale: clean linear 0..100; right scale: a DIFFERENT mapping - mixing them
    # would destroy the fit
    lefts = [(Tick(pixel=float(900 - v * 8), value=float(v)), "left")
             for v in range(0, 101, 10)]
    rights = [(Tick(pixel=float(880 - v * 0.0016), value=float(v)), "right")
              for v in (500_000, 1_000_000, 2_000_000)]
    flags: list[str] = []
    ticks = _pick_axis_side(lefts + rights, dual_expected=True, flags=flags)
    assert any(f.startswith("dual_axis:") for f in flags)
    values = {t.value for t in ticks}
    assert 500_000 not in values or 50.0 not in values  # one side only


def test_scale_fallback_picks_log():
    # decade ticks equally spaced in pixels: linear fit is poor, log fit is exact
    ticks = [Tick(pixel=float(900 - i * 200), value=float(10 ** i)) for i in range(4)]
    flags: list[str] = []
    fit = _fit_with_scale_fallback(ticks, "unknown", None, flags)
    assert fit.scale == "log"
    assert fit.r2 > 0.999


# ------------------------------------------------------- multi-series end-to-end

def _write_multiseries_sidecar(run_dir, spec):
    from graphdig.artifacts import TilesArtifact

    transform = load_artifact(TilesArtifact, run_dir / "tiles.json").tiles[0].transform
    x0, _, x1, _ = spec.plot
    xs_page = np.arange(x0, x1, 0.5)
    upper = transform.page_to_tile(np.column_stack([xs_page, spec.curve_y(xs_page)]))
    dup = upper + [0.0, 2.0]  # noqa: RUF005 - numpy broadcast: same stroke, must collapse
    lower = upper + [0.0, 150.0]  # noqa: RUF005 - numpy broadcast: separate second curve
    payload = [
        {"confidence": 0.90, "points": upper.tolist()},
        {"confidence": 0.85, "points": dup.tolist()},
        {"confidence": 0.80, "points": lower.tolist()},
    ]
    (run_dir / "tiles" / "p01.png.lines.json").write_text(json.dumps(payload),
                                                          encoding="utf-8")


def test_multiseries_pipeline(tmp_path, synth_chart):
    input_path, spec = synth_chart
    responses = _canned_responses(spec)
    triage = responses["TRIAGE_V1_GENERIC"]
    triage.n_series = 2
    triage.series_labels = ["upper curve", "lower curve"]
    responses["ASSIGN_V1"] = AssignResponse(
        assignments=[GAssignment(cand_id=0, series_label="upper curve"),
                     GAssignment(cand_id=2, series_label="lower curve")],
        confidence=0.9)
    responses["QC_V1"] = [
        QcResponse(verdict="ok", issues=[], reason="follows upper", confidence=0.9),
        QcResponse(verdict="ok", issues=[], reason="follows lower", confidence=0.9),
    ]
    fake = FakeGeminiClient(responses)

    cfg1 = RunConfig(input=input_path, out_parent=tmp_path / "runs", workers=1,
                     extractor="stub", baseline_enabled=False,
                     stages=["ingest", "triage", "calibrate", "preprocess"])
    assert Runner(cfg1, gemini_client=fake).run() == 0
    run_dir = next((tmp_path / "runs").iterdir())
    _write_multiseries_sidecar(run_dir, spec)
    cfg2 = cfg1.model_copy(update={"input": None, "run_dir": run_dir,
                                   "stages": ["extract", "select", "series", "qc",
                                              "report"]})
    assert Runner(cfg2, gemini_client=fake).run() == 0

    lines = load_artifact(LinesArtifact, run_dir / "lines.json")
    tl = lines.tiles["p01"]
    assert len(tl.selections) == 2
    assert {s.cand_id for s in tl.selections} == {0, 2}  # duplicate (1) collapsed
    assert {s.series_label for s in tl.selections} == {"upper curve", "lower curve"}

    series = load_artifact(SeriesArtifact, run_dir / "series.json")
    assert set(series.panels) == {"p01_s1", "p01_s2"}
    upper = series.panels["p01_s1"]
    lower = series.panels["p01_s2"]
    assert upper.series_label == "upper curve"
    assert (run_dir / upper.csv_path).exists() and (run_dir / lower.csv_path).exists()

    # the lower curve sits 150 px below -> values differ by 150 * |slope| = 15 units
    import csv as csvmod

    def mean_value(ps):
        with open(run_dir / ps.csv_path, encoding="utf-8") as fh:
            vals = [float(r["value_native"]) for r in csvmod.DictReader(fh)
                    if r["value_native"]]
        return float(np.mean(vals))

    assert mean_value(upper) - mean_value(lower) == pytest.approx(15.0, abs=0.6)
    # one combined reconstruction figure per panel
    assert (run_dir / "overlays" / "reconstruction_p01.png").exists()
