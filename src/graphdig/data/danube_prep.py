"""Seed pipeline runs for Danube monthly tiles from the published human annotations.

The Zenodo dataset ships monthly tiles WITHOUT any axis labels (they live on the unpublished
full-page margins), so Gemini cannot read absolute values here. This module reproduces the
paper's actual production setup instead: y-calibration from the month-annotation anchors
(LOW/HIGH at the January-box borders), panel = the tile itself, dates from the scan-id
mapping - then the automated stages (preprocess, extract, select, series, qc, report) run
unchanged. Gemini calibration/panel detection is exercised on label-bearing charts
(forestry samples, synthetic fixtures, your own full-page scans).
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image

from graphdig.artifacts import (
    AnchorEquivalent,
    CalibrationArtifact,
    FitModel,
    ImageRef,
    MetadataArtifact,
    Panel,
    PanelCalibration,
    PanelsArtifact,
    TickModel,
    XAxisCal,
    YAxisCal,
)
from graphdig.calibration.fit import two_anchor_fit
from graphdig.config import RunConfig
from graphdig.data.gt_loaders import ZenodoPaths, load_month_yolo
from graphdig.dates import month_span
from graphdig.geometry import BoxPx
from graphdig.runs import create_run_dir, init_manifest, save_manifest, sha256_file, stage_done
from graphdig.units import danube_unit_for


def prepare_run(scan_id: str, month: int, year: int,
                cfg: RunConfig, paths: ZenodoPaths | None = None) -> Path:
    """Create a run dir with ingest/panels/calibrate/metadata pre-seeded from annotations."""
    paths = paths or ZenodoPaths()
    tile_path = paths.tile(scan_id, month)
    ann = load_month_yolo(paths.month_yolo(scan_id))
    if month not in ann.boxes:
        raise ValueError(f"no month annotation for {scan_id} M{month:02d}")

    run_dir = create_run_dir(cfg.out_parent, f"{scan_id}_tif_M{month:02d}")
    manifest = init_manifest(run_dir, cfg.profile_name, cfg.model_dump(mode="json"), [])
    (run_dir / "input.txt").write_text(str(tile_path.resolve()), encoding="utf-8")

    img = Image.open(tile_path).convert("RGB")
    page_name = f"{scan_id}_M{month:02d}.png"
    img.save(run_dir / "pages" / page_name)
    manifest.inputs = [ImageRef(path=f"pages/{page_name}", width=img.width,
                                height=img.height,
                                sha256=sha256_file(run_dir / "pages" / page_name))]
    save_manifest(run_dir, manifest)

    # panel geometry: tile = month bbox + symmetric margin
    _bx0, by0, bx1, by1 = ann.boxes[month].edges_px(ann.width, ann.height)
    bbox_w, bbox_h = bx1 - _bx0, by1 - by0
    margin_x = (img.width - bbox_w) / 2.0
    margin_y = (img.height - bbox_h) / 2.0
    plot = BoxPx(x=round(margin_x), y=round(margin_y),
                 w=round(bbox_w), h=round(bbox_h))
    panel = Panel(panel_id="p01", label=f"M{month:02d}",
                  bbox_px=BoxPx(x=0, y=0, w=img.width, h=img.height),
                  plot_area_px=plot, confidence=1.0, flags=["seeded_from_annotations"])
    panels_art = PanelsArtifact(page_id=f"{scan_id}_M{month:02d}",
                                image=manifest.inputs[0], panels=[panel])
    from graphdig.artifacts import save_artifact

    save_artifact(panels_art, run_dir / "panels.json")

    # y calibration: anchors are page rows; tile row = page row - (by0 - margin_y)
    offset = by0 - margin_y
    c_low, c_high = ann.anchors_px  # page rows of LOW/HIGH values
    c_low_t, c_high_t = c_low - offset, c_high - offset
    fit = two_anchor_fit(c_low_t, ann.low_value, c_high_t, ann.high_value)
    unit = danube_unit_for(month_span(year, month)[0])
    d0, d1 = month_span(year, month)
    cal = PanelCalibration(
        y_axis=YAxisCal(
            unit={"raw": unit.canonical, "canonical": unit.canonical, "to_mm": unit.to_mm},
            ticks=[TickModel(pixel=c_low_t, value=ann.low_value, label_text="anchor_low"),
                   TickModel(pixel=c_high_t, value=ann.high_value, label_text="anchor_high")],
            fit=FitModel(method="human_anchors", slope=fit.slope, intercept=fit.intercept),
            anchor_equivalent=AnchorEquivalent(c_low=c_low_t, v_low=ann.low_value,
                                               c_high=c_high_t, v_high=ann.high_value),
            confidence=1.0, flags=["seeded_from_annotations"]),
        x_axis=XAxisCal(kind="date", start=d0.isoformat(), end=d1.isoformat(),
                        n_samples=(d1 - d0).days + 1, confidence=1.0),
    )
    save_artifact(CalibrationArtifact(panels={"p01": cal}), run_dir / "calibration.json")
    save_artifact(MetadataArtifact(station=scan_id[:2], year=year,
                                   y_unit_declared=unit.canonical, confidence=1.0),
                  run_dir / "metadata.json")

    for stage in ("ingest", "panels", "calibrate", "metadata"):
        stage_done(run_dir, manifest, stage)
    return run_dir
