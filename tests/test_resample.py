import numpy as np
import pytest

from graphdig.series.resample import coverage, last_point_per_slice, s_alpha


def test_last_point_per_slice_keeps_max_x():
    # two points in slice 0 of [0, 10) with n=2: the later (larger x) must win
    pts = np.array([[1.0, 11.0], [4.0, 22.0], [7.0, 33.0]])
    out = last_point_per_slice(pts, 0.0, 10.0, 2)
    assert out[0].tolist() == [4.0, 22.0]
    assert out[1].tolist() == [7.0, 33.0]


def test_last_point_per_slice_empty_slices_nan():
    pts = np.array([[0.5, 1.0]])
    out = last_point_per_slice(pts, 0.0, 30.0, 30)
    assert not np.isnan(out[0]).any()
    assert np.isnan(out[1:]).all()


def test_point_at_right_edge_belongs_to_last_slice():
    pts = np.array([[31.0, 5.0]])
    out = last_point_per_slice(pts, 0.0, 31.0, 31)
    assert out[30].tolist() == [31.0, 5.0]


def test_points_outside_extent_ignored():
    pts = np.array([[-1.0, 0.0], [32.0, 0.0], [15.0, 7.0]])
    out = last_point_per_slice(pts, 0.0, 31.0, 31)
    assert np.count_nonzero(~np.isnan(out[:, 0])) == 1


def test_coverage_full_and_partial():
    xs = np.linspace(0.1, 30.9, 500)
    full = np.column_stack([xs, np.ones_like(xs)])
    assert coverage(full, 0.0, 31.0, 31) == pytest.approx(1.0)
    half = full[xs < 15.5]
    assert coverage(half, 0.0, 31.0, 31) == pytest.approx(15 / 31, abs=0.05)


def test_s_alpha_paper_weights():
    # paper: s_alpha = (1-0.69)*confidence + 0.69*coverage
    assert s_alpha(1.0, 0.0) == pytest.approx(0.31)
    assert s_alpha(0.0, 1.0) == pytest.approx(0.69)
    assert s_alpha(0.8, 0.99, alpha_coverage=0.69) == pytest.approx(0.31 * 0.8 + 0.69 * 0.99)
