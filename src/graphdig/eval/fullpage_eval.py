"""Full-page evaluation: segmentation + end-to-end series from one annual-sheet run.

Given a pipeline run over a pseudo-page (or a real full sheet with known truth), report
per month: was the panel found, IoU vs the true extent, left/right edge errors in DAYS
(the unit that matters - a 1-day edge error shifts every date), and the digitized series'
accuracy vs the pixel ground truth.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from graphdig.artifacts import PanelsArtifact, load_artifact
from graphdig.data.gt_loaders import ZenodoPaths, load_gt_pixels, load_month_yolo
from graphdig.dates import days_in_month
from graphdig.eval.calibration_eval import _grid_to_gt_affine, _human_fit
from graphdig.eval.metrics import all_metrics
from graphdig.geometry import BoxPx


@dataclass
class FullPageMonthRow:
    scan_id: str
    month: int
    detected: bool
    iou: float = 0.0
    left_err_days: float = math.nan
    right_err_days: float = math.nan
    n_matched: int = 0
    rmse: float = math.nan
    mae: float = math.nan
    pearson_r: float = math.nan
    peak_score: float = math.nan


def _truth_boxes(truth: dict) -> list[BoxPx]:
    return [BoxPx(x=x, y=y, w=w, h=h) for x, y, w, h in truth["extents"]]


def evaluate_fullpage_run(run_dir: Path | str, truth: dict,
                          paths: ZenodoPaths | None = None) -> list[FullPageMonthRow]:
    run_dir = Path(run_dir)
    paths = paths or ZenodoPaths()
    scan_id, year = truth["scan_id"], truth["year"]
    panels_art = load_artifact(PanelsArtifact, run_dir / "panels.json")
    by_month = {p.month: p for p in panels_art.panels if p.month}

    gt_all = load_gt_pixels(paths.gt_pixels(scan_id))
    a, b = _grid_to_gt_affine(_human_fit(load_month_yolo(paths.month_yolo(scan_id))),
                              gt_all)
    series_by_month = _run_series_by_month(run_dir, panels_art)

    rows: list[FullPageMonthRow] = []
    for m, ext in enumerate(_truth_boxes(truth), start=1):
        panel = by_month.get(m)
        if panel is None:
            rows.append(FullPageMonthRow(scan_id, m, detected=False))
            continue
        n_days = days_in_month(year, m)
        px_per_day = ext.w / n_days
        box = panel.plot_area_px or panel.bbox_px
        row = FullPageMonthRow(
            scan_id, m, detected=True, iou=ext.iou(panel.bbox_px),
            left_err_days=(box.x - ext.x) / px_per_day,
            right_err_days=(box.right - ext.right) / px_per_day,
        )
        pred = series_by_month.get(m)
        if pred is not None and not pred.empty:
            gt = gt_all[[d.month == m for d in gt_all["DATE"]]]
            merged = pred.merge(gt, left_on="date", right_on="DATE", how="inner")
            if not merged.empty:
                y_pred = a * pd.to_numeric(merged["value_native"],
                                           errors="coerce").to_numpy(float) + b
                metrics = all_metrics(merged["GAUGELEVEL"].to_numpy(float), y_pred)
                row.n_matched = len(merged)
                row.rmse, row.mae = metrics["rmse"], metrics["mae"]
                row.pearson_r = metrics["pearson_r"]
                row.peak_score = metrics["peak_score"]
        rows.append(row)
    return rows


def _run_series_by_month(run_dir: Path, panels_art: PanelsArtifact) -> dict[int, pd.DataFrame]:
    """Each panel's digitized daily series keyed by its month identity."""
    from graphdig.artifacts import SeriesArtifact

    series_path = run_dir / "series.json"
    if not series_path.exists():
        return {}
    series_art = load_artifact(SeriesArtifact, series_path)
    month_by_pid = {p.panel_id: p.month for p in panels_art.panels}
    out: dict[int, pd.DataFrame] = {}
    for key, ps in series_art.panels.items():
        month = month_by_pid.get(ps.panel_id or key)
        if not month or ps.series_id != "s1" or key.startswith("annual"):
            continue
        df = pd.read_csv(run_dir / ps.csv_path)
        df["date"] = pd.to_datetime(df["x_key"], errors="coerce").dt.date
        out[month] = df
    return out


def summarize(rows: list[FullPageMonthRow]) -> dict[str, float]:
    import numpy as np

    detected = [r for r in rows if r.detected]
    edge_abs = [abs(v) for r in detected
                for v in (r.left_err_days, r.right_err_days) if not math.isnan(v)]
    peaks = [r.peak_score for r in detected if not math.isnan(r.peak_score)]
    return {
        "months": len(rows),
        "detected": len(detected),
        "mean_iou": float(np.mean([r.iou for r in detected])) if detected else 0.0,
        "median_abs_edge_days": float(np.median(edge_abs)) if edge_abs else math.nan,
        "mean_peak_score": float(np.mean(peaks)) if peaks else math.nan,
        "median_peak_score": float(np.median(peaks)) if peaks else math.nan,
    }


def evaluate_fullpage_cli(runs_glob: str, out_dir: Path,
                          paths: ZenodoPaths | None = None) -> list[FullPageMonthRow]:
    """Evaluate every pseudo-page run matched by the glob; truth files are located next
    to the run's input image (written by write_pseudo_page)."""
    import glob as globmod

    all_rows: list[FullPageMonthRow] = []
    for run_str in sorted(globmod.glob(runs_glob)):
        run_dir = Path(run_str)
        input_txt = run_dir / "input.txt"
        if not input_txt.exists():
            continue
        input_path = Path(input_txt.read_text(encoding="utf-8").strip())
        truth_path = input_path.parent / (input_path.stem + ".truth.json")
        if not truth_path.exists():
            continue
        truth = json.loads(truth_path.read_text(encoding="utf-8"))
        rows = evaluate_fullpage_run(run_dir, truth, paths)
        all_rows.extend(rows)
        s = summarize(rows)
        print(f"{truth['scan_id']} {truth['year']}: {s['detected']}/12 panels, "
              f"IoU {s['mean_iou']:.3f}, median |edge| {s['median_abs_edge_days']:.2f} d, "
              f"peak mean {s['mean_peak_score']:.3f}")
    if all_rows:
        out_dir.mkdir(parents=True, exist_ok=True)
        pd.DataFrame([r.__dict__ for r in all_rows]).to_csv(
            out_dir / "fullpage_eval.csv", index=False)
    return all_rows
