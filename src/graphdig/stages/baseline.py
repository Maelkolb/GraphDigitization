"""Baseline stage: locate the printed zero/reference line for warp correction.

Automates the paper's baseline_annotator.py (Sect. 4.5.3). Gemini localizes the printed
line at k sample x-positions; classical CV snaps each seed to the dark ridge sub-pixel.
The correction itself is applied later in the series stage (Eqs. 9-11).
"""

from __future__ import annotations

import numpy as np
from PIL import Image

from graphdig.artifacts import (
    BaselineArtifact,
    BaselinePoint,
    CalibrationArtifact,
    PanelBaseline,
    PanelsArtifact,
    Provenance,
)
from graphdig.calibration.baseline_fit import beta_from_fit, refine_points_cv
from graphdig.calibration.fit import AxisFit
from graphdig.gemini.prompts import PROMPTS
from graphdig.gemini.schemas import BaselinePointsResponse
from graphdig.pipeline import Context
from graphdig.render import draw_baseline
from graphdig.stages.calibrate import crop_box_for

N_SAMPLE_POINTS = 15
MAX_REFINE_DELTA = 20.0  # px; larger CV corrections suggest Gemini found the wrong line


def run(ctx: Context) -> None:
    panels_art = ctx.load(PanelsArtifact, "panels.json")
    cal_art = ctx.load(CalibrationArtifact, "calibration.json")
    page = Image.open(ctx.run_dir / panels_art.image.path)
    gray = np.asarray(page.convert("L"))

    art = BaselineArtifact()
    for panel in panels_art.panels:
        crop_box = crop_box_for(panel, page.width, page.height)
        crop = page.crop((crop_box.x, crop_box.y, crop_box.right, crop_box.bottom))
        xs_1000 = np.linspace(30, 970, N_SAMPLE_POINTS).astype(int).tolist()
        prompt = PROMPTS["BASELINE_V1"].format(x_positions=xs_1000)
        result = ctx.gemini.generate_json(
            images=[crop], prompt=prompt, schema=BaselinePointsResponse,
            prompt_id="BASELINE_V1", thinking_level=ctx.cfg.gemini.thinking_baseline,
            media_resolution="high",
        )
        art.provenance = Provenance(model=result.model, prompt_id=result.prompt_id,
                                    thinking_level=result.thinking_level,
                                    attempts=result.attempts, usage=result.usage)
        if not result.ok:
            ctx.add_flag("baseline", f"Gemini call failed: {result.error}",
                         panel_id=panel.panel_id, severity="warning")
            art.panels[panel.panel_id] = PanelBaseline(line_visible=False,
                                                       flags=["gemini_failed"])
            continue
        resp = result.data
        if not resp.line_visible or not resp.points:
            ctx.add_flag("baseline", "no printed zero/reference line visible",
                         panel_id=panel.panel_id, severity="info")
            art.panels[panel.panel_id] = PanelBaseline(line_visible=False,
                                                       confidence=resp.confidence)
            continue

        seeds = [(crop_box.x + p.x_1000 / 1000.0 * crop_box.w,
                  crop_box.y + p.y_1000 / 1000.0 * crop_box.h) for p in resp.points]
        refined = refine_points_cv(gray, seeds)
        points = []
        big_deltas = 0
        for (sx, _sy), (x, y, delta) in zip(seeds, refined, strict=True):
            if abs(delta) > MAX_REFINE_DELTA:
                big_deltas += 1
            points.append(BaselinePoint(x=x, y=y, refined=delta != 0.0, residual_px=delta))
        flags = []
        if big_deltas:
            flags.append(f"large_refinement:{big_deltas}")
            ctx.add_flag("baseline", f"{big_deltas} point(s) moved > {MAX_REFINE_DELTA}px "
                         "during CV refinement", panel_id=panel.panel_id, severity="warning")

        beta = None
        cal = cal_art.panels.get(panel.panel_id)
        if cal and cal.y_axis.fit:
            f = cal.y_axis.fit
            fit = AxisFit(slope=f.slope, intercept=f.intercept, scale=f.scale)
            try:
                beta = float(beta_from_fit(fit))
            except ValueError:
                flags.append("beta_unavailable")

        pb = PanelBaseline(points=points, beta_px=beta, confidence=resp.confidence,
                           flags=flags)
        art.panels[panel.panel_id] = pb
        draw_baseline(page, panel, pb,
                      ctx.run_dir / "overlays" / f"baseline_{panel.panel_id}.png")
    ctx.save(art, "baseline.json")
