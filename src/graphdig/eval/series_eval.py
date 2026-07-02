"""End-to-end evaluation: reconstructed series vs. ground truth / paper results.

Compares a pipeline run's `series/<panel>.csv` (per gauge-month) against:
- the pixel-level ground truth (`gt.zip`, GAUGELEVEL) - same target the paper evaluated
  against, using the same metric panel incl. the peak-aware composite;
- the paper's published per-month results (`eval_results_all.csv`, best candidate rows)
  for a direct "us vs. paper" table.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from graphdig.data.gt_loaders import ZenodoPaths, load_gt_pixels, load_paper_eval
from graphdig.eval.metrics import all_metrics


@dataclass
class SeriesEvalRow:
    scan_id: str
    month: int
    n_days: int
    n_matched: int
    rmse: float
    mae: float
    maxae: float
    pearson_r: float
    peak_score: float
    paper_peak_score: float | None = None
    paper_rmse: float | None = None


def load_run_series(run_dir: Path, panel_id: str = "p01") -> pd.DataFrame:
    """A run's digitized series CSV with parsed dates (x_key must be ISO dates)."""
    df = pd.read_csv(Path(run_dir) / "series" / f"{panel_id}.csv")
    df["date"] = pd.to_datetime(df["x_key"], errors="coerce").dt.date
    return df


def evaluate_month(run_dir: Path, scan_id: str, month: int,
                   paths: ZenodoPaths | None = None,
                   panel_id: str = "p01",
                   value_column: str = "value_native") -> SeriesEvalRow | None:
    """Compare one gauge-month run against GT. value_column="value_native" assumes the
    calibration read grid units (the GT GAUGELEVEL scale is grid-unit based)."""
    paths = paths or ZenodoPaths()
    pred = load_run_series(run_dir, panel_id)
    gt = load_gt_pixels(paths.gt_pixels(scan_id))
    gt = gt[[d.month == month for d in gt["DATE"]]]
    if gt.empty or pred.empty:
        return None
    merged = pred.merge(gt, left_on="date", right_on="DATE", how="inner")
    if merged.empty:
        return None
    y_pred = pd.to_numeric(merged[value_column], errors="coerce").to_numpy(dtype=float)
    y_true = merged["GAUGELEVEL"].to_numpy(dtype=float)
    m = all_metrics(y_true, y_pred)
    return SeriesEvalRow(
        scan_id=scan_id, month=month, n_days=len(gt), n_matched=len(merged),
        rmse=m["rmse"], mae=m["mae"], maxae=m["maxae"],
        pearson_r=m["pearson_r"], peak_score=m["peak_score"],
    )


def attach_paper_results(rows: list[SeriesEvalRow],
                         paths: ZenodoPaths | None = None) -> list[SeriesEvalRow]:
    paths = paths or ZenodoPaths()
    if not paths.eval_results.exists():
        return rows
    paper = load_paper_eval(paths.eval_results)
    best = paper[paper["isBest"] == "yes"]
    if best.empty:  # fall back to highest Custom per month
        best = paper.sort_values("peak_score").groupby(["scan_id", "month"]).tail(1)
    for row in rows:
        hit = best[(best["scan_id"] == row.scan_id) & (best["month"] == row.month)]
        if not hit.empty:
            row.paper_peak_score = float(hit["peak_score"].iloc[0])
            row.paper_rmse = float(hit["rmse"].iloc[0])
    return rows


def rows_to_frame(rows: list[SeriesEvalRow]) -> pd.DataFrame:
    df = pd.DataFrame([r.__dict__ for r in rows])
    if df.empty:
        return df
    summary = {c: df[c].mean() for c in
               ("rmse", "mae", "maxae", "pearson_r", "peak_score") if c in df}
    print("mean over months:",
          " ".join(f"{k}={v:.3f}" for k, v in summary.items() if not math.isnan(v)))
    return df


def scale_check(run_dir: Path, scan_id: str, month: int,
                paths: ZenodoPaths | None = None, panel_id: str = "p01") -> float:
    """Median ratio GT/prediction - diagnoses unit-scale mismatches (foot vs cm vs mm)."""
    paths = paths or ZenodoPaths()
    pred = load_run_series(run_dir, panel_id)
    gt = load_gt_pixels(paths.gt_pixels(scan_id))
    gt = gt[[d.month == month for d in gt["DATE"]]]
    merged = pred.merge(gt, left_on="date", right_on="DATE", how="inner")
    y_pred = pd.to_numeric(merged["value_native"], errors="coerce").to_numpy(dtype=float)
    y_true = merged["GAUGELEVEL"].to_numpy(dtype=float)
    ok = (np.abs(y_pred) > 1e-6) & ~np.isnan(y_true)
    return float(np.median(y_true[ok] / y_pred[ok])) if ok.any() else math.nan
