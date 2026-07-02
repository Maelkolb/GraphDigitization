"""Select stage: score candidates (coverage + confidence) and pick one per tile.

Implements the paper's automated candidate selection (Sect. 4.5.4): coverage is the
fraction of x-slices with a predicted point; s_alpha = 0.31*confidence + 0.69*coverage
(Eq. 12). When the top two viable candidates are nearly tied, an optional Gemini visual
pick arbitrates - the paper found human visual choice (0.968) beats score-based selection
(0.937), and the MLLM judge stands in for that human.
"""

from __future__ import annotations

import numpy as np
from PIL import Image

from graphdig.artifacts import (
    CalibrationArtifact,
    LinesArtifact,
    Selection,
    TilesArtifact,
)
from graphdig.gemini.prompts import PROMPTS
from graphdig.gemini.schemas import PickResponse
from graphdig.pipeline import Context
from graphdig.render import draw_candidates
from graphdig.series.resample import coverage, s_alpha

FALLBACK_SLICES = 100


def _n_slices(cal, tile_id: str) -> int:
    panel_cal = cal.panels.get(tile_id)
    if panel_cal and panel_cal.x_axis.n_samples:
        return panel_cal.x_axis.n_samples
    return FALLBACK_SLICES


def gemini_pick(ctx: Context, tile, viable) -> int | None:
    tile_img = Image.open(ctx.run_dir / tile.path)
    overlay_path = ctx.run_dir / "overlays" / f"pick_{tile.tile_id}.png"
    draw_candidates(tile_img,
                    [(c.cand_id, np.array(c.points_px_tile)) for c in viable[:6]],
                    overlay_path)
    result = ctx.gemini.generate_json(
        images=[overlay_path], prompt=PROMPTS["PICK_V1"], schema=PickResponse,
        prompt_id="PICK_V1", thinking_level=ctx.cfg.gemini.thinking_pick,
        media_resolution="high",
    )
    if result.ok and any(c.cand_id == result.data.best_cand_id for c in viable):
        return result.data.best_cand_id
    return None


def run(ctx: Context) -> None:
    lines = ctx.load(LinesArtifact, "lines.json")
    tiles_art = ctx.load(TilesArtifact, "tiles.json")
    cal = ctx.load(CalibrationArtifact, "calibration.json")
    gates = ctx.cfg.gates
    tiles_by_id = {t.tile_id: t for t in tiles_art.tiles}

    for tile_id, tl in lines.tiles.items():
        if tl.error or not tl.candidates:
            continue
        tile = tiles_by_id[tile_id]
        n = _n_slices(cal, tile_id)
        for c in tl.candidates:
            pts = np.asarray(c.points_px_tile, dtype=float).reshape(-1, 2)
            c.coverage = coverage(pts, 0.0, float(tile.width), n)
            c.s_alpha = s_alpha(c.confidence, c.coverage, gates.alpha_coverage)
            c.viable = c.coverage >= gates.coverage_viable

        ranked = sorted(tl.candidates, key=lambda c: -(c.s_alpha or 0.0))
        best = ranked[0]
        selection = Selection(cand_id=best.cand_id, method="s_alpha",
                              alpha_coverage=gates.alpha_coverage)

        viable = [c for c in ranked if c.viable]
        near_tie = (len(viable) >= 2
                    and (viable[0].s_alpha or 0) - (viable[1].s_alpha or 0) < gates.pick_margin)
        if near_tie:
            try:
                pick = gemini_pick(ctx, tile, viable)
            except Exception as exc:  # no API key / network: score selection stands
                ctx.add_flag("select", f"Gemini pick unavailable ({exc}); using s_alpha",
                             panel_id=tile_id, severity="info")
                pick = None
            if pick is not None:
                selection.gemini_pick = pick
                selection.agreement = pick == best.cand_id
                if pick != best.cand_id:
                    selection = Selection(cand_id=pick, method="gemini_pick",
                                          alpha_coverage=gates.alpha_coverage,
                                          gemini_pick=pick, agreement=False)

        if not best.viable and selection.method == "s_alpha":
            ctx.add_flag("select",
                         f"best candidate coverage {best.coverage:.3f} below viability "
                         f"gate {gates.coverage_viable}", panel_id=tile_id,
                         severity="warning")
        tl.selected = selection
    ctx.save(lines, "lines.json")
