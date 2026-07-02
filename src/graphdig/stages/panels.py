"""Panels stage: Gemini locates every chart panel + plot area on the page.

Automates the paper's month_annotator bounding boxes (Rehbein 2026, Sect. 4.5.1). Because
"a small x-overshoot can shift the date assignment by a whole day", panel x-edges can be
snapped to the strongest printed vertical gridline nearby (danube profile).
"""

from __future__ import annotations

import numpy as np
from PIL import Image

from graphdig.artifacts import ImageRef, Orientation, Panel, PanelsArtifact, Provenance, XExtentHint
from graphdig.gemini.prompts import panels_prompt
from graphdig.gemini.schemas import PanelsResponse
from graphdig.geometry import Box1000, BoxPx, bbox_1000_to_px
from graphdig.pipeline import Context
from graphdig.render import draw_panels

IOU_DEDUPE = 0.8
EDGE_SEARCH_FRACTION = 0.01  # search window for gridline snapping, fraction of page width


def _detect(ctx: Context, img: Image.Image, prompt_id: str, prompt: str):
    result = ctx.gemini.generate_json(
        images=[img], prompt=prompt, schema=PanelsResponse, prompt_id=prompt_id,
        thinking_level=ctx.cfg.gemini.thinking_panels, media_resolution="high",
    )
    if not result.ok:
        raise RuntimeError(f"panel detection failed: {result.error}")
    return result


def _to_panels(resp: PanelsResponse, width: int, height: int,
               conf_min: float) -> tuple[list[Panel], list[str]]:
    flags: list[str] = []
    panels: list[Panel] = []
    for gp in resp.panels:
        bbox = bbox_1000_to_px(Box1000(**gp.box.model_dump()), width, height, min_size=20)
        plot = bbox_1000_to_px(Box1000(**gp.plot_area.model_dump()), width, height, min_size=10)
        hint_kind = "unknown"
        panels.append(Panel(
            panel_id="", label=gp.label, bbox_px=bbox, plot_area_px=plot,
            x_extent_hint=XExtentHint(kind=hint_kind, start_label=gp.x_start_label,
                                      end_label=gp.x_end_label),
            confidence=gp.confidence,
        ))
    # drop near-duplicates, keep the higher-confidence one
    panels.sort(key=lambda p: -p.confidence)
    kept: list[Panel] = []
    for p in panels:
        if any(p.bbox_px.iou(k.bbox_px) > IOU_DEDUPE for k in kept):
            continue
        kept.append(p)
    low = [p for p in kept if p.confidence < conf_min]
    for p in low:
        p.flags.append("low_confidence")
    if low:
        flags.append(f"{len(low)} panel(s) below confidence gate")
    # reading order: row bands (quarter page height), then left to right
    band = max(1, max(p.bbox_px.h for p in kept) // 2) if kept else 1
    kept.sort(key=lambda p: (p.bbox_px.y // band, p.bbox_px.x))
    for i, p in enumerate(kept, start=1):
        p.panel_id = f"p{i:02d}"
    return kept, flags


def _refine_x_edges(page: Image.Image, panels: list[Panel]) -> None:
    """Snap plot-area left/right edges to the strongest vertical gridline nearby."""
    import cv2

    gray = np.asarray(page.convert("L"), dtype=np.float32)
    sobel = np.abs(cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3))
    window = max(3, int(page.width * EDGE_SEARCH_FRACTION))
    for p in panels:
        area = p.plot_area_px
        if area is None or area.w < 4 * window:
            continue
        rows = slice(area.y, area.bottom)
        col_strength = sobel[rows].sum(axis=0)
        new_edges = {}
        for name, edge in (("left", area.x), ("right", area.right)):
            lo = max(0, edge - window)
            hi = min(page.width, edge + window + 1)
            if hi - lo < 3:
                continue
            new_edges[name] = lo + int(np.argmax(col_strength[lo:hi]))
        left = new_edges.get("left", area.x)
        right = new_edges.get("right", area.right)
        if right - left > 2 * window:
            p.plot_area_px = BoxPx(x=left, y=area.y, w=right - left, h=area.h)
            p.x_edge_refined = True


def run(ctx: Context) -> None:
    pages = sorted((ctx.run_dir / "pages").glob("*.png"))
    page_path = pages[0]
    img = Image.open(page_path)

    prompt_id, prompt = panels_prompt(ctx.cfg.profile.panel_prompt_variant)
    result = _detect(ctx, img, prompt_id, prompt)
    orientation = Orientation()

    if result.data.rotation_deg:
        deg = result.data.rotation_deg
        img = img.rotate(-deg, expand=True)  # PIL rotates counter-clockwise
        rot_path = page_path.with_name(page_path.stem + f"_rot{deg}.png")
        img.save(rot_path)
        page_path = rot_path
        orientation = Orientation(rotation_applied_deg=deg,
                                  reason="Gemini: axis labels not horizontal")
        result = _detect(ctx, img, prompt_id, prompt)  # boxes in rotated coords

    panels, flags = _to_panels(result.data, img.width, img.height,
                               ctx.cfg.gates.panel_conf_min)
    for reason in flags:
        ctx.add_flag("panels", reason)

    expected = ctx.cfg.profile.expected_panels
    if expected and len(panels) not in (1, expected):
        ctx.add_flag("panels",
                     f"expected 1 or {expected} panels, got {len(panels)}", severity="warning")
    if not panels:
        ctx.add_flag("panels", "no chart panels detected", severity="blocking")

    if ctx.cfg.profile.refine_x_edges and panels:
        _refine_x_edges(img, panels)

    art = PanelsArtifact(
        page_id=page_path.stem,
        image=ImageRef(path=f"pages/{page_path.name}", width=img.width, height=img.height),
        orientation=orientation,
        panels=panels,
        provenance=Provenance(model=result.model, prompt_id=result.prompt_id,
                              thinking_level=result.thinking_level,
                              attempts=result.attempts, usage=result.usage),
    )
    ctx.save(art, "panels.json")
    draw_panels(img, panels, ctx.run_dir / "overlays" / "panels.png")
