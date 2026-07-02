"""GT loaders against inline fixtures copied verbatim from the real Zenodo files."""

from __future__ import annotations

import pytest

from graphdig.data.gt_loaders import (
    gauge_id_for_scan,
    load_baseline_yolo,
    load_gt_pixels,
    load_month_yolo,
)

MONTH_YOLO = """\
# LOW_VALUE: 0.5
# HIGH_VALUE: 3.5
# IMAGE_SIZE: 10062 4362
# DATE_TIME: 2025-05-20 14:27:54
# ANNOTATION_DURATION_SECONDS: 261.88
# MODIFIED: 2025-08-13 13:16:32
1 0.098092 0.832072 0.072351 0.064878
2 0.168655 0.799404 0.064798 0.129298
12 0.932072 0.783471 0.071656 0.128152
"""

BASELINE_YOLO = """\
# IMAGE_SIZE: 10062 4362
# DATE_TIME: 2025-08-13 17:05:02
# ANNOTATION_DURATION_SECONDS: 27.02
0 0.061618 0.853737 0.496223 0.852361 0.968595 0.841128
"""

GT_CSV = """\
INDEX,C_X,C_Y,DATE,GAUGELEVEL,ICE,REMARKS,date,GAUGELEVEL_NO_ADJUSTMENT
1,552,3678,1839-01-01,21.326229311820786,,,1839-01-01,49.40588644051472
2,577,3685,1839-01-02,19.10964576365678,,,1839-01-02,47.24167284233807
"""


def test_month_yolo(tmp_path):
    path = tmp_path / "Bay_Landesamt_fuer_Wasserwirtschaft_210003.tif.yolo"
    path.write_text(MONTH_YOLO, encoding="utf-8")
    ann = load_month_yolo(path)
    assert ann.scan_id == "210003"
    assert ann.low_value == 0.5 and ann.high_value == 3.5
    assert (ann.width, ann.height) == (10062, 4362)
    assert set(ann.boxes) == {1, 2, 12}
    # anchors: bottom/top border of the January box (descriptor Sect. 3.1)
    c_low, c_high = ann.anchors_px
    jan = ann.boxes[1]
    assert c_low == pytest.approx((jan.cy + jan.h / 2) * 4362)
    assert c_high == pytest.approx((jan.cy - jan.h / 2) * 4362)
    assert c_low > c_high  # low value sits lower on the page (larger y)


def test_baseline_yolo(tmp_path):
    path = tmp_path / "b.yolo"
    path.write_text(BASELINE_YOLO, encoding="utf-8")
    pts = load_baseline_yolo(path)
    assert len(pts) == 3
    assert pts[0] == pytest.approx((0.061618, 0.853737))
    assert pts[-1] == pytest.approx((0.968595, 0.841128))


def test_gt_pixels(tmp_path):
    path = tmp_path / "gt.csv"
    path.write_text(GT_CSV, encoding="utf-8")
    df = load_gt_pixels(path)
    assert list(df.columns) == ["C_X", "C_Y", "DATE", "GAUGELEVEL"]
    assert df["DATE"].iloc[0].year == 1839
    assert df["GAUGELEVEL"].iloc[1] == pytest.approx(19.1096, abs=1e-3)


def test_gauge_id_mapping():
    assert gauge_id_for_scan("210018") == "DE_BY_DAN_21"
    assert gauge_id_for_scan("300070") == "DE_BY_DAN_30"
