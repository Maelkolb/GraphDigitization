"""Component evaluation: Gemini panel detection vs. human month annotations.

The dataset publishes only monthly tiles, so full-page detection is evaluated on STITCHED
PSEUDO-PAGES: the 12 tiles of a gauge-year are concatenated horizontally (in month order)
and the panels stage must recover the seam positions. Reported per month: IoU between the
detected panel and the known tile extent, and the x-edge error in pixels and days.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from graphdig.data.gt_loaders import ZenodoPaths
from graphdig.data.pseudo_page import PseudoPage, build_pseudo_page
from graphdig.dates import days_in_month
from graphdig.geometry import BoxPx


@dataclass
class PanelEvalRow:
    scan_id: str
    month: int
    detected: bool
    iou: float = 0.0
    left_err_px: float = 0.0
    right_err_px: float = 0.0
    left_err_days: float = 0.0
    right_err_days: float = 0.0


def compare_panels(pseudo: PseudoPage, detected_boxes: list[BoxPx]) -> list[PanelEvalRow]:
    """Match detected panels to true monthly extents by best IoU (greedy, left to right)."""
    rows: list[PanelEvalRow] = []
    remaining = list(detected_boxes)
    for month_idx, truth in enumerate(pseudo.extents, start=1):
        n_days = days_in_month(pseudo.year, month_idx)
        px_per_day = truth.w / n_days
        best, best_iou = None, 0.0
        for box in remaining:
            iou = truth.iou(box)
            if iou > best_iou:
                best, best_iou = box, iou
        if best is None or best_iou < 0.2:
            rows.append(PanelEvalRow(pseudo.scan_id, month_idx, detected=False))
            continue
        remaining.remove(best)
        rows.append(PanelEvalRow(
            pseudo.scan_id, month_idx, detected=True, iou=best_iou,
            left_err_px=float(best.x - truth.x),
            right_err_px=float(best.right - truth.right),
            left_err_days=float((best.x - truth.x) / px_per_day),
            right_err_days=float((best.right - truth.right) / px_per_day),
        ))
    return rows


def evaluate_panels_on_pseudo_page(scan_id: str, year: int, out_dir: Path,
                                   paths: ZenodoPaths | None = None,
                                   client=None) -> list[PanelEvalRow]:
    """Run the panels stage (danube prompt) on a stitched pseudo-page. Live API."""
    from graphdig.config import GeminiConfig
    from graphdig.gemini.client import GeminiClient
    from graphdig.gemini.prompts import triage_prompt
    from graphdig.gemini.schemas import TriageResponse
    from graphdig.geometry import Box1000, bbox_1000_to_px

    paths = paths or ZenodoPaths()
    cfg = GeminiConfig()
    client = client or GeminiClient(cfg)
    pseudo = build_pseudo_page(scan_id, year, paths)
    out_dir.mkdir(parents=True, exist_ok=True)
    page_path = out_dir / f"pseudo_{scan_id}.png"
    pseudo.image.save(page_path)

    prompt_id, prompt = triage_prompt("danube")
    result = client.generate_json(images=[pseudo.image], prompt=prompt,
                                  schema=TriageResponse, prompt_id=prompt_id,
                                  thinking_level=cfg.thinking_panels,
                                  media_resolution="high")
    if not result.ok:
        raise RuntimeError(f"panel detection failed on pseudo page: {result.error}")
    boxes = [bbox_1000_to_px(Box1000(**p.box.model_dump()),
                             pseudo.image.width, pseudo.image.height)
             for p in result.data.panels]
    return compare_panels(pseudo, boxes)
