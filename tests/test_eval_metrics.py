import numpy as np
import pytest

from graphdig.eval.metrics import all_metrics, mae, maxae, peak_aware_score, pearson_r, rmse


@pytest.fixture
def month():
    rng = np.random.default_rng(7)
    y = 1000 + 300 * np.sin(np.linspace(0, 3, 31)) + rng.normal(0, 5, 31)
    return y


def test_perfect_prediction(month):
    ps = peak_aware_score(month, month)
    assert ps.score == pytest.approx(1.0)
    assert ps.pearson_r == pytest.approx(1.0)
    assert ps.s_peak_val == pytest.approx(1.0)
    assert ps.s_peak_time == 1.0
    assert rmse(month, month) == 0.0


def test_constant_series_r_is_zero():
    const = np.full(31, 5.0)
    varying = np.arange(31, dtype=float)
    assert pearson_r(const, varying) == 0.0
    assert pearson_r(varying, const) == 0.0


def test_peak_val_unclamped_negative_on_extreme_overshoot(month):
    pred = month.copy()
    pred[10] = 3 * month.max()  # gross overshoot
    ps = peak_aware_score(month, pred)
    assert ps.s_peak_val < -0.5  # 1 - |ymax-3ymax|/ymax ~= -1 (unclamped by design)


def test_peak_time_penalty(month):
    true = np.zeros(31)
    true[5] = 100.0
    pred = np.zeros(31)
    pred[25] = 100.0
    ps = peak_aware_score(true, pred)
    assert ps.peak_day_offset == 20
    assert ps.s_peak_time == pytest.approx(1 - 20 / 31)


def test_composite_weights():
    true = np.array([0.0, 1.0, 2.0, 1.0, 0.0])
    ps = peak_aware_score(true, true, alpha=0.4, beta=0.4)
    assert ps.score == pytest.approx(0.4 * 1 + 0.4 * 1 + 0.2 * 1)


def test_nan_pairs_dropped():
    t = np.array([1.0, 2.0, np.nan, 4.0])
    p = np.array([1.0, np.nan, 3.0, 4.0])
    assert rmse(t, p) == 0.0
    assert mae(t, p) == 0.0
    assert maxae(t, p) == 0.0


def test_all_metrics_keys(month):
    m = all_metrics(month, month + 1.0)
    assert set(m) == {"rmse", "mae", "maxae", "pearson_r", "peak_score",
                      "s_peak_val", "s_peak_time", "peak_day_offset"}
    assert m["rmse"] == pytest.approx(1.0)
