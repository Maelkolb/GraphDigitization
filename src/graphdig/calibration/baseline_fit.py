"""Baseline (printed zero/reference line) warp correction.

Implements the paper's grid-aware baseline adjustment (Rehbein 2026, Sect. 4.5.3, Eqs. 9-11):
the printed zero line is described as an x-ordered polyline; its local deviation from the
ideal flat zero-pixel beta is subtracted from curve y-coordinates before the linear
pixel-to-value conversion.
"""

from __future__ import annotations

from collections.abc import Callable

import numpy as np

from graphdig.calibration.fit import AxisFit, pixel_at


def beta_from_anchors(c_low: float, v_low: float, c_high: float, v_high: float) -> float:
    """Paper Eq. 9: pixel y at which the fitted axis reads value zero."""
    if v_high == v_low:
        raise ValueError("anchors share the same value")
    return c_low - v_low / (v_high - v_low) * (c_high - c_low)


def beta_from_fit(fit: AxisFit) -> float:
    """Generalization of Eq. 9 to an n-tick fit: the zero-value pixel."""
    return pixel_at(fit, 0.0)


def interp_baseline(points_px: np.ndarray) -> Callable[[np.ndarray], np.ndarray]:
    """Piecewise-linear interpolation of the baseline polyline (paper Eq. 10).

    Points outside the annotated x-range take the nearest endpoint's y (np.interp default).
    """
    pts = np.asarray(points_px, dtype=float).reshape(-1, 2)
    order = np.argsort(pts[:, 0])
    xs, ys = pts[order, 0], pts[order, 1]
    return lambda xq: np.interp(np.asarray(xq, dtype=float), xs, ys)


def apply_baseline_correction(curve_xy: np.ndarray,
                              baseline: Callable[[np.ndarray], np.ndarray],
                              beta: float) -> np.ndarray:
    """Paper Eq. 11: y_corrected(x) = y(x) - (baseline(x) - beta).

    Where the printed zero line sags below its ideal pixel row (baseline(x) > beta),
    the same sag is removed from the measured curve.
    """
    pts = np.asarray(curve_xy, dtype=float).reshape(-1, 2).copy()
    pts[:, 1] = pts[:, 1] - (baseline(pts[:, 0]) - beta)
    return pts


def refine_points_cv(gray: np.ndarray, seeds_px: list[tuple[float, float]],
                     window: int = 25, strip: int = 3) -> list[tuple[float, float, float]]:
    """Snap coarse baseline seeds to the nearest dark ridge in a vertical window.

    Gemini localizes the printed line only approximately; this sharpens each seed to the
    darkest row (sub-pixel via parabolic interpolation) within +-window pixels. Returns
    (x, refined_y, delta) per seed; seeds with no clear ridge keep their original y (delta 0).
    """
    import cv2

    h, w = gray.shape[:2]
    out: list[tuple[float, float, float]] = []
    for x, y in seeds_px:
        xi = round(min(max(x, 0), w - 1))
        yi = round(min(max(y, 0), h - 1))
        x0, x1 = max(0, xi - strip), min(w, xi + strip + 1)
        y0, y1 = max(0, yi - window), min(h, yi + window + 1)
        column = gray[y0:y1, x0:x1].astype(np.float32).mean(axis=1)
        if column.size < 3:
            out.append((x, y, 0.0))
            continue
        profile = cv2.GaussianBlur(column.reshape(-1, 1), (1, 5), 0).ravel()
        idx = int(np.argmin(profile))
        # require a meaningful dip relative to the local spread, else keep the seed
        if profile.std() < 1e-3 or (profile.mean() - profile[idx]) < 0.5 * profile.std():
            out.append((x, y, 0.0))
            continue
        refined = float(idx)
        if 0 < idx < len(profile) - 1:  # parabolic sub-pixel refinement
            denom = profile[idx - 1] - 2 * profile[idx] + profile[idx + 1]
            if abs(denom) > 1e-9:
                refined += 0.5 * float(profile[idx - 1] - profile[idx + 1]) / float(denom)
        new_y = y0 + refined
        out.append((x, float(new_y), float(new_y - y)))
    return out
