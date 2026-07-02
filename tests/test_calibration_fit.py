import numpy as np
import pytest

from graphdig.calibration.fit import (
    Tick,
    anchor_equivalent,
    fit_axis,
    pixel_at,
    two_anchor_fit,
    value_at,
)


def test_two_anchor_matches_paper_equation():
    # v = (c - c_low)(v_high - v_low)/(c_high - c_low) + v_low, hand-computed example
    fit = two_anchor_fit(c_low=800, v_low=2.0, c_high=200, v_high=10.0)
    assert value_at(fit, 500) == pytest.approx(6.0)
    assert value_at(fit, 800) == pytest.approx(2.0)
    assert value_at(fit, 200) == pytest.approx(10.0)


def test_pixel_at_inverts_value_at():
    fit = two_anchor_fit(c_low=800, v_low=2.0, c_high=200, v_high=10.0)
    assert pixel_at(fit, value_at(fit, 431.0)) == pytest.approx(431.0)


def test_two_anchor_requires_distinct_pixels():
    with pytest.raises(ValueError):
        two_anchor_fit(c_low=100, v_low=1.0, c_high=100, v_high=2.0)


def test_fit_axis_two_ticks_equals_two_anchor():
    ticks = [Tick(pixel=800, value=2.0), Tick(pixel=200, value=10.0)]
    fit = fit_axis(ticks)
    ref = two_anchor_fit(800, 2.0, 200, 10.0)
    assert fit.slope == pytest.approx(ref.slope)
    assert fit.intercept == pytest.approx(ref.intercept)
    assert fit.method == "two_anchor"


def test_fit_axis_rejects_planted_outlier():
    rng = np.random.default_rng(42)
    slope, intercept = -0.02, 25.0
    px = np.linspace(100, 900, 9)
    ticks = [Tick(pixel=float(p), value=float(slope * p + intercept + rng.normal(0, 0.01)))
             for p in px]
    ticks.append(Tick(pixel=500.0, value=slope * 500 + intercept + 5.0))  # gross misread
    fit = fit_axis(ticks)
    assert fit.method == "irls_mad"
    assert fit.n_rejected == 1
    assert not fit.ticks[-1].used
    assert fit.slope == pytest.approx(slope, rel=0.01)
    assert fit.r2 > 0.999


def test_fit_axis_perfect_collinear():
    ticks = [Tick(pixel=float(p), value=float(-0.5 * p + 100)) for p in (100, 300, 500, 700)]
    fit = fit_axis(ticks)
    assert fit.n_rejected == 0
    assert fit.r2 == pytest.approx(1.0)
    assert fit.rmse_value == pytest.approx(0.0, abs=1e-9)


def test_fit_axis_log_scale():
    # ticks at 1, 10, 100, 1000 equally spaced in pixels -> perfect log fit
    ticks = [Tick(pixel=float(900 - i * 200), value=float(10 ** i)) for i in range(4)]
    fit = fit_axis(ticks, scale="log")
    assert fit.scale == "log"
    assert value_at(fit, 700.0) == pytest.approx(10.0, rel=1e-6)
    assert pixel_at(fit, 100.0) == pytest.approx(500.0, rel=1e-6)


def test_fit_axis_needs_two_ticks():
    with pytest.raises(ValueError):
        fit_axis([Tick(pixel=1.0, value=1.0)])


def test_anchor_equivalent_roundtrip():
    ticks = [Tick(pixel=float(p), value=float(-0.5 * p + 100)) for p in (100, 300, 500, 700)]
    fit = fit_axis(ticks)
    v_low, v_high = anchor_equivalent(fit, 700, 100)
    ref = two_anchor_fit(700, v_low, 100, v_high)
    assert ref.slope == pytest.approx(fit.slope)
    assert ref.intercept == pytest.approx(fit.intercept)
