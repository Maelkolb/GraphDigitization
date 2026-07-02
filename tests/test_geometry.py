import numpy as np
import pytest

from graphdig.geometry import Box1000, BoxPx, Transform2D, bbox_1000_to_px, point_1000_to_px


def test_bbox_conversion_and_clamp():
    box = bbox_1000_to_px(Box1000(x0=100, y0=200, x1=500, y1=900), width=2000, height=1000)
    assert (box.x, box.y, box.right, box.bottom) == (200, 200, 1000, 900)


def test_bbox_swapped_edges_ordered():
    box = bbox_1000_to_px(Box1000(x0=500, y0=900, x1=100, y1=200), width=1000, height=1000)
    assert box.x == 100 and box.y == 200
    assert box.right == 500 and box.bottom == 900


def test_bbox_min_size_enforced():
    box = bbox_1000_to_px(Box1000(x0=500, y0=500, x1=500, y1=500), width=1000, height=1000)
    assert box.w >= 10 and box.h >= 10


def test_bbox_out_of_range_clamped():
    box = bbox_1000_to_px(Box1000(x0=-50, y0=0, x1=1200, y1=1000), width=800, height=600)
    assert box.x == 0 and box.y == 0
    assert box.right == 800 and box.bottom == 600


def test_point_conversion():
    assert point_1000_to_px(500, 250, 2000, 1000) == (1000.0, 250.0)


def test_transform_roundtrip_with_stretch():
    t = Transform2D(crop_x=120, crop_y=40, x_scale=2.0, y_scale=1.0)
    page_pts = np.array([[130.0, 50.0], [500.0, 300.0]])
    tile = t.page_to_tile(page_pts)
    assert tile[0].tolist() == [20.0, 10.0]
    back = t.tile_to_page(tile)
    assert np.allclose(back, page_pts)


def test_iou():
    a = BoxPx(x=0, y=0, w=10, h=10)
    b = BoxPx(x=5, y=0, w=10, h=10)
    assert a.iou(b) == pytest.approx(50 / 150)
    assert a.iou(a) == 1.0


def test_expand_clamped():
    a = BoxPx(x=5, y=5, w=10, h=10)
    e = a.expand(10, 10, width=20, height=20)
    assert (e.x, e.y, e.right, e.bottom) == (0, 0, 20, 20)
