"""Coordinate handling: Gemini's 0-1000 normalized space, pixel space, tile/page transforms.

Gemini localization returns integer coordinates normalized to 0-1000 on the image it saw
(convention from the Gemini docs, also used by HistOrniGraph's region detector). Everything
downstream works in pixels; conversion and clamping happen here and nowhere else.
"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
from pydantic import BaseModel

NORM = 1000.0


class BoxPx(BaseModel):
    """Axis-aligned pixel box, origin top-left, y down."""

    x: int
    y: int
    w: int
    h: int

    @property
    def right(self) -> int:
        return self.x + self.w

    @property
    def bottom(self) -> int:
        return self.y + self.h

    def iou(self, other: BoxPx) -> float:
        ix = max(0, min(self.right, other.right) - max(self.x, other.x))
        iy = max(0, min(self.bottom, other.bottom) - max(self.y, other.y))
        inter = ix * iy
        union = self.w * self.h + other.w * other.h - inter
        return inter / union if union > 0 else 0.0

    def expand(self, margin_x: int, margin_y: int, width: int, height: int) -> BoxPx:
        """Grow by a margin, clamped to the image."""
        x0 = max(0, self.x - margin_x)
        y0 = max(0, self.y - margin_y)
        x1 = min(width, self.right + margin_x)
        y1 = min(height, self.bottom + margin_y)
        return BoxPx(x=x0, y=y0, w=x1 - x0, h=y1 - y0)


class Box1000(BaseModel):
    """Gemini-space box: 0-1000 normalized, given as edges."""

    x0: float
    y0: float
    x1: float
    y1: float


def norm_to_px(v: float, dim: int) -> float:
    return v / NORM * dim


def px_to_norm(v: float, dim: int) -> float:
    return v / dim * NORM


def point_1000_to_px(x1000: float, y1000: float, width: int, height: int) -> tuple[float, float]:
    x = min(max(norm_to_px(x1000, width), 0.0), float(width))
    y = min(max(norm_to_px(y1000, height), 0.0), float(height))
    return x, y


def bbox_1000_to_px(box: Box1000, width: int, height: int, min_size: int = 10) -> BoxPx:
    """Convert and sanitize a Gemini box: order edges, clamp to image, enforce min size."""
    x0, x1 = sorted((box.x0, box.x1))
    y0, y1 = sorted((box.y0, box.y1))
    px0 = round(norm_to_px(x0, width))
    px1 = round(norm_to_px(x1, width))
    py0 = round(norm_to_px(y0, height))
    py1 = round(norm_to_px(y1, height))
    px0, px1 = max(0, px0), min(width, px1)
    py0, py1 = max(0, py0), min(height, py1)
    if px1 - px0 < min_size:
        px1 = min(width, px0 + min_size)
        px0 = max(0, px1 - min_size)
    if py1 - py0 < min_size:
        py1 = min(height, py0 + min_size)
        py0 = max(0, py1 - min_size)
    return BoxPx(x=px0, y=py0, w=px1 - px0, h=py1 - py0)


class Transform2D(BaseModel):
    """Affine map between page space and tile space.

    tile = (page - crop_offset) * scale;  page = tile / scale + crop_offset.
    Records how a tile was cut and stretched so extracted points can be mapped back.
    """

    crop_x: float = 0.0
    crop_y: float = 0.0
    x_scale: float = 1.0
    y_scale: float = 1.0

    def page_to_tile(self, xy: np.ndarray | Sequence[Sequence[float]]) -> np.ndarray:
        pts = np.asarray(xy, dtype=float).reshape(-1, 2)
        out = np.empty_like(pts)
        out[:, 0] = (pts[:, 0] - self.crop_x) * self.x_scale
        out[:, 1] = (pts[:, 1] - self.crop_y) * self.y_scale
        return out

    def tile_to_page(self, xy: np.ndarray | Sequence[Sequence[float]]) -> np.ndarray:
        pts = np.asarray(xy, dtype=float).reshape(-1, 2)
        out = np.empty_like(pts)
        out[:, 0] = pts[:, 0] / self.x_scale + self.crop_x
        out[:, 1] = pts[:, 1] / self.y_scale + self.crop_y
        return out
