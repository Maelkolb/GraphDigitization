"""Series stage: selected polyline -> physical time/value series (the digitized graph).

Paper Sect. 4.4.5: map tile points back to page space, optionally remove baseline warp
(Eqs. 9-11), partition the plot-area x-extent into n equal slices keeping the last point
per slice, and convert pixel y to physical units via the fitted axis (Eq. 8 generalized).

`build_panel_series` is exposed separately so the QC stage can rebuild a panel's series
after rejecting a candidate (qc_auto_reselect).
"""

from __future__ import annotations

import csv
import math
from datetime import date, timedelta

import numpy as np
from PIL import Image

from graphdig.artifacts import (
    BaselineArtifact,
    CalibrationArtifact,
    LineCandidate,
    LinesArtifact,
    Panel,
    PanelBaseline,
    PanelCalibration,
    PanelsArtifact,
    PanelSeries,
    SeriesArtifact,
    Tile,
    TilesArtifact,
)
from graphdig.calibration.baseline_fit import apply_baseline_correction, interp_baseline
from graphdig.calibration.fit import AxisFit, value_at
from graphdig.pipeline import Context
from graphdig.render import draw_polyline_overlay
from graphdig.series.resample import last_index_per_slice
from graphdig.units import Unit, canonicalize, danube_unit_for

FALLBACK_SLICES = 100

CSV_COLUMNS = ["x_key", "value_native", "native_unit", "value_mm",
               "pixel_x_page", "pixel_y_page", "pixel_y_corrected", "flagged"]


def _x_keys(cal: PanelCalibration, n: int) -> list[str]:
    x = cal.x_axis
    if x.kind == "date" and x.start:
        try:
            d0 = date.fromisoformat(x.start)
            return [(d0 + timedelta(days=i)).isoformat() for i in range(n)]
        except ValueError:
            pass
    if x.kind == "numeric" and x.start and x.end:
        try:
            xs = np.linspace(float(x.start), float(x.end), n)  # handles descending too
            return [f"{v:g}" for v in xs]
        except ValueError:
            pass
    return [str(i + 1) for i in range(n)]


def _unit_for(ctx: Context, cal: PanelCalibration, x_key: str) -> Unit:
    unit = canonicalize(cal.y_axis.unit.raw)
    if unit.to_mm is not None:
        return unit
    if ctx.cfg.profile.danube_units:
        try:
            return danube_unit_for(date.fromisoformat(x_key))
        except ValueError:
            pass
    return unit


def build_panel_series(ctx: Context, tile: Tile, panel: Panel, cal: PanelCalibration,
                       cand: LineCandidate,
                       baseline: PanelBaseline | None) -> PanelSeries:
    """Digitize one panel from one selected candidate; writes CSV + curve overlay."""
    pid = tile.panel_id
    pts_tile = np.asarray(cand.points_px_tile, dtype=float).reshape(-1, 2)
    pts_page = tile.transform.tile_to_page(pts_tile)

    corrected = pts_page
    baseline_applied = False
    if (baseline is not None and baseline.line_visible
            and len(baseline.points) >= 2 and baseline.beta_px is not None):
        base_pts = np.array([[p.x, p.y] for p in baseline.points])
        corrected = apply_baseline_correction(pts_page, interp_baseline(base_pts),
                                              baseline.beta_px)
        baseline_applied = True

    area = panel.plot_area_px or panel.bbox_px
    n = cal.x_axis.n_samples or FALLBACK_SLICES
    indices = last_index_per_slice(pts_page, float(area.x), float(area.right), n)
    x_keys = _x_keys(cal, n)

    f = cal.y_axis.fit
    fit = AxisFit(slope=f.slope, intercept=f.intercept, scale=f.scale)

    csv_rel = f"series/{pid}.csv"
    gaps: list[str] = []
    sampled_page = []
    with open(ctx.run_dir / csv_rel, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(CSV_COLUMNS)
        for i, idx in enumerate(indices):
            x_key = x_keys[i]
            if idx < 0:
                gaps.append(x_key)
                writer.writerow([x_key, "", "", "", "", "", "", "true"])
                continue
            px, py = pts_page[idx]
            y_corr = corrected[idx, 1]
            value_native = float(value_at(fit, y_corr))
            unit = _unit_for(ctx, cal, x_key)
            value_mm = value_native * unit.to_mm if unit.to_mm is not None else math.nan
            sampled_page.append((px, y_corr))
            writer.writerow([x_key, f"{value_native:.4f}", unit.canonical,
                             "" if math.isnan(value_mm) else f"{value_mm:.2f}",
                             f"{px:.1f}", f"{py:.1f}", f"{y_corr:.1f}", "false"])

    if gaps:
        ctx.add_flag("series", f"{len(gaps)} empty slice(s): {', '.join(gaps[:5])}"
                     + ("..." if len(gaps) > 5 else ""), panel_id=pid)

    tile_img = Image.open(ctx.run_dir / tile.path)
    sampled_tile = (tile.transform.page_to_tile(np.array(sampled_page))
                    if sampled_page else None)
    draw_polyline_overlay(tile_img, pts_tile, sampled_tile,
                          ctx.run_dir / "overlays" / f"curve_{pid}.png")

    return PanelSeries(
        csv_path=csv_rel, n=n, x_kind=cal.x_axis.kind, gaps=gaps,
        cand_id=cand.cand_id, baseline_applied=baseline_applied,
        confidence_chain={
            "panel": panel.confidence,
            "calibration": cal.y_axis.confidence,
            "extraction": cand.confidence,
            "coverage": cand.coverage or 0.0,
        },
    )


def load_context_artifacts(ctx: Context):
    """The artifact bundle both series and qc need."""
    panels_art = ctx.load(PanelsArtifact, "panels.json")
    cal_art = ctx.load(CalibrationArtifact, "calibration.json")
    lines = ctx.load(LinesArtifact, "lines.json")
    tiles_art = ctx.load(TilesArtifact, "tiles.json")
    baseline_path = ctx.run_dir / "baseline.json"
    baseline_art = (ctx.load(BaselineArtifact, "baseline.json")
                    if ctx.cfg.use_baseline and baseline_path.exists() else None)
    return panels_art, cal_art, lines, tiles_art, baseline_art


def run(ctx: Context) -> None:
    panels_art, cal_art, lines, tiles_art, baseline_art = load_context_artifacts(ctx)
    panels_by_id = {p.panel_id: p for p in panels_art.panels}

    art = SeriesArtifact()
    for tile in tiles_art.tiles:
        pid = tile.panel_id
        tl = lines.tiles.get(tile.tile_id)
        if tl is None or tl.selected is None:
            ctx.add_flag("series", "no selected polyline", panel_id=pid, severity="blocking")
            continue
        cal = cal_art.panels.get(pid)
        if cal is None or cal.y_axis.fit is None:
            ctx.add_flag("series", "no usable axis calibration", panel_id=pid,
                         severity="blocking")
            continue
        cand = next(c for c in tl.candidates if c.cand_id == tl.selected.cand_id)
        baseline = baseline_art.panels.get(pid) if baseline_art else None
        art.panels[pid] = build_panel_series(ctx, tile, panels_by_id[pid], cal,
                                             cand, baseline)
    ctx.save(art, "series.json")
