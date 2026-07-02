"""Polyline-to-series resampling and candidate scoring.

Follows the paper's curve-to-series transformation (Sect. 4.4.5): partition the x-extent
into n equal slices and keep the LAST (max-x) point per slice, which outperformed
median/mean/medoid aggregation in the paper's evaluation. Coverage and the
confidence/coverage combination s_alpha (Eq. 12, alpha = 0.69) drive candidate selection.
"""

from __future__ import annotations

import numpy as np


def _slice_indices(x: np.ndarray, x0: float, x1: float, n: int) -> np.ndarray:
    """Slice index per point; points exactly at x1 belong to the last slice."""
    if x1 <= x0:
        raise ValueError("empty x-extent")
    idx = np.floor((x - x0) / (x1 - x0) * n).astype(int)
    return np.clip(idx, 0, n - 1)


def last_point_per_slice(points: np.ndarray, x0: float, x1: float, n: int) -> np.ndarray:
    """(n, 2) array with the max-x point per slice; empty slices are (nan, nan).

    Points outside [x0, x1] are ignored.
    """
    pts = np.asarray(points, dtype=float).reshape(-1, 2)
    out = np.full((n, 2), np.nan)
    inside = (pts[:, 0] >= x0) & (pts[:, 0] <= x1)
    pts = pts[inside]
    if pts.size == 0:
        return out
    order = np.argsort(pts[:, 0], kind="stable")
    pts = pts[order]
    idx = _slice_indices(pts[:, 0], x0, x1, n)
    out[idx] = pts  # ascending x: later assignments per slice win => last point kept
    return out


def last_index_per_slice(points: np.ndarray, x0: float, x1: float, n: int) -> np.ndarray:
    """(n,) int array with the input index of the max-x point per slice; -1 if empty.

    Same selection rule as last_point_per_slice, but returns indices so callers can carry
    parallel per-point data (e.g. corrected and uncorrected y) through the resampling.
    """
    pts = np.asarray(points, dtype=float).reshape(-1, 2)
    out = np.full(n, -1, dtype=int)
    inside = np.where((pts[:, 0] >= x0) & (pts[:, 0] <= x1))[0]
    if inside.size == 0:
        return out
    order = inside[np.argsort(pts[inside, 0], kind="stable")]
    idx = _slice_indices(pts[order, 0], x0, x1, n)
    out[idx] = order
    return out


def coverage(points: np.ndarray, x0: float, x1: float, n: int) -> float:
    """Fraction of the n slices that contain at least one predicted point (paper: 'coverage')."""
    sampled = last_point_per_slice(points, x0, x1, n)
    return float(np.mean(~np.isnan(sampled[:, 0])))


def s_alpha(confidence: float, cov: float, alpha_coverage: float = 0.69) -> float:
    """Paper Eq. 12: s_alpha = (1 - alpha) * confidence + alpha * coverage."""
    return (1.0 - alpha_coverage) * confidence + alpha_coverage * cov
