"""Series-level accuracy metrics (Rehbein 2026, Sect. 4.2).

All metrics operate on aligned prediction/truth arrays; NaN pairs are dropped first
(the paper computes the composite "on aligned daily series after an inner join on dates").
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np


def _aligned(y_true: np.ndarray, y_pred: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    t = np.asarray(y_true, dtype=float).ravel()
    p = np.asarray(y_pred, dtype=float).ravel()
    if t.shape != p.shape:
        raise ValueError(f"shape mismatch: {t.shape} vs {p.shape}")
    mask = ~(np.isnan(t) | np.isnan(p))
    return t[mask], p[mask]


def rmse(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    t, p = _aligned(y_true, y_pred)
    return float(np.sqrt(np.mean((p - t) ** 2))) if t.size else math.nan


def mae(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    t, p = _aligned(y_true, y_pred)
    return float(np.mean(np.abs(p - t))) if t.size else math.nan


def maxae(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    t, p = _aligned(y_true, y_pred)
    return float(np.max(np.abs(p - t))) if t.size else math.nan


def pearson_r(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Pearson correlation; 0.0 when either series is constant/invalid (paper convention)."""
    t, p = _aligned(y_true, y_pred)
    if t.size < 2 or np.std(t) == 0 or np.std(p) == 0:
        return 0.0
    return float(np.corrcoef(t, p)[0, 1])


@dataclass(frozen=True)
class PeakScore:
    score: float
    pearson_r: float
    s_peak_val: float  # 1 - |ymax - ŷmax| / ymax, NOT clamped (sensitivity to overshoot)
    s_peak_time: float  # max(0, 1 - d/N)
    peak_day_offset: int


def peak_aware_score(y_true: np.ndarray, y_pred: np.ndarray,
                     alpha: float = 0.4, beta: float = 0.4) -> PeakScore:
    """Custom peak-aware composite (paper Sect. 4.2.3): alpha*r + beta*s_val + gamma*s_time,
    gamma = 1 - alpha - beta. Defaults are the paper's reference setting (0.4/0.4/0.2)."""
    t, p = _aligned(y_true, y_pred)
    gamma = 1.0 - alpha - beta
    if t.size == 0:
        return PeakScore(math.nan, 0.0, 0.0, 0.0, 0)

    r = pearson_r(t, p)

    ymax = float(np.max(t))
    yhat_max = float(np.max(p))
    s_val = 1.0 - abs(ymax - yhat_max) / ymax if ymax != 0 else 0.0

    n = t.size
    d = abs(int(np.argmax(t)) - int(np.argmax(p)))
    s_time = max(0.0, 1.0 - d / n)

    return PeakScore(score=alpha * r + beta * s_val + gamma * s_time,
                     pearson_r=r, s_peak_val=s_val, s_peak_time=s_time, peak_day_offset=d)


def all_metrics(y_true: np.ndarray, y_pred: np.ndarray,
                alpha: float = 0.4, beta: float = 0.4) -> dict[str, float]:
    ps = peak_aware_score(y_true, y_pred, alpha=alpha, beta=beta)
    return {
        "rmse": rmse(y_true, y_pred),
        "mae": mae(y_true, y_pred),
        "maxae": maxae(y_true, y_pred),
        "pearson_r": ps.pearson_r,
        "peak_score": ps.score,
        "s_peak_val": ps.s_peak_val,
        "s_peak_time": ps.s_peak_time,
        "peak_day_offset": float(ps.peak_day_offset),
    }
