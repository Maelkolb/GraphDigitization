"""Evaluation CLI: orchestrates component and end-to-end evaluations into a report."""

from __future__ import annotations

from datetime import date
from pathlib import Path


def _out_dir(args) -> Path:
    out = Path(args.out) if args.out else Path("outputs/eval") / date.today().isoformat()
    out.mkdir(parents=True, exist_ok=True)
    return out


def _eval_calibration(out: Path, lines: list[str]) -> None:
    import pandas as pd

    from graphdig.eval.calibration_eval import evaluate_calibration

    results = evaluate_calibration(out_dir=out / "calibration")
    df = pd.DataFrame([r.__dict__ for r in results])
    df.to_csv(out / "calibration_eval.csv", index=False)
    ok = df[df["slope_err_pct"].notna()]
    lines += ["## Calibration: Gemini vs. human anchors", "",
              f"- months evaluated: {len(df)} ({len(ok)} usable)",
              f"- median slope error: {ok['slope_err_pct'].median():.2f} %",
              f"- median zero-pixel error: {ok['zero_px_err'].median():.1f} px",
              f"- median induced series error (MAE): {ok['induced_mae_mm'].median():.2f} mm",
              f"- worst induced MAE: {ok['induced_mae_mm'].max():.2f} mm",
              "", "Full table: `calibration_eval.csv`", ""]


def _eval_panels(out: Path, lines: list[str], scan_ids: list[str] | None = None) -> None:
    import pandas as pd

    from graphdig.data.gt_loaders import GT_SCAN_IDS, ZenodoPaths, load_gt_pixels
    from graphdig.eval.panels_eval import evaluate_panels_on_pseudo_page

    paths = ZenodoPaths()
    rows = []
    for scan_id in scan_ids or GT_SCAN_IDS[:3]:
        year = load_gt_pixels(paths.gt_pixels(scan_id))["DATE"].iloc[0].year
        rows += [r.__dict__ for r in
                 evaluate_panels_on_pseudo_page(scan_id, year, out / "panels")]
    df = pd.DataFrame(rows)
    df.to_csv(out / "panels_eval.csv", index=False)
    det = df[df["detected"]]
    lines += ["## Panels: stitched pseudo-page seam recovery", "",
              f"- panels detected: {len(det)}/{len(df)}",
              f"- mean IoU: {det['iou'].mean():.3f}",
              f"- median |x-edge error|: "
              f"{det[['left_err_days', 'right_err_days']].abs().median().max():.2f} days",
              "", "Full table: `panels_eval.csv`", ""]


def _eval_series(out: Path, lines: list[str], runs_glob: str | None) -> None:
    import glob as globmod
    import re

    from graphdig.eval.series_eval import (
        attach_paper_results,
        evaluate_month,
        rows_to_frame,
    )

    if not runs_glob:
        lines += ["## Series: skipped (pass --runs <glob of run dirs>)", ""]
        return
    rows = []
    for run_dir in sorted(globmod.glob(runs_glob)):
        m = re.search(r"(\d{6})_tif_M(\d{2})", run_dir)
        if not m:
            continue
        row = evaluate_month(Path(run_dir), m.group(1), int(m.group(2)))
        if row:
            rows.append(row)
    attach_paper_results(rows)
    df = rows_to_frame(rows)
    df.to_csv(out / "series_eval.csv", index=False)
    if not df.empty:
        lines += ["## Series: end-to-end vs. ground truth", "",
                  f"- gauge-months evaluated: {len(df)}",
                  f"- mean peak-aware score: {df['peak_score'].mean():.3f}"
                  + (f" (paper best-candidate mean on same months: "
                     f"{df['paper_peak_score'].mean():.3f})"
                     if df["paper_peak_score"].notna().any() else ""),
                  f"- mean Pearson r: {df['pearson_r'].mean():.3f}",
                  f"- mean RMSE: {df['rmse'].mean():.2f} (GT units)",
                  "", "Full table: `series_eval.csv`", ""]


def evaluate_cli(args) -> int:
    out = _out_dir(args)
    lines: list[str] = [f"# GraphDigitization evaluation — {date.today().isoformat()}", ""]
    component = args.component
    scan_ids = ([s.strip() for s in args.scan_ids.split(",")]
                if getattr(args, "scan_ids", None) else None)
    try:
        if component in ("calibration", "all"):
            _eval_calibration(out, lines)
        if component in ("panels", "all"):
            _eval_panels(out, lines, scan_ids)
        if component in ("series", "all"):
            _eval_series(out, lines, args.runs)
        if component == "fullpage":
            from graphdig.eval.fullpage_eval import evaluate_fullpage_cli, summarize

            if not args.runs:
                lines += ["## Fullpage: skipped (pass --runs <glob of run dirs>)", ""]
            else:
                rows = evaluate_fullpage_cli(args.runs, out)
                if rows:
                    s = summarize(rows)
                    lines += ["## Full-page runs vs truth", "",
                              f"- panels detected: {s['detected']}/{s['months']}",
                              f"- mean IoU: {s['mean_iou']:.3f}",
                              f"- median |edge error|: "
                              f"{s['median_abs_edge_days']:.2f} days",
                              f"- peak score mean/median: {s['mean_peak_score']:.3f} / "
                              f"{s['median_peak_score']:.3f}",
                              "", "Full table: `fullpage_eval.csv`", ""]
    finally:
        (out / "report.md").write_text("\n".join(lines), encoding="utf-8")
        print(f"evaluation report: {out / 'report.md'}")
    return 0
