import numpy as np
import pytest

from graphdig.calibration.baseline_fit import (
    apply_baseline_correction,
    beta_from_anchors,
    beta_from_fit,
    interp_baseline,
    refine_points_cv,
)
from graphdig.calibration.fit import two_anchor_fit


def test_beta_hand_computed():
    # beta = c_low - v_low/(v_high - v_low) * (c_high - c_low)
    assert beta_from_anchors(800, 2.0, 200, 10.0) == pytest.approx(950.0)


def test_beta_from_fit_agrees_with_anchor_formula():
    fit = two_anchor_fit(800, 2.0, 200, 10.0)
    assert beta_from_fit(fit) == pytest.approx(beta_from_anchors(800, 2.0, 200, 10.0))


def test_interp_baseline_extends_endpoints():
    f = interp_baseline(np.array([[10.0, 100.0], [20.0, 110.0]]))
    assert f(np.array([0.0]))[0] == pytest.approx(100.0)
    assert f(np.array([15.0]))[0] == pytest.approx(105.0)
    assert f(np.array([99.0]))[0] == pytest.approx(110.0)


def test_baseline_correction_removes_synthetic_warp():
    beta = 950.0
    xs = np.linspace(0, 100, 51)
    sag = 5.0 * np.sin(np.pi * xs / 100)  # printed zero line sags up to 5 px mid-page
    baseline_pts = np.column_stack([xs, beta + sag])
    curve = np.column_stack([xs, 400.0 + sag])  # true flat curve drawn with the same warp
    corrected = apply_baseline_correction(curve, interp_baseline(baseline_pts), beta)
    assert np.allclose(corrected[:, 1], 400.0, atol=1e-9)
    assert np.allclose(corrected[:, 0], xs)


def test_refine_points_cv_snaps_to_dark_line():
    img = np.full((200, 100), 220, dtype=np.uint8)
    img[143:146, :] = 30  # dark horizontal line at y~144
    refined = refine_points_cv(img, [(50.0, 150.0)], window=20)
    (x, y, delta) = refined[0]
    assert x == 50.0
    assert y == pytest.approx(144.0, abs=1.5)
    assert delta == pytest.approx(y - 150.0)


def test_refine_points_cv_keeps_seed_without_ridge():
    img = np.full((200, 100), 220, dtype=np.uint8)  # no line anywhere
    refined = refine_points_cv(img, [(50.0, 100.0)], window=20)
    assert refined[0][1] == 100.0
    assert refined[0][2] == 0.0
