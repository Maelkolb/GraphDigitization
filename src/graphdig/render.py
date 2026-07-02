"""Overlay rendering (PIL). Overlays are the visual ground truth of every run:
each stage draws what it believes onto the scan so a human (or the QC judge) can verify it.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from graphdig.artifacts import Panel, PanelBaseline, PanelCalibration
from graphdig.calibration.fit import AxisFit, value_at

PANEL_COLOR = (220, 60, 40)
PLOT_AREA_COLOR = (40, 120, 220)
TICK_COLOR = (40, 160, 60)
BASELINE_COLOR = (200, 40, 200)
CURVE_COLOR = (230, 30, 30)
SAMPLE_COLOR = (30, 30, 230)
CANDIDATE_COLORS = [(230, 30, 30), (30, 120, 230), (30, 180, 60), (240, 160, 20),
                    (160, 40, 200), (0, 180, 180), (240, 80, 160), (120, 120, 40)]


def _font(size: int) -> ImageFont.ImageFont:
    try:
        return ImageFont.truetype("arial.ttf", size)
    except OSError:
        return ImageFont.load_default()


def _line_width(img: Image.Image) -> int:
    return max(2, min(img.width, img.height) // 600)


def draw_panels(page: Image.Image, panels: list[Panel], out_path: Path) -> Path:
    img = page.convert("RGB").copy()
    d = ImageDraw.Draw(img)
    lw = _line_width(img)
    font = _font(14 * lw)
    for p in panels:
        b = p.bbox_px
        d.rectangle([b.x, b.y, b.right, b.bottom], outline=PANEL_COLOR, width=lw)
        if p.plot_area_px:
            a = p.plot_area_px
            d.rectangle([a.x, a.y, a.right, a.bottom], outline=PLOT_AREA_COLOR, width=lw)
        d.text((b.x + lw, b.y + lw), f"{p.panel_id} {p.confidence:.2f}",
               fill=PANEL_COLOR, font=font)
    img.save(out_path)
    return out_path


def draw_calibration(page: Image.Image, panel: Panel, cal: PanelCalibration,
                     fit: AxisFit | None, out_path: Path) -> Path:
    """Panel crop with tick readings and (if fitted) the implied value gridlines."""
    b = panel.bbox_px
    img = page.convert("RGB").crop((b.x, b.y, b.right, b.bottom))
    d = ImageDraw.Draw(img)
    lw = _line_width(img)
    font = _font(12 * lw)
    for t in cal.y_axis.ticks:
        y = t.pixel - b.y
        color = TICK_COLOR if t.used else (150, 150, 150)
        d.line([(0, y), (img.width * 0.05 + 10, y)], fill=color, width=lw)
        d.text((img.width * 0.05 + 14, y - 7 * lw),
               f"{t.value:g}{'*' if not t.used else ''}", fill=color, font=font)
    if fit is not None and cal.y_axis.ticks:
        pixels = [t.pixel for t in cal.y_axis.ticks if t.used]
        if pixels:
            lo, hi = min(pixels), max(pixels)
            for y in np.linspace(lo, hi, 5):
                v = value_at(fit, float(y))
                d.line([(0, y - b.y), (img.width, y - b.y)], fill=(255, 0, 0), width=1)
                d.text((img.width - 60 * lw, y - b.y - 7 * lw), f"{v:.1f}",
                       fill=(255, 0, 0), font=font)
    img.save(out_path)
    return out_path


def draw_baseline(page: Image.Image, panel: Panel, baseline: PanelBaseline,
                  out_path: Path) -> Path:
    b = panel.bbox_px
    img = page.convert("RGB").crop((b.x, b.y, b.right, b.bottom))
    d = ImageDraw.Draw(img)
    lw = _line_width(img)
    pts = [(p.x - b.x, p.y - b.y) for p in baseline.points]
    if len(pts) >= 2:
        d.line(pts, fill=BASELINE_COLOR, width=lw)
    r = 2 * lw
    for x, y in pts:
        d.ellipse([x - r, y - r, x + r, y + r], outline=BASELINE_COLOR, width=lw)
    img.save(out_path)
    return out_path


def draw_polyline_overlay(tile: Image.Image, points_xy: np.ndarray,
                          sampled_xy: np.ndarray | None, out_path: Path) -> Path:
    """Selected polyline (red) + resampled per-slice points (blue dots) on the tile."""
    img = tile.convert("RGB").copy()
    d = ImageDraw.Draw(img)
    lw = _line_width(img)
    pts = np.asarray(points_xy, dtype=float).reshape(-1, 2)
    if len(pts) >= 2:
        order = np.argsort(pts[:, 0])
        d.line([tuple(p) for p in pts[order]], fill=CURVE_COLOR, width=lw)
    if sampled_xy is not None:
        r = 3 * lw
        for x, y in np.asarray(sampled_xy, dtype=float).reshape(-1, 2):
            if not (np.isnan(x) or np.isnan(y)):
                d.ellipse([x - r, y - r, x + r, y + r], fill=SAMPLE_COLOR)
    img.save(out_path)
    return out_path


def draw_candidates(tile: Image.Image, candidates: list[tuple[int, np.ndarray]],
                    out_path: Path) -> Path:
    """All candidate polylines in distinct colors with an id legend (for Gemini pick)."""
    img = tile.convert("RGB").copy()
    d = ImageDraw.Draw(img)
    lw = _line_width(img)
    font = _font(14 * lw)
    for i, (cand_id, pts) in enumerate(candidates):
        color = CANDIDATE_COLORS[i % len(CANDIDATE_COLORS)]
        pts = np.asarray(pts, dtype=float).reshape(-1, 2)
        if len(pts) >= 2:
            order = np.argsort(pts[:, 0])
            d.line([tuple(p) for p in pts[order]], fill=color, width=lw)
        d.rectangle([8, 8 + 18 * lw * i, 8 + 14 * lw, 8 + 18 * lw * i + 14 * lw], fill=color)
        d.text((12 + 14 * lw, 8 + 18 * lw * i), f"candidate {cand_id}", fill=color, font=font)
    img.save(out_path)
    return out_path
