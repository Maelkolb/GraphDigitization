"""Stitched pseudo-pages: full-sheet stand-ins built from the dataset's monthly tiles.

Zenodo 17296751 publishes no full annual pages, so full-page segmentation and end-to-end
digitization are validated on pseudo-pages: the 12 monthly tiles of a gauge-year
concatenated horizontally (bottom-aligned, like the originals). Ground-truth panel
extents fall out of the construction; calibration comes from the dataset's human
annotations expressed as user hints (the tiles carry no axis labels).

Real full-page scans use the exact same pipeline path:
`graphdig run sheet.tif --profile danube [--hints hints.json]` - nothing here is
pseudo-specific except the construction utilities.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from PIL import Image

from graphdig.data.danube_prep import tile_anchor_rows
from graphdig.data.gt_loaders import MonthAnnotations, ZenodoPaths, load_month_yolo
from graphdig.dates import days_in_month, month_span
from graphdig.geometry import BoxPx
from graphdig.hints import Hints, PanelHint, YAnchorHint, save_hints
from graphdig.units import danube_unit_for


@dataclass
class PseudoPage:
    image: Image.Image
    scan_id: str
    year: int
    extents: list[BoxPx]  # true tile extent per month (index 0 = January)


def build_pseudo_page(scan_id: str, year: int,
                      paths: ZenodoPaths | None = None) -> PseudoPage:
    paths = paths or ZenodoPaths()
    tiles = [Image.open(paths.tile(scan_id, m)) for m in range(1, 13)]
    height = max(t.height for t in tiles)
    width = sum(t.width for t in tiles)
    page = Image.new("RGB", (width, height), (235, 230, 220))
    extents: list[BoxPx] = []
    x = 0
    for t in tiles:
        page.paste(t, (x, height - t.height))  # bottom-aligned like the originals
        extents.append(BoxPx(x=x, y=height - t.height, w=t.width, h=t.height))
        x += t.width
    return PseudoPage(image=page, scan_id=scan_id, year=year, extents=extents)


def pseudo_page_truth(pseudo: PseudoPage) -> dict:
    """JSON-able ground truth for the segmentation evaluation."""
    return {
        "scan_id": pseudo.scan_id,
        "year": pseudo.year,
        "extents": [[b.x, b.y, b.w, b.h] for b in pseudo.extents],
        "seams": [b.x for b in pseudo.extents[1:]],
        "days": [days_in_month(pseudo.year, m) for m in range(1, 13)],
        "width": pseudo.image.width,
        "height": pseudo.image.height,
    }


def pseudo_page_hints(pseudo: PseudoPage,
                      paths: ZenodoPaths | None = None) -> Hints:
    """Calibration + layout hints in PSEUDO-PAGE coordinates.

    The y-anchors are the dataset's LOW/HIGH annotation rows, mapped through the January
    tile (tile row + paste offset). All 12 panels share the scale, so global anchors
    suffice.
    """
    paths = paths or ZenodoPaths()
    ann: MonthAnnotations = load_month_yolo(paths.month_yolo(pseudo.scan_id))
    jan = pseudo.extents[0]
    c_low_t, c_high_t = tile_anchor_rows(ann, 1, jan.w, jan.h)
    unit = danube_unit_for(month_span(pseudo.year, 1)[0])
    return Hints(
        station=pseudo.scan_id[:2], year=pseudo.year, unit=unit.canonical,
        y_scale="linear", rotation_deg=0, expected_panels=12, panel_layout="row",
        y_anchors=[YAnchorHint(pixel=c_low_t + jan.y, value=ann.low_value),
                   YAnchorHint(pixel=c_high_t + jan.y, value=ann.high_value)],
        panels=[PanelHint(index=m, month=m) for m in range(1, 13)],
        notes=f"pseudo-page from Zenodo tiles, scan {pseudo.scan_id}",
    )


def write_pseudo_page(scan_id: str, year: int, out_dir: Path | str,
                      paths: ZenodoPaths | None = None) -> tuple[Path, Path, Path]:
    """Materialize pseudo_<scan>_<year>.png + hints.json + truth.json."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    pseudo = build_pseudo_page(scan_id, year, paths)
    png = out_dir / f"pseudo_{scan_id}_{year}.png"
    pseudo.image.save(png)
    hints_path = save_hints(pseudo_page_hints(pseudo, paths),
                            out_dir / f"pseudo_{scan_id}_{year}.hints.json")
    truth_path = out_dir / f"pseudo_{scan_id}_{year}.truth.json"
    truth_path.write_text(json.dumps(pseudo_page_truth(pseudo), indent=2),
                          encoding="utf-8")
    return png, hints_path, truth_path


def baseline_to_pseudo(pseudo: PseudoPage, ann: MonthAnnotations,
                       baseline_norm: list[tuple[float, float]]) -> list[tuple[float, float]]:
    """Map the full-page baseline polyline (normalized coords) into pseudo coordinates.

    Each polyline point falls into some month's bbox on the original page; it re-appears
    inside that month's tile on the pseudo page (bbox offset + tile margin + paste offset).
    """
    out: list[tuple[float, float]] = []
    for nx, ny in baseline_norm:
        px, py = nx * ann.width, ny * ann.height
        for m in range(1, 13):
            if m not in ann.boxes or m > len(pseudo.extents):
                continue
            bx0, by0, bx1, by1 = ann.boxes[m].edges_px(ann.width, ann.height)
            if not (bx0 <= px <= bx1):
                continue
            ext = pseudo.extents[m - 1]
            margin_x = (ext.w - (bx1 - bx0)) / 2.0
            margin_y = (ext.h - (by1 - by0)) / 2.0
            out.append((ext.x + margin_x + (px - bx0), ext.y + margin_y + (py - by0)))
            break
    return out
