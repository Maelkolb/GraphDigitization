"""Gemini point-reading extractor: the MLLM traces each named series directly.

Complements LineFormer exactly where instance segmentation is weakest - faint or dotted
strokes, dense multi-curve bundles, sparse charts - by asking Gemini for the y position
of every named series at k sampled x positions. No GPU, no pinned environment.

Output contract: one candidate per series with the selection PRE-FILLED
(method="gemini_points"); the select stage keeps pre-filled selections and only adds
coverage/s_alpha diagnostics. Not suited to dense multi-thousand-point extraction -
that remains LineFormer's job (k is capped, default 40 samples).
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image

from graphdig.artifacts import (
    CalibrationArtifact,
    LineCandidate,
    LinesArtifact,
    PanelsArtifact,
    Selection,
    Tile,
    TileLines,
    load_artifact,
)
from graphdig.extractors.base import ExtractParams, LineExtractor
from graphdig.gemini.prompts import PROMPTS


class GeminiPointsExtractor(LineExtractor):
    name = "gemini_points"

    def __init__(self, ctx):
        if ctx is None:
            raise ValueError("gemini_points requires the pipeline context (Gemini client)")
        self.ctx = ctx

    def extract(self, tiles: list[Tile], run_dir: Path,
                params: ExtractParams) -> LinesArtifact:
        run_dir = Path(run_dir)
        panels_art = load_artifact(PanelsArtifact, run_dir / "panels.json")
        cal_art = load_artifact(CalibrationArtifact, run_dir / "calibration.json")
        cls = panels_art.classification
        k_cap = self.ctx.cfg.gemini_points_k

        art = LinesArtifact(backend=self.name, params={"k_cap": float(k_cap)})
        for tile in tiles:
            n_series = max(1, cls.n_series)
            labels = (cls.series_labels
                      or [f"series {i + 1}" for i in range(n_series)])[:n_series]
            cal = cal_art.panels.get(tile.panel_id)
            n_samples = cal.x_axis.n_samples if cal else None
            k = min(n_samples or k_cap, k_cap)
            xs_1000 = np.linspace(10, 990, k).astype(int)

            prompt = PROMPTS["POINTS_V1"].format(series_list=", ".join(labels),
                                                 x_positions=xs_1000.tolist())
            result = self.ctx.gemini.generate_json(
                images=[Image.open(run_dir / tile.path)], prompt=prompt,
                prompt_id="POINTS_V1",
                schema=_points_schema(), thinking_level=self.ctx.cfg.gemini.thinking_points,
                media_resolution="high",
            )
            if not result.ok:
                art.tiles[tile.tile_id] = TileLines(error=f"gemini_points: {result.error}")
                continue
            tl = TileLines()
            for i, trace in enumerate(result.data.series[:max(n_series, len(labels))]):
                pts = [(x / 1000.0 * tile.width, p.y_1000 / 1000.0 * tile.height)
                       for x, p in zip(xs_1000, trace.points, strict=False) if p.visible]
                if len(pts) < 2:
                    continue
                visible_frac = (sum(p.visible for p in trace.points)
                                / max(1, len(trace.points)))
                cand = LineCandidate(
                    cand_id=i, confidence=trace.confidence * visible_frac,
                    n_points=len(pts), points_px_tile=[[x, y] for x, y in pts])
                tl.candidates.append(cand)
                label = trace.series_label or (labels[i] if i < len(labels) else "")
                tl.selections.append(Selection(
                    cand_id=i, method="gemini_points",
                    series_id=f"s{len(tl.selections) + 1}", series_label=label))
            tl.selected = tl.selections[0] if tl.selections else None
            if not tl.candidates:
                tl.error = "gemini_points: no visible points returned"
            if result.usage:
                art.backend_meta[f"tokens:{tile.tile_id}"] = str(
                    result.usage.get("total_token_count", 0))
            art.tiles[tile.tile_id] = tl
        return art


def _points_schema():
    from graphdig.gemini.schemas import PointsResponse

    return PointsResponse
