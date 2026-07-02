"""Axis calibration: pixel -> physical value mapping.

Generalizes the paper's two-anchor linear map (Eq. 8) to a least-squares fit over all
legible axis ticks with iterative MAD-based outlier rejection. The two-anchor form remains
available both as a fallback (only 2 ticks readable) and for provenance/evaluation
(`anchor_equivalent`).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np


@dataclass(frozen=True)
class Tick:
    pixel: float  # coordinate along the axis (y pixel for the value axis)
    value: float  # labelled physical value
    label_text: str = ""
    used: bool = True  # set False by outlier rejection
    residual: float | None = None  # value-space residual after the final fit


@dataclass(frozen=True)
class AxisFit:
    """value = slope * pixel + intercept  (in log10(value) space when scale == "log")."""

    slope: float
    intercept: float
    scale: str = "linear"  # "linear" | "log"
    r2: float = 1.0
    rmse_value: float = 0.0
    n_ticks: int = 2
    n_used: int = 2
    n_rejected: int = 0
    method: str = "two_anchor"
    ticks: tuple[Tick, ...] = field(default=())


def value_at(fit: AxisFit, pixel: float | np.ndarray) -> float | np.ndarray:
    v = fit.slope * np.asarray(pixel, dtype=float) + fit.intercept
    if fit.scale == "log":
        v = np.power(10.0, v)
    return float(v) if np.ndim(pixel) == 0 else v


def pixel_at(fit: AxisFit, value: float) -> float:
    v = math.log10(value) if fit.scale == "log" else value
    if fit.slope == 0:
        raise ValueError("degenerate axis fit: slope is zero")
    return (v - fit.intercept) / fit.slope


def two_anchor_fit(c_low: float, v_low: float, c_high: float, v_high: float,
                   scale: str = "linear") -> AxisFit:
    """Exact paper mapping: v = (c - c_low)(v_high - v_low)/(c_high - c_low) + v_low."""
    if c_high == c_low:
        raise ValueError("anchors share the same pixel coordinate")
    lo, hi = (math.log10(v_low), math.log10(v_high)) if scale == "log" else (v_low, v_high)
    slope = (hi - lo) / (c_high - c_low)
    intercept = lo - slope * c_low
    ticks = (Tick(pixel=c_low, value=v_low), Tick(pixel=c_high, value=v_high))
    return AxisFit(slope=slope, intercept=intercept, scale=scale, method="two_anchor",
                   ticks=ticks)


def anchor_equivalent(fit: AxisFit, c_low: float, c_high: float) -> tuple[float, float]:
    """Values the fit implies at two pixel positions (paper-compatible anchor pair)."""
    return float(value_at(fit, c_low)), float(value_at(fit, c_high))


def fit_axis(ticks: list[Tick], scale: str = "linear",
             mad_k: float = 3.5, max_iter: int = 5) -> AxisFit:
    """Least-squares linear fit with iterative MAD outlier rejection (IRLS-style).

    Requires >= 2 ticks; with exactly 2 it degenerates to the two-anchor mapping.
    Residuals and rejection run in value space (log space for scale="log").
    """
    if len(ticks) < 2:
        raise ValueError(f"need at least 2 ticks, got {len(ticks)}")
    if scale == "log" and any(t.value <= 0 for t in ticks):
        raise ValueError("log scale requires strictly positive tick values")

    px = np.array([t.pixel for t in ticks], dtype=float)
    vals = np.array([t.value for t in ticks], dtype=float)
    y = np.log10(vals) if scale == "log" else vals

    if len(ticks) == 2:
        base = two_anchor_fit(px[0], vals[0], px[1], vals[1], scale=scale)
        return AxisFit(slope=base.slope, intercept=base.intercept, scale=scale,
                       method="two_anchor", ticks=tuple(ticks))

    keep = np.ones(len(ticks), dtype=bool)
    slope, intercept = 0.0, 0.0
    for _ in range(max_iter):
        if keep.sum() < 2:
            break
        slope, intercept = np.polyfit(px[keep], y[keep], 1)
        resid = y - (slope * px + intercept)
        r_kept = resid[keep]
        med = np.median(r_kept)
        mad = np.median(np.abs(r_kept - med))
        sigma = 1.4826 * mad
        if sigma <= 0:  # perfectly collinear (or too few points to estimate spread)
            break
        new_keep = np.abs(resid - med) <= mad_k * sigma
        new_keep |= ~keep & False  # rejected points stay rejected only if still outlying
        if new_keep.sum() < 2:
            break
        if np.array_equal(new_keep, keep):
            break
        keep = new_keep

    slope, intercept = np.polyfit(px[keep], y[keep], 1)
    resid = y - (slope * px + intercept)
    y_kept = y[keep]
    ss_res = float(np.sum(resid[keep] ** 2))
    ss_tot = float(np.sum((y_kept - y_kept.mean()) ** 2))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else (1.0 if ss_res == 0 else 0.0)
    rmse = math.sqrt(ss_res / keep.sum())

    out_ticks = tuple(
        Tick(pixel=t.pixel, value=t.value, label_text=t.label_text,
             used=bool(keep[i]), residual=float(resid[i]))
        for i, t in enumerate(ticks)
    )
    return AxisFit(slope=float(slope), intercept=float(intercept), scale=scale,
                   r2=float(r2), rmse_value=float(rmse), n_ticks=len(ticks),
                   n_used=int(keep.sum()), n_rejected=int((~keep).sum()),
                   method="irls_mad", ticks=out_ticks)
