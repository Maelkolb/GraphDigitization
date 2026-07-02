"""Pseudo-page construction, hints/truth geometry, and full-page evaluation - all
against a fabricated miniature dataset (no Zenodo download needed)."""

from __future__ import annotations

import csv
import json
from dataclasses import replace

import pytest
from PIL import Image

from graphdig.artifacts import (
    ImageRef,
    Panel,
    PanelsArtifact,
    PanelSeries,
    SeriesArtifact,
    save_artifact,
)
from graphdig.data.danube_prep import tile_anchor_rows
from graphdig.data.gt_loaders import STEM, ZenodoPaths, load_month_yolo
from graphdig.data.pseudo_page import (
    baseline_to_pseudo,
    build_pseudo_page,
    pseudo_page_hints,
    pseudo_page_truth,
    write_pseudo_page,
)
from graphdig.eval.fullpage_eval import evaluate_fullpage_run, summarize
from graphdig.geometry import BoxPx

SCAN, YEAR = "990001", 1850
PAGE_W, PAGE_H = 1300, 400
BOX_W, BOX_H, BOX_Y0 = 90, 200, 150
MARGIN = 10  # tile margin per side (mirrors the real dataset's ~5px; any value works)
LOW, HIGH = 0.0, 5.0


@pytest.fixture
def mini_dataset(tmp_path) -> ZenodoPaths:
    paths = ZenodoPaths(root=tmp_path / "zenodo")
    ann_dir = paths.root / "monthannotations" / "months_annotations"
    ann_dir.mkdir(parents=True)
    lines = [f"# LOW_VALUE: {LOW}", f"# HIGH_VALUE: {HIGH}",
             f"# IMAGE_SIZE: {PAGE_W} {PAGE_H}"]
    for m in range(1, 13):
        x0 = 20 + (m - 1) * 105
        cx, cy = (x0 + BOX_W / 2) / PAGE_W, (BOX_Y0 + BOX_H / 2) / PAGE_H
        lines.append(f"{m} {cx:.6f} {cy:.6f} {BOX_W / PAGE_W:.6f} {BOX_H / PAGE_H:.6f}")
    (ann_dir / f"{STEM}_{SCAN}.tif.yolo").write_text("\n".join(lines), encoding="utf-8")

    tile_dir = paths.root / "images_months"
    tile_dir.mkdir(parents=True)
    for m in range(1, 13):
        img = Image.new("RGB", (BOX_W + 2 * MARGIN, BOX_H + 2 * MARGIN),
                        (200 + m, 200, 190))
        img.save(paths.tile(SCAN, m))
    return paths


def test_build_and_truth(mini_dataset):
    pseudo = build_pseudo_page(SCAN, YEAR, mini_dataset)
    assert pseudo.image.width == 12 * (BOX_W + 2 * MARGIN)
    truth = pseudo_page_truth(pseudo)
    assert len(truth["extents"]) == 12
    assert truth["extents"][1][0] == BOX_W + 2 * MARGIN  # February starts after January
    assert truth["days"][1] == 28  # 1850 non-leap


def test_hints_anchor_geometry(mini_dataset):
    pseudo = build_pseudo_page(SCAN, YEAR, mini_dataset)
    hints = pseudo_page_hints(pseudo, mini_dataset)
    assert hints.expected_panels == 12
    assert [ph.month for ph in hints.panels] == list(range(1, 13))
    ann = load_month_yolo(mini_dataset.month_yolo(SCAN))
    jan = pseudo.extents[0]
    c_low_t, _c_high_t = tile_anchor_rows(ann, 1, jan.w, jan.h)
    assert hints.y_anchors[0].pixel == pytest.approx(c_low_t + jan.y)
    assert hints.y_anchors[0].value == LOW
    assert hints.y_anchors[1].value == HIGH
    # anchors are the January bbox borders: bottom border row inside the tile + paste y
    assert hints.y_anchors[1].pixel == pytest.approx(jan.y + MARGIN, abs=1e-6)


def test_baseline_mapping(mini_dataset):
    pseudo = build_pseudo_page(SCAN, YEAR, mini_dataset)
    ann = load_month_yolo(mini_dataset.month_yolo(SCAN))
    # one point in the middle of February's bbox on the original page
    feb_x0 = 20 + 105
    norm = [((feb_x0 + BOX_W / 2) / PAGE_W, (BOX_Y0 + BOX_H / 2) / PAGE_H)]
    mapped = baseline_to_pseudo(pseudo, ann, norm)
    assert len(mapped) == 1
    ext = pseudo.extents[1]
    assert mapped[0][0] == pytest.approx(ext.x + MARGIN + BOX_W / 2, abs=0.01)
    assert mapped[0][1] == pytest.approx(ext.y + MARGIN + BOX_H / 2, abs=0.01)


def test_write_pseudo_page(mini_dataset, tmp_path):
    png, hints_path, truth_path = write_pseudo_page(SCAN, YEAR, tmp_path / "out",
                                                    mini_dataset)
    assert png.exists() and hints_path.exists() and truth_path.exists()
    truth = json.loads(truth_path.read_text(encoding="utf-8"))
    assert truth["scan_id"] == SCAN


def test_backcompat_reexport():
    from graphdig.data.pseudo_page import PseudoPage
    from graphdig.eval.panels_eval import PseudoPage as ReExported

    assert ReExported is PseudoPage


def test_evaluate_fullpage_run(mini_dataset, tmp_path):
    from graphdig.calibration.fit import value_at
    from graphdig.eval.calibration_eval import _human_fit

    pseudo = build_pseudo_page(SCAN, YEAR, mini_dataset)
    truth = pseudo_page_truth(pseudo)
    ann = load_month_yolo(mini_dataset.month_yolo(SCAN))
    human = _human_fit(ann)

    # fabricated pixel GT: January daily rows whose GAUGELEVEL = (grid + 1) * 29
    gt_dir = mini_dataset.gt_pixels(SCAN).parent
    gt_dir.mkdir(parents=True)
    c_rows = [BOX_Y0 + 20 + (d % 5) * 25 for d in range(31)]
    with open(mini_dataset.gt_pixels(SCAN), "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["INDEX", "C_X", "C_Y", "DATE", "GAUGELEVEL"])
        for d, cy in enumerate(c_rows, start=1):
            grid = float(value_at(human, cy))
            w.writerow([d, 30 + d, cy, f"1850-01-{d:02d}", (grid + 1.0) * 29.0])

    # fabricated run: 12 panels at truth extents shifted +3 px; January series exact
    run_dir = tmp_path / "run"
    (run_dir / "series").mkdir(parents=True)
    panels = []
    for m, (x, y, w_, h) in enumerate(truth["extents"], start=1):
        box = BoxPx(x=x + 3, y=y, w=w_, h=h)
        panels.append(Panel(panel_id=f"p{m:02d}", month=m, bbox_px=box,
                            plot_area_px=box, confidence=1.0))
    save_artifact(PanelsArtifact(page_id="pseudo", panels=panels,
                                 image=ImageRef(path="pages/x.png",
                                                width=truth["width"],
                                                height=truth["height"])),
                  run_dir / "panels.json")
    with open(run_dir / "series" / "p01.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["x_key", "value_native", "native_unit", "value_mm",
                    "pixel_x_page", "pixel_y_page", "pixel_y_corrected", "flagged"])
        for d, cy in enumerate(c_rows, start=1):
            grid = float(value_at(human, cy))
            w.writerow([f"1850-01-{d:02d}", f"{grid:.4f}", "bavarian_foot", "",
                        "0", "0", "0", "false"])
    save_artifact(SeriesArtifact(panels={"p01": PanelSeries(
        csv_path="series/p01.csv", panel_id="p01", n=31, x_kind="date")}),
        run_dir / "series.json")

    rows = evaluate_fullpage_run(run_dir, truth, mini_dataset)
    assert len(rows) == 12
    jan = rows[0]
    assert jan.detected and jan.iou > 0.9
    px_per_day = truth["extents"][0][2] / 31
    assert jan.left_err_days == pytest.approx(3 / px_per_day, abs=0.01)
    assert jan.n_matched == 31
    assert jan.peak_score == pytest.approx(1.0, abs=1e-6)
    assert jan.rmse == pytest.approx(0.0, abs=1e-6)
    s = summarize(rows)
    assert s["detected"] == 12
    assert replace(jan).month == 1  # dataclass usable downstream
