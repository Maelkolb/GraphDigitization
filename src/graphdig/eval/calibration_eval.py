"""Component evaluation: Gemini axis calibration vs. the paper's human anchors.

For each GT gauge-year page and month tile:
1. HUMAN mapping: two-anchor fit from monthannotations (LOW/HIGH values at the bottom/top
   border of the January bbox, per the data descriptor) - exactly what annotators produced.
2. GEMINI mapping: the calibrate stage's fit on the monthly tile, shifted from tile to page
   coordinates via the month bbox.
3. Compare: slope error (%), zero-pixel (intercept) error, and the INDUCED SERIES ERROR -
   both mappings applied to the same GT pixel polyline, differenced on the GT level scale
   (a per-page affine derived from the human anchors; see _grid_to_gt_affine).

Requires: fetched tiles + a GEMINI_API_KEY (live component). Results are cached per tile
under the eval output dir so re-runs only hit the API for missing tiles.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image

from graphdig.artifacts import Provenance
from graphdig.calibration.fit import Tick, fit_axis, two_anchor_fit, value_at
from graphdig.config import GeminiConfig
from graphdig.data.gt_loaders import (
    GT_SCAN_IDS,
    ZenodoPaths,
    load_gt_pixels,
    load_month_yolo,
)
from graphdig.gemini.prompts import PROMPTS
from graphdig.gemini.schemas import AxisCalResponse


@dataclass
class MonthResult:
    scan_id: str
    month: int
    n_ticks: int
    n_used: int
    r2: float
    slope_err_pct: float
    zero_px_err: float
    induced_rmse_mm: float
    induced_mae_mm: float
    flags: str = ""


def _human_fit(ann):
    c_low, c_high = ann.anchors_px
    return two_anchor_fit(c_low, ann.low_value, c_high, ann.high_value)


def _grid_to_gt_affine(human, gt) -> tuple[float, float]:
    """Fit GT_level = a * grid_value + b using the human mapping over the GT rows.

    Empirically a ≈ 29.186 (per grid unit) and b ≈ +1 grid unit: the dataset's level
    scale is (grid + 1) x 29.1859 (see docs/dataset_layout.md). Deriving (a, b) per page
    keeps the eval correct even where that convention varies.
    """
    c = gt["C_Y"].to_numpy(dtype=float)
    v_grid = np.asarray(value_at(human, c), dtype=float)
    # GAUGELEVEL includes the baseline adjustment; the affine fit tolerates it as noise
    a, b = np.polyfit(v_grid, gt["GAUGELEVEL"].to_numpy(dtype=float), 1)
    return float(a), float(b)


def _gemini_ticks_page(client, tile_path: Path, tile_y0: float, tile_h_page: float,
                       cfg: GeminiConfig, cache: Path) -> tuple[list[Tick], dict]:
    """Ticks read from the tile, converted to PAGE pixel rows. Cached as JSON."""
    if cache.exists():
        raw = json.loads(cache.read_text(encoding="utf-8"))
    else:
        img = Image.open(tile_path)
        result = client.generate_json(
            images=[img], prompt=PROMPTS["CALIB_V1"], schema=AxisCalResponse,
            prompt_id="CALIB_V1", thinking_level=cfg.thinking_calibrate,
            media_resolution="ultra_high",
        )
        if not result.ok:
            raise RuntimeError(f"Gemini failed on {tile_path.name}: {result.error}")
        raw = {"response": result.data.model_dump(),
               "provenance": Provenance(model=result.model, prompt_id=result.prompt_id,
                                        attempts=result.attempts,
                                        usage=result.usage).model_dump(),
               "tile_height": img.height}
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_text(json.dumps(raw), encoding="utf-8")
    resp = AxisCalResponse.model_validate(raw["response"])
    tile_h = raw["tile_height"]
    # tiles are 1:1 crops of the month bbox plus a small symmetric margin (~5 px/side,
    # verified empirically) - map by offset, never by scaling
    margin_top = (tile_h - tile_h_page) / 2.0
    ticks = [Tick(pixel=tile_y0 - margin_top + t.pos_1000 / 1000.0 * tile_h,
                  value=t.value, label_text=t.label_text)
             for t in resp.y_ticks if t.legible]
    return ticks, raw


def evaluate_calibration(scan_ids: list[str] | None = None,
                         out_dir: Path = Path("outputs/eval/calibration"),
                         paths: ZenodoPaths | None = None,
                         client=None, months: list[int] | None = None) -> list[MonthResult]:
    from graphdig.gemini.client import GeminiClient

    paths = paths or ZenodoPaths()
    cfg = GeminiConfig()
    client = client or GeminiClient(cfg)
    scan_ids = scan_ids or GT_SCAN_IDS
    months = months or list(range(1, 13))
    results: list[MonthResult] = []

    for scan_id in scan_ids:
        ann = load_month_yolo(paths.month_yolo(scan_id))
        gt = load_gt_pixels(paths.gt_pixels(scan_id))
        human = _human_fit(ann)
        # Per-page affine map grid units -> GT GAUGELEVEL scale, derived from the human
        # anchors against the (exactly linear) GT level column. Self-calibrating: absorbs
        # the dataset's datum shift and 29.1859 factor without hardcoding either.
        a, b = _grid_to_gt_affine(human, gt)

        for month in months:
            tile_path = paths.tile(scan_id, month)
            if not tile_path.exists() or month not in ann.boxes:
                continue
            _bx0, by0, _bx1, by1 = ann.boxes[month].edges_px(ann.width, ann.height)
            cache = out_dir / "cache" / f"{scan_id}_M{month:02d}.json"
            try:
                ticks, _ = _gemini_ticks_page(client, tile_path, by0, by1 - by0, cfg, cache)
            except RuntimeError as exc:
                results.append(MonthResult(scan_id, month, 0, 0, 0.0, np.nan, np.nan,
                                           np.nan, np.nan, flags=str(exc)))
                continue
            if len(ticks) < 2:
                results.append(MonthResult(scan_id, month, len(ticks), 0, 0.0, np.nan,
                                           np.nan, np.nan, np.nan, flags="too_few_ticks"))
                continue
            fit = fit_axis(ticks)

            slope_err = abs(fit.slope - human.slope) / abs(human.slope) * 100.0
            zero_human = -human.intercept / human.slope
            zero_gemini = -fit.intercept / fit.slope
            # induced error: both mappings applied to this month's GT pixel rows,
            # differenced on the GT level scale
            month_gt = gt[[d.month == month for d in gt["DATE"]]]
            c = month_gt["C_Y"].to_numpy(dtype=float)
            v_human = a * np.asarray(value_at(human, c), dtype=float) + b
            v_gemini = a * np.asarray(value_at(fit, c), dtype=float) + b
            diff_mm = v_gemini - v_human
            results.append(MonthResult(
                scan_id, month, fit.n_ticks, fit.n_used, fit.r2,
                slope_err_pct=float(slope_err),
                zero_px_err=float(abs(zero_gemini - zero_human)),
                induced_rmse_mm=float(np.sqrt(np.mean(diff_mm ** 2))),
                induced_mae_mm=float(np.mean(np.abs(diff_mm))),
            ))
    return results
